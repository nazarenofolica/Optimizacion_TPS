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

    def test_aumentar_de_peso_suma_un_superavit(self):
        base = dict(sexo="F", edad=22, peso_kg=46, altura_cm=165, actividad="liviana")
        mantener = (14.818 * 46 + 486.6) * 1.55                                      # Schofield 18-30 × PAL 1,55
        r = rq.calcular(rq.Persona(**base, objetivo="aumentar"))
        self.assertEqual(r.energia_kcal, round(mantener + cfg.SUPERAVIT_AUMENTAR_KCAL, -1))
        self.assertEqual(r.energia_kcal - rq.calcular(rq.Persona(**base)).energia_kcal, cfg.SUPERAVIT_AUMENTAR_KCAL)
        self.assertEqual(r.proteina_g_kg, cfg.PROTEINA_AUMENTAR)
        self.assertAlmostEqual(meta(r.metas, "proteinas_g").minimo, cfg.PROTEINA_AUMENTAR * 46)
        self.assertIn("Objetivo: aumentar de peso", [x["titulo"] for x in r.pasos])
        self.assertFalse(any("sobrepeso" in a for a in r.avisos))                      # IMC 16,9

    def test_aumentar_con_sobrepeso_avisa(self):
        r = rq.calcular(rq.Persona(sexo="F", edad=30, peso_kg=75, altura_cm=165, objetivo="aumentar"))  # IMC 27,5
        self.assertIn("Con un IMC de sobrepeso no se recomienda aumentar de peso; consultá a un profesional.",
                      r.avisos)
        mantener = rq.calcular(rq.Persona(sexo="F", edad=30, peso_kg=75, altura_cm=165))
        self.assertEqual(r.energia_kcal - mantener.energia_kcal, cfg.SUPERAVIT_AUMENTAR_KCAL)   # se aplica igual
        sin_altura = rq.calcular(rq.Persona(sexo="F", edad=30, peso_kg=75, objetivo="aumentar"))
        self.assertFalse(any("sobrepeso" in a for a in sin_altura.avisos))

    def test_aumentar_no_aplica_en_menores_ni_en_el_embarazo(self):
        for base in (dict(sexo="M", edad=15, peso_kg=50, altura_cm=170, actividad="moderada"),
                     dict(sexo="F", edad=30, peso_kg=50, altura_cm=165, etapa="embarazo", trimestre=2),
                     dict(sexo="F", edad=30, peso_kg=50, altura_cm=165, etapa="lactancia")):
            with self.subTest(**base):
                aumentar = rq.calcular(rq.Persona(**base, objetivo="aumentar"))
                mantener = rq.calcular(rq.Persona(**base))
                self.assertEqual(aumentar.energia_kcal, mantener.energia_kcal)
                self.assertEqual(aumentar.proteina_g_kg, mantener.proteina_g_kg)
                self.assertTrue(aumentar.avisos)                  # el aviso de que no se ajusta
                self.assertNotIn("Objetivo: aumentar de peso", [x["titulo"] for x in aumentar.pasos])

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


