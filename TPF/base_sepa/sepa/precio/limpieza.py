"""
Precios anormales: se descartan observaciones, nunca se corrige un precio.

Para cada producto la referencia es la mediana de las medianas de cada cadena
(cada cadena vota una vez: una cadena grande que cargó mal el precio en todas
sus sucursales, el pack de 6 como si fuera la unidad, no mueve la referencia).
Cada precio de sucursal se compara con la referencia en escala logarítmica
(x2 y ÷2 quedan a la misma distancia):

  - hasta x2 / ÷2: queda siempre (estaciones de servicio, cadenas de descuento);
  - más de x3 / ÷3: se descarta siempre;
  - en el medio: queda si es coherente con la dispersión normal del producto
    (3,5 desvíos robustos: MAD x 1,4826).

Con dos cadenas que no coinciden no hay mayoría: arbitra el precio posible
para el producto según su subcategoría (_arbitrar_dos_cadenas).

Un producto que vende una sola cadena no tiene con quién compararse: para eso
están sus "gemelos" (ratio_gemelos), los productos casi iguales con precio de
consenso. Así aparecen los precios desactualizados (una cadena que sigue
publicando precios de hace años de códigos viejos: una mayonesa a $156 el
litro).

Los umbrales están en config.py.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from sepa import config as cfg
from sepa.producto.similitud import limpiar


def _arbitrar_dos_cadenas(mediana_cadena: pd.Series, rango: pd.DataFrame) -> pd.Series:
    """
    Con dos cadenas, la mediana de sus medianas es el punto medio y favorece siempre a la más cara: si una publica
    el precio de una caja de six-packs como el de uno, se descartaría el precio correcto de la otra. Cuando las dos
    difieren en más de TOLERANCIA_MAXIMA y solo una tiene un precio posible para el producto (rango: minimo y
    maximo por producto, de su subcategoría), la referencia es esa. Devuelve la referencia de esos productos.
    """
    mc = mediana_cadena.rename("precio").reset_index()
    mc = mc[mc.groupby("producto")["comercio"].transform("size").eq(2)]
    mc["dentro"] = (mc["precio"] >= mc["producto"].map(rango["minimo"])) & \
        (mc["precio"] <= mc["producto"].map(rango["maximo"]))
    g = mc.groupby("producto")
    dispares = np.log(g["precio"].transform("max") / g["precio"].transform("min")) > cfg.TOLERANCIA_MAXIMA
    unica = g["dentro"].transform("sum").eq(1)
    return mc[dispares & unica & mc["dentro"]].set_index("producto")["precio"]


def marcar_anormales(obs: pd.DataFrame, rango: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    obs: producto, tienda, comercio, precio. rango (opcional, índice producto): minimo y maximo de un precio
    posible para el producto, que arbitra cuando hay dos cadenas que no coinciden. Devuelve obs con referencia,
    ratio y motivo ('' si el precio vale; fuera_de_rango, muy_alto o muy_bajo si se descarta).
    """
    obs = obs.copy()
    fuera = (obs["precio"] < cfg.PRECIO_MINIMO) | (obs["precio"] > cfg.PRECIO_MAXIMO)
    validos = obs[~fuera]
    mediana_cadena = validos.groupby(["producto", "comercio"], sort=False)["precio"].median()
    referencia = mediana_cadena.groupby(level="producto").median()
    if rango is not None:
        arbitrada = _arbitrar_dos_cadenas(mediana_cadena, rango)
        referencia.loc[arbitrada.index] = arbitrada
    obs["referencia"] = obs["producto"].map(referencia)
    log_ratio = np.log(obs["precio"] / obs["referencia"])
    centro = log_ratio.groupby(obs["producto"]).transform("median")
    mad = (log_ratio - centro).abs().groupby(obs["producto"]).transform("median")
    tolerancia = (cfg.Z_ROBUSTO * 1.4826 * mad).clip(lower=cfg.TOLERANCIA_SIEMPRE, upper=cfg.TOLERANCIA_MAXIMA)
    anormal = log_ratio.abs() > tolerancia
    obs["ratio"] = np.exp(log_ratio).round(3)
    obs["motivo"] = np.select([fuera, anormal & (log_ratio > 0), anormal], ["fuera_de_rango", "muy_alto", "muy_bajo"],
                              "")
    return obs


def _mediana_ponderada(valores: np.ndarray, pesos: np.ndarray) -> float:
    orden = np.argsort(valores)
    acumulado = np.cumsum(pesos[orden])
    return float(valores[orden][np.searchsorted(acumulado, acumulado[-1] / 2)])


def ratio_gemelos(productos: pd.DataFrame) -> pd.Series:
    """
    Precio normalizado de cada producto sobre el de sus "gemelos": hasta K_GEMELOS productos de la misma
    subcategoría con la descripción más parecida (sin tamaños; similitud >= SIMILITUD_GEMELO), contenido parecido
    (hasta CONTENIDO_GEMELO veces) y precio de consenso (los venden al menos dos cadenas); la referencia es la
    mediana de sus precios ponderada por tiendas.

    productos (índice: producto): descripcion, alimento_id, cantidad_normalizada, precio_normalizado (la mediana
    del producto), tiendas, cadenas (frozenset de comercios), estimado (peso por unidad típico: no se evalúa ni
    sirve de referencia) y plausible (su precio está dentro de lo habitual de su subcategoría: solo esos sirven de
    referencia; un precio viejo que publican dos cadenas no es un consenso).

    Solo se evalúa lo que vende una sola cadena en pocas tiendas (MAX_TIENDAS_GEMELOS): lo que venden varias ya se
    comparó entre ellas en marcar_anormales, y una cadena grande mantiene al día lo que publica en cientos de
    sucursales. NaN si no se evalúa o no tiene gemelos.
    """
    out = pd.Series(np.nan, index=productos.index)
    productos = productos[~productos["estimado"]]
    for _, g in productos.groupby("alimento_id"):
        if len(g) < 2:
            continue
        m = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, dtype=np.float32) \
            .fit_transform([limpiar(d) for d in g["descripcion"]])
        sim = (m @ m.T).toarray()
        np.fill_diagonal(sim, 0)
        contenido = g["cantidad_normalizada"].to_numpy(dtype=np.float32)
        razon = contenido[:, None] / contenido[None, :]
        precio, tiendas = g["precio_normalizado"].to_numpy(dtype=float), g["tiendas"].to_numpy(dtype=float)
        n_cadenas = g["cadenas"].map(len).to_numpy()
        evaluar = (n_cadenas == 1) & (tiendas <= cfg.MAX_TIENDAS_GEMELOS)
        referente = (n_cadenas >= 2) & g["plausible"].to_numpy(dtype=bool)
        gemelo = (sim >= cfg.SIMILITUD_GEMELO) & (razon <= cfg.CONTENIDO_GEMELO) & \
            (razon >= 1 / cfg.CONTENIDO_GEMELO) & evaluar[:, None] & referente[None, :]
        for i in np.flatnonzero(gemelo.any(axis=1)):
            candidatos = np.flatnonzero(gemelo[i])
            elegidos = candidatos[np.argsort(-sim[i, candidatos])[:cfg.K_GEMELOS]]
            out.loc[g.index[i]] = precio[i] / _mediana_ponderada(precio[elegidos], tiendas[elegidos])
    return out
