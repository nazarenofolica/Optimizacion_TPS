"""
Modelo de programación lineal Pastarazzi.

Un único modelo parametrizado que sirve para todo el TP: el caso base, los barridos
de supuestos y los escenarios de las preguntas b), c) y d). La variación se maneja
por argumentos, nunca copiando el modelo.

    resolver(params)                                  # caso base
    resolver(params, objetivo="facturacion")          # mirada de la dirección
    resolver(params, desactivar=["R3_triguetti_min"]) # pregunta d)
    resolver(params, epsilon=800_000)                 # pregunta c), ε-constraint

Las restricciones llevan nombre para poder leer sus precios sombra y holguras por
nombre después (`res["duales"]["R3_triguetti_min"]`).
"""

import pulp

from . import datos

#: Nombre legible de cada restricción de tope de tramo.
_NOMBRE_LIMITE_TRAMO = {
    ("TRI", 1): "R7_sat_triguetti",
    ("CAN", 1): "R8a_lim_candealix",
    ("RS", 1): "R8b_lim_rena",
}

#: Para los reportes: qué significa cada restricción en castellano.
DESCRIPCION = {
    "R1_presupuesto": "Presupuesto total de marketing ($17.000MM)",
    "R2_paridad": "Paridad de inversión Don Carlo = Agnellis",
    "R3_triguetti_min": "Triguetti >= 30% del presupuesto",
    "R4_rena_doble": "Rena >= 2 x (Candealix + Triguetti)",
    "R5_tope_gama_baja": "Don Carlo + Agnellis <= 65% del segmento bajo",
    "R7_sat_triguetti": "Saturación de Triguetti a los $6.000MM",
    "R8a_lim_candealix": "Primer tramo de Candealix ($5.000MM al 300 cl/MM)",
    "R8b_lim_rena": "Primer tramo de Rena ($3.500MM al 150 cl/MM)",
    "R10_sat_bajo": "Saturación física del segmento bajo (100% del TAM)",
    "R10_sat_medio": "Saturación física del segmento medio (100% del TAM)",
    "R10_sat_alto": "Saturación física del segmento alto (100% del TAM)",
    "EPS_facturacion": "Piso de facturación (método ε-constraint)",
}


def _nombre_limite(cod, i):
    return _NOMBRE_LIMITE_TRAMO.get((cod, i), f"R8_lim_{cod}{i}")


def _validar_desactivar(desactivar):
    """Rechaza nombres de restricción que no existen.

    Sin esto, `desactivar=["R3_triguetti"]` (falta el `_min`) no da error: devuelve
    el caso base como si fuera el contrafactual. Como las preguntas b) y d) se
    responden justamente desactivando restricciones, un typo produciría una
    respuesta equivocada con apariencia de correcta.
    """
    desconocidos = set(desactivar) - set(DESCRIPCION)
    if desconocidos:
        raise KeyError(
            f"Restricción(es) inexistente(s): {sorted(desconocidos)}. "
            f"Válidas: {sorted(DESCRIPCION)}"
        )
    return set(desactivar)


