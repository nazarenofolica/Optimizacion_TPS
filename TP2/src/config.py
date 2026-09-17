"""
Parámetros del modelo de la Sección Cocinas de TODO DECO (TP2, punto a).

Este módulo es la ÚNICA fuente de verdad de los datos del problema. Está dividido en
dos bloques que conviene no mezclar:

  1. DATOS DEL ENUNCIADO  -> catálogo, composición de los 20 combos y capacidades del
                             depósito. No se tocan.
  2. SUPUESTOS PROPIOS    -> lo que la consigna NO dice o deja ambiguo, y que adoptamos
                             con justificación (S1..S3 del docs/plan_de_trabajo.md, §4).

La distinción importa para el informe: lo que se defiende ante la cátedra son los
supuestos, no los datos.

Uso:
    from src.config import construir_params
    params = construir_params()                                  # caso base
    params = construir_params(capacidades={"mesadas": 4})        # test de capacidad
    params = construir_params(S1_disponibilidad="compartida")    # test de S1
"""

from copy import deepcopy

# ---------------------------------------------------------------------------
# 1. DATOS DEL ENUNCIADO
# ---------------------------------------------------------------------------

#: Artículos que se ofrecen en los combos, agrupados por categoría.
#: El código de cada artículo empieza con la letra de su categoría.
CATALOGO = {
    "B": {
        "nombre": "Baldosas",
        "productos": {
            "B1": "Blanco",
            "B2": "Marfil",
            "B3": "Blanco y azul a cuadros",
            "B4": "Blanco y amarillo a cuadros",
        },
    },
    "E": {
        "nombre": "Empapelado vinílico",
        "productos": {
            "E1": "Símil marfil blanco",
            "E2": "Símil marfil a rayas celestes",
            "E3": "Símil mármol azul",
            "E4": "Símil mármol amarillo claro",
        },
    },
    "L": {
        "nombre": "Apliques de luz",
        "productos": {
            "L1": "Plafón único rectangular",
            "L2": "Plafones led ovalados",
            "L3": "Bombillas de filamentos",
            "L4": "Globos de luz fría",
        },
    },
    "A": {
        "nombre": "Alacenas",
        "productos": {
            "A1": "Madera clara",
            "A2": "Madera oscura",
            "A3": "Madera clara con puertas traslúcidas",
            "A4": "Madera oscura con puertas traslúcidas",
        },
    },
    "M": {
        "nombre": "Mesadas",
        "productos": {
            "M1": "Madera laqueada",
            "M2": "Cemento alisado",
            "M3": "Mármol sintético oscuro",
            "M4": "Granito",
        },
    },
    "G": {
        "nombre": "Bacha y grifería",
        "productos": {
            "G1": "Bacha dividida con grifo mono-comando",
            "G2": "Bacha dividida con grifos separados",
            "G3": "Bacha única con grifo mono-comando",
            "G4": "Bacha única con grifos separados",
        },
    },
    "W": {
        "nombre": "Lavavajillas",
        "productos": {
            "W1": "Blanco",
            "W2": "Gris",
        },
    },
    "C": {
        "nombre": "Cocinas",
        "productos": {
            "C1": "Cocina eléctrica blanca",
            "C2": "Cocina eléctrica negra",
            "C3": "Cocina a gas blanca",
            "C4": "Cocina a gas negra",
        },
    },
}

#: Composición de cada combo (tabla al pie de la consigna).
#: Ojo: los combos 12 y 13 no llevan empapelado, y del 14 al 20 no llevan lavavajillas.
COMBOS = {
    1: ("B2", "E2", "L4", "A2", "M4", "G2", "W2", "C2"),
    2: ("B1", "E1", "L1", "A4", "M4", "G4", "W1", "C2"),
    3: ("B1", "E2", "L2", "A1", "M1", "G4", "W1", "C3"),
    4: ("B3", "E3", "L3", "A3", "M3", "G1", "W1", "C1"),
    5: ("B4", "E4", "L1", "A2", "M2", "G2", "W1", "C1"),
    6: ("B2", "E2", "L2", "A4", "M4", "G3", "W2", "C4"),
    7: ("B1", "E3", "L4", "A3", "M2", "G1", "W1", "C1"),
    8: ("B2", "E1", "L3", "A1", "M1", "G3", "W2", "C4"),
    9: ("B4", "E1", "L2", "A3", "M2", "G2", "W2", "C2"),
    10: ("B1", "E4", "L1", "A1", "M3", "G4", "W1", "C3"),
    11: ("B3", "E4", "L3", "A3", "M1", "G1", "W1", "C3"),
    12: ("B2", "L1", "A2", "M2", "G4", "W2", "C2"),
    13: ("B4", "L3", "A3", "M1", "G2", "W1", "C3"),
    14: ("B4", "E1", "L4", "A1", "M3", "G1", "C1"),
    15: ("B3", "E2", "L1", "A1", "M1", "G3", "C3"),
    16: ("B3", "E3", "L4", "A1", "M3", "G2", "C1"),
    17: ("B1", "E3", "L2", "A3", "M3", "G4", "C3"),
    18: ("B2", "E3", "L3", "A2", "M4", "G1", "C2"),
    19: ("B2", "E2", "L4", "A4", "M4", "G2", "C4"),
    20: ("B2", "E2", "L1", "A1", "M2", "G3", "C4"),
}

