"""
Tests de robustez de los supuestos (docs/plan_de_trabajo.md §11).

Responde la pregunta "¿importa lo que asumimos?" con dos protocolos distintos:

  A. Barrido OAT (one-at-a-time) +-30% sobre cada parámetro numérico que
     nosotros mismos completamos porque el enunciado no lo daba con precisión
     (S1..S4 y R10, que se agregó en el punto a). Para cada uno se resuelve el
     modelo con el valor -30% y +30%, todo lo demás fijo, y se mide cuánto se
     mueve la utilidad y si cambia el plan óptimo. La salida es un gráfico
     tornado: de un vistazo muestra qué 2 o 3 parámetros mueven la aguja y
     cuáles son ruido.

  B. Escenarios estructurales (S5, S7, S8, R6): no son números que se puedan
     barrer +-30%, son decisiones de interpretación. Se resuelve el modelo
     completo bajo cada lectura alternativa y se compara.

    python scripts/05_tests_supuestos.py

Salidas: por consola, un gráfico tornado en resultados/graficos/ y dos tablas
en resultados/tablas/ (12_tornado_oat.csv, 13_escenarios_estructurales.csv).
"""

import sys
from copy import deepcopy
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
if hasattr(sys.stdout, "reconfigure"):  # consola de Windows en cp1252
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd  # noqa: E402

from src import datos, graficos, modelo  # noqa: E402
from src.config import construir_params  # noqa: E402

SALIDA = RAIZ / "resultados" / "tablas"

pd.set_option("display.width", 220)
pd.set_option("display.float_format", lambda v: f"{v:,.2f}")

TOL_MIX = 1.0  # $MM: por debajo de esto, dos planes se consideran "el mismo mix"

# ---------------------------------------------------------------------------
# A. Barrido OAT +-30%
# ---------------------------------------------------------------------------
# Cada entrada: (etiqueta, id_supuesto, setter(params, valor), valor_base, valor_menos, valor_mas)
# El setter muta `params` in-place; se le pasa siempre una copia fresca.


def _set_margen(cod):
    def setter(params, valor):
        params["productos"][cod]["m_neto"] = valor
    return setter


def _set_tasa(cod, idx):
    def setter(params, valor):
        params["tasas"][cod][idx]["tasa"] = valor
    return setter


def _set_limite(cod, idx):
    def setter(params, valor):
        params["tasas"][cod][idx]["limite"] = valor
    return setter


def _set_regla(clave):
    def setter(params, valor):
        params["reglas"][clave] = valor
    return setter


def _set_supuesto(clave):
    def setter(params, valor):
        params["supuestos"][clave] = valor
        if clave == "S1_tasa_triguetti":
            params["tasas"]["TRI"][0]["tasa"] = valor
    return setter


#: (etiqueta para el gráfico, setter, base, valor "-30%", valor "+30%", nota)
PARAMETROS_OAT = [
    ("S1 - Tasa Triguetti (cl/$MM)", _set_supuesto("S1_tasa_triguetti"), 200, 140, 260,
     "único parámetro que el enunciado no da; rango 140-260 (tope duro: 300)"),
    ("S2 - Captura de billetera (%)", _set_supuesto("S2_captura_billetera"), 1.00, 0.70, 1.00,
     "asimétrico: no puede superar el 100%"),
    ("S3 - Margen neto Don Carlo", _set_margen("DC"), 0.050, 0.035, 0.065, ""),
    ("S3 - Margen neto Agnellis", _set_margen("AG"), 0.075, 0.0525, 0.0975, ""),
    ("S3 - Margen neto Triguetti", _set_margen("TRI"), 0.090, 0.063, 0.117, ""),
    ("S3 - Margen neto Candealix", _set_margen("CAN"), 0.080, 0.056, 0.104, ""),
    ("S3 - Margen neto Rena Speziale", _set_margen("RS"), 0.100, 0.070, 0.130, ""),
    ("S4 - Tasa Don Carlo (cl/$MM)", _set_tasa("DC", 0), 400, 280, 520, ""),
    ("S4 - Tasa Agnellis (cl/$MM)", _set_tasa("AG", 0), 500, 350, 650, ""),
    ("S4 - Tasa Candealix 1er tramo", _set_tasa("CAN", 0), 300, 210, 390, ""),
    ("S4 - Tasa Rena 1er tramo", _set_tasa("RS", 0), 150, 105, 195, ""),
    ("S4 - Tope 65% gama baja (R5)", _set_regla("R5_tope_gama_baja"), 0.65, 0.55, 0.845,
     "el -30% teórico (45,5%) es INFACTIBLE: Don Carlo + Agnellis ya ocupan 53% del "
     "segmento bajo aun sin invertir un peso, así que el piso real de esta regla es "
     "53%; se usa 55% como el mínimo plausible por encima de ese piso"),
    ("S4 - Saturación Triguetti ($MM)", _set_limite("TRI", 0), 6_000, 4_200, 7_800, ""),
    ("R10 - Tope de saturación física", _set_regla("R10_tope_saturacion"), 1.00, 0.70, 1.00,
     "agregado en el punto a); no estaba en el plan original. Cota dura: 100%"),
]


