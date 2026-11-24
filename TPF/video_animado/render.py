"""
Render final del reel: Remotion arma el video (1080x1920, 30 fps) y ffmpeg normaliza el audio a -14 LUFS, que es el
nivel al que Instagram reproduce (si llega más fuerte lo baja, si llega más bajo suena flojo al lado de otros reels).

  salida/reel_crudo.mp4         lo que sale de Remotion
  salida/canasta_reel.mp4       el reel vertical, para subir (audio normalizado, H.264 + AAC, faststart)
  salida/canasta_horizontal.mp4 la versión horizontal 1920x1080 (--horizontal), para LinkedIn o una presentación

Uso (desde TPF/video_animado):  python render.py            (--borrador: a media resolución, más rápido)
                                python render.py --horizontal
"""

import json
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).parent
SALIDA = AQUI / "salida"
NPX = "npx.cmd" if sys.platform == "win32" else "npx"


def main() -> None:
    borrador = "--borrador" in sys.argv
    horizontal = "--horizontal" in sys.argv
    SALIDA.mkdir(exist_ok=True)
    nombre = "horizontal" if horizontal else "reel"
    crudo = SALIDA / (f"borrador_{nombre}_crudo.mp4" if borrador else f"{nombre}_crudo.mp4")
    final = SALIDA / (f"borrador_{nombre}.mp4" if borrador else f"canasta_{nombre}.mp4")
    cmd = [NPX, "remotion", "render", "ReelHorizontal" if horizontal else "Reel", str(crudo), "--log=error", "--crf=18"]
    if borrador:
        cmd.append("--scale=0.5")
    subprocess.run(cmd, cwd=AQUI, check=True)

    # Dos pasadas de loudnorm: la primera mide, la segunda corrige con esas medidas (más preciso que una sola).
    medir = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(crudo), "-af",
                            "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    m = json.loads(medir[medir.rindex("{"):medir.rindex("}") + 1])
    filtro = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
              f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
              "linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(crudo), "-c:v", "copy", "-af", filtro,
                    "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final)], check=True)
    print(f"{final}  (audio de {m['input_i']} a -14 LUFS)")


if __name__ == "__main__":
    main()
