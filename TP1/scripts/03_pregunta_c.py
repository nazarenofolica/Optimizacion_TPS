"""
Punto c) — Crecimiento de market share contra crecimiento en rentabilidad.

El directorio está partido: los accionistas quieren rentabilidad y los gerentes
quieren facturación (sus bonos dependen de los ingresos). Este script cuantifica
ese conflicto con el método ε-constraint (docs/plan_de_trabajo.md §6.5):

    Max  utilidad neta     sujeto a    facturación >= ε

y barre ε desde la facturación que sale "de arriba" al maximizar utilidad hasta
la máxima facturación alcanzable. Cada solución del barrido es un punto de la
frontera de Pareto: planes donde no se puede ganar más sin vender menos.

El resultado central del punto a) obliga a un giro respecto del plan: con las
reglas del directorio vigentes la frontera NO existe, colapsa en un solo punto
(§3.6). Por eso el barrido se repite en cuatro escenarios, aflojando las reglas
que estrangulan el problema, para mostrar cuánto trade-off aparece con cada una.

    python scripts/03_pregunta_c.py

Salidas: consola, resultados/graficos/03_frontera_pareto.png y
resultados/tablas/08_pregunta_c_frontera_pareto.csv
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
if hasattr(sys.stdout, "reconfigure"):  # consola de Windows en cp1252
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd  # noqa: E402

from src import datos, graficos, modelo, reportes  # noqa: E402
from src.config import construir_params  # noqa: E402

SALIDA = RAIZ / "resultados" / "tablas"

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
pd.set_option("display.float_format", lambda v: f"{v:,.2f}")

#: Escenarios del barrido: qué restricciones se desactivan en cada uno.
#: El primero es el caso real; los otros tres aflojan las reglas del directorio
#: para ver cuánto trade-off aparece cuando el problema deja de estar atado.
ESCENARIOS = {
    "Reglas actuales": [],
    "Sin R3 (30% Triguetti)": ["R3_triguetti_min"],
    "Sin R4 (doble de Rena)": ["R4_rena_doble"],
    "Sin R3 ni R4": ["R3_triguetti_min", "R4_rena_doble"],
}

#: Puntos del barrido de ε por escenario.
PASOS = 13

#: Tolerancia para decidir si la frontera es un punto, en $MM de facturación.
TOL_COLAPSO = 1.0

#: Margen relativo que se le descuenta al último ε del barrido.
#: Pedir exactamente la facturación máxima devuelve "Infeasible": el óptimo la
#: alcanza, pero la tolerancia de factibilidad de CBC deja el piso unas
#: millonésimas por encima de lo alcanzable. Medido sobre este modelo: con 1e-3
#: $MM de margen todavía falla, con 1e-2 ya resuelve. Se usa un margen relativo
#: (~0,11 $MM sobre una facturación de 1.092.333 $MM, es decir 1e-7 del valor)
#: para que el borde siga funcionando si cambian las magnitudes del problema.
MARGEN_EPS_REL = 1e-7
MARGEN_EPS_MIN = 1e-2

#: Columnas largas que se usan en varios lados.
COL_DUAL = "Costo marginal ($MM util / $MM fact)"
COL_PUNTO = "Costo marginal por punto de share ($MM)"


def titulo(texto, caracter="="):
    print(f"\n{caracter * 78}\n{texto}\n{caracter * 78}")


def extremos(params, desactivar):
    """Los dos vértices de la frontera: máxima utilidad y máxima facturación."""
    r_u = modelo.resolver(params, objetivo="neta", desactivar=desactivar)
    r_f = modelo.resolver(params, objetivo="facturacion", desactivar=desactivar)
    return reportes.resumen(r_u), reportes.resumen(r_f)


def barrer(params, nombre, desactivar, mercado_total):
    """Puntos de la frontera de Pareto de un escenario.

    Si la frontera colapsa (la facturación del óptimo de utilidad ya es la máxima
    alcanzable) devuelve un único punto: no hay nada que negociar.
    """
    s_u, s_f = extremos(params, desactivar)
    f_min = s_u["Facturación ($MM)"]
    f_max = s_f["Facturación ($MM)"]
    rango = f_max - f_min

    punto_share = mercado_total / 100  # $MM de facturación por punto de share

    if rango < TOL_COLAPSO:
        return [
            {
                "Escenario": nombre,
                "epsilon ($MM)": f_min,
                "Facturación ($MM)": f_min,
                "Market share (%)": 100 * f_min / mercado_total,
                "Utilidad neta ($MM)": s_u["Utilidad neta ($MM)"],
                COL_DUAL: 0.0,
                COL_PUNTO: 0.0,
            }
        ], rango

    filas = []
    tope = f_max - max(MARGEN_EPS_MIN, abs(f_max) * MARGEN_EPS_REL)
    for n in range(PASOS):
        eps = min(f_min + rango * n / (PASOS - 1), tope)
        res = modelo.resolver(
            params, objetivo="neta", epsilon=eps, desactivar=desactivar
        )
        if res["status"] != "Optimal":
            print(f"  {nombre}: eps={eps:,.0f} -> {res['status']} (se omite)")
            continue
        s = reportes.resumen(res)
        dual = res["duales"].get("EPS_facturacion", 0.0)
        filas.append(
            {
                "Escenario": nombre,
                "epsilon ($MM)": eps,
                "Facturación ($MM)": s["Facturación ($MM)"],
                "Market share (%)": s["Market share (%)"],
                "Utilidad neta ($MM)": s["Utilidad neta ($MM)"],
                COL_DUAL: dual,
                # El dual está en $MM de utilidad por $MM de facturación. Pasarlo a
                # "por punto de share" lo vuelve legible para el directorio.
                COL_PUNTO: -dual * punto_share,
            }
        )
    return filas, rango


def verificar(tabla, params):
    """Controles cruzados de las fronteras.

    Los tres primeros son propiedades que toda frontera de Pareto tiene que
    cumplir: si alguna falla, el barrido está mal armado y los números no sirven.
    El último es el más fuerte: los dos extremos del barrido tienen que coincidir
    con los óptimos que se obtienen resolviendo cada objetivo por separado, sin
    ε-constraint. Si no coinciden, el piso de facturación está mal construido.
    """
    controles = []
    for nombre, grupo in tabla.groupby("Escenario", sort=False):
        u = grupo["Utilidad neta ($MM)"].to_list()
        f = grupo["Facturación ($MM)"].to_list()
        if len(u) == 1:
            controles.append((f"{nombre}: frontera colapsada en 1 punto", True))
            continue
        controles.append(
            (
                f"{nombre}: la utilidad no crece al exigir más facturación",
                all(u[i] >= u[i + 1] - 1e-3 for i in range(len(u) - 1)),
            )
        )
        controles.append(
            (
                f"{nombre}: la facturación crece a lo largo del barrido",
                all(f[i] <= f[i + 1] + 1e-3 for i in range(len(f) - 1)),
            )
        )
        controles.append(
            (
                f"{nombre}: el dual del piso de facturación es <= 0",
                all(v <= 1e-9 for v in grupo[COL_DUAL].to_list()),
            )
        )
    base = tabla[tabla["Escenario"] == "Reglas actuales"]
    controles.append(
        (
            "El caso base reproduce el punto a) ($76.578,60 y 61,91%)",
            abs(base["Utilidad neta ($MM)"].iloc[0] - 76_578.60) < 0.01
            and abs(base["Market share (%)"].iloc[0] - 61.91) < 0.01,
        )
    )
    # Control fuerte: los extremos del barrido contra los óptimos por separado.
    for nombre, desactivar in ESCENARIOS.items():
        g = tabla[tabla["Escenario"] == nombre]
        s_u, s_f = extremos(params, desactivar)
        controles.append(
            (
                f"{nombre}: extremos = óptimos sin ε-constraint",
                abs(g["Utilidad neta ($MM)"].iloc[0] - s_u["Utilidad neta ($MM)"]) < 0.01
                and abs(
                    g["Utilidad neta ($MM)"].iloc[-1] - s_f["Utilidad neta ($MM)"]
                )
                < 1.0,
            )
        )
    for descripcion, ok in controles:
        print(f"  [{'OK ' if ok else 'MAL'}] {descripcion}")
    return all(ok for _, ok in controles)


def tabla_tradeoff(tabla):
    """Una fila por escenario con cuánto share hay en juego y a qué precio."""
    filas = []
    for nombre in ESCENARIOS:
        g = tabla[tabla["Escenario"] == nombre]
        u0, u1 = g["Utilidad neta ($MM)"].iloc[0], g["Utilidad neta ($MM)"].iloc[-1]
        s0, s1 = g["Market share (%)"].iloc[0], g["Market share (%)"].iloc[-1]
        d_share = s1 - s0
        # El costo marginal del primer tramo excluye el punto inicial, donde el
        # piso de facturación todavía no ata y el dual es 0 por construcción.
        marginales = g[COL_PUNTO].iloc[1:] if len(g) > 1 else g[COL_PUNTO]
        filas.append(
            {
                "Escenario": nombre,
                "Share mínimo (%)": s0,
                "Share máximo (%)": s1,
                "Puntos de share en juego": d_share,
                "Utilidad máxima ($MM)": u0,
                "Utilidad en share máx. ($MM)": u1,
                "Utilidad resignada ($MM)": u0 - u1,
                "Costo medio por punto ($MM)": (u0 - u1) / d_share if d_share else 0.0,
                "Costo marginal 1er tramo ($MM)": marginales.min(),
                "Costo marginal último tramo ($MM)": marginales.max(),
            }
        )
    return pd.DataFrame(filas)


def main():
    params = construir_params()
    mercado_total = datos.mercado_total(params)
    punto_share = mercado_total / 100  # $MM de facturación por punto de share

    titulo("PUNTO c) — MARKET SHARE CONTRA RENTABILIDAD")
    print(
        "Método ε-constraint: Max utilidad neta sujeto a facturación >= eps,\n"
        "barriendo eps entre los dos vértices de cada escenario.\n"
        f"\nMercado total de pastas: ${mercado_total:,.0f} MM\n"
        f"1 punto de market share = ${punto_share:,.0f} MM de facturación"
    )

    filas = []
    for nombre, desactivar in ESCENARIOS.items():
        f, _rango = barrer(params, nombre, desactivar, mercado_total)
        filas.extend(f)
    tabla = pd.DataFrame(filas)

    titulo("VERIFICACIÓN DE LAS FRONTERAS", "-")
    if not verificar(tabla, params):
        print("\nERROR: falló un control cruzado. No usar estos números.")
        return 1

    df_tradeoff = tabla_tradeoff(tabla)
    titulo("CUÁNTO TRADE-OFF HAY EN CADA ESCENARIO", "-")
    print(df_tradeoff.to_string(index=False))

    titulo("FRONTERA COMPLETA (todos los puntos del barrido)", "-")
    print(tabla.to_string(index=False))

    titulo("LECTURA PARA EL DIRECTORIO", "-")
    base = df_tradeoff.iloc[0]
    print(
        "  1) Con las reglas vigentes NO hay discusión que tener: la frontera\n"
        f"     colapsa en un punto ({base['Share mínimo (%)']:.2f}% de share, "
        f"${base['Utilidad máxima ($MM)']:,.0f}MM de utilidad).\n"
        "     Accionistas y gerentes quieren cosas distintas, pero el plan óptimo\n"
        "     es el mismo para los dos porque R3 y R4 ya lo fijaron.\n"
    )
    for _, fila in df_tradeoff.iloc[1:].iterrows():
        c_ini = fila["Costo marginal 1er tramo ($MM)"]
        c_fin = fila["Costo marginal último tramo ($MM)"]
        quiebre = "" if abs(c_fin - c_ini) < 1 else (
            f"\n     Y el precio no es constante: arranca en ${c_ini:,.0f}MM por punto "
            f"y salta a ${c_fin:,.0f}MM\n     en el último tramo."
        )
        print(
            f"  2) {fila['Escenario']}: aparecen "
            f"{fila['Puntos de share en juego']:.2f} puntos de share negociables,\n"
            f"     a un costo medio de ${fila['Costo medio por punto ($MM)']:,.0f}MM de "
            f"utilidad por punto.{quiebre}"
        )
    resto = df_tradeoff.iloc[1:]
    mejor = resto.loc[resto["Puntos de share en juego"].idxmax()]
    print(
        f"\n  El margen de negociación más ancho lo da quitar "
        f"{mejor['Escenario'].split('(')[0].strip().replace('Sin ', '')}: "
        f"{mejor['Puntos de share en juego']:.2f} puntos de share.\n"
        "\n  Conclusión: la pelea del directorio no se resuelve eligiendo un objetivo,\n"
        "  se resuelve revisando las reglas que ellos mismos impusieron. Y aun así el\n"
        "  premio es chico: todo el trade-off disponible cabe en poco más de un punto\n"
        "  de participación."
    )

    ruta_grafico = graficos.frontera_pareto(tabla)
    print(f"\nGráfico guardado en: {ruta_grafico.relative_to(RAIZ)}")

    ruta_csv = SALIDA / "08_pregunta_c_frontera_pareto.csv"
    tabla.to_csv(ruta_csv, index=False, encoding="utf-8-sig")
    df_tradeoff.to_csv(
        SALIDA / "09_pregunta_c_resumen_tradeoff.csv", index=False, encoding="utf-8-sig"
    )
    print(f"Tablas guardadas en: {ruta_csv.name} y 09_pregunta_c_resumen_tradeoff.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
