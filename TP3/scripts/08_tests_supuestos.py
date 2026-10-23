"""
Tests de supuestos (plan §13, tarea T22). Se cambia UN supuesto por vez con
`construir_params(...)`, se re-resuelve el modelo entero y se compara con el caso base.

    A  S1  distancias           OSRM -> línea recta × factor de ruta
    B  S2  centro principal     exactamente uno -> al menos uno (permite A y B juntos)
    C  S8  pallets por camión   26 -> 20 a 30
    D  S10 tarifa               solo ida -> ida y vuelta
    E  S11 conductores          W ± 30 %; K_max de 6.000 a 12.000 km
    F  S13 precio del carbono   0 -> USD 10, 50 y 100 por t (al dólar BNA)
    G  §7.1 apertura            mensual (× 1) -> × 0,05 a × 2 (pendiente P1: inversión amortizada)

Además verifica propiedades que cualquier resultado correcto tiene que cumplir (plan §13).

Salida: resultados/tablas/17_tests_supuestos.csv y resultados/graficos/12_tests_supuestos.png.

    python scripts/08_tests_supuestos.py
"""

import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
if hasattr(sys.stdout, "reconfigure"):  # consola de Windows en cp1252
    sys.stdout.reconfigure(encoding="utf-8")

from src import graficos, modelo, reportes  # noqa: E402
from src.config import SUPUESTOS, construir_params  # noqa: E402

TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"
DOLAR_BNA = 1_550                     # $ por USD, BNA venta 23/10/2026 (igual que 05_punto_c.py)
TOL = 1.0                             # $ de tolerancia para comparar costos (ruido de CBC)

W0, K0 = SUPUESTOS["W"], SUPUESTOS["K_max"]

#: (test, supuesto, descripción del valor, {overrides})
TESTS = [
    ("A", "S1 Distancias", "Línea recta × factor de ruta", {"distancias": "haversine"}),
    ("B", "S2 Centro principal", "Al menos uno de A y B", {"principal": "al_menos_uno"}),
    *[("C", "S8 Pallets por camión", f"Q = {q}", {"Q": q}) for q in (20, 22, 24, 28, 30)],
    ("D", "S10 Tarifa del tercerizado", "Sobre ida y vuelta", {"tarifa_ida_vuelta": True}),
    *[("E", "S11 Sueldo del conductor", f"W {'−' if f < 1 else '+'}30 %", {"W": round(W0 * f)}) for f in (0.7, 1.3)],
    *[("E", "S11 km por conductor", f"K_max = {k:,}".replace(",", "."), {"K_max": k})
      for k in (6_000, 7_000, 9_000, 10_000, 12_000)],
    *[("F", "S13 Precio del carbono", f"USD {u} por t", {"precio_co2": u * DOLAR_BNA / 1_000}) for u in (10, 50, 100)],
    *[("G", "§7.1 Costo de apertura", f"× {f:g}".replace(".", ","), {"factor_apertura": f})
      for f in (0.05, 0.1, 0.25, 0.5, 2.0)],
]


def pesos(x):
    return f"$ {x:,.0f}".replace(",", ".")