class TestAgua(unittest.TestCase):
    def test_meta_por_modo_y_persona(self):
        personas = {
            "adulta": (dict(sexo="F", edad=34, peso_kg=63), 2.7, 2.0),
            "adulto": (dict(sexo="M", edad=40, peso_kg=80), 3.7, 2.0),
            "chico": (dict(sexo="M", edad=8, peso_kg=27), 1.7, 1.2),
            "adolescente": (dict(sexo="M", edad=16, peso_kg=60), 3.3, 2.6),
            "embarazo": (dict(sexo="F", edad=30, peso_kg=66, etapa="embarazo", trimestre=2), 3.0, 2.3),
            "lactancia": (dict(sexo="F", edad=30, peso_kg=66, etapa="lactancia"), 3.8, 3.1),
        }
        for quien, (datos, total_l, bebidas_l) in personas.items():
            with self.subTest(persona=quien):
                p = rq.Persona(**datos)
                compra = meta(rq.calcular(p, "compra").metas, "agua")
                bebidas = meta(rq.calcular(p, "bebidas").metas, "agua")
                canilla = meta(rq.calcular(p, "canilla").metas, "agua")
                self.assertAlmostEqual(compra.minimo, total_l * 1000)
                self.assertEqual((compra.columna, compra.tipo, compra.maximo), ("agua_g", "nutriente", None))
                self.assertAlmostEqual(bebidas.minimo, bebidas_l * 1000)
                self.assertEqual((bebidas.columna, bebidas.alimentos, bebidas.tipo),
                                 (None, cfg.ALIMENTOS_AGUA, "nutriente"))
                self.assertAlmostEqual(canilla.minimo, total_l * 1000)
                self.assertEqual((canilla.columna, canilla.tipo), ("agua_g", "informativa"))
        r = rq.calcular(rq.Persona(sexo="F", edad=34, peso_kg=63))                 # canilla, la predeterminada
        self.assertEqual(meta(r.metas, "agua").tipo, "informativa")
        self.assertIn("Agua", [x["titulo"] for x in r.pasos])
        with self.assertRaises(ValueError):
            rq.calcular(rq.Persona(sexo="F", edad=34, peso_kg=63), "embotellada")

    def test_en_bebidas_no_cuenta_el_agua_de_los_alimentos(self):
        o = pd.DataFrame({"alimento_id": ["leche_entera", "agua", "soda"], "agua_g": [88.0, 99.98, 99.9],
                          "grupo_alimentario": ["Leche, yogur y queso", "Agua e infusiones", "Agua e infusiones"]})
        p = rq.Persona(sexo="F", edad=34, peso_kg=63)
        bebidas = modelo.coeficientes(o, meta(rq.calcular(p, "bebidas").metas, "agua"))
        total = modelo.coeficientes(o, meta(rq.calcular(p, "compra").metas, "agua"))
        self.assertEqual(bebidas.tolist(), [0.0, 1.0, 1.0])
        self.assertTrue(np.allclose(total, [0.88, 0.9998, 0.999]))

    def test_el_tope_de_variedad_no_limita_el_agua(self):
        # Dos porciones de 250 ml son medio litro: con ese tope, los 2 litros de bebida serían imposibles.
        o = pd.concat([_oferta_modelo(), pd.DataFrame({
            "subcategoria": ["Agua mineral y de mesa"], "grupo_alimentario": ["Agua e infusiones"],
            "alimento_id": ["agua"],
            "porcion_g": [250], "energia_kcal": [0.0], "proteinas_g": [0.0], "precio_compra": [2000.0],
            "gramos_comestibles_compra": [5000.0]}, index=["w"])])
        req = _req(60)
        agua = meta(rq.calcular(rq.Persona(sexo="F", edad=30, peso_kg=60), "bebidas").metas, "agua")
        req.metas.append(agua)
        s = modelo.resolver([(req, np.ones(4, dtype=bool))], o, dias=7)
        self.assertEqual(s.estado, "optima")
        self.assertAlmostEqual(s.dietas[0].consumo[3], 2000, delta=1)
        self.assertEqual(s.compra[3], 3)                                     # 14 litros en bidones de 5
        self.assertTrue(np.all(s.dietas[0].deficit <= 0.005))
        topes = modelo.tope_variedad(req, np.array([500.0, 250.0]), np.array([False, True]))
        self.assertEqual(topes.tolist(), [1000.0, 2000.0])
        # De la canilla (informativa) no se compra agua: no hace falta levantarle el tope.
        req.metas[-1] = meta(rq.calcular(rq.Persona(sexo="F", edad=30, peso_kg=60)).metas, "agua")
        self.assertEqual(modelo.tope_variedad(req, np.array([250.0]), np.array([True])).tolist(), [500.0])


