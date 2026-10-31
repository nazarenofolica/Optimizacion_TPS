"""Composición: alérgenos y aptitudes desde ingredientes, Open Food Facts, el catálogo web y el alimento genérico."""

from __future__ import annotations

import unittest

from sepa.producto import composicion as co

GALLETITA = {"gluten": "desconocido", "leche": "desconocido", "huevo": "desconocido", "mani": "desconocido",
             "frutos_secos": "desconocido", "soja": "desconocido", "pescado": "no", "mariscos": "no",
             "sesamo": "desconocido", "apto_vegetariano": "desconocido", "apto_vegano": "desconocido", "nova": "4"}
NALGA = {"gluten": "no", "leche": "no", "huevo": "no", "mani": "no", "frutos_secos": "no", "soja": "no",
         "pescado": "no", "mariscos": "no", "sesamo": "no", "apto_vegetariano": "no", "apto_vegano": "no", "nova": "1"}


class TestComposicion(unittest.TestCase):
    def test_alimento_natural(self):
        v = co._componer("NALGA X KG", NALGA, None, None)
        self.assertEqual((v["contiene_gluten"], v["sin_tacc"], v["sin_lactosa"], v["apto_vegano"]),
                         ("no", "si", "si", "no"))
        self.assertEqual(v["fuente_composicion"], "alimento genérico")

    def test_ingredientes_y_trazas(self):
        web = {"ingredientes": "harina de trigo, azúcar, aceite de palma, leche en polvo, sal. Puede contener maní "
                               "y soja", "certificaciones": ""}
        v = co._componer("GALLETITAS DULCES", GALLETITA, web, None)
        self.assertEqual((v["contiene_gluten"], v["contiene_leche"], v["contiene_mani"]), ("si", "si", "no"))
        self.assertEqual(v["puede_contener"], "maní, soja")
        self.assertEqual((v["apto_vegano"], v["apto_vegetariano"]), ("no", "si"))
        self.assertEqual((v["aceite_palma"], v["azucar_agregada"], v["sin_tacc"]), ("si", "si", "no"))

    def test_certificacion_sin_tacc(self):
        web = {"ingredientes": "harina de arroz, fécula de mandioca, azúcar, huevo", "certificaciones": "gluten_free"}
        v = co._componer("GALLETITAS S TACC", GALLETITA, web, None)
        self.assertEqual((v["contiene_gluten"], v["sin_tacc"], v["contiene_huevo"]), ("no", "si", "si"))

    def test_open_food_facts(self):
        off = {"alergenos_tags": "en:milk,en:soybeans", "trazas_tags": "en:nuts", "nova": "4", "aditivos_n": "3",
               "analisis_ingredientes_tags": "en:non-vegan", "etiquetas_tags": ""}
        v = co._componer("ALFAJOR", GALLETITA, None, off)
        self.assertEqual((v["contiene_leche"], v["contiene_soja"], v["puede_contener"]), ("si", "si", "frutos secos"))
        self.assertEqual((v["nova"], v["aditivos"], v["apto_vegano"]), (4, 3, "no"))


if __name__ == "__main__":
    unittest.main()
