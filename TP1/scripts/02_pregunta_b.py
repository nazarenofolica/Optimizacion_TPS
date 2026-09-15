"""
Punto b) — Escenarios en que Agnellis aumente su participación.

La restricción R2 del modelo base lee la paridad Don Carlo/Agnellis como igualdad
estricta (supuesto S6, docs/plan_de_trabajo.md §4.2): x_DonCarlo = x_Agnellis. Esta
pregunta es, literalmente, el test de ese supuesto: en lugar de la igualdad se
parametriza x_DonCarlo = k * x_Agnellis y se barre k desde 1.0 (paridad total, el
caso base del punto a) hasta 0.0 (toda la plata libre del par gama baja va a
Agnellis), reutilizando el mismo modelo de src/modelo.py sin copiarlo.

Responde las dos cosas que pide el enunciado:
  - cuánta inversión necesita Don Carlo para no perder presencia significativa
  - qué efecto tiene esto en la utilidad total

    python scripts/02_pregunta_b.py

Salidas: por consola, un gráfico en resultados/graficos/ y una tabla en
resultados/tablas/07_pregunta_b_escenarios_agnellis.csv
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

#: k = x_DonCarlo / x_Agnellis. k=1.00 es el caso base (R2 tal como está en el
#: punto a)). Valores menores simulan que Agnellis crece más rápido que Don Carlo;
#: k=0.00 es el extremo en que Don Carlo no recibe nada del presupuesto libre.
VALORES_K = [1.00, 0.90, 0.75, 0.60, 0.50, 0.40, 0.30, 0.20, 0.10, 0.00]


def titulo(texto, caracter="="):
    print(f"\n{caracter * 78}\n{texto}\n{caracter * 78}")


def fila_de(k, res):
    """Una fila del barrido, con las DOS métricas de presencia.

    La distinción es el corazón de la respuesta (ver docs/procedimiento.md §5.1):

    - "solo campaña" mide la presencia dentro de los clientes que la publicidad
      de este año capta. Es la métrica sensible a k, pero ignora que Don Carlo
      arranca con 7,5 millones de clientes.
    - "base + campaña" mide la presencia en el mercado real, sumando la base
      instalada. Es la que responde lo que pregunta el enunciado.
    """
    params = res["params"]
    _base, _incremental, total = reportes.facturacion(res)
    clientes = reportes.clientes_captados(res)
    base_cl = reportes.clientes_base(params)
    mercado_total = datos.mercado_total(params)
    tam_bajo = params["mercado"]["bajo"]["tam"]

    cl_dc, cl_ag = clientes["DC"], clientes["AG"]
    tot_dc, tot_ag = base_cl["DC"] + cl_dc, base_cl["AG"] + cl_ag

    nuevos = cl_dc + cl_ag
    presencia_campana = cl_dc / nuevos if nuevos else float("nan")
    presencia_real = tot_dc / (tot_dc + tot_ag)

    holgura_r5 = res["holguras"].get("R5_tope_gama_baja")
    return {
        "k": k,
        "Don Carlo ($MM)": res["x"]["DC"],
        "Agnellis ($MM)": res["x"]["AG"],
        "Clientes Don Carlo": cl_dc,
        "Clientes Agnellis": cl_ag,
        "Presencia DC solo campaña (%)": 100 * presencia_campana,
        "Presencia DC base+campaña (%)": 100 * presencia_real,
        "Share DC en segmento bajo (%)": 100 * tot_dc / tam_bajo,
        "Utilidad neta ($MM)": res["Z"],
        "Market share (%)": 100 * sum(total.values()) / mercado_total,
        "R5 holgura (clientes)": holgura_r5,
        "R5 activa": holgura_r5 is not None and abs(holgura_r5) < 1e-6,
    }


def verificar(tabla, params):
    """Controles cruzados del barrido, al estilo de 01_modelo_base.py.

    El más importante es el primero: la presencia dentro de la campaña NO es
    lineal en k, es la hipérbola r_DC·k / (r_DC·k + r_AG). Documentarla como
    lineal fue el error que originó esta corrección.
    """
    tasas = {cod: params["tasas"][cod][0]["tasa"] for cod in ("DC", "AG")}
    r_dc, r_ag = tasas["DC"], tasas["AG"]

    def cerrada(k):
        return 100 * r_dc * k / (r_dc * k + r_ag)

    err_forma = max(
        abs(f["Presencia DC solo campaña (%)"] - cerrada(f["k"]))
        for _, f in tabla.iterrows()
    )
    z = tabla["Utilidad neta ($MM)"]
    base, libre = tabla.iloc[0], tabla.iloc[-1]

    controles = [
        (f"Presencia campaña = {r_dc}k/({r_dc}k+{r_ag}) (err max {err_forma:.2e})",
         err_forma < 1e-6),
        ("k=1 reproduce el caso base ($76.578,60)",
         abs(base["Utilidad neta ($MM)"] - 76_578.60) < 0.01),
        ("La utilidad crece al bajar k (monótona)",
         all(z.iloc[i] <= z.iloc[i + 1] + 1e-6 for i in range(len(z) - 1))),
        ("Don Carlo + Agnellis = $1.700MM en todo el barrido",
         all(abs(f["Don Carlo ($MM)"] + f["Agnellis ($MM)"] - 1_700) < 1e-3
             for _, f in tabla.iterrows())),
        ("Ganancia de k=1 a k=0 = +$609,88MM",
         abs((libre["Utilidad neta ($MM)"] - base["Utilidad neta ($MM)"]) - 609.875) < 0.01),
        ("La presencia real (base+campaña) se mueve menos de 5 puntos",
         abs(base["Presencia DC base+campaña (%)"]
             - libre["Presencia DC base+campaña (%)"]) < 5),
    ]
    for descripcion, ok in controles:
        print(f"  [{'OK ' if ok else 'MAL'}] {descripcion}")
    return all(ok for _, ok in controles)


def main():
    titulo("PUNTO b) — ESCENARIOS DE CRECIMIENTO DE AGNELLIS")
    print(
        "Se reemplaza R2 (x_DonCarlo = x_Agnellis, supuesto S6) por\n"
        "x_DonCarlo = k * x_Agnellis, y se barre k de 1.0 (paridad, caso base)\n"
        "a 0.0 (toda la plata libre del par gama baja va a Agnellis)."
    )

    filas = []
    for k in VALORES_K:
        params = construir_params(S6_paridad_dc_ag=k)
        res = modelo.resolver(params, objetivo="neta")
        if res["status"] != "Optimal":
            print(f"  k={k}: status {res['status']} (se omite)")
            continue
        filas.append(fila_de(k, res))

    tabla = pd.DataFrame(filas)

    titulo("VERIFICACIÓN DEL BARRIDO", "-")
    if not verificar(tabla, construir_params()):
        print("\nERROR: falló un control cruzado. No usar estos números.")
        return 1

    titulo("TABLA: UTILIDAD Y REPARTO DON CARLO / AGNELLIS SEGÚN k", "-")
    print(tabla.to_string(index=False))

    base, libre = tabla.iloc[0], tabla.iloc[-1]  # k=1.0 y k=0.0
    ganancia = libre["Utilidad neta ($MM)"] - base["Utilidad neta ($MM)"]
    titulo("LECTURA: DE LA PARIDAD (k=1) A SOLTAR TODO A AGNELLIS (k=0)", "-")
    print(
        f"  Utilidad neta   : ${base['Utilidad neta ($MM)']:,.2f} MM -> "
        f"${libre['Utilidad neta ($MM)']:,.2f} MM  "
        f"(+${ganancia:,.2f} MM, +{100 * ganancia / base['Utilidad neta ($MM)']:.3f}%)\n"
        f"  Don Carlo       : ${base['Don Carlo ($MM)']:,.2f} MM -> "
        f"${libre['Don Carlo ($MM)']:,.2f} MM\n"
        f"  Agnellis        : ${base['Agnellis ($MM)']:,.2f} MM -> "
        f"${libre['Agnellis ($MM)']:,.2f} MM\n"
    )

    titulo("LAS DOS MEDIDAS DE 'PRESENCIA' DE DON CARLO", "-")
    caida = lambda col: base[col] - libre[col]
    print(
        "  El enunciado pide evitar una 'pérdida significativa de su presencia'.\n"
        "  Según cómo se mida, la respuesta cambia por completo:\n\n"
        f"  {'':34s}k=1,00    k=0,00      cae\n"
        f"  {'Solo la campaña de este año':34s}"
        f"{base['Presencia DC solo campaña (%)']:6.2f}%   "
        f"{libre['Presencia DC solo campaña (%)']:6.2f}%   "
        f"{caida('Presencia DC solo campaña (%)'):6.2f} pts\n"
        f"  {'Base instalada + campaña':34s}"
        f"{base['Presencia DC base+campaña (%)']:6.2f}%   "
        f"{libre['Presencia DC base+campaña (%)']:6.2f}%   "
        f"{caida('Presencia DC base+campaña (%)'):6.2f} pts\n"
        f"  {'Share del segmento bajo':34s}"
        f"{base['Share DC en segmento bajo (%)']:6.2f}%   "
        f"{libre['Share DC en segmento bajo (%)']:6.2f}%   "
        f"{caida('Share DC en segmento bajo (%)'):6.2f} pts\n\n"
        "  Don Carlo tiene 7.525.000 clientes de base y la campaña entera mueve\n"
        "  340.000 (el 4,5%). Medida sobre el mercado real, su presencia casi no\n"
        "  se mueve aunque no reciba un solo peso."
    )

    activa = tabla[tabla["R5 activa"]]
    if len(activa):
        print(f"\n  R5 (tope 65% gama baja) se activa a partir de k <= {activa['k'].max()}")
    else:
        print(
            "\n  R5 (tope 65% gama baja) no se activa en ningún escenario del "
            "barrido: el freno nunca es el mercado, es el presupuesto residual "
            "que dejan libre R3 y R4 (ver docs/procedimiento.md §3.5)."
        )

    ruta_grafico = graficos.utilidad_vs_k_paridad(tabla)
    print(f"\nGráfico guardado en: {ruta_grafico.relative_to(RAIZ)}")

    ruta_csv = SALIDA / "07_pregunta_b_escenarios_agnellis.csv"
    tabla.to_csv(ruta_csv, index=False, encoding="utf-8-sig")
    print(f"Tabla guardada en: {ruta_csv.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
