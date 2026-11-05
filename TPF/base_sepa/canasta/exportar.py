"""
Exporta la canasta a un solo archivo HTML que funciona sin servidor: la página, los estilos, el motor de cálculo
(canasta/web/motor.js, que resuelve el modelo en el navegador con HiGHS) y los datos del día comprimidos adentro.

Los datos son los mismos que usa el motor de Python (canasta/oferta.py): los productos de la canasta con sus
nutrientes y sus aptitudes ya evaluadas (sin TACC, vegano, cada alérgeno...), las sucursales que se pueden evaluar y
todos sus precios, más los parámetros de canasta/config.py y las tablas de referencia/. Así la lógica de las
restricciones y todos los números discutibles viven en un solo lugar.

    python -m canasta              # exporta salida/canasta.html y lo abre
    python -m canasta --exportar   # solo exporta

Para embeberlo en Streamlit:

    import streamlit.components.v1 as components
    components.html(Path("salida/canasta.html").read_text(encoding="utf-8"), height=2600, scrolling=True)
"""

from __future__ import annotations

import base64
import gzip
import json
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd

from canasta import config as cfg
from canasta import oferta
from canasta import requerimientos as rq
from canasta.resultado import EXCLUIDOS_SIEMPRE

logger = logging.getLogger("canasta.exportar")

DIR_WEB = Path(__file__).resolve().parent / "web"
RUTA_EXPORTACION = cfg.DIR_SALIDA / "canasta.html"
NUMERICAS = ["contenido", "unidades", "gramos_envase", "parte_comestible", "porcion_g", "precio_referencia_100g"]
TEXTOS = ["nombre", "marca"]
CATEGORICAS = ["subcategoria", "grupo_alimentario", "alimento_id", "unidad_contenido", "fuente_nutrientes"]
COLUMNAS_TIENDA = ["bandera", "comercio", "cuit", "sucursal_nombre", "direccion", "localidad", "barrio", "provincia",
                   "tipo_sucursal"]
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


