"""
Tests de supuestos del punto a) (docs/plan_de_trabajo.md §11).

  A. Capacidad +1 por espacio y barrido de mesadas  (§11.1)  — reemplaza a los precios sombra
  B. Lectura de "disponible": exclusiva vs. compartida (S1)  (§11.2)
  C. Rollos de empapelado por combo (S2)  (§11.3)
  D. Criterio de desempate entre óptimos (S3)  (§11.4)

    python scripts/02_tests_supuestos.py

Salidas: por consola y en resultados/tablas/*.csv
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
if hasattr(sys.stdout, "reconfigure"):  # consola de Windows en cp1252
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd  # noqa: E402

from src import datos, modelo, reportes  # noqa: E402
from src.config import construir_params  # noqa: E402

SALIDA = RAIZ / "resultados" / "tablas"

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)


def titulo(texto, caracter="="):
    print(f"\n{caracter * 78}\n{texto}\n{caracter * 78}")


def variedad_maxima(params):
    """V* de la etapa 1. Cualquier estado distinto de Optimal es un error del test."""
    res = modelo.resolver(params)
    if res["status"] != "Optimal":
        raise RuntimeError(f"Estado {res['status']} con supuestos {params['supuestos']}")
    return res["variedad"]


def espacios_que_suman(capacidades, v_actual):
    """Espacios a los que sumarles 1 lugar aumenta la variedad, dadas unas capacidades."""
    base = construir_params(capacidades=capacidades)
    suman = []
    for e, d in base["espacios"].items():
        probado = construir_params(capacidades={**capacidades, e: d["capacidad"] + 1})
        if variedad_maxima(probado) > v_actual:
            suman.append(d["nombre"])
    return suman


def test_capacidad():
    """A.1 — Un lugar más en cada espacio, de a uno por vez."""
    base = construir_params()
    v0 = variedad_maxima(base)
    filas = []
    for e, d in base["espacios"].items():
        v = variedad_maxima(construir_params(capacidades={e: d["capacidad"] + 1}))
        filas.append(
            {
                "Espacio": d["nombre"],
                "Capacidad base": d["capacidad"],
                "Capacidad probada": d["capacidad"] + 1,
                "V*": v,
                "Delta V*": v - v0,
            }
        )
    return pd.DataFrame(filas), v0


def test_mesadas(desde=3, hasta=6):
    """A.2 — Barrido de mesadas: en cada nivel, qué espacio pasa a ser el cuello de botella."""
    filas = []
    for cap in range(desde, hasta + 1):
        capacidades = {"mesadas": cap}
        v = variedad_maxima(construir_params(capacidades=capacidades))
        suman = espacios_que_suman(capacidades, v)
        filas.append(
            {
                "Mesadas": cap,
                "V*": v,
                "Espacios cuyo +1 suma un combo": ", ".join(suman) if suman else "ninguno por sí solo",
            }
        )
    return pd.DataFrame(filas)


def test_lectura():
    """B — S1: reserva exclusiva (base) vs. compartida (la lectura de b)."""
    filas = []
    for lectura in ("exclusiva", "compartida"):
        params = construir_params(S1_disponibilidad=lectura)
        etapa1, final = modelo.resolver_lexicografico(params)
        v = etapa1["variedad"]
        filas.append(
            {
                "Lectura S1": lectura,
                "V*": v,
                "Óptimos alternativos": len(datos.enumerar_factibles(params, v)),
                "Factibles con V*+1": len(datos.enumerar_factibles(params, v + 1)),
                "Categorías (desempate)": final["categorias"],
                "Unidades (desempate)": final["unidades"],
                "Combos (desempate)": " - ".join(map(str, final["combos"])),
            }
        )
    return pd.DataFrame(filas)


def test_rollos(desde=1, hasta=9):
    """C — S2: rollos de empapelado que lleva cada combo."""
    filas = []
    for rollos in range(desde, hasta + 1):
        params = construir_params(S2_unidades_por_articulo={"E": rollos})
        _etapa1, final = modelo.resolver_lexicografico(params)
        con_empapelado = [c for c in final["combos"] if "E" in datos.categorias_cubiertas(params, [c])]
        filas.append(
            {
                "Rollos por combo": rollos,
                "V*": final["variedad"],
                "Combos (desempate)": " - ".join(map(str, final["combos"])),
                "Combos con empapelado": len(con_empapelado),
                "Rollos ocupados": final["ocupacion"]["empapelado"],
                "Categorías cubiertas": final["categorias"],
            }
        )
    return pd.DataFrame(filas)


def test_desempate():
    """D — S3: cómo cambia la solución presentada según el criterio de desempate."""
    filas = []
    for criterio in ("categorias_y_unidades", "min_unidades", "max_articulos", "ninguno"):
        params = construir_params(S3_desempate=criterio)
        _etapa1, final = modelo.resolver_lexicografico(params)
        filas.append(
            {
                "Criterio S3": criterio,
                "V*": final["variedad"],
                "Combos": " - ".join(map(str, final["combos"])),
                "Categorías cubiertas": final["categorias"],
                "Unidades": final["unidades"],
                "Lugares lavav.+cocinas": final["ocupacion"]["lavav_cocinas"],
                "Lugares libres": sum(final["holgura"].values()),
            }
        )
    return pd.DataFrame(filas)


def main():
    titulo("TESTS DE SUPUESTOS — PUNTO a)")

    titulo("A.1 CAPACIDAD +1, UN ESPACIO POR VEZ (plan §10.1)", "-")
    t_cap, v0 = test_capacidad()
    print(t_cap.to_string(index=False))

    titulo("A.2 BARRIDO DE MESADAS: CADENA DE CUELLOS DE BOTELLA (plan §10.2)", "-")
    t_mes = test_mesadas()
    print(t_mes.to_string(index=False))

    titulo("B. S1 — LECTURA DE 'DISPONIBLE' (plan §11.2)", "-")
    print("(la lectura compartida enumera C(20,13)+C(20,14) conjuntos: tarda unos segundos)")
    t_lec = test_lectura()
    print(t_lec.to_string(index=False))

    titulo("C. S2 — ROLLOS DE EMPAPELADO POR COMBO (plan §11.3)", "-")
    t_rol = test_rollos()
    print(t_rol.to_string(index=False))

    titulo("D. S3 — CRITERIO DE DESEMPATE (plan §11.4)", "-")
    t_des = test_desempate()
    print(t_des.to_string(index=False))

    # --- Controles: propiedades que cualquier resultado correcto cumple --------
    titulo("CONTROLES", "-")
    v_lectura = dict(zip(t_lec["Lectura S1"], t_lec["V*"]))
    controles = [
        ("A.1: sumar capacidad nunca baja la variedad", (t_cap["Delta V*"] >= 0).all()),
        ("A.2: la variedad no baja al sumar mesadas", t_mes["V*"].is_monotonic_increasing),
        ("A.2: el primer nivel del barrido reproduce el caso base", t_mes["V*"].iloc[0] == v0),
        ("B: la lectura compartida da variedad >= la exclusiva", v_lectura["compartida"] >= v_lectura["exclusiva"]),
        ("B: en ambas lecturas no hay conjuntos factibles de V*+1", (t_lec["Factibles con V*+1"] == 0).all()),
        ("C: más rollos por combo nunca sube la variedad", t_rol["V*"].is_monotonic_decreasing),
        ("C: 1 rollo reproduce el caso base", t_rol["V*"].iloc[0] == v0),
        ("D: todos los criterios de desempate mantienen V*", (t_des["V*"] == v0).all()),
        (
            "D: el criterio base cubre al menos tantas categorías como los demás",
            (t_des["Categorías cubiertas"].iloc[0] >= t_des["Categorías cubiertas"]).all(),
        ),
        (
            "C: con 9 rollos el criterio base no vuelve infactible el modelo (resigna la categoría)",
            t_rol["V*"].iloc[-1] > 0 and t_rol["Categorías cubiertas"].iloc[-1] < len(construir_params()["catalogo"]),
        ),
    ]
    for descripcion, ok in controles:
        print(f"  [{'OK ' if ok else 'MAL'}] {descripcion}")
    if not all(ok for _, ok in controles):
        print("\nERROR: falló un control.")
        return 1

    tablas = {
        "08_test_capacidad_mas_uno": t_cap,
        "09_test_barrido_mesadas": t_mes,
        "10_test_lectura_disponibilidad": t_lec,
        "11_test_rollos_empapelado": t_rol,
        "12_test_desempate": t_des,
    }
    # Los tests A.1 y A.2 no llevan gráfico: son "uno vale +1 y seis valen 0" y un
    # barrido de cuatro puntos. Eso se lee mejor como tabla (procedimiento §4.1 y §4.2).
    reportes.guardar(tablas, SALIDA)
    titulo("ARCHIVOS GENERADOS", "-")
    for nombre in tablas:
        print(f"  resultados/tablas/{nombre}.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
