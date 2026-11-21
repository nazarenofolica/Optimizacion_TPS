"""
Promociones de SEPA con sus condiciones: de la leyenda que publica cada cadena a una promoción estructurada.

SEPA trae, por producto y sucursal, hasta dos promociones (productos_precio_unitario_promo1/2 y
productos_leyenda_promo1/2): el precio unitario con la promoción (el promedio por unidad si se cumple la
condición: en un 2×1, la mitad del precio de lista) y una leyenda de texto libre, distinta en cada cadena. Lo que se
vio en el ZIP del 20/11/2026 (1,76 millones de filas con promoción, 3.278 leyendas distintas):

  DIA            "25% de descuento. Precio Promocional Exclusivo DIA en Sucursales Indicadas ..." (promo 1) y
                 "35% de descuento. 2DO AL 70% YOG POTE - Vigencia: Desde el 18/11/2026 hasta el 23/11/2026"
                 (promo 2: el porcentaje del principio es el promedio y la promoción de verdad viene después,
                 recortada a 20 letras: 3X2 TANG, 2X$1400 CARAM HALLS, LLEVANDO 3 ACTIMEL, $3945 DESO PEARL)
  La Anónima     "25% de descuento con cualquier medio de pago - Vigencia: Desde el ... Hasta el ..." y
                 "Llevando 2 unidades - Vigencia: ..." (el precio dice si es 2×1 o la 2.ª al 50 o al 70 %)
  Coop. Obrera   "Descuentazo 20% - Vigencia desde el ... al ... hasta agotar Stock de 12 unidades.",
                 "Llevando 2 paga $3350.00 c/u - ..." y, la mayoría, solo la vigencia
  Carrefour      "Promo A valida desde el 18/11/2026 hasta 24/11/2026" (no dice qué promoción es)
  Coto           "DEL 16/11/2026 AL 22/11/2026" (tampoco)
  Toledo         "Producto en Oferta"

clasificar() lee una leyenda (se hace una vez por leyenda distinta) y devuelve:

  tipo            porcentaje (25 % de descuento), nxm (2×1, 3×2: n por el precio de m), segunda_unidad (la 2.ª al
                  q % de descuento), precio_fijo ($3.945), llevando_x (llevando n: c/u $P, n por $P o, sin precio,
                  el que publica SEPA) o desconocida
  n, m            unidades del grupo y unidades que se pagan (nxm); n en segunda_unidad (2) y llevando_x
  porcentaje      descuento en %: porcentaje y segunda_unidad (sobre la segunda unidad)
  precio          $ de la leyenda: precio_fijo y "c/u $P" (por unidad), "n x $P" (por el grupo)
  cada_unidad     llevando_x: el precio vale para cada unidad desde la n-ésima (c/u) y no por grupo de n
  tope            unidades máximas con la promoción ("hasta agotar stock de 12 unidades", "máximo 6 unidades")
  condicion_pago  tarjeta, banco, billetera, fidelidad o efectivo si la leyenda exige un medio de pago o un
                  programa de la cadena ("con cualquier medio de pago" no es una condición)
  condicion       otra condición que la canasta no puede cumplir por la persona: un horario, algunos días, solo
                  jubilados, solo la compra online
  vigencia_desde, vigencia_hasta   si la leyenda las trae
  aplicable       se puede aplicar a la compra: tipo entendido, sin condición de pago ni de otro tipo
  motivo          por qué no se aplica (resumido, sin nombrar bancos), vacío si se aplica
  resumen         la promoción en pocas letras para el ticket: "2×1", "2.ª al 70 %", "25 % de descuento"

Las promociones bancarias y de medios de pago quedan fuera de alcance (decisión del proyecto): se guardan y se
muestran como no aplicadas, con el motivo. Una leyenda que no dice qué promoción es (solo la vigencia, "Promo A") es
"desconocida" y no se aplica: no se promete un descuento que no se sabe si se cumple.

armar() junta las promociones leídas del ZIP con fact_precio y calcula, por fila, la forma en que entra al modelo de
la canasta (canasta/modelo.py):

  forma "precio"  cada unidad sale precio_unitario desde `unidades` unidades (porcentaje, precio_fijo, llevando c/u)
  forma "grupo"   cada grupo de `unidades` unidades sale unidades × precio_unitario (nxm, segunda_unidad, llevando
                  n por $P o sin precio: el modelo prudente, que nunca promete más de lo que da la caja)
  precio_unitario el que publica SEPA (el promedio con la promoción) si es válido; si no, el que sale de la leyenda y
                  el precio de lista. Si los dos están y difieren en más de PROMO_TOLERANCIA_LEYENDA, no se aplica.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from functools import lru_cache

import numpy as np
import pandas as pd

from sepa import config as cfg
from sepa.texto import sin_tildes

logger = logging.getLogger("sepa.promociones")

TIPOS = ["porcentaje", "nxm", "segunda_unidad", "precio_fijo", "llevando_x", "desconocida"]
CONDICIONES_PAGO = {
    "tarjeta": "requiere una tarjeta de crédito o débito",
    "banco": "requiere un banco",
    "billetera": "requiere una billetera virtual",
    "fidelidad": "requiere el programa o la tarjeta de la cadena",
    "efectivo": "requiere pagar en efectivo",
}
COLUMNAS = ["id_producto", "id_tienda", "orden", "leyenda", "precio_lista", "precio_promocion", "tipo", "n", "m",
            "porcentaje", "precio_leyenda", "cada_unidad", "tope", "condicion_pago", "condicion", "vigencia_desde",
            "vigencia_hasta", "aplicable", "motivo", "resumen", "forma", "unidades", "precio_unitario"]

_ESPACIOS = re.compile(r"\s+")
_NUM = r"(\d+(?:[.,]\d+)*)"
# Vigencia: "Desde el 18/11/2026 Hasta el 29/11/2026", "DEL 16/11/2026 AL 22/11/2026", "valida desde el ... hasta
# ...", y "Vigente hasta el 2026-11-24" (Cooperativa Obrera).
_RANGO = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})\D+?(\d{1,2})/(\d{1,2})/(\d{4})")
_HASTA_ISO = re.compile(r"HASTA (?:EL )?(\d{4})-(\d{2})-(\d{2})")
_TOPE = [re.compile(p) for p in (r"STOCK DE (\d+) UNIDADES", r"MAXIMO (?:DE )?(\d+) (?:UNIDADES|U\b|UN\b)",
                                 r"HASTA (\d+) (?:UNIDADES|U\b|UN\b)", r"LIMITE (?:DE )?(\d+) (?:UNIDADES|U\b|UN\b)",
                                 r"TOPE (?:DE )?(\d+) (?:UNIDADES|U\b|UN\b)")]
_CUALQUIER_MEDIO = re.compile(r"CUALQUIER MEDIO DE PAGO")
_PAGO = [
    ("fidelidad", re.compile(r"\b(CLUB|COMUNIDAD|SOCIOS?|MI ?CARREFOUR|MI CRF|PUNTOS|FIDELIDAD|APP|APLICACION|"
                             r"TARJETA (?:DE LA CADENA|CENCOSUD|LA ANONIMA|COTO|DIA|CARREFOUR|JUMBO|DISCO|VEA)|CMR)\b")),
    ("billetera", re.compile(r"\b(MERCADO ?PAGO|MODO|CUENTA DNI|BILLETERA|QR|PERSONAL PAY|NARANJA X|UALA|PREX)\b")),
    ("banco", re.compile(r"\b(BANCO|BNA|GALICIA|SANTANDER|BBVA|FRANCES|MACRO|ICBC|HSBC|PATAGONIA|SUPERVIELLE|"
                         r"CREDICOOP|COMAFI|HIPOTECARIO|BRUBANK|REINTEGRO)\b")),
    ("tarjeta", re.compile(r"\b(TARJETAS?|VISA|MASTER(?:CARD)?|AMEX|AMERICAN EXPRESS|CABAL|NARANJA|CREDITO|DEBITO|"
                           r"CUOTAS?)\b")),
    ("efectivo", re.compile(r"\bEFECTIVO\b")),
]
_DIAS = re.compile(r"\b(LUNES|MARTES|MIERCOLES|JUEVES|VIERNES|SABADOS?|DOMINGOS?|FINES? DE SEMANA)\b")
_OTRAS = [
    (re.compile(r"\b(?:X|POR LA|A LA|DE|EN LA) (?:TARDE|NOCHE|MANANA)\b|\bHORARIO|\bHAPPY HOUR\b|\b\d{1,2} ?HS\b"),
     "solo en un horario"),
    (re.compile(r"\bJUBILAD"), "solo para jubilados"),
    (re.compile(r"\b(ONLINE|WEB|ENVIOS?|E-?COMMERCE)\b"), "solo en la compra online"),
]
# Tipos, del más específico al más general. Las de DIA empiezan con el descuento promedio ("35% de descuento.") y
# después dicen la promoción: por eso el porcentaje es el último que se busca.
_SEGUNDA = re.compile(r"\b(?:2 ?(?:DA|DO|A|O)|SEGUND[AO])\b(?: UNIDAD| UN\b)? ?(?:AL|CON|A)? ?(\d{1,3}) ?%")
_N_POR_PRECIO = re.compile(r"\b(\d{1,2}) ?X ?\$ ?" + _NUM)
_NXM = re.compile(r"\b(\d{1,2}) ?X ?(\d{1,2})\b(?! ?(?:[.,]\d|KG|G\b|GR|ML|L\b|LT|CC|UN|U\b|%))")
_LLEVANDO = re.compile(r"\bLLEVANDO (\d{1,2})\b")
_PAGA_N = re.compile(r"\bLLEVANDO (\d{1,2}) PAGA(?:S|NDO)? (\d{1,2})\b(?! ?[.,]\d)(?! ?\$)")
_CADA_PRECIO = re.compile(r"(?:\$ ?" + _NUM + r" ?C/U|C/U \$? ?" + _NUM + r")")
_PRECIO_SOLO = re.compile(r"(?:^|\. |PRECIO (?:PROMO(?:CIONAL)? |ESPECIAL |OFERTA )?)\$ ?" + _NUM)
_PORCENTAJE = re.compile(r"(\d{1,2}(?:[.,]\d+)?) ?%")


def normalizar(leyenda: object) -> str:
    """Mayúsculas, sin tildes, espacios simples (se conservan los signos: $, %, / y la coma decimal)."""
    if not isinstance(leyenda, str):
        return ""
    t = sin_tildes(leyenda.replace("º", "O").replace("°", "O").replace("ª", "A")).upper()
    return _ESPACIOS.sub(" ", t).strip()


def _numero(texto: str) -> float:
    """'3350.00' -> 3350; '3.350,00' -> 3350; '1400' -> 1400; '4,5' -> 4,5."""
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    elif texto.count(".") == 1 and len(texto.split(".")[1]) == 3:
        texto = texto.replace(".", "")                       # punto de miles: $3.350
    return float(texto)


def _pesos(x: float) -> str:
    """$ con punto de miles y, si tiene centavos, coma decimal (como el resto de la página)."""
    d = 0 if abs(x - round(x)) < 0.005 else 2
    return "$" + f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(x: float) -> str:
    return (f"{x:g}".replace(".", ",")) + " %"


def _vigencia(t: str) -> tuple[date | None, date | None]:
    desde = hasta = None
    m = _RANGO.search(t)
    if m:
        try:
            desde = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            hasta = date(int(m.group(6)), int(m.group(5)), int(m.group(4)))
        except ValueError:
            desde = hasta = None
    if hasta is None:
        m = _HASTA_ISO.search(t)
        if m:
            try:
                hasta = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                pass
    return desde, hasta


def _tipo(t: str) -> dict:
    """Tipo y parámetros de la promoción (sin condiciones)."""
    vacio = {"tipo": "desconocida", "n": None, "m": None, "porcentaje": None, "precio": None, "cada_unidad": None}
    m = _SEGUNDA.search(t)
    if m and 0 < int(m.group(1)) <= 100:
        q = float(m.group(1))
        return vacio | {"tipo": "segunda_unidad", "n": 2, "porcentaje": q}
    m = _N_POR_PRECIO.search(t)
    if m and int(m.group(1)) >= 2:
        return vacio | {"tipo": "llevando_x", "n": int(m.group(1)), "precio": _numero(m.group(2)), "cada_unidad": False}
    m = _PAGA_N.search(t) or _NXM.search(t)
    if m and int(m.group(1)) > int(m.group(2)) >= 1:
        return vacio | {"tipo": "nxm", "n": int(m.group(1)), "m": int(m.group(2))}
    m = _LLEVANDO.search(t)
    if m and int(m.group(1)) >= 2:
        n = int(m.group(1))
        resto = t[m.end():]
        c = _CADA_PRECIO.search(resto)
        if c:
            return vacio | {"tipo": "llevando_x", "n": n, "precio": _numero(c.group(1) or c.group(2)),
                            "cada_unidad": True}
        p = _PORCENTAJE.search(resto)
        if p:
            return vacio | {"tipo": "llevando_x", "n": n, "porcentaje": _numero(p.group(1)), "cada_unidad": True}
        return vacio | {"tipo": "llevando_x", "n": n, "cada_unidad": False}
    sin_promedio = re.sub(r"^\d{1,2} ?% DE DESCUENTO\. ", "", t)     # DIA: el promedio, antes de la promoción
    m = _PRECIO_SOLO.search(sin_promedio)
    if m:
        return vacio | {"tipo": "precio_fijo", "precio": _numero(m.group(1))}
    m = _PORCENTAJE.search(sin_promedio) or _PORCENTAJE.search(t)
    if m and 0 < _numero(m.group(1)) < 100:
        return vacio | {"tipo": "porcentaje", "porcentaje": _numero(m.group(1))}
    return vacio


def _resumen(p: dict) -> str:
    tipo = p["tipo"]
    if tipo == "porcentaje":
        return f"{_pct(p['porcentaje'])} de descuento"
    if tipo == "nxm":
        return f"{p['n']}×{p['m']}"
    if tipo == "segunda_unidad":
        return f"2.ª al {_pct(p['porcentaje'])}"
    if tipo == "precio_fijo":
        return f"Precio promo {_pesos(p['precio'])}"
    if tipo == "llevando_x":
        if p["precio"] is not None and p["cada_unidad"]:
            return f"Llevando {p['n']}: {_pesos(p['precio'])} c/u"
        if p["precio"] is not None:
            return f"{p['n']} × {_pesos(p['precio'])}"
        if p["porcentaje"] is not None:
            return f"Llevando {p['n']}: {_pct(p['porcentaje'])} de descuento"
        return f"Llevando {p['n']}"
    return "Promoción"


def clasificar(leyenda: str) -> dict:
    """La promoción que describe una leyenda de SEPA (ver el docstring del módulo)."""
    return dict(_clasificar(leyenda))


@lru_cache(maxsize=None)
def _clasificar(leyenda: str) -> dict:
    t = normalizar(leyenda)
    p = _tipo(t)
    desde, hasta = _vigencia(t)
    tope = None
    for r in _TOPE:
        m = r.search(t)
        if m and int(m.group(1)) > 0:
            tope = int(m.group(1))
            break
    pago = None
    if not _CUALQUIER_MEDIO.search(t):
        pago = next((c for c, r in _PAGO if r.search(t)), None)
    otra = None
    dias = _DIAS.findall(t)
    if dias:
        otra = "solo algunos días (" + ", ".join(dict.fromkeys(d.lower().replace("miercoles", "miércoles")
                                                                .replace("sabado", "sábado") for d in dias)) + ")"
    else:
        otra = next((texto for r, texto in _OTRAS if r.search(t)), None)
    if pago:
        motivo = CONDICIONES_PAGO[pago]
    elif otra:
        motivo = otra
    elif not t:
        motivo = "sin leyenda: no se sabe qué promoción es"
    elif p["tipo"] == "desconocida":
        motivo = "la leyenda no dice qué promoción es ni sus condiciones"
    else:
        motivo = ""
    return p | {"tope": tope, "condicion_pago": pago, "condicion": otra, "vigencia_desde": desde,
                "vigencia_hasta": hasta, "aplicable": motivo == "", "motivo": motivo, "resumen": _resumen(p)}


def precios_unitarios(t: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(precio por unidad con la promoción, motivo si no se puede aplicar) de cada fila de t (tipo, n, m, porcentaje,
    precio, cada_unidad, precio_lista, precio_promocion). Se usa el publicado si es válido (menor al de lista y no
    menor a PROMO_FRACCION_MINIMA de él); si no, el que sale de la leyenda y el precio de lista."""
    lista = t["precio_lista"].to_numpy(float)
    publicado = t["precio_promocion"].to_numpy(float)
    tipo = t["tipo"].to_numpy(object)
    n, m = t["n"].to_numpy(float), t["m"].to_numpy(float)
    pct = t["porcentaje"].to_numpy(float) / 100
    precio = t["precio"].to_numpy(float)
    cada = t["cada_unidad"].eq(True).to_numpy()
    llevando = tipo == "llevando_x"
    ley = np.select(
        [tipo == "porcentaje", tipo == "precio_fijo", tipo == "nxm", tipo == "segunda_unidad",
         llevando & np.isfinite(precio) & cada, llevando & np.isfinite(precio), llevando & np.isfinite(pct)],
        [lista * (1 - pct), precio, lista * m / np.where(n > 0, n, np.nan), lista * (2 - pct) / 2, precio,
         precio / np.where(n > 0, n, np.nan), lista * (1 - pct)], np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        valido = lambda x: np.isfinite(x) & (x >= cfg.PROMO_FRACCION_MINIMA * lista) & (x < lista)  # noqa: E731
        ok_pub, ok_ley = valido(publicado), valido(ley)
        distinto = ok_pub & np.isfinite(ley) & (np.abs(publicado / ley - 1) > cfg.PROMO_TOLERANCIA_LEYENDA)
    pu = np.where(ok_pub, publicado, np.where(ok_ley, ley, np.nan))
    pu = np.where(distinto, np.nan, np.round(pu, 2))
    motivo = np.select([distinto, np.isfinite(pu), ~np.isfinite(publicado) & ~np.isfinite(ley)],
                       ["el precio publicado no coincide con lo que dice la leyenda", "",
                        "la leyenda no dice el precio con la promoción"],
                       "el precio con la promoción no es menor al de lista")
    return pu, motivo


def vigente(p: dict, dia: date) -> bool:
    """La leyenda incluye el día (sin fechas legibles, se acepta)."""
    desde, hasta = p["vigencia_desde"], p["vigencia_hasta"]
    return not ((desde is not None and dia < desde) or (hasta is not None and dia > hasta))


def armar(datos, fact: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    La tabla promocion: una fila por promoción vigente de un precio de fact_precio (producto y tienda; hasta dos por
    precio, orden 1 y 2), con la leyenda, su clasificación y cómo entra al modelo. datos: DatosSEPA (promociones,
    productos, tiendas, fecha). Devuelve (tabla, estadísticas).
    """
    pr = datos.promociones
    stats = {"leidas": len(pr)}
    if pr.empty:
        return pd.DataFrame(columns=COLUMNAS), stats | {"filas": 0}
    clave = dict(zip(datos.productos["producto"], datos.productos["clave_producto"]))
    tienda = dict(zip(datos.tiendas["tienda"], datos.tiendas["id_tienda"]))
    obs = pd.DataFrame({"id_producto": pr["producto"].map(clave), "id_tienda": pr["tienda"].map(tienda),
                        "orden": pr["orden"].to_numpy(), "leyenda": pr["leyenda"].astype(str).to_numpy(),
                        "precio_promocion": pr["precio_promocion"].to_numpy(float)})
    # El precio de lista de cada una, de fact_precio (con los códigos de sus categorías: 8 millones de claves como
    # texto no entran en memoria). Las de precios descartados o productos que no son comestibles quedan afuera.
    cp, ct = (fact[c].astype("category") for c in ("id_producto", "id_tienda"))
    nt = len(ct.cat.categories) + 1
    en_fact = cp.cat.codes.to_numpy(np.int64) * nt + ct.cat.codes.to_numpy(np.int64)
    orden = np.argsort(en_fact, kind="stable")
    p_cod = pd.Categorical(obs["id_producto"], categories=cp.cat.categories).codes.astype(np.int64)
    t_cod = pd.Categorical(obs["id_tienda"], categories=ct.cat.categories).codes.astype(np.int64)
    buscada = p_cod * nt + t_cod
    pos = np.clip(np.searchsorted(en_fact, buscada, sorter=orden), 0, len(orden) - 1)
    fila = orden[pos]
    esta = (p_cod >= 0) & (t_cod >= 0) & (en_fact[fila] == buscada)
    obs = obs[esta].assign(precio_lista=fact["precio"].to_numpy(float)[fila[esta]]).reset_index(drop=True)
    stats["de_precios_publicados"] = len(obs)

    # Se clasifica cada leyenda distinta una vez (unas 3.000 en 1,7 millones de filas).
    leyendas = obs["leyenda"].unique()
    clases = pd.DataFrame([clasificar(x) for x in leyendas], index=leyendas)
    clases["vigente"] = [vigente(c, datos.fecha) for c in clases.to_dict("records")]
    obs = obs.join(clases, on="leyenda")
    vig = obs.pop("vigente").to_numpy(bool)
    stats["fuera_de_vigencia"] = int((~vig).sum())
    obs = obs[vig].reset_index(drop=True)

    formas = np.select([obs["tipo"].isin(["porcentaje", "precio_fijo"]).to_numpy(),
                        obs["tipo"].isin(["nxm", "segunda_unidad"]).to_numpy(),
                        (obs["tipo"].eq("llevando_x") & obs["cada_unidad"].eq(True)).to_numpy(),
                        obs["tipo"].eq("llevando_x").to_numpy()], ["precio", "grupo", "precio", "grupo"], "")
    unidades = np.where(obs["tipo"].isin(["porcentaje", "precio_fijo"]), 1, obs["n"].fillna(0)).astype(int)
    pu, motivo_precio = precios_unitarios(obs)
    entendida = obs["aplicable"].to_numpy(bool)
    obs["precio_unitario"] = np.where(entendida, pu, np.nan)
    obs["motivo"] = np.where(entendida, motivo_precio, obs["motivo"].to_numpy(object))
    # Un tope menor que las unidades que pide la promoción la hace imposible.
    imposible = obs["tope"].notna() & (obs["tope"] < unidades) & obs["motivo"].eq("")
    obs.loc[imposible, "motivo"] = "el tope de unidades es menor que lo que pide la promoción"
    obs["aplicable"] = obs["motivo"].eq("")
    obs["forma"] = formas
    obs["unidades"] = unidades
    obs["precio_lista"] = obs["precio_lista"].round(2)
    obs["precio_promocion"] = obs["precio_promocion"].round(2)
    obs = obs.rename(columns={"precio": "precio_leyenda"})
    for c in ("n", "m", "tope"):
        obs[c] = obs[c].astype("Int64")
    obs["cada_unidad"] = obs["cada_unidad"].astype("boolean")
    for c in ("vigencia_desde", "vigencia_hasta"):
        obs[c] = pd.to_datetime(obs[c])
    obs = obs[COLUMNAS].sort_values(["id_producto", "id_tienda", "orden"], ignore_index=True)
    for c in ("id_producto", "id_tienda", "leyenda", "tipo", "condicion_pago", "condicion", "motivo", "resumen",
              "forma"):
        obs[c] = obs[c].astype("category")
    stats["filas"] = len(obs)
    stats["por_tipo"] = obs["tipo"].value_counts().to_dict()
    stats["aplicables"] = int(obs["aplicable"].sum())
    stats["por_motivo"] = obs.loc[~obs["aplicable"], "motivo"].astype(str).value_counts().to_dict()
    logger.info("Promociones: %d vigentes de %d leídas, %d aplicables (%.1f %%)", len(obs), len(pr),
                stats["aplicables"], 100 * stats["aplicables"] / max(len(obs), 1))
    return obs, stats


def cobertura(tabla: pd.DataFrame) -> pd.DataFrame:
    """Cuántas leyendas distintas y cuántas filas quedan aplicables, no aplicables por el medio de pago, por otra
    condición o por el precio, o desconocidas (para el LEEME y los tests)."""
    aplicable = tabla["aplicable"].to_numpy(bool)
    grupo = np.select([aplicable, tabla["condicion_pago"].notna().to_numpy(), tabla["tipo"].eq("desconocida").to_numpy(),
                       tabla["condicion"].notna().to_numpy()],
                      ["aplicable", "no aplicable: medio de pago", "desconocida", "no aplicable: otra condición"],
                      "no aplicable: precio")
    g = pd.DataFrame({"grupo": grupo, "leyenda": tabla["leyenda"].astype(str).to_numpy()})
    salida = g.groupby("grupo").agg(filas=("grupo", "size"), leyendas=("leyenda", "nunique"))
    salida["pct_filas"] = (100 * salida["filas"] / max(len(g), 1)).round(1)
    salida["pct_leyendas"] = (100 * salida["leyendas"] / max(g["leyenda"].nunique(), 1)).round(1)
    return salida.sort_values("filas", ascending=False)