def construir(params, objetivo="neta", epsilon=None, desactivar=()):
    """Arma el problema de PL y devuelve (problema, variables).

    Parameters
    ----------
    params : dict
        Salida de `config.construir_params()`.
    objetivo : {"neta", "oper", "facturacion"}
        Qué funcional maximizar (plan §6.2 a §6.4).
    epsilon : float, optional
        Piso de facturación en $MM. Si se pasa, agrega la restricción
        `Z_facturacion >= epsilon` del método ε-constraint (plan §6.5).
    desactivar : iterable of str
        Nombres de restricciones a omitir. Sirve para los contrafácticos:
        `desactivar=["R3_triguetti_min"]` responde la pregunta d).

    Returns
    -------
    (pulp.LpProblem, dict)
        El dict mapea (marca, indice_tramo) -> LpVariable.
    """
    if objetivo not in ("neta", "oper", "facturacion"):
        raise ValueError(f"Objetivo desconocido: {objetivo!r}")

    desactivar = _validar_desactivar(desactivar)
    reglas = params["reglas"]
    supuestos = params["supuestos"]
    lista_tramos = datos.tramos(params)

    prob = pulp.LpProblem("Pastarazzi", pulp.LpMaximize)

    # --- Variables: inversión por marca y tramo, en $MM ----------------------
    x = {
        (cod, i): pulp.LpVariable(f"x_{cod}{i}", lowBound=0)
        for cod, i, _tramo in lista_tramos
    }
    # Atajo: inversión total por marca (expresión, no variable nueva).
    total = {
        cod: pulp.lpSum(x[(c, i)] for (c, i) in x if c == cod)
        for cod in params["productos"]
    }

    # --- Función objetivo ---------------------------------------------------
    # El término constante se suma al final, en `resolver`: PuLP lo aceptaría acá,
    # pero dejarlo afuera mantiene los duales referidos solo a la parte variable.
    coefs = datos.coeficientes(params, objetivo)
    prob += pulp.lpSum(coefs[k] * x[k] for k in x), "funcional"

    # --- R1: presupuesto ----------------------------------------------------
    if "R1_presupuesto" not in desactivar:
        prob += (
            pulp.lpSum(total.values()) <= params["presupuesto"],
            "R1_presupuesto",
        )

    # --- R2: paridad Don Carlo / Agnellis (supuesto S6) ---------------------
    paridad = supuestos["S6_paridad_dc_ag"]
    if paridad != "libre" and "R2_paridad" not in desactivar:
        # "igualdad" -> x_DC = x_AG ; un float k -> x_DC = k * x_AG
        k = 1.0 if paridad == "igualdad" else float(paridad)
        prob += (total["DC"] - k * total["AG"] == 0, "R2_paridad")

    # --- R3: piso de Triguetti (supuesto S7) --------------------------------
    if "R3_triguetti_min" not in desactivar:
        pct = reglas["R3_pct_triguetti"]
        if supuestos["S7_base_r3"] == "presupuesto_total":
            prob += (total["TRI"] >= pct * params["presupuesto"], "R3_triguetti_min")
        else:  # "asignado": 30% de lo efectivamente repartido
            prob += (
                total["TRI"] - pct * pulp.lpSum(total.values()) >= 0,
                "R3_triguetti_min",
            )

    # --- R4: Rena al doble de Candealix + Triguetti (supuesto S7) -----------
    if "R4_rena_doble" not in desactivar:
        mult = reglas["R4_multiplo_rena"]
        expr = total["RS"] - mult * (total["CAN"] + total["TRI"])
        if supuestos["S7_operador_r4"] == "==":
            prob += (expr == 0, "R4_rena_doble")
        else:
            prob += (expr >= 0, "R4_rena_doble")

    # --- R5: tope del 65% en el segmento bajo -------------------------------
    if "R5_tope_gama_baja" not in desactivar:
        prob += (
            pulp.lpSum(
                tramo["tasa"] * x[(cod, i)]
                for cod, i, tramo in lista_tramos
                if cod in ("DC", "AG")
            )
            <= datos.cupo_gama_baja(params),
            "R5_tope_gama_baja",
        )

    # --- R7 y R8: topes de los tramos ---------------------------------------
    # Van como restricciones con nombre (y no como bounds de la variable) para que
    # el solver devuelva su precio sombra: hace falta en el análisis post-óptimo.
    for cod, i, tramo in lista_tramos:
        if tramo["limite"] is None:
            continue
        nombre = _nombre_limite(cod, i)
        if nombre not in desactivar:
            prob += (x[(cod, i)] <= tramo["limite"], nombre)

    # --- R10: saturación física del mercado ---------------------------------
    # No sale del enunciado. Sin ella el modelo capta más clientes de los que el
    # segmento tiene y devuelve participaciones de más del 100% (docs/procedimiento.md §2).
    # La captación de cada marca se reparte entre segmentos según el supuesto S5
    # (datos.segmentos_captacion): con la opción base ("posicionamiento") cada
    # marca aporta el 100% de sus clientes nuevos a un único segmento, igual que
    # antes; con "mix_fig2" aporta una fracción a cada segmento donde vende.
    cupos = datos.cupo_por_segmento(params)
    pesos = {cod: dict(datos.segmentos_captacion(params, cod)) for cod in params["productos"]}
    for seg, cupo in cupos.items():
        nombre = f"R10_sat_{seg}"
        if nombre in desactivar:
            continue
        captacion = pulp.lpSum(
            tramo["tasa"] * pesos[cod].get(seg, 0.0) * x[(cod, i)]
            for cod, i, tramo in lista_tramos
            if seg in pesos[cod]
        )
        if captacion:  # hay al menos una marca que capta en ese segmento
            prob += (captacion <= cupo, nombre)

    # --- ε-constraint: piso de facturación (pregunta c) ---------------------
    if epsilon is not None:
        coef_fact = datos.coeficientes(params, "facturacion")
        base_fact = datos.termino_constante(params, "facturacion")
        prob += (
            pulp.lpSum(coef_fact[k] * x[k] for k in x) >= epsilon - base_fact,
            "EPS_facturacion",
        )

    return prob, x


def resolver(params, objetivo="neta", epsilon=None, desactivar=(), verbose=False):
    """Construye, resuelve y devuelve la solución en un diccionario plano.

    Returns
    -------
    dict con:
        status        : "Optimal", "Infeasible", ...
        objetivo      : el objetivo maximizado
        Z             : valor del funcional COMPLETO (constante + parte variable)
        Z_variable    : solo la parte que depende de las decisiones
        Z_constante   : la utilidad/facturación de la base, sin invertir
        x             : {marca: inversión total en $MM}
        x_tramos      : {(marca, tramo): inversión en $MM}
        duales        : {nombre de restricción: precio sombra}
        holguras      : {nombre de restricción: holgura}
        params        : los parámetros usados (para que el reporte sea autocontenido)
    """
    prob, x = construir(params, objetivo, epsilon, desactivar)
    prob.solve(pulp.PULP_CBC_CMD(msg=1 if verbose else 0))

    status = pulp.LpStatus[prob.status]
    if status != "Optimal":
        return {
            "status": status,
            "objetivo": objetivo,
            "Z": None,
            "params": params,
        }

    z_variable = pulp.value(prob.objective)
    z_constante = datos.termino_constante(params, objetivo)

    x_tramos = {k: v.varValue for k, v in x.items()}
    x_total = {
        cod: sum(v for (c, _i), v in x_tramos.items() if c == cod)
        for cod in params["productos"]
    }

    return {
        "status": status,
        "objetivo": objetivo,
        "Z": z_variable + z_constante,
        "Z_variable": z_variable,
        "Z_constante": z_constante,
        "x": x_total,
        "x_tramos": x_tramos,
        "duales": {n: c.pi for n, c in prob.constraints.items()},
        "holguras": {n: c.slack for n, c in prob.constraints.items()},
        "params": params,
    }
