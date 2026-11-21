"""
La compra más barata de una sucursal que cubre las metas de un hogar: un problema de la dieta (Stigler, 1945) con
envases enteros, resuelto con HiGHS (scipy) en dos etapas. Cada persona tiene su propia dieta; la compra es común.

Variables (por persona i y producto p de la sucursal apto para ella; y por producto):
  c_ip  gramos comestibles que la persona come por día (continua, >= 0)
  x_p   unidades que se compran: envases o pasos de 100 g a granel (entera, >= 0)
  d_ik  déficit relativo de la meta k de la persona i (lo que falta del mínimo o sobra del máximo, como fracción)

Restricciones:
  - lo comprado alcanza para lo que comen todos en el período:  x_p * gramos_comestibles_p >= días * sum_i c_ip
  - energía de cada persona dentro de ±5 % de su meta (dura: con otra energía es otra dieta)
  - cada meta k de cada persona (nutriente o regla de las Guías):  sum_p a_kp c_ip + meta_k * d_ik >= meta_k (mínimos)
                                                                   sum_p a_kp c_ip - meta_k * d_ik <= meta_k (máximos)
  - variedad: nadie come más de 2 porciones por día de un mismo alimento genérico (escaladas por su energía); el agua
    y la soda, hasta la meta de agua de la persona (si se le exige a la compra).

Las metas informativas (vitamina D; B12 de un vegano) no entran en el modelo: solo se informa cuánto aportan.

Etapa 1 (programa lineal, sin precios): minimizar sum peso_k * d_ik. Da lo mejor que se puede cumplir con lo que
vende la sucursal; si todo se cumple, d* = 0.
Etapa 2 (entera): minimizar el costo de lo comprado sin que ningún déficit pase de d*. Primero la relajación lineal
sobre toda la oferta; después el modelo entero solo con las subcategorías que usó (con todas sus presentaciones), que
es chico y se resuelve rápido. Lo que se compra y no se come en el período se informa como sobrante.

Promociones (etapa 5; solo si se aplican y solo en los productos con una promoción aplicable, columnas promo_* de
canasta/oferta.py). La etapa 1 no cambia (no tiene precios: las metas son las mismas con o sin promociones, que solo
bajan el costo de la etapa 2). Con precio de lista P_p, precio por unidad con la promoción Q_p < P_p, n_p unidades
y tope T_p (unidades máximas con la promoción; sin tope, x_max_p):
  - forma "precio" desde 1 unidad y sin tope (porcentaje, precio fijo): el costo de x_p es Q_p x_p; sin variables
    nuevas.
  - forma "precio" con tope:  u_p unidades con la promoción, 0 <= u_p <= min(T_p, x_max_p), u_p <= x_p; costo
    P_p x_p - (P_p - Q_p) u_p (las otras x_p - u_p, a precio de lista).
  - forma "precio" desde n_p >= 2 unidades (llevando n, c/u $Q): además una binaria z_p "llego a n_p", con
    n_p z_p <= u_p <= min(T_p, x_max_p) z_p: el precio de promoción solo vale si se llevan n_p o más.
  - forma "grupo" de n_p (n×m, la 2.ª al q %, n por $P): k_p grupos (entera), n_p k_p <= x_p,
    0 <= k_p <= floor(min(T_p, x_max_p) / n_p); costo P_p x_p - n_p (P_p - Q_p) k_p (cada grupo de n_p cuesta
    n_p Q_p: m P_p en un n×m, (2 - q) P_p en la 2.ª al q %). Es x_p = n_p k_p + r_p con r_p >= 0 a precio de lista;
    la cota r_p <= n_p - 1 no hace falta: con k_p más grande el costo baja, así que el óptimo ya la cumple.
  x_max_p sube a n_p si era menor (se puede llevar el grupo aunque sobre). En la relajación de la etapa 2 (k, u, z
continuas) cada promoción vale su precio por unidad Q_p, así que las subcategorías que se eligen para el modelo entero
ya tienen en cuenta las promociones. El costo que se informa (subtotales) no es el del solver sino el de la caja para
las x_p compradas (costo_caja: la caja arma todos los grupos que puede), que nunca es mayor.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import block_diag, csr_matrix, hstack, vstack

from canasta import config as cfg
from canasta.requerimientos import Meta, Requerimientos

logger = logging.getLogger("canasta.modelo")


@dataclass
class Dieta:
    """Lo que come una persona del hogar."""
    metas: list[Meta]                   # metas usadas en el modelo
    valores: np.ndarray                 # aporte diario de cada meta
    deficit: np.ndarray                 # déficit relativo de cada meta
    consumo: np.ndarray                 # gramos comestibles por día de cada producto de la oferta
    reglas_sin_oferta: list[Meta]       # reglas que la sucursal no puede cumplir: no vende nada que cuente


@dataclass
class Solucion:
    estado: str                         # optima, factible o sin_solucion
    mensaje: str
    oferta: pd.DataFrame                # productos considerados
    compra: np.ndarray                  # unidades compradas por producto
    dietas: list[Dieta]
    costo: float                        # con las promociones que se aplicaron
    segundos: float
    subtotales: np.ndarray | None = None   # lo que cobra la caja por cada producto (con su promoción)

    @property
    def consumo(self) -> np.ndarray:
        """Gramos comestibles por día que come todo el hogar de cada producto."""
        return np.sum([dt.consumo for dt in self.dietas], axis=0) if self.dietas else np.zeros(len(self.oferta))


@dataclass
class Promos:
    """Las promociones que se aplican en una oferta (columnas promo_* de canasta/oferta.py; sin ellas, ninguna)."""
    forma: np.ndarray                   # 0 ninguna, 1 precio por unidad desde `unidades`, 2 grupos de `unidades`
    unidades: np.ndarray
    precio: np.ndarray                  # Q: precio por unidad de compra con la promoción
    tope: np.ndarray                    # unidades máximas con la promoción (inf: sin tope)

    @classmethod
    def de(cls, oferta: pd.DataFrame) -> "Promos":
        n = len(oferta)
        if "promo_forma" not in oferta:
            return cls(np.zeros(n, dtype=int), np.zeros(n, dtype=int), np.full(n, np.nan), np.full(n, np.inf))
        return cls(oferta["promo_forma"].to_numpy(int), oferta["promo_unidades"].to_numpy(int),
                   oferta["promo_precio_compra"].to_numpy(float), oferta["promo_tope"].to_numpy(float))

    @property
    def simple(self) -> np.ndarray:
        """Precio por unidad desde la primera y sin tope: basta con bajar el precio."""
        return (self.forma == 1) & (self.unidades <= 1) & ~np.isfinite(self.tope)

    @property
    def especial(self) -> np.ndarray:
        """Las que necesitan variables nuevas (grupos, tope o mínimo de unidades)."""
        return (self.forma > 0) & ~self.simple


def costo_caja(precio: np.ndarray, p: Promos, x: np.ndarray) -> np.ndarray:
    """Lo que cobra la caja por x unidades de cada producto con su promoción: arma todos los grupos que puede (hasta
    el tope) y cobra a precio de promoción las unidades que entran (si se llega al mínimo); el resto, de lista."""
    x = np.asarray(x, dtype=float)
    costo = precio * x
    n = np.maximum(p.unidades, 1)
    tope = np.where(np.isfinite(p.tope), p.tope, np.inf)
    en_promo = np.where(p.forma == 1, np.where(x >= n, np.minimum(x, tope), 0.0),
                        np.where(p.forma == 2, n * np.minimum(np.floor(x / n), np.floor(tope / n)), 0.0))
    con = p.forma > 0
    costo[con] = (p.precio * en_promo + precio * (x - en_promo))[con]
    return costo


def coeficientes(oferta: pd.DataFrame, m: Meta) -> np.ndarray:
    """Aporte de un gramo comestible de cada producto a la meta."""
    if m.columna is not None:
        return oferta[m.columna].to_numpy(float) / 100
    if m.grupo is not None:
        cuenta = (oferta["grupo_alimentario"] == m.grupo).to_numpy()
    else:
        cuenta = oferta["alimento_id"].isin(m.alimentos).to_numpy()
    if m.medida == "g":
        a = np.ones(len(oferta))
    elif m.medida == "porciones":
        a = 1 / oferta["porcion_g"].clip(lower=1).to_numpy(float)
    else:                               # kcal
        a = oferta["energia_kcal"].to_numpy(float) / 100
    return np.where(cuenta, a, 0.0)


def deficit_relativo(m: Meta, valor: float) -> float:
    """Cuánto falta para el mínimo o sobra sobre el máximo, como fracción de la meta (0 = se cumple)."""
    falta = max(0.0, 1 - valor / m.minimo) if m.minimo else 0.0
    sobra = max(0.0, valor / m.maximo - 1) if m.maximo else 0.0
    return max(falta, sobra)


def tope_por_porciones(porcion_g: np.ndarray, energia: float) -> np.ndarray:
    """Gramos por día que una persona puede comer de un mismo alimento genérico."""
    return cfg.PORCIONES_MAX_POR_ALIMENTO * porcion_g * max(1.0, energia / 2000)


def tope_variedad(req: Requerimientos, porcion_sub: np.ndarray, agua_sub: np.ndarray) -> np.ndarray:
    """Tope por subcategoría: el de las porciones y, para el agua y la soda (agua_sub), la meta de agua del día si se
    le exige a la compra (dos vasos no alcanzan)."""
    tope = tope_por_porciones(porcion_sub, req.energia_kcal)
    agua = next((m for m in req.metas if m.clave == "agua" and m.tipo != "informativa"), None)
    if agua is not None:
        tope = np.where(agua_sub, np.maximum(tope, agua.minimo), tope)
    return tope


@dataclass
class _Bloque:
    """Las filas del modelo de una persona, sobre sus columnas (los productos aptos para ella)."""
    columnas: np.ndarray                # posiciones en la oferta
    metas: list[tuple[Meta, np.ndarray]]
    sin_oferta: list[Meta]
    a_metas: csr_matrix                 # una fila por mínimo o máximo, dividida por la meta
    signo: np.ndarray                   # +1 mínimo, -1 máximo
    pesos: np.ndarray
    energia: Meta
    e_coef: csr_matrix
    a_var: csr_matrix                   # subcategoría x producto
    tope_var: np.ndarray


def _bloque(req: Requerimientos, oferta: pd.DataFrame, apto: np.ndarray, sub_codigos: np.ndarray,
            porcion_sub: np.ndarray, agua_sub: np.ndarray) -> _Bloque:
    columnas = np.flatnonzero(apto)
    o = oferta.iloc[columnas]
    metas, sin_oferta = [], []
    for m in req.metas:
        a = coeficientes(o, m)
        if m.tipo == "regla" and m.minimo is not None and not a.any():
            sin_oferta.append(m)        # nada de lo que vende la sucursal (y puede comer) cuenta para esta regla
            continue
        metas.append((m, a))
    energia = next(m for m, _ in metas if m.tipo == "energia")
    filas, signo, pesos = [], [], []
    for m, a in metas:
        if m.tipo in ("energia", "informativa"):
            continue
        if m.minimo is not None and m.minimo > 0:
            filas.append(a / m.minimo), signo.append(1.0), pesos.append(m.peso)
        if m.maximo is not None:
            filas.append(a / m.maximo), signo.append(-1.0), pesos.append(m.peso)
    n = len(columnas)
    a_metas = csr_matrix(np.vstack(filas)) if filas else csr_matrix((0, n))
    codigos = sub_codigos[columnas]
    a_var = csr_matrix((np.ones(n), (codigos, np.arange(n))), shape=(len(porcion_sub), n))
    return _Bloque(columnas, metas, sin_oferta, a_metas, np.array(signo), np.array(pesos), energia,
                   csr_matrix(coeficientes(o, energia)[None, :]), a_var, tope_variedad(req, porcion_sub, agua_sub))


def _sin_solucion(mensaje: str, oferta: pd.DataFrame, bloques: list[_Bloque], inicio: float) -> Solucion:
    n = len(oferta)
    dietas = [Dieta([m for m, _ in b.metas], np.zeros(len(b.metas)), np.zeros(len(b.metas)), np.zeros(n),
                    b.sin_oferta) for b in bloques]
    return Solucion("sin_solucion", mensaje, oferta, np.zeros(n), dietas, np.nan, time.time() - inicio, np.zeros(n))


def resolver(personas: list[tuple[Requerimientos, np.ndarray]], oferta: pd.DataFrame, dias: int) -> Solucion:
    """personas: (requerimientos, filas de la oferta aptas para esa persona)."""
    inicio = time.time()
    n = len(oferta)
    sub = pd.Categorical(oferta["subcategoria"])
    sub_codigos = sub.codes
    porcion_sub = oferta.groupby(sub, observed=False)["porcion_g"].max().to_numpy(float)
    agua_sub = np.zeros(len(porcion_sub), dtype=bool)
    agua_sub[sub_codigos[oferta["alimento_id"].isin(cfg.ALIMENTOS_AGUA).to_numpy()]] = True
    bloques = [_bloque(req, oferta, apto, sub_codigos, porcion_sub, agua_sub) for req, apto in personas]
    if any(len(b.columnas) == 0 for b in bloques):
        return _sin_solucion("La sucursal no vende alimentos aptos para alguien del hogar", oferta, bloques, inicio)

    # Matrices del hogar: bloques diagonales por persona sobre [c_1 .. c_m] y [d_1 .. d_m].
    nc = sum(len(b.columnas) for b in bloques)
    signo = np.concatenate([b.signo for b in bloques])
    k = len(signo)
    w = np.concatenate([b.pesos for b in bloques])
    a_metas = block_diag([b.a_metas for b in bloques], format="csr")
    a_def = csr_matrix(np.diag(signo)) if k else csr_matrix((0, 0))       # +d en mínimos, -d en máximos
    e_coef = block_diag([b.e_coef for b in bloques], format="csr")
    e_min = np.array([b.energia.minimo for b in bloques])
    e_max = np.array([b.energia.maximo for b in bloques])
    a_var = block_diag([b.a_var for b in bloques], format="csr")
    tope_var = np.concatenate([b.tope_var for b in bloques])
    producto = np.concatenate([b.columnas for b in bloques])            # producto de cada columna c
    # Suma por producto de lo que comen todos: producto x columnas c.
    a_suma = csr_matrix((np.ones(nc), (producto, np.arange(nc))), shape=(n, nc))
    mins, maxs = signo > 0, signo < 0

    # --- Etapa 1: lo mejor que se puede cumplir (programa lineal sobre c y d).
    gc = oferta["gramos_comestibles_compra"].to_numpy(float)
    precio = oferta["precio_compra"].to_numpy(float)
    precio_g = precio / gc
    escala = float(np.median(precio_g) * 1500) or 1.0
    c1 = np.r_[1e-3 * precio_g[producto] / escala, w]
    a_ub = vstack([
        hstack([-a_metas[mins], -a_def[mins]]),                           # mínimos: -(a c + d) <= -1
        hstack([a_metas[maxs], a_def[maxs]]),                             # máximos: a c - d <= 1
        hstack([e_coef, csr_matrix((len(bloques), k))]), hstack([-e_coef, csr_matrix((len(bloques), k))]),
        hstack([a_var, csr_matrix((a_var.shape[0], k))]),
    ]).tocsr()
    b_ub = np.r_[-np.ones(mins.sum()), np.ones(maxs.sum()), e_max, -e_min, tope_var]
    cotas = [(0, None)] * nc + [(0, 1 if s > 0 else None) for s in signo]
    lp = linprog(c1, A_ub=a_ub, b_ub=b_ub, bounds=cotas, method="highs")
    if lp.status != 0:
        return _sin_solucion("La sucursal no tiene alimentos aptos suficientes para llegar a la energía del día",
                             oferta, bloques, inicio)
    d_estrella = lp.x[nc:]

    # --- Etapa 2: la compra más barata (con las promociones que se aplican: ver el docstring del módulo).
    codigos = sub_codigos
    tope_hogar = np.zeros(len(porcion_sub))
    for b in bloques:
        tope_hogar += b.tope_var
    x_max = np.ceil(dias * tope_hogar[codigos] / gc) + 1
    tope_def = np.minimum(d_estrella + cfg.HOLGURA_DEFICIT, np.where(signo > 0, 1.0, np.inf))
    promos = Promos.de(oferta)
    precio_ef = np.where(promos.simple, promos.precio, precio)          # el costo de x_p (sin variables nuevas)
    especial = promos.especial
    x_max = np.where(especial, np.maximum(x_max, promos.unidades), x_max)

    def variables_promo(cols: np.ndarray, entera: bool):
        """Columnas u (unidades o grupos con la promoción) y z (llegó al mínimo) de las promociones especiales de cols:
        (filas de las restricciones sobre [x, u, z], sus cotas, costos de u y z, e integralidad)."""
        pos_x = np.cumsum(cols) - 1                                    # columna x de cada producto de cols
        esp = np.flatnonzero(cols & especial)
        grupo = promos.forma[esp] == 2
        n = np.maximum(promos.unidades[esp], 1).astype(float)
        tamano = np.where(grupo, n, 1.0)
        tope = np.minimum(promos.tope[esp], x_max[esp])
        cota_u = np.where(grupo, np.floor(tope / n), tope)
        costo_u = -tamano * (precio[esp] - promos.precio[esp])
        minimo = ~grupo & (n >= 2)                                     # llevando n, c/u $Q: binaria z
        n_u, n_z, n_x = len(esp), int(minimo.sum()), int(cols.sum())
        con_z = np.flatnonzero(minimo)
        # tamano * u - x <= 0
        filas_u = hstack([csr_matrix((-np.ones(n_u), (np.arange(n_u), pos_x[esp])), shape=(n_u, n_x)),
                          csr_matrix(np.diag(tamano)) if n_u else csr_matrix((0, 0)), csr_matrix((n_u, n_z))])
        # n z - u <= 0  y  u - M z <= 0
        a_z = csr_matrix((-np.ones(n_z), (np.arange(n_z), con_z)), shape=(n_z, n_u))
        filas_min = hstack([csr_matrix((n_z, n_x)), a_z, csr_matrix(np.diag(n[con_z])) if n_z else csr_matrix((0, 0))])
        filas_max = hstack([csr_matrix((n_z, n_x)), -a_z,
                            csr_matrix(np.diag(-tope[con_z])) if n_z else csr_matrix((0, 0))])
        filas = vstack([filas_u, filas_min, filas_max]).tocsr()
        ub = np.r_[cota_u, np.ones(n_z)]
        costos = np.r_[costo_u, np.zeros(n_z)]
        enteras = np.r_[np.where(grupo, 1.0, 0.0) if entera else np.zeros(n_u), np.full(n_z, 1.0 if entera else 0.0)]
        return filas, ub, costos, enteras, n_u + n_z

    def comprar(cols: np.ndarray, entera: bool):
        # cols: productos de la oferta que entran; las columnas c que entran son las de esos productos.
        cc = cols[producto]
        n_c, n_x = int(cc.sum()), int(cols.sum())
        filas_p, ub_p, costos_p, enteras_p, n_p = variables_promo(cols, entera)
        am, ae, av = a_metas[:, cc], e_coef[:, cc], a_var[:, cc]
        enlace = hstack([dias * a_suma[cols][:, cc], -csr_matrix(np.diag(gc[cols])), csr_matrix((n_x, k + n_p))])
        restricciones = [
            LinearConstraint(hstack([am[mins], csr_matrix((mins.sum(), n_x)), a_def[mins], csr_matrix((mins.sum(), n_p))]),
                             lb=1.0, ub=np.inf),
            LinearConstraint(hstack([am[maxs], csr_matrix((maxs.sum(), n_x)), a_def[maxs], csr_matrix((maxs.sum(), n_p))]),
                             lb=-np.inf, ub=1.0),
            LinearConstraint(hstack([ae, csr_matrix((len(bloques), n_x + k + n_p))]), lb=e_min, ub=e_max),
            LinearConstraint(hstack([av, csr_matrix((av.shape[0], n_x + k + n_p))]), lb=-np.inf, ub=tope_var),
            LinearConstraint(enlace, lb=-np.inf, ub=0.0),
        ]
        if n_p:                                         # sobre [x, u, z]: se completan las columnas c y d con ceros
            x_y_promo = filas_p[:, :n_x], filas_p[:, n_x:]
            restricciones.append(LinearConstraint(
                hstack([csr_matrix((filas_p.shape[0], n_c)), x_y_promo[0], csr_matrix((filas_p.shape[0], k)),
                        x_y_promo[1]]), lb=-np.inf, ub=0.0))
        cotas2 = Bounds(np.zeros(n_c + n_x + k + n_p), np.r_[np.full(n_c, np.inf), x_max[cols], tope_def, ub_p])
        c2 = np.r_[np.zeros(n_c), precio_ef[cols], 1e-6 * precio.mean() * w, costos_p]
        enteras = np.r_[np.zeros(n_c), np.full(n_x, 1.0 if entera else 0.0), np.zeros(k), enteras_p]
        res = milp(c2, constraints=restricciones, bounds=cotas2, integrality=enteras,
                   options={"time_limit": cfg.TIEMPO_MAXIMO_S, "mip_rel_gap": cfg.GAP_RELATIVO, "disp": False})
        return res, cc, n_c

    todos = np.ones(n, dtype=bool)
    relajada, cc, n_c = comprar(todos, entera=False)
    cols = todos
    if relajada.x is not None:
        usadas = np.unique(codigos[producto[cc][relajada.x[:n_c] > 1e-6]])
        cols = np.isin(codigos, usadas)
    res, cc, n_c = comprar(cols, entera=True)
    if res.x is None and not cols.all():
        cols = todos
        res, cc, n_c = comprar(cols, entera=True)
    if res.x is None:
        return _sin_solucion(f"El modelo entero no encontró solución ({res.message})", oferta, bloques, inicio)

    c_todas = np.zeros(nc)
    c_todas[cc] = np.clip(res.x[:n_c], 0, None)
    c_todas[c_todas < 0.05] = 0.0                  # restos numéricos del solver
    compra = np.zeros(n)
    compra[cols] = np.round(res.x[n_c:n_c + int(cols.sum())])
    dietas, desde = [], 0
    for b in bloques:
        consumo = np.zeros(n)
        consumo[b.columnas] = c_todas[desde:desde + len(b.columnas)]
        desde += len(b.columnas)
        propio = consumo[b.columnas]
        valores = np.array([a @ propio for _, a in b.metas])
        deficit = np.array([deficit_relativo(m, v) for (m, _), v in zip(b.metas, valores)])
        dietas.append(Dieta([m for m, _ in b.metas], valores, deficit, consumo, b.sin_oferta))
    estado = "optima" if res.status == 0 else "factible"
    # Lo que cobra la caja: de lista, menos lo que descuentan las promociones (sin promociones, exactamente como antes).
    subtotales = costo_caja(precio, promos, compra)
    descuento = float(np.sum((precio * compra - subtotales)[promos.forma > 0]))
    return Solucion(estado, res.message, oferta, compra, dietas, float(precio @ compra) - descuento,
                    time.time() - inicio, subtotales)
