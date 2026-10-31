"""Contenido neto: campos estructurados, unidad de referencia y descripción, con los errores reales de SEPA."""

from __future__ import annotations

import unittest

import pandas as pd

from sepa.producto import contenido as ct


class TestFila(unittest.TestCase):
    def test_casos_reales(self):
        casos = [
            # (cantidad, unidad, cant_ref, unidad_ref, ratio, descripcion) -> (contenido, unidad, fuente)
            (("500", "gr", "1", "KG", 0.5, "RAVIOLES"), (500.0, "g", "sepa")),
            (("33.00", "CL", "1.00", "UD", 33.0, "CERV S/TACC"), (330.0, "ml", "sepa")),              # centilitros
            (("0.11", "KG", "0.11", "EA", 1.0, "DULCOR CEREZ 110G"), (110.0, "g", "sepa")),
            (("300.00", "ml.", "1", "LT.", 0.3, "gaseosa MIRINDA 3lt PET-3000-ml."), (3000.0, "ml", "descripcion")),
            ((".90", "gr.", "100", "gr.", 0.9, "Pure ZUMMY 90g DOY-900-gr."), (90.0, "g", "descripcion")),
            (("1", "UNI", "190", "GRM", 0.19, "SALCHICHAS SWIFT X 6 UNI"), (190.0, "g", "referencia")),  # Carrefour
            (("1", "unidad", "1", "unidad", 1.0, "SMART WATER C/G 591 ML"), (591.0, "ml", "descripcion")),
            (("1", "EA", "1", "EA", 1.0, "CERVEZA 6 x 473 ml"), (2838.0, "ml", "descripcion")),
            (("1", "UNI", "1", "UNI", 1.0, "CAFE LA VIRGINIA 1/2 KG"), (500.0, "g", "descripcion")),
            (("1", "KG", "1", "KG", 1.0, "TOMATE PERITA X KG"), (1000.0, "g", "granel")),
            (("1", "UNI", "1", "UNI", 1.0, "TOALLA 50X80"), (None, None, None)),
            # packs que se venden como tal: el tamaño de la descripción es el de cada lata
            (("6", "un.", "1", "un.", 1.0, "gaseosa COCA COLA Original 354cc sixpack PCK-6-un."),
             (2124.0, "ml", "descripcion")),
            (("473", "cc.", "1", "LT.", 34.3, "cerveza ANDES six pack 473 cc LAT-473-cc."), (2838.0, "ml", "sepa")),
            (("2.84", "lt.", "1", "lt.", 2.84, "CERVEZA LATA SIX PACK, HEINEKEN, 2838 cm3"), (2838.0, "ml", "sepa")),
            # el bulto de 12 no es lo que se vende
            ((".50", "gr.", "100", "gr.", 5.0, "AVE MARIA TERRABUSI 100 AÑOS 12X500G PAQ-500-gr."),
             (500.0, "g", "descripcion")),
            (("20.00", "un.", "1", "un.", 1.0, "Té Green Hills Blend Relax 20 Saq x 1 gr PET-20-un."),
             (20.0, "g", "descripcion")),
            # botellas de 75 cl cargadas como 75 ml, redondeos del campo estructurado y el "1 g" que es una unidad
            ((".08", "ml.", "100", "ml.", 0.0008, "vino CRUX Malbec BOT-75-ml."), (750.0, "ml", "descripcion")),
            ((".13", "Kg", "1", "Kg", 0.125, "yogur descremado MOMY vainilla 125 gr POT-0.125-Kg"), (125.0, "g", "sepa")),
            (("1", "gr", "1", "kg", 0.001, "GELATINA FRAMBUESA MAGICA MORIXE X 40 GRS"), (40.0, "g", "descripcion")),
            # separador de miles y códigos en litros rotulados ml
            (("2250.00", "cm3", "1.00", "lt", 2.25, "GASEOSA CUNNINGTON COLA 2.250CC"), (2250.0, "ml", "sepa")),
            (("2.755", "GR", "1", "KG", 2.755, "Mayonesa Hellmanns Bolsa x 2.755 Gr"), (2755.0, "g", "descripcion")),
            ((".35", "ml.", "100", "ml.", 0.0035, "Gaseosa LAS BRISAS limon LAT-0.354-ml."), (354.0, "ml", "descripcion")),
            # Carrefour: "1 GRM" es "una unidad"; la referencia por 100 g vale si el texto no dice otra cosa
            (("1", "UNI", "1", "GRM", 0.001, "AVENA CON VAINILLA Y MIEL KUATI X 300 GRS"), (300.0, "g", "descripcion")),
            (("1", "UNI", "10", "GRS", 0.1, "LAUREL EN HOJAS ALICANTE X 10 GRS"), (10.0, "g", "referencia")),
            (("1", "UNI", "10", "GRS", 0.1, "MEDIA BARRA RUSTICA MULTICEREAL X 100 GRS."), (100.0, "g", "descripcion")),
            (("1", "UNI", "40", "GRS", 0.4, "TE TILO SILVESTRE TARAGUI X 20 UNI"), (40.0, "g", "referencia")),
            # la cantidad de saquitos cargada como gramos no es un contenido
            (("1", "UNI", "25", "GRS", 0.25, "TE CEDRON EN SAQUITOS LA VIRGINIA X 25 UNI"), (None, None, None)),
        ]
        for entrada, esperado in casos:
            with self.subTest(descripcion=entrada[-1]):
                self.assertEqual(ct.resolver_fila(*entrada)[:3], esperado)

    def test_unidades(self):
        self.assertEqual(ct.resolver_fila("6", "EA", "6", "EA", 1.0, "HUEVOS BL SEL X 6UN")[3], 6)
        self.assertEqual(ct.resolver_fila("1", "UNI", "30", "UNI", 30.0, "MAPLE BLANCO X30UNI")[3], 30)
        self.assertEqual(ct.resolver_fila("1", "un", "1", "un", 1.0, "HUEVOS COLOR DOCENA")[3], 12)
        self.assertEqual(ct.resolver_fila("1", "cu", "1", "cu", 1.0, "LECHUGA MANTECOSA X UN")[3], 1)
        # Solo el precio de referencia por unidad dice cuántos huevos trae ("X 30 C T").
        self.assertEqual(ct.resolver_fila("1", "UNI", "30", "UNI", 30.0006, "HUEVO BLANCO BENECH X 30 C T")[3], 30)

    def test_alternativo_cuando_las_fuentes_no_coinciden(self):
        # "N UN X M g" es ambiguo: vale M y N x M queda como alternativo (lo decide el precio).
        r = ct.resolver_fila("1", "UN", "1", "UN", 1.0, "FERRERO ROCHER BOMBON PAQ.3 UNID X 37.5G")
        self.assertEqual((r[0], r[5]), (37.5, (112.5, "g")))


