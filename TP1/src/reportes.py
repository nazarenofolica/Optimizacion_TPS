"""
Tablas de resultados del modelo Pastarazzi.

Convierte la salida cruda de `modelo.resolver()` en DataFrames listos para leer y
para pegar en el informe. Cada función responde a un pedido concreto de la
pregunta a) del caso:

    tabla_plan          -> "plan de asignación de presupuesto"
    tabla_comercial     -> "mix resultante" y "composición de la facturación"
    tabla_canales       -> "distribución por canales de venta"
    tabla_restricciones -> qué reglas atan la solución (insumo del análisis post-óptimo)
    tabla_comparativa   -> los tres objetivos enfrentados
"""

import pandas as pd

from . import datos, modelo
from .config import ETIQUETA_OBJETIVO


def _por_marca(res, funcion):
    """Aplica `funcion(cod)` a cada marca, en el orden de config.PRODUCTOS."""
    return {cod: funcion(cod) for cod in res["params"]["productos"]}


def clientes_captados(res):
    """Clientes nuevos por marca."""
    tasas = {(cod, i): tr["tasa"] for cod, i, tr in datos.tramos(res["params"])}
    return _por_marca(
        res,
        lambda cod: sum(
            tasas[k] * v for k, v in res["x_tramos"].items() if k[0] == cod
        ),
    )


def clientes_base(params):
    """Clientes que cada marca ya tiene, antes de la campaña, en su segmento.

    Bajo el supuesto S2 (el cliente vuelca todo su gasto anual en pastas en una
    sola marca), la participación en facturación de la Fig. 2 equivale a la
    participación en clientes, así que `share x TAM` da la base instalada.

    Hace falta para medir "presencia" como la entiende el enunciado: la posición
    de una marca en su mercado, no solo lo que la campaña de este año le agrega.
    Don Carlo arranca con 7.525.000 clientes; la campaña mueve 340.000. Ignorar
    la base exagera el efecto de la publicidad en un orden de magnitud.
    """
    return {
        cod: prod["share"][prod["segmento"]] * params["mercado"][prod["segmento"]]["tam"]
        for cod, prod in params["productos"].items()
    }


def desperdicio(res):
    """Inversión que no capta a nadie, por marca, en $MM.

    Es la plata que las reglas del directorio obligan a gastar en tramos de tasa
    cero: producto ya saturado o segmento sin gente por captar.
    """
    return _por_marca(
        res,
        lambda cod: sum(
            res["x_tramos"][(c, i)]
            for c, i, tr in datos.tramos(res["params"])
            if c == cod and tr["tasa"] == 0
        ),
    )


def facturacion(res):
    """Facturación total, base e incremental, por marca, en $MM."""
    base = datos.facturacion_base(res["params"])
    fxm = datos.facturacion_por_millon(res["params"])
    incremental = _por_marca(
        res,
        lambda cod: sum(fxm[k] * v for k, v in res["x_tramos"].items() if k[0] == cod),
    )
    total = {cod: base[cod] + incremental[cod] for cod in base}
    return base, incremental, total


def tabla_plan(res):
    """Cómo se reparte el presupuesto, por marca y por tramo."""
    params = res["params"]
    filas = []
    for cod, i, tramo in datos.tramos(params):
        limite = tramo["limite"]
        filas.append(
            {
                "Marca": params["productos"][cod]["nombre"],
                "Tramo": f"{i}. {tramo['etiqueta']}",
                "Tope ($MM)": limite if limite is not None else float("inf"),
                "Tasa (cl/$MM)": tramo["tasa"],
                "Inversión ($MM)": res["x_tramos"][(cod, i)],
            }
        )
    df = pd.DataFrame(filas)
    df["% del presupuesto"] = 100 * df["Inversión ($MM)"] / params["presupuesto"]
    return df


def tabla_comercial(res):
    """Mix resultante: inversión, clientes, facturación, unidades y utilidad."""
    params = res["params"]
    base, incremental, total = facturacion(res)
    clientes = clientes_captados(res)
    perdida = desperdicio(res)
    mercado_total = datos.mercado_total(params)

    filas = []
    for cod, prod in params["productos"].items():
        filas.append(
            {
                "Marca": prod["nombre"],
                "Inversión ($MM)": res["x"][cod],
                "de la cual estéril ($MM)": perdida[cod],
                "Clientes nuevos": clientes[cod],
                "Fact. base ($MM)": base[cod],
                "Fact. incremental ($MM)": incremental[cod],
                "Facturación total ($MM)": total[cod],
                "Crecimiento (%)": 100 * incremental[cod] / base[cod] if base[cod] else 0.0,
                # facturación en $MM / precio en $ = millones de paquetes
                "Unidades (millones)": total[cod] / prod["precio"],
                "Utilidad neta ($MM)": total[cod] * prod["m_neto"],
                "Utilidad oper. ($MM)": total[cod] * prod["m_oper"],
                "Market share (%)": 100 * total[cod] / mercado_total,
            }
        )
    df = pd.DataFrame(filas)
    df["% de la facturación"] = (
        100 * df["Facturación total ($MM)"] / df["Facturación total ($MM)"].sum()
    )

    total_fila = df.drop(columns=["Marca"]).sum()
    total_fila["Marca"] = "TOTAL"
    total_fila["Crecimiento (%)"] = (
        100 * df["Fact. incremental ($MM)"].sum() / df["Fact. base ($MM)"].sum()
    )
    return pd.concat([df, total_fila.to_frame().T], ignore_index=True)


