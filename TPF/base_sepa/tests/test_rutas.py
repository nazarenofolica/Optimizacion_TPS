"""Búsqueda por tiempo caminando: servicio de rutas (simulado), selección de sucursales, exportación y ticket."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd
import requests

from canasta import config as cfg
from canasta import exportar, oferta, rutas


class _Respuesta:
    def __init__(self, estado: int, datos=None):
        self.status_code, self._datos = estado, datos

    def json(self):
        return self._datos


class _Sesion:
    """Sesión de requests falsa: guarda el pedido y devuelve la respuesta dada (o lanza la excepción)."""

    def __init__(self, respuesta):
        self.respuesta, self.pedidos = respuesta, []

    def post(self, url, json=None, headers=None, timeout=None):
        self.pedidos.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        if isinstance(self.respuesta, Exception):
            raise self.respuesta
        return self.respuesta


def _datos() -> oferta.Datos:
    """Cinco sucursales en línea sobre la latitud -34.6: A1 y A2 de la cadena A, B, C y una estación de servicio."""
    t = pd.DataFrame({
        "id_tienda": ["A1", "B1", "A2", "C1", "E1"],
        "bandera": ["A", "B", "A", "C", "E"],
        "formato": ["Supermercado"] * 4 + ["Estación de servicio"],
        "es_web": [False] * 5,
        "lat": [-34.6] * 5,
        "lon": [-58.40 + k for k in (0.002, 0.004, 0.006, 0.02, 0.001)],     # ~0,18 / 0,37 / 0,55 / 1,8 km
        "ubicacion_precision": ["exacta"] * 5,
    }).set_index("id_tienda")
    rangos = {k: (0, 1) for k in t.index}
    return oferta.Datos(pd.DataFrame(), t, pd.DataFrame(), rangos, "2026-10-23", 0)


ORIGEN = (-34.6, -58.40)


class TestServicioDeRutas(unittest.TestCase):
    def test_matriz_traduce_la_respuesta(self):
        s = _Sesion(_Respuesta(200, {"durations": [[300.0, None, 1260.0]], "distances": [[410.4, None, 1702.0]]}))
        filas = rutas.matriz_caminando(ORIGEN, [(-34.6, -58.398), (-34.6, -58.396), (-34.6, -58.38)], "clave", s)
        self.assertEqual(filas[0], {"minutos": 5.0, "metros": 410, "fuente": "ruta"})
        self.assertIsNone(filas[1])                                  # sin ruta peatonal: no se ofrece
        self.assertEqual(filas[2]["minutos"], 21.0)
        pedido = s.pedidos[0]
        self.assertTrue(pedido["url"].endswith("/v2/matrix/foot-walking"))
        self.assertEqual(pedido["headers"]["Authorization"], "clave")
        self.assertEqual(pedido["json"]["locations"][0], [ORIGEN[1], ORIGEN[0]])     # ORS usa [lon, lat]
        self.assertEqual(pedido["json"]["sources"], [0])
        self.assertEqual(pedido["json"]["destinations"], [1, 2, 3])

    def test_errores_con_mensaje_claro(self):
        casos = [(_Respuesta(401), "no es válida"), (_Respuesta(403), "no es válida"), (_Respuesta(429), "cuota"),
                 (_Respuesta(500), "(500)"), (requests.ConnectionError("x"), "conectar"),
                 (requests.Timeout("x"), "conectar"), (_Respuesta(200, {"error": "x"}), "inesperada")]
        for respuesta, texto in casos:
            with self.subTest(texto=texto), self.assertRaises(rutas.ErrorRutas) as e:
                rutas.matriz_caminando(ORIGEN, [(-34.6, -58.398)], "clave", _Sesion(respuesta))
            self.assertIn(texto, str(e.exception))

    def test_sin_clave_no_consulta(self):
        s = _Sesion(_Respuesta(200, {}))
        with self.assertRaises(rutas.ErrorRutas):
            rutas.matriz_caminando(ORIGEN, [(-34.6, -58.398)], "", s)
        self.assertEqual(s.pedidos, [])

    def test_si_falla_estima_y_avisa(self):
        with mock.patch.object(rutas.oferta, "cargar", return_value=_datos()):
            tiempos, aviso = rutas.tiempos_caminando(*ORIGEN, minutos=15, clave="x",
                                                     sesion=_Sesion(_Respuesta(429)))
        self.assertIn("cuota", aviso)
        self.assertIn("estimados", aviso)
        self.assertEqual({v["fuente"] for v in tiempos.values()}, {"estimado"})
        self.assertNotIn("E1", tiempos)                              # la estación de servicio no se evalúa
        self.assertNotIn("C1", tiempos)                              # 1,8 km: fuera del radio de 15 min (1,25 km)

    def test_con_rutas_usa_los_tiempos_reales(self):
        cuerpo = {"durations": [[120.0, 240.0, 360.0]], "distances": [[180.0, 370.0, 560.0]]}
        with mock.patch.object(rutas.oferta, "cargar", return_value=_datos()):
            tiempos, aviso = rutas.tiempos_caminando(*ORIGEN, minutos=15, clave="x",
                                                     sesion=_Sesion(_Respuesta(200, cuerpo)))
        self.assertIsNone(aviso)
        self.assertEqual(tiempos, {"A1": {"minutos": 2.0, "metros": 180, "fuente": "ruta"},
                                   "B1": {"minutos": 4.0, "metros": 370, "fuente": "ruta"},
                                   "A2": {"minutos": 6.0, "metros": 560, "fuente": "ruta"}})

    def test_leer_env(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / ".env"
            ruta.write_text("# comentario\nORS_API_KEY = 'abc123'\nOTRA=1\n\nmal formada\n", encoding="utf-8")
            self.assertEqual(rutas.leer_env(ruta), {"ORS_API_KEY": "abc123", "OTRA": "1"})
            self.assertEqual(rutas.leer_env(Path(d) / "no_existe"), {})


class TestSucursalesPorTiempo(unittest.TestCase):
    def setUp(self):
        self.d = _datos()
        self.tiempos = {"A1": {"minutos": 3, "metros": 200}, "B1": {"minutos": 6, "metros": 400},
                        "A2": {"minutos": 8, "metros": 600}, "C1": {"minutos": 24, "metros": 1900}}

    def test_excluye_las_que_superan_el_limite(self):
        t = oferta.sucursales_por_tiempo(self.d, *ORIGEN, self.tiempos, limite_min=15)
        self.assertEqual(t.index.tolist(), ["A1", "B1", "A2"])
        self.assertTrue((t["minutos"] <= 15).all())

    def test_ampliar_suma_sucursales(self):
        corto = oferta.sucursales_por_tiempo(self.d, *ORIGEN, self.tiempos, limite_min=15)
        largo = oferta.sucursales_por_tiempo(self.d, *ORIGEN, self.tiempos, limite_min=30)
        self.assertLess(set(corto.index), set(largo.index))
        self.assertIn("C1", largo.index)

    def test_una_por_cadena_primero_y_orden_por_minutos(self):
        t = oferta.sucursales_por_tiempo(self.d, *ORIGEN, self.tiempos, limite_min=30, n=3)
        self.assertEqual(t.index.tolist(), ["A1", "B1", "C1"])        # A2 queda afuera: A ya está representada
        self.assertEqual(t["minutos"].tolist(), sorted(t["minutos"]))

    def test_sin_ninguna_dentro_del_limite(self):
        self.assertTrue(oferta.sucursales_por_tiempo(self.d, *ORIGEN, self.tiempos, limite_min=1).empty)

    def test_candidatas_dentro_del_radio(self):
        c = oferta.candidatas_caminando(self.d, *ORIGEN, minutos=15)
        self.assertEqual(c.index.tolist(), ["A1", "B1", "A2"])
        self.assertAlmostEqual(oferta.radio_caminata_km(15), 1.25)
        self.assertIn("C1", oferta.candidatas_caminando(self.d, *ORIGEN, minutos=30).index)

    def test_estimacion(self):
        self.assertAlmostEqual(oferta.minutos_estimados(1.0), 1.3 / 5.0 * 60)


class TestExportacionRutas(unittest.TestCase):
    def test_config_rutas(self):
        self.assertIn('"clave": ""', exportar._config_rutas(None))
        self.assertIn('"clave": "abc"', exportar._config_rutas("abc"))
        with self.assertRaises(RuntimeError):
            exportar._config_rutas("</script>")

    def test_la_pagina_incluye_rutas_js(self):
        html = (exportar.DIR_WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn('<script src="rutas.js"></script>', html)
        self.assertNotIn("</script", (exportar.DIR_WEB / "rutas.js").read_text(encoding="utf-8"))

    def test_parametros_de_caminata(self):
        p = exportar.parametros()
        for clave in ("CAMINATA_MINUTOS", "CAMINATA_OPCIONES", "VELOCIDAD_CAMINATA_KMH", "FACTOR_DESVIO_CAMINATA",
                      "CANDIDATAS_MAXIMAS_RUTEO", "SUCURSALES_A_EVALUAR_CAMINATA", "RUTEO_SERVIDOR", "RUTEO_PERFIL",
                      "RUTEO_TIEMPO_ESPERA_S"):
            self.assertIn(clave, p)
        self.assertIn(cfg.CAMINATA_MINUTOS, cfg.CAMINATA_OPCIONES)
        self.assertNotIn("ORS_API_KEY", str(p))


@unittest.skipUnless(cfg.RUTA_FACT_PRECIO.exists(), "faltan las tablas de ../datos/sepa/")
class TestCanastaPorTiempo(unittest.TestCase):
    """Con los datos reales y tiempos estimados (sin red): límite respetado y cuentas del ticket."""

    @classmethod
    def setUpClass(cls):
        from canasta import resultado
        from canasta import requerimientos as rq
        cls.lat, cls.lon = -34.60386, -58.38419
        persona = rq.persona_desde(next(p for p in rq.perfiles() if p["id"] == "oficinista"))
        tiempos, aviso = rutas.tiempos_caminando(cls.lat, cls.lon, 15, clave="")
        cls.r = resultado.armar([persona], cls.lat, cls.lon, 7, tiempos=tiempos, caminata_minutos=15,
                                aviso_tiempos=aviso)
        cls.vacio = resultado.armar([persona], cls.lat, cls.lon, 7, tiempos=tiempos, caminata_minutos=0.5)

    def test_solo_sucursales_dentro_del_limite(self):
        self.assertTrue(self.r["sucursales"])
        for s in self.r["sucursales"]:
            self.assertLessEqual(s["minutos"], 15)
            self.assertEqual(s["fuente_tiempo"], "estimado")
        self.assertEqual(self.r["caminata"]["fuente"], "estimado")
        self.assertIn("estimados", self.r["caminata"]["aviso"])
        self.assertIsNotNone(self.r["ticket"]["tienda"]["minutos"])

    def test_cuentas_del_ticket(self):
        t = self.r["ticket"]
        self.assertAlmostEqual(sum(it["subtotal"] for it in t["items"]), t["total"], places=2)
        for it in t["items"]:
            # subtotal = unidades × precio del envase (a granel: pasos de 100 g × precio por kg / 10)
            precio_compra = it["precio_unitario"] * (cfg.PASO_GRANEL_G / 1000 if it["granel"] else 1)
            self.assertAlmostEqual(it["subtotal"], it["unidades_compra"] * precio_compra,
                                   delta=0.02 + 0.005 * it["unidades_compra"])
        self.assertAlmostEqual(t["costo_diario"], t["total"] / 7, places=1)

    def test_sin_sucursales_en_el_limite(self):
        self.assertTrue(self.vacio.get("sin_sucursales"))
        self.assertIn("minutos caminando", self.vacio["error"])


if __name__ == "__main__":
    unittest.main()
