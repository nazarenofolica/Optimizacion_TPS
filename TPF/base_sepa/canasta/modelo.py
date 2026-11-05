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
  - variedad: nadie come más de 2 porciones por día de un mismo alimento genérico (escaladas por su energía).

Las metas informativas (vitamina D; B12 de un vegano) no entran en el modelo: solo se informa cuánto aportan.

Etapa 1 (programa lineal, sin precios): minimizar sum peso_k * d_ik. Da lo mejor que se puede cumplir con lo que
vende la sucursal; si todo se cumple, d* = 0.
Etapa 2 (entera): minimizar el costo de lo comprado sin que ningún déficit pase de d*. Primero la relajación lineal
sobre toda la oferta; después el modelo entero solo con las subcategorías que usó (con todas sus presentaciones), que
es chico y se resuelve rápido. Lo que se compra y no se come en el período se informa como sobrante.
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
    costo: float
    segundos: float

    @property
    def consumo(self) -> np.ndarray:
        """Gramos comestibles por día que come todo el hogar de cada producto."""
        return np.sum([dt.consumo for dt in self.dietas], axis=0) if self.dietas else np.zeros(len(self.oferta))


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
            porcion_sub: np.ndarray) -> _Bloque:
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
                   csr_matrix(coeficientes(o, energia)[None, :]), a_var,
                   tope_por_porciones(porcion_sub, req.energia_kcal))


def _sin_solucion(mensaje: str, oferta: pd.DataFrame, bloques: list[_Bloque], inicio: float) -> Solucion:
    n = len(oferta)
    dietas = [Dieta([m for m, _ in b.metas], np.zeros(len(b.metas)), np.zeros(len(b.metas)), np.zeros(n),
                    b.sin_oferta) for b in bloques]
    return Solucion("sin_solucion", mensaje, oferta, np.zeros(n), dietas, np.nan, time.time() - inicio)


def resolver(personas: list[tuple[Requerimientos, np.ndarray]], oferta: pd.DataFrame, dias: int) -> Solucion:
    """personas: (requerimientos, filas de la oferta aptas para esa persona)."""
    inicio = time.time()
    n = len(oferta)
    sub = pd.Categorical(oferta["subcategoria"])
    sub_codigos = sub.codes
    porcion_sub = oferta.groupby(sub, observed=False)["porcion_g"].max().to_numpy(float)
    bloques = [_bloque(req, oferta, apto, sub_codigos, porcion_sub) for req, apto in personas]
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

    # --- Etapa 2: la compra más barata.
    codigos = sub_codigos
    tope_hogar = np.zeros(len(porcion_sub))
    for b in bloques:
        tope_hogar += b.tope_var
    x_max = np.ceil(dias * tope_hogar[codigos] / gc) + 1
    tope_def = np.minimum(d_estrella + cfg.HOLGURA_DEFICIT, np.where(signo > 0, 1.0, np.inf))

    def comprar(cols: np.ndarray, entera: bool):
        # cols: productos de la oferta que entran; las columnas c que entran son las de esos productos.
        cc = cols[producto]
        n_c, n_x = int(cc.sum()), int(cols.sum())
        am, ae, av = a_metas[:, cc], e_coef[:, cc], a_var[:, cc]
        enlace = hstack([dias * a_suma[cols][:, cc], -csr_matrix(np.diag(gc[cols])), csr_matrix((n_x, k))])
        restricciones = [
            LinearConstraint(hstack([am[mins], csr_matrix((mins.sum(), n_x)), a_def[mins]]), lb=1.0, ub=np.inf),
            LinearConstraint(hstack([am[maxs], csr_matrix((maxs.sum(), n_x)), a_def[maxs]]), lb=-np.inf, ub=1.0),
            LinearConstraint(hstack([ae, csr_matrix((len(bloques), n_x + k))]), lb=e_min, ub=e_max),
            LinearConstraint(hstack([av, csr_matrix((av.shape[0], n_x + k))]), lb=-np.inf, ub=tope_var),
            LinearConstraint(enlace, lb=-np.inf, ub=0.0),
        ]
        cotas2 = Bounds(np.zeros(n_c + n_x + k), np.r_[np.full(n_c, np.inf), x_max[cols], tope_def])
        c2 = np.r_[np.zeros(n_c), precio[cols], 1e-6 * precio.mean() * w]
        enteras = np.r_[np.zeros(n_c), np.full(n_x, 1.0 if entera else 0.0), np.zeros(k)]
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
    return Solucion(estado, res.message, oferta, compra, dietas, float(precio @ compra), time.time() - inicio)
