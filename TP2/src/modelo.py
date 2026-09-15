"""
Modelo de programación lineal entera de la Sección Cocinas (TP2, punto a).

Un único modelo parametrizado que sirve para todo: la máxima variedad, el desempate
lexicográfico, la relajación lineal y los tests de supuestos. La variación se maneja
por argumentos, nunca copiando el modelo.

    resolver(params)                                             # etapa 1: máxima variedad
    resolver(params, objetivo="max_categorias", variedad_min=3)  # etapa 2: categorías cubiertas
    resolver(params, objetivo="min_unidades", variedad_min=3,
             categorias_min=8)                                   # etapa 3: mínimo stock
    resolver(params, relajar=True)                               # relajación lineal
    resolver_lexicografico(params)                               # todas las etapas, según S3

Las restricciones llevan nombre (R1_cob_<artículo>, R2_cap_<espacio>) para poder
leer holguras y, en la relajación, precios sombra.
"""

import pulp

from . import datos

#: Funcionales soportados (docs/plan_de_trabajo.md §6 y docs/procedimiento.md §2.5).
#:   variedad       -> Max Σ y_c                   (etapa 1)
#:   max_categorias -> Max Σ z_k                   (categorías que quedan en algún combo ofrecido)
#:   min_unidades   -> Min Σ x_p                   (stock total)
#:   max_articulos  -> Max Σ n_c·y_c − ε·Σ x_p     (desempate alternativo: combos más completos)
OBJETIVOS = ("variedad", "max_categorias", "min_unidades", "max_articulos")

_SOLVER = pulp.PULP_CBC_CMD(msg=False)


def construir(
    params,
    objetivo="variedad",
    variedad_min=None,
    categorias_min=None,
    combos_fijos=None,
    relajar=False,
):
    """Arma el problema y devuelve (problema, x, y).

    Parameters
    ----------
    params : dict
        Salida de `config.construir_params()`.
    objetivo : {"variedad", "max_categorias", "min_unidades", "max_articulos"}
        Qué funcional optimizar.
    variedad_min : int, optional
        Agrega `Σ y_c >= variedad_min`. Ata las etapas de desempate a la etapa 1.
    categorias_min : int, optional
        Agrega `Σ z_k >= categorias_min`: al menos esa cantidad de categorías del
        catálogo tienen que quedar en algún combo ofrecido. Ata la etapa 3 a la 2.
    combos_fijos : iterable of int, optional
        Fija exactamente qué combos se ofrecen. Sirve para ajustar el stock de una
        solución ya elegida (desempate "ninguno").
    relajar : bool
        Si es True, las variables enteras y binarias pasan a continuas (plan §6.4).
    """
    if objetivo not in OBJETIVOS:
        raise ValueError(f"Objetivo desconocido: {objetivo!r}. Válidos: {OBJETIVOS}")

    sentido = pulp.LpMinimize if objetivo == "min_unidades" else pulp.LpMaximize
    prob = pulp.LpProblem(f"cocinas_{objetivo}", sentido)

    cat_bin = pulp.LpContinuous if relajar else pulp.LpBinary
    cat_x = pulp.LpContinuous if relajar else pulp.LpInteger
    combos = sorted(params["combos"])
    articulos = datos.productos(params)
    y = {c: pulp.LpVariable(f"y_{c:02d}", 0, 1, cat_bin) for c in combos}
    x = {p: pulp.LpVariable(f"x_{p}", 0, None, cat_x) for p in articulos}

    # z_k = 1 si la categoría k está en al menos un combo ofrecido. Solo se crean
    # cuando las usa el funcional o una atadura, para no agrandar el modelo base.
    z = {}
    if objetivo == "max_categorias" or categorias_min is not None:
        z = {k: pulp.LpVariable(f"z_{k}", 0, 1, cat_bin) for k in params["catalogo"]}

    variedad = pulp.lpSum(y.values())
    stock_total = pulp.lpSum(x.values())

    # --- Funcional ----------------------------------------------------------
    if objetivo == "variedad":
        prob += variedad
    elif objetivo == "max_categorias":
        prob += pulp.lpSum(z.values())
    elif objetivo == "min_unidades":
        prob += stock_total
    else:
        # Cada artículo de un combo suma 1; el término −ε·Σx evita stock sobrante sin
        # poder cambiar la elección de combos: ε · (lugares totales) < 1.
        lugares = datos.lugares_por_combo(params)
        eps = 1 / (sum(d["capacidad"] for d in params["espacios"].values()) + 1)
        prob += pulp.lpSum(sum(lugares[c].values()) * y[c] for c in combos) - eps * stock_total

    # --- R1: cobertura (plan §7) ----------------------------------------------
    usan = datos.combos_que_usan(params)
    exclusiva = params["supuestos"]["S1_disponibilidad"] == "exclusiva"
    for p in articulos:
        u = datos.unidades(params, p)
        if exclusiva:
            prob += x[p] >= pulp.lpSum(u * y[c] for c in usan[p]), f"R1_cob_{p}"
        else:
            for c in usan[p]:
                prob += x[p] >= u * y[c], f"R1_cob_{p}_c{c:02d}"

    # --- R2 y R2': capacidad de cada espacio del depósito ---------------------
    espacio_de = datos.espacio_de_categoria(params)
    for e, d in params["espacios"].items():
        en_espacio = [x[p] for p in articulos if espacio_de[datos.categoria(p)] == e]
        prob += pulp.lpSum(en_espacio) <= d["capacidad"], f"R2_cap_{e}"

    # --- Cobertura de categorías ------------------------------------------------
    # z_k se ata a los combos ofrecidos y no al stock: si no, el solver "cubriría"
    # una categoría guardando una unidad suelta que no usa ningún combo.
    for k, zk in z.items():
        con_k = [y[c] for c in combos if k in datos.categorias_cubiertas(params, [c])]
        prob += zk <= pulp.lpSum(con_k), f"CAT_{k}"

    # --- Ataduras entre etapas ---------------------------------------------------
    if variedad_min is not None:
        prob += variedad >= variedad_min, "E2_variedad_min"
    if categorias_min is not None:
        prob += pulp.lpSum(z.values()) >= categorias_min, "E3_categorias_min"
    if combos_fijos is not None:
        fijos = set(combos_fijos)
        for c in combos:
            prob += y[c] == (1 if c in fijos else 0), f"FIJO_y_{c:02d}"

    return prob, x, y


