"""Promociones de SEPA: clasificación de las leyendas (reales, del ZIP del 20/11/2026), la tabla promocion y sus
controles. Sin red ni datos."""

from __future__ import annotations

import unittest
from datetime import date
from types import SimpleNamespace

import numpy as np
import pandas as pd

from sepa import verificacion
from sepa.precio import promociones as pr

# Leyendas reales, con las filas que tenían en el ZIP del 20/11/2026 (las más frecuentes de cada cadena y casos raros).
REALES = {
    # DIA, promo 1 (832.938 filas con este patrón): un porcentaje sin condiciones
    "25% de descuento. Precio Promocional Exclusivo DIA en Sucursales Indicadas Hasta Agotar Stock o Finalice "
    "Vigencia.": ("porcentaje", {"porcentaje": 25.0}, "25 % de descuento"),
    # DIA, promo 2: el porcentaje del principio es el promedio; la promoción viene después
    "35% de descuento. 2DO AL 70% YOG POTE - Vigencia: Desde el 18/11/2026 hasta el 23/11/2026":
        ("segunda_unidad", {"n": 2, "porcentaje": 70.0}, "2.ª al 70 %"),
    "25% de descuento. 2DO AL 50% SIDRAS Y - Vigencia: Desde el 18/11/2026 hasta el 23/11/2026":
        ("segunda_unidad", {"n": 2, "porcentaje": 50.0}, "2.ª al 50 %"),
    "33% de descuento. 3X2 TANG - Vigencia: Desde el 18/11/2026 hasta el 23/11/2026":
        ("nxm", {"n": 3, "m": 2}, "3×2"),
    "50% de descuento. 2X1 OBLEA KIT KAT 41 - Vigencia: Desde el 15/11/2026 hasta el 14/12/2026":
        ("nxm", {"n": 2, "m": 1}, "2×1"),
    "25% de descuento. 2X$1400 CARAM HALLS - Vigencia: Desde el 15/11/2026 hasta el 14/12/2026":
        ("llevando_x", {"n": 2, "precio": 1400.0, "cada_unidad": False}, "2 × $1.400"),
    "67% de descuento. LLEVANDO 3 ACTIMEL - Vigencia: Desde el 18/11/2026 hasta el 23/11/2026":
        ("llevando_x", {"n": 3, "precio": None, "cada_unidad": False}, "Llevando 3"),
    "75% de descuento. $3945 DESO PEARL TT - Vigencia: Desde el 04/11/2026 hasta el 30/11/2026":
        ("precio_fijo", {"precio": 3945.0}, "Precio promo $3.945"),
    "35% de descuento. 35% SEDAL - Vigencia: Desde el 18/11/2026 hasta el 23/11/2026":
        ("porcentaje", {"porcentaje": 35.0}, "35 % de descuento"),
    # La Anónima
    "25% de descuento con cualquier medio de pago - Vigencia: Desde el 18/11/2026 Hasta el 29/11/2026 - Stock: Hasta "
    "agotar stock.": ("porcentaje", {"porcentaje": 25.0}, "25 % de descuento"),
    "Llevando 2 unidades - Vigencia: Desde el 19/11/2026 Hasta el 29/11/2026 - Stock: Hasta agotar stock.":
        ("llevando_x", {"n": 2, "cada_unidad": False}, "Llevando 2"),
    # Cooperativa Obrera
    "Descuentazo 20% - Vigencia desde el 16/11/2026 al 30/11/2026 hasta agotar Stock de 6 unidades.":
        ("porcentaje", {"porcentaje": 20.0, "tope": 6}, "20 % de descuento"),
    "Llevando 2 paga $3350.00 c/u - Vigencia desde el 06/11/2026 al 29/11/2026 o hasta agotar Stock de 14 unidades.":
        ("llevando_x", {"n": 2, "precio": 3350.0, "cada_unidad": True, "tope": 14}, "Llevando 2: $3.350 c/u"),
}
# Las que no dicen qué promoción es: desconocidas, no se aplican.
DESCONOCIDAS = [
    "Promo A valida desde el 18/11/2026 hasta 24/11/2026",                              # Carrefour, 182.776 filas
    "DEL 16/11/2026 AL 22/11/2026",                                                    # Coto
    "Vigencia desde el 19/11/2026 al 25/11/2026 hasta agotar Stock de 12 unidades.",   # Cooperativa Obrera
    "Vigente hasta el 2026-11-24 hasta agotar Stock de 13 unidades.",
    "Producto en Oferta",                                                              # Toledo
    "0% de descuento. Precio Promocional Exclusivo DIA en Sucursales Indicadas Hasta Agotar Stock o Finalice "
    "Vigencia.",
    "Llevando 1800 unidades - Vigencia: Desde el 01/10/2026 Hasta el 25/11/2026 - Stock: Hasta agotar stock.",
    "",
]
# Condiciones de pago: el ZIP del 20/11/2026 no trae ninguna con su leyenda (las de Carrefour y Coto no dicen nada);
# estas son como las de los catálogos de las cadenas.
PAGO = {
    "20% de descuento con Tarjeta Visa del Banco Galicia": "banco",
    "2x1 pagando con Mercado Pago": "billetera",
    "25% con MODO": "billetera",
    "3x2 exclusivo Club La Anónima": "fidelidad",
    "2DA AL 70% CON MI CARREFOUR": "fidelidad",
    "15% de descuento con tarjeta de débito": "tarjeta",
    "30% pagando en efectivo": "efectivo",
}


