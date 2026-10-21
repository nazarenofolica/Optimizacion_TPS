"""
Parámetros del modelo de localización de CarroMenos (TP3).

Este módulo es la ÚNICA fuente de verdad de los datos del problema. Está dividido en dos bloques
que conviene no mezclar:

  1. DATOS DEL ENUNCIADO  -> demanda, centros, transporte, gerente y la regla de la pregunta e).
                             No se tocan.
  2. SUPUESTOS PROPIOS    -> lo que la consigna NO dice o deja ambiguo, y que adoptamos con
                             justificación (S1..S15 del docs/plan_de_trabajo.md §5). Los valores
                             que salen de una fuente externa (criterio "Explorar") están en
                             docs/procedimiento.md §1.1.

Las coordenadas y las distancias no viven acá: vienen del mapa (datos/) y las lee src/datos.py.

Uso:
    from src.config import construir_params
    params = construir_params()                         # caso base
    params = construir_params(Q=20)                     # test C
    params = construir_params(principal="al_menos_uno") # test B
"""

from copy import deepcopy

# ---------------------------------------------------------------------------
# 1. DATOS DEL ENUNCIADO
# ---------------------------------------------------------------------------

PRODUCTOS = ("Fideos", "Arroz", "Leche", "Gaseosas", "Galletitas")
SUPERMERCADOS = tuple(f"S{i}" for i in range(1, 11))

#: Demanda mensual promedio [pallets], por producto y supermercado S1..S10 (plan §2.3).
DEMANDA = {
    "Fideos":     (2000, 1900, 1800, 2100, 2500, 3000, 1200, 1700, 2100, 2000),
    "Arroz":      (1000,  900,  800, 1200,  500,  400,  850, 1200,  800,  900),
    "Leche":      ( 750,  800,  900, 1100, 1200,  950, 1000, 1100,  950, 1200),
    "Gaseosas":   ( 300,  400,  500,  540,  340,  500,  450,  400,  520,  600),
    "Galletitas": ( 800,  900,  850,  750,  950, 1000,  950,  850,  800,  650),
}

#: Centros de distribución (plan §2.1). capacidad [pallets/mes], apertura [$/mes],
#: costo por pallet operado [$].
CENTROS = {
    "A": {"capacidad": 40_000, "apertura": 3_000_000, "costo_pallet": 10},
    "B": {"capacidad": 35_000, "apertura": 2_500_000, "costo_pallet": 12},
    "C": {"capacidad": 15_000, "apertura": 1_200_000, "costo_pallet": 5},
    "D": {"capacidad": 10_000, "apertura": 900_000, "costo_pallet": 8},
}

#: "Debe elegir su centro principal para lo cual cuenta con dos opciones".
CENTROS_PRINCIPALES = ("A", "B")

#: Sueldo del gerente de coordinación logística, si se abren tres centros [$/mes].
GERENTE = 2_000_000

#: Transporte (plan §2.2).
PRECIO_DIESEL = 1_300     # $/litro
RENDIMIENTO = 4           # km/litro (el mismo camión en todos los tramos, S12)

#: Pregunta e): tope de km por conductor y penalidad por km excedido.
TOPE_KM_E = 500           # km por conductor y por mes (S14)
PENALIDAD_KM_E = 1_000    # $ por km excedido


# ---------------------------------------------------------------------------
# 2. SUPUESTOS PROPIOS  (docs/plan_de_trabajo.md §5, valores en procedimiento.md §1.1)
# ---------------------------------------------------------------------------

