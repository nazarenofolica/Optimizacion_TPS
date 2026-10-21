"""
Análisis de sensibilidad (informe b, plan §10, tareas T16 y T17).

    1. PL de flujos con la configuración óptima fija, en HiGHS (src/sensibilidad.py):
       b.i  rangos de lado derecho y precios sombra      -> 09_rangos_lado_derecho.csv
       b.ii rangos de costos de los arcos usados         -> 10_rangos_costos.csv
            costos reducidos de los arcos sin usar       -> 11_costos_reducidos.csv
    2. Control cruzado: se cambia el DATO en el modelo de PuLP y se re-resuelve, para comprobar
       que los precios y rangos de HiGHS dicen lo mismo     -> 11b_control_cruzado.csv
    3. Barridos que pueden cambiar la configuración: se re-resuelve el modelo entero
       (tarifa T, Q, apertura, demanda)                     -> 12_barridos.csv, 04_barridos.png

    python scripts/03_sensibilidad.py
"""

import copy
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
if hasattr(sys.stdout, "reconfigure"):  # consola de Windows en cp1252
    sys.stdout.reconfigure(encoding="utf-8")

from src import graficos, modelo, reportes, sensibilidad  # noqa: E402
from src.config import construir_params  # noqa: E402

TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"
TOL_REL = 1e-6

#: Barridos del plan §10.4: (supuesto, valores, etiqueta para el gráfico).
BARRIDOS = [
    ("tarifa_T", list(range(250, 1001, 50)), "Tarifa del tercerizado [$/km]"),
    ("Q", list(range(20, 31)), "Pallets por camión (Q)"),
    ("factor_apertura", [round(x, 2) for x in np.arange(0.5, 2.01, 0.1)], "Costo de apertura (× consigna)"),
    ("factor_demanda", [round(x, 2) for x in np.arange(0.8, 1.301, 0.02)], "Demanda (× consigna)"),
]


def pesos(x):
    return f"$ {x:,.0f}".replace(",", ".")


