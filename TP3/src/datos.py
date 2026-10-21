"""
Ubicaciones, distancias y coeficientes por arco del modelo de CarroMenos.

Las funciones que reciben `params` (de config.construir_params) son puras. Las de carga leen
datos/ (el mapa y la matriz de distancias que genera scripts/01_distancias.py).

Implementa el plan §2.4 (ubicaciones), S1 (distancias) y §6.2 (coeficientes por pallet):

    costo tramo 1 (tercerizado):   T · d_pj / Q        (S10: ida; ida + vuelta en el test D)
    costo tramo 1 (propio, en d):  CK · (d_pj + d_jp) / Q
    costo tramo 2 (propio):        CK · (d_ji + d_ij) / Q
    km físicos por pallet:         (ida + vuelta) / Q  (el camión vuelve vacío)

El plan escribe 2·d; con OSRM la vuelta no siempre mide lo mismo que la ida (desvío D4).
"""

import json
from itertools import combinations
import math
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CARPETA_DATOS = RAIZ / "datos"
ARCHIVO_UBICACIONES = CARPETA_DATOS / "ubicaciones.csv"
ARCHIVO_OSRM = CARPETA_DATOS / "distancias_osrm.csv"
ARCHIVO_HAVERSINE = CARPETA_DATOS / "distancias_haversine.csv"
ARCHIVO_META = CARPETA_DATOS / "distancias_meta.json"

RADIO_TIERRA_KM = 6371.0088  # radio medio (IUGG)


# ---------------------------------------------------------------------------
# Ubicaciones
# ---------------------------------------------------------------------------


def cargar_ubicaciones():
    """Los 21 puntos del mapa, indexados por id (S1..S10, A..D, P_<producto>_<n>)."""
    return pd.read_csv(ARCHIVO_UBICACIONES, index_col="id")


def ids(ubic, tipo):
    """Ids de un tipo de punto ('supermercado', 'centro' o 'planta'), en el orden del archivo."""
    return list(ubic.index[ubic["tipo"] == tipo])


def plantas_por_producto(ubic):
    """{producto: [plantas]}. Fideos y Leche tienen dos (plan §2.4)."""
    plantas = ubic[ubic["tipo"] == "planta"]
    return {k: sorted(g.index) for k, g in plantas.groupby("producto")}


def producto_de_planta(ubic):
    """{planta: producto}."""
    return ubic.loc[ubic["tipo"] == "planta", "producto"].to_dict()


def arcos_del_modelo(ubic):
    """Arcos (origen, destino) que usa algún escenario: planta -> centro, centro -> súper y
    planta -> súper (el viaje directo de Goyito, pregunta c)."""
    plantas, centros, supers = ids(ubic, "planta"), ids(ubic, "centro"), ids(ubic, "supermercado")
    return (
        [(p, j) for p in plantas for j in centros]
        + [(j, i) for j in centros for i in supers]
        + [(p, i) for p in plantas for i in supers]
    )


# ---------------------------------------------------------------------------
# Distancias (supuesto S1)
# ---------------------------------------------------------------------------