def tabla_canales(res):
    """Facturación por segmento de mercado (proxy de canal, supuesto S9).

    La facturación base de una marca vive en varios segmentos (Fig. 2), pero su
    captación incremental va toda al segmento de posicionamiento (supuesto S5).
    """
    params = res["params"]
    base_seg = datos.facturacion_base_por_segmento(params)
    _base, incremental, _total = facturacion(res)
    mercado = datos.mercado_por_segmento(params)
    clientes = clientes_captados(res)
    cupos = datos.cupo_por_segmento(params)

    filas = []
    for seg in params["mercado"]:
        f_base = sum(base_seg[cod][seg] for cod in params["productos"])
        marcas_seg = [
            cod
            for cod, prod in params["productos"].items()
            if prod["segmento"] == seg
        ]
        f_inc = sum(incremental[cod] for cod in marcas_seg)
        cl_nuevos = sum(clientes[cod] for cod in marcas_seg)
        filas.append(
            {
                "Segmento / canal": seg.capitalize(),
                "Mercado ($MM)": mercado[seg],
                "Fact. base ($MM)": f_base,
                "Fact. incremental ($MM)": f_inc,
                "Facturación total ($MM)": f_base + f_inc,
                "Share inicial (%)": 100 * f_base / mercado[seg],
                "Share final (%)": 100 * (f_base + f_inc) / mercado[seg],
                "Clientes nuevos": cl_nuevos,
                "Cupo disponible": cupos[seg],
                "Cupo usado (%)": 100 * cl_nuevos / cupos[seg] if cupos[seg] else 0.0,
            }
        )
    return pd.DataFrame(filas)


def tabla_restricciones(res):
    """Holgura, precio sombra y si la restricción quedó activa."""
    filas = []
    for nombre, dual in res["duales"].items():
        holgura = res["holguras"][nombre]
        filas.append(
            {
                "Restricción": nombre,
                "Descripción": modelo.DESCRIPCION.get(nombre, ""),
                "Holgura": holgura,
                "Activa": abs(holgura) < 1e-6,
                "Precio sombra": dual,
            }
        )
    return pd.DataFrame(filas)


def resumen(res):
    """Una fila con los indicadores globales de una corrida."""
    params = res["params"]
    _base, _inc, total = facturacion(res)
    clientes = clientes_captados(res)
    fact_total = sum(total.values())
    return {
        "Objetivo maximizado": ETIQUETA_OBJETIVO[res["objetivo"]],
        "Z": res["Z"],
        "Facturación ($MM)": fact_total,
        "Market share (%)": 100 * fact_total / datos.mercado_total(params),
        "Utilidad neta ($MM)": sum(
            total[c] * params["productos"][c]["m_neto"] for c in total
        ),
        "Utilidad oper. ($MM)": sum(
            total[c] * params["productos"][c]["m_oper"] for c in total
        ),
        "Clientes nuevos": sum(clientes.values()),
        "Presupuesto usado ($MM)": sum(res["x"].values()),
        "Inversión estéril ($MM)": sum(desperdicio(res).values()),
    }


def tabla_comparativa(resultados):
    """Enfrenta varias corridas: una fila de indicadores y otra de inversiones.

    Parameters
    ----------
    resultados : list of dict
        Salidas de `modelo.resolver()` con distintos objetivos.
    """
    filas = []
    for res in resultados:
        fila = resumen(res)
        for cod, prod in res["params"]["productos"].items():
            fila[f"$ {prod['nombre']}"] = res["x"][cod]
        filas.append(fila)
    return pd.DataFrame(filas).set_index("Objetivo maximizado").T


def guardar(tablas, carpeta):
    """Guarda un dict {nombre: DataFrame} como CSVs en `carpeta`."""
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, df in tablas.items():
        df.to_csv(carpeta / f"{nombre}.csv", index=True, encoding="utf-8-sig")
    return sorted(p.name for p in carpeta.glob("*.csv"))
