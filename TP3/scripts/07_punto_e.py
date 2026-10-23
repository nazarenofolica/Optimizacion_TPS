"""
Pregunta e): tope negociado de 500 km mensuales por conductor, con una penalidad de $ 1.000 por km
excedido (plan §12 e, tarea T21).

Cómo entra en el modelo (src/modelo.py, escenario "e"): una variable de desvío `exc` >= 0 y la
restricción

    TOPE_KM:   km_prop − 500 · n  <=  exc            con  + 1.000 · exc  en el funcional

Es una meta con desvío por exceso (Clase 05): el tope no se impone, se penaliza. La restricción de
capacidad real de los conductores (K_max · n >= km_prop) se mantiene (desvío D2).

    1. Escenario e) sobre el caso base y sobre d) (flota propia en los dos tramos).
    2. Alternativa de cumplir el tope contratando conductores (penalidad prohibitiva).
    3. Lectura "500 km por día" (≈ 11.000 km por mes) de la frase de la consigna (S14).
    4. Barrido del sueldo W: desde qué sueldo conviene contratar en vez de pagar la penalidad.
    5. Enumeración de configuraciones en e) (control).

Salidas: resultados/tablas/16_comparacion_e.csv, 16b_barrido_W_e.csv, 16c_configuraciones_e.csv y
resultados/graficos/10_comparacion_e.png, 11_mapa_flujos_e.png.

    python scripts/07_punto_e.py
"""

import copy
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
DIAS_HABILES = 22                                   # CCT 40/89 (procedimiento §1.1)
PENALIDAD_PROHIBITIVA = 1e7                         # $ por km: obliga a contratar
BARRIDO_W = [300_000, 400_000, 450_000, 490_000, 510_000, 600_000, 800_000, 1_200_000, 1_600_000, 2_080_000]


def pesos(x):
    return f"$ {x:,.0f}".replace(",", ".")


