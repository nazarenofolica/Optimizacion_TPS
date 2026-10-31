"""Lectura del ZIP de SEPA: códigos de barras, registros partidos, promociones, comercios desactualizados."""

from __future__ import annotations

import io
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from sepa.fuentes import sepa as fs

ENCABEZADO = ("id_comercio|id_bandera|id_sucursal|id_producto|productos_ean|productos_descripcion|"
              "productos_cantidad_presentacion|productos_unidad_medida_presentacion|productos_marca|"
              "productos_precio_lista|productos_precio_referencia|productos_cantidad_referencia|"
              "productos_unidad_medida_referencia|productos_precio_unitario_promo1|productos_leyenda_promo1|"
              "productos_precio_unitario_promo2|productos_leyenda_promo2")
COMERCIO = ("id_comercio|id_bandera|comercio_cuit|comercio_razon_social|comercio_bandera_nombre|comercio_bandera_url|"
            "comercio_ultima_actualizacion|comercio_version_sepa\n{c}|1|30|SA|Bandera|x|2026|1.0\n")
SUCURSALES = ("id_comercio|id_bandera|id_sucursal|sucursales_nombre|sucursales_tipo|sucursales_calle|sucursales_numero|"
              "sucursales_latitud|sucursales_longitud\n{c}|1|1|Centro|Supermercado|Necochea|445|-24.18\n|-65.30\n")


def _comercio(c: int, filas: list[str], actualizacion: str) -> bytes:
    productos = "﻿" + ENCABEZADO + "\n" + "\n".join(filas) + f"\n\nÚltima actualización: {actualizacion}\n"
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("productos.csv", productos)
        z.writestr("comercio.csv", COMERCIO.format(c=c))
        z.writestr("sucursales.csv", SUCURSALES.format(c=c))
    return b.getvalue()


def _zip(carpeta: Path) -> Path:
    filas = [
        "2|1|1|7790580660000|1|ARROZ LARGO FINO 1 KG|1|kg|GALLO|1000.00|1000|1|KG|800|DEL 20/10/2026 AL 25/10/2026||",
        "2|1|2|7790580660000|1|ARROZ LARGO FINO 1 KG|1|kg|GALLO|1100.00|1100|1|KG|900|DEL 01/10/2026 AL 05/10/2026||",
        "2|1|2|7790580660000|1|ARROZ LARGO FINO 1 KG|1|kg|GALLO|1100.00|1100|1|KG||||",   # repetido
        "2|1|1|2490110000000|1|BANANA X KG|1|kg||900.00|900|1|KG||||",                    # código de balanza
        "2|1|1|7790580660000|1|SIN PRECIO|1|kg|GALLO|||||||",
    ]
    ruta = carpeta / "sepa_viernes_2026-10-23.zip"
    with zipfile.ZipFile(ruta, "w") as z:
        z.writestr("2026-10-23/sepa_comercio-2.zip", _comercio(2, filas, "2026-10-23T04:00:00-03:00"))
        z.writestr("2026-10-23/sepa_comercio-47.zip", _comercio(47, ["47|1|1|7790580660000|1|ARROZ|1|kg|X|1|1|1|KG||||"],
                                                                  "2025-06-11T21:00:01-03:00"))   # archivo viejo
        z.writestr("2026-10-23/sepa_comercio-36.zip", b"")                                      # ZIP vacío
    return ruta


class TestCodigos(unittest.TestCase):
    def test_ean_global(self):
        casos = {"7790580660000": "7790580660000", "0000040084107": "0000040084107", "7790580660001": None,
                 "2490110000000": None, "0000000001816": None, "": None}
        for codigo, esperado in casos.items():
            with self.subTest(codigo=codigo):
                self.assertEqual(fs.ean_global(codigo), esperado)


class TestTablaChica(unittest.TestCase):
    def test_rearma_registros_partidos(self):
        # Un comercio parte la latitud, la longitud y los horarios con saltos de línea.
        crudo = ("﻿id_comercio|id_bandera|lat|lon|localidad\r\n6|1|-24.183838\r\n|-65.304235\r\n|Jujuy\r\n"
                 "6|1|-24.1|-65.3|Salta\r\n\r\nÚltima actualización: 2026-10-23T09:30:00-03:00\r\n").encode()
        tabla, actualizacion = fs.leer_tabla_chica(crudo)
        self.assertEqual(len(tabla), 2)
        self.assertEqual(tabla.loc[0, "lon"], "-65.304235")
        self.assertEqual(tabla.loc[0, "localidad"], "Jujuy")
        self.assertEqual(actualizacion, date(2026, 10, 23))


class TestLectura(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            cls.datos = fs.leer_zip(_zip(Path(tmp)))

    def test_fecha_y_comercios(self):
        d = self.datos
        self.assertEqual(d.fecha, date(2026, 10, 23))
        estados = dict(zip(d.archivos["archivo"], d.archivos["estado"]))
        self.assertEqual(estados["sepa_comercio-47.zip"], "desactualizado")
        self.assertEqual(estados["sepa_comercio-36.zip"], "ilegible")
        self.assertEqual(d.filas_sin_precio, 1)

    def test_claves_y_repetidos(self):
        d = self.datos
        claves = set(d.productos["clave_producto"])
        self.assertEqual(claves, {"7790580660000", "cadena2-2490110000000"})   # el 47 no deja rastros
        self.assertEqual(len(d.precios), 3)                                    # el repetido cuenta una vez
        self.assertEqual(set(d.tiendas["id_tienda"]), {"2-1-1", "2-1-2"})

    def test_promocion_solo_si_esta_vigente(self):
        d = self.datos
        arroz = d.productos.set_index("clave_producto").loc["7790580660000", "producto"]
        tienda = d.tiendas.set_index("id_tienda")["tienda"]
        p = d.precios[d.precios["producto"].eq(arroz)].set_index("tienda")["precio_promocion"]
        self.assertEqual(p[tienda["2-1-1"]], 800)
        self.assertTrue(np.isnan(p[tienda["2-1-2"]]))   # promoción vencida el 05/10


if __name__ == "__main__":
    unittest.main()
