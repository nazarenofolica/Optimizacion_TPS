"""
Parámetros del modelo Pastarazzi.

Este módulo es la ÚNICA fuente de verdad de los números del problema. Está dividido en
dos bloques que conviene no mezclar:

  1. DATOS DEL ENUNCIADO  -> números que la consigna provee. No se tocan.
  2. SUPUESTOS PROPIOS    -> números que la consigna NO provee o deja ambiguos, y que
                             nosotros adoptamos con justificación (S1..S9 del
                             docs/plan_de_trabajo.md, §4).

La distinción importa para el informe: lo que se defiende ante la cátedra son los
supuestos, no los datos.

Uso:
    from src.config import construir_params
    params = construir_params()                          # caso base
    params = construir_params(S1_tasa_triguetti=260)     # variante para los tests ±30%
"""

from copy import deepcopy

# ---------------------------------------------------------------------------
# 1. DATOS DEL ENUNCIADO
# ---------------------------------------------------------------------------

#: Presupuesto de marketing de la campaña, en millones de AR$.
PRESUPUESTO = 17_000

#: Segmentos de mercado (Fig. 3): tamaño y gasto anual en pastas por persona.
MERCADO = {
    "bajo": {"tam": 21_500_000, "gasto": 41_000},
    "medio": {"tam": 10_600_000, "gasto": 58_000},
    "alto": {"tam": 1_200_000, "gasto": 134_000},
}

#: Marcas del portafolio.
#:   precio  : AR$ por paquete de 500 g            (Fig. 1)
#:   m_oper  : margen operativo                     (Fig. 1)
#:   m_neto  : margen neto                          (Fig. 1)
#:   share   : market share inicial por segmento    (Fig. 2)
#:   segmento: segmento donde capta clientes nuevos (SUPUESTO S5, ver abajo)
PRODUCTOS = {
    "DC": {
        "nombre": "Don Carlo",
        "precio": 700,
        "m_oper": 0.090,
        "m_neto": 0.050,
        "share": {"bajo": 0.35, "medio": 0.02, "alto": 0.00},
        "segmento": "bajo",
    },
    "AG": {
        "nombre": "Agnellis",
        "precio": 850,
        "m_oper": 0.100,
        "m_neto": 0.075,
        "share": {"bajo": 0.18, "medio": 0.05, "alto": 0.02},
        "segmento": "bajo",
    },
    "TRI": {
        "nombre": "Triguetti",
        "precio": 1_200,
        "m_oper": 0.112,
        "m_neto": 0.090,
        "share": {"bajo": 0.00, "medio": 0.30, "alto": 0.01},
        "segmento": "medio",
    },
    "CAN": {
        "nombre": "Candealix",
        "precio": 1_800,
        "m_oper": 0.111,
        "m_neto": 0.080,
        "share": {"bajo": 0.00, "medio": 0.12, "alto": 0.03},
        "segmento": "medio",
    },
    "RS": {
        "nombre": "Rena Speziale",
        "precio": 3_500,
        "m_oper": 0.160,
        "m_neto": 0.100,
        "share": {"bajo": 0.00, "medio": 0.01, "alto": 0.08},
        "segmento": "alto",
    },
}

#: Tramos de captación de cada marca, en orden de eficiencia decreciente.
#:   limite  : tope del tramo en $MM (None = sin tope)
#:   tasa    : clientes nuevos captados por $MM invertido en ese tramo
#:   etiqueta: nombre legible para los reportes
#:
#: El último tramo de cada marca es de "desperdicio": tasa 0 y sin tope. Representa
#: la plata que se puede invertir sin captar a nadie, sea porque el producto ya
#: saturó su respuesta (Triguetti) o porque el segmento se quedó sin gente por
#: captar (restricción R10). Sin él, las reglas del directorio pueden volver
#: infactible el problema en lugar de mostrar que obligan a quemar presupuesto.
#:
#: La tasa del primer tramo de Triguetti es el supuesto S1: la inyecta
#: construir_params(), por eso queda en None acá.
TASAS = {
    "DC": [
        {"limite": None, "tasa": 400, "etiqueta": "captación"},
        {"limite": None, "tasa": 0, "etiqueta": "desperdicio"},
    ],
    "AG": [
        {"limite": None, "tasa": 500, "etiqueta": "captación"},
        {"limite": None, "tasa": 0, "etiqueta": "desperdicio"},
    ],
    "TRI": [
        {"limite": 6_000, "tasa": None, "etiqueta": "hasta saturar"},
        {"limite": None, "tasa": 0, "etiqueta": "desperdicio"},
    ],
    "CAN": [
        {"limite": 5_000, "tasa": 300, "etiqueta": "1er tramo"},
        {"limite": None, "tasa": 200, "etiqueta": "2do tramo"},
        {"limite": None, "tasa": 0, "etiqueta": "desperdicio"},
    ],
    "RS": [
        {"limite": 3_500, "tasa": 150, "etiqueta": "1er tramo"},
        {"limite": None, "tasa": 100, "etiqueta": "2do tramo"},
        {"limite": None, "tasa": 0, "etiqueta": "desperdicio"},
    ],
}

