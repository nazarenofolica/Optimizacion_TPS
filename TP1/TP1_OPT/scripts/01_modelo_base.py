"""
Punto a) — Plan de asignación del presupuesto de marketing.

Resuelve el modelo base con los tres funcionales del docs/plan_de_trabajo.md §6 y
reporta el plan, el mix comercial, la distribución por canales y el estado de
cada restricción.

    python scripts/01_modelo_base.py

Salidas: por consola y en resultados/tablas/*.csv
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
if hasattr(sys.stdout, "reconfigure"):  # consola de Windows en cp1252
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd  # noqa: E402

from src import datos, graficos, modelo, reportes  # noqa: E402
from src.config import ETIQUETA_OBJETIVO, construir_params  # noqa: E402

SALIDA = RAIZ / "resultados" / "tablas"

#: Tolerancia de los controles cruzados, en $MM. CBC reporta las variables con ~7
#: cifras significativas, así que sobre valores del orden de 1e4 arrastra errores de
#: hasta 1e-4. Mil pesos de tolerancia está muy por debajo de cualquier magnitud
#: relevante del problema.
TOL = 1e-3

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)
pd.set_option("display.float_format", lambda v: f"{v:,.2f}")


def titulo(texto, caracter="="):
    print(f"\n{caracter * 78}\n{texto}\n{caracter * 78}")


def verificar_cotas(res):
    """Control cruzado manual del óptimo (docs/plan_de_trabajo.md §7.2).

    Con R3 y R4 activas el espacio factible es chico y el resultado se puede
    verificar casi a mano. Si alguna de estas cotas falla, hay un error de modelado,
    no un resultado interesante.
    """
    x, params = res["x"], res["params"]
    presupuesto = params["presupuesto"]
    piso_tri = params["reglas"]["R3_pct_triguetti"] * presupuesto
    mult = params["reglas"]["R4_multiplo_rena"]
    # Cotas derivadas de R3 + R4: Triguetti se lleva su piso y Rena, como mínimo,
    # el doble de ese piso. Lo que sobra es lo único que el modelo reparte libremente.
    piso_tri_rs = piso_tri * (1 + mult)
    resto = presupuesto - piso_tri_rs

    controles = [
        ("Presupuesto agotado", abs(sum(x.values()) - presupuesto) < TOL),
        (f"R3: Triguetti >= {piso_tri:,.0f}", x["TRI"] >= piso_tri - TOL),
        ("R4: Rena >= 2 x (Can + Tri)", x["RS"] >= mult * (x["CAN"] + x["TRI"]) - TOL),
        ("R2: Don Carlo = Agnellis", abs(x["DC"] - x["AG"]) < TOL),
        (f"Triguetti + Rena >= {piso_tri_rs:,.0f}", x["TRI"] + x["RS"] >= piso_tri_rs - TOL),
        (f"Resto (DC+AG+CAN) <= {resto:,.0f}", x["DC"] + x["AG"] + x["CAN"] <= resto + TOL),
        ("Z > término constante", res["Z"] > res["Z_constante"]),
    ]
    for descripcion, ok in controles:
        print(f"  [{'OK ' if ok else 'MAL'}] {descripcion}")
    return all(ok for _, ok in controles)


def verificar_r6(res):
    """R6: ¿Candealix supera las 2.500.000 unidades? (docs/plan_de_trabajo.md §7.3)

    La hipótesis del plan es que la restricción NO está activa. Hay que confirmarlo
    con números, no asumirlo.
    """
    params = res["params"]
    _base, _inc, total = reportes.facturacion(res)
    unidades = total["CAN"] * datos.MILLON / params["productos"]["CAN"]["precio"]
    umbral = params["reglas"]["R6_umbral_candealix"]
    print(f"  Unidades de Candealix : {unidades:>18,.0f} paquetes")
    print(f"  Umbral exigido        : {umbral:>18,.0f} paquetes")
    print(f"  Múltiplo del umbral   : {unidades / umbral:>18,.1f} x")
    if unidades >= umbral:
        print("  -> R6 NO está activa: Candealix supera el umbral y se produce.")
    else:
        print("  -> R6 SÍ está activa: hay que resolver el escenario sin Candealix.")
    return unidades


def main():
    params = construir_params()

    titulo("PUNTO a) — PLAN DE ASIGNACIÓN DEL PRESUPUESTO DE MARKETING")
    print(f"Presupuesto            : ${params['presupuesto']:,} MM")
    print(f"Mercado total de pastas: ${datos.mercado_total(params):,.0f} MM")
    print(f"Facturación base       : ${sum(datos.facturacion_base(params).values()):,.0f} MM")
    print("\nSupuestos vigentes:")
    for clave, valor in params["supuestos"].items():
        print(f"  {clave:<28} = {valor}")

    # --- Las tres corridas --------------------------------------------------
    resultados = {}
    for objetivo in ("neta", "oper", "facturacion"):
        res = modelo.resolver(params, objetivo=objetivo)
        if res["status"] != "Optimal":
            print(f"\nERROR: la corrida '{objetivo}' terminó en estado {res['status']}.")
            return 1
        resultados[objetivo] = res

    base = resultados["neta"]  # caso base del informe: la mirada de los accionistas

    titulo("1. VERIFICACIÓN DE COTAS (control cruzado manual)", "-")
    if not verificar_cotas(base):
        print("\nERROR: el óptimo viola una cota deducida a mano. Revisar el modelo.")
        return 1

    titulo("2. VERIFICACIÓN DE R6 (umbral de Candealix)", "-")
    verificar_r6(base)

    titulo("3. PLAN DE INVERSIÓN — objetivo: utilidad neta", "-")
    t_plan = reportes.tabla_plan(base)
    print(t_plan.to_string(index=False))

    titulo("4. MIX COMERCIAL RESULTANTE — objetivo: utilidad neta", "-")
    t_com = reportes.tabla_comercial(base)
    print(t_com.to_string(index=False))

    titulo("5. DISTRIBUCIÓN POR CANALES (segmentos)", "-")
    t_can = reportes.tabla_canales(base)
    print(t_can.to_string(index=False))

    titulo("6. RESTRICCIONES: holgura y precio sombra", "-")
    t_res = reportes.tabla_restricciones(base)
    print(t_res.to_string(index=False))

    titulo("7. COMPARACIÓN DE LOS TRES OBJETIVOS", "-")
    t_cmp = reportes.tabla_comparativa(list(resultados.values()))
    print(t_cmp.to_string())

    # Costo de oportunidad de perseguir un objetivo en lugar del otro.
    r_neta, r_fact = resultados["neta"], resultados["facturacion"]
    u_neta = reportes.resumen(r_neta)
    u_fact = reportes.resumen(r_fact)
    print(
        f"\nCosto de maximizar facturación en vez de utilidad: "
        f"${u_neta['Utilidad neta ($MM)'] - u_fact['Utilidad neta ($MM)']:,.2f} MM de utilidad"
    )
    print(
        f"Ganancia de market share al hacerlo               : "
        f"{u_fact['Market share (%)'] - u_neta['Market share (%)']:+.4f} puntos"
    )

    ruta_grafico = graficos.plan_base(t_com, t_can)
    print(f"\nGráfico guardado en: {ruta_grafico.relative_to(RAIZ)}")

    # --- Guardado -----------------------------------------------------------
    tablas = {
        "01_plan_inversion": t_plan,
        "02_mix_comercial": t_com,
        "03_canales": t_can,
        "04_restricciones": t_res,
        "05_comparacion_objetivos": t_cmp,
    }
    for objetivo, res in resultados.items():
        tablas[f"06_mix_{objetivo}"] = reportes.tabla_comercial(res)
    archivos = reportes.guardar(tablas, SALIDA)

    titulo("ARCHIVOS GENERADOS", "-")
    for nombre in archivos:
        print(f"  resultados/tablas/{nombre}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
