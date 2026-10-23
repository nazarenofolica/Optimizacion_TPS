"""
Pregunta b): un único centro de distribución de capacidad infinita, sin costos de apertura ni de
operación. ¿Dónde se ubica? (plan §12 b, tarea T18).

Se resuelve en dos etapas:

    1. Punto de Weber continuo (src/weber.py) con distancia en línea recta × factor de ruta, con
       dos criterios: económico ($) y ambiental (km físicos). Grilla + Nelder–Mead; Weiszfeld como
       control independiente. Indica la ZONA donde conviene el centro.
    2. Grilla de puntos candidatos sobre esa zona (cada ~1 km), evaluada con distancias POR CALLE
       de OSRM. El factor de ruta es un promedio: en algunos lugares las calles dan 1,2 veces la
       línea recta y en otros 1,6, así que el mejor punto concreto lo decide la red de calles
       (desvío D11 en docs/procedimiento.md).

Después se compara con los centros candidatos A–D, con el centro de gravedad y con la red de la
pregunta a).

Salidas: resultados/tablas/13_punto_b.csv (etapa 1), 13b_punto_b_osrm.csv (etapa 2, tabla final),
13c_grilla_osrm.csv (todos los candidatos) y resultados/graficos/05_mapa_punto_b.png. Las
consultas a OSRM y a Nominatim (nombre de la zona) se guardan en datos/: si no cambian los
puntos, no hace falta internet.

    python scripts/04_punto_b.py
"""

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
if hasattr(sys.stdout, "reconfigure"):  # consola de Windows en cp1252
    sys.stdout.reconfigure(encoding="utf-8")

from src import datos, graficos, modelo, reportes, weber  # noqa: E402
from src.config import construir_params  # noqa: E402

TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"
CACHE_GRILLA = datos.CARPETA_DATOS / "osrm_grilla_punto_b.csv"
CACHE_ZONAS = datos.CARPETA_DATOS / "osrm_zonas_punto_b.json"
URL_TABLE = "https://router.project-osrm.org/table/v1/driving/{coords}"
URL_NEAREST = "https://router.project-osrm.org/nearest/v1/driving/{lon:.6f},{lat:.6f}?number=1"
URL_NOMINATIM = "https://nominatim.openstreetmap.org/reverse"
AGENTE = {"User-Agent": "TP3-Optimizacion-UCA/1.0 (uso academico)"}

TOL_WEISZFELD_KM = 0.05
#: Zona de la etapa 2: rodea a los dos puntos de Weber, al centro de gravedad y a A y B.
ZONA_LAT = (-34.640, -34.490)
ZONA_LON = (-58.620, -58.420)
PASO_ZONA = 0.01              # grados (≈ 1 km)
LOTE = 80                     # candidatos por consulta a OSRM (+ 17 destinos < 100)
ENGANCHE_MAX_M = 300          # un candidato que cae a más de 300 m de una calle se descarta


def pesos(x):
    return f"$ {x:,.0f}".replace(",", ".")


