"""
Modelo de localización de centros de distribución de CarroMenos (programación lineal entera mixta).

Es el ÚNICO modelo del trabajo: todas las preguntas lo llaman con otros argumentos (plan §5.6 y §14).

Variables (plan §6.3)
    y_j     binaria   se abre el centro j
    g       binaria   se contrata el gerente
    x_pj    >= 0      pallets/mes de la planta p al centro j (producto de la planta)
    z_jik   >= 0      pallets/mes del producto k del centro j al súper i
    n       entera    conductores propios
    exc     >= 0      km por encima del tope de la pregunta e)
    u_k     binaria   el producto k lo lleva Goyito directo (pregunta c)

Restricciones (plan §8)
    DEM_i_k        Σ_j z_jik = dem_ik · (1 − u_k)
    BAL_j_k        Σ_{p ∈ P_k} x_pj = Σ_i z_jik
    CAP_j          Σ_i Σ_k z_jik <= cap_j · y_j
    FUERTE_j_i_k   z_jik <= dem_ik · y_j            (formulación fuerte; no cambia el óptimo; opcional)
    PRINCIPAL      y_A + y_B = 1   (S2 'exclusivo')  /  >= 1  ('al_menos_uno', test B)
    GERENTE        g >= Σ_j y_j − 2
    CONDUCTORES    K_max · n >= km_prop
    TOPE_KM        km_prop − 500 · n <= exc          (solo e; CONDUCTORES se mantiene, desvío D2)
    CO2_MAX        CO2 <= ε                          (solo frontera costo–CO2)

Escenarios
    "a"   caso base: tramo 1 tercerizado, tramo 2 con camión propio
    "d"   flota propia también en el tramo 1 (planta -> centro)
    "e"   caso base + tope de 500 km por conductor con penalidad
    "de"  d + e
"""

import pandas as pd
import pulp

from src import datos

ESCENARIOS = {
    # escenario: (flota propia en el tramo 1, tope de km de la pregunta e)
    "a": (False, False),
    "d": (True, False),
    "e": (False, True),
    "de": (True, True),
}

RUBROS = (
    "apertura",
    "gerente",
    "operacion",
    "tramo1_tercerizado",
    "tramo1_combustible",
    "tramo2_combustible",
    "conductores",
    "penalidad_km",
    "goyito",
    "carbono",
)

TOLERANCIA = 1e-6


def _numero(expresion):
    """Valor de una expresión de PuLP después de resolver (0 si es una constante vacía)."""
    if isinstance(expresion, (int, float)):
        return float(expresion)
    return float(pulp.value(expresion) or 0.0)


