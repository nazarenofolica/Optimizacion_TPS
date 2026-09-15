"""
Punto d) — ¿Está mal la decisión histórica de invertir al menos el 30% del
presupuesto de marketing en Triguetti?

La respuesta que pide el enunciado es una opinión, pero fundamentada en números.
Este script arma esa fundamentación en tres pasos:

  1. El precio sombra de R3 en el caso base (ya calculado en el punto a):
     cada millón obligado a Triguetti cuesta $2,49225 de utilidad. Pero ese
     número es engañoso si se lee como "el costo de Triguetti": Triguetti por
     sí solo rinde 1,044 de utilidad por $MM. El costo real viene de que R4
     encadena Rena Speziale a Triguetti (Rena >= 2 x Triguetti), así que cada
     peso que entra a Triguetti arrastra dos pesos obligados a Rena, que ya
     está saturada (punto a), §3.4). Este script separa ambos efectos.
  2. Un barrido del piso mínimo (0%, 10%, 20%, 30%, 40%) para graficar cuánta
     utilidad se resigna a medida que la regla se pone más exigente.
  3. Un test del supuesto S1 (la tasa de Triguetti que el enunciado no da,
     140-260 cl/$MM): si la conclusión se sostiene en todo ese rango, es
     robusta pese al dato faltante.

    python scripts/04_pregunta_d.py

Salidas: por consola, un gráfico en resultados/graficos/ y una tabla en
resultados/tablas/10_pregunta_d_triguetti.csv
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

pd.set_option("display.width", 200)
pd.set_option("display.float_format", lambda v: f"{v:,.2f}")

#: Pisos mínimos de Triguetti a barrer, como fracción del presupuesto total.
#: 0,30 es el caso base (el punto a)); el resto son las alternativas que el
#: gerente de la pregunta d) tendría en mente. 0,40 se deja adentro a propósito:
#: da Infeasible, y ese resultado es un hallazgo (ver `LIMITE_TEORICO` abajo).
PISOS = [0.00, 0.10, 0.20, 0.30, 0.40]

#: Piso teórico de infactibilidad de R3, deducido a mano: con Candealix en su
#: mínimo (0), R4 exige Rena >= 2 x Triguetti, así que Triguetti + Rena >=
#: 3 x Triguetti >= 3 x (pct x presupuesto). Para que quepa en el presupuesto,
#: 3 x pct <= 1  =>  pct <= 1/3. Pasado ese punto, R3 y R4 exigen entre las dos
#: más plata de la que hay: ya no es un problema de optimizar, es que las reglas
#: del directorio se contradicen entre sí.
LIMITE_TEORICO_R3 = 1 / 3

#: Rango de test del supuesto S1 (tasa de Triguetti, plan §4.1): 140-260 cl/$MM,
#: con 200 como valor base adoptado.
TASAS_S1 = [140, 170, 200, 230, 260]


def titulo(texto, caracter="="):
    print(f"\n{caracter * 78}\n{texto}\n{caracter * 78}")


def fila_piso(pct):
    """Resuelve el modelo con el piso de Triguetti fijado en `pct` del presupuesto."""
    params = construir_params(R3_pct_triguetti=pct)
    res = modelo.resolver(params, objetivo="neta")
    if res["status"] != "Optimal":
        return None
    dual_r3 = res["duales"].get("R3_triguetti_min", 0.0)
    return {
        "% mínimo Triguetti": 100 * pct,
        "Triguetti ($MM)": res["x"]["TRI"],
        "Rena Speziale ($MM)": res["x"]["RS"],
        "Don Carlo ($MM)": res["x"]["DC"],
        "Agnellis ($MM)": res["x"]["AG"],
        "Candealix ($MM)": res["x"]["CAN"],
        "Inversión estéril ($MM)": sum(reportes.desperdicio(res).values()),
        "Utilidad neta ($MM)": res["Z"],
        "Market share (%)": 100
        * sum(reportes.facturacion(res)[2].values())
        / datos.mercado_total(params),
        "Precio sombra R3": dual_r3,
    }


def descomponer_costo_r3(params):
    """Separa el precio sombra de R3 en "efecto Triguetti" y "efecto arrastre a Rena".

    Reconstrucción a mano (docs/procedimiento.md §6.3, misma lógica que el resto de los
    duales del punto a): en el óptimo, R3 y R4 están activas y el único destino
    libre para un millón adicional es el par Don Carlo/Agnellis. Forzar un millón
    extra a Triguetti por R3 dispara, vía R4, dos millones extra obligatorios a
    Rena. Ese millón y esos dos millones salen de restarle presupuesto al par
    gama baja, que es el "precio de oportunidad" de la plata en este modelo.
    """
    coefs = datos.coeficientes(params, "neta")
    r_par = 0.5 * (coefs[("DC", 1)] + coefs[("AG", 1)])  # rinde el par gama baja
    r_tri = coefs[("TRI", 1)]  # lo que rinde Triguetti en su primer tramo
    mult = params["reglas"]["R4_multiplo_rena"]

    efecto_triguetti = r_tri - r_par  # ganás Triguetti, perdés un $MM de par
    efecto_arrastre = -mult * r_par  # los "mult" $MM extra a Rena son estériles
    total = efecto_triguetti + efecto_arrastre
    return r_par, r_tri, efecto_triguetti, efecto_arrastre, total


def verificar(tabla, params_base):
    """Controles cruzados de la pregunta d)."""
    base = tabla[tabla["% mínimo Triguetti"] == 30.0].iloc[0]
    sin_r3 = tabla[tabla["% mínimo Triguetti"] == 0.0].iloc[0]

    r_par, r_tri, ef_tri, ef_arr, total = descomponer_costo_r3(params_base)

    controles = [
        ("El caso base (30%) reproduce el punto a) ($76.578,60)",
         abs(base["Utilidad neta ($MM)"] - 76_578.60) < 0.01),
        ("La utilidad cae monótonamente al subir el piso de Triguetti",
         all(tabla["Utilidad neta ($MM)"].diff().dropna() <= 1e-6)),
        ("Sin la regla (0%), Triguetti queda en $0",
         abs(sin_r3["Triguetti ($MM)"]) < 1e-3),
        ("La descomposición del dual de R3 reproduce -2,49225",
         abs(total - (-2.49225)) < 1e-4),
        ("El dual de R3 reportado por PuLP coincide con la descomposición a mano",
         abs(base["Precio sombra R3"] - total) < 1e-3),
    ]
    for descripcion, ok in controles:
        print(f"  [{'OK ' if ok else 'MAL'}] {descripcion}")
    return all(ok for _, ok in controles), (r_par, r_tri, ef_tri, ef_arr, total)


def main():
    titulo("PUNTO d) — ¿ESTÁ MAL EL 30% OBLIGATORIO EN TRIGUETTI?")
    params_base = construir_params()

    print(
        "Se resuelve el modelo con distintos pisos mínimos para Triguetti\n"
        "(0%, 10%, 20%, 30% -caso base-, 40%) y se descompone el precio sombra\n"
        "de R3 en lo que aporta Triguetti por sí solo y lo que arrastra a Rena\n"
        "Speziale por la regla R4 (Rena >= 2 x (Candealix + Triguetti))."
    )

    filas = [fila_piso(p) for p in PISOS]
    infactibles = [PISOS[i] for i, f in enumerate(filas) if f is None]
    tabla = pd.DataFrame([f for f in filas if f is not None])

    if infactibles:
        titulo("HALLAZGO: EL MODELO SE VUELVE INFACTIBLE ARRIBA DE 1/3", "-")
        print(
            f"  Los pisos {[f'{100*p:.0f}%' for p in infactibles]} no tienen solución.\n"
            "  No es un problema numérico: es que R3 y R4 juntas exigen más\n"
            "  presupuesto del que existe. Con Candealix en su mínimo (Rena solo\n"
            "  tiene que igualar a Triguetti):\n\n"
            "      Triguetti + Rena  >=  Triguetti + 2 x Triguetti  =  3 x Triguetti\n"
            "      3 x Triguetti  <=  $17.000MM   =>   Triguetti  <=  $5.666,67MM\n"
            f"      =>  el piso de Triguetti no puede pasar de {100*LIMITE_TEORICO_R3:.2f}% "
            "del presupuesto\n\n"
            "  Es la versión más extrema del hallazgo de §7.2 del plan: la regla del\n"
            "  30% ya usa 9 de cada 10 puntos de margen que existen antes de que el\n"
            "  problema deje de tener solución. Si mañana el directorio quisiera subir\n"
            "  el piso al 35% o al 40%, ni siquiera haría falta correr el modelo para\n"
            "  saber que no hay ningún plan -de ningún tipo- que cumpla las dos reglas\n"
            "  a la vez."
        )

    titulo("VERIFICACIÓN", "-")
    ok, (r_par, r_tri, ef_tri, ef_arr, total) = verificar(tabla, params_base)
    if not ok:
        print("\nERROR: falló un control cruzado. No usar estos números.")
        return 1

    titulo("TABLA: BARRIDO DEL PISO MÍNIMO DE TRIGUETTI", "-")
    print(tabla.to_string(index=False))

    titulo("DESCOMPOSICIÓN DEL COSTO DE R3 (precio sombra = -2,49225)", "-")
    print(
        f"  Rendimiento del par Don Carlo/Agnellis (destino libre)  : {r_par:8.4f} $/$MM\n"
        f"  Rendimiento de Triguetti, 1er tramo                     : {r_tri:8.4f} $/$MM\n"
        f"  (a) Efecto directo -ganar Triguetti, perder 1 MM de par-: {ef_tri:+8.4f} $/$MM\n"
        f"  (b) Efecto arrastre -perder 2 MM de par por R4-         : {ef_arr:+8.4f} $/$MM\n"
        f"  Costo total del millón forzado a Triguetti              : {total:+8.4f} $/$MM\n"
        "\n  Lectura: Triguetti en sí mismo casi no cuesta nada -su primer tramo\n"
        "  rinde casi lo mismo que el par gama baja-. Lo caro es el arrastre:\n"
        "  por cada millón que entra a Triguetti, R4 obliga a poner DOS millones\n"
        "  más en Rena, que ya tiene saturado su segmento (punto a, §3.4) y no\n"
        "  capta un solo cliente adicional. El verdadero costo de la regla del\n"
        "  30% es indirecto y triplicado, no un problema de Triguetti."
    )

    base = tabla[tabla["% mínimo Triguetti"] == 30.0].iloc[0]
    sin_regla = tabla[tabla["% mínimo Triguetti"] == 0.0].iloc[0]
    ganancia = sin_regla["Utilidad neta ($MM)"] - base["Utilidad neta ($MM)"]
    titulo("CUÁNTO SE GANARÍA SACANDO LA REGLA POR COMPLETO", "-")
    print(
        f"  Utilidad neta con 30% (caso base) : ${base['Utilidad neta ($MM)']:,.2f} MM\n"
        f"  Utilidad neta sin la regla (0%)   : ${sin_regla['Utilidad neta ($MM)']:,.2f} MM\n"
        f"  Ganancia de sacar la regla        : ${ganancia:,.2f} MM "
        f"(+{100 * ganancia / base['Utilidad neta ($MM)']:.2f}%)\n"
        f"  Inversión estéril con 30%         : ${base['Inversión estéril ($MM)']:,.2f} MM "
        f"({100 * base['Inversión estéril ($MM)'] / 17_000:.2f}% del presupuesto)\n"
        f"  Inversión estéril sin la regla    : ${sin_regla['Inversión estéril ($MM)']:,.2f} MM"
    )

    # --- Test de robustez: ¿la conclusión depende del supuesto S1? ----------
    titulo("TEST DE ROBUSTEZ — SUPUESTO S1 (tasa de Triguetti, 140 a 260 cl/$MM)", "-")
    filas_s1 = []
    for tasa in TASAS_S1:
        p = construir_params(S1_tasa_triguetti=tasa)
        r_con = modelo.resolver(p, objetivo="neta")
        r_sin = modelo.resolver(p, objetivo="neta", desactivar=["R3_triguetti_min"])
        filas_s1.append(
            {
                "S1 (cl/$MM)": tasa,
                "Utilidad con 30% ($MM)": r_con["Z"],
                "Utilidad sin regla ($MM)": r_sin["Z"],
                "Costo de la regla ($MM)": r_sin["Z"] - r_con["Z"],
            }
        )
    tabla_s1 = pd.DataFrame(filas_s1)
    print(tabla_s1.to_string(index=False))
    costo_min, costo_max = (
        tabla_s1["Costo de la regla ($MM)"].min(),
        tabla_s1["Costo de la regla ($MM)"].max(),
    )
    print(
        f"\n  El costo de la regla se mueve entre ${costo_min:,.2f}MM y ${costo_max:,.2f}MM\n"
        "  en todo el rango plausible de S1: la conclusión (la regla cuesta caro y\n"
        "  el motivo es el arrastre a Rena, no Triguetti en sí) NO depende del\n"
        "  dato que el enunciado no da. Es un resultado robusto."
    )

    titulo("RESPUESTA A LA PREGUNTA DEL GERENTE", "-")
    print(
        "  El gerente tiene razón en el número: la regla del 30% cuesta caro,\n"
        f"  del orden de ${ganancia:,.0f}MM al año, y encima obliga a quemar\n"
        f"  ${base['Inversión estéril ($MM)']:,.0f}MM sin captar un cliente. Pero no tiene\n"
        "  razón en el diagnóstico: la culpa no es de Triguetti -que rinde casi\n"
        "  lo mismo que el resto del portafolio- sino de la regla R4, que ata a\n"
        "  Rena Speziale al tamaño de Triguetti en un segmento premium que ya está\n"
        "  saturado. El modelo, además, solo mide un año: lo que la regla del 30%\n"
        "  protege -identidad de marca, presencia en góndola, poder de\n"
        "  negociación con supermercados y almacenes- no entra en el funcional.\n"
        "  La respuesta correcta no es 'sacar la regla', es: 'la regla cuesta\n"
        f"  ${ganancia:,.0f}MM al año; que el directorio decida si esa presencia de\n"
        "  marca vale más que esa plata'. Eso es análisis, no aritmética."
    )

    ruta_grafico = graficos.utilidad_vs_pct_triguetti(tabla)
    print(f"\nGráfico guardado en: {ruta_grafico.relative_to(RAIZ)}")

    ruta_csv = SALIDA / "10_pregunta_d_triguetti.csv"
    tabla.to_csv(ruta_csv, index=False, encoding="utf-8-sig")
    tabla_s1.to_csv(
        SALIDA / "11_pregunta_d_test_s1.csv", index=False, encoding="utf-8-sig"
    )
    print(f"Tablas guardadas en: {ruta_csv.name} y 11_pregunta_d_test_s1.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