@unittest.skipUnless(cfg.RUTA_FACT_PRECIO.exists(), "faltan las tablas de ../datos/sepa/")
class TestAguaConDatos(unittest.TestCase):
    """Con los datos reales: el oficinista en CABA, en las tres sucursales más cercanas (tiempos estimados, sin red)."""

    @classmethod
    def setUpClass(cls):
        from canasta import resultado, rutas
        cls.lat, cls.lon = -34.60386, -58.38419
        cls.persona = rq.persona_desde(next(p for p in rq.perfiles() if p["id"] == "oficinista"))
        tiempos, _ = rutas.tiempos_caminando(cls.lat, cls.lon, 15, clave="")
        cls.tiempos = dict(sorted(tiempos.items(), key=lambda kv: kv[1]["minutos"])[:3])
        cls.r = {modo: resultado.armar([cls.persona], cls.lat, cls.lon, 7, tiempos=cls.tiempos, caminata_minutos=15,
                                       agua=modo) for modo in cfg.AGUA_MODOS}

    @staticmethod
    def agua(r: dict) -> dict:
        return next(c for c in r["personas"][0]["cobertura"] if c["clave"] == "agua")

    def test_canilla_cuesta_lo_mismo_que_sin_agua(self):
        # La canasta de antes: sin agua en la oferta ni meta de agua. Mismas sucursales, mismo costo exacto.
        d = oferta.cargar()
        req = rq.calcular(self.persona)
        req.metas = [m for m in req.metas if m.clave != "agua"]
        apto, _ = oferta.aptos(d.productos, self.persona.restricciones)
        apto = (apto & ~oferta.es_agua(d.productos)).to_numpy()
        r = self.r["canilla"]
        self.assertTrue(r["sucursales"])
        for s in r["sucursales"]:
            o, por_persona = oferta.oferta_tienda(d, s["id"], [apto])
            self.assertFalse(o["alimento_id"].isin(cfg.ALIMENTOS_AGUA).any())
            antes = modelo.resolver([(req, por_persona[0])], o, 7)
            self.assertEqual(round(antes.costo, 2), s["costo"], s["bandera"])
        self.assertFalse(any(it["agua"] for it in r["ticket"]["items"]))
        self.assertEqual(self.agua(r)["estado"], "informativa")
        self.assertGreater(self.agua(r)["valor"], 0)                       # lo que aportan los alimentos
        self.assertEqual(r["catalogo"]["productos_canasta"], int((~oferta.es_agua(d.productos)).sum()))

    def test_compra_incluye_agua_y_cubre_la_meta(self):
        r = self.r["compra"]
        self.assertTrue(any(it["agua"] for it in r["ticket"]["items"]))
        agua = self.agua(r)
        self.assertEqual(agua["estado"], "cumple")
        self.assertGreaterEqual(agua["valor"], agua["minimo"] * 0.995)
        self.assertGreater(r["ticket"]["total"], self.r["canilla"]["ticket"]["total"])

    def test_bebidas_solo_cuenta_el_agua_comprada(self):
        r = self.r["bebidas"]
        agua = self.agua(r)
        tomada = sum(it["gramos_dia"] for it in r["ticket"]["items"] if it["agua"])
        self.assertEqual(agua["estado"], "cumple")
        self.assertAlmostEqual(agua["valor"], tomada, delta=1)
        self.assertAlmostEqual(agua["minimo"], 2000)


def _cobertura(clave, estado, valor, minimo=None, maximo=None, porcentaje=None, nota="", tipo="nutriente"):
    return {"clave": clave, "nombre": clave.capitalize(), "estado": estado, "valor": valor, "minimo": minimo,
            "maximo": maximo, "porcentaje": porcentaje, "nota": nota, "tipo": tipo}


class TestResumenMetas(unittest.TestCase):
    def test_cuenta_solo_las_exigidas_y_dice_cuanto_cubre(self):
        from canasta import resultado
        persona = {"datos": {"nombre": "Ana"}, "cobertura": [
            _cobertura("energia_kcal", "cumple", 1900, 1805, 1995, 100, tipo="energia"),
            _cobertura("calcio_mg", "falta", 760, 1000, 2500, 76.0),
            _cobertura("sodio_mg", "excede", 2400, None, 2000, 120.0),
            _cobertura("vitamina_d_ug", "informativa", 7, 15, 100, 46.7, tipo="informativa"),
        ], "reglas": [
            _cobertura("regla_lacteos", "falta", 0.0, 3, None, 0.0,
                       nota="la sucursal no vende ningún alimento apto que cuente para esta regla", tipo="regla"),
            _cobertura("regla_pescado", "no_aplica", None, 2, None, None, tipo="regla"),
        ]}
        sucursales = [{"costo": 100.0, "faltantes": ["Calcio"]}, {"costo": None, "faltantes": []}]
        m = resultado.resumen_metas({"personas": [persona], "sucursales": sucursales})
        self.assertEqual((m["cumple"], m["total"]), (1, 4))                    # sin la informativa ni la que no aplica
        self.assertEqual([f["clave"] for f in m["faltan"]], ["calcio_mg", "sodio_mg", "regla_lacteos"])
        self.assertEqual([f["porcentaje"] for f in m["faltan"]], [76.0, 120.0, 0.0])
        self.assertEqual([f["no_lo_vende"] for f in m["faltan"]], [False, False, True])
        self.assertEqual(m["faltan"][0]["persona"], "")                        # una sola persona: sin nombre
        self.assertTrue(m["ninguna_las_logra"])                                # la sin solución no cuenta
        self.assertEqual(m["sucursales"], 1)
        hogar = resultado.resumen_metas({"personas": [persona, persona], "sucursales": [{"costo": 1.0, "faltantes": []}]})
        self.assertEqual((hogar["cumple"], hogar["total"]), (2, 8))
        self.assertEqual(hogar["faltan"][0]["persona"], "Ana")
        self.assertFalse(hogar["ninguna_las_logra"])