def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia en línea recta sobre la esfera [km]."""
    f1, f2 = math.radians(lat1), math.radians(lat2)
    df, dl = f2 - f1, math.radians(lon2 - lon1)
    a = math.sin(df / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(dl / 2) ** 2
    return 2 * RADIO_TIERRA_KM * math.asin(math.sqrt(a))


def matriz_haversine(ubic):
    """Matriz 21 x 21 de distancias en línea recta [km]."""
    return pd.DataFrame(
        [[haversine_km(a.lat, a.lon, b.lat, b.lon) for b in ubic.itertuples()] for a in ubic.itertuples()],
        index=ubic.index,
        columns=ubic.index,
    )


def factor_ruta():
    """Mediana de OSRM / haversine sobre los arcos del modelo (lo calcula 01_distancias.py)."""
    return json.loads(ARCHIVO_META.read_text(encoding="utf-8"))["factor_ruta"]


def cargar_distancias(tipo):
    """Matriz de distancias [km] según S1.

    'osrm'      -> por calle, leída de datos/distancias_osrm.csv.
    'haversine' -> línea recta x factor de ruta (respaldo de S1, test A y pregunta b).
    """
    if tipo == "osrm":
        if not ARCHIVO_OSRM.exists():
            raise FileNotFoundError(f"Falta {ARCHIVO_OSRM.name}: correr scripts/01_distancias.py")
        return pd.read_csv(ARCHIVO_OSRM, index_col=0)
    if tipo == "haversine":
        return matriz_haversine(cargar_ubicaciones()) * factor_ruta()
    raise ValueError(f"Tipo de distancia desconocido: {tipo!r}")


def distancias(params):
    """Matriz de distancias del escenario (`params['supuestos']['distancias']`)."""
    return cargar_distancias(params["supuestos"]["distancias"])


# ---------------------------------------------------------------------------
# Demanda (plan §2.3)
# ---------------------------------------------------------------------------


def tabla_demanda(params):
    """DataFrame producto x supermercado [pallets/mes]."""
    return pd.DataFrame(
        {s: [params["demanda"][s, k] for k in params["productos"]] for s in params["supermercados"]},
        index=list(params["productos"]),
    )


def demanda_por_producto(params):
    return tabla_demanda(params).sum(axis=1)


def demanda_por_super(params):
    return tabla_demanda(params).sum(axis=0)


# ---------------------------------------------------------------------------
# Coeficientes por pallet (plan §6.2)
# ---------------------------------------------------------------------------


def costo_tramo1_tercerizado(params, d_ida, d_iv):
    """$ por pallet de planta a centro con el tercerizado: T · d / Q.

    S10: la tarifa se cobra sobre el km de ida (`d_ida`), o sobre ida y vuelta (`d_iv`) en el test D.
    """
    s = params["supuestos"]
    km_cobrados = d_iv if s["tarifa_ida_vuelta"] else d_ida
    return s["tarifa_T"] * km_cobrados / s["Q"]


def costo_propio(params, d_iv):
    """$ de combustible por pallet con camión propio: CK · (ida + vuelta) / Q."""
    return params["combustible_km"] * d_iv / params["supuestos"]["Q"]


def km_fisicos(params, d_iv):
    """km que recorre el camión por pallet transportado: (ida + vuelta) / Q.

    Plan §6.2 escribe 2·d; con OSRM la vuelta puede ser distinta de la ida (calles de una mano),
    así que se usa la suma real (desvío D4). Con haversine es exactamente 2·d.
    """
    return d_iv / params["supuestos"]["Q"]


def coeficientes_por_arco(params, dist=None):
    """Tabla de todos los arcos con distancia, km físicos y costos por pallet.

    Columnas: tramo, origen, destino, producto (solo plantas), d_km (ida), d_iv_km (ida y
    vuelta), km_por_pallet, costo_tercerizado (tramo 1 y directo), costo_propio (combustible),
    kg_co2_por_pallet.
    """
    ubic = cargar_ubicaciones()
    dist = distancias(params) if dist is None else dist
    prod = producto_de_planta(ubic)
    phi, r = params["supuestos"]["phi"], params["rendimiento"]
    filas = []
    for o, de in arcos_del_modelo(ubic):
        tipo_o, tipo_d = ubic.at[o, "tipo"], ubic.at[de, "tipo"]
        tramo = {
            ("planta", "centro"): "1_planta_centro",
            ("centro", "supermercado"): "2_centro_super",
            ("planta", "supermercado"): "directo_goyito",
        }[tipo_o, tipo_d]
        d = float(dist.loc[o, de])
        d_iv = d + float(dist.loc[de, o])
        km = km_fisicos(params, d_iv)
        filas.append({
            "tramo": tramo,
            "origen": o,
            "destino": de,
            "producto": prod.get(o, ""),
            "d_km": d,
            "d_iv_km": d_iv,
            "km_por_pallet": km,
            "costo_tercerizado": (
                costo_tramo1_tercerizado(params, d, d_iv) if tramo != "2_centro_super" else None
            ),
            "costo_propio": costo_propio(params, d_iv),
            "kg_co2_por_pallet": km / r * phi,
        })
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Configuraciones de centros (plan §4.2 y §9)
# ---------------------------------------------------------------------------


def configuraciones(params):
    """Todas las combinaciones de centros que respetan S2, con capacidad, fijos y si cubren la
    demanda. Ordenadas por costo fijo.

    S2 'exclusivo'    -> exactamente uno de A, B.
    S2 'al_menos_uno' -> al menos uno de A, B (test B).
    El gerente se paga con 3 o más centros abiertos (S3).
    """
    centros = params["centros"]
    principales = set(params["principales"])
    exclusivo = params["supuestos"]["principal"] == "exclusivo"
    demanda_total = sum(params["demanda"].values())
    filas = []
    for n in range(1, len(centros) + 1):
        for combo in combinations(centros, n):
            m = len(principales & set(combo))
            if m == 0 or (exclusivo and m != 1):
                continue
            gerente = n >= 3
            apertura = sum(centros[j]["apertura"] for j in combo)
            capacidad = sum(centros[j]["capacidad"] for j in combo)
            filas.append({
                "configuracion": "+".join(combo),
                "centros": combo,
                "capacidad": capacidad,
                "cubre_demanda": capacidad >= demanda_total,
                "apertura": apertura,
                "gerente": gerente,
                "fijo_total": apertura + gerente * params["gerente"],
            })
    return pd.DataFrame(filas).sort_values("fijo_total", ignore_index=True)


def configuraciones_factibles(params):
    """Las configuraciones de `configuraciones` que cubren la demanda total."""
    tabla = configuraciones(params)
    return tabla[tabla["cubre_demanda"]].reset_index(drop=True)