#: Espacios del depósito. Cada espacio guarda una o más categorías y tiene una
#: capacidad en unidades. Modelarlo así (y no como un tope por categoría) hace que
#: el inciso c), donde mesadas y alacenas pasan a compartir lugar, sea un cambio de
#: datos y no de modelo.
ESPACIOS = {
    "baldosas": {"nombre": "Baldosas", "categorias": ("B",), "capacidad": 5},
    "empapelado": {"nombre": "Empapelado vinílico", "categorias": ("E",), "capacidad": 8},
    "apliques": {"nombre": "Apliques de luz", "categorias": ("L",), "capacidad": 4},
    "alacenas": {"nombre": "Alacenas", "categorias": ("A",), "capacidad": 4},
    "mesadas": {"nombre": "Mesadas", "categorias": ("M",), "capacidad": 3},
    "bachas": {"nombre": "Bacha y grifería", "categorias": ("G",), "capacidad": 4},
    # "Los lavavajillas y las cocinas tienen el mismo tamaño así que pueden
    # almacenarse juntos, con un máximo de 5 unidades en total."
    "lavav_cocinas": {"nombre": "Lavavajillas + cocinas", "categorias": ("W", "C"), "capacidad": 5},
}


# ---------------------------------------------------------------------------
# 2. SUPUESTOS PROPIOS  (docs/plan_de_trabajo.md §4)
# ---------------------------------------------------------------------------

SUPUESTOS = {
    # S1 — Qué significa "combo disponible" con reposición mensual.
    #      "exclusiva"  -> cada combo ofrecido tiene su propio juego de unidades
    #                      reservado para el mes (si dos combos usan B2, hacen falta 2).
    #      "compartida" -> alcanza con una unidad de cada artículo. Es la lectura del
    #                      inciso b) (reposición automática); acá solo se usa como test.
    "S1_disponibilidad": "exclusiva",
    # S2 — Unidades de cada artículo que lleva un combo, por categoría.
    #      La consigna lista qué artículos trae cada combo, no cuántos. El único
    #      dudoso es el empapelado (una cocina puede necesitar más de un rollo).
    "S2_unidades_por_articulo": {cat: 1 for cat in CATALOGO},
    # S3 — Criterio de desempate entre soluciones de igual variedad.
    #      "categorias_y_unidades" -> primero el plan que deja más categorías del
    #                                 catálogo en algún combo ofrecido (la consigna
    #                                 enumera lo que vende la sección); después, el
    #                                 que menos lugar ocupa. Caso base
    #                                 (docs/procedimiento.md §2.5).
    #      "min_unidades"          -> solo el que menos lugar ocupa. Era el caso base
    #                                 del plan; dejaba la sección sin lavavajillas.
    #      "max_articulos"         -> los combos más completos.
    #      "ninguno"               -> lo que elija el solver; solo se ajusta el stock.
    "S3_desempate": "categorias_y_unidades",
}

#: Valores válidos de los supuestos que son una elección entre opciones.
OPCIONES = {
    "S1_disponibilidad": ("exclusiva", "compartida"),
    "S3_desempate": ("categorias_y_unidades", "min_unidades", "max_articulos", "ninguno"),
}


# ---------------------------------------------------------------------------
# 3. Construcción del diccionario de parámetros
# ---------------------------------------------------------------------------


def construir_params(capacidades=None, espacios=None, **overrides):
    """Devuelve el diccionario de parámetros del modelo.

    Parameters
    ----------
    capacidades : dict, optional
        {espacio: capacidad} para pisar capacidades del depósito. Es lo que usan
        los tests de "un lugar más" (plan §10.1).
    espacios : dict, optional
        Reemplaza por completo la estructura de espacios del depósito (por defecto,
        `ESPACIOS`). Es lo que necesita el inciso c) (plan §17.2): mesadas y
        alacenas pasan a compartir un espacio nuevo, en vez de tener uno cada una.
        `capacidades` se aplica encima de este argumento, no de `ESPACIOS`.
    **overrides
        Cualquier clave de SUPUESTOS. `S2_unidades_por_articulo` se combina con el
        valor base: alcanza con pasar las categorías que cambian.

        Ejemplos:
            construir_params(S1_disponibilidad="compartida")
            construir_params(S2_unidades_por_articulo={"E": 3})
            construir_params(capacidades={"mesadas": 4})
            construir_params(espacios=espacios_c, S1_disponibilidad="compartida")

    Returns
    -------
    dict
        Con las claves: catalogo, combos, espacios, supuestos.

    Raises
    ------
    KeyError
        Si un supuesto, una categoría o un espacio no existe.
    ValueError
        Si un supuesto de opciones recibe un valor no válido.
        Las dos validaciones son deliberadas: un typo silencioso devolvería el caso
        base haciéndose pasar por el escenario pedido.
    """
    supuestos = deepcopy(SUPUESTOS)
    for clave, valor in overrides.items():
        if clave not in supuestos:
            raise KeyError(f"Supuesto desconocido: {clave!r}. Válidos: {sorted(supuestos)}")
        if clave in OPCIONES and valor not in OPCIONES[clave]:
            raise ValueError(f"{clave}={valor!r} no es válido. Opciones: {OPCIONES[clave]}")
        if clave == "S2_unidades_por_articulo":
            desconocidas = set(valor) - set(CATALOGO)
            if desconocidas:
                raise KeyError(f"Categorías desconocidas en S2: {sorted(desconocidas)}")
            supuestos[clave].update(valor)
        else:
            supuestos[clave] = valor

    espacios = deepcopy(espacios if espacios is not None else ESPACIOS)
    for espacio, capacidad in (capacidades or {}).items():
        if espacio not in espacios:
            raise KeyError(f"Espacio desconocido: {espacio!r}. Válidos: {sorted(espacios)}")
        espacios[espacio]["capacidad"] = capacidad

    return {
        "catalogo": deepcopy(CATALOGO),
        "combos": deepcopy(COMBOS),
        "espacios": espacios,
        "supuestos": supuestos,
    }