@unittest.skipUnless(cfg.RUTA_FACT_PRECIO.exists(), "faltan las tablas de ../datos/sepa/")
class TestNingunaSucursalLograTodo(unittest.TestCase):
    """El primer caso en que ninguna sucursal logra todo (la demo ahora usa caso_extremo): celíaca y alérgica a la leche, el huevo, la soja, el maní y los frutos secos, solo listos
    para comer, en el centro de Córdoba a 15 min caminando (tiempos estimados, como en la página sin clave)."""

    @classmethod
    def setUpClass(cls):
        from canasta import resultado, rutas
        lat, lon = -31.41670, -64.18330
        persona = rq.persona_desde(next(p for p in rq.perfiles() if p["id"] == "restricciones_extremas"))
        tiempos, aviso = rutas.tiempos_caminando(lat, lon, 15, clave="")
        cls.r = resultado.armar([persona], lat, lon, 7, listos=True, tiempos=tiempos, caminata_minutos=15,
                                aviso_tiempos=aviso)
        cls.m = resultado.resumen_metas(cls.r)

    def test_ninguna_sucursal_cubre_todo_pero_hay_compra(self):
        self.assertNotIn("error", self.r)
        validas = [s for s in self.r["sucursales"] if s["costo"] is not None]
        self.assertGreater(len(validas), 1)
        for s in validas:
            with self.subTest(sucursal=f"{s['bandera']} {s['sucursal']}"):
                self.assertTrue(s["faltantes"])
                self.assertGreater(s["puntaje"], 0)                            # déficit ponderado de lo exigido
        self.assertIn(self.r["modelo"]["estado"], ("optima", "factible"))     # no es "sin solución"
        self.assertTrue(self.r["ticket"]["items"])
        self.assertGreater(self.r["ticket"]["total"], 0)

    def test_la_mejor_logra_casi_todas(self):
        m = self.m
        self.assertEqual(m["total"], 37)                                       # agua de la canilla: informativa
        self.assertTrue(m["ninguna_las_logra"])
        self.assertEqual(m["cumple"] + len(m["faltan"]), m["total"])
        self.assertLessEqual(len(m["faltan"]), 3)                              # pocas y entendibles
        calcio = next(f for f in m["faltan"] if f["clave"] == "calcio_mg")
        self.assertTrue(50 < calcio["porcentaje"] < 100)
        lacteos = next(f for f in m["faltan"] if f["clave"] == "regla_lacteos")
        self.assertEqual(lacteos["nombre"], "Leche, yogur y queso")
        self.assertTrue(lacteos["no_lo_vende"])


def _sucursal(precios: dict[str, float]) -> tuple[pd.DataFrame, list[np.ndarray]]:
    """La oferta de _oferta_modelo con otros precios (los mismos productos, en otra sucursal)."""
    o = _oferta_modelo()
    for p, precio in precios.items():
        o.loc[p, "precio_compra"] = precio
    return o, [np.ones(len(o), dtype=bool)]


