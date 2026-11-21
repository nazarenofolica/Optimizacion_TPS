"""Lectura del ZIP de SEPA: códigos de barras, registros partidos, promociones, comercios con precios de días
anteriores (dentro de la tolerancia, con su fecha) y desactualizados (afuera)."""

from __future__ import annotations

import io
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from sepa import config as cfg
from sepa import salida, verificacion
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
        "2|1|1|7790000000010|1|YOGUR 1 KG|1|kg|SER|2000.00|2000|1|KG|1500|25% de descuento|1300|"
        "35% de descuento. 2DO AL 70% YOG POTE - Vigencia: Desde el 18/10/2026 hasta el 25/10/2026",
        "2|1|1|7790580660000|1|SIN PRECIO|1|kg|GALLO|||||||",
    ]
    ruta = carpeta / "sepa_viernes_2026-10-23.zip"
    with zipfile.ZipFile(ruta, "w") as z:
        z.writestr("2026-10-23/sepa_comercio-2.zip", _comercio(2, filas, "2026-10-23T04:00:00-03:00"))
        z.writestr("2026-10-23/sepa_comercio-47.zip", _comercio(47, ["47|1|1|7790580660000|1|ARROZ|1|kg|X|1|1|1|KG||||"],
                                                                  "2025-06-11T21:00:01-03:00"))   # archivo viejo
        z.writestr("2026-10-23/sepa_comercio-36.zip", b"")                                      # ZIP vacío
        # Dentro de la tolerancia (8 días: antes, con 7, se excluía): se usa con su fecha. Y uno de 16 días, afuera.
        z.writestr("2026-10-23/sepa_comercio-8.zip", _comercio(8, ["8|1|1|7790580660000|1|ARROZ|1|kg|X|1200|1200|1|KG||||"],
                                                                 "2026-10-15T16:30:38-03:00"))
        z.writestr("2026-10-23/sepa_comercio-20.zip", _comercio(20, ["20|1|1|7790000000010|1|YOGUR|1|kg|X|9|9|1|KG||||"],
                                                                  "2026-10-07T18:55:51-03:00"))
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
        self.assertEqual(estados["sepa_comercio-2.zip"], "ok")
        self.assertEqual(estados["sepa_comercio-8.zip"], "anterior")
        self.assertEqual(estados["sepa_comercio-20.zip"], "desactualizado")          # 16 días: más que la tolerancia
        dias = dict(zip(d.archivos["archivo"], d.archivos["dias_antes_del_zip"]))
        self.assertEqual((dias["sepa_comercio-2.zip"], dias["sepa_comercio-8.zip"], dias["sepa_comercio-20.zip"]),
                         (0, 8, 16))
        self.assertEqual(estados["sepa_comercio-36.zip"], "ilegible")
        self.assertEqual(d.filas_sin_precio, 1)

    def test_claves_y_repetidos(self):
        d = self.datos
        claves = set(d.productos["clave_producto"])
        self.assertEqual(claves, {"7790580660000", "cadena2-2490110000000", "7790000000010"})   # el 47 no deja rastros
        self.assertEqual(len(d.precios), 5)                    # el repetido cuenta una vez; el 8 suma uno, el 20 no
        self.assertEqual(set(d.tiendas["id_tienda"]), {"2-1-1", "2-1-2", "8-1-1"})

    def test_fecha_de_los_precios_por_sucursal(self):
        # Cada sucursal lleva la fecha del archivo de su comercio, no la del ZIP.
        f = self.datos.tiendas.set_index("id_tienda")["fecha_precios"]
        self.assertEqual(f["2-1-1"], pd.Timestamp("2026-10-23"))
        self.assertEqual(f["2-1-2"], pd.Timestamp("2026-10-23"))
        self.assertEqual(f["8-1-1"], pd.Timestamp("2026-10-15"))

    def test_promocion_solo_si_esta_vigente(self):
        d = self.datos
        arroz = d.productos.set_index("clave_producto").loc["7790580660000", "producto"]
        tienda = d.tiendas.set_index("id_tienda")["tienda"]
        p = d.precios[d.precios["producto"].eq(arroz)].set_index("tienda")["precio_promocion"]
        self.assertEqual(p[tienda["2-1-1"]], 800)
        self.assertTrue(np.isnan(p[tienda["2-1-2"]]))   # promoción vencida el 05/10

    def test_promociones_1_y_2_con_su_leyenda(self):
        # Las dos promociones tal como vienen (las clasifica después precio/promociones.py), también la vencida; del
        # comercio desactualizado (47) no queda ninguna.
        d = self.datos
        clave = dict(zip(d.productos["producto"], d.productos["clave_producto"]))
        pr = d.promociones.assign(clave=d.promociones["producto"].map(clave))
        yogur = pr[pr["clave"] == "7790000000010"].sort_values("orden")
        self.assertEqual(yogur["orden"].tolist(), [1, 2])
        self.assertEqual(yogur["precio_promocion"].tolist(), [1500.0, 1300.0])
        self.assertTrue(yogur["leyenda"].iloc[1].startswith("35% de descuento. 2DO AL 70%"))
        self.assertEqual(len(pr[pr["clave"] == "7790580660000"]), 2)          # la vigente y la vencida
        self.assertEqual(set(d.tiendas.set_index("tienda").loc[pr["tienda"].unique(), "id_tienda"]), {"2-1-1", "2-1-2"})


