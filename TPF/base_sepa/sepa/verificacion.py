"""
Verificación final: reglas que las tres tablas tienen que cumplir siempre.

Cada control cuenta las filas que lo violan. Los críticos (claves, integridad
referencial, nutrientes imposibles, precios no positivos) detienen la corrida:
una tabla que los viola "rompe todo" aguas abajo. El resto se informa en
salida/calidad/verificacion.md.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from sepa import config as cfg
from sepa.producto.nutrientes import NUTRIENTES

logger = logging.getLogger("sepa.verificacion")

TRIESTADO = {"si", "no", "desconocido"}
ALERGENOS = ["gluten", "leche", "huevo", "mani", "frutos_secos", "soja", "pescado", "mariscos", "sesamo"]
# Genéricos cuya energía no cierra con Atwater general por su composición (USDA usa factores específicos o casi
# todo es mineral): polvo de hornear, cacao amargo, especias, sal, caldos, edulcorantes, té, café, jugos en polvo
# (sus carbohidratos por diferencia incluyen los ácidos orgánicos) y golosinas sin azúcar (polialcoholes, ~2,4 kcal/g).
SIN_ATWATER = {"levadura_polvo", "cacao_amargo", "especias", "sal", "sopa_caldo", "edulcorante", "edulcorante_liquido",
               "te", "cafe", "yerba", "gelatina", "gelatina_light", "salsas_varias", "vinagre", "aceto_balsamico",
               "jugo_polvo", "golosinas_sin_azucar"}


class Fallo(RuntimeError):
    pass


def _control(resultados: list, nombre: str, mascara: pd.Series | np.ndarray | int, critico: bool = False,
             ejemplos: pd.Series | None = None) -> None:
    n = int(mascara if isinstance(mascara, (int, np.integer)) else np.asarray(mascara).sum())
    muestra = ""
    if n and ejemplos is not None:
        muestra = ", ".join(map(str, ejemplos[np.asarray(mascara)].head(5).tolist()))
    resultados.append({"control": nombre, "filas_que_fallan": n, "critico": critico, "ejemplos": muestra})


def verificar(dim_producto: pd.DataFrame, dim_tienda: pd.DataFrame, fact: pd.DataFrame) -> pd.DataFrame:
    r: list = []
    p, t, f = dim_producto, dim_tienda, fact
    ids = p["id_producto"]

    # --- dim_producto
    _control(r, "producto: id_producto único y no vacío", ids.isna() | ids.duplicated(), True, ids)
    for c in ("nombre", "categoria", "subcategoria", "grupo_alimentario", "forma_venta", "unidad_normalizada"):
        _control(r, f"producto: {c} completo", p[c].isna() | p[c].astype(str).str.strip().eq(""), True, ids)
    _control(r, "producto: unidad_normalizada en kg / l / unidad", ~p["unidad_normalizada"].isin(["kg", "l", "unidad"]),
             True, ids)
    _control(r, "producto: cantidad_normalizada > 0", ~(p["cantidad_normalizada"] > 0), True, ids)
    _control(r, "producto: gramos_envase > 0", ~(p["gramos_envase"] > 0), True, ids)
    _control(r, "producto: parte_comestible entre 0 y 1", ~p["parte_comestible"].between(0.01, 1), True, ids)
    n = p[NUTRIENTES]
    _control(r, "nutrientes: sin vacíos", n.isna().any(axis=1), True, ids)
    _control(r, "nutrientes: sin negativos", (n < 0).any(axis=1), True, ids)
    _control(r, "nutrientes: energía <= 950 kcal", n["energia_kcal"] > cfg.MAX_KCAL_100, True, ids)
    macros = n["proteinas_g"] + n["carbohidratos_g"] + n["grasas_totales_g"] + n["fibra_g"] + n["alcohol_g"]
    _control(r, "nutrientes: proteínas + carbohidratos + grasas + fibra + alcohol <= 105 g", macros > 105, True, ids)
    _control(r, "nutrientes: saturadas <= grasas totales", n["grasas_saturadas_g"] > n["grasas_totales_g"] + 0.01,
             True, ids)
    fraccion = n["grasas_saturadas_g"] + n["grasas_monoinsaturadas_g"] + n["grasas_poliinsaturadas_g"] + \
        n["grasas_trans_g"]
    _control(r, "nutrientes: saturadas + mono + poli + trans <= grasas totales (+5 %)",
             fraccion > n["grasas_totales_g"] * 1.05 + 0.1, True, ids)
    _control(r, "nutrientes: azúcares <= carbohidratos", n["azucares_g"] > n["carbohidratos_g"] + 0.01, True, ids)
    _control(r, "nutrientes: sodio <= 40.000 mg", n["sodio_mg"] > cfg.SODIO_MAXIMO_MG, True, ids)
    _control(r, "nutrientes: agua + sólidos <= 105 g", n["agua_g"] + macros > 105, True, ids)
    # Fibra a 2 kcal/g (UE) o sin contar (Mercosur): vale cualquiera de las dos convenciones.
    atwater = 4 * n["proteinas_g"] + 4 * n["carbohidratos_g"] + 9 * n["grasas_totales_g"] + 7 * n["alcohol_g"]
    dif = np.minimum((n["energia_kcal"] - atwater).abs(), (n["energia_kcal"] - atwater - 2 * n["fibra_g"]).abs())
    no_cierra = (dif > 25) & (dif > 0.25 * n["energia_kcal"].clip(lower=1)) & ~p["alimento_id"].isin(SIN_ATWATER)
    _control(r, "nutrientes: energía coherente con los macronutrientes (Atwater, ±25 %)", no_cierra, False, ids)
    for a in ALERGENOS:
        _control(r, f"composición: contiene_{a} en si/no/desconocido", ~p[f"contiene_{a}"].isin(TRIESTADO), True, ids)
    for c in ("apto_vegetariano", "apto_vegano", "sin_tacc", "sin_lactosa", "azucar_agregada"):
        _control(r, f"composición: {c} en si/no/desconocido", ~p[c].isin(TRIESTADO), True, ids)
    _control(r, "composición: vegano implica vegetariano",
             p["apto_vegano"].eq("si") & ~p["apto_vegetariano"].eq("si"), True, ids)
    animal = p[["contiene_leche", "contiene_huevo", "contiene_pescado", "contiene_mariscos"]].eq("si").any(axis=1)
    _control(r, "composición: con leche, huevo, pescado o mariscos no es vegano", animal & p["apto_vegano"].eq("si"),
             True, ids)
    _control(r, "composición: con gluten no es sin TACC", p["contiene_gluten"].eq("si") & p["sin_tacc"].eq("si"),
             True, ids)

    # --- dim_tienda
    tid = t["id_tienda"]
    _control(r, "tienda: id_tienda único y no vacío", tid.isna() | tid.duplicated(), True, tid)
    ubicada = t["lat"].notna()
    fuera = ubicada & ~(t["lat"].between(*cfg.LAT_ARGENTINA) & t["lon"].between(*cfg.LON_ARGENTINA))
    _control(r, "tienda: coordenada dentro de la Argentina", fuera, True, tid)
    _control(r, "tienda: ubicada tiene provincia y departamento", ubicada & (t["provincia"].isna() |
             t["departamento"].isna()), False, tid)
    _control(r, "tienda: sin ubicación (sin ficha de sucursal en SEPA)", ~ubicada & ~t["es_web"], False, tid)
    _control(r, "tienda: ubicación dudosa (se conserva la de SEPA)", t["ubicacion_precision"].eq("dudosa"), False, tid)

    # --- fact_precio
    _control(r, "fact: id_producto existe en dim_producto", ~f["id_producto"].isin(ids), True, f["id_producto"])
    _control(r, "fact: id_tienda existe en dim_tienda", ~f["id_tienda"].isin(tid), True, f["id_tienda"])
    _control(r, "fact: un precio por producto y tienda", f.duplicated(["id_producto", "id_tienda"]), True)
    _control(r, "fact: precio > 0", ~(f["precio"] > 0), True)
    _control(r, "fact: precio_normalizado > 0", ~(f["precio_normalizado"] > 0), True)
    _control(r, "fact: precio_100g > 0", ~(f["precio_100g"] > 0), True)
    _control(r, "fact: promoción menor al precio de lista", f["precio_promocion"].notna() &
             ~(f["precio_promocion"] < f["precio"]), True)
    sin_precio = ~ids.isin(f["id_producto"].unique())
    _control(r, "producto: tiene al menos un precio en fact_precio", sin_precio, True, ids)
    sin_hechos = ~tid.isin(f["id_tienda"].unique())
    _control(r, "tienda: tiene al menos un precio en fact_precio", sin_hechos, False, tid)

    res = pd.DataFrame(r)
    criticos = res[res["critico"] & res["filas_que_fallan"].gt(0)]
    for row in res.itertuples():
        nivel = logging.ERROR if row.critico and row.filas_que_fallan else (
            logging.WARNING if row.filas_que_fallan else logging.DEBUG)
        logger.log(nivel, "%-80s %8d %s", row.control, row.filas_que_fallan, row.ejemplos)
    if len(criticos):
        raise Fallo("Verificación: controles críticos que fallan:\n" + criticos.to_string(index=False))
    logger.info("Verificación: %d controles, ningún crítico falla", len(res))
    return res
