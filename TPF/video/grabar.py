"""
Graba la página real (datos/sepa/canasta.html) completando el formulario como lo haría una persona: la oficinista del
caso base, en el centro de Buenos Aires. Usa Chrome sin ventana y el screencast de DevTools (un cuadro cada vez que
la pantalla cambia), con un cursor dibujado encima para que se vea qué se toca.

Escribe en salida/pagina/: los cuadros (JPEG), marcas.json (cuándo pasa cada cosa) y pagina.mp4 (2560 x 1440, 30 cuadros
por segundo, con los tiempos reales). montar.py recorta y acelera los tramos según las marcas.

Uso (desde TPF/video):  python grabar.py
"""

from __future__ import annotations

import base64
import http.server
import json
import queue
import shutil
import subprocess
import threading
import time
import urllib.request
from functools import partial
from pathlib import Path

import imageio_ffmpeg
import websocket
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

AQUI = Path(__file__).parent
PAGINA = AQUI.parent / "datos" / "sepa"
SALIDA = AQUI / "salida" / "pagina"
PUERTO = 8767
ANCHO, ALTO, ESCALA = 1600, 900, 1.5          # una pantalla de 1600 px, capturada a 2400 x 1350 (para acercar sin perder nitidez)
LUGAR = (-34.60386, -58.38419)                 # Microcentro, el caso base del informe
# Cámara lenta: la página corre 3 veces más lenta (animaciones de CSS y reloj de JavaScript) y el video se acelera 3
# veces al armarlo. Así el screencast, que da ~12 cuadros por segundo a esta resolución, rinde ~35 efectivos.
LENTO = 3
# requestAnimationFrame recibe el mismo reloj lento que performance.now: Chrome ya frena el tiempo de rAF con
# Animation.setPlaybackRate, y la página compara los dos (contar() en app.js); con relojes distintos el total quedaba
# en $0.
RELOJ_LENTO_JS = """
(() => { const k = %d; const pn = performance.now.bind(performance);
  performance.now = () => pn() / k;
  const raf = window.requestAnimationFrame.bind(window);
  window.requestAnimationFrame = (cb) => raf(() => cb(performance.now()));
  const st = window.setTimeout.bind(window);
  window.setTimeout = (f, ms, ...a) => st(f, (ms || 0) * k, ...a);
})();
""" % LENTO

# Cursor de mentira: una flecha que se desliza hasta cada control antes del clic, con un pulso al tocar.
CURSOR_JS = """
if (!window.__cursor) {
  const c = document.createElement('div');
  c.innerHTML = '<svg width="30" height="30" viewBox="0 0 24 24"><path d="M4 2l15 9-6.5 1.4L16 20l-2.6 1.2-3.4-7.3L5 19z" fill="#16171a" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  Object.assign(c.style, {position: 'fixed', left: '0px', top: '0px', zIndex: 99999, pointerEvents: 'none',
    transition: 'transform 650ms cubic-bezier(0.25,1,0.5,1)', transform: 'translate(820px, 520px)',
    filter: 'drop-shadow(0 2px 3px rgba(0,0,0,.35))'});
  document.body.appendChild(c);
  const p = document.createElement('div');
  Object.assign(p.style, {position: 'fixed', width: '44px', height: '44px', margin: '-22px 0 0 -22px', borderRadius: '50%',
    border: '3px solid #f3d03e', zIndex: 99998, pointerEvents: 'none', opacity: 0, left: '0px', top: '0px'});
  document.body.appendChild(p);
  window.__cursor = {c, p, x: 820, y: 520};
}
"""
MOVER_JS = """
const el = arguments[0]; const r = el.getBoundingClientRect();
const x = r.left + Math.min(r.width / 2, 60), y = r.top + r.height / 2;
const k = window.__cursor; k.x = x; k.y = y;
k.c.style.transform = `translate(${x - 4}px, ${y - 2}px)`;
"""
PULSO_JS = """
const k = window.__cursor; const p = k.p;
p.style.left = k.x + 'px'; p.style.top = k.y + 'px';
p.animate([{opacity: 0.95, transform: 'scale(0.4)'}, {opacity: 0, transform: 'scale(1.5)'}], {duration: 520, easing: 'ease-out'});
"""
DESPLAZAR_JS = """
const destino = arguments[0], ms = arguments[1], inicio = scrollY, t0 = performance.now();
const paso = (t) => { const f = Math.min(1, (t - t0) / ms), e = 1 - Math.pow(1 - f, 3);
  scrollTo(0, inicio + (destino - inicio) * e); if (f < 1) requestAnimationFrame(paso); };
requestAnimationFrame(paso);
"""