class TestToleranciaDeFechas(unittest.TestCase):
    """Controles de la verificación y el resumen del LEEME con la fecha de cada sucursal."""

    @staticmethod
    def _tablas(fechas: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame]:
        t = pd.DataFrame({"id_tienda": list(fechas), "bandera": ["A"] * (len(fechas) - 1) + ["B"],
                          "fecha_precios": pd.to_datetime(list(fechas.values()))})
        f = pd.DataFrame({"id_tienda": pd.Categorical([k for k in fechas for _ in range(3)]),
                          "fecha": pd.to_datetime([v for v in fechas.values() for _ in range(3)])})
        return t, f

    def _controles(self, t, f, fecha_zip=date(2026, 11, 20)) -> dict[str, int]:
        r: list = []
        verificacion._fechas(r, t, f, fecha_zip)
        return {x["control"].split(":")[0] + ":" + x["control"].split(":")[1][:20]: x["filas_que_fallan"] for x in r}

    def test_la_tolerancia_es_de_15_dias(self):
        self.assertEqual(cfg.DIAS_TOLERANCIA_PRECIO, 15)

    def test_dentro_de_la_tolerancia_pasa_y_se_cuenta(self):
        t, f = self._tablas({"1-1-1": "2026-11-20", "1-1-2": "2026-11-20", "2-1-1": "2026-11-05"})   # 15 días
        c = self._controles(t, f)
        self.assertEqual(list(c.values()), [0, 0, 1])          # ninguna vieja, fechas coherentes, 1 de días anteriores

    def test_mas_vieja_o_del_futuro_falla(self):
        t, f = self._tablas({"1-1-1": "2026-11-21", "2-1-1": "2026-11-04"})           # posterior al ZIP y 16 días
        self.assertEqual(list(self._controles(t, f).values())[0], 2)

    def test_fact_con_otra_fecha_que_su_tienda_falla(self):
        t, f = self._tablas({"1-1-1": "2026-11-20", "2-1-1": "2026-11-19"})
        f.loc[0, "fecha"] = pd.Timestamp("2026-11-19")                            # un precio de 1-1-1 con otra fecha
        self.assertEqual(list(self._controles(t, f).values())[1], 1)

    def test_resumen_del_leeme(self):
        t, _ = self._tablas({"1-1-1": "2026-11-20", "1-1-2": "2026-11-20", "2-1-1": "2026-11-19"})
        linea = salida._fechas_md(t, date(2026, 11, 20))[0]
        self.assertIn("2 del 2026-11-20 y 1 de días anteriores", linea)
        self.assertIn("B, del 2026-11-19 (1)", linea)


if __name__ == "__main__":
    unittest.main()