class TestClasificar(unittest.TestCase):
    def test_leyendas_reales(self):
        for leyenda, (tipo, parametros, resumen) in REALES.items():
            with self.subTest(leyenda=leyenda[:50]):
                p = pr.clasificar(leyenda)
                self.assertEqual(p["tipo"], tipo)
                for k, v in parametros.items():
                    self.assertEqual(p[k], v, k)
                self.assertEqual(p["resumen"], resumen)
                self.assertTrue(p["aplicable"], p["motivo"])
                self.assertEqual(p["motivo"], "")
                self.assertIsNone(p["condicion_pago"])

    def test_vigencia(self):
        p = pr.clasificar("35% de descuento. 35% SEDAL - Vigencia: Desde el 18/11/2026 hasta el 23/11/2026")
        self.assertEqual((p["vigencia_desde"], p["vigencia_hasta"]), (date(2026, 11, 18), date(2026, 11, 23)))
        self.assertTrue(pr.vigente(p, date(2026, 11, 20)))
        self.assertFalse(pr.vigente(p, date(2026, 11, 24)))
        p = pr.clasificar("Vigente hasta el 2026-11-24 hasta agotar Stock de 13 unidades.")
        self.assertEqual((p["vigencia_desde"], p["vigencia_hasta"], p["tope"]), (None, date(2026, 11, 24), 13))
        sin_fechas = pr.clasificar("25% de descuento. Precio Promocional Exclusivo DIA en Sucursales Indicadas")
        self.assertTrue(pr.vigente(sin_fechas, date(2026, 11, 20)))

    def test_desconocidas_no_se_aplican(self):
        for leyenda in DESCONOCIDAS:
            with self.subTest(leyenda=leyenda[:50]):
                p = pr.clasificar(leyenda)
                self.assertEqual(p["tipo"], "desconocida")
                self.assertFalse(p["aplicable"])
                self.assertTrue(p["motivo"])

    def test_condicion_de_pago_no_se_aplica(self):
        for leyenda, condicion in PAGO.items():
            with self.subTest(leyenda=leyenda):
                p = pr.clasificar(leyenda)
                self.assertEqual(p["condicion_pago"], condicion)
                self.assertFalse(p["aplicable"])
                self.assertEqual(p["motivo"], pr.CONDICIONES_PAGO[condicion])
                self.assertNotIn("Galicia", p["motivo"])                  # el motivo no nombra bancos

    def test_cualquier_medio_de_pago_no_es_una_condicion(self):
        p = pr.clasificar("30% de descuento con cualquier medio de pago - Vigencia: Desde el 18/11/2026 Hasta el "
                          "29/11/2026")
        self.assertIsNone(p["condicion_pago"])
        self.assertTrue(p["aplicable"])
        # "Descuentazo" no es "cuenta" ni "Exclusivo DIA" es el programa de la cadena.
        self.assertTrue(pr.clasificar("Descuentazo 20% - Vigencia desde el 16/11/2026 al 30/11/2026")["aplicable"])

    def test_otras_condiciones(self):
        casos = {"25% de descuento. 25% PANIF X TARDE - Vigencia: Desde el 07/01/2026 hasta el 31/12/2026":
                 "solo en un horario",
                 "2x1 los miércoles y jueves": "solo algunos días (miércoles, jueves)",
                 "10% jubilados": "solo para jubilados",
                 "20% en compras online": "solo en la compra online"}
        for leyenda, motivo in casos.items():
            with self.subTest(leyenda=leyenda[:40]):
                p = pr.clasificar(leyenda)
                self.assertFalse(p["aplicable"])
                self.assertEqual(p["motivo"], motivo)

    def test_tamanos_no_son_nxm(self):
        # Un pack (6 x 1,5 L) o un peso (2 x 500 g) no es un 6×1.
        for leyenda in ("Lleva 6 x 1,5 L", "PACK 2 X 500 G", "4X1L"):
            with self.subTest(leyenda=leyenda):
                self.assertNotEqual(pr.clasificar(leyenda)["tipo"], "nxm")


