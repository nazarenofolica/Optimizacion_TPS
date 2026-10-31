"""
fact_precio: una fila por producto y tienda con el precio publicado ese día,
limpio y llevado a la misma unidad dentro de cada subcategoría.

  precio                 precio de lista publicado (ARS) por la presentación
  precio_promocion       precio unitario de la promoción de alcance general vigente (si hay)
  cantidad, unidad       la presentación que compra ese precio: 500 g, 1,5 l, 12 unidades o, a granel, 1 kg
  precio_normalizado     precio por kg, por litro o por unidad (huevos), según la subcategoría: así "1 kg de
                         banana a $x" y "500 g de banana a $y" quedan comparables
  unidad_normalizada     kg, l o unidad
  precio_100g            precio cada 100 g tal como se compra (líquidos con su densidad): el que se combina con
                         los nutrientes de dim_producto (que son cada 100 g comestibles: dividir por
                         parte_comestible para el precio de la parte comestible)

Antes se descartan los precios anormales (limpieza.py) y, a nivel producto, los productos cuyo precio
normalizado no tiene sentido frente al resto de su subcategoría o frente a sus gemelos de otras cadenas: un
contenido mal cargado (un pack tomado como unidad, gramos por kilos) o un precio desactualizado.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from sepa import config as cfg
from sepa.fuentes.sepa import DatosSEPA
from sepa.precio import limpieza
from sepa.producto.dimension import COLUMNAS_PRESENTACION

logger = logging.getLogger("sepa.precio")


def armar(datos: DatosSEPA, precios: pd.DataFrame, dim_producto: pd.DataFrame, dim_tienda: pd.DataFrame
          ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """
    precios: producto, tienda, precio, precio_promocion (los del ZIP). Devuelve (fact, precios descartados,
    productos excluidos por precio implausible, presentaciones corregidas por precio (índice: producto; para
    actualizar dim_producto), estadísticas).
    """
    prod = dim_producto.set_index("producto")
    tiendas = datos.tiendas[datos.tiendas["id_tienda"].isin(dim_tienda["id_tienda"])].set_index("tienda")
    obs = precios[precios["producto"].isin(prod.index) & precios["tienda"].isin(tiendas.index)]
    obs = obs.assign(comercio=obs["tienda"].map(tiendas["id_comercio"]).astype(np.int16))
    stats = {"precios_de_productos_y_tiendas": len(obs)}

    # Precio posible de cada producto según su subcategoría (percentiles de todos sus precios por kilo, litro o
    # unidad, con un margen de RATIO_DISPUTA), para arbitrar entre dos cadenas que no coinciden.
    por_kilo = (obs["precio"] / obs["producto"].map(prod["cantidad_normalizada"])).groupby(
        obs["producto"].map(prod["alimento_id"]))
    p10 = prod["alimento_id"].map(por_kilo.quantile(cfg.PERCENTIL_SUBCATEGORIA_BAJO))
    p90 = prod["alimento_id"].map(por_kilo.quantile(cfg.PERCENTIL_SUBCATEGORIA_ALTO))
    rango = pd.DataFrame({"minimo": p10 / cfg.RATIO_DISPUTA * prod["cantidad_normalizada"],
                          "maximo": p90 * cfg.RATIO_DISPUTA * prod["cantidad_normalizada"]})
    obs = limpieza.marcar_anormales(obs, rango)
    descartes = obs[obs["motivo"].ne("")]
    obs = obs[obs["motivo"].eq("")].drop(columns=["referencia", "ratio", "motivo"])
    stats["precios_descartados"] = descartes["motivo"].value_counts().to_dict()

    def normalizar() -> pd.DataFrame:
        return obs.assign(precio_normalizado=obs["precio"] / obs["producto"].map(prod["cantidad_normalizada"]),
                          precio_100g=obs["precio"] / obs["producto"].map(prod["gramos_envase"]) * 100)

    def rango_subcategoria() -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        """Mediana de cada producto, su subcategoría y los percentiles de la subcategoría (todos sus precios)."""
        mediana = obs.groupby("producto")["precio_normalizado"].median()
        sub = prod["alimento_id"].reindex(mediana.index)
        por_sub = obs.groupby(obs["producto"].map(prod["alimento_id"]))["precio_normalizado"]
        return (mediana, sub, sub.map(por_sub.quantile(cfg.PERCENTIL_SUBCATEGORIA_BAJO)),
                sub.map(por_sub.quantile(cfg.PERCENTIL_SUBCATEGORIA_ALTO)))

    obs = normalizar()
    # Contenido en disputa: cuando las cadenas informan tamaños distintos para el mismo producto (5 g y 50 g de
    # una caja de cápsulas), gana el que deja el precio por kilo dentro de lo habitual de su subcategoría.
    mediana, sub, p10, p90 = rango_subcategoria()
    alt = prod["cantidad_normalizada_alt"].reindex(mediana.index)
    mediana_alt = mediana * prod["cantidad_normalizada"].reindex(mediana.index) / alt
    misma_unidad = prod["unidad_contenido_alt"].reindex(mediana.index).eq(prod["unidad_contenido"].reindex(mediana.index))
    raro = (mediana < p10 / cfg.RATIO_DISPUTA) | (mediana > p90 * cfg.RATIO_DISPUTA)
    cambiar = (raro & misma_unidad & (mediana_alt >= p10) & (mediana_alt <= p90)).fillna(False)
    cambiados = cambiar.index[cambiar]
    prod = prod.copy()
    for col in COLUMNAS_PRESENTACION:
        prod.loc[cambiados, col] = prod.loc[cambiados, f"{col}_alt"]
    prod.loc[cambiados, "contenido_fuente"] = "precio (contenido en disputa entre cadenas)"
    correcciones = prod.loc[cambiados, COLUMNAS_PRESENTACION + ["contenido_fuente"]]
    stats["contenidos_corregidos_por_precio"] = len(cambiados)
    obs = normalizar()

    # Precio normalizado mediano de cada producto frente a la distribución de su subcategoría (percentiles de
    # todos sus precios: pesa lo que se vende en más tiendas) y frente a sus gemelos (limpieza.ratio_gemelos).
    mediana, sub, p10, p90 = rango_subcategoria()
    tiendas_prod = obs.groupby("producto").size().reindex(mediana.index)
    r = limpieza.ratio_gemelos(pd.DataFrame({
        "descripcion": prod["descripcion"].reindex(mediana.index), "alimento_id": sub,
        "cantidad_normalizada": prod["cantidad_normalizada"].reindex(mediana.index), "precio_normalizado": mediana,
        "tiendas": tiendas_prod,
        "estimado": prod["base_normalizacion"].reindex(mediana.index).eq("peso_unidad_estimado"),
        "plausible": (mediana >= p10 / cfg.RATIO_DISPUTA) & (mediana <= p90 * cfg.RATIO_DISPUTA),
        "cadenas": obs.groupby("producto")["comercio"].agg(frozenset).reindex(mediana.index)}))
    # Muy caro por kilo pero con un precio de envase también fuera de lo común y en muchas góndolas: un producto de
    # lujo (champagne, jamón ibérico), no un contenido mal cargado, que deja el precio del envase en lo normal y
    # solo dispara el precio por kilo.
    envase = obs.groupby("producto")["precio"].median()
    envase_p90 = sub.map(obs.groupby(obs["producto"].map(prod["alimento_id"]))["precio"].quantile(
        cfg.PERCENTIL_SUBCATEGORIA_ALTO))
    lujo = (envase > envase_p90 * cfg.RATIO_ENVASE_LUJO) & (tiendas_prod >= cfg.MIN_TIENDAS_LUJO)
    motivos = [
        ((mediana > p90 * cfg.RATIO_SUBCATEGORIA_ARRIBA) & ~lujo,
         "precio por unidad muy por encima de su subcategoría (contenido dudoso)"),
        (mediana < p10 / cfg.RATIO_SUBCATEGORIA_ABAJO,
         "precio por unidad muy por debajo de su subcategoría (contenido dudoso o precio que no es de hoy)"),
        # Frente a los gemelos solo cuenta si además está en el extremo de su subcategoría: dos vinos Viognier de
        # bodegas distintas pueden costar 6 veces uno que otro.
        ((r > cfg.RATIO_GEMELOS_ARRIBA) & (mediana > p90),
         "precio muy por encima del de productos casi iguales (contenido dudoso)"),
        ((r < 1 / cfg.RATIO_GEMELOS_ABAJO) & (mediana < p10),
         "precio muy por debajo del de productos casi iguales (precio desactualizado o contenido dudoso)"),
    ]
    stats["productos_de_lujo_tolerados"] = int((lujo & (mediana > p90 * cfg.RATIO_SUBCATEGORIA_ARRIBA)).sum())
    motivo = pd.Series(np.select([m.fillna(False).to_numpy() for m, _ in motivos], [t for _, t in motivos], ""),
                       index=mediana.index)
    implausible = motivo.ne("")
    ratio_sub = mediana / sub.map(obs.groupby(obs["producto"].map(prod["alimento_id"]))["precio_normalizado"].median())
    excluidos = pd.DataFrame({"producto": mediana.index[implausible],
                              "ratio_subcategoria": ratio_sub[implausible].round(3).to_numpy(),
                              "ratio_gemelos": r[implausible].round(3).to_numpy(),
                              "motivo_exclusion": motivo[implausible].to_numpy()})
    obs = obs[~obs["producto"].isin(excluidos["producto"])]
    stats["productos_excluidos_por_precio"] = len(excluidos)

    fact = pd.DataFrame({
        "fecha": pd.Timestamp(datos.fecha),
        "id_producto": obs["producto"].map(prod["id_producto"]).to_numpy(),
        "id_tienda": obs["tienda"].map(tiendas["id_tienda"]).to_numpy(),
        "precio": obs["precio"].round(2).to_numpy(),
        "precio_promocion": obs["precio_promocion"].round(2).to_numpy(),
        "cantidad": obs["producto"].map(prod["cantidad_publicada"]).to_numpy(),
        "unidad": obs["producto"].map(prod["unidad_publicada"]).to_numpy(),
        "precio_normalizado": obs["precio_normalizado"].round(2).to_numpy(),
        "unidad_normalizada": obs["producto"].map(prod["unidad_normalizada"]).to_numpy(),
        "precio_100g": obs["precio_100g"].round(2).to_numpy(),
    })
    for c in ("id_producto", "id_tienda", "unidad", "unidad_normalizada"):
        fact[c] = fact[c].astype("category")
    fact = fact.sort_values(["id_producto", "id_tienda"], ignore_index=True)
    stats["filas"] = len(fact)
    stats["con_promocion"] = int(fact["precio_promocion"].notna().sum())

    descartes = descartes.assign(id_producto=descartes["producto"].map(prod["id_producto"]),
                                 id_tienda=descartes["tienda"].map(tiendas["id_tienda"]))
    descartes = descartes[["id_producto", "id_tienda", "precio", "referencia", "ratio", "motivo"]]
    return fact, descartes.reset_index(drop=True), excluidos, correcciones, stats