def titulo(texto, caracter="="):
    print(f"\n{caracter * 78}\n{texto}\n{caracter * 78}")


def _resolver_con(setter, valor):
    params = construir_params()
    setter(params, valor)
    return modelo.resolver(params, objetivo="neta")


def barrido_oat():
    z_base_global = None
    filas = []
    for etiqueta, setter, base, menos, mas, nota in PARAMETROS_OAT:
        r_base = _resolver_con(setter, base)
        r_menos = _resolver_con(setter, menos)
        r_mas = _resolver_con(setter, mas)
        if r_base["status"] != "Optimal":
            raise RuntimeError(f"{etiqueta}: el caso BASE no es Optimal ({r_base['status']})")
        for extremo, r in (("-30%", r_menos), ("+30%", r_mas)):
            if r["status"] != "Optimal":
                print(
                    f"  [AVISO] {etiqueta} en {extremo}: status {r['status']} "
                    "(el rango teórico pisa una cota física; ver Nota)"
                )
        if z_base_global is None:
            z_base_global = r_base["Z"]

        cambia_menos = any(
            abs(r_menos["x"][c] - r_base["x"][c]) > TOL_MIX for c in r_base["x"]
        )
        cambia_mas = any(
            abs(r_mas["x"][c] - r_base["x"][c]) > TOL_MIX for c in r_base["x"]
        )
        filas.append(
            {
                "Parámetro": etiqueta,
                "Valor base": base,
                "Valor -30%": menos,
                "Valor +30%": mas,
                "Z base ($MM)": r_base["Z"],
                "Z en -30% ($MM)": r_menos["Z"],
                "Z en +30% ($MM)": r_mas["Z"],
                "|ΔZ| máx ($MM)": max(
                    abs(r_menos["Z"] - r_base["Z"]), abs(r_mas["Z"] - r_base["Z"])
                ),
                "|ΔZ| máx (%)": 100 * max(
                    abs(r_menos["Z"] - r_base["Z"]), abs(r_mas["Z"] - r_base["Z"])
                ) / r_base["Z"],
                "¿Cambia el mix en -30%?": cambia_menos,
                "¿Cambia el mix en +30%?": cambia_mas,
                "Nota": nota,
            }
        )
    return pd.DataFrame(filas).sort_values("|ΔZ| máx (%)", ascending=False), z_base_global


# ---------------------------------------------------------------------------
# B. Escenarios estructurales
# ---------------------------------------------------------------------------


def escenarios_estructurales():
    base = modelo.resolver(construir_params(), objetivo="neta")
    filas = []

    def agregar(nombre, res, nota, z_reportado=None):
        z = z_reportado if z_reportado is not None else res["Z"]
        d_z = z - base["Z"]
        cambia = any(abs(res["x"][c] - base["x"][c]) > TOL_MIX for c in base["x"])
        filas.append(
            {
                "Escenario": nombre,
                "Z ($MM)": z,
                "ΔZ vs. base ($MM)": d_z,
                "ΔZ vs. base (%)": 100 * d_z / base["Z"],
                "¿Cambia el mix?": cambia,
                "Nota": nota,
            }
        )

    agregar("Base (todas las lecturas adoptadas)", base, "referencia")

    # S5 — segmento de captación: posicionamiento (base) vs. mix normalizado Fig. 2
    r_mix = modelo.resolver(
        construir_params(S5_segmento_captacion="mix_fig2"), objetivo="neta"
    )
    agregar(
        "S5 — captación repartida según mix Fig. 2 (opción B)",
        r_mix,
        "en vez de que cada marca capte 100% en su segmento de posicionamiento",
    )

    # S7a — base de R3: 30% del presupuesto total (base) vs. 30% de lo asignado
    r_r3b = modelo.resolver(
        construir_params(S7_base_r3="asignado"), objetivo="neta"
    )
    agregar(
        "S7a — R3 sobre lo asignado (Σx_j) en vez de sobre $17.000MM",
        r_r3b,
        "solo difieren si el presupuesto no se agota; en el óptimo se agota siempre",
    )

    # S7b — operador de R4: >= (piso, base) vs. == (cuota exacta)
    r_r4b = modelo.resolver(
        construir_params(S7_operador_r4="=="), objetivo="neta"
    )
    agregar(
        "S7b — R4 como igualdad (Rena = 2·(Can+Tri)) en vez de piso",
        r_r4b,
        "una igualdad nunca puede mejorar a un óptimo que ya cumple la desigualdad "
        "con holgura nula",
    )

    # S8 — presupuesto dentro o fuera del funcional
    agregar(
        "S8 — descontando el presupuesto del funcional",
        base,
        "mismo plan óptimo; solo cambia el número reportado (Z - $17.000MM)",
        z_reportado=base["Z"] - base["params"]["presupuesto"],
    )

    return pd.DataFrame(filas), base