#: Reglas comerciales y del directorio (los "term. independientes" de las restricciones).
REGLAS = {
    "R3_pct_triguetti": 0.30,  # Triguetti >= 30% del presupuesto
    "R4_multiplo_rena": 2.0,  # Rena >= 2 x (Candealix + Triguetti)
    "R5_tope_gama_baja": 0.65,  # Don Carlo + Agnellis <= 65% del segmento bajo
    "R6_umbral_candealix": 2_500_000,  # unidades mínimas para producir Candealix
    # R10 — Saturación física del mercado: nadie puede captar más clientes de los
    # que el segmento tiene. NO está en el enunciado; se agrega porque sin ella el
    # modelo produce participaciones de más del 100% (ver docs/procedimiento.md §2).
    # 1.00 = hasta el 100% del TAM. Es una cota conservadora: el techo comercial
    # realista es más bajo, y por eso el valor queda parametrizado.
    "R10_tope_saturacion": 1.00,
}


# ---------------------------------------------------------------------------
# 2. SUPUESTOS PROPIOS  (docs/plan_de_trabajo.md §4)
# ---------------------------------------------------------------------------

SUPUESTOS = {
    # S1 — Tasa de captación de Triguetti en su primer tramo [clientes/$MM].
    #      El enunciado da el punto de saturación ($6.000MM) pero NUNCA la tasa.
    #      Adoptamos 200: Triguetti compite en el mismo segmento que Candealix
    #      (300 cl/$MM) pero el enunciado le atribuye "menor elasticidad".
    #      Rango de test: 140-260 (±30%). Cota dura superior: 300.
    "S1_tasa_triguetti": 200,
    # S2 — Tasa de captura de billetera [0..1].
    #      Fracción del gasto anual en pastas que el cliente captado destina a la
    #      marca que lo captó. 1.0 = todo. Sobreestima el retorno del marketing.
    #      Rango de test: 0.70-1.00.
    "S2_captura_billetera": 1.00,
    # S5 — Segmento donde capta clientes cada marca.
    #      "posicionamiento" -> el campo PRODUCTOS[j]["segmento"] (opción A del plan)
    #      "mix_fig2"        -> reparto según el mix normalizado de la Fig. 2 (opción B)
    "S5_segmento_captacion": "posicionamiento",
    # S6 — Lectura de la restricción R2 (paridad Don Carlo / Agnellis).
    #      "igualdad" -> x_DC = x_AG
    #      "libre"    -> sin restricción (se usa en la pregunta b)
    #      float k    -> x_DC = k * x_AG (parametrización de la pregunta b)
    "S6_paridad_dc_ag": "igualdad",
    # S7 — Lecturas de R3 y R4.
    #      R4: ">=" (piso exigido) o "==" (cuota exacta)
    #      R3: "presupuesto_total" (30% de 17.000) o "asignado" (30% de la suma de x_j)
    "S7_operador_r4": ">=",
    "S7_base_r3": "presupuesto_total",
    # S8 — ¿Se descuenta el presupuesto de marketing del funcional?
    #      False: se trata como recurso a asignar (evita doble conteo con el margen).
    "S8_descontar_presupuesto": False,
}


# ---------------------------------------------------------------------------
# 3. Construcción del diccionario de parámetros
# ---------------------------------------------------------------------------

#: Objetivos soportados por el modelo.
OBJETIVOS = ("neta", "oper", "facturacion")

#: Etiqueta legible de cada objetivo, para los reportes.
ETIQUETA_OBJETIVO = {
    "neta": "Utilidad neta",
    "oper": "Utilidad operativa",
    "facturacion": "Facturación (market share)",
}


def construir_params(**overrides):
    """Devuelve el diccionario de parámetros del modelo, ya resuelto.

    Resolver significa que los supuestos quedan inyectados donde corresponde: por
    ejemplo, S1 se escribe dentro de TASAS["TRI"], de modo que el resto del código
    no necesita saber que ese número era un supuesto.

    Parameters
    ----------
    **overrides
        Cualquier clave de SUPUESTOS o de REGLAS, para pisar su valor base.
        Es el mecanismo con el que se corren los barridos ±30% y los escenarios
        de las preguntas b), c) y d), sin tocar el modelo.

        Ejemplos:
            construir_params(S1_tasa_triguetti=140)
            construir_params(R3_pct_triguetti=0.0)      # correr sin la regla del 30%
            construir_params(S6_paridad_dc_ag="libre")

    Returns
    -------
    dict
        Con las claves: presupuesto, mercado, productos, tasas, reglas, supuestos.

    Raises
    ------
    KeyError
        Si un override no corresponde a ningún supuesto ni regla conocida. Es
        deliberado: un typo en un barrido de 40 corridas es un error silencioso caro.
    """
    supuestos = deepcopy(SUPUESTOS)
    reglas = deepcopy(REGLAS)

    for clave, valor in overrides.items():
        if clave in supuestos:
            supuestos[clave] = valor
        elif clave in reglas:
            reglas[clave] = valor
        else:
            raise KeyError(
                f"Override desconocido: {clave!r}. "
                f"Válidos: {sorted(supuestos) + sorted(reglas)}"
            )

    tasas = deepcopy(TASAS)
    # S1: inyectar la tasa asumida de Triguetti en su primer tramo.
    tasas["TRI"][0]["tasa"] = supuestos["S1_tasa_triguetti"]

    return {
        "presupuesto": PRESUPUESTO,
        "mercado": deepcopy(MERCADO),
        "productos": deepcopy(PRODUCTOS),
        "tasas": tasas,
        "reglas": reglas,
        "supuestos": supuestos,
    }
