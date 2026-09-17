"""
Punto c) — Mesadas y alacenas comparten un espacio de 12 lugares.

Parte del escenario de b) (reposición automática, S1_disponibilidad="compartida",
plan §17.2 y consigna: "Considerando el escenario del inciso b)") y fusiona dos
espacios del depósito en uno solo, del mismo modo en que ya se guardan lavavajillas
y cocinas juntos: mesadas y alacenas pasan a compartir 12 lugares en vez de tener
4 + 3 = 7 lugares separados. Es el único inciso que toca código, y es un cambio
chico: `config.construir_params` ahora acepta redefinir la estructura de espacios
(ver `src/config.py`, argumento `espacios`); el resto del modelo (restricciones,
cotas triviales, ocupación, reportes) recorre `params["espacios"]` de forma
genérica y no necesitó cambios.

Verifica si la nueva disposición permite completar la oferta de los 20 combos,
decide si conviene, y si hace falta pedir más lugar en algún otro espacio, usando
el mismo test de capacidad +1 que en a) y b).

    python scripts/04_punto_c.py

Salidas: por consola y en resultados/tablas/*.csv
"""

import sys
from copy import deepcopy
from math import comb
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
if hasattr(sys.stdout, "reconfigure"):  # consola de Windows en cp1252
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd  # noqa: E402

from src import config, datos, graficos, modelo, reportes  # noqa: E402
from src.config import construir_params  # noqa: E402

SALIDA = RAIZ / "resultados" / "tablas"

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)
pd.set_option("display.float_format", lambda v: f"{v:,.4f}")


def titulo(texto, caracter="="):
    print(f"\n{caracter * 78}\n{texto}\n{caracter * 78}")


def espacios_mesadas_alacenas_juntas(capacidad=12):
    """La nueva disposición física: mesadas y alacenas comparten un espacio.

    Igual construcción que lavavajillas + cocinas, con las capacidades que el
    inciso c) da: 12 lugares para las 8 variantes de mesada y alacena juntas.
    """
    espacios = deepcopy(config.ESPACIOS)
    del espacios["mesadas"], espacios["alacenas"]
    espacios["mesadas_alacenas"] = {
        "nombre": "Mesadas + alacenas",
        "categorias": ("M", "A"),
        "capacidad": capacidad,
    }
    return espacios


