"""
Punto a) — Stock que maximiza la variedad de combos con reposición mensual.

Resuelve el modelo por etapas lexicográficas (docs/plan_de_trabajo.md §6.3, con el
desempate de docs/procedimiento.md §2.5),
enumera todos los óptimos alternativos por fuerza bruta (§8), resuelve la relajación
lineal (§6.4) y verifica todo contra las cotas deducidas a mano (§7).

    python scripts/01_punto_a.py

Salidas: por consola y en resultados/tablas/*.csv
"""

import sys
from collections import Counter
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

#: Tolerancia para comparar el valor de la relajación lineal (continua).
TOL = 1e-6

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)
pd.set_option("display.float_format", lambda v: f"{v:,.4f}")


def titulo(texto, caracter="="):
    print(f"\n{caracter * 78}\n{texto}\n{caracter * 78}")


def main():
    params = construir_params()
    n_combos = len(params["combos"])

    titulo("PUNTO a) — STOCK QUE MAXIMIZA LA VARIEDAD DE COMBOS (reposición mensual)")
    print("Supuestos vigentes:")
    for clave, valor in params["supuestos"].items():
        print(f"  {clave:<26} = {valor}")

    # --- 1. Cota trivial ------------------------------------------------------
    titulo("1. COTA TRIVIAL POR ESPACIO (plan §3.6)", "-")
    t_cota = reportes.tabla_cota_trivial(params)
    print(t_cota.to_string(index=False))
    cota = min(v for v in datos.cota_trivial(params).values() if v is not None)
    print(f"\nCota superior de la variedad: {cota} combos")

    # --- 2 y 3. Las dos etapas ------------------------------------------------
    etapa1, final = modelo.resolver_lexicografico(params)
    if etapa1["status"] != "Optimal" or final["status"] != "Optimal":
        print(f"\nERROR: estados {etapa1['status']} / {final['status']}.")
        return 1
    v_max = etapa1["variedad"]

    titulo("2. ETAPA 1 — MÁXIMA VARIEDAD", "-")
    print(f"Variedad máxima V*                     : {v_max} combos de {n_combos}")
    print(f"Combos que eligió el solver            : {etapa1['combos']}")
    necesario_e1 = sum(datos.stock_necesario(params, etapa1["combos"]).values())
    print(f"Unidades en stock que dejó el solver   : {etapa1['unidades']}")
    print(f"Unidades realmente necesarias          : {necesario_e1}")
    print(f"Stock sobrante (el funcional no lo ve) : {etapa1['unidades'] - necesario_e1}")

    titulo(f"3. DESEMPATE: {params['supuestos']['S3_desempate']} (supuesto S3)", "-")
    print(f"Variedad                               : {final['variedad']} combos")
    print(f"Categorías del catálogo cubiertas      : {final['categorias']} de {len(params['catalogo'])}")
    print(f"Unidades totales en stock              : {final['unidades']}")
    t_combos = reportes.tabla_combos(final)
    print()
    print(t_combos.to_string(index=False))

    # --- 4. Plan de stock -----------------------------------------------------
    titulo("4. PLAN DE STOCK — cuántas unidades de cada artículo", "-")
    t_stock = reportes.tabla_stock(final)
    con_stock = t_stock[t_stock["Unidades en stock"] > 0]
    print(con_stock.to_string(index=False))
    print(
        f"\n{len(con_stock)} artículos con stock, {len(t_stock) - len(con_stock)} en cero "
        f"(la tabla completa de 30 filas va al CSV)."
    )

    # --- 5. Ocupación ---------------------------------------------------------
    titulo("5. OCUPACIÓN DEL DEPÓSITO", "-")
    t_esp = reportes.tabla_espacios(final)
    print(t_esp.to_string(index=False))
    print(f"\nLugares ocupados: {final['unidades']} de {sum(t_esp['Capacidad'])}")
    ruta_grafico = graficos.ocupacion_deposito(t_esp)
    print(f"Gráfico guardado en: {ruta_grafico.relative_to(RAIZ)}")

    # --- 6. Óptimos alternativos ----------------------------------------------
    titulo("6. ÓPTIMOS ALTERNATIVOS — enumeración exhaustiva sin solver (plan §8)", "-")
    optimos = datos.enumerar_factibles(params, v_max)
    siguientes = datos.enumerar_factibles(params, v_max + 1)
    t_opt = reportes.tabla_optimos(params, optimos)
    nombre_lc = params["espacios"]["lavav_cocinas"]["nombre"]
    print(f"Conjuntos de {v_max} combos que entran     : {len(optimos):>5} de {comb(n_combos, v_max):,}")
    print(f"Conjuntos de {v_max + 1} combos que entran     : {len(siguientes):>5} de {comb(n_combos, v_max + 1):,}")
    print(f"\nÓptimos por unidades totales       : {dict(sorted(Counter(t_opt['Unidades']).items()))}")
    print(f"Óptimos por lugares de lavav.+coc. : {dict(sorted(Counter(t_opt[nombre_lc]).items()))}")
    print(f"Óptimos por categorías cubiertas   : {dict(sorted(Counter(t_opt['Categorías cubiertas']).items()))}")
    min_unidades = int(t_opt["Unidades"].min())
    n_min = int((t_opt["Unidades"] == min_unidades).sum())
    print(f"\nÓptimos con el mínimo de unidades ({min_unidades})              : {n_min}")
    max_cat = int(t_opt["Categorías cubiertas"].max())
    con_max_cat = t_opt[t_opt["Categorías cubiertas"] == max_cat]
    min_u_cat = int(con_max_cat["Unidades"].min())
    empatados = int((con_max_cat["Unidades"] == min_u_cat).sum())
    print(f"Óptimos con {max_cat} categorías y {min_u_cat} unidades (desempate base) : {empatados}")

    print("\n¿Qué espacios quedan llenos?")
    for e, d in params["espacios"].items():
        llenos = int((t_opt[d["nombre"]] == d["capacidad"]).sum())
        print(f"  {d['nombre']:<24} lleno en {llenos:>4} de {len(optimos)} óptimos")

    # --- 7. Relajación lineal ---------------------------------------------------
    titulo("7. RELAJACIÓN LINEAL (plan §6.4)", "-")
    relajada = modelo.resolver(params, relajar=True)
    if relajada["status"] != "Optimal":
        print(f"ERROR: la relajación terminó en estado {relajada['status']}.")
        return 1
    print(f"Cota de la relajación lineal: {relajada['Z']:.4f} combos")
    fraccion = {c: round(v, 4) for c, v in relajada["y"].items() if v > 1e-6}
    enteros = all(abs(v - round(v)) < TOL for v in relajada["y"].values())
    print(f"y_c > 0 en la relajación     : {fraccion}")
    print(f"¿Solución de la relajación entera?: {'Sí' if enteros else 'No'}")
    print(
        f"Stock que dejó el solver     : {relajada['unidades']:.4f} unidades "
        f"(necesarias: {sum(relajada['ocupacion_necesaria'].values()):.4f})"
    )
    t_rel = reportes.tabla_espacios(relajada)
    print(t_rel.to_string(index=False))
    print("\nOJO: estos precios sombra son del PL relajado, no del modelo entero.")

    # --- 8. Controles cruzados --------------------------------------------------
    titulo("8. CONTROLES CRUZADOS", "-")
    controles = [
        (f"V* <= cota trivial ({cota})", v_max <= cota),
        (f"Fuerza bruta: hay conjuntos de {v_max} y ninguno de {v_max + 1}", bool(optimos) and not siguientes),
        ("El desempate no pierde variedad", final["variedad"] == v_max),
        (
            "Stock de la solución final = stock necesario (sin sobrante)",
            final["stock"] == datos.stock_necesario(params, final["combos"]),
        ),
        ("La ocupación respeta todas las capacidades", all(h >= 0 for h in final["holgura"].values())),
        ("Los combos de la solución final están entre los óptimos enumerados", tuple(final["combos"]) in set(optimos)),
        ("Relajación lineal >= V*", relajada["Z"] >= v_max - TOL),
    ]
    # El orden del desempate se verifica contra la enumeración, que no usa el solver.
    criterio = params["supuestos"]["S3_desempate"]
    if criterio == "categorias_y_unidades":
        controles += [
            (f"Categorías = máximo entre los óptimos ({max_cat})", final["categorias"] == max_cat),
            (
                f"Unidades = mínimo entre los óptimos con {max_cat} categorías ({min_u_cat})",
                final["unidades"] == min_u_cat,
            ),
        ]
    elif criterio == "min_unidades":
        controles.append((f"Unidades = mínimo entre los óptimos ({min_unidades})", final["unidades"] == min_unidades))
    for descripcion, ok in controles:
        print(f"  [{'OK ' if ok else 'MAL'}] {descripcion}")
    if not all(ok for _, ok in controles):
        print("\nERROR: falló un control cruzado. Revisar el modelo.")
        return 1

    # --- Guardado -----------------------------------------------------------
    tablas = {
        "01_apariciones_articulos": reportes.tabla_apariciones(params),
        "02_cota_trivial": t_cota,
        "03_combos_ofrecidos": t_combos,
        "04_plan_stock": t_stock,
        "05_ocupacion_deposito": t_esp,
        "06_optimos_alternativos": t_opt,
        "07_relajacion_lineal": t_rel,
    }
    archivos = reportes.guardar(tablas, SALIDA)
    titulo("ARCHIVOS GENERADOS", "-")
    for nombre in archivos:
        print(f"  resultados/tablas/{nombre}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