class Grabadora:
    """Recibe los cuadros del screencast de DevTools por su propio websocket y los guarda con su hora."""

    def __init__(self, debugger: str):
        paginas = json.load(urllib.request.urlopen(f"http://{debugger}/json"))
        url = next(p["webSocketDebuggerUrl"] for p in paginas if p["type"] == "page")
        self.ws = websocket.create_connection(url, max_size=None, suppress_origin=True)
        self.cuadros: list[tuple[float, Path]] = []
        self.activa = True
        self.n = 0
        self.pendientes: queue.Queue = queue.Queue()
        self.hilo = threading.Thread(target=self._recibir, daemon=True)
        self.escritor = threading.Thread(target=self._escribir, daemon=True)

    def empezar(self):
        self.ws.send(json.dumps({"id": 1, "method": "Page.startScreencast",
                                 "params": {"format": "jpeg", "quality": 88, "everyNthFrame": 1,
                                            "maxWidth": ANCHO * ESCALA, "maxHeight": ALTO * ESCALA}}))
        self.hilo.start()
        self.escritor.start()

    def _escribir(self):
        """Decodifica y guarda los cuadros en otro hilo: así el screencast no espera al disco."""
        while True:
            item = self.pendientes.get()
            if item is None:
                break
            ruta, datos = item
            ruta.write_bytes(base64.b64decode(datos))

    def _recibir(self):
        while self.activa:
            try:
                msg = json.loads(self.ws.recv())
            except Exception:
                break
            if msg.get("method") != "Page.screencastFrame":
                continue
            p = msg["params"]
            # Primero se confirma el cuadro (Chrome no manda el siguiente hasta recibir la confirmación).
            self.ws.send(json.dumps({"id": 1000 + self.n, "method": "Page.screencastFrameAck",
                                     "params": {"sessionId": p["sessionId"]}}))
            ruta = SALIDA / "cuadros" / f"{self.n:06d}.jpg"
            self.cuadros.append((time.time(), ruta))
            self.pendientes.put((ruta, p["data"]))
            self.n += 1

    def terminar(self):
        # Orden: dejar de recibir, esperar al hilo que recibe y recién ahí cerrar el que escribe (si no, un cuadro que
        # llega a último momento queda en la lista sin archivo).
        self.activa = False
        try:
            self.ws.send(json.dumps({"id": 2, "method": "Page.stopScreencast"}))
            self.ws.close()
        except Exception:
            pass
        self.hilo.join(timeout=5)
        self.pendientes.put(None)


def servidor() -> http.server.ThreadingHTTPServer:
    manejador = partial(http.server.SimpleHTTPRequestHandler, directory=str(PAGINA))
    manejador.log_message = lambda *a: None
    s = http.server.ThreadingHTTPServer(("127.0.0.1", PUERTO), manejador)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


