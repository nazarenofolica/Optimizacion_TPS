"""
Verificación de los datos derivados contra los valores calculados a mano.

Se corre ANTES de optimizar. Un error de carga en una tabla (un share mal tipeado,
un gasto con un cero de más) produce un óptimo perfectamente plausible y
completamente equivocado; estos asserts lo detectan al instante.

Los valores esperados son los del docs/plan_de_trabajo.md §3.4 a §3.7 y §6.2 a §6.4.

    python scripts/00_verificar_datos.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):  # consola de Windows en cp1252
    sys.stdout.reconfigure(encoding="utf-8")

from src import datos  # noqa: E402
from src.config import construir_params  # noqa: E402

TOL = 0.01  # $MM  — tolerancia de comparación

#: (descripción, valor obtenido, valor esperado)
CHEQUEOS = []


def chequear(descripcion, obtenido, esperado, tol=TOL):
    CHEQUEOS.append((descripcion, obtenido, esperado, abs(obtenido - esperado) <= tol))


def main():
    params = construir_params()

    # --- Tabla derivada 1: mercado por segmento (plan §3.4) -----------------
    mercado = datos.mercado_por_segmento(params)
    chequear("Mercado bajo ($MM)", mercado["bajo"], 881_500)
    chequear("Mercado medio ($MM)", mercado["medio"], 614_800)
    chequear("Mercado alto ($MM)", mercado["alto"], 160_800)
    chequear("Mercado total ($MM)", datos.mercado_total(params), 1_657_100)

    # --- Tabla derivada 2: facturación base (plan §3.5) ---------------------
    base = datos.facturacion_base(params)
    chequear("Fact. base Don Carlo ($MM)", base["DC"], 320_821)
    chequear("Fact. base Agnellis ($MM)", base["AG"], 192_626)
    chequear("Fact. base Triguetti ($MM)", base["TRI"], 186_048)
    chequear("Fact. base Candealix ($MM)", base["CAN"], 78_600)
    chequear("Fact. base Rena Speziale ($MM)", base["RS"], 19_012)
    chequear("Fact. base total ($MM)", sum(base.values()), 797_107)
    chequear(
        "Market share inicial (%)",
        100 * sum(base.values()) / datos.mercado_total(params),
        48.1025,  # 797.107 / 1.657.100
        tol=0.001,
    )

    # --- Tabla derivada 3: cupo de la gama baja (plan §7.1) -----------------
    chequear("Cupo gama baja (clientes)", datos.cupo_gama_baja(params), 2_580_000, tol=1)

    # --- Tabla derivada 4: coeficientes del funcional (plan §6.2 a §6.4) ----
    fxm = datos.facturacion_por_millon(params)
    esperado_fact = {
        ("DC", 1): 16.40,
        ("AG", 1): 20.50,
        ("TRI", 1): 11.60,
        ("TRI", 2): 0.00,
        ("CAN", 1): 17.40,
        ("CAN", 2): 11.60,
        ("RS", 1): 20.10,
        ("RS", 2): 13.40,
    }
    for clave, valor in esperado_fact.items():
        chequear(f"Facturación/$MM {clave[0]}{clave[1]}", fxm[clave], valor, tol=1e-9)

    neta = datos.coeficientes(params, "neta")
    esperado_neta = {
        ("DC", 1): 0.8200,
        ("AG", 1): 1.5375,
        ("TRI", 1): 1.0440,
        ("TRI", 2): 0.0000,
        ("CAN", 1): 1.3920,
        ("CAN", 2): 0.9280,
        ("RS", 1): 2.0100,
        ("RS", 2): 1.3400,
    }
    for clave, valor in esperado_neta.items():
        chequear(f"Coef. utilidad neta {clave[0]}{clave[1]}", neta[clave], valor, tol=1e-9)

    # --- Términos constantes del funcional (plan §6.1) ----------------------
    chequear(
        "Término constante Z_neta ($MM)",
        datos.termino_constante(params, "neta"),
        55_421.52,
    )
    chequear(
        "Término constante Z_oper ($MM)",
        datos.termino_constante(params, "oper"),
        80_740.39,
    )
    chequear(
        "Término constante Z_facturación ($MM)",
        datos.termino_constante(params, "facturacion"),
        797_107,
    )

    # --- Salida -------------------------------------------------------------
    ancho = max(len(d) for d, *_ in CHEQUEOS)
    print("=" * (ancho + 40))
    print("VERIFICACIÓN DE DATOS DERIVADOS")
    print("=" * (ancho + 40))
    fallidos = 0
    for descripcion, obtenido, esperado, ok in CHEQUEOS:
        marca = "OK " if ok else "MAL"
        print(f"[{marca}] {descripcion:<{ancho}}  {obtenido:>14,.4f}  (esp. {esperado:>12,.4f})")
        fallidos += not ok

    print("-" * (ancho + 40))
    if fallidos:
        print(f"FALLARON {fallidos} de {len(CHEQUEOS)} verificaciones.")
        return 1
    print(f"Las {len(CHEQUEOS)} verificaciones pasaron.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