SUPUESTOS = {
    # S1 — Distancias. "osrm": por calle (datos/distancias_osrm.csv).
    #      "haversine": línea recta x factor de ruta (respaldo y test A).
    "distancias": "osrm",
    # S2 — Centro principal. "exclusivo": y_A + y_B = 1. "al_menos_uno": >= 1 (test B).
    "principal": "exclusivo",
    # S8 — Pallets por camión (DSV: 26 pallets de 1,00 x 1,20 no remontables). Test C: 20 a 30.
    "Q": 26,
    # S10 — La tarifa del tercerizado se paga sobre el km de ida (False) o ida y vuelta (test D).
    "tarifa_ida_vuelta": False,
    # S11 — Costo mensual de un conductor con aguinaldo y cargas (CCT 40/89, oct-2026).
    "W": 1_600_000,
    # S11 — km máximos por conductor y mes: 22 días x 350 km (desvío D1). Test E: 6.000 a 12.000.
    "K_max": 7_700,
    # S12 — kg de CO2 por litro de gasoil (IPCC 2006).
    "phi": 2.68,
    # S13 — Precio del carbono dentro del funcional [$ por kg de CO2]. 0 = no se monetiza (test F).
    "precio_co2": 0.0,
    # Tarifa del tercerizado [$/km]. Es dato de la consigna; está acá para los barridos (§10.4).
    "tarifa_T": 500,
    # Multiplicadores para los barridos y el test G (§10.4, §13). 1 = dato de la consigna.
    "factor_apertura": 1.0,
    "factor_demanda": 1.0,
}

#: Valores válidos de los supuestos que son una elección entre opciones.
OPCIONES = {
    "distancias": ("osrm", "haversine"),
    "principal": ("exclusivo", "al_menos_uno"),
    "tarifa_ida_vuelta": (False, True),
}

#: Rango admitido (mínimo, máximo) de los supuestos numéricos.
RANGOS = {
    "Q": (1, 40),
    "W": (0, 10_000_000),
    "K_max": (500, 30_000),
    "phi": (2.0, 3.5),
    "precio_co2": (0, 1_000),
    "tarifa_T": (0, 5_000),
    "factor_apertura": (0, 10),
    "factor_demanda": (0.1, 3),
}


# ---------------------------------------------------------------------------
# 3. Construcción del diccionario de parámetros
# ---------------------------------------------------------------------------


def construir_params(**overrides):
    """Devuelve el diccionario de parámetros del modelo.

    Parameters
    ----------
    **overrides
        Cualquier clave de SUPUESTOS. Ejemplos:
            construir_params(Q=20)
            construir_params(distancias="haversine")
            construir_params(tarifa_T=750, factor_demanda=1.1)

    Returns
    -------
    dict
        Con las claves: productos, supermercados, demanda {(super, producto): pallets},
        centros, principales, gerente, combustible_km, tope_km_e, penalidad_km_e, supuestos.

    Raises
    ------
    KeyError
        Si un supuesto no existe.
    ValueError
        Si un supuesto recibe un valor no válido o fuera de rango.
        Las dos validaciones son deliberadas: un typo silencioso devolvería el caso base
        haciéndose pasar por el escenario pedido.
    """
    supuestos = deepcopy(SUPUESTOS)
    for clave, valor in overrides.items():
        if clave not in supuestos:
            raise KeyError(f"Supuesto desconocido: {clave!r}. Válidos: {sorted(supuestos)}")
        if clave in OPCIONES and valor not in OPCIONES[clave]:
            raise ValueError(f"{clave}={valor!r} no es válido. Opciones: {OPCIONES[clave]}")
        if clave in RANGOS:
            if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                raise ValueError(f"{clave}={valor!r} tiene que ser un número")
            minimo, maximo = RANGOS[clave]
            if not minimo <= valor <= maximo:
                raise ValueError(f"{clave}={valor!r} fuera de rango [{minimo}, {maximo}]")
        supuestos[clave] = valor

    fd = supuestos["factor_demanda"]
    demanda = {
        (s, k): DEMANDA[k][i] * fd for k in PRODUCTOS for i, s in enumerate(SUPERMERCADOS)
    }
    centros = deepcopy(CENTROS)
    for c in centros.values():
        c["apertura"] *= supuestos["factor_apertura"]

    return {
        "productos": PRODUCTOS,
        "supermercados": SUPERMERCADOS,
        "demanda": demanda,
        "centros": centros,
        "principales": CENTROS_PRINCIPALES,
        "gerente": GERENTE,
        "rendimiento": RENDIMIENTO,
        "combustible_km": PRECIO_DIESEL / RENDIMIENTO,  # $325 por km físico
        "tope_km_e": TOPE_KM_E,
        "penalidad_km_e": PENALIDAD_KM_E,
        "supuestos": supuestos,
    }
