"""Tiendas: arreglos de coordenadas, horarios y direcciones."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from sepa.fuentes import geografia
from sepa.tienda import dimension as td


class TestCoordenadas(unittest.TestCase):
    def test_arreglos_mecanicos(self):
        lat = pd.Series([-34.6474, -34.6048, -58.4571, -34603722.0, 12.0])
        lon = pd.Series([58.7942, -58.4571, -34.6048, -58.381592, 20.0])
        la, lo, corr = td.corregir_coordenadas(lat, lon)
        self.assertEqual(corr.tolist(), ["signo", "", "ejes_invertidos", "coma_corrida", "fuera_de_argentina"])
        self.assertAlmostEqual(lo[0], -58.7942)                       # la longitud sin signo cae en el Índico
        self.assertAlmostEqual(la[2], -34.6048)
        self.assertAlmostEqual(la[3], -34.603722)
        self.assertTrue(np.isnan(la[4]))

    def test_distancia(self):
        # Obelisco a Plaza de Mayo: ~1,1 km
        d = float(geografia.distancia_m(-34.6037, -58.3816, -34.6083, -58.3712))
        self.assertTrue(1000 < d < 1200)


class TestHorarios(unittest.TestCase):
    def test_normalizar_horario(self):
        casos = {"8:00 a 22:00": "08:00-22:00", "09.00 a 13.00 - 17.00 a 21.00": "09:00-13:00,17:00-21:00",
                 "Cerrado": "", "20:00 a 02:00": "20:00-26:00", "": None, "consultar": None}
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(td.normalizar_horario(texto), esperado)


class TestDirecciones(unittest.TestCase):
    def test_limpiar_direccion(self):
        casos = {"AV DR.HONORIO PUEYRREDON 652-654-656 (ALMAGRO)": "AV DR HONORIO PUEYRREDON 652",
                 "CUENCA2567": "CUENCA 2567", "Cacheuta 4419 4419": "Cacheuta 4419"}
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(geografia.limpiar_direccion(texto), esperado)

    def test_variantes_de_cencosud(self):
        v = geografia._variantes_usig("Avenida Las Heras gral. Juan Gregori 2564", 9)
        self.assertIn("Las Heras 2564", v)


if __name__ == "__main__":
    unittest.main()
