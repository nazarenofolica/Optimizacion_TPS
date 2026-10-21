"""
Análisis de sensibilidad del PL de flujos con la configuración óptima fija (plan §10, tarea T16).

Con binarias no hay precios sombra (Clase 06). Se fija lo entero del óptimo —qué centros se abren
(y*), el gerente y la cantidad de conductores (n*, desvío D3)— y queda un PL continuo de flujos
(transbordo, Clase 09). Ese PL es el MISMO modelo de `modelo.resolver` (con `config_fija` y
`fijar_n`), exportado a MPS y resuelto con HiGHS, que sí devuelve rangos (`getRanging`).

PuLP escribe las restricciones con todo lo variable a la izquierda, así que algunas filas tienen
lado derecho 0 aunque representan otra cosa. Este módulo las traduce a unidades del problema:

    CAP_j        Σ z_jik − cap_j · y_j <= 0     ->  capacidad del centro j [pallets/mes]
    CONDUCTORES  K_max · n − km_prop >= 0       ->  km disponibles de los conductores [km/mes]
    DEM_i_k      Σ_j z_jik = dem_ik             ->  demanda [pallets/mes]

Convención de signos: `precio_sombra` = cuánto cambia el costo total si el recurso (capacidad,
km disponibles, demanda) sube en una unidad, dentro del rango informado.

Degeneración. El PL de transbordo es muy degenerado y además la fila CONDUCTORES está activa (los
km del tramo 2 son justo K_max · n*). Por eso el precio de SUBIR un recurso puede ser distinto del
de BAJARLO, y HiGHS informa uno solo (con rango 0 del otro lado). Se agregan los dos precios
laterales medidos re-resolviendo el PL con el lado derecho ±1 (`marginal`): para un PL son las
derivadas laterales exactas del costo óptimo.
"""

import tempfile
from pathlib import Path

import highspy
import pandas as pd
import pulp

from src import modelo

INF = float("inf")


def resolver_pl(params, base):
    """PL de flujos con y*, g* y n* del óptimo `base` fijos. Devuelve (Highs, res de PuLP)."""
    # Sin FUERTE: con y fija es redundante, y si queda, al perturbar DEM cada flujo sigue atado
    # a la demanda vieja (z <= dem) y los precios laterales salen mal.
    res = modelo.resolver(params, escenario=base["escenario"], config_fija=base["centros"],
                          fijar_n=base["conductores"], fuerte=False)
    if res["estado"] != "Optimal":
        raise RuntimeError(f"El PL de flujos no es óptimo: {res['estado']}")
    m = res["modelo"]
    for v in m.variables():  # y, n ya están fijas por cotas; g queda forzada por GERENTE
        v.cat = pulp.LpContinuous
    with tempfile.TemporaryDirectory() as tmp:
        archivo = Path(tmp) / "pl_flujos.mps"
        m.writeMPS(str(archivo))
        h = highspy.Highs()
        h.setOptionValue("output_flag", False)
        h.readModel(str(archivo))
    h.run()
    if h.getModelStatus() != highspy.HighsModelStatus.kOptimal:
        raise RuntimeError(f"HiGHS: {h.modelStatusToString(h.getModelStatus())}")
    return h, res


def _filas(h):
    lp, sol = h.getLp(), h.getSolution()
    _, rg = h.getRanging()
    return pd.DataFrame({
        "fila": [h.getRowName(i)[1] for i in range(lp.num_row_)],
        "valor": sol.row_value,
        "inf": lp.row_lower_,
        "sup": lp.row_upper_,
        "dual": sol.row_dual,
        "rango_dn": rg.row_bound_dn.value_,
        "rango_up": rg.row_bound_up.value_,
    })


def _columnas(h):
    lp, sol = h.getLp(), h.getSolution()
    _, rg = h.getRanging()
    n = lp.num_col_  # los vectores de ranging de costos traen también las holguras (n_col + n_fila)
    return pd.DataFrame({
        "variable": [h.getColName(j)[1] for j in range(n)],
        "valor": sol.col_value,
        "costo": lp.col_cost_,
        "costo_reducido": sol.col_dual,
        "costo_min": list(rg.col_cost_dn.value_)[:n],
        "costo_max": list(rg.col_cost_up.value_)[:n],
    })


def marginal(h, fila, delta):
    """(costo con el lado derecho de `fila` corrido en `delta`) − (costo actual), re-resolviendo.

    Deja el modelo como estaba. Para un PL, marginal(+1) y −marginal(−1) son los precios laterales
    exactos de subir y de bajar el lado derecho una unidad.
    """
    lp = h.getLp()
    i = [h.getRowName(r)[1] for r in range(lp.num_row_)].index(fila)
    lo, up = lp.row_lower_[i], lp.row_upper_[i]
    c0 = costo_pl(h)
    h.changeRowBounds(i, lo + delta if lo > -INF else lo, up + delta if up < INF else up)
    h.run()
    ok = h.getModelStatus() == highspy.HighsModelStatus.kOptimal
    c = costo_pl(h) if ok else float("nan")
    h.changeRowBounds(i, lo, up)
    h.run()
    return c - c0