def numero(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main():
    base = modelo.resolver(construir_params())
    assert base["estado"] == "Optimal"
    filas = [{"test": "—", "supuesto": "Caso base", "alternativa": "Valores adoptados",
              **reportes.fila_resumen(base)}]
    resultados = {}
    for test, supuesto, alternativa, cambios in TESTS:
        r = modelo.resolver(construir_params(**cambios))
        assert r["estado"] == "Optimal", f"{test} {alternativa}: {r['estado']}"
        resultados[test, alternativa] = r
        filas.append({"test": test, "supuesto": supuesto, "alternativa": alternativa, **reportes.fila_resumen(r)})
    tabla = pd.DataFrame(filas)
    # Costo sin el término del carbono: el test F suma ese término al funcional y no es un gasto.
    tabla["costo_sin_carbono"] = tabla["costo_total"] - tabla["costo_carbono"]
    tabla["variacion_costo_pct"] = 100 * (tabla["costo_sin_carbono"] / base["costo"] - 1)
    tabla["variacion_co2_pct"] = 100 * (tabla["co2_kg"] / base["co2_kg"] - 1)
    tabla["cambia_configuracion"] = tabla["configuracion"] != base["configuracion"]

    # --- Propiedades (plan §13) ---------------------------------------------------------------
    def fila(test, alternativa):
        return tabla[(tabla["test"] == test) & (tabla["alternativa"] == alternativa)].iloc[0]

    props = []

    def prop(descripcion, condicion):
        props.append((descripcion, bool(condicion)))

    prop("Relajar S2 (test B) nunca sube el costo", fila("B", "Al menos uno de A y B")["costo_total"] <= base["costo"] + TOL)
    q = tabla[tabla["test"] == "C"].assign(Q=[20, 22, 24, 28, 30])
    q = pd.concat([q, pd.DataFrame([{"Q": 26, "costo_total": base["costo"]}])]).sort_values("Q")
    prop("Más pallets por camión nunca suben el costo", q["costo_total"].diff().dropna().le(TOL).all())
    prop("Cobrar la tarifa ida y vuelta nunca baja el costo",
         fila("D", "Sobre ida y vuelta")["costo_total"] >= base["costo"] - TOL)
    f_ = tabla[tabla["test"] == "F"]
    prop("Con precio del carbono, el CO₂ del óptimo nunca sube", (f_["co2_kg"] <= base["co2_kg"] + 1e-3).all())
    prop("Más precio del carbono, CO₂ no creciente", f_["co2_kg"].diff().dropna().le(1e-3).all())
    k = tabla[tabla["supuesto"] == "S11 km por conductor"].assign(K=[6_000, 7_000, 9_000, 10_000, 12_000])
    k = pd.concat([k, pd.DataFrame([{"K": K0, "costo_total": base["costo"]}])]).sort_values("K")
    prop("Más km por conductor nunca suben el costo", k["costo_total"].diff().dropna().le(TOL).all())
    w = tabla[tabla["supuesto"] == "S11 Sueldo del conductor"]
    prop("Más sueldo nunca baja el costo", w["costo_total"].iloc[0] <= base["costo"] + TOL <= w["costo_total"].iloc[1] + 2 * TOL)
    g = tabla[tabla["test"] == "G"].assign(F=[0.05, 0.1, 0.25, 0.5, 2.0])
    g = pd.concat([g, pd.DataFrame([{"F": 1.0, "costo_total": base["costo"]}])]).sort_values("F")
    prop("Más costo de apertura nunca baja el costo", g["costo_total"].diff().dropna().ge(-TOL).all())
    for descripcion, ok in props:
        assert ok, descripcion

    reportes.guardar({"17_tests_supuestos": tabla}, TABLAS)
    GRAFICOS.mkdir(parents=True, exist_ok=True)
    graficos.tests_supuestos(tabla, base, GRAFICOS / "12_tests_supuestos.png")

    print("=" * 78)
    print("TESTS DE SUPUESTOS — un supuesto por vez, modelo entero re-resuelto")
    print("=" * 78)
    for f in tabla.itertuples():
        marca = " ← cambia" if f.cambia_configuracion else ""
        print(f"  {f.test:<2}{f.supuesto:<28}{f.alternativa:<30}{f.configuracion:<8}{pesos(f.costo_sin_carbono):>15}"
              f" ({numero(f.variacion_costo_pct, 1):>6} %)  CO₂ {numero(f.co2_kg):>7} ({numero(f.variacion_co2_pct, 1):>5} %)"
              f"  cond. {f.conductores:>2}{marca}")
    print("\nPropiedades:")
    for descripcion, ok in props:
        print(f"  [{'OK ' if ok else 'MAL'}] {descripcion}")
    print(f"\nTabla en {TABLAS.relative_to(RAIZ)}/17_tests_supuestos.csv, gráfico 12_tests_supuestos.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
