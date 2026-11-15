"""Abre la presentación con la demo en vivo.

    python informe/presentar.py            (desde TPF/)

Sirve la carpeta TPF/ en http://localhost para que la demo embebida cargue los mapas y, si existe
datos/sepa/canasta_local.html (la genera `python -m canasta` desde base_sepa/, con la clave de OpenRouteService),
use rutas a pie reales. Sin ella, la demo usa la versión publicada en GitHub Pages
(https://nazarenofolica.github.io/Optimizacion_TPS/), con tiempos estimados por distancia.
"""

from __future__ import annotations

import functools
import http.server
import sys
import threading
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent           # TPF/
PUERTO = 8770


class _Silencioso(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main() -> int:
    try:                                   # la consola de Windows (cp1252) no imprime todos los caracteres
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass
    local = RAIZ / "datos" / "sepa" / "canasta_local.html"
    if not local.exists():
        print("Aviso: no está datos/sepa/canasta_local.html; la demo usa la de GitHub Pages y estima los tiempos caminando.\n"
              "  Para rutas reales: cd base_sepa && python -m canasta --exportar ../datos/sepa/canasta_local.html --con-clave")
    manejador = functools.partial(_Silencioso, directory=str(RAIZ))
    try:
        servidor = http.server.ThreadingHTTPServer(("127.0.0.1", PUERTO), manejador)
    except OSError:
        servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), manejador)
    url = f"http://localhost:{servidor.server_address[1]}/informe/presentacion.html"
    print(f"Presentacion en {url}  (F: pantalla completa, flechas: diapositivas, Ctrl+C para cerrar)")
    threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