def numero(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------------------
# OSRM
# ---------------------------------------------------------------------------


def _destinos(ubic):
    return ubic[ubic["tipo"].isin(["planta", "supermercado"])]


def consultar_lote(candidatos, destinos):
    """Distancias por calle [km] de cada candidato a cada destino (ida) y de vuelta, y la distancia
    a la que OSRM engancha cada candidato a una calle [m]."""
    import requests  # solo si hace falta consultar

    n = len(candidatos)
    coords = [f"{lon:.6f},{lat:.6f}" for lat, lon in candidatos]
    coords += [f"{r.lon:.7f},{r.lat:.7f}" for r in destinos.itertuples()]
    idx_c = ";".join(str(i) for i in range(n))
    idx_d = ";".join(str(i) for i in range(n, len(coords)))
    base = URL_TABLE.format(coords=";".join(coords)) + "?annotations=distance"
    ida = requests.get(f"{base}&sources={idx_c}&destinations={idx_d}", timeout=90).json()
    vuelta = requests.get(f"{base}&sources={idx_d}&destinations={idx_c}", timeout=90).json()
    if ida.get("code") != "Ok" or vuelta.get("code") != "Ok":
        raise RuntimeError(f"OSRM: {ida.get('code')} / {vuelta.get('code')}")
    filas = []
    for c, (lat, lon) in enumerate(candidatos):
        for d, dest in enumerate(destinos.index):
            filas.append({"lat": round(lat, 6), "lon": round(lon, 6), "destino": dest,
                          "ida_km": ida["distances"][c][d] / 1000,
                          "vuelta_km": vuelta["distances"][d][c] / 1000,
                          "enganche_m": round(ida["sources"][c]["distance"], 1)})
    return filas


def distancias_osrm(candidatos, ubic, cache):
    """Distancias por calle de cada candidato [(lat, lon)], leídas de `cache` o consultadas."""
    claves = {(round(lat, 6), round(lon, 6)) for lat, lon in candidatos}
    previo = pd.read_csv(cache) if cache.exists() else pd.DataFrame(columns=["lat", "lon"])
    tenidos = set(zip(previo["lat"].round(6), previo["lon"].round(6)))
    faltan = sorted(claves - tenidos)
    if faltan:
        destinos = _destinos(ubic)
        filas = []
        for i in range(0, len(faltan), LOTE):
            filas += consultar_lote(faltan[i:i + LOTE], destinos)
        nuevo = pd.DataFrame(filas)
        nuevo["fecha_consulta"] = date.today().isoformat()
        previo = pd.concat([previo, nuevo], ignore_index=True) if len(previo) else nuevo
        previo.to_csv(cache, index=False)
    previo = previo.assign(lat=previo["lat"].round(6), lon=previo["lon"].round(6))
    return previo[[(la, lo) in claves for la, lo in zip(previo["lat"], previo["lon"])]]


def zona(lat, lon):
    """Calle más cercana (OSRM) y nombre de la zona (Nominatim). Guardado en CACHE_ZONAS."""
    cache = json.loads(CACHE_ZONAS.read_text(encoding="utf-8")) if CACHE_ZONAS.exists() else {}
    clave = f"{lat:.6f},{lon:.6f}"
    if clave not in cache:
        import requests

        cerca = requests.get(URL_NEAREST.format(lat=lat, lon=lon), timeout=30).json()
        nom = requests.get(URL_NOMINATIM, params={"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 14,
                                                  "accept-language": "es"}, headers=AGENTE, timeout=30).json()
        cache[clave] = {"calle": cerca["waypoints"][0]["name"],
                        "enganche_m": round(cerca["waypoints"][0]["distance"], 1),
                        "zona": nom.get("display_name", ""), "fecha_consulta": date.today().isoformat()}
        CACHE_ZONAS.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    return cache[clave]


# ---------------------------------------------------------------------------
# Evaluación de un centro único con distancias por calle
# ---------------------------------------------------------------------------


def evaluar_calle(params, ida, vuelta, nombre=None):
    """Costo y emisiones de un centro único. `ida[d]`: km del centro al destino d; `vuelta[d]`: km
    de d al centro. Cada producto sale de su planta más cercana al centro.

    Devuelve también los dos objetivos de la etapa 1 (conductores como costo por km, para poder
    comparar candidatos sin el salto del entero) y el costo real con conductores enteros."""
    ubic = datos.cargar_ubicaciones()
    s = params["supuestos"]
    Q = s["Q"]
    dem_k = datos.demanda_por_producto(params)
    dem_i = datos.demanda_por_super(params)
    elegidas = {k: min(ps, key=lambda p: vuelta[p]) for k, ps in datos.plantas_por_producto(ubic).items()}
    km_ida_t1 = sum(dem_k[k] / Q * vuelta[elegidas[k]] for k in dem_k.index)       # planta -> centro
    km_fis_t1 = sum(dem_k[k] / Q * (vuelta[elegidas[k]] + ida[elegidas[k]]) for k in dem_k.index)
    km_t2 = sum(dem_i[i] / Q * (ida[i] + vuelta[i]) for i in dem_i.index)
    fila = weber.evaluar(params, km_ida_t1, km_t2, elegidas, {"ubicacion": nombre} if nombre else None)
    # La tarifa se cobra sobre la ida; los km físicos usan la vuelta real (desvío D4).
    fila["km_tramo1"] = km_fis_t1
    fila["km_total"] = km_fis_t1 + km_t2
    fila["litros"] = fila["km_total"] / params["rendimiento"]
    fila["co2_kg"] = fila["litros"] * s["phi"]
    a, b = weber.pesos(params, "economico")
    fila["objetivo_economico"] = a * km_ida_t1 + b * km_t2
    return fila


def evaluar_grilla(params, dist):
    filas = []
    for (lat, lon), g in dist.groupby(["lat", "lon"]):
        ida, vuelta = g.set_index("destino")["ida_km"], g.set_index("destino")["vuelta_km"]
        fila = evaluar_calle(params, ida, vuelta)
        fila.update({"lat": lat, "lon": lon, "enganche_m": g["enganche_m"].iloc[0]})
        filas.append(fila)
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------


def main():
    params = construir_params()
    ubic = datos.cargar_ubicaciones()

    # --- Etapa 1: Weber continuo (línea recta × factor de ruta) ---------------------------
    sol = {}
    for criterio in ("economico", "ambiental"):
        pr = weber.Problema(params, criterio)
        lat, lon, valor, malla = weber.optimizar(pr)
        elegidas = pr.planta_elegida(lat, lon)
        lat_w, lon_w = weber.weiszfeld(pr, elegidas, lat, lon)
        dif = weber.distancia_km(lat, lon, lat_w, lon_w)
        assert dif < TOL_WEISZFELD_KM, f"{criterio}: Weiszfeld a {dif:.3f} km del óptimo"
        assert valor <= malla[2].min() + 1e-6, "El refinamiento no mejora la grilla"
        sol[criterio] = {"problema": pr, "lat": lat, "lon": lon, "valor": valor, "malla": malla,
                         "elegidas": elegidas, "weiszfeld_km": dif}
    eco, amb = sol["economico"], sol["ambiental"]
    pr_eco = eco["problema"]
    cg_lat, cg_lon = weber.centro_de_gravedad(pr_eco, eco["elegidas"])

    candidatos = {
        "Weber económico": (eco["lat"], eco["lon"]),
        "Weber ambiental": (amb["lat"], amb["lon"]),
        "Centro de gravedad": (cg_lat, cg_lon),
        **{f"Centro {j}": (ubic.at[j, "lat"], ubic.at[j, "lon"]) for j in "ABCD"},
    }
    filas = []
    for nombre, (lat, lon) in candidatos.items():
        fila = pr_eco.desglose(lat, lon)
        fila.update({"ubicacion": nombre, "lat": lat, "lon": lon,
                     "objetivo_economico": float(pr_eco.costo(lat, lon)),
                     "km_al_weber_economico": weber.distancia_km(lat, lon, eco["lat"], eco["lon"])})
        filas.append(fila)
    etapa1 = pd.DataFrame(filas)
    minimo = etapa1.loc[0, "objetivo_economico"]
    etapa1["sobrecosto_pct"] = 100 * (etapa1["objetivo_economico"] / minimo - 1)
    assert (etapa1["objetivo_economico"] >= minimo - 1e-6).all(), "Un candidato supera al óptimo"
    assert etapa1.loc[1, "km_total"] <= etapa1["km_total"].min() + 1e-6, "El ambiental no minimiza km"
    etapa1 = etapa1[["ubicacion", "lat", "lon", "km_al_weber_economico", "plantas", "km_tramo1",
                     "km_tramo2", "km_total", "litros", "co2_kg", "costo_tramo1", "costo_combustible_t2",
                     "conductores", "costo_conductores", "costo_total", "objetivo_economico",
                     "sobrecosto_pct"]]

    # --- Etapa 2: grilla por calle (OSRM) ---------------------------------------------------
    lats = np.round(np.arange(ZONA_LAT[0], ZONA_LAT[1] + 1e-9, PASO_ZONA), 6)
    lons = np.round(np.arange(ZONA_LON[0], ZONA_LON[1] + 1e-9, PASO_ZONA), 6)
    grilla = [(la, lo) for la in lats for lo in lons]
    for la, lo in ((eco["lat"], eco["lon"]), (amb["lat"], amb["lon"])):
        assert ZONA_LAT[0] < la < ZONA_LAT[1] and ZONA_LON[0] < lo < ZONA_LON[1], "Weber fuera de la zona"
    puntos_weber = [(round(eco["lat"], 6), round(eco["lon"], 6)), (round(amb["lat"], 6), round(amb["lon"], 6))]
    dist = distancias_osrm(grilla + puntos_weber, ubic, CACHE_GRILLA)
    todos = evaluar_grilla(params, dist)
    validos = todos[todos["enganche_m"] <= ENGANCHE_MAX_M].copy()
    validos["en_grilla"] = [(la, lo) in set(grilla) for la, lo in zip(validos["lat"], validos["lon"])]
    g = validos[validos["en_grilla"]]
    mejor_eco = g.loc[g["objetivo_economico"].idxmin()]
    mejor_amb = g.loc[g["km_total"].idxmin()]
    # Los mejores no pueden estar en el borde de la zona: si lo están, la zona es chica.
    for m in (mejor_eco, mejor_amb):
        assert lats[0] < m["lat"] < lats[-1] and lons[0] < m["lon"] < lons[-1], "Óptimo en el borde de la zona"

    osrm = datos.cargar_distancias("osrm")
    final = []
    ubicaciones = {
        "Óptimo por calle (económico)": (mejor_eco["lat"], mejor_eco["lon"]),
        "Óptimo por calle (ambiental)": (mejor_amb["lat"], mejor_amb["lon"]),
        "Weber económico": puntos_weber[0],
        "Weber ambiental": puntos_weber[1],
    }
    for nombre, (lat, lon) in ubicaciones.items():
        f = todos[(todos["lat"] == lat) & (todos["lon"] == lon)].iloc[0].to_dict()
        f.update({"ubicacion": nombre})
        final.append(f)
    for j in "ABCD":
        f = evaluar_calle(params, osrm.loc[j].to_dict(), osrm[j].to_dict(), f"Centro {j}")
        f.update({"lat": ubic.at[j, "lat"], "lon": ubic.at[j, "lon"], "enganche_m": np.nan})
        final.append(f)
    etapa2 = pd.DataFrame(final)
    etapa2["sobrecosto_pct"] = 100 * (etapa2["objetivo_economico"] / etapa2["objetivo_economico"].min() - 1)
    assert etapa2["objetivo_economico"].idxmin() == 0, "Otra ubicación supera al óptimo por calle"
    etapa2["km_al_optimo"] = [weber.distancia_km(la, lo, mejor_eco["lat"], mejor_eco["lon"])
                              for la, lo in zip(etapa2["lat"], etapa2["lon"])]
    zonas = {n: zona(*ubicaciones[n]) for n in list(ubicaciones)[:2]}
    etapa2["calle"] = [zonas[n]["calle"] if n in zonas else "" for n in etapa2["ubicacion"]]
    etapa2["zona"] = [zonas[n]["zona"] if n in zonas else "" for n in etapa2["ubicacion"]]
    etapa2 = etapa2[["ubicacion", "lat", "lon", "calle", "zona", "km_al_optimo", "plantas", "km_tramo1",
                     "km_tramo2", "km_total", "litros", "co2_kg", "costo_tramo1", "costo_combustible_t2",
                     "conductores", "costo_conductores", "costo_total", "objetivo_economico",
                     "sobrecosto_pct"]]

    # --- Comparación con la red de la pregunta a) ------------------------------------------
    base = modelo.resolver(params)
    transporte_a = sum(base["desglose"][r] for r in ("tramo1_tercerizado", "tramo2_combustible", "conductores"))
    ref = etapa2.iloc[0]
    assert ref["costo_total"] > transporte_a, "Un centro único no debería mejorar el transporte de a)"

    # --- Salidas ----------------------------------------------------------------------------
    reportes.guardar({
        "13_punto_b": etapa1,
        "13b_punto_b_osrm": etapa2,
        "13c_grilla_osrm": todos.drop(columns=["plantas"]).sort_values("objetivo_economico"),
    }, TABLAS)
    GRAFICOS.mkdir(parents=True, exist_ok=True)
    sobre = validos[validos["en_grilla"]].copy()
    sobre["sobrecosto_pct"] = 100 * (sobre["objetivo_economico"] / mejor_eco["objetivo_economico"] - 1)
    graficos.mapa_punto_b(
        ubic, sobre,
        [("Óptimo por calle (económico)", mejor_eco["lat"], mejor_eco["lon"], "*"),
         ("Óptimo por calle (ambiental)", mejor_amb["lat"], mejor_amb["lon"], "D"),
         ("Weber en línea recta (económico)", eco["lat"], eco["lon"], "o"),
         ("Centro de gravedad", cg_lat, cg_lon, "X")],
        "¿Dónde conviene un único centro de distribución?", GRAFICOS / "05_mapa_punto_b.png")
    cerca = sobre[sobre["sobrecosto_pct"] <= 1]

    # --- Resumen en consola -----------------------------------------------------------------
    print("=" * 78)
    print("PREGUNTA b) — UN ÚNICO CENTRO DE CAPACIDAD INFINITA Y COSTOS NULOS")
    print("=" * 78)
    print("Etapa 1 — Weber continuo (línea recta × factor de ruta):")
    for criterio, s in sol.items():
        print(f"  {criterio:<10} lat {s['lat']:.5f}, lon {s['lon']:.5f}  (Weiszfeld a {s['weiszfeld_km'] * 1000:.0f} m)")
    print(f"  centro de gravedad lat {cg_lat:.5f}, lon {cg_lon:.5f}")
    for f in etapa1.itertuples():
        print(f"    {f.ubicacion:<20}{pesos(f.costo_total):>16}  +{numero(f.sobrecosto_pct, 1):>5} %"
              f"{numero(f.km_total):>10} km{numero(f.co2_kg):>10} kg CO₂  conductores {f.conductores}")
    print(f"\nEtapa 2 — {len(g)} candidatos por calle (OSRM; {len(todos) - len(validos)} descartados por estar"
          f" a más de {ENGANCHE_MAX_M} m de una calle):")
    for f in etapa2.itertuples():
        print(f"  {f.ubicacion:<30}{pesos(f.costo_total):>16}  +{numero(f.sobrecosto_pct, 1):>5} %"
              f"{numero(f.km_total):>10} km{numero(f.co2_kg):>10} kg CO₂  conductores {f.conductores}")
    for n, z in zonas.items():
        print(f"  {n}: lat {ubicaciones[n][0]:.3f}, lon {ubicaciones[n][1]:.3f} · {z['calle']} — {z['zona']}")
    print(f"  Candidatos a menos de 1 % del mejor: {len(cerca)}, entre lat {cerca['lat'].min():.2f} y "
          f"{cerca['lat'].max():.2f}, lon {cerca['lon'].min():.2f} y {cerca['lon'].max():.2f}")
    print(f"\nRed de la pregunta a) ({base['configuracion']}): transporte {pesos(transporte_a)},"
          f" {numero(base['km_total'])} km, {numero(base['co2_kg'])} kg CO₂")
    print(f"Centro único (óptimo por calle): transporte {pesos(ref['costo_total'])},"
          f" {numero(ref['km_total'])} km, {numero(ref['co2_kg'])} kg CO₂")
    print(f"\nTablas en {TABLAS.relative_to(RAIZ)}, gráfico 05_mapa_punto_b.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