def _datos(filas: list[tuple], dia: date = date(2026, 11, 20)) -> SimpleNamespace:
    """Un DatosSEPA mínimo: promociones (producto, tienda, orden, leyenda, precio_promocion) y sus claves."""
    promos = pd.DataFrame(filas, columns=["producto", "tienda", "orden", "leyenda", "precio_promocion"])
    promos["leyenda"] = promos["leyenda"].astype("category")
    productos = pd.DataFrame({"producto": [0, 1, 2], "clave_producto": ["7790000000001", "7790000000002", "x-3"]})
    tiendas = pd.DataFrame({"tienda": [0, 1], "id_tienda": ["15-1-1", "2-1-1"]})
    return SimpleNamespace(promociones=promos, productos=productos, tiendas=tiendas, fecha=dia)


FACT = pd.DataFrame({"id_producto": pd.Categorical(["7790000000001", "7790000000002", "7790000000002"]),
                     "id_tienda": pd.Categorical(["15-1-1", "15-1-1", "2-1-1"]), "precio": [1000.0, 2000.0, 1800.0]})


class TestTabla(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tabla, cls.stats = pr.armar(_datos([
            (0, 0, 1, "25% de descuento. Precio Promocional Exclusivo DIA en Sucursales Indicadas", 750.0),
            (0, 0, 2, "50% de descuento. 2X1 OBLEA - Vigencia: Desde el 15/11/2026 hasta el 14/12/2026", 500.0),
            (1, 0, 2, "35% de descuento. 2DO AL 70% YOG POTE - Vigencia: Desde el 18/11/2026 hasta el 23/11/2026",
             1300.0),
            (1, 1, 1, "Llevando 2 unidades - Vigencia: Desde el 19/11/2026 Hasta el 29/11/2026", 1350.0),
            (1, 1, 2, "20% de descuento con Tarjeta Visa del Banco Galicia", 1440.0),
            (2, 0, 1, "25% de descuento", 10.0),                       # producto que no está en fact_precio
            (0, 1, 1, "25% de descuento", 10.0),                       # tienda en la que no tiene precio
            (1, 0, 1, "35% SEDAL - Vigencia: Desde el 01/11/2026 hasta el 05/11/2026", 1300.0),   # vencida
            (1, 0, 1, "Promo A valida desde el 18/11/2026 hasta 24/11/2026", 1500.0),       # la vigente
        ]), FACT)

    def fila(self, producto, tienda, orden):
        t = self.tabla
        return t[(t["id_producto"] == producto) & (t["id_tienda"] == tienda) & (t["orden"] == orden)].iloc[0]

    def test_solo_las_de_precios_publicados_y_vigentes(self):
        self.assertEqual(self.stats["de_precios_publicados"], 7)
        self.assertEqual(self.stats["fuera_de_vigencia"], 1)
        self.assertEqual(len(self.tabla), 6)
        self.assertEqual(list(self.tabla.columns), pr.COLUMNAS)

    def test_forma_y_precio_unitario(self):
        f = self.fila("7790000000001", "15-1-1", 1)
        self.assertEqual((f["forma"], f["unidades"], f["precio_unitario"], f["precio_lista"]), ("precio", 1, 750.0, 1000))
        f = self.fila("7790000000001", "15-1-1", 2)
        self.assertEqual((f["tipo"], f["forma"], f["unidades"], f["precio_unitario"]), ("nxm", "grupo", 2, 500.0))
        f = self.fila("7790000000002", "15-1-1", 2)
        self.assertEqual((f["tipo"], f["forma"], f["unidades"], f["precio_unitario"]), ("segunda_unidad", "grupo", 2,
                                                                                        1300.0))
        f = self.fila("7790000000002", "2-1-1", 1)               # La Anónima: el precio publicado dice cuánto
        self.assertEqual((f["tipo"], f["forma"], f["unidades"], f["precio_unitario"]), ("llevando_x", "grupo", 2,
                                                                                        1350.0))
        self.assertEqual(self.tabla["aplicable"].sum(), 4)

    def test_no_aplicables_con_motivo(self):
        f = self.fila("7790000000002", "2-1-1", 2)
        self.assertFalse(f["aplicable"])
        self.assertEqual((f["condicion_pago"], f["motivo"]), ("banco", "requiere un banco"))
        self.assertTrue(np.isnan(f["precio_unitario"]))
        f = self.fila("7790000000002", "15-1-1", 1)
        self.assertEqual((f["tipo"], bool(f["aplicable"])), ("desconocida", False))

    def test_precio_que_no_coincide_con_la_leyenda(self):
        tabla, _ = pr.armar(_datos([(0, 0, 1, "25% de descuento", 500.0),        # 25 % de 1.000 no da 500
                                    (0, 0, 2, "3X2 TANG", 1000.0),               # no es menor al de lista
                                    (1, 0, 1, "25% de descuento", np.nan)]),     # sin publicado: el de la leyenda
                            FACT)
        motivos = dict(zip(tabla["orden"].astype(str) + tabla["id_producto"].astype(str), tabla["motivo"]))
        self.assertEqual(motivos["17790000000001"], "el precio publicado no coincide con lo que dice la leyenda")
        self.assertEqual(motivos["27790000000001"], "")
        f = tabla[tabla["id_producto"] == "7790000000002"].iloc[0]
        self.assertEqual((bool(f["aplicable"]), f["precio_unitario"]), (True, 1500.0))
        f = tabla[(tabla["id_producto"] == "7790000000001") & (tabla["orden"] == 2)].iloc[0]
        self.assertAlmostEqual(f["precio_unitario"], 666.67)              # el 3×2 sale de la leyenda

    def test_verificacion(self):
        r: list = []
        verificacion._promocion(r, FACT, self.tabla)
        res = pd.DataFrame(r)
        self.assertEqual(res.loc[res["critico"], "filas_que_fallan"].sum(), 0, res.to_string())
        mala = self.tabla.copy()
        mala["aplicable"] = True                                          # la del banco no se puede aplicar
        r = []
        verificacion._promocion(r, FACT, mala)
        res = pd.DataFrame(r).set_index("control")["filas_que_fallan"]
        self.assertEqual(res["promoción: con condición de pago no se aplica"], 1)
        self.assertGreater(res["promoción: la aplicable no tiene motivo y la otra sí"], 0)

    def test_cobertura(self):
        c = pr.cobertura(self.tabla)
        self.assertEqual(c["filas"].sum(), len(self.tabla))
        self.assertEqual(c.loc["aplicable", "filas"], 4)
        self.assertEqual(c.loc["no aplicable: medio de pago", "filas"], 1)
        self.assertEqual(c.loc["desconocida", "filas"], 1)

    def test_sin_promociones(self):
        tabla, stats = pr.armar(_datos([]), FACT)
        self.assertEqual(len(tabla), 0)
        self.assertEqual(list(tabla.columns), pr.COLUMNAS)


if __name__ == "__main__":
    unittest.main()
