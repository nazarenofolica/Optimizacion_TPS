"""
Punto b) — Reposición automática: ¿se beneficia la variedad de oferta?

Reformula el modelo de a) bajo la lectura "compartida" del supuesto S1
(docs/plan_de_trabajo.md §17.1, docs/procedimiento.md §4.3): con reposición
automática, lo que se vende vuelve enseguida y alcanza con **una unidad de cada
artículo** para que un combo esté disponible. Es el mismo modelo de a) — mismos
datos, mismas restricciones de capacidad, mismo desempate S3 — con esa única
lectura de S1 cambiada. No hay que escribir un modelo nuevo (plan §17).

Responde la pregunta de la consigna ("¿la variedad de oferta se ve beneficiada?")
con las dos lecturas posibles de "variedad": combos ofrecidos y artículos
distintos en stock, comparando siempre contra el escenario a).

    python scripts/03_punto_b.py

Salidas: por consola y en resultados/tablas/*.csv
"""

import sys
from math import comb
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
if hasattr(sys.stdout, "reconfigure"):  # consola de Windows en cp1252
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd  # noqa: E402

from src import datos, graficos, modelo, reportes  # noqa: E402
from src.config import construir_params  # noqa: E402

SALIDA = RAIZ / "resultados" / "tablas"

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)
pd.set_option("display.float_format", lambda v: f"{v:,.4f}")


def titulo(texto, caracter="="):
    print(f"\n{caracter * 78}\n{texto}\n{caracter * 78}")


def articulos_distintos(stock):
    """Cuántos de los 30 artículos tienen al menos 1 unidad en stock."""
    return sum(1 for v in stock.values() if v > 0)


