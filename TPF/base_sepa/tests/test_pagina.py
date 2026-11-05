"""Paridad entre el motor de la página (canasta/web/motor.js, en Chrome headless) y el de Python.

Necesita Chrome o Edge, internet (la página baja HiGHS de jsDelivr) y las tablas de salida/; tarda alrededor de un
minuto. Por eso es opcional:  CANASTA_TEST_PAGINA=1 python -m unittest tests.test_pagina -v
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from canasta import config as cfg
from canasta import exportar, resultado
from canasta import requerimientos as rq

NAVEGADORES = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
               r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
               "google-chrome", "chromium", "chromium-browser"]
CASOS = [
    # perfiles, lugar, días, listos
    (["oficinista"], (-34.60386, -58.38419), 7, False),                    # CABA
    (["celiaca", "vegano"], (-31.41670, -64.18330), 7, False),             # Córdoba, hogar con restricciones
    (["escolar"], (-32.89785, -68.84131), 14, True),                       # Mendoza, listos para comer
]
TOLERANCIA_COSTO = 0.02      # los dos motores cortan la búsqueda entera con una brecha de 1 %


def _navegador() -> str | None:
    for n in NAVEGADORES:
        if Path(n).exists() or shutil.which(n):
            return n
    return None


@unittest.skipUnless(os.environ.get("CANASTA_TEST_PAGINA") == "1", "opcional: CANASTA_TEST_PAGINA=1")
class TestParidadPagina(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.navegador = _navegador()
        if cls.navegador is None:
            raise unittest.SkipTest("no hay Chrome ni Edge")
        if not cfg.RUTA_FACT_PRECIO.exists():
            raise unittest.SkipTest("faltan las tablas de salida/ (python -m sepa)")
        cls.dir = Path(tempfile.mkdtemp(prefix="canasta_"))
        cls.pagina = exportar.exportar(cls.dir / "canasta.html")
        cls.perfiles = {p["id"]: p for p in rq.perfiles()}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(getattr(cls, "dir", ""), ignore_errors=True)

    def _pagina(self, ids, lat, lon, dias, listos) -> dict:
        consulta = (f"perfiles={','.join(ids)}&lat={lat}&lon={lon}&dias={dias}&listos={int(listos)}&motor=pagina")
        r = subprocess.run([self.navegador, "--headless=new", "--disable-gpu", "--virtual-time-budget=600000",
                            "--dump-dom", f"{self.pagina.as_uri()}?{consulta}"],
                           capture_output=True, text=True, encoding="utf-8", timeout=900)
        m = re.search(r'<pre id="resultado-json" hidden="">(.*?)</pre>', r.stdout, re.S)
        if not m or not m.group(1).strip():
            self.skipTest("la página no llegó a calcular (¿sin conexión para bajar el solver?)")
        return json.loads(html.unescape(m.group(1)))

    def test_los_dos_motores_dan_lo_mismo(self):
        for ids, (lat, lon), dias, listos in CASOS:
            with self.subTest(perfiles=ids, dias=dias, listos=listos):
                js = self._pagina(ids, lat, lon, dias, listos)
                py = resultado.armar([rq.persona_desde(self.perfiles[i]) for i in ids], lat, lon, dias, listos=listos)
                self.assertNotIn("error", js)
                # Requerimientos idénticos: mismos números y el mismo texto de cada paso.
                for a, b in zip(py["personas"], js["personas"]):
                    self.assertEqual(a["requerimientos"]["energia_kcal"], b["requerimientos"]["energia_kcal"])
                    self.assertEqual(a["requerimientos"]["pasos"], b["requerimientos"]["pasos"])
                    self.assertEqual(a["restricciones"]["efecto"], b["restricciones"]["efecto"])
                    self.assertEqual(a["restricciones"]["productos_aptos"], b["restricciones"]["productos_aptos"])
                # Mismas sucursales, con costos dentro de la brecha y el mismo cumplimiento.
                self.assertEqual([s["id"] for s in py["sucursales"]], [s["id"] for s in js["sucursales"]])
                for a, b in zip(py["sucursales"], js["sucursales"]):
                    self.assertEqual(a["costo"] is None, b["costo"] is None, a["bandera"])
                    if a["costo"] is not None:
                        self.assertLessEqual(abs(a["costo"] - b["costo"]) / a["costo"], TOLERANCIA_COSTO, a["bandera"])
                        self.assertAlmostEqual(a["puntaje"], b["puntaje"], delta=0.02, msg=a["bandera"])
                elegida_py = next(s for s in py["sucursales"] if s.get("elegida"))
                elegida_js = next(s for s in js["sucursales"] if s.get("elegida"))
                self.assertLessEqual(abs(elegida_py["costo"] - elegida_js["costo"]) / elegida_py["costo"], TOLERANCIA_COSTO)
                if elegida_py["id"] == elegida_js["id"]:
                    for a, b in zip(py["personas"], js["personas"]):
                        estados = lambda p: [(c["clave"], c["estado"]) for c in p["cobertura"] + p["reglas"]]  # noqa: E731
                        self.assertEqual(estados(a), estados(b))


if __name__ == "__main__":
    unittest.main()
