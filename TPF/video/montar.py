"""
Arma el video final a partir de las escenas animadas (escenas.py, Manim), la grabación de la página (grabar.py) y la
locución (voz.py):

  1. La escena 3 es la grabación de la página dentro del marco de ventana que dibuja E3Marco. Cada tramo de la
     grabación se ajusta a lo que dice la voz en ese momento (acelerado o no), con su encuadre (un recorte de la
     grabación, que es de 2560 x 1440) y, donde conviene, un acercamiento suave. Los tramos se unen con fundidos cortos.
  2. Cada escena dura PAUSA_INICIO + su audio + fin(escena); la voz entra a PAUSA_INICIO segundos.
  3. Se concatenan las siete escenas, se normaliza el volumen de la voz (-16 LUFS) y se escriben dos versiones: sin
     subtítulos y con subtítulos (uno por tramo del guion, con IBM Plex), además del .srt suelto.

Uso (desde TPF/video):  python montar.py [--calidad baja]
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw

from estilo import PAUSA_INICIO, _normal, fin
from guion import ESCENAS

AQUI = Path(__file__).parent
SALIDA = AQUI / "salida"
VOZ = SALIDA / "voz"
TMP = SALIDA / "tmp"
FF = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 60
CLASES = {"e1_pregunta": "E1Pregunta", "e2_datos": "E2Datos", "e3_pagina": "E3Marco", "e4_modelo": "E4Modelo",
          "e5_ejemplo": "E5Ejemplo", "e6_casos": "E6Casos", "e7_cierre": "E7Cierre"}
VENTANA = {"x": 232, "y": 196, "w": 1456, "h": 818, "radio": 14}     # el hueco de E3Marco, en píxeles de 1920 x 1080
FUNDIDO = 0.3                                                         # entre tramos de la página
ETIQUETAS = ["-color_range", "tv"]                                   # el mismo rango en todos los tramos


def ff(*args: str) -> None:
    subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", *args], check=True)


def duracion(ruta: Path) -> float:
    r = subprocess.run([FF, "-i", str(ruta)], capture_output=True, text=True)
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def cuando(escena: str, frase: str) -> float:
    """Segundo de la escena (con la pausa inicial) en que la voz dice `frase`."""
    obj = _normal(frase).split()
    ps = json.loads((VOZ / f"{escena}.palabras.json").read_text(encoding="utf-8"))
    ws = [_normal(p["w"]) for p in ps]
    for i in range(len(ws) - len(obj) + 1):
        if ws[i:i + len(obj)] == obj:
            return ps[i]["t"] + PAUSA_INICIO
    raise KeyError(frase)


# ----------------------------------------------------------------------------------------------------------------------
# Escena 3: la página
# ----------------------------------------------------------------------------------------------------------------------
def mascara() -> Path:
    """El hueco de la ventana con las esquinas de abajo redondeadas (las de arriba las tapa la barra del navegador)."""
    w, h, r = VENTANA["w"], VENTANA["h"], VENTANA["radio"]
    k = 4                                                 # se dibuja más grande y se achica: bordes suaves
    m = Image.new("L", (w * k, h * k), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, -r * k * 2, w * k - 1, h * k - 1], radius=r * k, fill=255)
    ruta = TMP / "mascara.png"
    m.resize((w, h), Image.LANCZOS).save(ruta)
    return ruta


def tramo_pagina(i: int, rec: tuple[float, float], largo: float, encuadre, total_largo: float) -> Path:
    """Un tramo de la grabación, de `largo` segundos, con su encuadre:
    (x, y, ancho) fijo o (x0, y0, ancho0, x1, y1, ancho1) para un acercamiento suave de uno a otro (16:9 siempre)."""
    a, b = rec
    velocidad = (b - a) / largo
    filtros = [f"trim=start={a:.3f}:end={b:.3f}", "setpts=PTS-STARTPTS", f"setpts=PTS/{velocidad:.5f}", f"fps={FPS}",
               f"tpad=stop_mode=clone:stop_duration={total_largo:.3f}", f"trim=duration={total_largo:.3f}"]
    W, H = VENTANA["w"], VENTANA["h"]
    destino = TMP / f"pagina_{i}.mp4"
    fuente = str(SALIDA / "pagina" / "pagina.mp4")
    if len(encuadre) == 3:
        x, y, w = encuadre
        # La grabación viene de cuadros JPEG (rango completo, "pc"); las animaciones, en rango "tv". Se pasa todo a
        # "tv": si se mezclan, al quemar los subtítulos el fondo se agrisa desde el corte en adelante.
        filtros += [f"crop={w}:{round(w * 9 / 16)}:{x}:{y}",
                    f"scale={W}:{H}:flags=lanczos:in_range=pc:out_range=tv", "format=yuv420p"]
        ff("-i", fuente, "-vf", ",".join(filtros), "-an", "-c:v", "libx264", "-crf", "14", "-preset", "fast",
           *ETIQUETAS, str(destino))
    else:
        acercar(fuente, filtros, encuadre, largo, destino)
    print(f"  tramo {i}: {b - a:5.1f} s de grabación en {largo:4.1f} s (x{velocidad:.2f})")
    return destino


def acercar(fuente: str, filtros: list[str], encuadre, largo: float, destino: Path) -> None:
    """Acercamiento suave (con precisión de subpíxel, cuadro por cuadro) del encuadre (x0, y0, ancho0) al
    (x1, y1, ancho1), con aceleración y frenado. ffmpeg (zoompan) redondea a píxeles enteros y el movimiento tiembla."""
    import math

    import numpy as np

    x0, y0, w0, x1, y1, w1 = encuadre
    W, H = VENTANA["w"], VENTANA["h"]
    lee = subprocess.Popen([FF, "-v", "error", "-i", fuente, "-vf", ",".join(filtros), "-f", "rawvideo",
                            "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    escribe = subprocess.Popen([FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "14", "-preset", "fast",
                                "-pix_fmt", "yuv420p", *ETIQUETAS, str(destino)], stdin=subprocess.PIPE)
    n_total = max(1, round(largo * FPS))
    tam = 2560 * 1440 * 3
    k = 0
    while True:
        crudo = lee.stdout.read(tam)
        if len(crudo) < tam:
            break
        e = (1 - math.cos(math.pi * min(k / n_total, 1))) / 2
        w = w0 + (w1 - w0) * e
        x, y = x0 + (x1 - x0) * e, y0 + (y1 - y0) * e
        s = w / W                                          # píxeles de la grabación por píxel de salida
        im = Image.frombuffer("RGB", (2560, 1440), crudo)
        cuadro = im.transform((W, H), Image.AFFINE, (s, 0, x, 0, s, y), resample=Image.BICUBIC)
        escribe.stdin.write(np.asarray(cuadro).tobytes())
        k += 1
    escribe.stdin.close()
    escribe.wait()
    lee.wait()


def escena_pagina(total: float, carpeta: str) -> Path:
    m = json.loads((SALIDA / "pagina" / "marcas.json").read_text(encoding="utf-8"))
    e = "e3_pagina"
    c = {k: cuando(e, f) for k, f in (("contas", "le contas"), ("donde", "donde compras"),
                                      ("tiempo", "y para cuanto tiempo"), ("segundos", "en unos segundos"),
                                      ("ticket", "te devuelve el ticket"), ("super", "en que supermercado"),
                                      ("oficinista", "para una oficinista"), ("cumple", "y cumple sus"))}
    r = m["resultado"]
    columna = (320, 0, 1920)                              # la columna de contenido de la página, a tamaño natural
    ticket = (280, 200, 1760)                             # el ticket y el total
    total_ = (925, 235, 1360)                             # el total y la sucursal, de cerca (sin el ticket)
    # (desde, hasta) en la grabación, (desde, hasta) en la escena, encuadre
    tramos = [
        ((m["datos_listos"], m["formulario"]), (0, c["contas"]), columna),                    # la portada
        ((m["formulario"], m["paso_ubicacion"]), (c["contas"], c["donde"]), columna),         # quiénes comen
        ((m["paso_ubicacion"], m["paso_compra"]), (c["donde"], c["tiempo"]), columna),        # dónde comprás
        ((m["paso_compra"], m["armar"] + 0.7), (c["tiempo"], c["segundos"]), columna),        # para cuánto tiempo
        ((m["armar"] + 0.7, r), (c["segundos"], c["ticket"]), columna),                       # calculando
        ((r, r + 6.5), (c["ticket"], c["super"]), ticket),                                    # el ticket se imprime
        ((m["mapa"] - 1.8, m["mapa"] + 3.5), (c["super"], c["oficinista"]), (320, 100, 1920)),  # el mapa
        ((r + 4.5, r + 9.0), (c["oficinista"], c["cumple"]), (*ticket, *total_)),            # del ticket al total
        ((m["balas"] - 0.2, m["fin"]), (c["cumple"], total), (320, 140, 1920)),               # las metas
    ]
    partes = []
    for i, (rec, (x, y), encuadre) in enumerate(tramos):
        extra = FUNDIDO if i < len(tramos) - 1 else 0.0
        partes.append(tramo_pagina(i, rec, y - x, encuadre, y - x + extra))
    # Fundidos cortos entre tramos: cada uno dura FUNDIDO más y se solapa con el siguiente.
    entradas = sum((["-i", str(p)] for p in partes), [])
    filtros, previo, t = [], "[0:v]", 0.0
    for i, (_, (x, y), _) in enumerate(tramos[:-1]):
        t = y                                             # el tramo i+1 empieza (en la escena) en y
        salida = f"[f{i}]"
        filtros.append(f"{previo}[{i + 1}:v]xfade=transition=fade:duration={FUNDIDO}:offset={t - 0.0:.3f}{salida}")
        previo = salida
    pagina = TMP / "e3_pagina_sola.mp4"
    ff(*entradas, "-filter_complex", ";".join(filtros), "-map", previo, "-c:v", "libx264", "-crf", "14", "-preset",
       "fast", "-r", str(FPS), *ETIQUETAS, str(pagina))

    # La página dentro del marco: aparece y se va con el marco (E3Marco: 0,6 s de capítulo y 0,5 s de fundido).
    marco = AQUI / "salida" / "manim" / "videos" / "escenas" / carpeta / "E3Marco.mp4"
    v = VENTANA
    salida = TMP / "e3_pagina.mp4"
    ff("-i", str(marco), "-i", str(pagina), "-loop", "1", "-i", str(mascara()), "-filter_complex",
       f"[0:v]scale=1920:1080:flags=lanczos,fps={FPS}[base];"
       f"[2:v]format=gray,fps={FPS}[m];"
       f"[1:v]format=yuva420p[p];[p][m]alphamerge,format=yuva420p,"
       f"fade=t=in:st=0.6:d=0.5:alpha=1,fade=t=out:st={total - 0.5:.3f}:d=0.5:alpha=1[pa];"
       f"[base][pa]overlay={v['x']}:{v['y']}:shortest=1,trim=duration={total:.3f},format=yuv420p[v]",
       "-map", "[v]", "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-r", str(FPS), *ETIQUETAS, str(salida))
    return salida


# ----------------------------------------------------------------------------------------------------------------------
# Subtítulos
# ----------------------------------------------------------------------------------------------------------------------
def dos_renglones(s: str, largo: int = 44) -> str:
    """Corta en dos renglones parejos si no entra en uno."""
    if len(s) <= largo:
        return s
    palabras = s.split()
    mejor, corte = None, 1
    for k in range(1, len(palabras)):
        a, b = " ".join(palabras[:k]), " ".join(palabras[k:])
        d = abs(len(a) - len(b))
        if mejor is None or d < mejor:
            mejor, corte = d, k
    return " ".join(palabras[:corte]) + "\n" + " ".join(palabras[corte:])


def bloques_subtitulos(inicios: dict[str, float]) -> list[tuple[float, float, str]]:
    bloques = []
    for e in ESCENAS:
        for s in json.loads((VOZ / f"{e['id']}.subs.json").read_text(encoding="utf-8")):
            t0 = inicios[e["id"]] + PAUSA_INICIO + s["t0"]
            t1 = inicios[e["id"]] + PAUSA_INICIO + s["t1"]
            bloques.append((t0, t1, dos_renglones(s["texto"])))
    final = []
    for i, (a, b, s) in enumerate(bloques):                # se queda un poco más, sin pisar al siguiente
        siguiente = bloques[i + 1][0] if i + 1 < len(bloques) else b + 1.0
        final.append((a, min(max(b + 0.35, a + 1.0), siguiente - 0.04), s))
    return final


def hms(t: float, sep: str = ",") -> str:
    h, resto = divmod(t, 3600)
    m, s = divmod(resto, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", sep)


def escribir_subtitulos(bloques, srt: Path, ass: Path) -> None:
    srt.write_text("".join(f"{i}\n{hms(a)} --> {hms(b)}\n{s}\n\n" for i, (a, b, s) in enumerate(bloques, 1)),
                   encoding="utf-8")
    cab = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Voz,IBM Plex Sans,38,&H00FEFFFF,&H00FEFFFF,&H281A1716,&H281A1716,0,0,0,0,100,100,0,0,3,12,0,2,160,160,34,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    salto = "\\N"   # salto de línea de ASS (fuera del f-string: Python < 3.12 no admite "\" en sus expresiones)
    eventos = "".join(f"Dialogue: 0,{hms(a, '.')[1:-1]},{hms(b, '.')[1:-1]},Voz,,0,0,0,,{s.replace(chr(10), salto)}\n"
                      for a, b, s in bloques)
    ass.write_text(cab + eventos, encoding="utf-8")


# ----------------------------------------------------------------------------------------------------------------------
def main() -> None:
    carpeta = "480p15" if "--calidad" in sys.argv and sys.argv[sys.argv.index("--calidad") + 1] == "baja" \
        else "1080p60"
    TMP.mkdir(parents=True, exist_ok=True)
    dur = json.loads((VOZ / "duraciones.json").read_text(encoding="utf-8"))
    totales = {e["id"]: round(PAUSA_INICIO + dur[e["id"]] + fin(e["id"]), 3) for e in ESCENAS}

    clips, inicios, t = [], {}, 0.0
    for e in ESCENAS:
        i = e["id"]
        inicios[i] = t
        if i == "e3_pagina":
            print("escena 3: la página")
            video = escena_pagina(totales[i], carpeta)
        else:
            video = AQUI / "salida" / "manim" / "videos" / "escenas" / carpeta / f"{CLASES[i]}.mp4"
        # Video de la escena (1080p, 60 cuadros) con su voz, que entra a PAUSA_INICIO segundos.
        clip = TMP / f"clip_{i}.mp4"
        ms = int(PAUSA_INICIO * 1000)
        ff("-i", str(video), "-i", str(VOZ / f"{i}.wav"), "-filter_complex",
           f"[0:v]scale=1920:1080:flags=lanczos:out_range=tv,fps={FPS},tpad=stop_mode=clone:stop_duration=2,"
           f"trim=duration={totales[i]:.3f},format=yuv420p[v];"
           f"[1:a]aresample=48000,adelay={ms}|{ms},apad,atrim=duration={totales[i]:.3f}[a]",
           "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "16", "-preset", "medium", *ETIQUETAS, "-c:a", "pcm_s16le",
           str(clip.with_suffix(".mkv")))
        clips.append(clip.with_suffix(".mkv"))
        t += totales[i]
        print(f"{i}: {totales[i]:.2f} s (video de origen {duracion(video):.2f} s)")

    lista = TMP / "clips.txt"
    lista.write_text("".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8")
    final = SALIDA / "canasta_saludable.mp4"
    ff("-f", "concat", "-safe", "0", "-i", str(lista), "-c:v", "copy", "-af",
       "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000", "-c:a", "aac", "-b:a", "192k", "-ac", "2",
       "-movflags", "+faststart", str(final))

    bloques = bloques_subtitulos(inicios)
    srt, ass = SALIDA / "canasta_saludable.srt", TMP / "subtitulos.ass"
    escribir_subtitulos(bloques, srt, ass)
    con_subs = SALIDA / "canasta_saludable_subtitulado.mp4"
    fuentes = (AQUI / "fuentes").as_posix().replace(":", "\\:")
    ruta_ass = ass.as_posix().replace(":", "\\:")
    ff("-i", str(final), "-vf", f"subtitles='{ruta_ass}':fontsdir='{fuentes}'", "-c:v", "libx264", "-crf", "17",
       "-preset", "medium", *ETIQUETAS, "-c:a", "copy", "-movflags", "+faststart", str(con_subs))
    print(f"\nlisto: {final.name} y {con_subs.name}, {duracion(final):.1f} s, {len(bloques)} subtítulos")


if __name__ == "__main__":
    main()
