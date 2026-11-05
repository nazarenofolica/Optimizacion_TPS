"""Clasificación en alimentos genéricos con el catálogo real y la categoría de góndola como segunda opinión."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from sepa.producto import categorias, clasificacion as cl


class TestReglas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogo = cl.cargar_catalogo()

    def clasificar(self, descripcion: str, ean: bool = True) -> str | None:
        df = pd.DataFrame({"descripcion": [descripcion], "descripciones_alternativas": [None], "es_ean": [ean]})
        return cl.clasificar_productos(df, self.catalogo).iloc[0]

    def test_lo_compuesto_gana_al_ingrediente(self):
        casos = {
            "POLLO FRESCO X KG": "pollo_entero", "YOGUR BEBIBLE BANANA SANCOR 1 LT": "yogur",
            "MEDALLONES DE POLLO SWIFT X4": "nuggets_pollo", "VINO CORDERO C/PIEL LOBO C.SAUV.X750ML": "vino",
            "ASADO DE CORDERO X KG": "cordero", "LECHE ENTERA LA SERENISIMA SACHET 1 LT": "leche_entera",
            "GALLETITAS DE AGUA CRIOLLITAS 300 G": "galletitas_agua", "PATE DE FOIE SWIFT 90 GR": "pate",
            "SEMILLAS DE CHIA 200 G": "semillas", "REMOLACHA X KG": "remolacha", "CHAMPIGNONES X KG": "hongos",
            "TURRON DE MANI ARCOR 25 GRS": "caramelos", "EDULCORANTE LIQUIDO HILERET 200 ML": "edulcorante_liquido",
        }
        for descripcion, esperado in casos.items():
            with self.subTest(descripcion=descripcion):
                self.assertEqual(self.clasificar(descripcion, ean=not descripcion.endswith("X KG")), esperado)

    def test_errores_corregidos(self):
        # Encontrados al cruzar con las categorías de los catálogos web.
        casos = {
            "Aceite NATURA Blend Girasol & Oliva PET-900-ml.": "aceite_oliva",   # no es vino por "Blend"
            "saborizada LEVITE Pomelo Rosado 500cc": "agua_saborizada",          # no es vino por "Rosado"
            "BLOCK A4 AMERICA NOS2 CUAD 80H": None,                               # útiles escolares, no chocolate
            "ENDULZANTE CHUKER 300 TABLETAS": "edulcorante",                     # no es chocolate por "tabletas"
            "ALF DDL C/BAN REPOST": "alfajor",                                    # alfajor abreviado, no dulce de leche
            "JARRO CHOPP HOLANDES 350cc": None,                                   # vaso, no cerveza
            "GUANTES MEDIANO PATITO PAR 1 UNI": None,                             # guantes, no aceite
            # Encontrados al armar canastas: abreviaturas que se colaban en alimentos básicos.
            "GALL.DULC.ROSQ.SAB.LECHE ISABELA PAQ 300 GRM": "galletitas_dulces",  # no es leche (ni en polvo)
            "BALLCH CHO MANI 70G": None,                                          # chocolate, no maní
            "EDULC.SAB.AVELLANA SVELTA BOT 110 ML": "edulcorante_liquido",        # no es un fruto seco
            "GARRAPIÑADA DE ALMENDRA GEORGALOS BOLSA X 80 GRS": "caramelos",      # golosina, no almendras
        }
        for descripcion, esperado in casos.items():
            with self.subTest(descripcion=descripcion):
                self.assertEqual(self.clasificar(descripcion), esperado)

    def test_lo_que_no_es_comida_no_se_clasifica(self):
        for descripcion in ["SHAMPOO MANZANA FRESCA 400 ML", "LAVAVAJILLAS LIMON ZORRO 500 CC",
                            "ALIMENTO PERROS ADULTOS POLLO 15 KG", "CUCHARA MANGO MADERA",
                            "OJOTA BASICAS MONOCOLOR 27AL34 NARANJA"]:
            with self.subTest(descripcion=descripcion):
                self.assertIsNone(self.clasificar(descripcion))

    def test_fruta_fresca_con_ean_necesita_senal_de_fresco(self):
        self.assertEqual(self.clasificar("NARANJA X KG (PAX)"), "citricos")
        self.assertIsNone(self.clasificar("VWS CREATINE NARANJA 378 G SUPLEMENTO"))

    def test_una_exclusion_no_veta_por_una_parte_de_otra_palabra_ni_por_una_marca(self):
        casos = {
            "YOGUR DESCREMADO VAINILLA GRAN COMPRA X 120 GRS": "yogur_descremado",   # CREMA en DESCREMADO
            "FIDEOS RIGATONI CARREFOUR CLASSIC X 500 GRS": "fideos",                 # GATO en RIGATONI
            "DULCE DE LECHE FAMILIAR MILKAUT POTE X 400 GRS": "dulce_de_leche",       # MILKA en MILKAUT
            "Pan lactal LA ESPAÑOLA x 350 grs. BSA-350-gr.": "pan_lactal",            # PANO en ESPANOLA
            "AGUA MINERAL SIN GAS HIPERTERMAL PALAU PET X 2 LT": "agua",              # TERMAL en HIPERTERMAL
            "VINO TINTO MALBEC, 4 DE COPAS, 750 cm3": "vino",                         # la marca, no copas
            "SALAME COLONIA CAROYA FAMILIA GRION X KGM": "salame",                    # no es agua de colonia
            "HELADO PEÑAS 1L. LIMON": "helado",                                       # un helado se vende por litro
            "PIZZA A LA PIEDRA MOZZARELLA PIETRO CJA 600 GRM": "pizza",               # no es una piedra para pizza
            "PANAL DE MEMBRILLO": "dulce_membrillo",                                  # no es un pañal
        }
        for descripcion, esperado in casos.items():
            with self.subTest(descripcion=descripcion):
                self.assertEqual(self.clasificar(descripcion), esperado)

    def test_objetos_que_nombran_un_alimento(self):
        # Encontrados entre los que el clasificador de góndola no reconoce: un gazebo azul no es queso azul.
        for descripcion in ["GAZEBO PLEGABLE CON PAREDES 3X3 MTS AZUL", "MANT SHERP 120X150CM",
                            "ACEITE GULF MAX 20W 50 X 4L", "SILLON QUALITY PLASTIC MILO REBATIBLE",
                            "TORNILLO P MADERA PUNTA AGUJA CARREFOUR 6 X 1 1 2", "SOPAPA CMT GOMA NEGRA MEDIANA",
                            "SAND. DE MILANESA CON J. Y Q. X 1 UNID.", "AEROSOL PAPAYA"]:
            with self.subTest(descripcion=descripcion):
                self.assertIsNone(self.clasificar(descripcion))

    def test_genericos_agregados(self):
        casos = {
            "ACEITE DE COCO NEUTRO CARREFOUR CLASSIC X 200 CC": "aceite_coco",
            "CHAMPIGNONES E/TROZOS INCA LAT 350 GRM": "verduras_conserva",
            "ZANAHORIAS EN RODAJAS DAUCY LAT 400 GRM": "verduras_conserva",
            "CIRUELA DAGEN S/C X 150 GS POT-1-un.": "frutas_secas",
            # sin azúcar por la marca o por la descripción; los chicles con azúcar siguen siendo caramelos
            "CHICLE BELDENT MANDARINA x20g PCK-20-gr.": "golosinas_sin_azucar",
            "CHICLES TOPLINE S/AZ.FRUTA TABLETAS": "golosinas_sin_azucar",
            "MENTHO-PLUS CARAMELOS SIN AZUCAR CHERRY X 27.3G": "golosinas_sin_azucar",
            "chicle Doublemnit 15 stk x 45grs PAQ-45-gr.": "caramelos",
            "GELATINA FRAMBUESA DIET CARREFOUR CLASSIC X 20 GRS": "gelatina_light",
            "GELATINA EXQUISITA FRUTILLA 25": "gelatina",
            "MERMELADA ARCOR LIGHT DURAZ. 390GRS": "mermelada_light",
            "MERMELADA DE DURAZNO ARCOR 454 G": "mermelada",
            "Aceto Balsamico de Modena MENOYO 250 ml": "aceto_balsamico",
            "ACETO BALS.TIPO REDUC ESPESO FAVINCO PET 250 ML": "salsas_varias",   # la reducción es una salsa
            "Vinagre MENOYO de manzana PVC-1-lt.": "vinagre",
            "CHOCOLATE NEGRO SIN AZUCAR GEORGALOS X 30 GRS": "chocolate_leche",
            "RAPIDITAS BIMBO Clásicas x 275grs. BSA-270-gr.": "pan_frances",
            "TORTILLA PAPA SMART MENU": "tarta",
            "ICE TEA FRUT.MANGO X10 SAQ. SAINT GOTTARD CJA 25 GRM": "te",
        }
        for descripcion, esperado in casos.items():
            with self.subTest(descripcion=descripcion):
                self.assertEqual(self.clasificar(descripcion), esperado)


class TestCategorias(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogo = cl.cargar_catalogo()
        cls.reglas = cl.cargar_categorias()

    def test_prefijo_mas_largo(self):
        estado, compatibles, defecto = cl.compatibilidad("Almacén > Aderezos > Mayonesas", self.reglas)
        self.assertEqual((estado, defecto), ("compatibles", "mayonesa"))
        self.assertIn("mayonesa_light", compatibles)
        self.assertEqual(cl.compatibilidad("Limpieza > Insecticidas", self.reglas)[0], "fuera")
        self.assertEqual(cl.compatibilidad("Mundo Bebe > Alimentación", self.reglas)[0], "compatibles")
        self.assertEqual(cl.compatibilidad("Mundo Bebe > Pañales", self.reglas)[0], "fuera")

    def test_combinacion_con_reglas(self):
        df = pd.DataFrame({
            "descripcion": ["PALITOS SAB MOSTAZA", "ARMA SPAGHE 500G", "BLOCK RAYADO A4 AVON", "MAYONESA HELLMANNS 250",
                            "BIFE DE CHORIZO AL VACIO"],
            "descripciones_alternativas": [None] * 5, "es_ean": [True] * 4 + [False],
            "categoria_web": ["Almacén > Snacks > Palitos Salados", "Almacén > Pastas Secas y Salsas > Pastas Secas Largas",
                              "Hogar y textil", "Almacén > Aderezos > Mayonesas", "Carnes > Embutidos > Chorizos"],
            "categoria_origen": ["exacta", "predicha", "predicha", "predicha", "predicha"],
            "categoria_probabilidad": [1.0, 0.93, 0.99, 0.62, 0.95],
        })
        r = cl.clasificar_con_categorias(df, self.catalogo, self.reglas)
        self.assertEqual(r["alimento_id"].tolist(), ["snacks_maiz", "fideos", None, "mayonesa", "bife"])
        self.assertEqual(r.loc[1, "clasificacion_origen"], "categoría (alimento predeterminado)")
        self.assertEqual(r.loc[3, "clasificacion_origen"], "reglas y categoría")
        # Una categoría predicha no alcanza para contradecir a la regla.
        self.assertEqual(r.loc[4, "clasificacion_origen"], "reglas")

    def test_lo_que_se_vende_en_ml_no_es_un_polvo(self):
        # Polvos en mililitros y líquidos en gramos (un sobre de jugo, una leche en polvo; el smoothie de 450 g sigue
        # siendo jugo).
        alimento, motivo = cl.corregir_forma(
            pd.Series(["jugo_polvo", "jugo_polvo", "gelatina", "fideos", "jugo", "jugo", "leche_entera"]),
            pd.Series([1000.0, 18.0, 1000.0, 500.0, 126.0, 450.0, 800.0]),
            pd.Series(["ml", "g", "ml", "g", "g", "g", "g"]))
        self.assertEqual(alimento.tolist(), ["jugo", "jugo_polvo", None, "fideos", "jugo_polvo", "jugo", "leche_polvo"])
        self.assertEqual((motivo != "").tolist(), [False, False, True, False, False, False, False])

    def test_la_categoria_no_rescata_lo_que_no_es_comida(self):
        # Una pintura con el EAN de un caramelo en la web y el envase retornable de una cerveza.
        df = pd.DataFrame({
            "descripcion": ["PINTURA LATEX GRIS ACERO, TOPLINE, 1 lt", "ENVASE STELLA ARTOIS X 985 CC."],
            "descripciones_alternativas": [None] * 2, "es_ean": [True] * 2,
            "categoria_web": ["Almacén > Golosinas y Chocolates > Caramelos y Chicles", "Bebidas > Cervezas"],
            "categoria_origen": ["exacta", "exacta"], "categoria_probabilidad": [1.0, 1.0],
        })
        r = cl.clasificar_con_categorias(df, self.catalogo, self.reglas)
        self.assertEqual(r["alimento_id"].tolist(), [None, None])

    def test_nada_se_pierde_sin_motivo(self):
        # Un sándwich queda fuera de alcance; lo que la góndola dice que es comida y ninguna regla reconoce queda
        # registrado; una mezcla de frutos secos toma el predeterminado de su góndola.
        frutas_secas = "Frutas y Verduras > Frutas > Frutas Secas y Desecadas"
        df = pd.DataFrame({
            "descripcion": ["SAND. DE MILANESA CON J. Y Q. X 1 UNID.", "Tomate en Mitades Deshidratados BSA-70-gr.",
                            "MIX EUROPEO bolsa 500 gramos BSA-0.5-Kg"],
            "descripciones_alternativas": [None] * 3, "es_ean": [True] * 3,
            "categoria_web": ["Panaderia y Pasteleria > Panadería Salada", frutas_secas, frutas_secas],
            "categoria_origen": ["exacta"] * 3, "categoria_probabilidad": [1.0] * 3,
        })
        r = cl.clasificar_con_categorias(df, self.catalogo, self.reglas)
        self.assertEqual(r["alimento_id"].tolist(), [None, None, "nueces"])
        self.assertTrue(r.loc[0, "motivo_exclusion"].startswith("comida preparada"))
        self.assertTrue(r.loc[1, "motivo_exclusion"].startswith("góndola de comida"))


class TestConfianzaDeLaCategoria(unittest.TestCase):
    def test_un_producto_que_el_modelo_no_reconoce_no_tiene_confianza(self):
        # Todos los puntajes negativos: la categoría menos mala no es una certeza.
        np.testing.assert_allclose(categorias.confianza(np.array([-2.0, -0.5, 0.0, 0.6, 3.0])),
                                   [0.0, 0.25, 0.5, 0.8, 1.0])

    def test_la_descripcion_sin_la_marca(self):
        self.assertEqual(categorias._sin_marca("MORTADELA FETEADA X 150G BULNEZ", "BULNEZ"), "MORTADELA FETEADA X 150G")
        self.assertEqual(categorias._sin_marca("LECHE ULTRA CARREFOUR CLASSIC 1L", "CARREFOUR CLASSIC"), "LECHE ULTRA 1L")


if __name__ == "__main__":
    unittest.main()
