"""
Verificación de los datos cargados contra la consigna y las tablas calculadas a mano.

Se corre ANTES de optimizar. Un artículo mal tipeado en un combo produce un óptimo
perfectamente plausible y completamente equivocado; estos chequeos lo detectan.

Los valores esperados son los del docs/plan_de_trabajo.md §3.2 a §3.6.

    python scripts/00_verificar_datos.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):  # consola de Windows en cp1252
    sys.stdout.reconfigure(encoding="utf-8")

from src import datos  # noqa: E402
from src.config import construir_params  # noqa: E402

#: (descripción, valor obtenido, valor esperado, ok)
CHEQUEOS = []


def chequear(descripcion, obtenido, esperado):
    CHEQUEOS.append((descripcion, obtenido, esperado, obtenido == esperado))


def main():
    params = construir_params()
    combos = params["combos"]
    catalogo = set(datos.productos(params))

    # --- Composición de los combos (plan §3.2) -------------------------------
    chequear("Cantidad de combos", len(combos), 20)
    chequear("Cantidad de artículos del catálogo", len(catalogo), 30)
    chequear(
        "Artículos de los combos que no existen en el catálogo",
        sorted({p for arts in combos.values() for p in arts} - catalogo),
        [],
    )
    chequear(
        "Combos que repiten categoría",
        [c for c, arts in combos.items() if len({datos.categoria(p) for p in arts}) != len(arts)],
        [],
    )
    chequear(
        "Combos a los que les falta B, L, A, M, G o C",
        [c for c, arts in combos.items() if not set("BLAMGC") <= {datos.categoria(p) for p in arts}],
        [],
    )
    chequear(
        "Combos sin empapelado",
        [c for c, arts in combos.items() if "E" not in {datos.categoria(p) for p in arts}],
        [12, 13],
    )
    chequear(
        "Combos sin lavavajillas",
        [c for c, arts in combos.items() if "W" not in {datos.categoria(p) for p in arts}],
        list(range(14, 21)),
    )
    chequear("Combos de 8 artículos", sum(len(a) == 8 for a in combos.values()), 11)
    chequear("Combos de 7 artículos", sum(len(a) == 7 for a in combos.values()), 9)

    # --- Tabla derivada 1: apariciones (plan §3.4) ---------------------------
    ap = datos.apariciones(params)
    esperado_ap = {
        "B1": 5, "B2": 7, "B3": 4, "B4": 4,
        "E1": 4, "E2": 6, "E3": 5, "E4": 3,
        "L1": 6, "L2": 4, "L3": 5, "L4": 5,
        "A1": 7, "A2": 4, "A3": 6, "A4": 3,
        "M1": 5, "M2": 5, "M3": 5, "M4": 5,
        "G1": 5, "G2": 6, "G3": 4, "G4": 5,
        "W1": 8, "W2": 5,
        "C1": 5, "C2": 5, "C3": 6, "C4": 4,
    }  # fmt: skip
    for p, esperado in esperado_ap.items():
        chequear(f"Apariciones de {p}", ap[p], esperado)
    chequear("Suma de apariciones (11x8 + 9x7)", sum(ap.values()), 151)
    chequear("Artículos que no aparecen en ningún combo", [p for p, n in ap.items() if n == 0], [])
    chequear("Combos de B2 (ejemplo de R1 del plan §7)", datos.combos_que_usan(params)["B2"], [1, 6, 8, 12, 18, 19, 20])

    # --- Tabla derivada 2: lugares por combo (plan §3.5) ---------------------
    lugares = datos.lugares_por_combo(params)
    chequear(
        "Lugares de lavav.+cocinas, combos 1 a 13",
        {lugares[c]["lavav_cocinas"] for c in range(1, 14)},
        {2},
    )
    chequear(
        "Lugares de lavav.+cocinas, combos 14 a 20",
        {lugares[c]["lavav_cocinas"] for c in range(14, 21)},
        {1},
    )

    # --- Capacidades y tabla derivada 3: cota trivial (plan §3.3 y §3.6) -----
    chequear("Capacidad total del depósito", sum(d["capacidad"] for d in params["espacios"].values()), 33)
    chequear(
        "Cota trivial por espacio",
        datos.cota_trivial(params),
        {
            "baldosas": 5,
            "empapelado": None,
            "apliques": 4,
            "alacenas": 4,
            "mesadas": 3,
            "bachas": 4,
            "lavav_cocinas": 5,
        },
    )

    # --- Salida -------------------------------------------------------------
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
