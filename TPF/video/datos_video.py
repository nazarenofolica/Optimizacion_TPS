"""
Los datos reales que usan las animaciones, tomados de la base (datos/sepa/): las coordenadas de cada sucursal para el
mapa de la escena 2. Escribe salida/datos/sucursales.json ([lon, lat] por sucursal).

Uso (desde TPF/video):  python datos_video.py
"""

import json
from pathlib import Path

import pyarrow.parquet as pq

AQUI = Path(__file__).parent
SALIDA = AQUI / "salida" / "datos"


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    t = pq.read_table(AQUI.parent / "datos" / "sepa" / "dim_tienda.parquet", columns=["lat", "lon"]).to_pandas()
    t = t.dropna()
    puntos = [[round(lon, 3), round(lat, 3)] for lat, lon in zip(t["lat"], t["lon"])]
    (SALIDA / "sucursales.json").write_text(json.dumps(puntos), encoding="utf-8")
    print(len(puntos), "sucursales")


if __name__ == "__main__":
    main()
