"""
Verificación de los datos cargados contra la consigna y las cuentas hechas a mano.

Se corre ANTES de optimizar. Una demanda mal tipeada o un punto del mapa mal clasificado
producen un óptimo perfectamente plausible y completamente equivocado; estos chequeos lo detectan.

Los valores esperados son los del docs/plan_de_trabajo.md §2 y §4. Además guarda la tabla de
coeficientes por arco (resultados/tablas/01_costo_por_pallet_arco.csv).

    python scripts/00_verificar_datos.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
if hasattr(sys.stdout, "reconfigure"):  # consola de Windows en cp1252
    sys.stdout.reconfigure(encoding="utf-8")

from src import datos  # noqa: E402
from src.config import construir_params  # noqa: E402

CARPETA_TABLAS = RAIZ / "resultados" / "tablas"

#: (descripción, valor obtenido, valor esperado, ok)
CHEQUEOS = []


def chequear(descripcion, obtenido, esperado):
    CHEQUEOS.append((descripcion, obtenido, esperado, obtenido == esperado))


def falla_con(excepcion, funcion, **kwargs):
    """True si `funcion(**kwargs)` levanta `excepcion`."""
    try:
        funcion(**kwargs)
    except excepcion:
        return True
    except Exception:  # noqa: BLE001 — otra excepción también es un error del chequeo
        return False
    return False


def main():
    params = construir_params()
    ubic = datos.cargar_ubicaciones()

    # --- Demanda (plan §2.3) --------------------------------------------------
    chequear("Demanda total [pallets/mes]", sum(params["demanda"].values()), 51_850)
    chequear(
        "Demanda por producto",
        datos.demanda_por_producto(params).to_dict(),
        {"Fideos": 20_300, "Arroz": 8_550, "Leche": 9_950, "Gaseosas": 4_550, "Galletitas": 8_500},
    )
    chequear(
        "Demanda por supermercado (fila Total)",
        list(datos.demanda_por_super(params)),
        [4_850, 4_900, 4_850, 5_690, 5_490, 5_850, 4_450, 5_250, 5_170, 5_350],
    )

    # --- Ubicaciones (plan §2.4) -------------------------------------------------
    chequear(
        "Puntos del mapa por tipo",
        ubic["tipo"].value_counts().to_dict(),
        {"supermercado": 10, "centro": 4, "planta": 7},
    )
    chequear("Supermercados del mapa = los de la demanda", datos.ids(ubic, "supermercado"), list(params["supermercados"]))
    chequear("Centros del mapa = los de la consigna", datos.ids(ubic, "centro"), list(params["centros"]))
    chequear(
        "Plantas por producto",
        {k: len(v) for k, v in datos.plantas_por_producto(ubic).items()},
        {"Arroz": 1, "Fideos": 2, "Galletitas": 1, "Gaseosas": 1, "Leche": 2},
    )
    chequear(
        "Coordenadas dentro del AMBA (lat -35..-34, lon -59..-58)",
        bool(ubic["lat"].between(-35, -34).all() and ubic["lon"].between(-59, -58).all()),
        True,
    )

    # --- Centros y transporte (plan §2.1 y §2.2) -------------------------------
    chequear(
        "Centros: (capacidad, apertura, costo por pallet)",
        {j: (c["capacidad"], c["apertura"], c["costo_pallet"]) for j, c in params["centros"].items()},
        {
            "A": (40_000, 3_000_000, 10),
            "B": (35_000, 2_500_000, 12),
            "C": (15_000, 1_200_000, 5),
            "D": (10_000, 900_000, 8),
        },
    )
    chequear("Combustible del camión propio [$/km]", params["combustible_km"], 325)
    chequear("Ningún centro solo cubre la demanda (plan §4.1)",
             max(c["capacidad"] for c in params["centros"].values()) < 51_850, True)

    # --- Configuraciones (plan §4.2) --------------------------------------------
    # El plan suma el gerente dos veces en las de 3 centros (la columna "Apertura" ya lo incluye).
    # Valores corregidos: apertura + 2.000.000 de gerente (desvío D5 en procedimiento.md §2).
    fact = datos.configuraciones_factibles(params)
    chequear(
        "Configuraciones factibles con S2 y su costo fijo",
        dict(zip(fact["configuracion"], fact["fijo_total"])),
        {"A+C": 4_200_000, "B+C+D": 4_600_000 + 2_000_000, "A+C+D": 5_100_000 + 2_000_000},
    )
    fact_b = datos.configuraciones_factibles(construir_params(principal="al_menos_uno"))
    chequear(
        "Configuraciones factibles del test B (A y B juntos permitidos)",
        sorted(fact_b["configuracion"]),
        sorted(["A+C", "A+B", "B+C+D", "A+C+D", "A+B+C", "A+B+D", "A+B+C+D"]),
    )

    # --- Distancias (supuesto S1) -------------------------------------------------
    osrm = datos.cargar_distancias("osrm")
    hav = datos.matriz_haversine(ubic)
    chequear("Matriz OSRM 21 x 21 con los ids del mapa",
             (list(osrm.index), list(osrm.columns)), (list(ubic.index), list(ubic.index)))
    chequear("Diagonal de OSRM en cero", bool((np.diag(osrm.to_numpy()) == 0).all()), True)
    fuera = ~np.eye(len(osrm), dtype=bool)
    chequear("Sin ceros fuera de la diagonal", bool((osrm.to_numpy()[fuera] > 0).all()), True)
    chequear("Ruta >= línea recta en todos los pares",
             bool((osrm.to_numpy()[fuera] >= hav.to_numpy()[fuera]).all()), True)
    asim = (osrm - osrm.T).abs().to_numpy().max()
    chequear("Asimetría ida/vuelta menor a 10 km", bool(asim < 10), True)
    chequear("Haversine x factor de ruta",
             bool(np.allclose(datos.cargar_distancias("haversine"), hav * datos.factor_ruta())), True)

    # --- Coeficientes por pallet (plan §6.2) ---------------------------------------
    # El ejemplo del plan: 30 km en el tramo 1 y 30 km (60 ida y vuelta) en el tramo 2.
    chequear("Ejemplo §6.2, tramo 1: 500 x 30 / 26",
             round(datos.costo_tramo1_tercerizado(params, 30, 60), 2), 576.92)
    chequear("Ejemplo §6.2, tramo 2: 325 x 60 / 26", round(datos.costo_propio(params, 60), 2), 750.0)
    # Un arco calculado a mano desde el CSV crudo: A -> S1.
    crudo = pd.read_csv(datos.ARCHIVO_OSRM, index_col=0)
    a_mano = 325 * (crudo.at["A", "S1"] + crudo.at["S1", "A"]) / 26
    coef = datos.coeficientes_por_arco(params)
    fila = coef[(coef["origen"] == "A") & (coef["destino"] == "S1")].iloc[0]
    chequear("Arco A -> S1, combustible por pallet calculado a mano", round(fila["costo_propio"], 6), round(a_mano, 6))
    chequear("Arcos de la tabla (28 + 40 + 70)", coef["tramo"].value_counts().to_dict(),
             {"directo_goyito": 70, "2_centro_super": 40, "1_planta_centro": 28})
    chequear("Test D: tarifa ida y vuelta >= tarifa ida, en todos los arcos",
             bool((datos.coeficientes_por_arco(construir_params(tarifa_ida_vuelta=True))["costo_tercerizado"].fillna(0)
                   >= coef["costo_tercerizado"].fillna(0)).all()), True)

    # --- Validación de los supuestos (config.construir_params) -------------------
    chequear("Supuesto mal escrito -> KeyError", falla_con(KeyError, construir_params, Qq=20), True)
    chequear("Valor fuera de rango -> ValueError", falla_con(ValueError, construir_params, Q=0), True)
    chequear("Opción inexistente -> ValueError", falla_con(ValueError, construir_params, distancias="google"), True)

    # --- Salida ------------------------------------------------------------------
    CARPETA_TABLAS.mkdir(parents=True, exist_ok=True)
    coef.round(4).to_csv(CARPETA_TABLAS / "01_costo_por_pallet_arco.csv", index=False)

    ancho = max(len(d) for d, *_ in CHEQUEOS)
    print("=" * (ancho + 30))
    print("VERIFICACIÓN DE DATOS")
    print("=" * (ancho + 30))
    fallidos = 0
    for descripcion, obtenido, esperado, ok in CHEQUEOS:
        marca = "OK " if ok else "MAL"
        detalle = "" if ok else f"  obtenido={obtenido!r}  esperado={esperado!r}"
        print(f"[{marca}] {descripcion}{detalle}")
        fallidos += not ok

    print("-" * (ancho + 30))
    if fallidos:
        print(f"FALLARON {fallidos} de {len(CHEQUEOS)} verificaciones.")
        return 1
    print(f"Las {len(CHEQUEOS)} verificaciones pasaron.")
    print(f"Tabla de coeficientes: {(CARPETA_TABLAS / '01_costo_por_pallet_arco.csv').relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