class TestDosSuper(unittest.TestCase):
    """Compra en dos supermercados, sin datos: A es la sucursal de _oferta_modelo (fideos $100, lentejas $400, arroz
    $250) y las vecinas venden lo mismo a otros precios."""

    def test_mensaje_cuando_ahorra_pero_cubre_peor(self):
        # Ahorra más que el mínimo pero no se elige porque cubre peor las metas: no puede decir "menos del mínimo".
        from canasta import resultado
        texto = resultado._mensaje("no_conviene", None, "A", "B", ["Naranja"], 5000.0, 20.0, 1000.0, 3.0,
                                   {"cumple": 37, "total": 37}, {"cumple": 36, "total": 37})
        self.assertIn("cubrirías peor las metas", texto)
        self.assertNotIn("menos del mínimo", texto)
        texto = resultado._mensaje("no_conviene", None, "A", "B", ["Naranja"], 500.0, 2.0, 1000.0, 3.0,
                                   {"cumple": 37, "total": 37}, {"cumple": 37, "total": 37})
        self.assertIn("menos del mínimo", texto)

    def setUp(self):
        from canasta import resultado
        self.r = resultado
        self.a = _sucursal({})

    def comprado(self, s: modelo.Solucion, tienda: str) -> set[str]:
        de = s.oferta["id_tienda"].to_numpy()
        return set(s.oferta.index[(s.compra > 0) & (de == tienda)])

    def test_compra_en_b_lo_que_es_mas_barato_ahi_y_el_resto_en_a(self):
        b = _sucursal({"l": 150.0, "f": 160.0, "a": 300.0})          # en B solo las lentejas son más baratas
        s = self.r._par([_req(60)], self.a, b, "A", "B", 7)
        solo = modelo.resolver([(_req(60), TODOS)], self.a[0], 7)
        self.assertEqual(s.estado, "optima")
        self.assertEqual(self.comprado(s, "B"), {"l"})
        self.assertNotIn("l", self.comprado(s, "A"))
        self.assertTrue(self.comprado(s, "A"))                        # los fideos (o el arroz) siguen en A
        self.assertTrue(self.r._compra_en(s, "B"))
        self.assertLess(s.costo, solo.costo)
        self.assertTrue(np.all(s.dietas[0].deficit[1:] <= 0.005))   # cubre lo mismo

    def test_la_union_saca_lo_que_a_vende_igual_o_mas_barato(self):
        b = _sucursal({"l": 150.0, "f": 100.0, "a": 900.0})
        b[0].loc["q"] = b[0].loc["a"]                                 # un producto que A no vende
        b = (b[0], [np.ones(4, dtype=bool)])
        o, aptos = self.r._union(self.a, b, "A", "B")
        self.assertEqual(o[o["id_tienda"] == "B"].index.tolist(), ["l", "q"])
        self.assertEqual(o[o["id_tienda"] == "A"].index.tolist(), ["f", "l", "a"])
        self.assertEqual(len(aptos[0]), len(o))

    def test_si_b_no_aporta_es_a_sola(self):
        b = _sucursal({"l": 400.0, "f": 120.0, "a": 250.0})           # nada más barato que en A
        s = self.r._par([_req(60)], self.a, b, "A", "B", 7)
        solo = modelo.resolver([(_req(60), TODOS)], self.a[0], 7)
        self.assertFalse(self.r._compra_en(s, "B"))
        self.assertAlmostEqual(s.costo, solo.costo)
        vecina = {"id": "B", "costo": round(s.costo, 2), "puntaje": 0.0, "compra_en_b": False}
        self.assertEqual(self.r._decidir(round(solo.costo, 2), 0.0, [vecina]), ("no_conviene", None, None))

    def test_a_lo_sumo_dos_sucursales(self):
        # B tiene las lentejas más baratas y C los fideos: comprar en las tres no es una opción (cada par es A y una).
        b = _sucursal({"l": 150.0})
        c = _sucursal({"f": 50.0, "l": 300.0})
        pares = {i: self.r._par([_req(60)], self.a, o, "A", i, 7) for i, o in (("B", b), ("C", c))}
        vecinas = [{"id": i, "costo": round(s.costo, 2), "puntaje": 0.0, "compra_en_b": self.r._compra_en(s, i)}
                   for i, s in pares.items()]
        _, _, mejor = self.r._decidir(10_000.0, 0.0, vecinas)
        s = pares[mejor["id"]]
        tiendas = set(s.oferta["id_tienda"].to_numpy()[s.compra > 0])
        self.assertLessEqual(len(tiendas), cfg.DOS_SUPER_MAXIMO)
        self.assertEqual(mejor["costo"], min(v["costo"] for v in vecinas))

    def test_una_sucursal_no_cambia(self):
        # La columna de la sucursal y una vecina que no aporta nada no cambian la compra de A.
        solo = modelo.resolver([(_req(60), TODOS)], self.a[0], 7)
        con_columna = modelo.resolver([(_req(60), TODOS)], self.a[0].assign(id_tienda="A"), 7)
        igual = self.r._par([_req(60)], self.a, _sucursal({}), "A", "B", 7)
        for s in (con_columna, igual):
            self.assertEqual(s.compra.tolist(), solo.compra.tolist())
            self.assertEqual(s.costo, solo.costo)
            self.assertEqual(s.consumo.tolist(), solo.consumo.tolist())

    def test_decidir(self):
        decidir = self.r._decidir
        par = lambda costo, puntaje, en_b=True: {"id": "B", "costo": costo, "puntaje": puntaje, "compra_en_b": en_b}
        self.assertEqual(decidir(100_000.0, 0.0, []), ("sin_vecinas", None, None))
        self.assertEqual(decidir(100_000.0, 0.0, [par(90_000.0, 0.0, en_b=False)]), ("no_conviene", None, None))
        # Cubre más metas: conviene aunque cueste más (nunca se cambia nutrición por plata).
        self.assertEqual(decidir(100_000.0, 0.741, [par(110_000.0, 0.545)])[:2], ("conviene", "metas"))
        # Cubre menos: no conviene aunque sea más barato.
        self.assertEqual(decidir(100_000.0, 0.0, [par(50_000.0, 0.2)])[:2], ("no_conviene", None))
        # Igual de metas (al 1 %): decide el ahorro, que tiene que pasar el porcentaje y los pesos.
        self.assertEqual(decidir(100_000.0, 0.741, [par(97_000.0, 0.744)])[:2], ("conviene", "ahorro"))
        self.assertEqual(decidir(100_000.0, 0.0, [par(97_100.0, 0.0)])[:2], ("no_conviene", None))
        self.assertEqual(decidir(20_000.0, 0.0, [par(19_100.0, 0.0)])[:2], ("no_conviene", None))   # 4,5 %: $900
        self.assertEqual(self.r.ahorro_minimo(20_000.0), cfg.DOS_SUPER_AHORRO_MINIMO_PESOS)
        self.assertEqual(self.r.ahorro_minimo(100_000.0), 100_000.0 * cfg.DOS_SUPER_AHORRO_MINIMO_PCT / 100)
        # El mejor par: menor déficit y, a igual déficit, el más barato.
        vecinas = [{**par(95_000.0, 0.0), "id": "B"}, {**par(93_000.0, 0.0), "id": "C"},
                   {**par(80_000.0, 0.0, en_b=False), "id": "D"}]
        self.assertEqual(decidir(100_000.0, 0.0, vecinas)[2]["id"], "C")

    def test_minutos_del_circuito(self):
        tienda = lambda minutos, desde_a=None, km=None: pd.Series(
            {"minutos": minutos, "fuente_tiempo": "ruta", "minutos_desde_a": desde_a, "km_desde_a": km})
        m = self.r._circuito(tienda(8.0), tienda(6.0, 4.0, 0.25))
        self.assertEqual((m["solo_a"], m["circuito"], m["extra"], m["fuente"]), (16.0, 18.0, 2.0, "estimado"))
        self.assertEqual([t["fuente"] for t in m["tramos"]], ["ruta", "estimado", "ruta"])
        m = self.r._circuito(tienda(10.0), tienda(3.0, 2.0, 0.1))     # B queda de camino: no se camina de más
        self.assertEqual(m["extra"], 0.0)

    def test_vecinas(self):
        # A en el origen; una sucursal cada ~100 m hacia el norte (0,0009° de latitud ≈ 100 m).
        t = pd.DataFrame({"bandera": ["X", "X", "Y", "Y", "Z", "X"], "lat": [0.0, 0.0009, 0.0018, 0.0027, 0.0036, 0.09],
                          "lon": [0.0] * 6}, index=["a", "x1", "y1", "y2", "z1", "lejos"])
        v = oferta.vecinas_de(t, "a", cfg.DOS_SUPER_MINUTOS_ENTRE)
        self.assertEqual(v.index.tolist(), ["x1", "y1", "y2", "z1"])                  # "lejos": ~10 km
        self.assertTrue((v["minutos_desde_a"] <= cfg.DOS_SUPER_MINUTOS_ENTRE).all())
        self.assertAlmostEqual(v.loc["x1", "minutos_desde_a"], oferta.minutos_estimados(0.1), delta=0.05)
        # Primero la más cercana de cada otra cadena, después la de la misma cadena que A.
        self.assertEqual(oferta.elegir_vecinas(v, "X", 2).index.tolist(), ["y1", "z1"])
        self.assertEqual(oferta.elegir_vecinas(v, "X", 3).index.tolist(), ["x1", "y1", "z1"])


