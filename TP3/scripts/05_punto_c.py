"""
Pregunta c): valor unitario mínimo ofrecido por Goyito, por producto, a partir del cual no resulta
económicamente viable instalar el centro de distribución (plan §12 c, tarea T19).

Goyito cobra un precio por pallet entregado y lleva la mercadería directo de la planta al súper
(supuesto S15). Para cada producto k:

    umbral_k = ( Z* − Z*(sin k) ) / demanda_k

donde Z*(sin k) es el costo óptimo de la red propia cuando Goyito se lleva el producto k (se
resuelve con `goyito={k: 0}`: el precio no cambia la red, solo se suma). Si Goyito ofrece menos
que umbral_k, conviene dejarle el producto. Es el ahorro incremental de la red, no el costo
promedio: los costos fijos (apertura y gerente) no se reparten entre productos.

Controles:
    - Bisección sobre el precio con la binaria u_k del modelo: con el precio un poco por debajo del
      umbral, el modelo le da el producto a Goyito; un poco por encima, no.
    - Umbral global (todo a Goyito, precio único): Z* / 51.850.

Ambiental: km, litros y CO2 del viaje directo de Goyito contra los del mismo producto por el
centro (con los flujos del óptimo). Con un precio del carbono (Ley 27.430: USD 10/t, al tipo de
cambio BNA) se recalculan los umbrales con el CO2 dentro del funcional.

Salidas: resultados/tablas/14_umbral_goyito.csv, 14b_goyito_ambiental.csv y
resultados/graficos/06_umbral_goyito.png.

    python scripts/05_punto_c.py
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

#: Precio del carbono: USD 10 por tonelada (Ley 27.430, procedimiento §1.1) al dólar oficial BNA
#: (venta, 23/10/2026: $ 1.550). USD 10/t × 1.550 $/USD / 1.000 kg/t = $ 15,5 por kg de CO2.
DOLAR_BNA = 1_550
PRECIO_CO2 = 10 * DOLAR_BNA / 1_000
#: Margen para el control por bisección [$ por pallet] (CBC tiene error de centavos sobre $ 56 M).
MARGEN = 2.0


def pesos(x):
    return f"$ {x:,.0f}".replace(",", ".")


def numero(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def umbrales(params):
    """Umbral por producto para un juego de parámetros."""
    base = modelo.resolver(params)
    assert base["estado"] == "Optimal"
    dem_k = datos.demanda_por_producto(params)
    filas = []
    for k in params["productos"]:
        sin_k = modelo.resolver(params, goyito={k: 0})
        assert sin_k["estado"] == "Optimal" and sin_k["goyito"][k], f"Goyito gratis y no lleva {k}"
        filas.append({
            "producto": k,
            "demanda": dem_k[k],
            "costo_con_k": base["costo"],
            "costo_sin_k": sin_k["costo"],
            "configuracion_sin_k": sin_k["configuracion"],
            "conductores_sin_k": sin_k["conductores"],
            "umbral": (base["costo"] - sin_k["costo"]) / dem_k[k],
        })
    return base, pd.DataFrame(filas)


def control_biseccion(params, tabla):
    """El modelo, con la binaria u_k, cambia de decisión justo en el umbral."""
    ok = []
    for f in tabla.itertuples():
        abajo = modelo.resolver(params, goyito={f.producto: f.umbral - MARGEN})["goyito"][f.producto]
        arriba = modelo.resolver(params, goyito={f.producto: f.umbral + MARGEN})["goyito"][f.producto]
        ok.append(abajo and not arriba)
    return ok


def costo_directo_tarifa(params, coef, ubic):
    """Lo que costaría llevar cada producto directo planta -> súper con la tarifa de mercado
    ($ 500 por km de ida, S10), desde la planta más cercana: referencia de lo que le cuesta el
    servicio a Goyito."""
    P_k = datos.plantas_por_producto(ubic)
    c = coef.set_index(["origen", "destino"])["costo_tercerizado"]
    km = coef.set_index(["origen", "destino"])["km_por_pallet"]
    filas = {}
    for k, ps in P_k.items():
        total = sum(params["demanda"][i, k] * min(c[p, i] for p in ps) for i in params["supermercados"])
        km_k = sum(params["demanda"][i, k] * min(km[p, i] for p in ps) for i in params["supermercados"])
        filas[k] = (total / sum(params["demanda"][i, k] for i in params["supermercados"]), km_k)
    return filas


def km_por_producto_centro(base, coef):
    """km físicos atribuibles a cada producto en la red propia (con los flujos del óptimo)."""
    km = coef.set_index(["origen", "destino"])["km_por_pallet"]
    f1, f2 = base["flujos_tramo1"], base["flujos_tramo2"]
    t1 = f1.assign(km=[km[p, j] * x for p, j, x in zip(f1["planta"], f1["centro"], f1["pallets"])])
    t2 = f2.assign(km=[km[j, i] * x for j, i, x in zip(f2["centro"], f2["super"], f2["pallets"])])
    return t1.groupby("producto")["km"].sum() + t2.groupby("producto")["km"].sum()


def main():
    params = construir_params()
    ubic = datos.cargar_ubicaciones()
    coef = datos.coeficientes_por_arco(params)
    s = params["supuestos"]

    # --- Umbrales sin y con precio del carbono ------------------------------------------
    base, tabla = umbrales(params)
    ok = control_biseccion(params, tabla)
    assert all(ok), f"La bisección no coincide: {dict(zip(tabla['producto'], ok))}"
    base_c, tabla_c = umbrales(construir_params(precio_co2=PRECIO_CO2))
    tabla["umbral_con_carbono"] = tabla_c["umbral"].to_numpy()
    tabla["control_biseccion_ok"] = ok

    ref = costo_directo_tarifa(params, coef, ubic)
    tabla["costo_directo_tarifa"] = [ref[k][0] for k in tabla["producto"]]
    tabla["margen_goyito"] = tabla["umbral"] - tabla["costo_directo_tarifa"]
    total_demanda = tabla["demanda"].sum()
    umbral_global = base["costo"] / total_demanda
    no_asignable = base["costo"] - (tabla["umbral"] * tabla["demanda"]).sum()

    # --- Ambiental: directo contra vía centro ----------------------------------------------
    km_cd = km_por_producto_centro(base, coef)
    r, phi = params["rendimiento"], s["phi"]
    amb = pd.DataFrame({
        "producto": tabla["producto"],
        "km_via_centro": [km_cd[k] for k in tabla["producto"]],
        "km_directo_goyito": [ref[k][1] for k in tabla["producto"]],
    })
    amb.loc[len(amb)] = ["Total", amb["km_via_centro"].sum(), amb["km_directo_goyito"].sum()]
    amb["co2_via_centro_kg"] = amb["km_via_centro"] / r * phi
    amb["co2_directo_kg"] = amb["km_directo_goyito"] / r * phi
    amb["variacion_km_pct"] = 100 * (amb["km_directo_goyito"] / amb["km_via_centro"] - 1)
    amb["costo_carbono_ahorrado"] = (amb["co2_via_centro_kg"] - amb["co2_directo_kg"]) * PRECIO_CO2
    assert abs(amb["km_via_centro"].iloc[-1] - base["km_total"]) < 1e-3 * base["km_total"], "km por producto"
    co2_todo_goyito = amb["co2_directo_kg"].iloc[-1]
    umbral_global_carbono = (base_c["costo"] - co2_todo_goyito * PRECIO_CO2) / total_demanda

    # --- Salidas ----------------------------------------------------------------------------
    reportes.guardar({"14_umbral_goyito": tabla, "14b_goyito_ambiental": amb}, TABLAS)
    GRAFICOS.mkdir(parents=True, exist_ok=True)
    graficos.umbral_goyito(tabla, umbral_global, GRAFICOS / "06_umbral_goyito.png")

    print("=" * 78)
    print("PREGUNTA c) — PRECIO MÍNIMO DE GOYITO POR PRODUCTO")
    print("=" * 78)
    print(f"Red propia (a): {base['configuracion']}, {pesos(base['costo'])} por mes, "
          f"{numero(total_demanda)} pallets\n")
    print("Producto     umbral $/pallet   con carbono   viaje directo a tarifa   red sin el producto")
    for f in tabla.itertuples():
        print(f"  {f.producto:<11}{pesos(f.umbral):>12}{pesos(f.umbral_con_carbono):>14}"
              f"{pesos(f.costo_directo_tarifa):>18}         {f.configuracion_sin_k}, {f.conductores_sin_k} cond.")
    print(f"\nTodo a Goyito con precio único: {pesos(umbral_global)} por pallet "
          f"(con carbono: {pesos(umbral_global_carbono)})")
    print(f"Costo de la red que no se puede asignar a ningún producto: {pesos(no_asignable)}"
          f" (apertura + gerente = {pesos(base['desglose']['apertura'] + base['desglose']['gerente'])})")
    print(f"Control por bisección (±{MARGEN:.0f} $/pallet): {'OK' if all(ok) else 'MAL'} en los 5 productos\n")
    print(f"Ambiental (precio del carbono: $ {numero(PRECIO_CO2, 1)} por kg):")
    for f in amb.itertuples():
        print(f"  {f.producto:<11}{numero(f.km_via_centro):>9} km por el centro{numero(f.km_directo_goyito):>9} km directo"
              f"  ({numero(f.variacion_km_pct, 1):>6} %){numero(f.co2_via_centro_kg - f.co2_directo_kg):>8} kg CO₂ menos")
    print(f"\nTablas en {TABLAS.relative_to(RAIZ)}, gráfico 06_umbral_goyito.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
