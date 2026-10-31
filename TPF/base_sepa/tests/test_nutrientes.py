"""Controles de los rótulos y coherencia de los nutrientes por producto."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from sepa.producto import nutrientes as nu


def _rotulo(**v) -> pd.DataFrame:
    base = dict.fromkeys(["energia_kcal", "proteinas_g", "carbohidratos_g", "grasas_totales_g", "fibra_g",
                          "grasas_saturadas_g", "azucares_g", "sodio_mg"], np.nan)
    base.update(v)
    return pd.DataFrame([base])


def _control(df: pd.DataFrame, energia_generico: float = np.nan, alcohol: float = 0.0) -> str:
    return nu.controlar_rotulo(df, pd.Series([energia_generico]), pd.Series([False]),
                               pd.Series([alcohol])).iloc[0]


class TestControles(unittest.TestCase):
    def test_tabla_coherente(self):
        self.assertEqual(_control(_rotulo(energia_kcal=348, proteinas_g=7, carbohidratos_g=78, grasas_totales_g=0.6)), "")

    def test_kj_cargados_como_kcal(self):
        r = _rotulo(energia_kcal=1456, proteinas_g=7, carbohidratos_g=78, grasas_totales_g=0.6)
        self.assertEqual(_control(r), "energia_imposible")
        r = _rotulo(energia_kcal=600, proteinas_g=7, carbohidratos_g=78, grasas_totales_g=0.6)
        self.assertEqual(_control(r), "energia_inconsistente")

    def test_porcion_cargada_como_100g(self):
        # Aceite con la tabla de una cucharada (13 ml) cargada como si fuera por 100 ml.
        r = _rotulo(energia_kcal=108, proteinas_g=0, carbohidratos_g=0, grasas_totales_g=12)
        self.assertEqual(_control(r, energia_generico=884), "energia_lejos_del_generico")

    def test_cero_kcal_en_un_alimento_denso_es_redondeo(self):
        # un sazonador declara 0 kcal en su porción de 1 g: no es su composición, aunque el genérico sea exento
        r = _rotulo(energia_kcal=0, proteinas_g=0, carbohidratos_g=0, grasas_totales_g=0)
        sazonador = nu.controlar_rotulo(r, pd.Series([200.0]), pd.Series([True]), pd.Series([0.0])).iloc[0]
        self.assertEqual(sazonador, "energia_redondeada_a_cero")
        self.assertEqual(_control(r, energia_generico=18.0), "")   # una infusión: 0 kcal es posible

    def test_bebida_alcoholica_sin_macros_cierra_con_el_alcohol_del_generico(self):
        # Whisky: 222 kcal cada 100 ml = 234 cada 100 g; la web no declara el alcohol (33,4 g en el genérico).
        r = _rotulo(energia_kcal=234, proteinas_g=0, grasas_totales_g=0)
        self.assertEqual(_control(r, energia_generico=250, alcohol=33.4), "")

    def test_imposibles(self):
        self.assertEqual(_control(_rotulo(energia_kcal=1200, proteinas_g=0, carbohidratos_g=0, grasas_totales_g=100)),
                         "energia_imposible")
        r = _rotulo(energia_kcal=90, proteinas_g=1, carbohidratos_g=20, grasas_totales_g=1, grasas_saturadas_g=3)
        self.assertEqual(_control(r), "saturadas_mayor_grasas")

    def test_sodio_con_unidades_corridas(self):
        # 450.000 y 90.000 mg: microgramos cargados como miligramos; 9.000.000: imposible, vale el genérico.
        s = nu.sodio_verosimil(pd.Series([450_000.0, 90_000.0, 9_000_000.0, 300.0]),
                               pd.Series([500.0, 20.0, 20.0, 300.0]))
        self.assertEqual(s.tolist(), [450.0, 90.0, 20.0, 300.0])

    def test_fibra_contada_o_no(self):
        # Porotos (rótulo del Mercosur: la energía no cuenta la fibra) y el mismo con la fibra a 2 kcal/g (UE).
        self.assertEqual(_control(_rotulo(energia_kcal=91.5, proteinas_g=8.5, carbohidratos_g=12.3,
                                          grasas_totales_g=0.9, fibra_g=13.1)), "")
        self.assertEqual(_control(_rotulo(energia_kcal=117.7, proteinas_g=8.5, carbohidratos_g=12.3,
                                          grasas_totales_g=0.9, fibra_g=13.1)), "")

    def test_aceite_por_100ml_que_ya_es_por_100g(self):
        # 92 g de grasa cada 100 ml son 100 g cada 100 g; "100 g cada 100 ml" ya estaba por 100 g.
        t = pd.DataFrame({"grasas_totales_g": [92.0, 100.0], "energia_kcal": [828.0, 900.0]})
        r = nu._por_100g(t, np.array([True, True]), np.array([0.92, 0.92]), ["grasas_totales_g", "energia_kcal"])
        self.assertEqual(r["grasas_totales_g"].round(1).tolist(), [100.0, 100.0])
        self.assertEqual(r["energia_kcal"].round(0).tolist(), [900.0, 900.0])

    def test_perfil_central_es_un_rotulo_real(self):
        # Caldos en cubo y en polvo: las medianas sueltas (kcal de uno, macros de otro) no cierran por Atwater.
        t = pd.DataFrame({"energia_kcal": [250.0, 334.0, 290.0, 180.0, 340.0],
                          "proteinas_g": [10.0, 12.0, 11.0, 8.0, 15.0],
                          "carbohidratos_g": [30.0, 60.0, 45.0, 20.0, 50.0],
                          "grasas_totales_g": [10.0, 5.0, 7.0, 7.5, 7.0]})
        perfil = nu.perfil_central(t, list(t.columns))
        self.assertTrue((t == perfil).all(axis=1).any())
        atwater = 4 * perfil["proteinas_g"] + 4 * perfil["carbohidratos_g"] + 9 * perfil["grasas_totales_g"]
        self.assertLess(abs(perfil["energia_kcal"] - atwater), 20)

    def test_micronutriente_inverosimil_vuelve_al_generico(self):
        valores = pd.DataFrame({c: [np.nan] for c in nu.MICROS} | {"hierro_mg": [16.0]})
        generico = pd.DataFrame({c: [0.1] for c in nu.MICROS})
        gaseosa = nu.micros_verosimiles(valores, generico, pd.Series(["gaseosa_cola"]))
        cereal = nu.micros_verosimiles(valores, generico, pd.Series(["cereales_desayuno"]))
        self.assertTrue(np.isnan(gaseosa.loc[0, "hierro_mg"]))     # una gaseosa con 16 mg de hierro: error
        self.assertEqual(cereal.loc[0, "hierro_mg"], 16.0)         # un cereal fortificado: verosímil


class TestNombre(unittest.TestCase):
    def test_nombre_coincide(self):
        casos = [("YOG BEB BANANA SANCOR", "Yogur bebible banana", True),
                 ("ALMIDON DE MAIZ MAIZENA", "Maicena", True),
                 ("ARROZ LARGO FINO GALLO", "Shampoo anticaspa", False)]
        for sepa, off, esperado in casos:
            with self.subTest(sepa=sepa):
                self.assertIs(nu.nombre_coincide(sepa, off), esperado)


class TestSellos(unittest.TestCase):
    def test_gaseosa_y_fruta(self):
        n = pd.DataFrame({"energia_kcal": [42.0, 89.0], "azucares_g": [10.6, 12.2], "grasas_saturadas_g": [0, 0.1],
                          "grasas_totales_g": [0, 0.3], "sodio_mg": [10.0, 1.0]})
        s = nu.sellos(n, pd.Series(["Bebidas", "Frutas"]), pd.Series([True, False]), pd.Series([1.04, 1.0]),
                      envasado=pd.Series([True, False]), azucar_agregada=pd.Series(["si", "no"]))
        self.assertTrue(s.loc[0, "exceso_azucares"] and s.loc[0, "exceso_calorias"])
        self.assertEqual(s.loc[1, "sellos"], 0)   # la fruta fresca no lleva sellos

    def test_sin_energia_no_lleva_sellos_de_proporcion(self):
        # un té de 2 kcal con 0,1 g de azúcar y de grasa y 5 mg de sodio
        n = pd.DataFrame({"energia_kcal": [2.0], "azucares_g": [0.1], "grasas_saturadas_g": [0.05],
                          "grasas_totales_g": [0.1], "sodio_mg": [5.0]})
        s = nu.sellos(n, pd.Series(["Infusiones"]), pd.Series([False]), pd.Series([1.0]),
                      envasado=pd.Series([True]), azucar_agregada=pd.Series(["no"]))
        self.assertEqual(s.loc[0, "sellos"], 0)

    def test_polvo_para_preparar(self):
        # 100 g de jugo en polvo, sin y con azúcar: la ley mira el vaso preparado; el sodio y las calorías del
        # polvo no dicen nada, la parte de la energía que viene del azúcar no cambia al diluir
        n = pd.DataFrame({"energia_kcal": [218.0, 333.0], "azucares_g": [0.0, 60.0], "grasas_saturadas_g": [0.0, 0.0],
                          "grasas_totales_g": [0.04, 0.0], "sodio_mg": [404.0, 404.0]})
        args = (n, pd.Series(["Bebidas"] * 2), pd.Series([False] * 2), pd.Series([1.0] * 2))
        comun = dict(envasado=pd.Series([True] * 2), azucar_agregada=pd.Series(["no", "si"]))
        self.assertTrue(nu.sellos(*args, **comun).loc[0, "exceso_sodio"])
        s = nu.sellos(*args, **comun, para_preparar=pd.Series([True, True]))
        self.assertEqual(list(s["sellos"]), [0, 1])
        self.assertTrue(s.loc[1, "exceso_azucares"])


class TestSimilitud(unittest.TestCase):
    def test_sin_azucar_solo_toma_vecinos_sin_azucar(self):
        from sepa.producto import similitud
        # sin la restricción, cada objetivo tomaría al vecino de la otra condición (comparte fruta o marca)
        filas = [("MERMELADA ORIETA FRUTILLA", 260.0, 65.0, "rotulo_web")] * 5 + \
                [("MERMELADA SIN AZUCAR ORIETA DURAZNO", 120.0, 30.0, "rotulo_web")] * 5 + \
                [("MERMELADA SIN AZUCAR ORIETA FRUTILLA", 250.0, 60.0, "generico: rotulos"),
                 ("MERMELADA ORIETA DURAZNO", 250.0, 60.0, "generico: rotulos")]
        out = pd.DataFrame(filas, columns=["descripcion", "energia_kcal", "carbohidratos_g", "fuente_nutrientes"])
        out["alimento_id"] = "mermelada"
        for c in similitud.IMPUTABLES:
            if c not in out:
                out[c] = 0.0
        out["azucares_g"] = out["carbohidratos_g"]
        gen = pd.DataFrame([dict.fromkeys(similitud.IMPUTABLES, 0.0) | {"alcohol_g": 0.0}], index=["mermelada"])
        res, _ = similitud.imputar(out, out["fuente_nutrientes"].str.startswith("rotulo"), gen)
        self.assertEqual(res.loc[10, "fuente_nutrientes"], "similar")
        self.assertEqual(res.loc[10, "energia_kcal"], 120.0)
        self.assertEqual(res.loc[11, "fuente_nutrientes"], "generico: rotulos")   # ningún vecino común alcanza
        self.assertEqual(list(similitud.reducido(pd.Series(["MERM S/AZUC. DURAZNO", "YOGUR 0% GRASA",
                                                            "JUGO CLIGHT ANANA 7gr.", "JUGO POLVO PERA LIGH",
                                                            "JUGO EN POLVO BC ANANA", "QUESO S AZUL",
                                                            "MERMELADA DE DURAZNO", "JUGO TANG NARANJA 18gr."]))),
                         [True, True, True, True, True, False, False, False])


if __name__ == "__main__":
    unittest.main()
