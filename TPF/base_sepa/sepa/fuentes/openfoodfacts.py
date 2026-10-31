"""
Open Food Facts (https://world.openfoodfacts.org): base abierta (licencia ODbL)
de productos envasados de todo el mundo, cruzable por código de barras.

Se baja el dump completo una vez (~1,2 GB, se reutiliza config.DIAS_VIGENCIA_OFF
días) y en una sola pasada se extraen, para los EAN de SEPA y todos los
argentinos (prefijo 779), la tabla nutricional, la composición (ingredientes,
alérgenos, trazas, etiquetas, aditivos, NOVA), la cantidad del envase y las
fotos del rótulo. La selección queda en cache (seleccion.parquet) hasta que
cambie el dump. La API por producto no sirve: ~100 consultas por minuto para
~75.000 EAN.

Los nutrientes quedan por 100 g (o 100 ml en líquidos, como los informa Open
Food Facts) en las unidades del nombre de cada columna (g, mg, ug). Open Food
Facts es colaborativa y tiene errores de carga: los controles se aplican en
sepa/producto/nutrientes.py.
"""

from __future__ import annotations

import csv
import gzip
import logging
import time
from pathlib import Path

import pandas as pd
import requests

from sepa import config as cfg

logger = logging.getLogger("sepa.fuentes.off")

META = {
    "code": "off_codigo", "product_name": "off_nombre", "brands_en": "off_marcas", "quantity": "off_cantidad",
    "product_quantity": "off_contenido", "serving_size": "off_porcion", "categories_en": "off_categorias",
    "main_category_en": "off_categoria_principal", "countries_en": "off_paises", "nutriscore_grade": "nutriscore",
    "nova_group": "nova", "no_nutrition_data": "off_sin_tabla", "data_quality_errors_tags": "off_errores_calidad",
    "completeness": "off_completitud", "last_modified_t": "off_modificado_t",
    "ingredients_text": "ingredientes", "allergens_tags": "alergenos_tags", "traces_tags": "trazas_tags",
    "labels_tags": "etiquetas_tags", "ingredients_analysis_tags": "analisis_ingredientes_tags",
    "additives_n": "aditivos_n", "additives_tags": "aditivos_tags",
    "image_nutrition_url": "foto_tabla", "image_ingredients_url": "foto_ingredientes",
}

# nombre en Open Food Facts -> (columna, factor desde gramos). Energía en kcal / kJ, alcohol en % vol.
NUTRIENTES = {
    "energy-kcal": ("energia_kcal", 1), "energy-kj": ("energia_kj", 1), "proteins": ("proteinas_g", 1),
    "carbohydrates": ("carbohidratos_g", 1), "sugars": ("azucares_g", 1), "added-sugars": ("azucares_agregados_g", 1),
    "fiber": ("fibra_g", 1), "fat": ("grasas_totales_g", 1), "saturated-fat": ("grasas_saturadas_g", 1),
    "monounsaturated-fat": ("grasas_monoinsaturadas_g", 1), "polyunsaturated-fat": ("grasas_poliinsaturadas_g", 1),
    "trans-fat": ("grasas_trans_g", 1), "cholesterol": ("colesterol_mg", 1e3), "salt": ("sal_g", 1),
    "sodium": ("sodio_mg", 1e3), "potassium": ("potasio_mg", 1e3), "calcium": ("calcio_mg", 1e3),
    "phosphorus": ("fosforo_mg", 1e3), "iron": ("hierro_mg", 1e3), "magnesium": ("magnesio_mg", 1e3),
    "zinc": ("zinc_mg", 1e3), "copper": ("cobre_mg", 1e3), "selenium": ("selenio_ug", 1e6),
    "vitamin-a": ("vitamina_a_ug", 1e6), "vitamin-d": ("vitamina_d_ug", 1e6), "vitamin-e": ("vitamina_e_mg", 1e3),
    "vitamin-k": ("vitamina_k_ug", 1e6), "vitamin-c": ("vitamina_c_mg", 1e3), "vitamin-b1": ("vitamina_b1_mg", 1e3),
    "vitamin-b2": ("vitamina_b2_mg", 1e3), "vitamin-pp": ("vitamina_b3_niacina_mg", 1e3),
    "vitamin-b6": ("vitamina_b6_mg", 1e3), "vitamin-b9": ("vitamina_b9_folato_ug", 1e6),
    "vitamin-b12": ("vitamina_b12_ug", 1e6), "alcohol": ("alcohol_pct_vol", 1), "water": ("agua_g", 1),
}
FILAS_POR_BLOQUE = 100_000
PREFIJOS_ARGENTINA = ("779", "778")


