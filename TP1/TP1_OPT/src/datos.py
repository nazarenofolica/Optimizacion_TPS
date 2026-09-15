"""
Tablas derivadas del modelo Pastarazzi.

Todas las funciones son puras: reciben `params` (de config.construir_params) y no
tocan estado global. Cada una implementa una de las tablas derivadas del
docs/plan_de_trabajo.md §3.4 a §3.7.

Unidades, para no perderse:
    - inversión, facturación y utilidad ...... millones de AR$  ($MM)
    - clientes ............................... personas
    - gasto por persona ...................... AR$/año (NO millones)
    - tasas de captación ..................... clientes por $MM invertido
"""

#: Pesos = millones de pesos. Se usa para pasar de AR$ a $MM.
MILLON = 1_000_000


def mercado_por_segmento(params):
    """Tamaño de cada segmento en $MM/año.  (plan §3.4)

    mercado_s = TAM_s x gasto_s
    """
    return {
        seg: datos["tam"] * datos["gasto"] / MILLON
        for seg, datos in params["mercado"].items()
    }


def facturacion_base(params):
    """Facturación de cada marca antes de invertir en marketing, en $MM/año. (plan §3.5)

    F_base_j = suma sobre segmentos de (share_js x mercado_s)
    """
    mercado = mercado_por_segmento(params)
    return {
        cod: sum(share * mercado[seg] for seg, share in prod["share"].items())
        for cod, prod in params["productos"].items()
    }


def facturacion_base_por_segmento(params):
    """Facturación base desagregada como {marca: {segmento: $MM}}.

    Hace falta para la tabla de canales: la facturación base de una marca vive en
    varios segmentos aunque su captación incremental vaya a uno solo (supuesto S5).
    """
    mercado = mercado_por_segmento(params)
    return {
        cod: {seg: share * mercado[seg] for seg, share in prod["share"].items()}
        for cod, prod in params["productos"].items()
    }


def tramos(params):
    """Lista de tramos del modelo como (marca, indice, tramo).

    `tramo` es el dict de config.TASAS: {"limite", "tasa", "etiqueta"}.
    El índice arranca en 1 para que los nombres de variable queden x_TRI1, x_TRI2...,
    igual que en el docs/plan_de_trabajo.md §5.2.
    """
    return [
        (cod, i, tramo)
        for cod, lista in params["tasas"].items()
        for i, tramo in enumerate(lista, start=1)
    ]


def segmentos_captacion(params, cod):
    """En qué segmento(s) capta clientes nuevos la marca `cod`, y con qué peso. (S5)

    Supuesto S5 (plan §4.2), con dos lecturas:

    - "posicionamiento" (opción A, la base): toda la captación incremental de una
      marca va a un único segmento, el de su posicionamiento de producto
      (`PRODUCTOS[cod]["segmento"]`). Es la lectura que sostiene el propio
      enunciado cuando mide el tope de Don Carlo + Agnellis contra "el mercado
      de menor poder adquisitivo".
    - "mix_fig2" (opción B): se reparte según el mix de ventas ya observado en la
      Fig. 2, normalizado a 1. Por ejemplo, Agnellis vende 18/5/2 en
      bajo/medio/alto (share de la Fig. 2): un cliente nuevo de Agnellis se
      reparte en esas mismas proporciones (18/25, 5/25, 2/25) entre los tres
      segmentos. Es más fina pero no está sostenida por ningún dato adicional:
      solo reinterpreta la Fig. 2 como si describiera también a los clientes
      *nuevos*, no solo a la base instalada.

    Returns
    -------
    list of (segmento, peso)
        Los pesos suman 1.0.
    """
    prod = params["productos"][cod]
    modo = params["supuestos"]["S5_segmento_captacion"]
    if modo == "posicionamiento":
        return [(prod["segmento"], 1.0)]
    if modo == "mix_fig2":
        total = sum(prod["share"].values())
        return [(seg, sh / total) for seg, sh in prod["share"].items() if sh > 0]
    raise ValueError(f"S5_segmento_captacion desconocido: {modo!r}")


