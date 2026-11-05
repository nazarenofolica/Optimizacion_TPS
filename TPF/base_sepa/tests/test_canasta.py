"""Canasta saludable: requerimientos, tablas de referencia, restricciones y modelo de compra."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from canasta import config as cfg
from canasta import modelo, oferta
from canasta import requerimientos as rq


def meta(metas: list[rq.Meta], clave: str) -> rq.Meta:
    return next(m for m in metas if m.clave == clave)


class TestEnergia(unittest.TestCase):
    def test_adulta_sedentaria(self):
        r = rq.calcular(rq.Persona(sexo="F", edad=34, peso_kg=63, altura_cm=163, actividad="sedentaria"))
        self.assertEqual(r.energia_kcal, round((8.126 * 63 + 845.6) * 1.40, -1))     # Schofield 30-60 × PAL 1,40
        self.assertAlmostEqual(meta(r.metas, "proteinas_g").minimo, 0.8 * 63)

    def test_chicos_usan_la_ecuacion_de_gasto_total(self):
        r = rq.calcular(rq.Persona(sexo="F", edad=8, peso_kg=27, actividad="moderada"))
        esperado = (263.4 + 65.3 * 27 - 0.454 * 27 ** 2) * 1.02
        self.assertEqual(r.energia_kcal, round(esperado, -1))
        self.assertAlmostEqual(meta(r.metas, "proteinas_g").minimo, 0.95 * 27)

    def test_embarazo_y_lactancia_suman_energia(self):
        base = rq.calcular(rq.Persona(sexo="F", edad=30, peso_kg=66, actividad="liviana")).energia_kcal
        emb = rq.calcular(rq.Persona(sexo="F", edad=30, peso_kg=66, actividad="liviana", etapa="embarazo",
                                     trimestre=3)).energia_kcal
        lac = rq.calcular(rq.Persona(sexo="F", edad=30, peso_kg=66, actividad="liviana",
                                     etapa="lactancia")).energia_kcal
        self.assertAlmostEqual(emb - base, 475, delta=10)
        self.assertAlmostEqual(lac - base, 505, delta=10)

    def test_obesidad_usa_peso_ajustado(self):
        r = rq.calcular(rq.Persona(sexo="M", edad=58, peso_kg=110, altura_cm=170, actividad="sedentaria"))
        ideal = 25 * 1.70 ** 2
        self.assertAlmostEqual(r.peso_referencia_kg, ideal + 0.25 * (110 - ideal))

    def test_objetivos(self):
        base = dict(sexo="M", edad=24, peso_kg=74, actividad="muy_intensa")
        mantener = rq.calcular(rq.Persona(**base))
        subir = rq.calcular(rq.Persona(**base, objetivo="subir"))
        bajar = rq.calcular(rq.Persona(**base, objetivo="bajar"))
        self.assertGreater(subir.energia_kcal, mantener.energia_kcal)
        self.assertLess(bajar.energia_kcal, mantener.energia_kcal)
        self.assertEqual(subir.proteina_g_kg, cfg.PROTEINA_SUBIR)

    def test_validacion(self):
        with self.assertRaises(ValueError):
            rq.calcular(rq.Persona(sexo="F", edad=2, peso_kg=12))
        with self.assertRaises(ValueError):
            rq.calcular(rq.Persona(sexo="M", edad=30, peso_kg=70, etapa="embarazo", trimestre=2))
        with self.assertRaises(ValueError):
            rq.calcular(rq.Persona(sexo="F", edad=30, peso_kg=70, restricciones=["sin_gluten"]))


class TestMicronutrientes(unittest.TestCase):
    def test_hierro_por_etapa_y_dieta(self):
        mujer = rq.calcular(rq.Persona(sexo="F", edad=25, peso_kg=60))
        vegetariana = rq.calcular(rq.Persona(sexo="F", edad=25, peso_kg=60, restricciones=["vegetariano"]))
        embarazada = rq.calcular(rq.Persona(sexo="F", edad=25, peso_kg=60, etapa="embarazo", trimestre=1))
        self.assertEqual(meta(mujer.metas, "hierro_mg").minimo, 18)
        self.assertAlmostEqual(meta(vegetariana.metas, "hierro_mg").minimo, 18 * 1.8)
        self.assertEqual(meta(embarazada.metas, "hierro_mg").minimo, 27)
        self.assertEqual(meta(embarazada.metas, "hierro_mg").maximo, 45)

    def test_hipertension_y_metas_informativas(self):
        r = rq.calcular(rq.Persona(sexo="M", edad=58, peso_kg=80, restricciones=["hipertension", "vegano"]))
        self.assertEqual(meta(r.metas, "sodio_mg").maximo, cfg.SODIO_HIPERTENSION_MG)
        self.assertEqual(meta(r.metas, "vitamina_d_ug").tipo, "informativa")
        self.assertEqual(meta(r.metas, "vitamina_b12_ug").tipo, "informativa")

    def test_tabla_cubre_todas_las_edades(self):
        tabla = rq.leer_tabla(cfg.RUTA_REQUERIMIENTOS)
        for sexo in ("F", "M"):
            for edad in range(cfg.EDAD_MINIMA, cfg.EDAD_MAXIMA + 1):
                p = rq.Persona(sexo=sexo, edad=edad, peso_kg=60)
                for tipo in ("minimo", "maximo"):
                    rq._fila_etapa(tabla, p, tipo)                       # no levanta: hay fila
        for edad in range(14, 51):
            for etapa in ("embarazo", "lactancia"):
                p = rq.Persona(sexo="F", edad=edad, peso_kg=60, etapa=etapa)
                self.assertEqual(rq._fila_etapa(tabla, p, "minimo")["etapa"], etapa)

    def test_columnas_existen_en_los_datos(self):
        tabla = rq.leer_tabla(cfg.RUTA_REQUERIMIENTOS)
        columnas = set(tabla.columns) - {"tipo", "sexo", "edad_desde", "edad_hasta", "etapa"}
        self.assertLessEqual(columnas, set(oferta.NUTRIENTES) | set(oferta.DERIVADOS))
        self.assertLessEqual(columnas, set(rq.NOMBRES))


class TestReglas(unittest.TestCase):
    def test_reglas_semanales_y_escaladas(self):
        r = rq.calcular(rq.Persona(sexo="M", edad=30, peso_kg=70, actividad="moderada"))
        pescado = meta(r.metas, "regla_pescado")
        self.assertTrue(pescado.semanal)
        self.assertAlmostEqual(pescado.minimo, 2 / 7)
        self.assertAlmostEqual(meta(r.metas, "regla_aceite").minimo, 20 * r.energia_kcal / 2000)
        self.assertAlmostEqual(meta(r.metas, "regla_opcionales").maximo, 0.05 * r.energia_kcal)

    def test_alimentos_de_las_reglas_existen(self):
        ids = set(pd.read_csv(cfg.DIR_REFERENCIA / "alimentos.csv", sep=";", dtype=str, encoding="utf-8-sig")["id"])
        for m in rq._reglas(2000):
            if m.alimentos:
                self.assertLessEqual(m.alimentos, ids, m.clave)


def _productos(**cambios) -> pd.DataFrame:
    base = {
        "nombre": "X", "forma_venta": "Envase", "grupo_alimentario": "Legumbres, cereales, papa, pan y pastas",
        "nova": 1, "fuente_composicion": "alimento genérico", "puede_contener": "", "sin_tacc": "si",
        "apto_vegetariano": "si", "apto_vegano": "si", "sin_lactosa": "si", "exceso_sodio": False,
        "exceso_azucares": False, **{f"contiene_{a}": "no" for a in oferta.NOMBRE_ALERGENO},
    }
    filas = []
    for clave, valores in cambios.items():
        filas.append({**base, "id_producto": clave, **valores})
    return pd.DataFrame(filas).set_index("id_producto")


class TestRestricciones(unittest.TestCase):
    def test_celiaquia(self):
        p = _productos(
            arroz_envasado={},
            arroz_granel={"forma_venta": "Granel (precio por kg)"},
            banana_granel={"forma_venta": "Granel (precio por kg)", "grupo_alimentario": "Verduras y frutas"},
            sin_dato={"sin_tacc": "desconocido"},
            trazas={"puede_contener": "gluten, soja"},
        )
        apto, efecto = oferta.aptos(p, ["celiaquia"])
        self.assertEqual(apto[apto].index.tolist(), ["arroz_envasado", "banana_granel"])
        self.assertEqual(efecto[0]["excluye"], 3)

    def test_alergia_exige_rotulo_en_procesados(self):
        p = _productos(
            fresco={},
            procesado_sin_rotulo={"nova": 4},
            procesado_con_rotulo={"nova": 4, "fuente_composicion": "rótulo (catálogo web)"},
            trazas={"nova": 4, "fuente_composicion": "rótulo (catálogo web)", "puede_contener": "maní"},
            contiene={"contiene_mani": "si"},
        )
        apto, _ = oferta.aptos(p, ["sin_mani"])
        self.assertEqual(apto[apto].index.tolist(), ["fresco", "procesado_con_rotulo"])

    def test_vegano_y_salud(self):
        p = _productos(lenteja={}, leche={"apto_vegano": "no"}, salado={"exceso_sodio": True})
        apto, _ = oferta.aptos(p, ["vegano", "hipertension"])
        self.assertEqual(apto[apto].index.tolist(), ["lenteja"])


def _oferta_modelo() -> pd.DataFrame:
    """Tres productos: barato pero sin proteína, caro con proteína, y uno intermedio en envase grande."""
    o = pd.DataFrame({
        "subcategoria": ["Fideos", "Lentejas", "Arroz"], "grupo_alimentario": ["G"] * 3,
        "alimento_id": ["fideos", "lentejas", "arroz"], "porcion_g": [500, 500, 500],
        "energia_kcal": [350.0, 350.0, 350.0], "proteinas_g": [2.0, 25.0, 7.0],
        "precio_compra": [100.0, 400.0, 250.0], "gramos_comestibles_compra": [500.0, 500.0, 1000.0],
    }, index=["f", "l", "a"])
    return o


def _req(minimo_proteina: float) -> rq.Requerimientos:
    p = rq.Persona(sexo="F", edad=30, peso_kg=60)
    metas = [rq.Meta("energia_kcal", "Energía", "kcal", "energia_kcal", 1900, 2100, tipo="energia"),
             rq.Meta("proteinas_g", "Proteínas", "g", "proteinas_g", minimo_proteina, None, tipo="macro")]
    return rq.Requerimientos(p, 2000, 0.8, 60, metas, [], [])


TODOS = np.ones(3, dtype=bool)


class TestModelo(unittest.TestCase):
    def test_compra_entera_y_cumple(self):
        o = _oferta_modelo()
        s = modelo.resolver([(_req(60), TODOS)], o, dias=7)
        self.assertEqual(s.estado, "optima")
        self.assertTrue(np.allclose(s.compra, np.round(s.compra)))
        comprado = s.compra * o["gramos_comestibles_compra"].to_numpy()
        self.assertTrue(np.all(comprado + 1e-6 >= 7 * s.consumo))         # lo comprado alcanza
        energia = float(o["energia_kcal"].to_numpy() / 100 @ s.consumo)
        self.assertTrue(1900 - 1 <= energia <= 2100 + 1)
        self.assertTrue(np.all(s.dietas[0].deficit[1:] <= 0.005))
        self.assertAlmostEqual(s.costo, float(o["precio_compra"].to_numpy() @ s.compra))

    def test_informa_lo_que_no_se_puede_cumplir(self):
        # 2.000 kcal con 25 g de proteína cada 350 kcal dan como mucho ~143 g: 300 g es imposible.
        s = modelo.resolver([(_req(300), TODOS)], _oferta_modelo(), dias=7)
        self.assertNotEqual(s.estado, "sin_solucion")
        dieta = s.dietas[0]
        prot = next(i for i, m in enumerate(dieta.metas) if m.clave == "proteinas_g")
        self.assertGreater(dieta.deficit[prot], 0.4)

    def test_hogar_cada_uno_come_lo_suyo_y_la_compra_es_comun(self):
        o = _oferta_modelo()
        sin_lentejas = np.array([True, False, True])
        s = modelo.resolver([(_req(60), TODOS), (_req(40), sin_lentejas)], o, dias=7)
        self.assertEqual(s.estado, "optima")
        self.assertEqual(s.dietas[1].consumo[1], 0)                          # no come lo que no es apto para ella
        comprado = s.compra * o["gramos_comestibles_compra"].to_numpy()
        total = s.dietas[0].consumo + s.dietas[1].consumo
        self.assertTrue(np.all(comprado + 1e-6 >= 7 * total))               # la compra alcanza para los dos
        for dieta in s.dietas:
            energia = float(o["energia_kcal"].to_numpy() / 100 @ dieta.consumo)
            self.assertTrue(1900 - 1 <= energia <= 2100 + 1)

    def test_sin_productos_aptos_no_hay_solucion(self):
        s = modelo.resolver([(_req(60), np.zeros(3, dtype=bool))], _oferta_modelo(), dias=7)
        self.assertEqual(s.estado, "sin_solucion")

    def test_deficit_relativo(self):
        m = rq.Meta("x", "x", "g", "x", 10, 20)
        self.assertEqual(modelo.deficit_relativo(m, 15), 0)
        self.assertAlmostEqual(modelo.deficit_relativo(m, 5), 0.5)
        self.assertAlmostEqual(modelo.deficit_relativo(m, 30), 0.5)


class TestListosParaComer(unittest.TestCase):
    def test_lo_que_hay_que_cocinar_existe_y_no_incluye_lo_listo(self):
        ids = set(pd.read_csv(cfg.DIR_REFERENCIA / "alimentos.csv", sep=";", dtype=str, encoding="utf-8-sig")["id"])
        self.assertLessEqual(cfg.ALIMENTOS_A_COCINAR, ids)
        for listo in ("manzana", "leche_entera", "yogur", "pan_frances", "atun_lata", "legumbres_lata", "nueces"):
            self.assertNotIn(listo, cfg.ALIMENTOS_A_COCINAR)


class TestPerfiles(unittest.TestCase):
    def test_todos_los_perfiles_son_validos(self):
        for f in rq.perfiles():
            with self.subTest(perfil=f["id"]):
                self.assertEqual(rq.persona_desde(f).validar(), [])


class TestExportacion(unittest.TestCase):
    def test_la_pagina_tiene_los_puntos_de_insercion(self):
        from canasta.exportar import DIR_WEB
        html = (DIR_WEB / "index.html").read_text(encoding="utf-8")
        for marca in ('<link rel="stylesheet" href="estilos.css">', "<!-- DATOS -->", '<script src="app.js"></script>'):
            self.assertIn(marca, html)
        for archivo in ("app.js", "motor.js"):
            self.assertNotIn("</script", (DIR_WEB / archivo).read_text(encoding="utf-8"))

    def test_parametros_que_usa_el_motor(self):
        from canasta.exportar import parametros
        p = parametros()
        for clave in ("SCHOFIELD", "ACTIVIDAD", "RESTRICCIONES", "ALIMENTOS_A_COCINAR", "PESO_DEFICIT", "GAP_RELATIVO",
                      "DIAS_PERIODO", "PERSONAS_MAXIMAS", "EXCLUIDOS_SIEMPRE", "LAT_ARGENTINA"):
            self.assertIn(clave, p)
        self.assertEqual(list(p["RESTRICCIONES"]), list(cfg.RESTRICCIONES))       # el orden define los bits de aptitud


if __name__ == "__main__":
    unittest.main()
