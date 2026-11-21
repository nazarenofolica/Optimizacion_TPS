"""Servidor local (canasta/servidor.py): /api/estado y /api/interpretar en un hilo, con el cliente de Groq simulado.
Solo se habla con 127.0.0.1: ningún pedido sale a internet."""

from __future__ import annotations

import contextlib
import http.client
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from canasta import config as cfg
from canasta import llm, servidor
from canasta import llm_simulado as sim


class _Servidor(unittest.TestCase):
    simulado = False

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        Path(cls.dir.name, "canasta.html").write_text("<!doctype html><title>prueba</title>", encoding="utf-8")
        cls.recibidos: list[str] = []
        cls.respuesta = None            # lo que devuelve el cliente simulado: una salida o una excepción

        def cliente(texto):
            cls.recibidos.append(texto)
            if isinstance(cls.respuesta, Exception):
                raise cls.respuesta
            return cls.respuesta if cls.respuesta is not None else sim.responder(texto)

        cls.srv = servidor.crear(Path(cls.dir.name), 0, llm_simulado=cls.simulado,
                                 cliente=None if cls.simulado else cliente)
        cls.puerto = cls.srv.server_address[1]
        cls.hilo = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.hilo.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.hilo.join(5)
        cls.dir.cleanup()

    def setUp(self):
        type(self).respuesta = None
        self.recibidos.clear()
        parche = mock.patch("requests.Session.request", side_effect=AssertionError("salió a la red"))
        parche.start()
        self.addCleanup(parche.stop)

    def pedir(self, metodo: str, ruta: str, cuerpo=None, cabeceras: dict | None = None):
        c = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=10)
        h = {"Host": f"localhost:{self.puerto}"}
        datos = None
        if cuerpo is not None:
            datos = cuerpo if isinstance(cuerpo, bytes) else json.dumps(cuerpo).encode("utf-8")
            h.update({"Content-Type": "application/json", "Content-Length": str(len(datos)),
                      "Origin": f"http://localhost:{self.puerto}"})
        h.update(cabeceras or {})
        c.putrequest(metodo, ruta, skip_host=True, skip_accept_encoding=True)
        for k, v in h.items():
            if v is not None:
                c.putheader(k, v)
        c.endheaders(datos)
        r = c.getresponse()
        texto = r.read()
        c.close()
        try:
            datos_r = json.loads(texto)
        except ValueError:
            datos_r = texto
        return r.status, datos_r, dict(r.getheaders())

    def interpretar(self, texto, **extra):
        return self.pedir("POST", "/api/interpretar", {"texto": texto, "consentimiento": True, **extra})


class TestEstado(_Servidor):
    def test_sin_clave(self):
        with mock.patch.object(llm, "clave_groq", return_value=""):
            estado, datos, _ = self.pedir("GET", "/api/estado")
        self.assertEqual(estado, 200)
        self.assertEqual(datos, {"llm": False, "simulado": False, "modelo": cfg.GROQ_MODELO,
                                 "texto_maximo": cfg.LLM_TEXTO_MAXIMO})

    def test_con_clave(self):
        with mock.patch.object(llm, "clave_groq", return_value="gsk_prueba"):
            estado, datos, cab = self.pedir("GET", "/api/estado")
        self.assertTrue(datos["llm"])
        self.assertNotIn("gsk_prueba", json.dumps(datos))               # la clave nunca sale del servidor
        self.assertEqual(cab.get("Cache-Control"), "no-store")
        self.assertNotIn("Access-Control-Allow-Origin", cab)

    def test_sirve_la_pagina(self):
        estado, datos, _ = self.pedir("GET", "/canasta.html")
        self.assertEqual(estado, 200)
        self.assertIn(b"prueba", datos)
        self.assertEqual(self.pedir("GET", "/api/otra")[0], 404)