def main() -> None:
    # Se vacía la carpeta en lugar de borrarla: en Windows, una terminal parada adentro la bloquea.
    if (SALIDA / "cuadros").exists():
        shutil.rmtree(SALIDA / "cuadros")
    (SALIDA / "cuadros").mkdir(parents=True)
    srv = servidor()
    op = Options()
    # La escala va como opción de arranque: el screencast captura al tamaño físico de la ventana, y la emulación de
    # DevTools (deviceScaleFactor) no lo cambia.
    for a in ("--headless=new", "--disable-gpu", "--hide-scrollbars", "--remote-debugging-port=0",
              f"--window-size={ANCHO},{ALTO}", f"--force-device-scale-factor={ESCALA}"):
        op.add_argument(a)
    d = webdriver.Chrome(options=op)
    d.set_script_timeout(300)
    d.execute_cdp_cmd("Emulation.setDeviceMetricsOverride",
                      {"width": ANCHO, "height": ALTO, "deviceScaleFactor": ESCALA, "mobile": False})
    d.execute_cdp_cmd("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": "light"}]})
    d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": RELOJ_LENTO_JS})

    def lento():
        d.execute_cdp_cmd("Animation.enable", {})
        d.execute_cdp_cmd("Animation.setPlaybackRate", {"playbackRate": 1 / LENTO})

    def dormir(s: float):
        time.sleep(s * LENTO)
    marcas: dict[str, float] = {}
    g = Grabadora(d.capabilities["goog:chromeOptions"]["debuggerAddress"])
    g.empezar()
    t0 = time.time()

    def marca(nombre: str):
        marcas[nombre] = round(time.time() - t0, 3)
        print(f"{marcas[nombre]:7.2f}  {nombre}")

    def esperar(cond_js: str, tope: float = 240):
        fin = time.time() + tope
        while time.time() < fin:
            try:
                if d.execute_script(cond_js):
                    return True
            except Exception:
                pass
            time.sleep(0.2)
        raise TimeoutError(cond_js)

    def tocar(css: str, pausa: float = 0.75):
        el = d.find_element("css selector", css)
        d.execute_script("arguments[0].scrollIntoView({block: 'nearest', behavior: 'smooth'})", el)
        dormir(0.25)
        d.execute_script(CURSOR_JS)
        d.execute_script(MOVER_JS, el)
        dormir(0.7)
        d.execute_script(PULSO_JS)
        d.execute_script("arguments[0].click()", el)
        dormir(pausa)

    def escribir(css: str, texto: str):
        tocar(css, 0.2)
        el = d.find_element("css selector", css)
        el.clear()
        for ch in texto:
            el.send_keys(ch)
            dormir(0.09)
        dormir(0.35)

    try:
        d.get(f"http://127.0.0.1:{PUERTO}/canasta.html?lat={LUGAR[0]}&lon={LUGAR[1]}")
        lento()
        marca("carga")
        esperar("return document.querySelector('#estado-datos') && !/Preparando/.test(document.querySelector('#estado-datos').textContent)")
        marca("datos_listos")
        dormir(3.0)                                       # la portada y el ticket de la cabecera
        d.execute_script(CURSOR_JS)
        d.execute_script(DESPLAZAR_JS, 380, 1100)
        dormir(1.4)
        marca("formulario")
        escribir("#p-nombre", "Oficinista")
        tocar("input[name='p-sexo'][value='F'] + span")
        escribir("#p-edad", "34")
        escribir("#p-peso", "63")
        escribir("#p-altura", "163")
        tocar("input[name='p-actividad'][value='sedentaria'] + span")
        tocar("input[name='p-objetivo'][value='mantener'] + span", 1.0)
        marca("paso_ubicacion")
        tocar("#siguiente", 2.4)
        marca("paso_compra")
        tocar("#siguiente", 2.0)
        marca("armar")
        tocar("#armar", 0.5)
        esperar("return !!document.querySelector('#resumen-total')")
        marca("resultado")
        dormir(9.0)                                       # el ticket se imprime y el total cuenta
        y = d.execute_script("return document.querySelector('#donde-comprar').getBoundingClientRect().top + scrollY - 70")
        d.execute_script(DESPLAZAR_JS, y, 1600)
        dormir(1.8)
        marca("mapa")
        dormir(4.0)
        y = d.execute_script("return document.querySelector('.balas-grid').getBoundingClientRect().top + scrollY - 160")
        d.execute_script(DESPLAZAR_JS, y, 1800)
        dormir(2.0)
        marca("balas")
        dormir(3.5)
        marca("fin")
    finally:
        g.terminar()
        g.escritor.join()                                 # que estén todos los cuadros en disco
        d.quit()
        srv.shutdown()

    # Video a 30 cuadros por segundo con los tiempos reales: cada cuadro dura hasta que llega el siguiente.
    lista = SALIDA / "cuadros.txt"
    with open(lista, "w", encoding="utf-8") as f:
        for (t, ruta), siguiente in zip(g.cuadros, g.cuadros[1:] + [(t0 + marcas["fin"] + 0.5, None)]):
            f.write(f"file '{ruta.as_posix()}'\nduration {max(siguiente[0] - t, 0.001) / LENTO:.4f}\n")
        f.write(f"file '{g.cuadros[-1][1].as_posix()}'\n")
    inicio = g.cuadros[0][0] - t0
    # Relativas al primer cuadro, y en el tiempo del video (que va LENTO veces más rápido que la grabación).
    marcas = {k: round((v - inicio) / LENTO, 3) for k, v in marcas.items()}
    (SALIDA / "marcas.json").write_text(json.dumps(marcas, indent=1), encoding="utf-8")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error", "-f", "concat",
                    "-safe", "0", "-i", str(lista), "-vf", "scale=2560:1440:flags=lanczos,format=yuv420p",
                    "-r", "30", "-c:v", "libx264", "-crf", "18", str(SALIDA / "pagina.mp4")], check=True)
    print("cuadros:", len(g.cuadros), "->", SALIDA / "pagina.mp4")


if __name__ == "__main__":
    main()