def numero(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def con(params, **cambios):
    """Copia de params con claves de primer nivel cambiadas (tope y penalidad de e)."""
    p = copy.deepcopy(params)
    p.update(cambios)
    return p


def main():
    params = construir_params()
    ubic = datos.cargar_ubicaciones()

    corridas = {
        "a) Caso base": modelo.resolver(params, escenario="a"),
        "e) Tope 500 km, con penalidad": modelo.resolver(params, escenario="e"),
        "e) Tope 500 km, cumplido contratando": modelo.resolver(
            con(params, penalidad_km_e=PENALIDAD_PROHIBITIVA), escenario="e"),
        "e) Tope 500 km por día": modelo.resolver(
            con(params, tope_km_e=500 * DIAS_HABILES), escenario="e"),
        "d) Flota propia": modelo.resolver(params, escenario="d"),
        "d + e) Flota propia con tope": modelo.resolver(params, escenario="de"),
    }
    for nombre, r in corridas.items():
        assert r["estado"] == "Optimal", f"{nombre}: {r['estado']}"
    e = corridas["e) Tope 500 km, con penalidad"]
    a = corridas["a) Caso base"]

    # Controles del escenario e).
    assert abs(e["exceso_km"] - max(0, e["km_propios"] - params["tope_km_e"] * e["conductores"])) < 1e-3, "exc"
    assert e["km_propios"] <= params["supuestos"]["K_max"] * e["conductores"] + 1e-4, "D2: capacidad real"
    contratando = corridas["e) Tope 500 km, cumplido contratando"]
    assert contratando["exceso_km"] < 1e-6, "Con penalidad prohibitiva no debería haber exceso"
    assert corridas["e) Tope 500 km por día"]["exceso_km"] < 1e-6, "500 km por día no debería limitar"

    comp = pd.DataFrame([reportes.fila_resumen(r, escenario=n) for n, r in corridas.items()])
    comp["variacion_costo_vs_a_pct"] = 100 * (comp["costo_total"] / a["costo"] - 1)
    comp["variacion_co2_vs_a_pct"] = 100 * (comp["co2_kg"] / a["co2_kg"] - 1)

    # Barrido de W en e): el umbral teórico es W = 500 km × $ 1.000 = $ 500.000.
    filas = []
    for W in BARRIDO_W:
        r = modelo.resolver(construir_params(W=W), escenario="e")
        assert r["estado"] == "Optimal"
        filas.append(reportes.fila_resumen(r, W=W))
    barrido = pd.DataFrame(filas)
    umbral_W = params["tope_km_e"] * params["penalidad_km_e"]
    debajo = barrido[barrido["W"] < umbral_W]
    encima = barrido[barrido["W"] > umbral_W]
    # Por debajo del umbral se contrata hasta que el exceso no llega a un tope (pagar menos de 500 km
    # sale más barato que un conductor entero); por encima, no se contrata por el tope.
    assert (debajo["exceso_km"] < params["tope_km_e"]).all(), "Con W bajo debería contratar"
    assert (encima["conductores"] == e["conductores"]).all(), "Con W alto no debería contratar por el tope"

    # Enumeración de configuraciones en e) (control).
    filas = []
    for conf in datos.configuraciones_factibles(params).itertuples():
        r = modelo.resolver(params, escenario="e", config_fija=conf.centros)
        filas.append(reportes.fila_resumen(r))
    enum = pd.DataFrame(filas).sort_values("costo_total", ignore_index=True)
    assert enum.loc[0, "configuracion"] == e["configuracion"]
    assert abs(enum.loc[0, "costo_total"] - e["costo"]) <= TOL_REL * e["costo"]

    reportes.guardar({"16_comparacion_e": comp, "16b_barrido_W_e": barrido,
                      "16c_configuraciones_e": enum}, TABLAS)
    GRAFICOS.mkdir(parents=True, exist_ok=True)
    elegidos = ["a) Caso base", "e) Tope 500 km, con penalidad", "d) Flota propia", "d + e) Flota propia con tope"]
    graficos.comparacion_escenarios(
        comp[comp["escenario"].isin(elegidos)].assign(escenario=["a) Base", "e) Base con tope",
                                                                   "d) Flota propia", "d + e) Propia con tope"]),
        "El tope de 500 km por conductor",
        "Costo por mes por rubro, total y emisiones · la configuración es A+C+D en los cuatro",
        GRAFICOS / "10_comparacion_e.png")
    graficos.mapa_asignacion(e, ubic, "Con el tope de 500 km: ¿qué centro abastece a cada supermercado?",
                             GRAFICOS / "11_mapa_flujos_e.png")

    print("=" * 78)
    print("PREGUNTA e) — TOPE DE 500 km POR CONDUCTOR CON PENALIDAD DE $ 1.000 POR km")
    print("=" * 78)
    for f in comp.itertuples():
        print(f"  {f.escenario:<38}{f.configuracion:<7}{pesos(f.costo_total):>17} ({numero(f.variacion_costo_vs_a_pct, 1):>6} %)"
              f"  cond. {f.conductores:>3}  exceso {numero(f.exceso_km):>8} km"
              f"  km propios {numero(f.km_tramo2 + (f.costo_tramo1_combustible > 0) * f.km_tramo1):>8}"
              f"  CO₂ {numero(f.co2_kg):>7} kg ({numero(f.variacion_co2_vs_a_pct, 1)} %)")
    print(f"\nDesglose de e): " + ", ".join(f"{k} {pesos(v)}" for k, v in e["desglose"].items() if abs(v) > 1e-6))
    print(f"\nkm del tramo 1 (tercerizado): a) {numero(a['km_tramo1'])} → e) {numero(e['km_tramo1'])};"
          f" tramo 2 (propio): {numero(a['km_tramo2'])} → {numero(e['km_tramo2'])}")
    print(f"\nBarrido de W en e) (umbral teórico: 500 km × $ 1.000 = {pesos(umbral_W)}):")
    for f in barrido.itertuples():
        print(f"  W = {pesos(f.W):>12}: conductores {f.conductores:>3}, exceso {numero(f.exceso_km):>7} km,"
              f" costo {pesos(f.costo_total)}")
    print("\nConfiguraciones en e) (control):")
    for f in enum.itertuples():
        print(f"  {f.configuracion:<7}{pesos(f.costo_total):>17}  exceso {numero(f.exceso_km)} km  CO₂ {numero(f.co2_kg)} kg")
    print(f"\nTablas en {TABLAS.relative_to(RAIZ)}, gráficos 10 y 11")
    return 0


if __name__ == "__main__":
    sys.exit(main())
