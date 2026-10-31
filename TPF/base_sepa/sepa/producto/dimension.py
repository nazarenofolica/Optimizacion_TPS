"""
dim_producto: una fila por producto comestible, sin precio.

Pasos (cada uno en su módulo):
  1. identificacion  descripción, marca y nombre legible
  2. contenido       gramos o mililitros, unidades, granel
  3. categorias      categoría de góndola (exacta o predicha)
  4. clasificacion   alimento genérico: categoría, subcategoría y grupo alimentario
  5. presentación    forma de venta y factor para llevar el precio publicado a la unidad
                     de su subcategoría (kg, l o unidad) y a 100 g
  6. nutrientes      33 nutrientes cada 100 g comestibles, sin vacíos
  7. composicion     alérgenos, aptitudes, procesamiento; sellos de advertencia

Un producto entra solo si es comida, tiene una clasificación sin conflictos, un
contenido conocido (o una unidad con peso típico) y un rótulo, si lo tiene,
compatible con su alimento genérico. Lo que no entra queda en
salida/calidad/productos_excluidos.csv con el motivo.
"""

from __future__ import annotations

import gc
import logging

import numpy as np
import pandas as pd

from sepa.fuentes.sepa import DatosSEPA
from sepa.producto import categorias, clasificacion, composicion, contenido, identificacion, nutrientes

logger = logging.getLogger("sepa.producto")

TIPO_CODIGO = {True: "EAN", False: "Interno de cadena"}
COLUMNAS_PRESENTACION = ["contenido", "unidad_contenido", "cantidad_publicada", "unidad_publicada", "gramos_envase",
                         "cantidad_normalizada", "base_normalizacion"]


def presentacion(p: pd.DataFrame, cat: pd.DataFrame) -> pd.DataFrame:
    """
    Forma de venta y factores de normalización de cada producto (p: alimento_id, contenido, unidad_contenido,
    unidades, granel):

      gramos_envase         gramos que compra el precio publicado (líquidos con su densidad; por unidad, con el
                            peso típico de la unidad);
      unidad_normalizada    la de su subcategoría: kg, l o unidad (huevos);
      cantidad_normalizada  cuántos kg, l o unidades compra el precio publicado: precio / cantidad_normalizada
                            es el precio por kg, l o unidad;
      base_normalizacion    "directa", "densidad" (g <-> ml) o "peso_unidad_estimado" (aproximada).
    """
    c = cat.set_index("id")
    dens = p["alimento_id"].map(c["densidad_g_ml"]).astype(float)
    peso_u = p["alimento_id"].map(c["peso_unidad_g"]).astype(float)
    destino = p["alimento_id"].map(c["unidad_precio"])
    g = p["unidad_contenido"].eq("g") & p["contenido"].gt(0)
    ml = p["unidad_contenido"].eq("ml") & p["contenido"].gt(0)
    por_unidad = ~g & ~ml & p["unidades"].gt(0)

    out = pd.DataFrame(index=p.index)
    out["forma_venta"] = np.select([p["granel"], g | ml, por_unidad],
                                   ["Granel (precio por kg)", "Envase", "Por unidad"], "")
    # Lo que compra el precio publicado, en las unidades en que se publica.
    out["cantidad_publicada"] = np.select([p["granel"], g | ml, por_unidad], [1.0, p["contenido"], p["unidades"]],
                                          np.nan)
    out["unidad_publicada"] = np.select([p["granel"], g, ml, por_unidad], ["kg", "g", "ml", "unidad"], "")
    gramos = np.select([g, ml, por_unidad], [p["contenido"], p["contenido"] * dens, p["unidades"] * peso_u], np.nan)
    out["gramos_envase"] = pd.Series(gramos, index=p.index).round(3)
    kg = destino.eq("kg")
    litros = destino.eq("l")
    unidad = destino.eq("unidad")
    cantidad = np.select(
        [kg & (g | ml | por_unidad), litros & ml, litros & (g | por_unidad), unidad & p["unidades"].gt(0),
         unidad & (g | ml)],
        [out["gramos_envase"] / 1000, p["contenido"] / 1000, out["gramos_envase"] / dens / 1000, p["unidades"],
         out["gramos_envase"] / peso_u],
        np.nan)
    out["unidad_normalizada"] = destino
    out["cantidad_normalizada"] = pd.Series(cantidad, index=p.index).round(6)
    out["base_normalizacion"] = np.select(
        [por_unidad & ~unidad, unidad & ~p["unidades"].gt(0), (kg & ml) | (litros & g)],
        ["peso_unidad_estimado", "peso_unidad_estimado", "densidad"], "directa")
    out.loc[out["cantidad_normalizada"].isna(), "base_normalizacion"] = ""
    return out


