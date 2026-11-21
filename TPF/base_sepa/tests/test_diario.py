"""Corrida sin intervención (ETL diario): qué se baja, qué se recorre y la fecha del último ZIP de SEPA. Sin red."""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sepa import __main__ as principal
from sepa import config as cfg
from sepa.fuentes import catalogos_web
from sepa.fuentes import sepa as fs

RECURSOS = [
    {"description": "Precios SEPA Minoristas jueves, 2026-11-19", "url": "https://x/download/sepa_jueves.zip"},
    {"description": "Precios SEPA Minoristas viernes, 2026-11-20", "url": "https://x/download/sepa_viernes.zip"},
    {"description": "Precios SEPA Minoristas sabado, 2026-11-14", "url": "https://x/download/sepa_sabado.zip"},
    {"description": "Excel para decodificar el nombre de la provincia", "url": "https://x/maestro-provincias.xlsx"},
    {"description": "Anexo II, 2020-01-01", "url": "https://x/anexo.pdf"},
]


class _Respuesta:
    def __init__(self, cuerpo: dict | None = None, contenido: bytes = b""):
        self.cuerpo, self.contenido = cuerpo, contenido

    def raise_for_status(self):
        pass

    def json(self):
        return self.cuerpo

    def iter_content(self, chunk_size=1):
        yield self.contenido

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Sesion:
    """Sesión de requests simulada: la API devuelve `recursos` y cada ZIP baja `contenido`."""

    def __init__(self, recursos: list[dict]):
        self.recursos, self.pedidos = recursos, []

    def get(self, url, **kwargs):
        self.pedidos.append(url)
        if "package_show" in url:
            return _Respuesta({"result": {"resources": self.recursos}})
        return _Respuesta(contenido=b"PK zip simulado")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _args(*argv: str):
    return principal.parse_args(list(argv))


class TestUltimaFecha(unittest.TestCase):
    def test_la_mas_reciente_de_los_zip(self):
        with mock.patch.object(fs, "_sesion", return_value=_Sesion(RECURSOS)):
            self.assertEqual(fs.ultima_fecha(), "2026-11-20")

    def test_sin_zip_con_fecha_es_un_error(self):
        with mock.patch.object(fs, "_sesion", return_value=_Sesion(RECURSOS[3:])):
            with self.assertRaises(RuntimeError):
                fs.ultima_fecha()

    def test_main_solo_escribe_la_fecha(self):
        salida = io.StringIO()
        with mock.patch.object(fs, "ultima_fecha", return_value="2026-11-20"), \
                mock.patch.object(cfg, "configurar_logging"), \
                mock.patch.object(fs, "descargar_ultimo") as descargar, \
                mock.patch.object(fs, "leer_zip") as leer, contextlib.redirect_stdout(salida):
            self.assertEqual(principal.main(["--ultima-fecha"]), 0)
        self.assertEqual(salida.getvalue().strip().splitlines()[-1], "2026-11-20")
        descargar.assert_not_called()
        leer.assert_not_called()


class TestDescargarUltimo(unittest.TestCase):
    def test_baja_el_mas_reciente_y_borra_los_anteriores(self):
        with tempfile.TemporaryDirectory() as d:
            carpeta = Path(d)
            (carpeta / "sepa_2026-11-19.zip").write_bytes(b"viejo")
            sesion = _Sesion(RECURSOS)
            with mock.patch.object(fs, "_sesion", return_value=sesion):
                ruta = fs.descargar_ultimo(carpeta)
            self.assertEqual(ruta.name, "sepa_2026-11-20.zip")
            self.assertEqual(ruta.read_bytes(), b"PK zip simulado")
            self.assertEqual(sorted(p.name for p in carpeta.iterdir()), ["sepa_2026-11-20.zip"])
            self.assertIn("https://x/download/sepa_viernes.zip", sesion.pedidos)

    def test_si_ya_esta_no_lo_vuelve_a_bajar(self):
        with tempfile.TemporaryDirectory() as d:
            carpeta = Path(d)
            (carpeta / "sepa_2026-11-20.zip").write_bytes(b"ya estaba")
            sesion = _Sesion(RECURSOS)
            with mock.patch.object(fs, "_sesion", return_value=sesion):
                ruta = fs.descargar_ultimo(carpeta)
            self.assertEqual(ruta.read_bytes(), b"ya estaba")
            self.assertEqual(len(sesion.pedidos), 1)          # solo la consulta a la API


class TestPlan(unittest.TestCase):
    def test_modo_normal_no_cambia(self):
        with mock.patch.object(catalogos_web, "faltantes", return_value=["jumbo.jsonl.gz"]) as faltan:
            self.assertEqual(principal.plan(_args()), (False, False))
            self.assertEqual(principal.plan(_args("--descargar")), (True, False))
            self.assertEqual(principal.plan(_args("--actualizar-web")), (False, True))
        faltan.assert_not_called()          # solo el modo diario mira la caché

    def test_diario_con_cache_solo_descarga(self):
        with mock.patch.object(catalogos_web, "faltantes", return_value=[]):
            self.assertEqual(principal.plan(_args("--diario")), (True, False))

    def test_diario_sin_catalogos_los_recorre(self):
        with mock.patch.object(catalogos_web, "faltantes", return_value=["jumbo.jsonl.gz"]):
            self.assertEqual(principal.plan(_args("--diario")), (True, True))

    def test_diario_con_actualizar_web(self):
        with mock.patch.object(catalogos_web, "faltantes") as faltan:
            self.assertEqual(principal.plan(_args("--diario", "--actualizar-web")), (True, True))
        faltan.assert_not_called()


class TestCatalogosFaltantes(unittest.TestCase):
    def test_detecta_los_que_faltan(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(cfg, "DIR_WEB", Path(d)):
            self.assertEqual(sorted(catalogos_web.faltantes()),
                             sorted(["jumbo.jsonl.gz", "disco.jsonl.gz", "vea.jsonl.gz",
                                     "jumbo_no_alimentos.jsonl.gz"]))
            for nombre in ("jumbo", "disco", "vea", "jumbo_no_alimentos"):
                (Path(d) / f"{nombre}.jsonl.gz").write_bytes(b"")
            self.assertEqual(catalogos_web.faltantes(), [])


class TestOpenFoodFacts(unittest.TestCase):
    def test_el_volcado_se_pide_con_un_user_agent_propio(self):
        # Open Food Facts responde 403 al User-Agent de requests (pasó el 21/11/2026, en la primera corrida sin caché).
        from sepa.fuentes import openfoodfacts

        class _Flujo:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def raise_for_status(self):
                pass

            def iter_content(self, chunk_size):
                yield b"dump"

        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(cfg, "RUTA_OFF_DUMP", Path(d) / "products.csv.gz"), \
                mock.patch.object(openfoodfacts.requests, "get", return_value=_Flujo()) as get:
            ruta = openfoodfacts.asegurar_dump()
            self.assertEqual(ruta.read_bytes(), b"dump")
        agente = get.call_args.kwargs["headers"]["User-Agent"]
        self.assertFalse(agente.lower().startswith("python-requests"))


if __name__ == "__main__":
    unittest.main()
