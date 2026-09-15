"""
Tablas derivadas y chequeos de factibilidad del modelo de la Sección Cocinas.

Todas las funciones son puras: reciben `params` (de config.construir_params) y no
tocan estado global. Implementan las tablas derivadas del docs/plan_de_trabajo.md
§3.4 a §3.6 y la enumeración exhaustiva de §8.

Unidades: todo se mide en unidades de stock, que son también los "lugares" del
depósito (un juego de baldosas, un rollo, un aplique, una cocina...; supuesto S4).
"""

from itertools import combinations


def categoria(producto):
    """Categoría de un artículo: la letra con la que empieza su código."""
    return producto[0]


def productos(params):
    """Los 30 artículos del catálogo, en orden de categoría."""
    return [p for cat in params["catalogo"].values() for p in cat["productos"]]


def espacio_de_categoria(params):
    """{categoría: espacio del depósito donde se guarda}."""
    return {cat: esp for esp, d in params["espacios"].items() for cat in d["categorias"]}


def unidades(params, producto):
    """Unidades de un artículo que lleva un combo (supuesto S2)."""
    return params["supuestos"]["S2_unidades_por_articulo"][categoria(producto)]


def combos_que_usan(params):
    """{artículo: [combos que lo incluyen]}. Es la matriz a_pc leída por columnas."""
    usan = {p: [] for p in productos(params)}
    for c, articulos in sorted(params["combos"].items()):
        for p in articulos:
            usan[p].append(c)
    return usan


def categorias_cubiertas(params, combos):
    """Categorías del catálogo que trae al menos uno de los `combos`."""
    return {categoria(p) for c in combos for p in params["combos"][c]}


def apariciones(params):
    """En cuántos combos aparece cada artículo.  (plan §3.4)"""
    return {p: len(cs) for p, cs in combos_que_usan(params).items()}


def lugares_por_combo(params):
    """{combo: {espacio: lugares}} que ocupa un juego completo de cada combo.  (plan §3.5)"""
    espacio_de = espacio_de_categoria(params)
    lugares = {}
    for c, articulos in params["combos"].items():
        uso = {e: 0 for e in params["espacios"]}
        for p in articulos:
            uso[espacio_de[categoria(p)]] += unidades(params, p)
        lugares[c] = uso
    return lugares


def cota_trivial(params):
    """Cota superior de la variedad que impone cada espacio por sí solo.  (plan §3.6)

    Si todos los combos ocupan al menos u lugares de un espacio de capacidad K, no se
    pueden reservar más de K // u combos. Devuelve None para los espacios que algún
    combo no usa (esos no acotan nada).
    """
    lugares = lugares_por_combo(params)
    cotas = {}
    for e, d in params["espacios"].items():
        minimo = min(lugares[c][e] for c in lugares)
        cotas[e] = None if minimo == 0 else d["capacidad"] // minimo
    return cotas


def stock_requerido(params, disponibilidad):
    """Stock mínimo que exige un vector de disponibilidad {combo: y_c}, según S1.

    exclusiva  -> cada combo reserva sus propias unidades: se suman u·y_c.
    compartida -> alcanza con las unidades de un combo: se toma el máximo de u·y_c.

    Acepta y_c fraccionarios para poder medir la relajación lineal: ahí el solver
    llena el depósito con stock que no usa, y la ocupación real no dice nada.
    """
    exclusiva = params["supuestos"]["S1_disponibilidad"] == "exclusiva"
    stock = {p: 0 for p in productos(params)}
    for c, peso in disponibilidad.items():
        for p in params["combos"][c]:
            necesario = unidades(params, p) * peso
            stock[p] = stock[p] + necesario if exclusiva else max(stock[p], necesario)
    return stock


def stock_necesario(params, combos):
    """Stock mínimo para que `combos` queden disponibles, según la lectura S1."""
    return stock_requerido(params, {c: 1 for c in combos})


def ocupacion(params, stock):
    """{espacio: lugares ocupados} por un stock dado."""
    espacio_de = espacio_de_categoria(params)
    uso = {e: 0 for e in params["espacios"]}
    for p, cantidad in stock.items():
        uso[espacio_de[categoria(p)]] += cantidad
    return uso


def es_factible(params, combos):
    """¿Entra en el depósito el stock necesario para ofrecer `combos`?"""
    uso = ocupacion(params, stock_necesario(params, combos))
    return all(uso[e] <= d["capacidad"] for e, d in params["espacios"].items())


def enumerar_factibles(params, k):
    """Todos los conjuntos de k combos que entran en el depósito.  (plan §8)

    Fuerza bruta pura, sin solver: es el control independiente del modelo. Si el
    solver dice V* y acá hay conjuntos factibles de tamaño V* pero ninguno de V*+1,
    los dos caminos coinciden.
    """
    return [S for S in combinations(sorted(params["combos"]), k) if es_factible(params, S)]