def main():
    params_a = construir_params()  # caso base de a): S1 = exclusiva
    params_b = construir_params(S1_disponibilidad="compartida")
    n_combos = len(params_b["combos"])

    titulo("PUNTO b) — REPOSICIÓN AUTOMÁTICA (S1_disponibilidad = compartida)")
    print("Supuestos vigentes (igual que a), salvo S1):")
    for clave, valor in params_b["supuestos"].items():
        print(f"  {clave:<26} = {valor}")

    # --- 1. Resolver a) y b) ---------------------------------------------------
    etapa1_a, final_a = modelo.resolver_lexicografico(params_a)
    etapa1_b, final_b = modelo.resolver_lexicografico(params_b)
    if etapa1_a["status"] != "Optimal" or final_a["status"] != "Optimal":
        print(f"\nERROR: a) no dio Optimal ({etapa1_a['status']} / {final_a['status']}).")
        return 1
    if etapa1_b["status"] != "Optimal" or final_b["status"] != "Optimal":
        print(f"\nERROR: b) no dio Optimal ({etapa1_b['status']} / {final_b['status']}).")
        return 1

    v_a, v_b = etapa1_a["variedad"], etapa1_b["variedad"]

    titulo("1. ETAPA 1 — MÁXIMA VARIEDAD BAJO REPOSICIÓN AUTOMÁTICA", "-")
    print(f"Variedad máxima V* (b, compartida)     : {v_b} combos de {n_combos}")
    print(f"Variedad máxima V* (a, referencia)     : {v_a} combos de {n_combos}")

    titulo(f"2. DESEMPATE: {params_b['supuestos']['S3_desempate']} (mismo criterio S3 que a)", "-")
    print(f"Variedad                               : {final_b['variedad']} combos")
    print(f"Categorías del catálogo cubiertas      : {final_b['categorias']} de {len(params_b['catalogo'])}")
    print(f"Unidades totales en stock              : {final_b['unidades']}")
    t_combos_b = reportes.tabla_combos(final_b)
    print()
    print(t_combos_b.to_string(index=False))

    # --- 3. Plan de stock -------------------------------------------------------
    titulo("3. PLAN DE STOCK BAJO b) — cuántas unidades de cada artículo", "-")
    t_stock_b = reportes.tabla_stock(final_b)
    con_stock_b = t_stock_b[t_stock_b["Unidades en stock"] > 0]
    print(con_stock_b.to_string(index=False))
    print(
        f"\n{len(con_stock_b)} artículos con stock, {len(t_stock_b) - len(con_stock_b)} en cero "
        f"(la tabla completa de 30 filas va al CSV)."
    )

    # --- 4. Ocupación del depósito -----------------------------------------------
    titulo("4. OCUPACIÓN DEL DEPÓSITO BAJO b)", "-")
    t_esp_b = reportes.tabla_espacios(final_b)
    print(t_esp_b.to_string(index=False))
    print(f"\nLugares ocupados: {final_b['unidades']} de {sum(t_esp_b['Capacidad'])}")
    ruta_grafico = graficos.ocupacion_deposito(t_esp_b, nombre_archivo="02_ocupacion_deposito_b")
    print(f"Gráfico guardado en: {ruta_grafico.relative_to(RAIZ)}")

    # --- 5. ¿Se beneficia la variedad? -------------------------------------------
    titulo("5. ¿SE BENEFICIA LA VARIEDAD DE OFERTA? — comparación a) vs b)", "-")
    dist_a = articulos_distintos(final_a["stock"])
    dist_b = articulos_distintos(final_b["stock"])
    t_comp = pd.DataFrame(
        [
            {"Métrica": "Combos ofrecidos", "a) exclusiva": v_a, "b) compartida": v_b, "Δ": v_b - v_a},
            {
                "Métrica": "Artículos distintos en stock",
                "a) exclusiva": dist_a,
                "b) compartida": dist_b,
                "Δ": dist_b - dist_a,
            },
            {
                "Métrica": "Unidades totales en stock",
                "a) exclusiva": final_a["unidades"],
                "b) compartida": final_b["unidades"],
                "Δ": final_b["unidades"] - final_a["unidades"],
            },
            {
                "Métrica": "Categorías del catálogo cubiertas",
                "a) exclusiva": final_a["categorias"],
                "b) compartida": final_b["categorias"],
                "Δ": final_b["categorias"] - final_a["categorias"],
            },
        ]
    )
    print(t_comp.to_string(index=False))
    print(
        "\nLas dos lecturas de \"variedad de oferta\" mejoran con la reposición automática: "
        f"combos ofrecidos {v_a} -> {v_b} y artículos distintos en stock {dist_a} -> {dist_b}."
    )

    # --- 6. Óptimos alternativos --------------------------------------------------
    titulo("6. ÓPTIMOS ALTERNATIVOS BAJO b) — enumeración exhaustiva sin solver", "-")
    print("(V* = 13: enumerar tarda unos segundos, C(20,13) + C(20,14) conjuntos)")
    optimos_b = datos.enumerar_factibles(params_b, v_b)
    siguientes_b = datos.enumerar_factibles(params_b, v_b + 1)
    t_opt_b = reportes.tabla_optimos(params_b, optimos_b)
    print(f"Conjuntos de {v_b} combos que entran     : {len(optimos_b):>6} de {comb(n_combos, v_b):,}")
    print(f"Conjuntos de {v_b + 1} combos que entran     : {len(siguientes_b):>6} de {comb(n_combos, v_b + 1):,}")
    print()
    print(t_opt_b.to_string(index=False))

    # --- 7. Capacidad +1 por espacio, bajo reposición automática ------------------
    titulo("7. CAPACIDAD +1 POR ESPACIO, BAJO b) (mismo test que el plan §10.1 para a)", "-")
    filas_cap = []
    for e, d in params_b["espacios"].items():
        probado = construir_params(S1_disponibilidad="compartida", capacidades={e: d["capacidad"] + 1})
        r = modelo.resolver(probado)
        filas_cap.append(
            {
                "Espacio": d["nombre"],
                "Capacidad base": d["capacidad"],
                "Capacidad probada": d["capacidad"] + 1,
                "V*": r["variedad"],
                "Delta V*": r["variedad"] - v_b,
            }
        )
    t_cap_b = pd.DataFrame(filas_cap)
    print(t_cap_b.to_string(index=False))

    # --- 8. Controles cruzados ----------------------------------------------------
    titulo("8. CONTROLES CRUZADOS", "-")
    controles = [
        ("V*(b) >= V*(a): la reposición automática nunca empeora la variedad", v_b >= v_a),
        (
            f"Fuerza bruta bajo b): hay conjuntos de {v_b} y ninguno de {v_b + 1}",
            bool(optimos_b) and not siguientes_b,
        ),
        ("El desempate no pierde variedad en b)", final_b["variedad"] == v_b),
        (
            "Stock de la solución final de b) = stock necesario (sin sobrante)",
            final_b["stock"] == datos.stock_necesario(params_b, final_b["combos"]),
        ),
        ("La ocupación respeta todas las capacidades en b)", all(h >= 0 for h in final_b["holgura"].values())),
        ("Los combos de la solución final están entre los óptimos enumerados", tuple(final_b["combos"]) in set(optimos_b)),
        ("Capacidad +1 en b): sumar un lugar nunca baja la variedad", (t_cap_b["Delta V*"] >= 0).all()),
        ("Artículos distintos en stock: b) >= a)", dist_b >= dist_a),
    ]
    for descripcion, ok in controles:
        print(f"  [{'OK ' if ok else 'MAL'}] {descripcion}")
    if not all(ok for _, ok in controles):
        print("\nERROR: falló un control cruzado. Revisar el modelo.")
        return 1

    # --- Guardado -------------------------------------------------------------
    tablas = {
        "13_comparacion_a_b": t_comp,
        "14_combos_ofrecidos_b": t_combos_b,
        "15_plan_stock_b": t_stock_b,
        "16_ocupacion_deposito_b": t_esp_b,
        "17_optimos_alternativos_b": t_opt_b,
        "18_test_capacidad_mas_uno_b": t_cap_b,
    }
    archivos = reportes.guardar(tablas, SALIDA)
    titulo("ARCHIVOS GENERADOS", "-")
    for nombre in archivos:
        if nombre.split("_", 1)[0] in {"13", "14", "15", "16", "17", "18"}:
            print(f"  resultados/tablas/{nombre}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