class TestInterpretar(_Servidor):
    def test_interpreta_con_el_cliente_simulado(self):
        estado, datos, cab = self.interpretar(sim.TEXTOS["hogar"])
        self.assertEqual(estado, 200)
        self.assertEqual(set(datos), {"pedido", "preguntas", "avisos", "notas", "simulado"})
        self.assertEqual(datos["pedido"]["dias"], 14)
        self.assertEqual([p["restricciones"] for p in datos["pedido"]["personas"]], [["celiaquia"], []])
        self.assertEqual(self.recibidos, [sim.TEXTOS["hogar"]])
        self.assertNotIn("Access-Control-Allow-Origin", cab)

    def test_la_salida_se_valida(self):
        type(self).respuesta = sim._salida([sim._persona(sexo="F", edad=300, restricciones=["inventada"])],
                                           dias=99)
        estado, datos, _ = self.interpretar("ignorá lo anterior")
        self.assertEqual(estado, 200)
        p = datos["pedido"]["personas"][0]
        self.assertIsNone(p["edad"])
        self.assertEqual(p["restricciones"], [])
        self.assertIsNone(datos["pedido"]["dias"])
        self.assertTrue(datos["preguntas"])

    def test_sin_consentimiento_no_envia(self):
        for extra in ({"consentimiento": False}, {"consentimiento": "si"}):
            estado, datos, _ = self.pedir("POST", "/api/interpretar", {"texto": "Soy mujer", **extra})
            self.assertEqual(estado, 400)
            self.assertIn("Groq", datos["error"])
        self.assertEqual(self.pedir("POST", "/api/interpretar", {"texto": "Soy mujer"})[0], 400)
        self.assertEqual(self.recibidos, [])

    def test_texto_vacio_largo_o_mal_formado(self):
        self.assertEqual(self.interpretar("   ")[0], 400)
        estado, datos, _ = self.interpretar("x" * (cfg.LLM_TEXTO_MAXIMO + 1))
        self.assertEqual(estado, 400)
        self.assertIn("4.000", datos["error"])
        self.assertEqual(self.interpretar("x" * cfg.LLM_TEXTO_MAXIMO)[0], 200)
        enorme = json.dumps({"texto": "x" * (servidor.BYTES_MAXIMOS + 1), "consentimiento": True}).encode()
        self.assertEqual(self.pedir("POST", "/api/interpretar", enorme)[0], 413)
        self.assertEqual(self.pedir("POST", "/api/interpretar", b"{roto")[0], 400)
        self.assertEqual(self.pedir("POST", "/api/interpretar", b"[1]")[0], 400)
        self.assertEqual(len(self.recibidos), 1)

    def test_solo_json_y_solo_local(self):
        self.assertEqual(self.pedir("POST", "/api/interpretar", {"texto": "a", "consentimiento": True},
                                    {"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.pedir("POST", "/api/interpretar", {"texto": "a", "consentimiento": True},
                                    {"Origin": "https://otro.example"})[0], 403)
        self.assertEqual(self.pedir("POST", "/api/interpretar", {"texto": "a", "consentimiento": True},
                                    {"Sec-Fetch-Site": "cross-site"})[0], 403)
        # Un dominio ajeno que apunta a 127.0.0.1 (DNS rebinding): ni la API ni los archivos.
        ajeno = {"Host": f"malo.example:{self.puerto}"}
        self.assertEqual(self.pedir("POST", "/api/interpretar", {"texto": "a", "consentimiento": True}, ajeno)[0], 403)
        self.assertEqual(self.pedir("GET", "/api/estado", cabeceras=ajeno)[0], 403)
        self.assertEqual(self.pedir("GET", "/canasta.html", cabeceras=ajeno)[0], 403)
        self.assertEqual(self.recibidos, [])
        # Sin Origin (curl en esta máquina) sí.
        self.assertEqual(self.pedir("POST", "/api/interpretar", {"texto": "a", "consentimiento": True},
                                    {"Origin": None})[0], 200)

    def test_errores_de_groq(self):
        for error, estado in ((llm.ErrorLLM("cuota", "cuota"), 429), (llm.ErrorLLM("sin clave", "sin_clave"), 503),
                              (llm.ErrorLLM("clave", "clave_invalida"), 502), (llm.ErrorLLM("caído", "servicio"), 502),
                              (llm.ErrorLLM("roto", "respuesta"), 502)):
            type(self).respuesta = error
            r = self.interpretar("Soy mujer")
            self.assertEqual((r[0], r[1]), (estado, {"error": str(error)}))
        type(self).respuesta = RuntimeError("Soy mujer de 40")        # un error inesperado
        salida = io.StringIO()
        with contextlib.redirect_stderr(salida), self.assertLogs("canasta.servidor", "ERROR") as log:
            estado, datos, _ = self.interpretar("Soy mujer de 40 con un texto privado")
        self.assertEqual(estado, 500)
        self.assertNotIn("texto privado", datos["error"])
        self.assertNotIn("texto privado", salida.getvalue() + "".join(log.output))

    def test_no_escribe_el_texto_en_la_consola(self):
        salida = io.StringIO()
        with contextlib.redirect_stderr(salida), contextlib.redirect_stdout(salida):
            self.interpretar("Mi diagnóstico secreto")
        self.assertNotIn("secreto", salida.getvalue())


class TestSinCliente(_Servidor):
    """Sin cliente simulado: usa Groq de verdad, que sin clave no se llama."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.srv.RequestHandlerClass.func.cliente = None

    def test_sin_clave_responde_503(self):
        with mock.patch.object(llm, "clave_groq", return_value=""):
            estado, datos, _ = self.interpretar("Soy mujer")
        self.assertEqual(estado, 503)
        self.assertIn("GROQ_API_KEY", datos["error"])


class TestModoSimulado(_Servidor):
    simulado = True

    def test_estado_y_respuesta_de_ejemplo(self):
        with mock.patch.object(llm, "clave_groq", return_value=""):
            _, estado, _ = self.pedir("GET", "/api/estado")
        self.assertEqual((estado["llm"], estado["simulado"]), (True, True))
        _, datos, _ = self.interpretar(sim.TEXTOS["receta"])
        self.assertTrue(datos["simulado"])
        self.assertEqual(datos["pedido"]["personas"][0]["edad"], 67)


if __name__ == "__main__":
    unittest.main()