def rangos_lado_derecho(h, params, base, tol=1e-6):
    """b.i — Precio sombra y rango de validez de demanda, capacidades y km de conductores.

    Columnas:
        precio_sombra        dual de HiGHS (d costo / d recurso), válido en [rango_min, rango_max]
        precio_subir         costo de una unidad MÁS del recurso (re-resolviendo)
        precio_bajar         costo de una unidad MENOS, con signo de "subir" (re-resolviendo)
    Una restricción con holgura tiene precio 0 y vale desde lo usado hasta +infinito (Clase 03).
    """
    f = _filas(h).set_index("fila")
    filas = []

    def agregar(fila_lp, recurso, unidad, actual, usado, dual, rmin, rmax, signo):
        holgura = actual - usado
        if holgura > tol:  # no activa: precio 0, rango [usado, +inf)
            dual, rmin, rmax, subir, bajar = 0.0, usado, INF, 0.0, 0.0
        else:  # signo: +1 si subir el recurso es subir el lado derecho de la fila; −1 si es bajarlo
            subir = marginal(h, fila_lp, signo * 1.0)
            bajar = -marginal(h, fila_lp, -signo * 1.0)
        filas.append({
            "restriccion": fila_lp, "recurso": recurso, "unidad": unidad, "valor_actual": actual,
            "usado": usado, "holgura": holgura, "precio_sombra": dual, "rango_min": rmin,
            "rango_max": rmax, "precio_subir": subir, "precio_bajar": bajar,
        })

    for j in base["centros"]:
        r = f.loc[f"CAP_{j}"]
        cap = params["centros"][j]["capacidad"]
        # Fila: pallets − cap·y <= 0. Más capacidad = cota superior más alta: mismo sentido.
        agregar(f"CAP_{j}", f"Capacidad del centro {j}", "pallets/mes", cap, cap + r["valor"],
                r["dual"], cap + r["rango_dn"], cap + r["rango_up"], +1)

    r = f.loc["CONDUCTORES"]
    disp = params["supuestos"]["K_max"] * base["conductores"]
    # Fila: K_max·n − km >= 0. Más km disponibles = cota inferior más baja: sentido opuesto.
    agregar("CONDUCTORES", f"km disponibles ({base['conductores']} conductores)", "km/mes", disp,
            disp - r["valor"], -r["dual"], disp - r["rango_up"], disp - r["rango_dn"], -1)

    for (i, k), dem in params["demanda"].items():
        r = f.loc[f"DEM_{i}_{k}"]
        agregar(f"DEM_{i}_{k}", f"Demanda de {k} en {i}", "pallets/mes", dem, dem, r["dual"],
                r["rango_dn"], r["rango_up"], +1)
    return pd.DataFrame(filas)


def _arco(nombre, centros):
    """('x', planta, centro, '') o ('z', centro, súper, producto) a partir del nombre de PuLP."""
    partes = nombre.split("_")
    if partes[0] == "x":
        return "planta → centro", "_".join(partes[1:-1]), partes[-1], ""
    if partes[0] == "z":
        return "centro → súper", partes[1], partes[2], "_".join(partes[3:])
    return None


def rangos_costos(h, base, tol=1e-6):
    """b.ii — Para cada arco con flujo: costo por pallet y rango en que la solución no cambia."""
    c = _columnas(h)
    filas = []
    for v in c.itertuples():
        arco = _arco(v.variable, base["centros"])
        if arco is None or v.valor <= tol:
            continue
        tramo, o, d, k = arco
        filas.append({
            "tramo": tramo, "origen": o, "destino": d, "producto": k, "pallets": v.valor,
            "costo_pallet": v.costo, "costo_min": v.costo_min, "costo_max": v.costo_max,
            "puede_bajar": v.costo - v.costo_min, "puede_subir": v.costo_max - v.costo,
        })
    return pd.DataFrame(filas).sort_values(["tramo", "origen", "destino", "producto"], ignore_index=True)


def costos_reducidos(h, base, tol=1e-6):
    """b.ii — Arcos sin flujo de los centros abiertos: cuánto tendría que bajar su costo por pallet
    para que convenga usarlos (el costo reducido)."""
    c = _columnas(h)
    abiertos = set(base["centros"])
    filas = []
    for v in c.itertuples():
        arco = _arco(v.variable, base["centros"])
        if arco is None or v.valor > tol:
            continue
        tramo, o, d, k = arco
        centro = d if tramo == "planta → centro" else o
        if centro not in abiertos:
            continue
        filas.append({
            "tramo": tramo, "origen": o, "destino": d, "producto": k,
            "costo_pallet": v.costo, "costo_reducido": v.costo_reducido,
            "costo_para_entrar": v.costo - v.costo_reducido,
        })
    return pd.DataFrame(filas).sort_values("costo_reducido", ignore_index=True)


def costo_pl(h):
    return h.getInfo().objective_function_value + h.getLp().offset_