@unittest.skipUnless(cfg.RUTA_FACT_PRECIO.exists(), "faltan las tablas de ../datos/sepa/")
class TestDosSuperConDatos(unittest.TestCase):
    """Con los datos reales y tiempos estimados (sin red): el oficinista en el Microcentro, donde hay varias cadenas a
    pocas cuadras, y el caso que no llega a las 37 metas en el centro de Córdoba."""

    @classmethod
    def setUpClass(cls):
        import copy
        from canasta import resultado, rutas
        cls.casos = {}
        for nombre, perfil, lat, lon, listos in (("caba", "oficinista", -34.60386, -58.38419, False),
                                                  ("cordoba", "restricciones_extremas", -31.41670, -64.18330, True)):
            persona = rq.persona_desde(next(p for p in rq.perfiles() if p["id"] == perfil))
            tiempos, aviso = rutas.tiempos_caminando(lat, lon, 15, clave="")
            r = resultado.armar([persona], lat, lon, 7, listos=listos, tiempos=tiempos, caminata_minutos=15,
                                aviso_tiempos=aviso)
            antes = copy.deepcopy(r)
            cls.casos[nombre] = (r, antes, resultado.dos_super([persona], r, tiempos))

    def test_cuentas_y_forma(self):
        import json
        for nombre, (r, antes, ds) in self.casos.items():
            with self.subTest(caso=nombre):
                self.assertEqual(r, antes)                                   # no toca el resultado normal
                json.dumps(ds)                                               # se puede mandar a la página
                elegida = next(s for s in r["sucursales"] if s.get("elegida"))
                self.assertEqual((ds["a"]["id"], ds["costo_a"]), (elegida["id"], elegida["costo"]))
                self.assertLessEqual(len(ds["vecinas"]), cfg.DOS_SUPER_VECINAS)
                for v in ds["vecinas"]:
                    self.assertNotEqual(v["id"], ds["a"]["id"])
                    self.assertLessEqual(v["minutos_desde_a"], cfg.DOS_SUPER_MINUTOS_ENTRE)
                if ds["b"] is None:
                    continue
                self.assertAlmostEqual(ds["ahorro"], ds["costo_a"] - ds["costo_combinado"], places=2)
                self.assertGreaterEqual(ds["minutos"]["extra"], 0)
                self.assertEqual(ds["minutos"]["fuente"], "estimado")
                t = ds["ticket"]
                self.assertEqual([b["tienda"]["id"] for b in t["sucursales"]], [ds["a"]["id"], ds["b"]["id"]])
                self.assertAlmostEqual(sum(b["subtotal"] for b in t["sucursales"]), ds["costo_combinado"], delta=0.05)
                self.assertAlmostEqual(t["total"], ds["costo_combinado"], delta=0.05)
                for b in t["sucursales"]:
                    self.assertTrue(all(it["id_tienda"] == b["tienda"]["id"] for it in b["items"]))
                    self.assertAlmostEqual(b["subtotal"], sum(it["subtotal"] for it in b["items"]), places=2)
                self.assertTrue(t["sucursales"][1]["items"])                 # si no compra nada en B, no hay B
                self.assertEqual(ds["productos_b"],
                                 list(dict.fromkeys(it["subcategoria"] for it in t["sucursales"][1]["items"])))
                self.assertGreaterEqual(ds["metas_despues"]["cumple"], ds["metas_antes"]["cumple"])

    def test_microcentro_conviene_por_ahorro(self):
        _, _, ds = self.casos["caba"]
        self.assertEqual((ds["estado"], ds["motivo"]), ("conviene", "ahorro"))
        self.assertGreaterEqual(ds["ahorro"], ds["ahorro_minimo"])
        self.assertGreaterEqual(ds["ahorro_pct"], cfg.DOS_SUPER_AHORRO_MINIMO_PCT)
        self.assertNotEqual(ds["b"]["bandera"], ds["a"]["bandera"])
        self.assertEqual(ds["metas_despues"]["cumple"], ds["metas_despues"]["total"])
        self.assertIsNone(ds["personas"])                                    # las metas no cambian

    def test_cordoba_con_dos_super_no_llega_a_mas_metas(self):
        # Las vecinas son de la misma cadena: ninguna vende bebida vegetal apta ni más calcio.
        _, _, ds = self.casos["cordoba"]
        self.assertEqual(ds["estado"], "no_conviene")
        self.assertEqual(ds["metas_antes"]["cumple"], 35)
        self.assertTrue(all(round(v["puntaje"], 2) >= round(ds["puntaje_a"], 2) for v in ds["vecinas"]))


