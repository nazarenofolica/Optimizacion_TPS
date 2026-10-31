"""
Fuentes geográficas oficiales para ubicar y validar las sucursales.

  - API Georef (Servicio de Normalización de Datos Geográficos de Argentina,
    apis.datos.gob.ar/georef): a qué provincia, departamento y municipio
    corresponde una coordenada (con los códigos del INDEC) y dónde queda una
    dirección (calle y altura, interpolada sobre la cartografía de calles).
    Se consulta en lotes de hasta MAX_LOTE.
  - Normalizador de direcciones de la Ciudad de Buenos Aires (USIG): más
    preciso en CABA y tolerante con las formas de escribir las calles.
  - Barrios y comunas de CABA (datos abiertos del GCBA).

Todas las respuestas se guardan en cache/geo/ y se reutilizan: una corrida
nueva solo consulta lo que no vio antes.
"""

from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from sepa import config as cfg

logger = logging.getLogger("sepa.fuentes.geografia")

MAX_LOTE = 1000        # consultas por pedido
MAX_SUMA_MAX = 5000    # suma de los "max" de las consultas de un pedido
RUTA_UBICACIONES = cfg.DIR_GEO / "georef_ubicaciones.json"
RUTA_DIRECCIONES = cfg.DIR_GEO / "georef_direcciones.json"
RUTA_USIG = cfg.DIR_GEO / "geocodigos.json"
RUTA_BARRIOS = cfg.DIR_GEO / "barrios.geojson"

# ISO 3166-2 (como lo informa SEPA) -> código de provincia del INDEC (como lo usa Georef).
PROVINCIAS = {
    "AR-C": ("02", "Ciudad Autónoma de Buenos Aires"), "AR-B": ("06", "Buenos Aires"), "AR-K": ("10", "Catamarca"),
    "AR-X": ("14", "Córdoba"), "AR-W": ("18", "Corrientes"), "AR-H": ("22", "Chaco"), "AR-U": ("26", "Chubut"),
    "AR-E": ("30", "Entre Ríos"), "AR-P": ("34", "Formosa"), "AR-Y": ("38", "Jujuy"), "AR-L": ("42", "La Pampa"),
    "AR-F": ("46", "La Rioja"), "AR-M": ("50", "Mendoza"), "AR-N": ("54", "Misiones"), "AR-Q": ("58", "Neuquén"),
    "AR-R": ("62", "Río Negro"), "AR-A": ("66", "Salta"), "AR-J": ("70", "San Juan"), "AR-D": ("74", "San Luis"),
    "AR-Z": ("78", "Santa Cruz"), "AR-S": ("82", "Santa Fe"), "AR-G": ("86", "Santiago del Estero"),
    "AR-T": ("90", "Tucumán"), "AR-V": ("94", "Tierra del Fuego, Antártida e Islas del Atlántico Sur"),
}


def _leer_cache(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}