def numero(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------------------
# Control cruzado: cambiar el dato en PuLP y re-resolver (independiente del ranging)
# ---------------------------------------------------------------------------


def costo_pl_pulp(params, base):
    """Costo del PL de flujos (y*, n* fijos) re-resuelto con PuLP/CBC para `params`."""
    res = modelo.resolver(params, config_fija=base["centros"], fijar_n=base["conductores"], fuerte=False)
    return res["costo"] if res["estado"] == "Optimal" else float("nan")


def control_cruzado(params, base, h, rhs, rc):
    filas = []
    c0 = costo_pl_pulp(params, base)

    def caso(descripcion, modificar, delta, esperado, comparar="igual"):
        p = copy.deepcopy(params)
        modificar(p)
        obtenido = (costo_pl_pulp(p, base) - c0) / delta
        ok = abs(obtenido - esperado) <= 0.01 + 1e-6 * abs(esperado) if comparar == "igual" \
            else abs(obtenido - esperado) > 0.01
        filas.append({"caso": descripcion, "esperado_highs": esperado, "obtenido_pulp": obtenido,
                      "criterio": comparar, "ok": ok})

    r = rhs.set_index("restriccion")
    cap_d = r.loc["CAP_D"]
    dentro = 0.9 * (cap_d["rango_max"] - cap_d["valor_actual"])
    fuera = 1.5 * (cap_d["rango_max"] - cap_d["valor_actual"])
    caso(f"Capacidad de D +{numero(dentro)} (dentro del rango): Δcosto/pallet",
         lambda p: p["centros"]["D"].__setitem__("capacidad", p["centros"]["D"]["capacidad"] + dentro),
         dentro, cap_d["precio_sombra"])
    caso(f"Capacidad de D +{numero(fuera)} (fuera del rango): el precio cambia",
         lambda p: p["centros"]["D"].__setitem__("capacidad", p["centros"]["D"]["capacidad"] + fuera),
         fuera, cap_d["precio_sombra"], comparar="distinto")

    cond = r.loc["CONDUCTORES"]
    km = 0.9 * (cond["rango_max"] - cond["valor_actual"])
    n = base["conductores"]
    caso(f"km de conductores +{numero(km)} (dentro del rango): Δcosto/km",
         lambda p: p["supuestos"].__setitem__("K_max", p["supuestos"]["K_max"] + km / n),
         km, cond["precio_sombra"])

    for fila in ("DEM_S9_Leche", "DEM_S8_Fideos"):
        d = r.loc[fila]
        _, i, k = fila.split("_")
        # ±5 pallets (dentro del rango): con ±1 el ruido de CBC sobre $56 M pesa demasiado.
        caso(f"Demanda de {k} en {i} +5: costo por pallet extra",
             lambda p, i=i, k=k: p["demanda"].__setitem__((i, k), p["demanda"][i, k] + 5), 5, d["precio_subir"])
        caso(f"Demanda de {k} en {i} −5: ahorro por pallet (precio sombra de HiGHS)",
             lambda p, i=i, k=k: p["demanda"].__setitem__((i, k), p["demanda"][i, k] - 5), -5, d["precio_sombra"])

    # Rango de costo de un arco: dentro del rango la solución no cambia; afuera, sí (en HiGHS,
    # cambiando el coeficiente y re-resolviendo).
    arco = rc[(rc["origen"] == "P_Galletitas_1") & (rc["destino"] == "C")].iloc[0]
    lp = h.getLp()
    nombres = [h.getColName(j)[1] for j in range(lp.num_col_)]
    col = nombres.index("x_P_Galletitas_1_C")
    x0 = np.array(h.getSolution().col_value)
    costo_orig = lp.col_cost_[col]
    for etiqueta, nuevo, debe_cambiar in (
        ("dentro", arco["costo_max"] - 0.05 * arco["puede_subir"], False),
        ("fuera", arco["costo_max"] + 0.05 * arco["puede_subir"] + 1, True),
    ):
        h.changeColCost(col, nuevo)
        h.run()
        cambio = not np.allclose(np.array(h.getSolution().col_value), x0, atol=1e-6)
        filas.append({"caso": f"Costo Galletitas 1 → C = {numero(nuevo, 1)} ({etiqueta} del rango): "
                              "¿cambian los flujos?",
                      "esperado_highs": float(debe_cambiar), "obtenido_pulp": float(cambio),
                      "criterio": "igual", "ok": cambio == debe_cambiar})
    h.changeColCost(col, costo_orig)
    h.run()
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Barridos (re-resolución del modelo entero)
# ---------------------------------------------------------------------------


def barridos():
    filas = []
    for supuesto, valores, _ in BARRIDOS:
        for v in valores:
            res = modelo.resolver(construir_params(**{supuesto: v}))
            if res["estado"] != "Optimal":
                filas.append({"parametro": supuesto, "valor": v, "estado": res["estado"],
                              "configuracion": "infactible"})
                continue
            filas.append({"parametro": supuesto, "valor": v, "estado": res["estado"],
                          **reportes.fila_resumen(res)})
    return pd.DataFrame(filas)


def _configuracion(supuesto, valor):
    res = modelo.resolver(construir_params(**{supuesto: valor}))
    return res["configuracion"] if res["estado"] == "Optimal" else "infactible"


def umbral(supuesto, a, b, conf_a, iteraciones=14):
    """Bisección: valor entre a y b donde la configuración deja de ser `conf_a`."""
    for _ in range(iteraciones):
        m = (a + b) / 2
        if supuesto == "Q":  # Q es entero
            m = round(m)
            if m in (a, b):
                break
        if _configuracion(supuesto, m) == conf_a:
            a = m
        else:
            b = m
    return (a + b) / 2


def cambios(tabla):
    """Valores del barrido en que cambia la configuración óptima, con el umbral afinado."""
    filas = []
    for parametro, g in tabla.groupby("parametro", sort=False):
        g = g.sort_values("valor")
        previa = None
        for f in g.itertuples():
            if previa is not None and f.configuracion != previa.configuracion:
                filas.append({"parametro": parametro, "desde": previa.valor, "hasta": f.valor,
                              "umbral": umbral(parametro, previa.valor, f.valor, previa.configuracion),
                              "antes": previa.configuracion, "despues": f.configuracion})
            previa = f
    return pd.DataFrame(filas)


def main():
    params = construir_params()
    base = modelo.resolver(params)
    assert base["estado"] == "Optimal"

    # --- 1. PL de flujos en HiGHS -------------------------------------------------
    h, _ = sensibilidad.resolver_pl(params, base)
    costo_highs = sensibilidad.costo_pl(h)
    assert abs(costo_highs - base["costo"]) <= TOL_REL * base["costo"], (costo_highs, base["costo"])
    rhs = sensibilidad.rangos_lado_derecho(h, params, base)
    rc = sensibilidad.rangos_costos(h, base)
    cr = sensibilidad.costos_reducidos(h, base)

    # --- 2. Control cruzado ------------------------------------------------------------
    control = control_cruzado(params, base, h, rhs, rc)
    assert control["ok"].all(), control[~control["ok"]]

    # --- 3. Barridos -------------------------------------------------------------------
    barr = barridos()
    camb = cambios(barr)

    reportes.guardar({
        "09_rangos_lado_derecho": rhs,
        "10_rangos_costos": rc,
        "11_costos_reducidos": cr,
        "11b_control_cruzado": control,
        "12_barridos": barr,
        "12b_cambios_configuracion": camb,
    }, TABLAS)
    graficos.barridos(barr, BARRIDOS, {s: params["supuestos"][s] for s, *_ in BARRIDOS}, camb,
                      GRAFICOS / "04_barridos.png")

    # --- Resumen en consola --------------------------------------------------------------
    print("=" * 78)
    print("SENSIBILIDAD — PL de flujos con A+C+D y 6 conductores fijos")
    print("=" * 78)
    print(f"Costo HiGHS = {pesos(costo_highs)}  (PuLP/CBC: {pesos(base['costo'])})\n")
    print("b.i  Recursos (precio = cambio del costo por una unidad MÁS del recurso):")
    for f in rhs[~rhs["restriccion"].str.startswith("DEM")].itertuples():
        rango = f"[{numero(f.rango_min)}, {'∞' if np.isinf(f.rango_max) else numero(f.rango_max)}]"
        print(f"  {f.recurso:<34} usado {numero(f.usado):>7} de {numero(f.valor_actual):>7}"
              f"   precio {numero(f.precio_sombra, 1):>8}   rango {rango}")
    dem = rhs[rhs["restriccion"].str.startswith("DEM")]
    asim = (dem["precio_subir"] - dem["precio_bajar"]).abs() > 0.01
    print(f"\n  Demanda (50 pares súper–producto): un pallet más cuesta entre "
          f"{pesos(dem['precio_sombra'].min())} y {pesos(dem['precio_sombra'].max())}"
          f"  ·  pares con precio distinto al subir y al bajar: {asim.sum()}")
    print(f"\nb.ii Arcos usados: {len(rc)}  ·  sin margen para subir: {(rc['puede_subir'] < 1e-6).sum()}"
          f"  ·  arcos sin uso con costo reducido 0 (óptimos alternativos): {(cr['costo_reducido'].abs() < 1e-6).sum()}")
    print("\nControl cruzado (dato cambiado en PuLP vs. HiGHS):")
    for f in control.itertuples():
        print(f"  [{'OK ' if f.ok else 'MAL'}] {f.caso}: HiGHS {numero(f.esperado_highs, 2)}  ·  "
              f"re-resuelto {numero(f.obtenido_pulp, 2)}")
    print("\nBarridos — cambios de configuración:")
    if camb.empty:
        print("  ninguno: A+C+D es óptima en todos los valores barridos")
    for f in camb.itertuples():
        print(f"  {f.parametro} = {numero(f.umbral, 3)}:  {f.antes} → {f.despues}")
    print(f"\nTablas en {TABLAS.relative_to(RAIZ)}, gráfico 04_barridos.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
