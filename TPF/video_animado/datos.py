"""
Los datos reales que usa el reel:

  src/datos/mapa.json        las sucursales de dim_tienda, proyectadas a [x, y] en 0..1 (para dibujarlas como puntos),
                             y Córdoba y CABA con la misma proyección
  public/pagina_form.mp4     la grabación real de la página (TPF/video/grabar.py): del formulario al botón de armar
  public/pagina_res.mp4      la misma grabación: el ticket, el mapa y las metas
  src/datos/pagina.json      cuándo hace clic y cuándo tipea el cursor en pagina_form.mp4 (para el sonido)

La grabación sale de TPF/video/salida/pagina/pagina.mp4 y sus marcas (marcas.json); si no está, correr antes
`python grabar.py` en TPF/video.

Uso (desde TPF/video_animado):  python datos.py
"""

import json
import math
import subprocess
from pathlib import Path

import pyarrow.parquet as pq

AQUI = Path(__file__).parent
TPF = AQUI.parent
PAGINA = TPF / "video" / "salida" / "pagina"


def mapa() -> None:
    t = pq.read_table(TPF / "datos" / "sepa" / "dim_tienda.parquet", columns=["lat", "lon"]).to_pandas().dropna()
    t = t[(t.lat < -21) & (t.lat > -56) & (t.lon > -74) & (t.lon < -53)]          # Argentina continental
    k = math.cos(math.radians(-38))
    xs, ys = t.lon * k, -t.lat
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    escala = max(x1 - x0, y1 - y0)
    puntos = sorted({(round((x - x0) / escala, 4), round((y - y0) / escala, 4)) for x, y in zip(xs, ys)},
                    key=lambda p: p[1])                                               # de norte a sur

    def proy(lat: float, lon: float) -> list[float]:
        return [round((lon * k - x0) / escala, 4), round((-lat - y0) / escala, 4)]

    (AQUI / "src" / "datos").mkdir(parents=True, exist_ok=True)
    (AQUI / "src" / "datos" / "mapa.json").write_text(json.dumps(
        {"ancho": round((x1 - x0) / escala, 4), "alto": round((y1 - y0) / escala, 4), "puntos": puntos,
         "cordoba": proy(-31.4167, -64.1833), "caba": proy(-34.6037, -58.3816)}),
        encoding="utf-8")
    print(len(t), "sucursales,", len(puntos), "puntos distintos")


def pagina() -> None:
    m = json.loads((PAGINA / "marcas.json").read_text(encoding="utf-8"))
    cortes = {"pagina_form.mp4": (m["formulario"], m["armar"] + 1.0),
              "pagina_res.mp4": (m["resultado"], m["fin"])}
    for nombre, (a, b) in cortes.items():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.2f}", "-to", f"{b:.2f}",
                        "-i", str(PAGINA / "pagina.mp4"), "-an", "-vf", "scale=1280:-2,fps=30",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-g", "15", "-pix_fmt", "yuv420p",
                        str(AQUI / "public" / nombre)], check=True)
        print(nombre, f"{b - a:.1f} s")


# Lo que hace grabar.py en el formulario, en su orden: (acción, pausa después del clic, letras tipeadas).
# tocar(): 0,25 s de scroll + 0,7 s moviendo el cursor + clic + pausa. escribir(): tocar con pausa 0,2, una letra cada
# 0,09 s y 0,35 s al final. Los tiempos de grabar.py están en tiempo de video (LENTO ya compensado).
ACCIONES = [("nombre", 0.2, 10), ("sexo", 0.75, 0), ("edad", 0.2, 2), ("peso", 0.2, 2), ("altura", 0.2, 3),
            ("actividad", 0.75, 0), ("objetivo", 1.0, 0)]


def clics() -> None:
    """Cuándo hace clic y cuándo tipea el cursor en pagina_form.mp4 (para ponerles sonido). El anillo del clic no
    queda en el screencast, así que se reconstruye con la secuencia de grabar.py, escalada entre sus marcas: la
    medición cuadro a cuadro del video coincide con ±0,15 s."""
    m = json.loads((PAGINA / "marcas.json").read_text(encoding="utf-8"))
    ini = m["formulario"]
    modelo = sum(0.95 + pausa + letras * 0.09 + (0.35 if letras else 0) for _, pausa, letras in ACCIONES)
    k = (m["paso_ubicacion"] - m["formulario"]) / modelo          # lo que tardan las llamadas a Selenium
    t, out, tipeo = 0.0, [], []
    for _, pausa, letras in ACCIONES:
        out.append(round(t + 0.95 * k, 2))
        if letras:
            tipeo.append([round(t + (0.95 + pausa) * k, 2), round(t + (0.95 + pausa + letras * 0.09) * k, 2)])
        t += (0.95 + pausa + letras * 0.09 + (0.35 if letras else 0)) * k
    for marca in ("paso_ubicacion", "paso_compra", "armar"):                # los botones "Siguiente" y "Armar"
        out.append(round(m[marca] - ini + 0.95 * k, 2))
    (AQUI / "src" / "datos" / "pagina.json").write_text(json.dumps({"clics": out, "tipeo": tipeo}), encoding="utf-8")
    print("clics", out)


if __name__ == "__main__":
    mapa()
    pagina()
    clics()