def main():
    params_b = construir_params(S1_disponibilidad="compartida")  # escenario de partida
    params_c = construir_params(espacios=espacios_mesadas_alacenas_juntas(), S1_disponibilidad="compartida")
    n_combos = len(params_c["combos"])

    titulo("PUNTO c) — MESADAS Y ALACENAS COMPARTEN 12 LUGARES (parte de b)")
    print("Espacios del depósito bajo c):")
    for e, d in params_c["espacios"].items():
        print(f"  {e:<18} {d['nombre']:<24} categorías {d['categorias']}  capacidad {d['capacidad']}")
    print("\nSupuestos vigentes (los mismos de b):")
    for clave, valor in params_c["supuestos"].items():
        print(f"  {clave:<26} = {valor}")

    # --- 1. Resolver b) y c) ----------------------------------------------------
    etapa1_b, final_b = modelo.resolver_lexicografico(params_b)
    etapa1_c, final_c = modelo.resolver_lexicografico(params_c)
    if etapa1_b["status"] != "Optimal" or final_b["status"] != "Optimal":
        print(f"\nERROR: b) no dio Optimal ({etapa1_b['status']} / {final_b['status']}).")
        return 1
    if etapa1_c["status"] != "Optimal" or final_c["status"] != "Optimal":
        print(f"\nERROR: c) no dio Optimal ({etapa1_c['status']} / {final_c['status']}).")
        return 1

    v_b, v_c = etapa1_b["variedad"], etapa1_c["variedad"]

    titulo("1. ETAPA 1 — MÁXIMA VARIEDAD CON MESADAS Y ALACENAS JUNTAS", "-")
    print(f"Variedad máxima V* (c, mesadas+alacenas juntas) : {v_c} combos de {n_combos}")
    print(f"Variedad máxima V* (b, referencia)               : {v_b} combos de {n_combos}")

    titulo(f"2. DESEMPATE: {params_c['supuestos']['S3_desempate']} (mismo criterio S3 que a) y b)", "-")
    print(f"Variedad                               : {final_c['variedad']} combos")
    print(f"Categorías del catálogo cubiertas      : {final_c['categorias']} de {len(params_c['catalogo'])}")
    print(f"Unidades totales en stock              : {final_c['unidades']}")
    t_combos_c = reportes.tabla_combos(final_c)
    print()
    print(t_combos_c.to_string(index=False))
    faltantes = sorted(set(params_c["combos"]) - set(final_c["combos"]))
    print(f"\nCombos que NO quedan disponibles ({len(faltantes)}): {faltantes}")

    # --- 3. Plan de stock -------------------------------------------------------
    titulo("3. PLAN DE STOCK BAJO c) — cuántas unidades de cada artículo", "-")
    t_stock_c = reportes.tabla_stock(final_c)
    con_stock_c = t_stock_c[t_stock_c["Unidades en stock"] > 0]
    print(con_stock_c.to_string(index=False))
    print(
        f"\n{len(con_stock_c)} artículos con stock, {len(t_stock_c) - len(con_stock_c)} en cero "
        f"(la tabla completa de 30 filas va al CSV)."
    )

    # --- 4. Ocupación del depósito -----------------------------------------------
    titulo("4. OCUPACIÓN DEL DEPÓSITO BAJO c)", "-")
    t_esp_c = reportes.tabla_espacios(final_c)
    print(t_esp_c.to_string(index=False))
    print(f"\nLugares ocupados: {final_c['unidades']} de {sum(t_esp_c['Capacidad'])}")
    ruta_grafico = graficos.ocupacion_deposito(t_esp_c, nombre_archivo="03_ocupacion_deposito_c")
    print(f"Gráfico guardado en: {ruta_grafico.relative_to(RAIZ)}")

    # --- 5. ¿Se completan los 20 combos? -----------------------------------------
    titulo("5. ¿SE COMPLETA LA OFERTA DE 20 COMBOS? — comparación b) vs c)", "-")
    t_comp = pd.DataFrame(
        [
            {"Métrica": "Combos ofrecidos", "b) espacios separados": v_b, "c) mesadas+alacenas juntas": v_c, "Δ": v_c - v_b},
            {
                "Métrica": "Unidades totales en stock",
                "b) espacios separados": final_b["unidades"],
                "c) mesadas+alacenas juntas": final_c["unidades"],
                "Δ": final_c["unidades"] - final_b["unidades"],
            },
            {
                "Métrica": "Categorías del catálogo cubiertas",
                "b) espacios separados": final_b["categorias"],
                "c) mesadas+alacenas juntas": final_c["categorias"],
                "Δ": final_c["categorias"] - final_b["categorias"],
            },
        ]
    )
    print(t_comp.to_string(index=False))
    if v_c == n_combos:
        print(f"\nSí: la nueva disposición alcanza para ofrecer los {n_combos} combos.")
    else:
        print(f"\nNo: quedan {n_combos - v_c} combos afuera ({faltantes}) aun con mesadas y alacenas juntas.")

    # --- 6. Óptimos alternativos --------------------------------------------------
    titulo("6. ÓPTIMOS ALTERNATIVOS BAJO c) — enumeración exhaustiva sin solver", "-")
    optimos_c = datos.enumerar_factibles(params_c, v_c)
    siguientes_c = datos.enumerar_factibles(params_c, v_c + 1)
    t_opt_c = reportes.tabla_optimos(params_c, optimos_c)
    print(f"Conjuntos de {v_c} combos que entran     : {len(optimos_c):>6} de {comb(n_combos, v_c):,}")
    print(f"Conjuntos de {v_c + 1} combos que entran     : {len(siguientes_c):>6} de {comb(n_combos, v_c + 1):,}")
    print()
    print(t_opt_c.to_string(index=False))

    # --- 7. Capacidad +1 por espacio bajo c): ¿qué más pedir? ---------------------
    titulo("7. CAPACIDAD +1 POR ESPACIO, BAJO c) — ¿qué otras unidades solicitar?", "-")
    filas_cap = []
    for e, d in params_c["espacios"].items():
        probado = construir_params(
            espacios=espacios_mesadas_alacenas_juntas(),
            S1_disponibilidad="compartida",
            capacidades={e: d["capacidad"] + 1},
        )
        r = modelo.resolver(probado)
        filas_cap.append(
            {
                "Espacio": d["nombre"],
                "Capacidad base": d["capacidad"],
                "Capacidad probada": d["capacidad"] + 1,
                "V*": r["variedad"],
                "Delta V*": r["variedad"] - v_c,
            }
        )
    t_cap_c = pd.DataFrame(filas_cap)
    print(t_cap_c.to_string(index=False))

    # --- 8. Controles cruzados ----------------------------------------------------
    titulo("8. CONTROLES CRUZADOS", "-")
    controles = [
        ("V*(c) >= V*(b): unir mesadas y alacenas nunca empeora la variedad", v_c >= v_b),
        (
            f"Fuerza bruta bajo c): hay conjuntos de {v_c} y ninguno de {v_c + 1}",
            bool(optimos_c) and not siguientes_c,
        ),
        ("El desempate no pierde variedad en c)", final_c["variedad"] == v_c),
        (
            "Stock de la solución final de c) = stock necesario (sin sobrante)",
            final_c["stock"] == datos.stock_necesario(params_c, final_c["combos"]),
        ),
        ("La ocupación respeta todas las capacidades en c)", all(h >= 0 for h in final_c["holgura"].values())),
        ("Los combos de la solución final están entre los óptimos enumerados", tuple(final_c["combos"]) in set(optimos_c)),
        ("Capacidad +1 en c): sumar un lugar nunca baja la variedad", (t_cap_c["Delta V*"] >= 0).all()),
        (
            "Mesadas + alacenas nunca limita bajo c) (12 lugares para 8 variantes posibles)",
            final_c["holgura"]["mesadas_alacenas"] > 0,
        ),
    ]
    for descripcion, ok in controles:
        print(f"  [{'OK ' if ok else 'MAL'}] {descripcion}")
    if not all(ok for _, ok in controles):
        print("\nERROR: falló un control cruzado. Revisar el modelo.")
        return 1

    # --- Guardado -------------------------------------------------------------
    tablas = {
        "19_comparacion_b_c": t_comp,
        "20_combos_ofrecidos_c": t_combos_c,
        "21_plan_stock_c": t_stock_c,
        "22_ocupacion_deposito_c": t_esp_c,
        "23_optimos_alternativos_c": t_opt_c,
        "24_test_capacidad_mas_uno_c": t_cap_c,
    }
    archivos = reportes.guardar(tablas, SALIDA)
    titulo("ARCHIVOS GENERADOS", "-")
    for nombre in archivos:
        if nombre.split("_", 1)[0] in {"19", "20", "21", "22", "23", "24"}:
            print(f"  resultados/tablas/{nombre}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