class TestListosParaComer(unittest.TestCase):
    def test_lo_que_hay_que_cocinar_existe_y_no_incluye_lo_listo(self):
        ids = set(pd.read_csv(cfg.DIR_REFERENCIA / "alimentos.csv", sep=";", dtype=str, encoding="utf-8-sig")["id"])
        self.assertLessEqual(cfg.ALIMENTOS_A_COCINAR, ids)
        for listo in ("manzana", "leche_entera", "yogur", "pan_frances", "atun_lata", "legumbres_lata", "nueces"):
            self.assertNotIn(listo, cfg.ALIMENTOS_A_COCINAR)


PERFILES_VISIBLES = ["deportista", "aumentar_peso", "embarazada_sin_lactosa", "adulto_mayor", "caso_extremo"]


@unittest.skipUnless(cfg.RUTA_FACT_PRECIO.exists(), "faltan las tablas de ../datos/sepa/")
class TestPerfilesVisiblesConDatos(unittest.TestCase):
    """Los cinco perfiles que ofrece la página arman una canasta con los datos reales, a 15 min caminando del
    Microcentro (tiempos estimados, como la página sin clave). El caso extremo es el de la demo: ninguna sucursal
    logra todas sus metas, pero hay compra."""

    @classmethod
    def setUpClass(cls):
        from canasta import resultado, rutas
        cls.resultado = resultado
        lat, lon = -34.60386, -58.38419
        tiempos, aviso = rutas.tiempos_caminando(lat, lon, 15, clave="")
        por_id = {p["id"]: p for p in rq.perfiles()}
        cls.r = {i: resultado.armar([rq.persona_desde(por_id[i])], lat, lon, 7, tiempos=tiempos, caminata_minutos=15,
                                    aviso_tiempos=aviso) for i in PERFILES_VISIBLES}

    def test_cada_uno_arma_una_canasta(self):
        for i, r in self.r.items():
            with self.subTest(perfil=i):
                self.assertNotIn("error", r)
                self.assertIn(r["modelo"]["estado"], ("optima", "factible"))
                self.assertTrue(r["ticket"]["items"])
                self.assertGreater(r["ticket"]["total"], 0)
                if i != "caso_extremo":
                    m = self.resultado.resumen_metas(r)
                    self.assertEqual(m["cumple"], m["total"], m["faltan"])

    def test_caso_extremo_ninguna_sucursal_logra_todo(self):
        m = self.resultado.resumen_metas(self.r["caso_extremo"])
        self.assertTrue(m["ninguna_las_logra"])
        self.assertGreater(m["sucursales"], 1)
        self.assertLessEqual(len(m["faltan"]), 2)                              # pocas y entendibles
        self.assertLess(self.r["caso_extremo"]["ticket"]["total"], 80_000)     # una semana, no un costo absurdo


