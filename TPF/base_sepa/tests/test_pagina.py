"""Paridad entre el motor de la página (canasta/web/motor.js, en Chrome headless) y el de Python.

Necesita Chrome o Edge, internet (la página baja HiGHS de jsDelivr) y las tablas de ../datos/sepa/; tarda varios
minutos. También compara la búsqueda por tiempo caminando (con tiempos estimados: la página no lleva clave) y la compra
en dos supermercados (MotorCanasta.dosSuper contra resultado.dos_super). Por eso es opcional:
CANASTA_TEST_PAGINA=1 python -m unittest tests.test_pagina -v
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
from canasta import exportar, resultado, rutas
from canasta import requerimientos as rq

NAVEGADORES = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
               r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
               "google-chrome", "chromium", "chromium-browser"]
CASOS = [
    # perfiles, lugar, días, listos, agua
    (["oficinista"], (-34.60386, -58.38419), 7, False, "canilla"),                    # CABA
    (["celiaca", "vegano"], (-31.41670, -64.18330), 7, False, "canilla"),             # Córdoba, hogar con restricciones
    (["escolar"], (-32.89785, -68.84131), 14, True, "canilla"),                       # Mendoza, listos para comer
    (["bajo_peso"], (-32.94682, -60.63932), 7, False, "canilla"),                     # Rosario, aumentar de peso
    (["oficinista"], (-34.60386, -58.38419), 7, False, "compra"),                     # CABA, agua comprada
    (["celiaca", "escolar"], (-31.41670, -64.18330), 7, False, "bebidas"),            # Córdoba, 2 litros de bebida
    (["caso_extremo"], (-34.60386, -58.38419), 7, False, "canilla"),                  # CABA, ninguna cubre todo
    (["kosher", "halal", "anemia"], (-34.60386, -58.38419), 7, False, "canilla"),     # CABA, etapa 4: religión y
]                                                                                     # condiciones médicas
TOLERANCIA_COSTO = 0.02      # los dos motores cortan la búsqueda entera con una brecha de 1 %
CASOS_DOS_SUPER = [
    # perfiles, lugar, minutos de caminata, listos; lo que da Python
    (["oficinista"], (-34.60386, -58.38419), 15, False),                 # Microcentro: conviene, por ahorro
    (["restricciones_extremas"], (-31.41670, -64.18330), 15, True),      # Córdoba: no conviene
    (["restricciones_extremas"], (-31.41670, -64.18330), 30, True),      # Córdoba a 30 min: conviene, por metas
]
# Página mínima para la compra en dos supermercados (la interfaz todavía no la usa): los datos, el motor y rutas.js de
# la página exportada, y un guion que arma la canasta como la página (tiempos de Rutas.tiempos, sin clave: estimados)
# y después llama a MotorCanasta.dosSuper con el mismo pedido y ese resultado.
ARNES_DOS_SUPER = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>Dos supermercados</title></head><body>
<pre id="resultado-json" hidden></pre>
%(scripts)s
<script>
(async () => {
  const salida = document.getElementById("resultado-json");
  try {
    const s = document.createElement("script");
    s.textContent = document.getElementById("motor-codigo").textContent;
    document.head.appendChild(s);
    const M = window.MotorCanasta, q = new URLSearchParams(location.search);
    const resumen = await M.cargarPaquete(document.getElementById("datos-meta").textContent,
      document.getElementById("datos-binario").textContent);
    const personas = q.get("perfiles").split(",").map((id) => resumen.perfiles.find((f) => f.id === id));
    const lat = Number(q.get("lat")), lon = Number(q.get("lon")), minutos = Number(q.get("caminata"));
    const rutas = await Rutas.tiempos(resumen.parametros, { lat, lon }, M.candidatasCaminando(lat, lon, minutos));
    const pedido = { personas, lat, lon, dias: Number(q.get("dias")), listos: q.get("listos") === "1",
      agua: q.get("agua"), tiempos: rutas.tiempos, caminata_minutos: minutos, aviso_tiempos: rutas.aviso };
    const r = await M.armar(pedido);
    const ds = await M.dosSuper(pedido, r);
    salida.textContent = JSON.stringify({ resultado: r, dos_super: ds, tiempos: rutas.tiempos });
  } catch (err) {
    salida.textContent = JSON.stringify({ error: String((err && err.stack) || err) });
  }
})();
</script></body></html>
"""


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
        exportada = cls.pagina.read_text(encoding="utf-8")
        scripts = [re.search(rf'<script id="{i}"[^>]*>.*?</script>', exportada, re.S).group(0)
                   for i in ("datos-meta", "datos-binario", "motor-codigo", "config-rutas")]
        scripts.append(f"<script>\n{(exportar.DIR_WEB / 'rutas.js').read_text(encoding='utf-8')}</script>")
        cls.arnes = cls.dir / "dos_super.html"
        cls.arnes.write_text(ARNES_DOS_SUPER.replace("%(scripts)s", "\n".join(scripts)), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(getattr(cls, "dir", ""), ignore_errors=True)

    def test_busqueda_por_tiempo_caminando(self):
        # La página exportada sin clave estima los tiempos por distancia, igual que rutas.py sin clave: las mismas
        # sucursales dentro del límite y los mismos costos. El segundo es el caso de la demo en que ninguna sucursal
        # logra todas las metas (caso_extremo en el Microcentro): las dos dejan sin cubrir lo mismo.
        for ids, (lat, lon), listos in ((["oficinista"], (-34.60386, -58.38419), False),
                                        (["caso_extremo"], (-34.60386, -58.38419), False)):
            with self.subTest(perfiles=ids, listos=listos):
                minutos = 15
                js = self._pagina(ids, lat, lon, 7, listos, extra=f"&caminata={minutos}")
                tiempos, aviso = rutas.tiempos_caminando(lat, lon, minutos, clave="")
                py = resultado.armar([rq.persona_desde(self.perfiles[i]) for i in ids], lat, lon, 7, listos=listos,
                                     tiempos=tiempos, caminata_minutos=minutos, aviso_tiempos=aviso)
                self.assertEqual(js["caminata"]["fuente"], "estimado")
                self.assertEqual([s["id"] for s in py["sucursales"]], [s["id"] for s in js["sucursales"]])
                for a, b in zip(py["sucursales"], js["sucursales"]):
                    self.assertAlmostEqual(a["minutos"], b["minutos"], delta=0.11)
                    self.assertLessEqual(a["minutos"], minutos)
                    self.assertEqual(a["costo"] is None, b["costo"] is None, f"{a['id']}: {a['mensaje']} | {b['mensaje']}")
                    if a["costo"] is not None:
                        self.assertLessEqual(abs(a["costo"] - b["costo"]) / a["costo"], TOLERANCIA_COSTO, a["bandera"])
                        self.assertEqual(bool(a["faltantes"]), bool(b["faltantes"]), a["bandera"])

    def _pagina(self, ids, lat, lon, dias, listos, extra="&rutas=0", agua=cfg.AGUA_MODO_PREDETERMINADO) -> dict:
        # rutas=0: la página busca las sucursales como resultado.armar sin tiempos (las más cercanas en línea recta).
        consulta = (f"perfiles={','.join(ids)}&lat={lat}&lon={lon}&dias={dias}&listos={int(listos)}&agua={agua}"
                    f"&motor=pagina{extra}")
        return self._correr(self.pagina, consulta)

    def _correr(self, pagina: Path, consulta: str) -> dict:
        r = subprocess.run([self.navegador, "--headless=new", "--disable-gpu", "--virtual-time-budget=600000",
                            "--dump-dom", f"{pagina.as_uri()}?{consulta}"],
                           capture_output=True, text=True, encoding="utf-8", timeout=900)
        m = re.search(r'<pre id="resultado-json" hidden="">(.*?)</pre>', r.stdout, re.S)
        if not m or not m.group(1).strip():
            self.skipTest("la página no llegó a calcular (¿sin conexión para bajar el solver?)")
        return json.loads(html.unescape(m.group(1)))

    def test_dos_supermercados(self):
        # La misma búsqueda por tiempo (estimado) en los dos motores y, sobre cada resultado, la compra en dos súper.
        # La selección de vecinas y las cuentas son deterministas: mismas vecinas, minutos y decisión. Los costos, con
        # la brecha del MILP (TOLERANCIA_COSTO). Si los motores eligen B distintas, solo se acepta cuando en los dos
        # esos pares quedan dentro de esa brecha uno del otro (un empate del solver, no una lógica distinta).
        agua = cfg.AGUA_MODO_PREDETERMINADO
        for ids, (lat, lon), minutos, listos in CASOS_DOS_SUPER:
            with self.subTest(perfiles=ids, minutos=minutos, listos=listos):
                consulta = (f"perfiles={','.join(ids)}&lat={lat}&lon={lon}&dias=7&listos={int(listos)}&agua={agua}"
                            f"&caminata={minutos}")
                pagina = self._correr(self.arnes, consulta)
                self.assertNotIn("error", pagina)
                personas = [rq.persona_desde(self.perfiles[i]) for i in ids]
                tiempos, aviso = rutas.tiempos_caminando(lat, lon, minutos, clave="")
                py = resultado.armar(personas, lat, lon, 7, listos=listos, tiempos=tiempos, caminata_minutos=minutos,
                                     aviso_tiempos=aviso, agua=agua)
                a, b = resultado.dos_super(personas, py, tiempos), pagina["dos_super"]
                self.assertEqual(set(tiempos), set(pagina["tiempos"]))
                self.assertEqual(a["a"]["id"], b["a"]["id"])
                self.assertEqual(a["costo_a"], next(s["costo"] for s in py["sucursales"] if s.get("elegida")))
                self.assertLessEqual(abs(a["costo_a"] - b["costo_a"]) / a["costo_a"], TOLERANCIA_COSTO)
                self.assertEqual(a["metas_antes"]["cumple"], b["metas_antes"]["cumple"])
                self.assertEqual(a["metas_antes"]["total"], b["metas_antes"]["total"])
                # Vecinas: las mismas, en el mismo orden y a los mismos minutos de A.
                self.assertEqual([v["id"] for v in a["vecinas"]], [v["id"] for v in b["vecinas"]])
                for va, vb in zip(a["vecinas"], b["vecinas"]):
                    self.assertAlmostEqual(va["minutos_desde_a"], vb["minutos_desde_a"], delta=0.11)
                    self.assertEqual(va["costo"] is None, vb["costo"] is None, va["id"])
                    if va["costo"] is not None:
                        self.assertLessEqual(abs(va["costo"] - vb["costo"]) / va["costo"], TOLERANCIA_COSTO, va["id"])
                        self.assertAlmostEqual(va["puntaje"], vb["puntaje"], delta=0.02, msg=va["id"])
                self.assertEqual((a["estado"], a["motivo"]), (b["estado"], b["motivo"]))
                self.assertEqual(set(a), set(b))                             # la misma forma
                if a["costo_a"] == b["costo_a"]:
                    self.assertEqual(a["ahorro_minimo"], b["ahorro_minimo"])
                self.assertEqual(a["b"] is None, b["b"] is None)
                if a["b"] is None:
                    self.assertIsNone(b["ticket"])
                    if a["costo_a"] == b["costo_a"]:
                        self.assertEqual(a["mensaje"], b["mensaje"])
                    continue
                for ds in (a, b):                                           # cuentas de cada motor
                    self.assertAlmostEqual(ds["ahorro"], ds["costo_a"] - ds["costo_combinado"], places=2)
                    t = ds["ticket"]
                    self.assertEqual([x["tienda"]["id"] for x in t["sucursales"]], [ds["a"]["id"], ds["b"]["id"]])
                    self.assertAlmostEqual(sum(x["subtotal"] for x in t["sucursales"]), ds["costo_combinado"], delta=0.05)
                    self.assertAlmostEqual(t["total"], ds["costo_combinado"], delta=0.05)
                    for x in t["sucursales"]:
                        self.assertTrue(all(it["id_tienda"] == x["tienda"]["id"] for it in x["items"]))
                    self.assertEqual(ds["personas"] is None, ds["motivo"] != "metas")
                if a["b"]["id"] != b["b"]["id"]:
                    # Empate dentro de la brecha: en cada motor, el par que eligió el otro cuesta casi lo mismo.
                    for ds in (a, b):
                        costo = {v["id"]: v["costo"] for v in ds["vecinas"]}
                        self.assertLessEqual(abs(costo[a["b"]["id"]] - costo[b["b"]["id"]]) / ds["costo_combinado"],
                                             TOLERANCIA_COSTO)
                    continue
                self.assertLessEqual(abs(a["costo_combinado"] - b["costo_combinado"]) / a["costo_combinado"],
                                     TOLERANCIA_COSTO)
                self.assertLessEqual(abs(a["ahorro"] - b["ahorro"]),
                                     TOLERANCIA_COSTO * (a["costo_a"] + a["costo_combinado"]))
                self.assertAlmostEqual(a["minutos"]["extra"], b["minutos"]["extra"], delta=0.11)
                for ta, tb in zip(a["minutos"]["tramos"], b["minutos"]["tramos"]):
                    self.assertAlmostEqual(ta["minutos"], tb["minutos"], delta=0.11)
                    self.assertEqual(ta["fuente"], tb["fuente"])
                self.assertEqual(a["metas_despues"]["cumple"], b["metas_despues"]["cumple"])
                if (a["costo_a"], a["costo_combinado"]) == (b["costo_a"], b["costo_combinado"]):
                    self.assertEqual(set(a["productos_b"]), set(b["productos_b"]))
                    if a["minutos"]["extra"] == b["minutos"]["extra"]:
                        self.assertEqual(a["mensaje"], b["mensaje"])

    def test_los_dos_motores_dan_lo_mismo(self):
        for ids, (lat, lon), dias, listos, agua in CASOS:
            with self.subTest(perfiles=ids, dias=dias, listos=listos, agua=agua):
                js = self._pagina(ids, lat, lon, dias, listos, agua=agua)
                py = resultado.armar([rq.persona_desde(self.perfiles[i]) for i in ids], lat, lon, dias, listos=listos,
                                     agua=agua)
                self.assertNotIn("error", js)
                self.assertEqual(js["opciones"]["agua"], agua)
                self.assertEqual(py["catalogo"]["productos_canasta"], js["catalogo"]["productos_canasta"])
                # Requerimientos idénticos: mismos números y el mismo texto de cada paso.
                for a, b in zip(py["personas"], js["personas"]):
                    self.assertEqual(a["requerimientos"]["energia_kcal"], b["requerimientos"]["energia_kcal"])
                    self.assertEqual(a["requerimientos"]["pasos"], b["requerimientos"]["pasos"])
                    self.assertEqual(a["requerimientos"]["avisos"], b["requerimientos"]["avisos"])
                    self.assertEqual(a["restricciones"]["criterios"], b["restricciones"]["criterios"])
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
