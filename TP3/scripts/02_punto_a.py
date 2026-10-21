"""
Pregunta a): localización óptima de los centros, minimizando el costo total, con indicadores
ambientales (plan §12 a, tareas T12 a T15).

    1. Óptimo del modelo entero (caso base).
    2. Enumeración de las configuraciones factibles con la configuración fija (control, plan §9).
    3. Frontera costo–CO2 por ε-restricción.
    4. Mapa de flujos.

Salidas en resultados/tablas (02 a 08) y resultados/graficos (01 a 03).

    python scripts/02_punto_a.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
if hasattr(sys.stdout, "reconfigure"):  # consola de Windows en cp1252
    sys.stdout.reconfigure(encoding="utf-8")

from src import datos, graficos, modelo, reportes  # noqa: E402
from src.config import construir_params  # noqa: E402

TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"
PUNTOS_FRONTERA = 30
TOL_REL = 1e-6


def pesos(x):
    return f"$ {x:,.0f}".replace(",", ".")


def numero(x):
    return f"{x:,.0f}".replace(",", ".")


def enumerar(params):
    """Resuelve el PL de flujos para cada configuración factible (plan §9)."""
    filas = []
    for conf in datos.configuraciones_factibles(params).itertuples():
        res = modelo.resolver(params, config_fija=conf.centros)
        assert res["estado"] == "Optimal", f"{conf.configuracion}: {res['estado']}"
        filas.append(reportes.fila_resumen(res))
    return pd.DataFrame(filas).sort_values("costo_total", ignore_index=True)


def frontera(params, base):
    """ε-restricción entre el mínimo CO2 y el CO2 del óptimo de costo (plan §12 a.4)."""
    extremo = modelo.resolver(params, objetivo="co2")
    co2_min = extremo["co2_kg"]
    filas = []
    for eps in np.linspace(co2_min, base["co2_kg"], PUNTOS_FRONTERA):
        # Holgura relativa mínima para que el extremo no quede infactible por redondeo.
        res = modelo.resolver(params, epsilon_co2=eps * (1 + TOL_REL))
        assert res["estado"] == "Optimal", f"ε={eps}: {res['estado']}"
        filas.append({"epsilon_kg": eps, **reportes.fila_resumen(res)})
    tabla = pd.DataFrame(filas)
    # Con n entera, muchos ε dan la misma solución: se deja un punto por solución distinta.
    tabla = (tabla.round({"co2_kg": 1, "costo_total": 0})
             .drop_duplicates(subset=["co2_kg", "costo_total"])
             .sort_values("co2_kg", ignore_index=True))
    tabla["co2_t"] = tabla["co2_kg"] / 1000
    tabla["costo_M"] = tabla["costo_total"] / 1e6
    return tabla, extremo


def main():
    params = construir_params()
    ubic = datos.cargar_ubicaciones()

    # --- 1. Óptimo ---------------------------------------------------------------
    base = modelo.resolver(params)
    assert base["estado"] == "Optimal", base["estado"]

    # Controles del óptimo (tarea T11).
    f2 = base["flujos_tramo2"].groupby(["super", "producto"])["pallets"].sum()
    for (i, k), d in params["demanda"].items():
        assert abs(f2.get((i, k), 0) - d) < 1e-4, f"Demanda no cumplida en {i}, {k}"
    oc = base["ocupacion"]
    assert (oc["pallets"] <= oc["capacidad"] + 1e-4).all(), "Un centro supera su capacidad"
    assert (oc.loc[~oc["abierto"], "pallets"] < 1e-4).all(), "Un centro cerrado mueve pallets"
    f1 = base["flujos_tramo1"].groupby("producto")["pallets"].sum()
    assert np.allclose(f1.reindex(params["productos"]).to_numpy(),
                       datos.demanda_por_producto(params).to_numpy()), "Balance de plantas"

    # --- 2. Enumeración (control, plan §9) ----------------------------------------
    enum = enumerar(params)
    minimo = enum.iloc[0]
    assert minimo["configuracion"] == base["configuracion"], "La enumeración elige otra configuración"
    assert abs(minimo["costo_total"] - base["costo"]) <= TOL_REL * base["costo"], "Costos distintos"

    # --- 3. Frontera costo–CO2 ---------------------------------------------------
    front, extremo = frontera(params, base)

    # --- 4. Tablas y gráficos --------------------------------------------------
    reportes.guardar({
        "02_configuraciones": enum,
        "03_flujos_tramo1": reportes.tabla_flujos_tramo1(base),
        "04_flujos_tramo2": reportes.tabla_flujos_tramo2(base),
        "05_ocupacion_centros": base["ocupacion"],
        "06_desglose_costos": reportes.tabla_desglose(base),
        "07_indicadores_ambientales": reportes.tabla_indicadores(base, params),
        "07b_asignacion_supers": reportes.tabla_asignacion(base),
        "08_frontera_costo_co2": front,
    }, TABLAS)
    GRAFICOS.mkdir(parents=True, exist_ok=True)
    graficos.frontera_costo_co2(front, GRAFICOS / "01_frontera_costo_co2.png")
    graficos.mapa_asignacion(base, ubic, "¿Qué centro abastece a cada supermercado?",
                             GRAFICOS / "02_mapa_flujos_a.png")
    graficos.tabla_tramo1(base, "¿De qué planta se abastece cada centro?",
                          GRAFICOS / "03_tabla_tramo1_a.png")

    # --- Resumen en consola --------------------------------------------------------
    print("=" * 78)
    print("PREGUNTA a) — LOCALIZACIÓN ÓPTIMA")
    print("=" * 78)
    print(f"Configuración óptima: {base['configuracion']}"
          f"  (gerente: {'sí' if base['gerente'] else 'no'}, conductores: {base['conductores']})")
    print(f"Costo total: {pesos(base['costo'])} por mes\n")
    print("Desglose:")
    for fila in reportes.tabla_desglose(base).itertuples():
        print(f"  {fila.rubro:<22}{pesos(fila.costo):>18}{fila.pct:>8.1f} %")
    print("\nOcupación de los centros:")
    for fila in base["ocupacion"].itertuples():
        estado = f"{numero(fila.pallets):>7} / {numero(fila.capacidad):>6}  ({fila.uso_pct:5.1f} %)" if fila.abierto else "cerrado"
        print(f"  {fila.centro}: {estado}")
    print("\nIndicadores ambientales:")
    for fila in reportes.tabla_indicadores(base, params).itertuples():
        print(f"  {fila.tramo:<24}{numero(fila.km):>9} km{numero(fila.litros):>9} l{numero(fila.co2_kg):>9} kg CO₂")
    print("\nConfiguraciones (control por enumeración, plan §9):")
    for fila in enum.itertuples():
        print(f"  {fila.configuracion:<7}{pesos(fila.costo_total):>18}{numero(fila.km_total):>9} km"
              f"{numero(fila.co2_kg):>9} kg CO₂   conductores {fila.conductores}")
    print(f"\nFrontera costo–CO₂: de {numero(extremo['co2_kg'])} kg ({extremo['configuracion']}, "
          f"{pesos(front.iloc[0]['costo_total'])}) a {numero(base['co2_kg'])} kg "
          f"({base['configuracion']}, {pesos(base['costo'])})")
    print(f"\nTablas en {TABLAS.relative_to(RAIZ)}, gráficos en {GRAFICOS.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