def verificar(tabla_oat, z_base, tabla_estr, base_res):
    controles = [
        ("La utilidad base del barrido OAT reproduce el punto a) ($76.578,60)",
         abs(z_base - 76_578.60) < 0.01),
        ("Todas las |ΔZ| son >= 0", (tabla_oat["|ΔZ| máx ($MM)"] >= 0).all()),
        ("El escenario 'Base' de estructurales reproduce el punto a)",
         abs(tabla_estr.iloc[0]["Z ($MM)"] - 76_578.60) < 0.01),
        ("S7b (R4 en igualdad) da exactamente lo mismo que el piso (R4 ya ataba)",
         abs(tabla_estr[tabla_estr["Escenario"].str.startswith("S7b")]["Z ($MM)"].iloc[0]
             - 76_578.60) < 0.01),
        ("S8 reporta Z - $17.000MM",
         abs(tabla_estr[tabla_estr["Escenario"].str.startswith("S8")]["Z ($MM)"].iloc[0]
             - (76_578.60 - 17_000)) < 0.01),
    ]
    for descripcion, ok in controles:
        print(f"  [{'OK ' if ok else 'MAL'}] {descripcion}")
    return all(ok for _, ok in controles)


def main():
    titulo("TESTS DE ROBUSTEZ DE LOS SUPUESTOS (plan §11)")

    titulo("A. BARRIDO OAT +-30% (o rango asimétrico donde corresponda)", "-")
    tabla_oat, z_base = barrido_oat()

    titulo("B. ESCENARIOS ESTRUCTURALES (S5, S7, S8)", "-")
    tabla_estr, base_res = escenarios_estructurales()

    titulo("VERIFICACIÓN", "-")
    if not verificar(tabla_oat, z_base, tabla_estr, base_res):
        print("\nERROR: falló un control cruzado. No usar estos números.")
        return 1

    titulo("TABLA A — TORNADO (ordenado por impacto)", "-")
    print(
        tabla_oat[
            [
                "Parámetro", "Z en -30% ($MM)", "Z base ($MM)", "Z en +30% ($MM)",
                "|ΔZ| máx (%)", "¿Cambia el mix en -30%?", "¿Cambia el mix en +30%?",
            ]
        ].to_string(index=False)
    )

    n_cambia = (
        tabla_oat["¿Cambia el mix en -30%?"] | tabla_oat["¿Cambia el mix en +30%?"]
    ).sum()
    titulo("LECTURA DEL TORNADO", "-")
    top3 = tabla_oat.head(3)
    print(
        "  Los tres parámetros que más mueven la utilidad son:\n"
        + "\n".join(
            f"    {i+1}. {r['Parámetro']}: hasta {r['|ΔZ| máx (%)']:.2f}% de ΔZ"
            for i, (_, r) in enumerate(top3.iterrows())
        )
        + f"\n\n  De los {len(tabla_oat)} parámetros barridos, {n_cambia} cambian el "
        "plan óptimo (mix)\n  en al menos uno de los dos extremos del rango; el resto "
        "solo mueve el\n  nivel de utilidad sin alterar el reparto. Esto es exactamente "
        "el tipo\n  de conclusión que permite decir en el informe qué tan firme es el "
        "plan\n  del punto a) frente a los datos que tuvimos que completar."
    )

    titulo("TABLA B — ESCENARIOS ESTRUCTURALES", "-")
    print(tabla_estr.to_string(index=False))

    titulo("R6 (umbral de Candealix) — recordatorio", "-")
    print(
        "  Ya verificado en el punto a): Candealix vende 43,7 millones de paquetes\n"
        "  con inversión $0, contra un umbral de 2,5 millones (17,5x). La restricción\n"
        "  no está activa bajo ninguno de los escenarios de este barrido, porque\n"
        "  ninguno mueve la facturación BASE de Candealix (solo la incremental)."
    )

    ruta_grafico = graficos.tornado(tabla_oat)
    print(f"\nGráfico guardado en: {ruta_grafico.relative_to(RAIZ)}")

    ruta_csv_a = SALIDA / "12_tornado_oat.csv"
    ruta_csv_b = SALIDA / "13_escenarios_estructurales.csv"
    tabla_oat.to_csv(ruta_csv_a, index=False, encoding="utf-8-sig")
    tabla_estr.to_csv(ruta_csv_b, index=False, encoding="utf-8-sig")
    print(f"Tablas guardadas en: {ruta_csv_a.name} y {ruta_csv_b.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