class TestVotos(unittest.TestCase):
    def test_gana_lo_que_respaldan_mas_sucursales_sin_importar_g_o_ml(self):
        pres = pd.DataFrame({
            "producto": [1, 1, 1],
            "descripcion": ["QUESO MASCARPONE X 200 CC", "Queso mascarpone x200grs POT-200-gr.", "MASCARPONE 250 G"],
            "cantidad": ["1", "200.00", "250"], "unidad": ["UNI", "gr.", "gr"],
            "cantidad_referencia": ["200", "1", "1"], "unidad_referencia": ["CM3", "KG.", "KG"],
            "ratio_referencia": [0.2, 0.2, 0.25], "veces": [446, 161, 100],
        })
        r = ct.resolver(pres, internos=set()).iloc[0]
        self.assertEqual(r["contenido"], 200.0)
        self.assertEqual(r["unidad_contenido"], "ml")          # la unidad más respaldada entre los que dicen 200
        self.assertAlmostEqual(r["contenido_acuerdo"], 607 / 707, places=3)

    def test_contenido_en_disputa_queda_como_alternativo(self):
        # Una cadena informa el peso de una cápsula (5 g) y otra el de la caja (50 g): decide el precio, después.
        pres = pd.DataFrame({
            "producto": [3, 3], "descripcion": ["CAPS SELECCION NE 5G", "CAFE CAPS BONAFIDE CJA 50 GRM"],
            "cantidad": ["0.005", "50"], "unidad": ["KG", "grm"], "cantidad_referencia": ["0.005", "1"],
            "unidad_referencia": ["EA", "kgm"], "ratio_referencia": [1.0, 0.05], "veces": [93, 56],
        })
        r = ct.resolver(pres, internos=set()).iloc[0]
        self.assertEqual((r["contenido"], r["contenido_alternativo"], r["unidad_alternativa"]), (5.0, 50.0, "g"))

    def test_balanza_de_un_kilo_es_granel(self):
        pres = pd.DataFrame({"producto": [7], "descripcion": ["BANANA ECUADOR"], "cantidad": ["1"], "unidad": ["KG"],
                             "cantidad_referencia": ["1"], "unidad_referencia": ["KG"], "ratio_referencia": [1.0],
                             "veces": [50]})
        r = ct.resolver(pres, internos={7}).iloc[0]
        self.assertTrue(r["granel"])
        self.assertEqual((r["contenido"], r["unidad_contenido"]), (1000.0, "g"))


if __name__ == "__main__":
    unittest.main()