def asegurar_dump(forzar: bool = False) -> Path:
    ruta = cfg.RUTA_OFF_DUMP
    if ruta.exists() and not forzar:
        dias = (time.time() - ruta.stat().st_mtime) / 86400
        if dias <= cfg.DIAS_VIGENCIA_OFF:
            return ruta
        logger.info("Open Food Facts: el dump local tiene %.0f días, se vuelve a bajar", dias)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".gz.part")
    logger.info("Bajando el dump de Open Food Facts (~1,2 GB)...")
    with requests.get(cfg.URL_OFF_DUMP, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for bloque in r.iter_content(chunk_size=4 * 1024 * 1024):
                f.write(bloque)
    tmp.replace(ruta)
    return ruta


def seleccion(eans: set[str], forzar: bool = False) -> pd.DataFrame:
    """
    Una fila por EAN (13 dígitos) con metadatos, composición y nutrientes. Usa la selección guardada si es
    más nueva que el dump y cubre los EAN pedidos que pueden estar (se vuelve a leer con forzar).
    """
    dump = asegurar_dump(forzar)
    cache = cfg.RUTA_OFF_SELECCION
    if cache.exists() and not forzar and cache.stat().st_mtime > dump.stat().st_mtime:
        sel = pd.read_parquet(cache)
        consultados = set(sel.attrs.get("consultados", "").split(",")) if sel.attrs.get("consultados") else set()
        faltan = {e for e in eans if not e.startswith(PREFIJOS_ARGENTINA)} - consultados - set(sel["ean"])
        if len(faltan) <= 0.01 * len(eans):
            logger.info("Open Food Facts: selección guardada (%d EAN)", len(sel))
            return sel
        logger.info("Open Food Facts: %d EAN nuevos, se vuelve a leer el dump", len(faltan))
    sel = _leer_dump(dump, eans)
    sel.attrs["consultados"] = ",".join(sorted(e for e in eans if not e.startswith(PREFIJOS_ARGENTINA)))
    cache.parent.mkdir(parents=True, exist_ok=True)
    sel.to_parquet(cache, index=False)
    return sel


def _leer_dump(ruta: Path, eans: set[str]) -> pd.DataFrame:
    with gzip.open(ruta, "rt", encoding="utf-8", errors="replace") as f:
        encabezado = f.readline().rstrip("\n").split("\t")
    meta = [c for c in META if c in encabezado]
    nutr = [f"{n}_100g" for n in NUTRIENTES if f"{n}_100g" in encabezado]
    buscados = {e.lstrip("0") for e in eans}
    partes, leidas, inicio = [], 0, time.time()
    logger.info("Open Food Facts: leyendo el dump (una pasada, ~4 minutos)...")
    with gzip.open(ruta, "rt", encoding="utf-8", errors="replace") as f:
        lector = pd.read_csv(f, sep="\t", usecols=meta + nutr, dtype=str, chunksize=FILAS_POR_BLOQUE,
                             quoting=csv.QUOTE_NONE, on_bad_lines="skip", keep_default_na=False, na_values=[""])
        for bloque in lector:
            leidas += len(bloque)
            codigo = bloque["code"].str.replace(r"\D", "", regex=True).str.lstrip("0")
            sel = codigo.isin(buscados) | (codigo.str.len().eq(13) & codigo.str.startswith(PREFIJOS_ARGENTINA))
            if sel.any():
                partes.append(bloque[sel].assign(ean=codigo[sel].str.zfill(13)))
    off = pd.concat(partes, ignore_index=True)
    salida = pd.DataFrame({"ean": off["ean"]})
    for col, nuevo in META.items():
        if col in off:
            salida[nuevo] = off[col]
    columnas = []
    for n, (nombre, factor) in NUTRIENTES.items():
        col = f"{n}_100g"
        if col in off:
            salida[nombre] = (pd.to_numeric(off[col], errors="coerce") * factor).round(4)
            columnas.append(nombre)
    # Mismo EAN repetido: la ficha con más nutrientes y, a igualdad, la más nueva.
    salida["_n"] = salida[columnas].notna().sum(axis=1)
    salida["_t"] = pd.to_numeric(salida["off_modificado_t"], errors="coerce")
    salida = (salida.sort_values(["ean", "_n", "_t"], ascending=[True, False, False])
              .drop_duplicates("ean").drop(columns=["_n", "_t", "off_modificado_t"]).reset_index(drop=True))
    logger.info("Open Food Facts: %d filas leídas en %.0f s, %d EAN seleccionados", leidas,
                time.time() - inicio, len(salida))
    return salida