def facturacion_por_millon(params):
    """Facturación incremental que genera cada $MM invertido, por tramo. (plan §3.7)

    f = tasa [clientes/$MM] x gasto_efectivo [AR$/cliente] x beta / 1e6

    donde beta es la tasa de captura de billetera (supuesto S2) y gasto_efectivo es
    el promedio del gasto por segmento, ponderado por dónde capta la marca (S5).
    Bajo la opción base de S5 ("posicionamiento") esto es simplemente el gasto del
    único segmento de la marca.

    Returns
    -------
    dict
        {(marca, indice_tramo): $MM de facturación por $MM invertido}
    """
    beta = params["supuestos"]["S2_captura_billetera"]
    coefs = {}
    for cod, i, tramo in tramos(params):
        gasto = sum(
            peso * params["mercado"][seg]["gasto"]
            for seg, peso in segmentos_captacion(params, cod)
        )
        coefs[(cod, i)] = tramo["tasa"] * gasto * beta / MILLON
    return coefs


def coeficientes(params, objetivo):
    """Coeficientes del funcional, por tramo. (plan §6.2 a §6.4)

    Parameters
    ----------
    objetivo : {"neta", "oper", "facturacion"}
        Cuál de los tres funcionales se está armando.

    Returns
    -------
    dict
        {(marca, indice_tramo): coeficiente}
    """
    fact = facturacion_por_millon(params)
    if objetivo == "facturacion":
        return dict(fact)

    campo = {"neta": "m_neto", "oper": "m_oper"}[objetivo]
    return {
        (cod, i): valor * params["productos"][cod][campo]
        for (cod, i), valor in fact.items()
    }


def termino_constante(params, objetivo):
    """Parte del funcional que no depende de las variables. (plan §6.1)

    Es la utilidad (o facturación) que la empresa obtiene aunque no invierta un peso.
    No afecta al óptimo, pero sin ella las cifras no tienen sentido de negocio.
    """
    base = facturacion_base(params)
    if objetivo == "facturacion":
        return sum(base.values())

    campo = {"neta": "m_neto", "oper": "m_oper"}[objetivo]
    return sum(f * params["productos"][cod][campo] for cod, f in base.items())


def cupo_gama_baja(params):
    """Clientes que Don Carlo y Agnellis todavía pueden captar en el segmento bajo.

    Es el término independiente de R5. (plan §7.1)

        (tope - share_DC - share_AG) x TAM_bajo
        (0,65 -   0,35   -   0,18  ) x 21.500.000 = 2.580.000
    """
    tope = params["reglas"]["R5_tope_gama_baja"]
    ocupado = sum(params["productos"][c]["share"]["bajo"] for c in ("DC", "AG"))
    return (tope - ocupado) * params["mercado"]["bajo"]["tam"]


def share_ocupado(params):
    """Participación de Pastarazzi en cada segmento, antes de la campaña.

    Bajo el supuesto S2 (el cliente vuelca todo su gasto en pastas en una sola
    marca), la participación en facturación equivale a la participación en clientes,
    y por eso se puede sumar la columna de la Fig. 2.
    """
    return {
        seg: sum(prod["share"][seg] for prod in params["productos"].values())
        for seg in params["mercado"]
    }


def cupo_por_segmento(params):
    """Clientes que todavía quedan por captar en cada segmento.

    Es el término independiente de R10, la restricción de saturación física del
    mercado. No sale del enunciado: se agrega porque sin ella el modelo capta más
    clientes de los que el segmento tiene (ver docs/procedimiento.md §2).

        (tope - share ocupado) x TAM
    """
    tope = params["reglas"]["R10_tope_saturacion"]
    ocupado = share_ocupado(params)
    return {
        seg: (tope - ocupado[seg]) * datos_seg["tam"]
        for seg, datos_seg in params["mercado"].items()
    }


def mercado_total(params):
    """Mercado total de pastas en $MM/año. Denominador del market share."""
    return sum(mercado_por_segmento(params).values())