def resolver(
    params,
    objetivo="variedad",
    variedad_min=None,
    categorias_min=None,
    combos_fijos=None,
    relajar=False,
):
    """Construye, resuelve y devuelve un dict con los resultados.

    Claves: status, objetivo, relajado, params y, si el estado es Optimal: Z,
    variedad, combos, categorias, y, stock, unidades, ocupacion, holgura y
    ocupacion_necesaria. Si `relajar` es True, además `duales` con el precio
    sombra de cada espacio.

    `ocupacion` mide el stock que dejó el solver; `ocupacion_necesaria`, el que
    exigen los combos elegidos. Difieren cuando el funcional no penaliza el stock
    (etapa 1 y relajación lineal), porque el solver puede guardar unidades de más.
    """
    prob, x, y = construir(
        params,
        objetivo=objetivo,
        variedad_min=variedad_min,
        categorias_min=categorias_min,
        combos_fijos=combos_fijos,
        relajar=relajar,
    )
    prob.solve(_SOLVER)

    res = {
        "status": pulp.LpStatus[prob.status],
        "objetivo": objetivo,
        "relajado": relajar,
        "params": params,
    }
    if res["status"] != "Optimal":
        return res

    valores_y = {c: v.varValue or 0.0 for c, v in y.items()}
    valores_x = {p: v.varValue or 0.0 for p, v in x.items()}
    if not relajar:
        # CBC devuelve los enteros con ruido numérico (0.9999999); se redondean.
        valores_y = {c: round(v) for c, v in valores_y.items()}
        valores_x = {p: round(v) for p, v in valores_x.items()}

    combos = [c for c, v in valores_y.items() if v > 1e-6]
    ocupado = datos.ocupacion(params, valores_x)
    res.update(
        Z=pulp.value(prob.objective),
        variedad=sum(valores_y.values()),
        combos=combos,
        categorias=len(datos.categorias_cubiertas(params, combos)),
        y=valores_y,
        stock=valores_x,
        unidades=sum(valores_x.values()),
        ocupacion=ocupado,
        holgura={e: d["capacidad"] - ocupado[e] for e, d in params["espacios"].items()},
        ocupacion_necesaria=datos.ocupacion(params, datos.stock_requerido(params, valores_y)),
    )
    if relajar:
        # "+ 0.0" normaliza los -0.0 que devuelve CBC para que no ensucien los reportes.
        res["duales"] = {e: prob.constraints[f"R2_cap_{e}"].pi + 0.0 for e in params["espacios"]}
    return res


def resolver_lexicografico(params):
    """Resuelve por etapas según el criterio de desempate S3.  (plan §6.3, procedimiento §2.5)

    Devuelve (etapa1, final). `final` es la solución a reportar: misma variedad que
    la etapa 1 y stock sin excedentes.

      categorias_y_unidades -> 1) máx. variedad  2) máx. categorías  3) mín. unidades
      min_unidades          -> 1) máx. variedad  2) mín. unidades
      max_articulos         -> 1) máx. variedad  2) máx. artículos, sin stock sobrante
      ninguno               -> 1) máx. variedad, y se le quita el stock sobrante
    """
    etapa1 = resolver(params, "variedad")
    if etapa1["status"] != "Optimal":
        return etapa1, etapa1

    v_max = etapa1["variedad"]
    criterio = params["supuestos"]["S3_desempate"]
    if criterio == "ninguno":
        return etapa1, resolver(params, "min_unidades", combos_fijos=etapa1["combos"])
    if criterio == "categorias_y_unidades":
        etapa2 = resolver(params, "max_categorias", variedad_min=v_max)
        if etapa2["status"] != "Optimal":
            return etapa1, etapa2
        final = resolver(params, "min_unidades", variedad_min=v_max, categorias_min=etapa2["categorias"])
        return etapa1, final
    return etapa1, resolver(params, criterio, variedad_min=v_max)
