"""
Servidor local de la página (python -m canasta), con la biblioteca estándar: sirve la carpeta de la página exportada y
dos rutas para "Contalo con tus palabras" (etapa 6), que necesitan la clave de Groq y por eso no pueden estar en la
página:

    GET  /api/estado       {llm, simulado, modelo, texto_maximo}: llm es true si hay GROQ_API_KEY (o en modo simulado)
    POST /api/interpretar  {texto, consentimiento: true} -> {pedido, preguntas, avisos, notas, simulado} o {error}

Solo atiende a esta máquina: escucha en 127.0.0.1, rechaza pedidos de otra dirección o con otro Host (protege de un
sitio que apunte su dominio a 127.0.0.1) y, en /api/interpretar, exige Content-Type application/json y un Origin de
localhost si viene: así otra página abierta en el navegador no puede usarlo (no hay CORS: sin las cabeceras, el
navegador no le deja leer la respuesta, y el JSON obliga a una consulta previa que este servidor no acepta). El texto no
se guarda ni se escribe en el log; tiene un tope de config.LLM_TEXTO_MAXIMO caracteres.

La lógica está en canasta/llm.py, separada del servidor: en producción la puede envolver un backend propio (FastAPI)
sin cambiarla.
"""

from __future__ import annotations

import functools
import http.server
import json
import logging
import threading
import webbrowser
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from canasta import config as cfg
from canasta import llm

logger = logging.getLogger("canasta.servidor")

LOCALES = {"127.0.0.1", "::1", "localhost"}
BYTES_MAXIMOS = 64 * 1024        # el texto llega en JSON: 4.000 caracteres son, como mucho, ~24 KB escapados
ESTADO_HTTP = {"sin_clave": 503, "cuota": 429, "texto": 400}


class Manejador(http.server.SimpleHTTPRequestHandler):
    """Archivos de la carpeta de la página y la API. llm_simulado: responde con canasta/llm_simulado, sin red."""

    cliente: Callable[[str], dict] | None = None     # en lugar de Groq (modo simulado o tests)
    simulado = False

    def log_message(self, *args):  # noqa: D102 - sin una línea por pedido en la consola (y nada del texto)
        pass

    # ------------------------------------------------------------
    def _local(self) -> bool:
        host = urlsplit(f"//{self.headers.get('Host', '')}").hostname or ""
        return self.client_address[0] in LOCALES and host in LOCALES

    def _json(self, estado: int, datos: dict) -> None:
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(estado)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _error(self, estado: int, mensaje: str) -> None:
        self._json(estado, {"error": mensaje})

    # ------------------------------------------------------------
    def do_GET(self):  # noqa: N802 - nombre de http.server
        if not self._local():          # también los archivos: canasta_local.html lleva la clave de rutas
            return self._error(403, "Solo se atiende desde esta máquina.")
        if self.path.split("?")[0].startswith("/api/"):
            if self.path.split("?")[0] != "/api/estado":
                return self._error(404, "No existe.")
            return self._json(200, {"llm": self.simulado or bool(llm.clave_groq()), "simulado": self.simulado,
                                    "modelo": cfg.GROQ_MODELO, "texto_maximo": cfg.LLM_TEXTO_MAXIMO})
        return super().do_GET()

    def do_POST(self):  # noqa: N802
        if self.path.split("?")[0] != "/api/interpretar":
            return self._error(404, "No existe.")
        if not self._local():
            return self._error(403, "Solo se atiende desde esta máquina.")
        origen = self.headers.get("Origin")
        if origen and (urlsplit(origen).hostname or "") not in LOCALES:
            return self._error(403, "Solo se atiende a la página local.")
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            return self._error(403, "Solo se atiende a la página local.")
        if not (self.headers.get("Content-Type") or "").lower().startswith("application/json"):
            return self._error(415, "El pedido tiene que ser JSON.")
        try:
            largo = int(self.headers.get("Content-Length") or "")
        except ValueError:
            return self._error(411, "Falta el largo del pedido.")
        if largo > BYTES_MAXIMOS:
            return self._error(413, f"El texto tiene más de {cfg.LLM_TEXTO_MAXIMO:,} caracteres: acortalo."
                               .replace(",", "."))
        try:
            datos = json.loads(self.rfile.read(largo).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return self._error(400, "El pedido no es un JSON válido.")
        if not isinstance(datos, dict):
            return self._error(400, "El pedido no es un JSON válido.")
        if datos.get("consentimiento") is not True:
            return self._error(400, "Falta confirmar que el texto se puede enviar a Groq.")
        try:
            r = llm.interpretar(datos.get("texto"), cliente=self.cliente)
        except llm.ErrorLLM as e:
            return self._error(ESTADO_HTTP.get(e.codigo, 502), str(e))
        except Exception:                      # noqa: BLE001 - sin el texto en el log
            logger.exception("Error al interpretar el texto")
            return self._error(500, "No se pudo interpretar el texto: probá de nuevo.")
        return self._json(200, {**r, "simulado": self.simulado})


def crear(carpeta: Path, puerto: int, llm_simulado: bool = False,
          cliente: Callable[[str], dict] | None = None) -> http.server.ThreadingHTTPServer:
    """Un servidor (sin arrancar) para la carpeta. Si el puerto está ocupado, toma uno libre."""
    if llm_simulado and cliente is None:
        from canasta import llm_simulado as sim
        cliente = sim.responder
    manejador_cls = type("ManejadorCanasta", (Manejador,), {"cliente": staticmethod(cliente) if cliente else None,
                                                             "simulado": llm_simulado})
    manejador = functools.partial(manejador_cls, directory=str(carpeta))
    try:
        return http.server.ThreadingHTTPServer(("127.0.0.1", puerto), manejador)
    except OSError:
        return http.server.ThreadingHTTPServer(("127.0.0.1", 0), manejador)


def servir(ruta: Path, puerto: int, llm_simulado: bool = False, abrir: bool = True) -> None:
    """Sirve la carpeta de la página en http://localhost: desde file:// los mapas de OpenStreetMap pueden no cargar
    (piden el encabezado Referer), el navegador no comparte la ubicación y no hay API para el texto libre."""
    servidor = crear(ruta.parent, puerto, llm_simulado)
    url = f"http://localhost:{servidor.server_address[1]}/{ruta.name}"
    if llm_simulado:
        estado = "simulado (respuestas de ejemplo, no se llama a Groq)"
    else:
        estado = "con Groq" if llm.clave_groq() else "sin GROQ_API_KEY: no se ofrece"
    print(f"Canasta en {url}  (Ctrl+C para cerrar). Texto libre: {estado}.")
    if abrir:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
