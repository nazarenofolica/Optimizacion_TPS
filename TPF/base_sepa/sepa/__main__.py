"""
SEPA 2.0: de un ZIP diario de SEPA a un modelo estrella listo para usar.

    python -m sepa                    # usa el ZIP de datos/entrada/
    python -m sepa --descargar        # baja antes el último ZIP minorista (y borra el anterior)
    python -m sepa --zip ruta.zip     # un ZIP puntual
    python -m sepa --actualizar-off   # vuelve a bajar el dump de Open Food Facts (~1,2 GB)
    python -m sepa --actualizar-web   # vuelve a recorrer los catálogos de Jumbo, Disco y Vea

Salidas en salida/: dim_producto, dim_tienda, fact_precio, calidad/ y LEEME.md.
"""

from __future__ import annotations

import argparse
import gc
import logging
import shutil
import sys
import time
from pathlib import Path

import pandas as pd

from sepa import config as cfg
from sepa import salida, verificacion
from sepa.fuentes import catalogos_web, openfoodfacts
from sepa.fuentes import sepa as fuente_sepa
from sepa.precio import hecho
from sepa.producto import dimension as dim_producto
from sepa.tienda import dimension as dim_tienda

logger = logging.getLogger("sepa")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m sepa", description=__doc__.split("\n\n")[0])
    p.add_argument("--zip", type=Path, help="ZIP de SEPA a usar (por defecto, el de datos/entrada/).")
    p.add_argument("--descargar", action="store_true", help="Bajar antes el último ZIP minorista de la API.")
    p.add_argument("--actualizar-off", action="store_true", help="Volver a bajar el dump de Open Food Facts.")
    p.add_argument("--actualizar-web", action="store_true", help="Volver a recorrer los catálogos de Cencosud.")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg.configurar_logging(args.verbose)
    inicio = time.time()
    ruta = fuente_sepa.descargar_ultimo() if args.descargar else (args.zip or fuente_sepa.zip_del_dia())

    logger.info("== 1/5 Lectura de %s", ruta.name)
    datos = fuente_sepa.leer_zip(ruta)
    logger.info("%d precios, %d productos, %d tiendas", len(datos.precios), len(datos.productos), len(datos.tiendas))
    datos.precios.to_parquet(cfg.RUTA_PRECIOS_DEL_DIA, index=False)
    n_precios, datos.precios = len(datos.precios), pd.DataFrame()      # libera ~350 MB hasta el paso 4
    gc.collect()

    logger.info("== 2/5 Tiendas")
    tiendas, st_tienda = dim_tienda.armar(datos)

    logger.info("== 3/5 Productos")
    eans = set(datos.productos.loc[~datos.productos["clave_producto"].str.startswith("cadena"), "clave_producto"])
    off = openfoodfacts.seleccion(eans, forzar=args.actualizar_off)
    if args.actualizar_web:
        for sitio in catalogos_web.SITIOS:
            catalogos_web.descargar(sitio, sorted(eans))
        catalogos_web.descargar_no_alimentos()
    web = catalogos_web.procesar()
    productos, excluidos, st_producto = dim_producto.armar(datos, off, web)
    genericos = st_producto.pop("genericos")
    validacion_similitud = st_producto["nutrientes"].pop("validacion_similitud")
    del off, web
    gc.collect()

    logger.info("== 4/5 Precios")
    precios = pd.read_parquet(cfg.RUTA_PRECIOS_DEL_DIA, filters=[("producto", "in", productos["producto"].tolist())])
    fact, descartes, excl_precio, correcciones, st_precio = hecho.armar(datos, precios, productos, tiendas)
    del precios
    cfg.RUTA_PRECIOS_DEL_DIA.unlink(missing_ok=True)
    st_precio["precios_leidos"] = n_precios
    excluidos = pd.concat([excluidos, excl_precio], ignore_index=True)
    productos = productos[productos["id_producto"].isin(fact["id_producto"].unique())].copy()
    corregido = productos["producto"].isin(correcciones.index)
    for col in correcciones.columns:
        productos.loc[corregido, col] = productos.loc[corregido, "producto"].map(correcciones[col])
    tiendas = tiendas[tiendas["id_tienda"].isin(fact["id_tienda"].unique())]

    logger.info("== 5/5 Verificación y salida")
    p, t = salida.tablas_finales(productos, tiendas)
    try:
        verif = verificacion.verificar(p, t, fact)
    except verificacion.Fallo:
        # salida/ queda como estaba; las tablas que no pasaron quedan para revisarlas.
        revisar = cfg.DIR_CACHE / "corrida_fallida"
        revisar.mkdir(parents=True, exist_ok=True)
        for nombre, tabla in (("dim_producto", p), ("dim_tienda", t), ("fact_precio", fact)):
            tabla.to_parquet(revisar / f"{nombre}.parquet", index=False)
        logger.error("Las tablas de esta corrida quedaron en %s para revisar", revisar)
        raise
    info = datos.productos.merge(datos.presentaciones.sort_values("veces", ascending=False)
                                 .drop_duplicates("producto")[["producto", "descripcion", "marca"]], on="producto")
    excluidos = info.merge(excluidos, on="producto").drop(columns="producto").rename(
        columns={"clave_producto": "id_producto"}).sort_values(["motivo_exclusion", "descripcion"])
    calidad = {
        "productos_excluidos": excluidos,
        "precios_descartados": descartes.sort_values(["id_producto", "precio"]),
        "tiendas_ubicacion": t[~t["ubicacion_fuente"].eq("sepa")],
        "nutrientes_genericos": genericos.reset_index(),
        "validacion_similitud": validacion_similitud,
        "lectura_comercios": datos.archivos,
    }
    stats = {"archivo": ruta.name, "minutos": (time.time() - inicio) / 60, "tienda": st_tienda,
             "producto": st_producto, "precio": st_precio}
    salida.escribir(p, t, fact, calidad, verif, stats)
    shutil.rmtree(cfg.DIR_CACHE / "corrida_fallida", ignore_errors=True)
    logger.info("Listo en %.1f min: %d productos, %d tiendas, %d precios", (time.time() - inicio) / 60, len(p),
                len(t), len(fact))
    return 0


if __name__ == "__main__":
    sys.exit(main())
