"""Precios: descarte de anormales y normalización a la unidad de cada subcategoría."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from sepa.precio import limpieza
from sepa.producto import clasificacion
from sepa.producto.dimension import presentacion


def _obs(precios_por_cadena: dict[int, list[float]], producto: int = 1) -> pd.DataFrame:
    filas, tienda = [], 0
    for comercio, lista in precios_por_cadena.items():
        for p in lista:
            filas.append((producto, tienda, comercio, p))
            tienda += 1
    return pd.DataFrame(filas, columns=["producto", "tienda", "comercio", "precio"])


class TestLimpieza(unittest.TestCase):
    def test_error_de_carga(self):
        r = limpieza.marcar_anormales(_obs({1: [1000, 1010, 990], 2: [1050, 1040], 3: [10.5]}))
        self.assertEqual(r["motivo"].tolist(), [""] * 5 + ["muy_bajo"])

    def test_una_cadena_grande_mal_cargada_no_arrastra_la_referencia(self):
        # La cadena 1 cargó el pack de 6 en sus 50 sucursales.
        r = limpieza.marcar_anormales(_obs({1: [6000] * 50, 2: [1000, 1020], 3: [990], 4: [1010]}))
        self.assertEqual((r["motivo"] == "muy_alto").sum(), 50)
        self.assertEqual(r.loc[r["motivo"].eq(""), "precio"].median(), 1005.0)

    def test_dispersion_normal_y_fuera_de_rango(self):
        r = limpieza.marcar_anormales(_obs({1: [1000], 2: [1300], 3: [800], 4: [1100], 5: [0.5]}))
        self.assertEqual(r["motivo"].tolist(), [""] * 4 + ["fuera_de_rango"])

    def test_dos_cadenas_que_no_coinciden_las_arbitra_el_precio_posible(self):
        # Una cadena publica el precio de una caja de six-packs (245.400) y otra el del six-pack (25.500): sin
        # árbitro, el punto medio descartaría el precio correcto.
        obs = _obs({9: [245_400] * 32, 2: [25_500] * 139})
        rango = pd.DataFrame({"minimo": [5_000.0], "maximo": [45_000.0]}, index=[1])
        r = limpieza.marcar_anormales(obs, rango)
        self.assertEqual(r.loc[r["comercio"].eq(9), "motivo"].unique().tolist(), ["muy_alto"])
        self.assertEqual(r.loc[r["comercio"].eq(2), "motivo"].unique().tolist(), [""])

    def test_estacion_de_servicio_y_cadena_de_descuento_son_precios_reales(self):
        # Una gaseosa que en el resto cuesta lo mismo en todas partes: 1,7 veces en la estación, 40 % menos en
        # la de descuento. Un precio de hace años (0,25) sí se descarta.
        r = limpieza.marcar_anormales(_obs({1: [1000] * 5, 2: [1000] * 3, 3: [1700], 4: [600], 5: [250]}))
        self.assertEqual(r["motivo"].tolist(), [""] * 10 + ["muy_bajo"])

    def test_gemelos(self):
        # Un aceite que vende una sola cadena chica a $90 el litro, frente al mismo producto en otras cadenas.
        p = pd.DataFrame({
            "descripcion": ["ACEITE GIRASOL NATURA 1.5 L", "ACEITE GIRASOL NATURA 1500 ML", "ACEITE GIRASOL COCINERO"],
            "alimento_id": ["aceite"] * 3, "cantidad_normalizada": [1.5, 1.5, 1.5],
            "precio_normalizado": [90.0, 4000.0, 3800.0], "tiendas": [7, 900, 800],
            "cadenas": [frozenset({5}), frozenset({9, 10, 11}), frozenset({10, 12})], "estimado": [False] * 3,
            "plausible": [False, True, True],
        }, index=["solo", "natura", "cocinero"])
        r = limpieza.ratio_gemelos(p)
        self.assertLess(r["solo"], 0.05)
        self.assertTrue(np.isnan(r["natura"]))      # lo que venden varias cadenas no se evalúa


class TestNormalizacion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = clasificacion.cargar_catalogo()

    def test_misma_unidad_dentro_de_la_subcategoria(self):
        p = pd.DataFrame({
            "alimento_id": ["banana", "banana", "leche_entera", "aceite", "huevos", "lechuga", "yogur"],
            "contenido": [1000.0, 500.0, 1000.0, 900.0, np.nan, np.nan, 1000.0],
            "unidad_contenido": ["g", "g", "ml", "g", None, None, "ml"],
            "unidades": [np.nan, np.nan, np.nan, np.nan, 12, 1, np.nan],
            "granel": [True, False, False, False, False, False, False],
        })
        r = presentacion(p, self.cat)
        self.assertEqual(r["unidad_normalizada"].tolist(), ["kg", "kg", "l", "l", "unidad", "kg", "kg"])
        # 1 kg a granel y 500 g quedan comparables por kilo
        self.assertEqual(r["cantidad_normalizada"].tolist()[:2], [1.0, 0.5])
        self.assertEqual(r["forma_venta"].tolist()[:2], ["Granel (precio por kg)", "Envase"])
        self.assertAlmostEqual(r.loc[3, "cantidad_normalizada"], 0.9 / 0.92, places=4)   # aceite en gramos -> litros
        self.assertEqual(r.loc[3, "base_normalizacion"], "densidad")
        self.assertEqual(r.loc[4, "cantidad_normalizada"], 12)                            # huevos por unidad
        self.assertEqual(r.loc[5, "base_normalizacion"], "peso_unidad_estimado")          # lechuga x unidad
        self.assertAlmostEqual(r.loc[6, "gramos_envase"], 1050.0)                         # yogur 1 l = 1,05 kg
        self.assertEqual((r.loc[2, "cantidad_publicada"], r.loc[2, "unidad_publicada"]), (1000.0, "ml"))


if __name__ == "__main__":
    unittest.main()
