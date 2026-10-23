"""
Pregunta d): vehículos propios también desde los proveedores hasta el centro de distribución
(plan §12 d, tarea T20).

Es el mismo modelo con `escenario="d"`: el tramo planta -> centro deja de pagar la tarifa del
tercerizado ($ 500 por km de ida) y pasa a pagar combustible ($ 325 por km físico, ida y vuelta)
y conductores; sus km se suman a los que limita CONDUCTORES.

    1. Óptimo del escenario d) y comparación con a): costo, desglose, configuración, conductores,
       km, litros y CO2.
    2. Enumeración de configuraciones con flota propia (control, como en a).
    3. Costo por km físico de cada alternativa del tramo 1 (explica el resultado).

Salidas: resultados/tablas/15_comparacion_a_d.csv, 15b_configuraciones_d.csv y
resultados/graficos/07_comparacion_a_d.png, 08_mapa_flujos_d.png, 09_tabla_tramo1_d.png.

    python scripts/06_punto_d.py
"""

import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
if hasattr(sys.stdout, "reconfigure"):  # consola de Windows en cp1252
    sys.stdout.reconfigure(encoding="utf-8")

from src import datos, graficos, modelo, reportes  # noqa: E402
from src.config import construir_params  # noqa: E402

TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"
TOL_REL = 1e-6


def pesos(x):
    return f"$ {x:,.0f}".replace(",", ".")


def numero(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main():
    params = construir_params()
    ubic = datos.cargar_ubicaciones()
    s = params["supuestos"]

    a = modelo.resolver(params, escenario="a")
    d = modelo.resolver(params, escenario="d")
    assert a["estado"] == d["estado"] == "Optimal"

    # Controles: demanda cumplida, capacidad, y la restricción de conductores.
    f2 = d["flujos_tramo2"].groupby(["super", "producto"])["pallets"].sum()
    for (i, k), dem in params["demanda"].items():
        assert abs(f2.get((i, k), 0) - dem) < 1e-4, f"Demanda no cumplida en {i}, {k}"
    oc = d["ocupacion"]
    assert (oc["pallets"] <= oc["capacidad"] + 1e-4).all(), "Un centro supera su capacidad"
    assert d["km_propios"] <= s["K_max"] * d["conductores"] + 1e-4, "Conductores insuficientes"
    assert abs(d["km_propios"] - (d["km_tramo1"] + d["km_tramo2"])) < 1e-4, "En d) todo es flota propia"

    # Enumeración de configuraciones con flota propia (control).
    filas = []
    for conf in datos.configuraciones_factibles(params).itertuples():
        r = modelo.resolver(params, escenario="d", config_fija=conf.centros)
        assert r["estado"] == "Optimal"
        filas.append(reportes.fila_resumen(r))
    enum = pd.DataFrame(filas).sort_values("costo_total", ignore_index=True)
    assert enum.loc[0, "configuracion"] == d["configuracion"], "La enumeración elige otra configuración"
    assert abs(enum.loc[0, "costo_total"] - d["costo"]) <= TOL_REL * d["costo"]

    comp = pd.DataFrame([
        reportes.fila_resumen(a, escenario="a) Tercerizado + propio"),
        reportes.fila_resumen(d, escenario="d) Flota propia en los dos tramos"),
    ])
    comp.loc[2] = ["Diferencia d − a", "", *(comp.iloc[1, 2:].to_numpy() - comp.iloc[0, 2:].to_numpy())]
    comp["variacion_pct"] = [None, None, 100 * (d["costo"] / a["costo"] - 1)]

    # Costo por km físico del tramo 1 en cada alternativa.
    tercerizado_km_fisico = s["tarifa_T"] / 2                      # $ 500 por km de ida = 250 por km físico
    propio_km_fisico = params["combustible_km"] + s["W"] / s["K_max"]

    reportes.guardar({"15_comparacion_a_d": comp, "15b_configuraciones_d": enum}, TABLAS)
    GRAFICOS.mkdir(parents=True, exist_ok=True)
    graficos.comparacion_escenarios(
        comp.iloc[:2].assign(escenario=["a) Tercerizado", "d) Flota propia"]),
        "Flota propia también en el tramo planta → centro",
        "Costo por mes por rubro, total y emisiones · la configuración es A+C+D en los dos",
        GRAFICOS / "07_comparacion_a_d.png")
    graficos.mapa_asignacion(d, ubic, "Con flota propia: ¿qué centro abastece a cada supermercado?",
                             GRAFICOS / "08_mapa_flujos_d.png")
    graficos.tabla_tramo1(d, "Con flota propia: ¿de qué planta se abastece cada centro?",
                          GRAFICOS / "09_tabla_tramo1_d.png")

    print("=" * 78)
    print("PREGUNTA d) — FLOTA PROPIA TAMBIÉN DE LOS PROVEEDORES AL CENTRO")
    print("=" * 78)
    for nombre, r in (("a)", a), ("d)", d)):
        print(f"{nombre} {r['configuracion']}: {pesos(r['costo'])} · conductores {r['conductores']} · "
              f"{numero(r['km_total'])} km · {numero(r['litros'])} l · {numero(r['co2_kg'])} kg CO₂")
        for rubro, v in r["desglose"].items():
            if abs(v) > 1e-6:
                print(f"     {rubro:<22}{pesos(v):>16}")
    print(f"\nVariación d − a: costo {pesos(d['costo'] - a['costo'])} ({numero(100 * (d['costo'] / a['costo'] - 1), 1)} %),"
          f" km {numero(d['km_total'] - a['km_total'])} ({numero(100 * (d['km_total'] / a['km_total'] - 1), 1)} %),"
          f" CO₂ {numero(d['co2_kg'] - a['co2_kg'])} kg ({numero(100 * (d['co2_kg'] / a['co2_kg'] - 1), 1)} %)")
    print(f"\nTramo 1 por km físico: tercerizado {pesos(tercerizado_km_fisico)} · propio "
          f"{pesos(params['combustible_km'])} de combustible + {pesos(s['W'] / s['K_max'])} de conductor "
          f"= {pesos(propio_km_fisico)}")
    print("\nConfiguraciones con flota propia (control):")
    for f in enum.itertuples():
        print(f"  {f.configuracion:<7}{pesos(f.costo_total):>16}{numero(f.km_total):>10} km"
              f"{numero(f.co2_kg):>9} kg CO₂  conductores {f.conductores}")
    print(f"\nTablas en {TABLAS.relative_to(RAIZ)}, gráficos 07 a 09")
    return 0


if __name__ == "__main__":
    sys.exit(main())
