"""
Matriz de distancias por calle (OSRM) y en línea recta (haversine) entre los 21 puntos del mapa.

Se corre UNA vez (necesita internet). El resultado queda guardado y el resto del trabajo lo lee
de disco, sin depender del servicio:

    datos/distancias_osrm.csv        km por ruta, 21 x 21 (fila = origen, columna = destino)
    datos/distancias_haversine.csv   km en línea recta, 21 x 21
    datos/distancias_meta.json       fecha de consulta, servicio y factor de ruta

Supuesto S1 del docs/plan_de_trabajo.md §5.1. El factor de ruta es el respaldo de S1 (y lo que
usa la pregunta b): la mediana de OSRM / haversine sobre los arcos que usa el modelo.

    python scripts/01_distancias.py            # usa lo guardado si ya existe
    python scripts/01_distancias.py --forzar   # vuelve a consultar OSRM
"""

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
if hasattr(sys.stdout, "reconfigure"):  # consola de Windows en cp1252
    sys.stdout.reconfigure(encoding="utf-8")

from src import datos  # noqa: E402

URL_OSRM = "https://router.project-osrm.org/table/v1/driving/{coords}?annotations=distance"


def consultar_osrm(ubic):
    """Matriz de distancias por ruta en km, con el servicio `table` de OSRM."""
    coords = ";".join(f"{lon:.7f},{lat:.7f}" for lat, lon in zip(ubic["lat"], ubic["lon"]))
    resp = requests.get(URL_OSRM.format(coords=coords), timeout=60)
    resp.raise_for_status()
    cuerpo = resp.json()
    if cuerpo.get("code") != "Ok":
        raise RuntimeError(f"OSRM respondió {cuerpo.get('code')}: {cuerpo.get('message')}")
    km = pd.DataFrame(cuerpo["distances"], index=ubic.index, columns=ubic.index) / 1000
    # Dónde "engancha" OSRM cada punto en la red de calles: si está lejos, el punto del
    # mapa cae fuera de una calle y conviene saberlo.
    enganche = pd.Series([w["distance"] for w in cuerpo["sources"]], index=ubic.index)
    return km, enganche


def main(forzar=False):
    ubic = datos.cargar_ubicaciones()
    if datos.ARCHIVO_OSRM.exists() and not forzar:
        print(f"Ya existe {datos.ARCHIVO_OSRM.relative_to(RAIZ)}; uso --forzar para volver a bajarla.")
        osrm = datos.cargar_distancias("osrm")
        meta = json.loads(datos.ARCHIVO_META.read_text(encoding="utf-8"))
    else:
        print("Consultando OSRM...")
        osrm, enganche = consultar_osrm(ubic)
        osrm.round(3).to_csv(datos.ARCHIVO_OSRM)
        meta = {
            "fecha_consulta": date.today().isoformat(),
            "servicio": URL_OSRM.split("{")[0],
            "perfil": "driving (auto; OSRM público no tiene perfil de camión)",
            "enganche_m": enganche.round(1).to_dict(),
        }

    hav = datos.matriz_haversine(ubic)
    hav.round(3).to_csv(datos.ARCHIVO_HAVERSINE)

    # Factor de ruta sobre los arcos que usa el modelo (y los de Goyito, pregunta c).
    arcos = datos.arcos_del_modelo(ubic)
    ratio = pd.Series({(o, d): osrm.loc[o, d] / hav.loc[o, d] for o, d in arcos})
    meta["factor_ruta"] = round(float(ratio.median()), 4)
    meta["factor_ruta_p10_p90"] = [round(float(ratio.quantile(q)), 4) for q in (0.1, 0.9)]
    meta["arcos_factor"] = len(arcos)
    datos.ARCHIVO_META.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Puntos: {len(ubic)}  ·  arcos del modelo: {len(arcos)}")
    print(f"Factor de ruta (mediana OSRM / haversine): {meta['factor_ruta']:.3f}"
          f"  (p10–p90: {meta['factor_ruta_p10_p90'][0]:.3f}–{meta['factor_ruta_p10_p90'][1]:.3f})")
    asim = (osrm - osrm.T).abs().to_numpy().max()
    print(f"Asimetría máxima de OSRM (ida vs. vuelta): {asim:.2f} km")
    print(f"Enganche máximo a la red de calles: {max(meta['enganche_m'].values()):.0f} m")
    print(f"Guardado en {datos.ARCHIVO_OSRM.parent.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main(forzar="--forzar" in sys.argv)