def _guardar_cache(ruta: Path, datos: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")


def _post(recurso: str, cuerpo: dict) -> dict:
    for intento in range(4):
        try:
            r = requests.post(f"{cfg.URL_GEOREF}/{recurso}", json=cuerpo, timeout=120)
            if r.status_code == 200:
                return r.json()
            logger.warning("Georef %s respondió %s", recurso, r.status_code)
        except requests.RequestException as e:
            logger.warning("Georef %s: %s", recurso, e)
        time.sleep(3 * (intento + 1))
    raise RuntimeError(f"La API Georef ({recurso}) no responde")


# ============================================================
# COORDENADA -> PROVINCIA, DEPARTAMENTO, MUNICIPIO
# ============================================================

def ubicar(lat: pd.Series, lon: pd.Series) -> pd.DataFrame:
    """Provincia, departamento y municipio (nombre y código INDEC) de cada coordenada; vacío fuera del país."""
    cache = _leer_cache(RUTA_UBICACIONES)
    claves = [f"{a:.6f},{o:.6f}" if np.isfinite(a) and np.isfinite(o) else "" for a, o in zip(lat, lon)]
    faltan = sorted({k for k in claves if k and k not in cache})
    for i in range(0, len(faltan), MAX_LOTE):
        lote = faltan[i:i + MAX_LOTE]
        cuerpo = {"ubicaciones": [{"lat": float(k.split(",")[0]), "lon": float(k.split(",")[1]), "aplanar": True}
                                  for k in lote]}
        for k, res in zip(lote, _post("ubicacion", cuerpo)["resultados"]):
            cache[k] = res.get("ubicacion") or {}
    if faltan:
        logger.info("Georef: %d coordenadas ubicadas", len(faltan))
        _guardar_cache(RUTA_UBICACIONES, cache)
    campos = ["provincia_id", "provincia_nombre", "departamento_id", "departamento_nombre", "municipio_id",
              "municipio_nombre"]
    return pd.DataFrame([{c: (cache.get(k) or {}).get(c) for c in campos} for k in claves], index=lat.index)


# ============================================================
# DIRECCIÓN -> COORDENADA
# ============================================================

def geocodificar(direcciones: pd.Series, provincias: pd.Series, localidades_censales: pd.Series,
                 max_candidatos: int = 5) -> pd.Series:
    """
    Candidatos de Georef para cada dirección dentro de su provincia y, si se conoce, de su localidad censal
    (sin acotar, "San Martín 251" aparece en decenas de pueblos, incluso de un mismo departamento): lista de
    dicts con lat, lon, departamento_id, departamento_nombre, localidad, nomenclatura. Vacía si no la encuentra.
    """
    cache = _leer_cache(RUTA_DIRECCIONES)
    claves = [f"{p}|{loc if isinstance(loc, str) else ''}|{d}" if isinstance(d, str) and d and isinstance(p, str) and p
              else "" for d, p, loc in zip(direcciones, provincias, localidades_censales)]
    faltan = sorted({k for k in claves if k and k not in cache})
    for i in range(0, len(faltan), MAX_SUMA_MAX // max_candidatos):
        lote = faltan[i:i + MAX_SUMA_MAX // max_candidatos]
        cuerpo = {"direcciones": []}
        for k in lote:
            prov, loc, dire = k.split("|", 2)
            consulta = {"direccion": dire, "provincia": prov, "aplanar": True, "max": max_candidatos}
            if loc:
                consulta["localidad_censal"] = loc
            cuerpo["direcciones"].append(consulta)
        for k, res in zip(lote, _post("direcciones", cuerpo)["resultados"]):
            cache[k] = [{"lat": d.get("ubicacion_lat"), "lon": d.get("ubicacion_lon"),
                         "departamento_id": d.get("departamento_id"), "departamento_nombre": d.get("departamento_nombre"),
                         "localidad": d.get("localidad_censal_nombre"), "nomenclatura": d.get("nomenclatura")}
                        for d in res.get("direcciones") or [] if d.get("ubicacion_lat") is not None]
    if faltan:
        logger.info("Georef: %d direcciones geocodificadas", len(faltan))
        _guardar_cache(RUTA_DIRECCIONES, cache)
    return pd.Series([cache.get(k, []) if k else [] for k in claves], index=direcciones.index, dtype=object)


def localidades(nombres: pd.Series) -> pd.Series:
    """
    Dónde existe una localidad con ese nombre (en cualquier provincia): lista de dicts con provincia_id,
    departamento_id, municipio_id, nombre, lat, lon del centroide. Sirve para decidir si una coordenada es
    coherente con la localidad declarada aunque el código de provincia de SEPA esté mal.
    """
    ruta = cfg.DIR_GEO / "georef_localidades_por_nombre.json"
    cache = _leer_cache(ruta)
    claves = [n.strip() if isinstance(n, str) and len(n.strip()) >= 3 else "" for n in nombres]
    faltan = sorted({k for k in claves if k and k not in cache})
    por_lote = MAX_SUMA_MAX // 20     # Georef: la suma de los "max" de un lote no puede pasar de 5000
    for i in range(0, len(faltan), por_lote):
        lote = faltan[i:i + por_lote]
        cuerpo = {"localidades": [{"nombre": k, "max": 20, "aplanar": True} for k in lote]}
        for k, res in zip(lote, _post("localidades", cuerpo)["resultados"]):
            cache[k] = [{"provincia_id": l.get("provincia_id"), "departamento_id": l.get("departamento_id"),
                         "municipio_id": l.get("municipio_id"), "localidad_censal_id": l.get("localidad_censal_id"),
                         "nombre": l.get("nombre"), "lat": l.get("centroide_lat"), "lon": l.get("centroide_lon")}
                        for l in res.get("localidades") or []]
    if faltan:
        logger.info("Georef: %d nombres de localidad consultados", len(faltan))
        _guardar_cache(ruta, cache)
    return pd.Series([cache.get(k, []) if k else [] for k in claves], index=nombres.index, dtype=object)


def localidades_de_departamentos(departamentos: list[str]) -> dict[str, list[str]]:
    """Nombres de todas las localidades de cada departamento (para reconocer "Budge" en "Ingeniero Budge")."""
    ruta = cfg.DIR_GEO / "georef_localidades_por_departamento.json"
    cache = _leer_cache(ruta)
    faltan = sorted({d for d in departamentos if isinstance(d, str) and d and d not in cache})
    por_lote = MAX_SUMA_MAX // 500
    for i in range(0, len(faltan), por_lote):
        lote = faltan[i:i + por_lote]
        cuerpo = {"localidades": [{"departamento": d, "max": 500, "aplanar": True, "campos": "nombre"} for d in lote]}
        for d, res in zip(lote, _post("localidades", cuerpo)["resultados"]):
            cache[d] = sorted({l.get("nombre") for l in res.get("localidades") or [] if l.get("nombre")})
    if faltan:
        _guardar_cache(ruta, cache)
    return {d: cache.get(d, []) for d in departamentos if isinstance(d, str)}


def centroides_localidad(nombres: pd.Series, provincias: pd.Series) -> pd.DataFrame:
    """Centroide de la localidad declarada (Georef), para ubicar aproximadamente lo que no tiene dirección útil."""
    ruta = cfg.DIR_GEO / "georef_localidades.json"
    cache = _leer_cache(ruta)
    claves = [f"{p}|{n}" if isinstance(n, str) and n.strip() and isinstance(p, str) and p else ""
              for n, p in zip(nombres, provincias)]
    faltan = sorted({k for k in claves if k and k not in cache})
    for i in range(0, len(faltan), MAX_LOTE):
        lote = faltan[i:i + MAX_LOTE]
        cuerpo = {"localidades": [{"nombre": k.split("|", 1)[1], "provincia": k.split("|", 1)[0], "max": 1,
                                   "aplanar": True} for k in lote]}
        for k, res in zip(lote, _post("localidades", cuerpo)["resultados"]):
            loc = (res.get("localidades") or [{}])[0]
            cache[k] = {"lat": loc.get("centroide_lat"), "lon": loc.get("centroide_lon"), "nombre": loc.get("nombre")}
    if faltan:
        _guardar_cache(ruta, cache)
    return pd.DataFrame([cache.get(k, {}) if k else {} for k in claves], index=nombres.index,
                        columns=["lat", "lon", "nombre"])


# ============================================================
# CABA: normalizador USIG, barrios y comunas
# ============================================================

TITULOS = {"GRAL", "GENERAL", "DR", "DOCTOR", "ING", "INGENIERO", "MRCAL", "MARISCAL", "PTE", "PRESIDENTE",
           "CNEL", "CRNEL", "CORONEL", "TTE", "TENIENTE", "ALTE", "ALMIRANTE", "CAP", "CAPITAN", "GOB", "PBRO"}
PREFIJOS = {"AV", "AVENIDA", "AVDA", "CL", "CALLE", "PJE", "PASAJE", "BV", "BOULEVARD"}
COMERCIO_NOMBRE_AL_FINAL = 9     # Cencosud escribe "Rivadavia Bernardino", "Las Heras gral. Juan Gregori"


def limpiar_direccion(texto: str) -> str:
    """'AV DR.HONORIO PUEYRREDON 652-654-656 (ALMAGRO)' -> 'AV DR HONORIO PUEYRREDON 652'."""
    t = re.sub(r"\(.*?\)|\[.*?\]", " ", texto or "")
    t = re.sub(r"\b[Nn][º°o]\.?\s*", " ", t)                            # "n° 4402", "Nro."
    t = re.sub(r"([A-Za-zÁÉÍÓÚÑáéíóúñ])(\d)", r"\1 \2", t)               # "CUENCA2567"
    t = re.sub(r"(\d+)\s*[-/]\s*\d+(\s*[-/,]\s*\d+)*", r"\1", t)         # rangos de altura: la primera
    t = re.sub(r"\b(\d+)\s+\1\b", r"\1", t)                              # altura repetida: "5501 5501"
    t = re.sub(r"^\s*(CL|CALLE)\s*(?=[A-Z])", "", t, flags=re.I)          # "CL HIDALGO", "CLFERRE"
    t = t.replace(".", " ")
    return re.sub(r"\s+", " ", t).strip()


def _variantes_usig(direccion: str, comercio: int) -> list[str]:
    t = limpiar_direccion(direccion)
    salida = [t]
    m = re.search(r"^(.*?)\s+(\d+)\s*$", t)
    if m:
        calle, altura = m.group(1), m.group(2)
        pegada = re.match(r"^AV(?!ELLANEDA|IADOR|ENIDA)([A-Z]{2,}.*)$", calle, flags=re.I)   # "AVLA PLATA"
        if pegada:
            salida.append(f"AV {pegada.group(1)} {altura}")
        if comercio == COMERCIO_NOMBRE_AL_FINAL:
            palabras = [w for w in calle.split() if w.upper() not in PREFIJOS]
            corte = next((i for i, w in enumerate(palabras) if w.upper() in TITULOS), None)
            if corte:
                salida.append(" ".join(palabras[:corte]) + " " + altura)
            for k in (1, 2):
                if len(palabras) > k:
                    salida.append(" ".join(palabras[:-k]) + " " + altura)
    return list(dict.fromkeys(v for v in salida if v))


def _consultar_usig(direccion: str) -> list[dict]:
    for intento in range(3):
        try:
            r = requests.get(cfg.URL_USIG, params={"direccion": f"{direccion}, CABA", "geocodificar": "true",
                                                    "srid": 4326}, timeout=30)
            r.raise_for_status()
            datos = r.json()
            break
        except (requests.RequestException, ValueError):
            time.sleep(1 + intento * 2)
    else:
        return []
    salida = []
    for d in datos.get("direccionesNormalizadas", []) or []:
        coord = d.get("coordenadas") or {}
        if d.get("cod_partido") != "caba" or not coord:
            continue
        try:
            salida.append({"direccion": d.get("direccion"), "lon": float(coord["x"]), "lat": float(coord["y"])})
        except (KeyError, TypeError, ValueError):
            continue
    return salida


def geocodificar_caba(direcciones: pd.Series, comercios: pd.Series) -> pd.Series:
    """Candidatos del normalizador USIG para direcciones de CABA (primera variante que devuelve algo)."""
    cache = _leer_cache(RUTA_USIG)
    pedidos = list(zip(direcciones.fillna(""), comercios.astype(int)))
    pendientes = {p: _variantes_usig(*p) for p in set(pedidos) if p[0]}
    resultado: dict = {}
    consultadas = 0
    while pendientes:
        faltan = sorted({vs[0] for vs in pendientes.values() if vs[0] not in cache})
        if faltan:
            consultadas += len(faltan)
            with ThreadPoolExecutor(4) as ex:
                for v, r in zip(faltan, ex.map(_consultar_usig, faltan)):
                    cache[v] = r
        siguiente = {}
        for p, vs in pendientes.items():
            if cache.get(vs[0]) or len(vs) == 1:
                resultado[p] = cache.get(vs[0], [])
            else:
                siguiente[p] = vs[1:]
        pendientes = siguiente
    if consultadas:
        logger.info("USIG: %d variantes de dirección consultadas", consultadas)
        _guardar_cache(RUTA_USIG, cache)
    return pd.Series([resultado.get(p, []) for p in pedidos], index=direcciones.index, dtype=object)


def barrios_caba(lat: pd.Series, lon: pd.Series) -> pd.DataFrame:
    """Barrio y comuna oficiales de CABA para cada coordenada (el más cercano, para puntos sobre el borde)."""
    import geopandas as gpd
    from shapely import points

    if not RUTA_BARRIOS.exists():
        RUTA_BARRIOS.parent.mkdir(parents=True, exist_ok=True)
        RUTA_BARRIOS.write_bytes(requests.get(cfg.URL_BARRIOS_CABA, timeout=120).content)
    b = gpd.read_file(RUTA_BARRIOS).rename(columns={"nombre": "barrio"})[["barrio", "comuna", "geometry"]]
    b = b.to_crs("EPSG:32721")
    pts = gpd.GeoDataFrame(index=lat.index, geometry=gpd.GeoSeries(points(lon.to_numpy(float), lat.to_numpy(float)),
                                                                     index=lat.index, crs="EPSG:4326").to_crs("EPSG:32721"))
    unido = gpd.sjoin_nearest(pts, b, how="left")
    unido = unido[~unido.index.duplicated()]
    return pd.DataFrame({"barrio": unido["barrio"].str.title(),
                         "comuna": pd.to_numeric(unido["comuna"], errors="coerce").astype("Int64")}, index=lat.index)


def distancia_m(lat1, lon1, lat2, lon2) -> np.ndarray:
    """Distancia en metros (haversine)."""
    lat1, lon1, lat2, lon2 = (np.radians(np.asarray(x, dtype=float)) for x in (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6_371_000 * np.arcsin(np.sqrt(a))
