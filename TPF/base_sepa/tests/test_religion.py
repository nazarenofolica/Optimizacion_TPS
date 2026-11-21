"""Dieta y religión: cerdo, carne, gelatina, alcohol, vino, carmín y rótulos kosher y halal (sepa/producto/religion.py)."""

from __future__ import annotations

import unittest

import pandas as pd

from sepa.producto import religion as rl


def _tabla(**productos) -> pd.DataFrame:
    base = {"nombre": "X", "marca": "", "descripcion_sepa": "", "ingredientes": None, "alimento_id": "fideos",
            "nova": 1, "apto_vegetariano": "si", "alcohol_g": 0.0}
    return pd.DataFrame([{**base, "id": k, **v} for k, v in productos.items()]).set_index("id")


class TestReligion(unittest.TestCase):
    def test_cerdo_por_alimento_nombre_e_ingredientes(self):
        r = rl.derivar(_tabla(
            bondiola={"nombre": "Bondiola de cerdo", "alimento_id": "bondiola", "apto_vegetariano": "no"},
            bife_de_chorizo={"nombre": "Bife de chorizo", "alimento_id": "bife", "apto_vegetariano": "no"},
            ravioles={"nombre": "Ravioles", "alimento_id": "pastas_rellenas", "nova": 4,
                      "ingredientes": "harina de trigo, huevo, jamón cocido, queso", "apto_vegetariano": "no"},
            medallon={"nombre": "Medallón de carne", "alimento_id": "hamburguesa", "nova": 4, "apto_vegetariano": "no",
                      "ingredientes": "carne vacuna, agua, sal, aromatizante idéntico al natural panceta"},
            galletita={"nombre": "Galletitas", "alimento_id": "galletitas_agua", "nova": 4,
                       "apto_vegetariano": "desconocido"},
            papa={"nombre": "Papa", "alimento_id": "papa"},
        ))
        self.assertEqual(r["contiene_cerdo"].to_dict(), {
            "bondiola": "si", "bife_de_chorizo": "no", "ravioles": "si", "medallon": "no",
            "galletita": "desconocido", "papa": "no"})
        # El medallón no tiene cerdo (el aromatizante es sintético) pero sí carne; la papa, nada.
        self.assertEqual(r.loc[["medallon", "bife_de_chorizo", "papa"], "contiene_carne"].tolist(), ["si", "si", "no"])

    def test_gelatina_sin_origen_puede_ser_porcina(self):
        r = rl.derivar(_tabla(
            sin_origen={"nombre": "Yogur", "alimento_id": "yogur", "nova": 3, "apto_vegetariano": "no",
                        "ingredientes": "leche entera, azúcar, gelatina, fermentos lácticos"},
            bovina={"nombre": "Yogur", "alimento_id": "yogur", "nova": 3, "apto_vegetariano": "no",
                    "ingredientes": "leche entera, azúcar, gelatina bovina, fermentos lácticos"},
            sin_lista={"nombre": "Yogur", "alimento_id": "yogur", "nova": 3, "apto_vegetariano": "desconocido"},
        ))
        self.assertEqual(r["contiene_gelatina"].tolist(), ["si", "si", "desconocido"])
        self.assertEqual(r["contiene_cerdo"].tolist(), ["desconocido", "no", "desconocido"])
        self.assertEqual(r["contiene_carne"].tolist(), ["no", "no", "desconocido"])   # la gelatina no es carne

    def test_alcohol_sin_vinagre_ni_licor_de_cacao(self):
        r = rl.derivar(_tabla(
            budin={"nombre": "Pan dulce", "alimento_id": "budin_torta", "nova": 4, "apto_vegetariano": "si",
                   "ingredientes": "harina de trigo, frutas abrillantadas, ron, azúcar, huevo"},
            conserva={"nombre": "Morrones", "alimento_id": "verduras_conserva", "nova": 3,
                      "ingredientes": "morrones, agua, vinagre de alcohol, sal"},
            chocolate={"nombre": "Chocolate", "alimento_id": "chocolate_leche", "nova": 4, "apto_vegetariano": "si",
                       "ingredientes": "azúcar, licor de cacao, leche en polvo, manteca de cacao"},
            cerveza={"nombre": "Cerveza rubia", "alimento_id": "cerveza", "nova": 3},
        ))
        self.assertEqual(r["contiene_alcohol"].tolist(), ["si", "no", "no", "si"])
        self.assertEqual(r.loc["cerveza", "contiene_vino"], "no")

    def test_procesado_sin_lista_solo_es_dudoso_si_su_alimento_lo_trae_seguido(self):
        # Dos budines con lista, uno con ron (50 %): un budín sin lista no se sabe. Las galletitas nunca lo traen.
        r = rl.derivar(_tabla(
            budin_ron={"alimento_id": "budin_torta", "nova": 4, "ingredientes": "harina de trigo, ron, azúcar"},
            budin={"alimento_id": "budin_torta", "nova": 4, "ingredientes": "harina de trigo, azúcar, huevo"},
            budin_sin_lista={"alimento_id": "budin_torta", "nova": 4},
            galletita={"alimento_id": "galletitas_agua", "nova": 4, "ingredientes": "harina de trigo, sal, aceite"},
            galletita_sin_lista={"alimento_id": "galletitas_agua", "nova": 4},
        ))
        self.assertEqual(r["contiene_alcohol"].tolist(), ["si", "no", "desconocido", "no", "no"])

    def test_vino_y_carmin_para_kosher(self):
        r = rl.derivar(_tabla(
            mermelada={"alimento_id": "mermelada_light", "nova": 3, "ingredientes": "ciruela, jugo de uva concentrado"},
            yogur={"alimento_id": "yogur", "nova": 3, "apto_vegetariano": "no",
                   "ingredientes": "leche, azúcar, colorante carmín (INS 120), almidón"},
            mermelada_antiespumante={"alimento_id": "mermelada", "nova": 3,
                                     "ingredientes": "frutilla, azúcar, antiespumante INS 900"},
        ))
        self.assertEqual(r["contiene_vino"].tolist(), ["si", "no", "no"])
        self.assertEqual(r["contiene_carmin"].tolist(), ["no", "si", "no"])

    def test_rotulos(self):
        r = rl.derivar(_tabla(
            kosher={"nombre": "Vino kosher malbec"}, parve={"ingredientes": "poroto de soja, sal. Parve"},
            koshihikari={"nombre": "Arroz koshihikari"}, halal={"marca": "Halal Foods"},
            chala={"descripcion_sepa": "CERVEZA CHALA LAND IPA"},
        ))
        self.assertEqual(r["rotulo_kosher"].tolist(), ["si", "si", "no", "no", "no"])
        self.assertEqual(r["rotulo_halal"].tolist(), ["no", "no", "no", "si", "no"])

    def test_columnas_y_estados(self):
        r = rl.derivar(_tabla(a={}, b={"nova": 4, "apto_vegetariano": "desconocido"}))
        self.assertEqual(list(r.columns), rl.COLUMNAS)
        for c in rl.COLUMNAS:
            self.assertTrue(r[c].isin({"si", "no", "desconocido"}).all(), c)


if __name__ == "__main__":
    unittest.main()