class TestPerfiles(unittest.TestCase):
    def test_todos_los_perfiles_son_validos(self):
        for f in rq.perfiles():
            with self.subTest(perfil=f["id"]):
                self.assertEqual(rq.persona_desde(f).validar(), [])

    def test_columna_visible(self):
        # La página ofrece solo estos cinco; los demás siguen para los enlaces, la consola y los tests.
        todos = rq.perfiles()
        self.assertTrue(all(isinstance(f["visible"], bool) for f in todos))
        self.assertEqual([f["id"] for f in todos if f["visible"]], PERFILES_VISIBLES)
        self.assertGreater(len(todos), len(PERFILES_VISIBLES))
        self.assertEqual(len({f["id"] for f in todos}), len(todos))

    def test_perfiles_visibles_sin_metas_contradictorias(self):
        for f in rq.perfiles():
            if not f["visible"]:
                continue
            with self.subTest(perfil=f["id"]):
                for m in rq.calcular(rq.persona_desde(f)).metas:
                    if m.minimo is not None and m.maximo is not None:
                        self.assertLessEqual(m.minimo, m.maximo, m.clave)

    def test_perfiles_visibles_son_lo_que_dicen(self):
        f = {x["id"]: x for x in rq.perfiles()}
        imc = lambda x: x["peso_kg"] / (x["altura_cm"] / 100) ** 2                      # noqa: E731
        self.assertEqual((f["deportista"]["actividad"], f["deportista"]["objetivo"]), ("muy_intensa", "subir"))
        self.assertEqual(f["aumentar_peso"]["objetivo"], "aumentar")
        self.assertLess(imc(f["aumentar_peso"]), 18.5)                                   # bajo peso (OMS)
        self.assertEqual((f["embarazada_sin_lactosa"]["etapa"], f["embarazada_sin_lactosa"]["trimestre"]), ("embarazo", 2))
        self.assertEqual(set(f["adulto_mayor"]["restricciones"]), {"diabetes", "hipertension"})
        self.assertGreaterEqual(imc(f["adulto_mayor"]), 25)                              # sobrepeso
        self.assertGreaterEqual(len(f["caso_extremo"]["restricciones"]), 5)

    def test_perfil_bajo_peso(self):
        f = next(f for f in rq.perfiles() if f["id"] == "bajo_peso")
        r = rq.calcular(rq.persona_desde(f))
        self.assertEqual(f["objetivo"], "aumentar")
        self.assertLess(f["peso_kg"] / (f["altura_cm"] / 100) ** 2, 18.5)              # bajo peso (OMS)
        self.assertEqual(r.energia_kcal, round((14.818 * 46 + 486.6) * 1.55 + cfg.SUPERAVIT_AUMENTAR_KCAL, -1))


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
                      "DIAS_PERIODO", "PERSONAS_MAXIMAS", "EXCLUIDOS_SIEMPRE", "LAT_ARGENTINA", "DOS_SUPER_MAXIMO",
                      "DOS_SUPER_MINUTOS_ENTRE", "DOS_SUPER_VECINAS", "DOS_SUPER_AHORRO_MINIMO_PCT",
                      "DOS_SUPER_AHORRO_MINIMO_PESOS", "VELOCIDAD_CAMINATA_KMH", "FACTOR_DESVIO_CAMINATA"):
            self.assertIn(clave, p)
        self.assertEqual(list(p["RESTRICCIONES"]), list(cfg.RESTRICCIONES))       # el orden define los bits de aptitud


if __name__ == "__main__":
    unittest.main()
