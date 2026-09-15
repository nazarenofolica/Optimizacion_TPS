"""
Tablas de salida del punto a) (docs/plan_de_trabajo.md §12).

Cada función devuelve un DataFrame listo para imprimir o guardar como CSV.
"""

import pandas as pd

from . import datos


def tabla_apariciones(params):
    """En cuántos combos aparece cada artículo.  (plan §3.4)"""
    usan = datos.combos_que_usan(params)
    filas = []
    for cat in params["catalogo"].values():
        for p, descripcion in cat["productos"].items():
            filas.append(
                {
                    "Categoría": cat["nombre"],
                    "Artículo": p,
                    "Descripción": descripcion,
                    "Combos que lo usan": len(usan[p]),
                    "Lista de combos": ", ".join(map(str, usan[p])),
                }
            )
    return pd.DataFrame(filas)


def tabla_cota_trivial(params):
    """Cota de variedad que impone cada espacio por sí solo.  (plan §3.6)"""
    lugares = datos.lugares_por_combo(params)
    cotas = datos.cota_trivial(params)
    filas = []
    for e, d in params["espacios"].items():
        filas.append(
            {
                "Espacio": d["nombre"],
                "Capacidad": d["capacidad"],
                "Lugares mínimos por combo": min(lugares[c][e] for c in lugares),
                "Cota (combos como máximo)": "sin cota" if cotas[e] is None else cotas[e],
            }
        )
    return pd.DataFrame(filas)


def tabla_combos(res):
    """Combos ofrecidos en una solución, con lo que ocupa cada uno."""
    params = res["params"]
    lugares = datos.lugares_por_combo(params)
    filas = [
        {
            "Combo": c,
            "Artículos": " ".join(params["combos"][c]),
            "Unidades": sum(lugares[c].values()),
            "Lugares lavav.+cocinas": lugares[c]["lavav_cocinas"],
        }
        for c in res["combos"]
    ]
    return pd.DataFrame(filas)


def tabla_stock(res):
    """Plan de stock: los 30 artículos con sus unidades, incluidos los que quedan en 0."""
    params = res["params"]
    usan = datos.combos_que_usan(params)
    ofrecidos = set(res["combos"])
    filas = []
    for cat in params["catalogo"].values():
        for p, descripcion in cat["productos"].items():
            filas.append(
                {
                    "Categoría": cat["nombre"],
                    "Artículo": p,
                    "Descripción": descripcion,
                    "Unidades en stock": res["stock"][p],
                    "Para los combos": ", ".join(str(c) for c in usan[p] if c in ofrecidos),
                }
            )
    return pd.DataFrame(filas)


def tabla_espacios(res):
    """Ocupación del depósito. En la relajación lineal agrega el precio sombra.

    En la relajación se mide la ocupación NECESARIA para los y_c obtenidos, no el
    stock que dejó el solver: como el funcional no penaliza el stock, el solver
    llena todos los espacios y la tabla los mostraría a todos como limitantes.
    """
    params = res["params"]
    ocupado = res["ocupacion_necesaria"] if res["relajado"] else res["ocupacion"]
    columna = "Ocupado (necesario)" if res["relajado"] else "Ocupado"
    filas = []
    for e, d in params["espacios"].items():
        holgura = d["capacidad"] - ocupado[e]
        fila = {
            "Espacio": d["nombre"],
            "Capacidad": d["capacidad"],
            columna: ocupado[e],
            "Holgura": holgura,
            "Limita": "Sí" if abs(holgura) < 1e-6 else "No",
        }
        if res["relajado"]:
            fila["Precio sombra (combos por lugar)"] = res["duales"][e]
        filas.append(fila)
    return pd.DataFrame(filas)


def tabla_optimos(params, conjuntos):
    """Una fila por conjunto de combos, con unidades y ocupación de cada espacio."""
    filas = []
    for S in conjuntos:
        uso = datos.ocupacion(params, datos.stock_necesario(params, S))
        fila = {
            "Combos": " - ".join(map(str, S)),
            "Unidades": sum(uso.values()),
            "Categorías cubiertas": len(datos.categorias_cubiertas(params, S)),
        }
        fila.update({params["espacios"][e]["nombre"]: v for e, v in uso.items()})
        filas.append(fila)
    return pd.DataFrame(filas)


def guardar(tablas, carpeta):
    """Guarda un dict {nombre: DataFrame} como CSVs en `carpeta`."""
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, df in tablas.items():
        df.to_csv(carpeta / f"{nombre}.csv", index=False, encoding="utf-8-sig")
    return sorted(p.name for p in carpeta.glob("*.csv"))
