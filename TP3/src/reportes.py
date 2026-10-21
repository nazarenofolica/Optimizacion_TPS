"""
Tablas de salida a partir del dict que devuelve modelo.resolver. Todas devuelven DataFrames;
`guardar` las escribe como CSV.
"""

from pathlib import Path

import pandas as pd

from src.modelo import RUBROS


def fila_resumen(res, **extra):
    """Una fila con lo principal de un resultado: configuración, costo, rubros e indicadores."""
    fila = dict(extra)
    fila.update({
        "configuracion": res["configuracion"],
        "costo_total": res["costo"],
        **{f"costo_{r}": res["desglose"][r] for r in RUBROS},
        "conductores": res["conductores"],
        "exceso_km": res["exceso_km"],
        "km_tramo1": res["km_tramo1"],
        "km_tramo2": res["km_tramo2"],
        "km_total": res["km_total"],
        "litros": res["litros"],
        "co2_kg": res["co2_kg"],
    })
    return fila


def tabla_desglose(res):
    """Costo por rubro, en $ y en % del total (solo rubros no nulos)."""
    filas = [{"rubro": r, "costo": v} for r, v in res["desglose"].items() if abs(v) > 1e-6]
    tabla = pd.DataFrame(filas)
    tabla["pct"] = 100 * tabla["costo"] / tabla["costo"].sum()
    total = pd.DataFrame([{"rubro": "TOTAL", "costo": tabla["costo"].sum(), "pct": 100.0}])
    return pd.concat([tabla, total], ignore_index=True)


def tabla_indicadores(res, params):
    """km, litros y kg de CO2 por tramo y total (plan S12)."""
    r, phi = params["rendimiento"], params["supuestos"]["phi"]
    filas = [
        ("Planta → centro", res["km_tramo1"]),
        ("Centro → supermercado", res["km_tramo2"]),
    ]
    if res["km_goyito"]:
        filas.append(("Goyito directo", res["km_goyito"]))
    filas.append(("Total", res["km_total"]))
    return pd.DataFrame(
        [{"tramo": t, "km": km, "litros": km / r, "co2_kg": km / r * phi} for t, km in filas]
    )


def tabla_flujos_tramo1(res):
    """Pallets/mes de cada planta a cada centro."""
    return res["flujos_tramo1"].sort_values(["producto", "planta", "centro"], ignore_index=True)


def tabla_flujos_tramo2(res):
    """Pallets/mes de cada centro a cada súper, por producto (formato ancho)."""
    f = res["flujos_tramo2"]
    ancho = f.pivot_table(index=["centro", "super"], columns="producto", values="pallets",
                          aggfunc="sum", fill_value=0)
    ancho["total"] = ancho.sum(axis=1)
    return ancho.reset_index()


def tabla_asignacion(res):
    """Qué centro atiende a cada súper (y qué parte, si lo atienden dos)."""
    f = res["flujos_tramo2"].groupby(["super", "centro"])["pallets"].sum().reset_index()
    f["pct_del_super"] = 100 * f["pallets"] / f.groupby("super")["pallets"].transform("sum")
    return f


def guardar(tablas, carpeta):
    """Escribe {nombre: DataFrame} como CSV en `carpeta`."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, tabla in tablas.items():
        tabla.round(4).to_csv(carpeta / f"{nombre}.csv", index=False)