def armar(datos: DatosSEPA, off: pd.DataFrame, web: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Devuelve (dim_producto con columnas internas, productos excluidos con su motivo, estadísticas)."""
    stats: dict = {}
    cat = clasificacion.cargar_catalogo()
    p = datos.productos.copy()
    p["es_ean"] = ~p["clave_producto"].str.startswith("cadena")
    p = p.merge(identificacion.armar(datos.presentaciones), on="producto", how="left")
    internos = set(p.loc[~p["es_ean"], "producto"])
    p = p.merge(contenido.resolver(datos.presentaciones, internos), on="producto", how="left")
    stats["productos_sepa"] = len(p)

    logger.info("Categoría de góndola de %d productos...", len(p))
    p = p.merge(categorias.asignar(p), on="producto", how="left")
    gc.collect()
    clas = clasificacion.clasificar_con_categorias(p, cat, clasificacion.cargar_categorias())
    clas["alimento_id"], forma = clasificacion.corregir_forma(clas["alimento_id"], p["contenido"],
                                                              p["unidad_contenido"])
    clas["motivo_exclusion"] = clas["motivo_exclusion"].mask(forma.ne(""), forma)
    p = pd.concat([p, clas], axis=1)
    stats["clasificacion_origen"] = p["clasificacion_origen"].replace("", "sin clasificar").value_counts().to_dict()

    excluidos = [p.loc[p["motivo_exclusion"].ne(""), ["producto", "motivo_exclusion"]]]
    p = p[p["alimento_id"].notna()].reset_index(drop=True)
    c = cat.set_index("id")
    p["categoria"] = p["alimento_id"].map(c["rubro"])
    p["subcategoria"] = p["alimento_id"].map(c["alimento"])
    p["grupo_alimentario"] = p["alimento_id"].map(c["grupo_alimentario"])
    p = pd.concat([p, presentacion(p, cat)], axis=1)
    # La presentación según el contenido alternativo (otra cadena informa otro tamaño): la elige precio/hecho.py
    # si deja el precio por kilo dentro de lo habitual y el elegido no.
    con_alt = p["contenido_alternativo"].notna()
    alt = presentacion(p.assign(contenido=p["contenido_alternativo"], unidad_contenido=p["unidad_alternativa"],
                                granel=False), cat)
    alt = alt.assign(contenido=p["contenido_alternativo"], unidad_contenido=p["unidad_alternativa"]).where(con_alt)
    p = p.join(alt[COLUMNAS_PRESENTACION].add_suffix("_alt"))
    sin_contenido = p["cantidad_normalizada"].isna() | ~(p["cantidad_normalizada"] > 0)
    excluidos.append(p.loc[sin_contenido, ["producto"]].assign(
        motivo_exclusion="contenido desconocido (no se puede normalizar el precio)"))
    p = p[~sin_contenido].reset_index(drop=True)
    logger.info("Productos comestibles con contenido conocido: %d", len(p))

    nut, gen, st_nut = nutrientes.armar(p, cat, off, web, nutrientes.leer_rotulos_fotos(), nutrientes.leer_manual())
    stats["nutrientes"] = st_nut
    dudosa = nut["clasificacion_dudosa"].to_numpy()
    excluidos.append(p.loc[dudosa, ["producto"]].assign(
        motivo_exclusion="el rótulo no es compatible con su alimento genérico (clasificación o rótulo dudoso)"))
    columnas_nut = nutrientes.NUTRIENTES + ["fuente_nutrientes"]
    p = pd.concat([p, nut[columnas_nut].set_axis(p.index)], axis=1)[~dudosa].reset_index(drop=True)

    comp = composicion.armar(p, off, web)
    p = p.merge(comp, on="producto", how="left")
    liquido = p["unidad_contenido"].eq("ml")
    sel = nutrientes.sellos(p, p["categoria"], liquido, p["alimento_id"].map(c["densidad_g_ml"]),
                            envasado=p["es_ean"], azucar_agregada=p["azucar_agregada"],
                            para_preparar=p["alimento_id"].isin(nutrientes.PARA_PREPARAR))
    p = pd.concat([p, sel], axis=1)
    p["parte_comestible"] = p["alimento_id"].map(c["parte_comestible"])
    p["densidad_g_ml"] = p["alimento_id"].map(c["densidad_g_ml"]).where(liquido)
    p["porcion_g"] = p["alimento_id"].map(c["porcion"])
    p["id_producto"] = p["clave_producto"]
    p["tipo_codigo"] = p["es_ean"].map(TIPO_CODIGO)
    p["id_comercio_interno"] = p["clave_producto"].str.extract(r"^cadena(\d+)-", expand=False).astype("Int64")

    excl = pd.concat(excluidos, ignore_index=True).drop_duplicates("producto")
    stats["excluidos"] = excl["motivo_exclusion"].value_counts().to_dict()
    return p, excl, stats | {"genericos": gen}