def _texto(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else str(v)


def parametros() -> dict:
    """Todo lo de canasta/config.py que usa el motor del navegador."""
    nombres = [k for k in dir(cfg) if k.isupper() and not k.startswith(("RUTA_", "DIR_", "URL_"))]
    salida = {}
    for k in nombres:
        v = getattr(cfg, k)
        if isinstance(v, (set, frozenset)):
            v = sorted(v)
        try:
            json.dumps(v)
        except TypeError:
            continue
        salida[k] = v
    salida["DIAS_PERIODO"] = {str(k): v for k, v in cfg.DIAS_PERIODO.items()}
    salida["ENERGIA_EMBARAZO"] = {str(k): v for k, v in cfg.ENERGIA_EMBARAZO.items()}
    salida["EXCLUIDOS_SIEMPRE"] = EXCLUIDOS_SIEMPRE
    return salida


def _tiendas(d: oferta.Datos) -> pd.DataFrame:
    """Las sucursales que sucursales_cercanas() puede elegir, en el mismo orden."""
    t = d.tiendas
    return t[t["formato"].isin(cfg.FORMATOS_SUCURSAL) & ~t["es_web"].astype(bool) & t["lat"].notna()
             & (t["ubicacion_precision"] != "sin_ubicacion") & t.index.isin(list(d.rangos))]


class _Binario:
    """Secciones binarias alineadas a 8 bytes; el motor las lee como vistas tipadas."""

    def __init__(self):
        self.partes, self.secciones, self.largo = [], {}, 0

    def agregar(self, nombre: str, arr: np.ndarray):
        arr = np.ascontiguousarray(arr)
        tipo = {np.dtype("<f8"): "f64", np.dtype("<u4"): "u32", np.dtype("<u2"): "u16",
                np.dtype("<i4"): "i32"}[arr.dtype.newbyteorder("<")]
        relleno = (-self.largo) % 8
        if relleno:
            self.partes.append(b"\0" * relleno)
            self.largo += relleno
        datos = arr.astype(arr.dtype.newbyteorder("<")).tobytes()
        self.secciones[nombre] = {"desde": self.largo, "tipo": tipo, "n": int(arr.size)}
        self.partes.append(datos)
        self.largo += len(datos)

    def bytes(self) -> bytes:
        return b"".join(self.partes)


def paquete() -> tuple[dict, bytes]:
    d = oferta.cargar()
    p = d.productos
    t = _tiendas(d)
    binario = _Binario()

    # Productos: numéricos y nutrientes en float64; aptitud como bits (uno por restricción, en el orden de config).
    for c in NUMERICAS + oferta.NUTRIENTES + oferta.DERIVADOS:
        binario.agregar(f"p.{c}", p[c].to_numpy(float))
    aptitud = np.zeros(len(p), dtype=np.uint32)
    for i, r in enumerate(cfg.RESTRICCIONES):
        apto, _ = oferta.aptos(p, [r])
        aptitud |= apto.to_numpy().astype(np.uint32) << i
    binario.agregar("p.aptitud", aptitud)
    meta_productos = {"id": p.index.tolist(), "granel": p["forma_venta"].str.startswith("Granel").tolist()}
    for c in TEXTOS:
        meta_productos[c] = [_texto(v) for v in p[c]]
    for c in CATEGORICAS:
        cat = pd.Categorical(p[c].astype("object").where(p[c].notna(), None))
        meta_productos[c] = {"valores": [str(v) for v in cat.categories], "codigos": cat.codes.tolist()}

    # Precios por producto (así se repiten y comprimen mejor): de cada producto, sus tiendas y precios en centavos.
    tienda_pos = {k: i for i, k in enumerate(t.index)}
    filas_tienda = np.full(len(d.precios), -1, dtype=np.int64)
    for k, (a, b) in d.rangos.items():
        if k in tienda_pos:
            filas_tienda[a:b] = tienda_pos[k]
    quedan = filas_tienda >= 0
    prod = d.precios["prod"].to_numpy()[quedan]
    tienda = filas_tienda[quedan]
    orden = np.lexsort((tienda, prod))
    prod, tienda = prod[orden], tienda[orden]
    precio = np.round(d.precios["precio"].to_numpy()[quedan][orden] * 100).astype(np.uint32)
    promo = d.precios["precio_promocion"].to_numpy()[quedan][orden]
    promo = np.where(np.isnan(promo), 0, np.round(promo * 100)).astype(np.uint32)
    binario.agregar("precios.por_producto", np.bincount(prod, minlength=len(p)).astype(np.uint32))
    binario.agregar("precios.tienda", tienda.astype(np.uint16))
    binario.agregar("precios.centavos", precio)
    binario.agregar("precios.promocion", promo)

    tiendas = {"id": t.index.tolist(), "lat": t["lat"].astype(float).tolist(), "lon": t["lon"].astype(float).tolist()}
    for c in COLUMNAS_TIENDA:
        tiendas[c] = [_texto(v) for v in t[c]]
    tiendas["horarios"] = [[_texto(v) for v in fila] for fila in t[[f"horario_{x}" for x in DIAS]].to_numpy()]

    meta = {
        "fecha_precios": d.fecha, "generado": time.strftime("%Y-%m-%d %H:%M"),
        "productos_total": d.total_productos, "productos": meta_productos, "tiendas": tiendas,
        "binario": binario.secciones, "columnas_nutrientes": oferta.NUTRIENTES + oferta.DERIVADOS,
        "parametros": parametros(), "nombres": rq.NOMBRES,
        "requerimientos": rq.leer_tabla(cfg.RUTA_REQUERIMIENTOS).to_dict("records"),
        "guias": rq.leer_tabla(cfg.RUTA_GUIAS).to_dict("records"), "perfiles": rq.perfiles(),
        "criterios": {c["clave"]: c["criterio"] for c in oferta.criterios(list(cfg.RESTRICCIONES))},
    }
    return meta, binario.bytes()


def _comprimido(datos: bytes) -> str:
    return base64.b64encode(gzip.compress(datos, 9, mtime=0)).decode("ascii")


def exportar(ruta: Path = RUTA_EXPORTACION) -> Path:
    inicio = time.time()
    meta, binario = paquete()
    html = (DIR_WEB / "index.html").read_text(encoding="utf-8")
    css = (DIR_WEB / "estilos.css").read_text(encoding="utf-8")
    app = (DIR_WEB / "app.js").read_text(encoding="utf-8")
    motor = (DIR_WEB / "motor.js").read_text(encoding="utf-8")
    for nombre, codigo in (("app.js", app), ("motor.js", motor)):
        if "</script" in codigo:
            raise RuntimeError(f"{nombre} no se puede incrustar tal cual: contiene </script")
    texto_meta = json.dumps(meta, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    datos = (f'<script id="datos-meta" type="application/octet-stream">{_comprimido(texto_meta)}</script>\n'
             f'<script id="datos-binario" type="application/octet-stream">{_comprimido(binario)}</script>\n'
             f'<script id="motor-codigo" type="text/plain">\n{motor}</script>')
    for viejo, nuevo in (
        ('<link rel="stylesheet" href="estilos.css">', f"<style>\n{css}</style>"),
        ("<!-- DATOS -->", datos),
        ('<script src="app.js"></script>', f"<script>\n{app}</script>"),
    ):
        if viejo not in html:
            raise RuntimeError(f"La página cambió: no se encontró {viejo}")
        html = html.replace(viejo, nuevo)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(html, encoding="utf-8")
    logger.info("Página exportada en %s (%.1f MB: datos %.1f MB de metadatos y %.1f MB de precios y nutrientes, "
                "comprimidos; %.0f s)", ruta, ruta.stat().st_size / 1e6, len(_comprimido(texto_meta)) / 1e6,
                len(_comprimido(binario)) / 1e6, time.time() - inicio)
    return ruta
