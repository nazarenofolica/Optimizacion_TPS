"""Promociones en la canasta (etapa 5): el modelo con cada tipo de promoción (ofertas sintéticas, sin datos), lo que
cobra la caja, el ticket, la compra en dos supermercados y, con los datos, que la base sin promociones da lo mismo de
siempre y que unas promociones de prueba se aplican."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from canasta import config as cfg
from canasta import modelo, oferta
from canasta import requerimientos as rq


def _oferta() -> pd.DataFrame:
    """Fideos baratos sin proteína, lentejas caras con proteína y arroz intermedio (como test_canasta)."""
    return pd.DataFrame({
        "subcategoria": ["Fideos", "Lentejas", "Arroz"], "grupo_alimentario": ["G"] * 3,
        "alimento_id": ["fideos", "lentejas", "arroz"], "porcion_g": [500, 500, 500],
        "energia_kcal": [350.0, 350.0, 350.0], "proteinas_g": [2.0, 25.0, 7.0],
        "precio_compra": [100.0, 400.0, 250.0], "gramos_comestibles_compra": [500.0, 500.0, 1000.0],
    }, index=["f", "l", "a"])


def _con(o: pd.DataFrame, **promos: tuple) -> pd.DataFrame:
    """o con promociones aplicadas: producto=(forma, unidades, precio por unidad[, tope])."""
    o = o.assign(promo_forma=0, promo_unidades=0, promo_precio_compra=np.nan, promo_tope=np.inf)
    for p, (forma, unidades, precio, *tope) in promos.items():
        o.loc[p, ["promo_forma", "promo_unidades", "promo_precio_compra", "promo_tope"]] = [
            forma, unidades, precio, tope[0] if tope else np.inf]
    return o


def _req(proteina: float = 60) -> rq.Requerimientos:
    p = rq.Persona(sexo="F", edad=30, peso_kg=60)
    metas = [rq.Meta("energia_kcal", "Energía", "kcal", "energia_kcal", 1900, 2100, tipo="energia"),
             rq.Meta("proteinas_g", "Proteínas", "g", "proteinas_g", proteina, None, tipo="macro")]
    return rq.Requerimientos(p, 2000, 0.8, 60, metas, [], [])


TODOS = np.ones(3, dtype=bool)
PRECIO, GRUPO = 1, 2


def resolver(o: pd.DataFrame, proteina: float = 60) -> modelo.Solucion:
    return modelo.resolver([(_req(proteina), TODOS)], o, dias=7)


class TestCostoCaja(unittest.TestCase):
    def test_cada_forma(self):
        precio = np.full(5, 100.0)
        p = modelo.Promos(forma=np.array([0, 1, 1, 2, 2]), unidades=np.array([0, 1, 3, 2, 3]),
                          precio=np.array([np.nan, 75.0, 80.0, 50.0, 200 / 3]), tope=np.array([np.inf, 2, np.inf,
                                                                                              np.inf, 3]))
        # 5 unidades: de lista; 25 % hasta 2; llevando 3 a $80 c/u; 2×1 (2 grupos y una suelta); 3×2 con tope 3.
        np.testing.assert_allclose(modelo.costo_caja(precio, p, np.full(5, 5.0)), [500, 450, 400, 300, 400])
        # Con 2: el "llevando 3" no llega; el 2×1 arma un grupo.
        np.testing.assert_allclose(modelo.costo_caja(precio, p, np.full(5, 2.0)), [200, 150, 200, 100, 200])


class TestModeloConPromociones(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sin = resolver(_oferta())

    def test_sin_promociones_da_exactamente_lo_mismo(self):
        # Las columnas de promoción vacías (o una promoción que no se aplica: forma 0) no cambian nada.
        for o in (_con(_oferta()), _con(_oferta()).assign(promo_resumen="2×1", promo_aplicable=False)):
            s = resolver(o)
            self.assertEqual(s.compra.tolist(), self.sin.compra.tolist())
            self.assertEqual(s.costo, self.sin.costo)
            self.assertEqual(s.consumo.tolist(), self.sin.consumo.tolist())
            self.assertEqual(s.subtotales.tolist(), (self.sin.oferta["precio_compra"] * self.sin.compra).tolist())

    def test_2x1_compra_de_a_pares(self):
        s = resolver(_con(_oferta(), l=(GRUPO, 2, 200.0)))
        x = s.compra[1]
        self.assertGreaterEqual(x, 2)
        self.assertEqual(x % 2, 0)                                           # no deja una suelta a precio de lista
        self.assertAlmostEqual(s.subtotales[1], x / 2 * 400)
        self.assertLess(s.costo, self.sin.costo)
        self.assertAlmostEqual(s.costo, float(s.subtotales.sum()))

    def test_segunda_unidad_al_70(self):
        s = resolver(_con(_oferta(), l=(GRUPO, 2, 260.0)))                  # (1 + 0,3) / 2 × 400
        self.assertEqual(s.compra[1] % 2, 0)
        self.assertAlmostEqual(s.subtotales[1], s.compra[1] / 2 * 520)
        self.assertLess(s.costo, self.sin.costo)

    def test_llevando_3(self):
        # Llevando 3, c/u $250: 3 lentejas ($750) salen menos que 2 de lista ($800), aunque sobre.
        s = resolver(_con(_oferta(), l=(PRECIO, 3, 250.0)))
        self.assertGreaterEqual(s.compra[1], 3)
        self.assertAlmostEqual(s.subtotales[1], 250 * s.compra[1])
        self.assertLess(s.costo, self.sin.costo)

    def test_llevando_muchas_no_conviene(self):
        # Llevando 10 a $390: no conviene comprar 10 para ahorrar $10 por unidad; se compra como siempre.
        s = resolver(_con(_oferta(), l=(PRECIO, 10, 390.0)))
        self.assertEqual(s.compra.tolist(), self.sin.compra.tolist())
        self.assertAlmostEqual(s.costo, self.sin.costo)

    def test_tope_de_unidades(self):
        s = resolver(_con(_oferta(), l=(PRECIO, 1, 200.0, 1)))             # $200 una sola unidad
        self.assertGreaterEqual(s.compra[1], 2)
        self.assertAlmostEqual(s.subtotales[1], 200 + 400 * (s.compra[1] - 1))

    def test_porcentaje_baja_el_precio(self):
        s = resolver(_con(_oferta(), l=(PRECIO, 1, 300.0)))                # 25 % de descuento
        self.assertEqual(s.compra.tolist(), self.sin.compra.tolist())
        self.assertAlmostEqual(self.sin.costo - s.costo, 100 * s.compra[1])

    def test_la_promocion_nunca_empeora_las_metas(self):
        # La etapa 1 no cambia: con cualquier promoción los déficits son los mismos (con la holgura de siempre) y el
        # costo nunca sube. También cuando no se pueden cumplir todas (300 g de proteína).
        casos = [dict(l=(GRUPO, 2, 200.0)), dict(f=(GRUPO, 2, 50.0)), dict(a=(PRECIO, 3, 100.0)),
                 dict(f=(PRECIO, 1, 10.0), l=(GRUPO, 3, 270.0), a=(PRECIO, 1, 200.0, 2))]
        for proteina in (60, 300):
            sin = resolver(_oferta(), proteina)
            for promos in casos:
                with self.subTest(proteina=proteina, promos=promos):
                    s = resolver(_con(_oferta(), **promos), proteina)
                    self.assertNotEqual(s.estado, "sin_solucion")
                    np.testing.assert_array_less(s.dietas[0].deficit, sin.dietas[0].deficit + cfg.HOLGURA_DEFICIT
                                                 + 1e-6)
                    self.assertLessEqual(s.costo, sin.costo + 1e-6)


def _datos_promos(specs: list[dict], filas: list[int], precios: list[float]) -> oferta.Datos:
    """Un Datos con solo las promociones (para probar _promos_de sin la base)."""
    return oferta.Datos(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {}, "", 0, pd.DataFrame(specs),
                        np.array(filas, dtype=np.int64), np.arange(len(filas), dtype=np.int32), np.array(precios))


class TestOfertaConPromociones(unittest.TestCase):
    def setUp(self):
        self.d = _datos_promos([
            {"forma": 2, "unidades": 2, "tope": np.inf, "aplicable": True, "motivo": "", "resumen": "2×1"},
            {"forma": 0, "unidades": 0, "tope": np.inf, "aplicable": False, "motivo": "requiere un banco",
             "resumen": "20 % de descuento"},
            {"forma": 1, "unidades": 1, "tope": 6.0, "aplicable": True, "motivo": "", "resumen": "20 % de descuento"},
        ], filas=[3, 5, 8], precios=[500.0, np.nan, 1600.0])

    def test_se_aplican_solo_las_aplicables(self):
        c = oferta._promos_de(self.d, np.array([3, 4, 5, 8]), np.array([False, False, False, True]), aplicar=True)
        self.assertEqual(c["promo_forma"].tolist(), [2, 0, 0, 1])           # la del banco no entra al modelo
        self.assertEqual(c["promo_resumen"].tolist(), ["2×1", None, "20 % de descuento", "20 % de descuento"])
        self.assertEqual(c["promo_motivo"].tolist(), ["", "", "requiere un banco", ""])
        self.assertEqual(c["promo_precio_compra"][0], 500.0)
        self.assertEqual(c["promo_precio_compra"][3], 160.0)                # a granel: el precio de 100 g
        self.assertEqual(c["promo_tope"].tolist(), [np.inf, np.inf, np.inf, 6.0])

    def test_desactivadas_no_entran_pero_se_muestran(self):
        c = oferta._promos_de(self.d, np.array([3, 5]), np.array([False, False]), aplicar=False)
        self.assertEqual(c["promo_forma"].tolist(), [0, 0])
        self.assertEqual(c["promo_resumen"].tolist(), ["2×1", "20 % de descuento"])

    def test_renglon_dice_por_que_no_se_aplico(self):
        from canasta import resultado
        fila = pd.Series({"promo_resumen": "20 % de descuento", "promo_aplicable": False,
                          "promo_motivo": "requiere un banco"})
        self.assertEqual(resultado._promo_renglon(fila, 0.0, True),
                         {"resumen": "20 % de descuento", "aplicada": False, "motivo": "requiere un banco"})
        fila = pd.Series({"promo_resumen": "2×1", "promo_aplicable": True, "promo_motivo": ""})
        self.assertTrue(resultado._promo_renglon(fila, 400.0, True)["aplicada"])
        self.assertEqual(resultado._promo_renglon(fila, 0.0, False)["motivo"], "desactivaste las promociones")
        self.assertEqual(resultado._promo_renglon(fila, 0.0, True)["motivo"],
                         "la compra no llega a las unidades que pide")
        self.assertIsNone(resultado._promo_renglon(pd.Series({"promo_resumen": None}), 0.0, True))
        self.assertIsNone(resultado._promo_renglon(pd.Series({"precio": 1.0}), 0.0, True))   # base anterior

    def test_ahorro_del_ticket(self):
        from canasta import resultado
        items = [{"subtotal": 400.0, "subtotal_lista": 800.0, "promo": {"aplicada": True}},
                 {"subtotal": 250.0, "subtotal_lista": 250.0, "promo": {"aplicada": False}},
                 {"subtotal": 100.0, "subtotal_lista": 100.0, "promo": None}]
        self.assertEqual(resultado._ahorro(items), {"total_lista": 1150.0, "ahorro_promociones": 400.0,
                                                    "promociones_aplicadas": 1})


class TestDosSuperConPromociones(unittest.TestCase):
    """Cada sucursal del par aplica sus promociones: A tiene 2×1 en lentejas y B, la 2.ª al 70 % en el arroz."""

    def test_cada_sucursal_con_sus_promociones(self):
        from canasta import resultado
        a = (_con(_oferta(), l=(GRUPO, 2, 200.0)), [TODOS])
        b = (_con(_oferta().assign(precio_compra=[120.0, 450.0, 200.0]), a=(GRUPO, 2, 130.0)), [TODOS])
        s = resultado._par([_req(60)], a, b, "A", "B", 7)
        self.assertEqual(s.estado, "optima")
        de = s.oferta["id_tienda"].to_numpy()
        np.testing.assert_allclose(s.subtotales, modelo.costo_caja(s.oferta["precio_compra"].to_numpy(),
                                                                    modelo.Promos.de(s.oferta), s.compra))
        compra = dict(zip(zip(de, s.oferta.index), s.compra))
        self.assertEqual(compra.get(("B", "l"), 0), 0)                     # en A, con el 2×1, salen más baratas
        self.assertEqual(compra[("A", "l")] % 2, 0)
        solo_a = modelo.resolver([(_req(60), TODOS)], a[0], 7)
        self.assertLessEqual(s.costo, solo_a.costo + 1e-6)

    def test_union_no_saca_una_promocion_mejor(self):
        from canasta import resultado
        # B: lentejas al mismo precio pero con 2×1 (queda), fideos más caros sin promoción (sale) y arroz igual con la
        # misma promoción que A pero más cara (sale).
        a = (_con(_oferta(), a=(GRUPO, 2, 150.0)), [TODOS])
        b = (_con(_oferta().assign(precio_compra=[150.0, 400.0, 250.0]), l=(GRUPO, 2, 200.0), a=(GRUPO, 2, 160.0)),
             [TODOS])
        o, _ = resultado._union(a, b, "A", "B")
        self.assertEqual(o[o["id_tienda"] == "B"].index.tolist(), ["l"])


class TestPromocionesConDatos(unittest.TestCase):
    """Con la base del día (con la tabla promocion), el oficinista en el Microcentro: las promociones aplicables bajan
    el costo sin tocar las metas y, desactivadas, todo es a precio de lista; con una base sin la tabla nada cambia; y
    con promociones de prueba en la sucursal elegida, se aplican (y las que piden un banco, no)."""

    @classmethod
    def setUpClass(cls):
        from canasta import resultado
        if not cfg.RUTA_FACT_PRECIO.exists():
            raise unittest.SkipTest("faltan las tablas de salida/ (python -m sepa)")
        cls.r = resultado
        cls.persona = rq.persona_desde(next(p for p in rq.perfiles() if p["id"] == "oficinista"))
        cls.lugar = (-34.60386, -58.38419)
        cls.base = resultado.armar([cls.persona], *cls.lugar, 7)
        cls.sin = resultado.armar([cls.persona], *cls.lugar, 7, promos=False)

    def test_la_base_trae_promociones_aplicables(self):
        if not cfg.RUTA_PROMOCION.exists():
            self.skipTest("la base no trae la tabla promocion")
        self.assertGreater(oferta.cargar().promos_aplicables, 1000)
        self.assertTrue(self.base["opciones"]["promos"])                   # predeterminadas si la base trae
        self.assertFalse(self.sin["opciones"]["promos"])

    def test_con_promociones_no_empeoran_las_metas_ni_el_costo(self):
        if not cfg.RUTA_PROMOCION.exists():
            self.skipTest("la base no trae la tabla promocion")
        sin = {s["id"]: s for s in self.sin["sucursales"]}
        self.assertEqual([s["id"] for s in self.base["sucursales"]], list(sin))
        for s in self.base["sucursales"]:
            if s["costo"] is None:
                continue
            self.assertLessEqual(s["costo"], sin[s["id"]]["costo"] * (1 + cfg.GAP_RELATIVO) + 0.01, s["bandera"])
            self.assertLessEqual(round(s["puntaje"], 2), round(sin[s["id"]]["puntaje"], 2), s["bandera"])
        for t in (self.base["ticket"], self.sin["ticket"]):                 # las cuentas del ticket
            self.assertAlmostEqual(t["total"], sum(it["subtotal"] for it in t["items"]), places=2)
            self.assertAlmostEqual(t["total_lista"] - t["total"], t["ahorro_promociones"], places=2)
        t = self.sin["ticket"]                                              # desactivadas: precio de lista
        self.assertEqual((t["ahorro_promociones"], t["promociones_aplicadas"]), (0, 0))
        self.assertTrue(all(it["descuento"] == 0 and not (it["promo"] or {}).get("aplicada") for it in t["items"]))

    def test_sin_tabla_promocion_no_hay_promociones(self):
        if cfg.RUTA_PROMOCION.exists():
            self.skipTest("la base ya trae la tabla promocion")
        d = oferta.cargar()
        self.assertEqual((d.promos_aplicables, len(d.promo_filas)), (0, 0))
        self.assertFalse(self.base["opciones"]["promos"])
        t = self.base["ticket"]
        self.assertEqual((t["ahorro_promociones"], t["promociones_aplicadas"]), (0, 0))
        self.assertEqual(t["total"], t["total_lista"])
        self.assertTrue(all(it["promo"] is None and it["descuento"] == 0 for it in t["items"]))
        con = self.r.armar([self.persona], *self.lugar, 7, promos=True)     # pedirlas no cambia nada
        self.assertEqual([(s["id"], s["costo"]) for s in con["sucursales"]],
                         [(s["id"], s["costo"]) for s in self.base["sucursales"]])
        self.assertEqual(con["ticket"]["items"], t["items"])

    def test_promociones_de_prueba(self):
        t = self.base["ticket"]
        elegida = next(s for s in self.base["sucursales"] if s.get("elegida"))
        antes = oferta.cargar().promos_aplicables
        caros = sorted((it for it in t["items"] if not it["granel"]), key=lambda it: -it["subtotal"])
        dos_por_uno, banco = caros[0], caros[1]
        promos = pd.DataFrame([
            {"id_producto": dos_por_uno["id_producto"], "id_tienda": elegida["id"], "forma": "grupo", "unidades": 2,
             "precio_unitario": dos_por_uno["precio_unitario"] / 2, "resumen": "2×1"},
            {"id_producto": banco["id_producto"], "id_tienda": elegida["id"], "forma": "precio", "unidades": 1,
             "precio_unitario": banco["precio_unitario"] * 0.5, "resumen": "50 % de descuento", "aplicable": False,
             "motivo": "requiere un banco"}])
        with oferta.promociones_de_prueba(promos) as d:
            self.assertGreaterEqual(d.promos_aplicables, 1)
            r = self.r.armar([self.persona], *self.lugar, 7)
            sin = self.r.armar([self.persona], *self.lugar, 7, promos=False)
        self.assertEqual(oferta.cargar().promos_aplicables, antes)           # al salir, los datos de siempre
        self.assertTrue(r["opciones"]["promos"])
        nueva = next(s for s in r["sucursales"] if s["id"] == elegida["id"])
        self.assertLessEqual(nueva["costo"], elegida["costo"] * (1 + cfg.GAP_RELATIVO))
        self.assertLessEqual(round(nueva["puntaje"], 2), round(elegida["puntaje"], 2))    # las metas, igual o mejor
        self.assertEqual([(s["id"], s["costo"]) for s in sin["sucursales"]],
                         [(s["id"], s["costo"]) for s in self.sin["sucursales"]])            # desactivadas: lo de siempre
        if r["ticket"]["tienda"]["id"] != elegida["id"]:
            return
        tk = r["ticket"]
        por_id = {it["id_producto"]: it for it in tk["items"]}
        self.assertAlmostEqual(tk["total"], sum(it["subtotal"] for it in tk["items"]), places=2)
        self.assertAlmostEqual(tk["total_lista"] - tk["total"], tk["ahorro_promociones"], places=2)
        if dos_por_uno["id_producto"] in por_id:
            it = por_id[dos_por_uno["id_producto"]]
            if it["unidades_compra"] >= 2:
                self.assertEqual(it["promo"], {"resumen": "2×1", "aplicada": True, "motivo": ""})
                self.assertAlmostEqual(it["descuento"], it["unidades_compra"] // 2 * it["precio_unitario"], places=2)
                self.assertGreater(tk["ahorro_promociones"], 0)
        if banco["id_producto"] in por_id:
            self.assertEqual(por_id[banco["id_producto"]]["promo"]["motivo"], "requiere un banco")
            self.assertEqual(por_id[banco["id_producto"]]["descuento"], 0)


if __name__ == "__main__":
    unittest.main()