def resolver(params, escenario="a", config_fija=None, epsilon_co2=None, goyito=None,
             objetivo="costo", fijar_n=None, dist=None, fuerte=True):
    """Arma y resuelve el modelo. Devuelve un dict con todos los resultados.

    Parameters
    ----------
    params : dict
        De config.construir_params().
    escenario : {"a", "d", "e", "de"}
    config_fija : iterable de centros, optional
        Fija y_j = 1 para esos centros y 0 para el resto: queda el PL de flujos (plan §9, §10).
    epsilon_co2 : float, optional
        Tope de kg de CO2 por mes (frontera costo–CO2, plan §12 a).
    goyito : dict {producto: $ por pallet}, optional
        Habilita que Goyito lleve ese producto directo de la planta al súper (pregunta c).
    objetivo : {"costo", "co2"}
        "co2" minimiza las emisiones (extremo de la frontera); el costo se informa igual.
    fijar_n : int, optional
        Fija la cantidad de conductores (para el PL de sensibilidad, desvío D3).
    dist : DataFrame, optional
        Matriz de distancias a usar; por defecto la del supuesto S1.
    fuerte : bool
        Incluir FUERTE_j_i_k (z <= dem · y). Ajusta la relajación del entero; con la configuración
        fija es redundante y en el análisis de sensibilidad estorba (ata cada flujo a la demanda
        vieja cuando se perturba DEM), así que `sensibilidad` la apaga.
    """
    if escenario not in ESCENARIOS:
        raise KeyError(f"Escenario desconocido: {escenario!r}. Válidos: {sorted(ESCENARIOS)}")
    if objetivo not in ("costo", "co2"):
        raise ValueError(f"objetivo={objetivo!r}: tiene que ser 'costo' o 'co2'")
    propio_t1, con_tope = ESCENARIOS[escenario]
    goyito = dict(goyito or {})

    s = params["supuestos"]
    ubic = datos.cargar_ubicaciones()
    dist = datos.distancias(params) if dist is None else dist
    coef = datos.coeficientes_por_arco(params, dist).set_index(["origen", "destino"])

    K, I = params["productos"], params["supermercados"]
    J = list(params["centros"])
    P = datos.ids(ubic, "planta")
    prod_de = datos.producto_de_planta(ubic)
    P_k = datos.plantas_por_producto(ubic)
    dem = params["demanda"]
    desconocidos = set(goyito) - set(K)
    if desconocidos:
        raise KeyError(f"Productos desconocidos en goyito: {sorted(desconocidos)}")
    if config_fija is not None:
        config_fija = set(config_fija)
        if config_fija - set(J):
            raise KeyError(f"Centros desconocidos en config_fija: {sorted(config_fija - set(J))}")

    m = pulp.LpProblem("CarroMenos", pulp.LpMinimize)

    # --- Variables -----------------------------------------------------------
    y = {}
    for j in J:
        if config_fija is None:
            y[j] = pulp.LpVariable(f"y_{j}", cat="Binary")
        else:
            v = int(j in config_fija)
            y[j] = pulp.LpVariable(f"y_{j}", lowBound=v, upBound=v)
    g = pulp.LpVariable("g", cat="Binary")
    x = {(p, j): pulp.LpVariable(f"x_{p}_{j}", lowBound=0) for p in P for j in J}
    z = {(j, i, k): pulp.LpVariable(f"z_{j}_{i}_{k}", lowBound=0) for j in J for i in I for k in K}
    if fijar_n is None:
        n = pulp.LpVariable("n", lowBound=0, cat="Integer")
    else:
        n = pulp.LpVariable("n", lowBound=fijar_n, upBound=fijar_n)
    exc = pulp.LpVariable("exc", lowBound=0) if con_tope else 0
    u = {k: pulp.LpVariable(f"u_{k}", cat="Binary") for k in goyito}

    # --- Expresiones auxiliares (plan §6.3) ----------------------------------
    pallets_j = {j: pulp.lpSum(z[j, i, k] for i in I for k in K) for j in J}
    km_1 = pulp.lpSum(coef.at[(p, j), "km_por_pallet"] * x[p, j] for p in P for j in J)
    km_2 = pulp.lpSum(coef.at[(j, i), "km_por_pallet"] * z[j, i, k] for j in J for i in I for k in K)
    km_prop = km_1 + km_2 if propio_t1 else km_2

    # Goyito: cada pallet va de la planta más cercana del producto al súper (no consolida, S15).
    km_goyito_k = {
        k: sum(dem[i, k] * min(coef.at[(p, i), "km_por_pallet"] for p in P_k[k]) for i in I) for k in goyito
    }
    km_goyito = pulp.lpSum(km_goyito_k[k] * u[k] for k in goyito)
    litros = (km_1 + km_2 + km_goyito) * (1 / params["rendimiento"])
    co2 = litros * s["phi"]

    costos = {
        "apertura": pulp.lpSum(params["centros"][j]["apertura"] * y[j] for j in J),
        "gerente": params["gerente"] * g,
        "operacion": pulp.lpSum(params["centros"][j]["costo_pallet"] * pallets_j[j] for j in J),
        "tramo1_tercerizado": 0 if propio_t1 else pulp.lpSum(
            coef.at[(p, j), "costo_tercerizado"] * x[p, j] for p in P for j in J),
        "tramo1_combustible": pulp.lpSum(
            coef.at[(p, j), "costo_propio"] * x[p, j] for p in P for j in J) if propio_t1 else 0,
        "tramo2_combustible": pulp.lpSum(
            coef.at[(j, i), "costo_propio"] * z[j, i, k] for j in J for i in I for k in K),
        "conductores": s["W"] * n,
        "penalidad_km": params["penalidad_km_e"] * exc if con_tope else 0,
        "goyito": pulp.lpSum(goyito[k] * sum(dem[i, k] for i in I) * u[k] for k in goyito),
        "carbono": s["precio_co2"] * co2 if s["precio_co2"] else 0,
    }
    costo_total = pulp.lpSum(costos.values())

    # --- Función objetivo (plan §7) --------------------------------------------
    m += costo_total if objetivo == "costo" else co2

    # --- Restricciones (plan §8) -----------------------------------------------
    for i in I:
        for k in K:
            atendido = dem[i, k] * (1 - u[k]) if k in u else dem[i, k]
            m += pulp.lpSum(z[j, i, k] for j in J) == atendido, f"DEM_{i}_{k}"
    for j in J:
        for k in K:
            m += pulp.lpSum(x[p, j] for p in P_k[k]) == pulp.lpSum(z[j, i, k] for i in I), f"BAL_{j}_{k}"
    for j in J:
        m += pallets_j[j] <= params["centros"][j]["capacidad"] * y[j], f"CAP_{j}"
        if fuerte:
            for i in I:
                for k in K:
                    m += z[j, i, k] <= dem[i, k] * y[j], f"FUERTE_{j}_{i}_{k}"
    principales = pulp.lpSum(y[j] for j in params["principales"])
    if s["principal"] == "exclusivo":
        m += principales == 1, "PRINCIPAL"
    else:
        m += principales >= 1, "PRINCIPAL"
    m += g >= pulp.lpSum(y.values()) - 2, "GERENTE"
    m += s["K_max"] * n >= km_prop, "CONDUCTORES"
    if con_tope:
        m += km_prop - params["tope_km_e"] * n <= exc, "TOPE_KM"
    if epsilon_co2 is not None:
        m += co2 <= epsilon_co2, "CO2_MAX"

    m.solve(pulp.PULP_CBC_CMD(msg=False))
    estado = pulp.LpStatus[m.status]
    res = {"estado": estado, "escenario": escenario, "objetivo": objetivo, "modelo": m}
    if estado != "Optimal":
        return res

    val = pulp.value
    abiertos = [j for j in J if val(y[j]) > 0.5]
    flujos1 = pd.DataFrame(
        [{"planta": p, "producto": prod_de[p], "centro": j, "pallets": val(x[p, j])}
         for p in P for j in J if val(x[p, j]) > TOLERANCIA]
    )
    flujos2 = pd.DataFrame(
        [{"centro": j, "super": i, "producto": k, "pallets": val(z[j, i, k])}
         for j in J for i in I for k in K if val(z[j, i, k]) > TOLERANCIA]
    )
    ocupacion = pd.DataFrame(
        [{"centro": j, "abierto": j in abiertos, "capacidad": params["centros"][j]["capacidad"],
          "pallets": val(pallets_j[j]) or 0.0} for j in J]
    )
    ocupacion["uso_pct"] = 100 * ocupacion["pallets"] / ocupacion["capacidad"]

    desglose = {r: _numero(costos[r]) for r in RUBROS}
    res.update({
        "costo": sum(desglose.values()),
        "desglose": desglose,
        "centros": abiertos,
        "configuracion": "+".join(abiertos),
        "gerente": val(g) > 0.5,
        "conductores": round(val(n)),
        "exceso_km": _numero(exc),
        "goyito": {k: val(u[k]) > 0.5 for k in goyito},
        "km_tramo1": _numero(km_1),
        "km_tramo2": _numero(km_2),
        "km_goyito": _numero(km_goyito),
        "km_propios": _numero(km_prop),
        "litros": _numero(litros),
        "co2_kg": _numero(co2),
        "flujos_tramo1": flujos1,
        "flujos_tramo2": flujos2,
        "ocupacion": ocupacion,
    })
    res["km_total"] = res["km_tramo1"] + res["km_tramo2"] + res["km_goyito"]
    return res
