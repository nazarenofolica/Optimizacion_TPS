"""
La locución. Cada frase del guion se sintetiza por separado con la voz neural de guion.VOZ (edge-tts), se le recorta el
silencio de los bordes y se une a la siguiente con la pausa que pide el guion. Escribe en salida/voz/:

  <escena>.wav            el audio de la escena (24 kHz, mono)
  <escena>.palabras.json  [{"t": segundos, "d": duración, "w": palabra dicha}, ...]
  <escena>.subs.json      [{"t0": s, "t1": s, "texto": lo que se lee}, ...]  (un subtítulo por tramo " / ")
  duraciones.json         {escena: segundos de audio}

Las frases ya sintetizadas quedan en salida/voz/frases/ (por el texto y la voz): cambiar una frase solo rehace esa.

Uso (desde TPF/video):  python voz.py
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import subprocess
import unicodedata
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import numpy as np

from guion import ESCENAS, PAUSA, VELOCIDAD, VOZ

SALIDA = Path(__file__).parent / "salida" / "voz"
CACHE = SALIDA / "frases"
FS = 24000
ANTES, DESPUES = 0.03, 0.12        # margen que se deja alrededor de la primera y la última palabra de cada frase


def normal(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9ñ ]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def partir(frase: str) -> list[tuple[str, str]]:
    """Los tramos de subtítulo de una frase: [(escrito, dicho)], resolviendo {escrito|dicho}."""
    tramos = []
    for tramo in frase.split(" / "):
        escrito = re.sub(r"\{([^|}]*)\|[^}]*\}", r"\1", tramo).strip()
        dicho = re.sub(r"\{[^|}]*\|([^}]*)\}", r"\1", tramo).strip()
        tramos.append((escrito, dicho))
    return tramos


async def sintetizar(texto: str, mp3: Path, js: Path) -> None:
    com = edge_tts.Communicate(texto, VOZ, rate=VELOCIDAD, boundary="WordBoundary")
    audio, palabras = bytearray(), []
    async for parte in com.stream():
        if parte["type"] == "audio":
            audio += parte["data"]
        elif parte["type"] == "WordBoundary":         # offset y duration en unidades de 100 ns
            palabras.append({"t": parte["offset"] / 1e7, "d": parte["duration"] / 1e7, "w": parte["text"]})
    mp3.write_bytes(bytes(audio))
    js.write_text(json.dumps(palabras, ensure_ascii=False), encoding="utf-8")


def frase_audio(dicho: str) -> tuple[np.ndarray, list[dict]]:
    """Audio (float32, FS) y palabras de una frase, recortado a sus palabras."""
    clave = hashlib.sha1(f"{VOZ}|{VELOCIDAD}|{dicho}".encode()).hexdigest()[:16]
    mp3, js = CACHE / f"{clave}.mp3", CACHE / f"{clave}.json"
    if not mp3.exists() or not js.exists():
        asyncio.run(sintetizar(dicho, mp3, js))
        print("  voz:", dicho[:70])
    crudo = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(mp3), "-f", "s16le", "-ac", "1",
                            "-ar", str(FS), "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(crudo, dtype=np.int16).astype(np.float32) / 32768
    ps = json.loads(js.read_text(encoding="utf-8"))
    a = max(0.0, ps[0]["t"] - ANTES)
    b = min(len(x) / FS, ps[-1]["t"] + ps[-1]["d"] + DESPUES)
    x = x[int(a * FS):int(b * FS)].copy()
    n = int(0.01 * FS)                                  # 10 ms de fundido en cada borde, para que no haga clic
    x[:n] *= np.linspace(0, 1, n)
    x[-n:] *= np.linspace(1, 0, n)
    return x, [{**p, "t": round(p["t"] - a, 3)} for p in ps]


def alinear(dichas: list[str], palabras: list[dict]) -> list[int]:
    """Para cada palabra dicha del guion, el índice de su palabra en el audio (edge-tts a veces junta o separa)."""
    ws = [normal(p["w"]) for p in palabras]
    idx, j = [], 0
    for d in dichas:
        nd = normal(d)
        k = next((k for k in range(j, min(j + 4, len(ws)))
                  if nd and ws[k] and (ws[k] == nd or ws[k].startswith(nd) or nd.startswith(ws[k]))), None)
        if k is None:                                   # no está tal cual: se queda con la siguiente del audio
            idx.append(min(j, len(ws) - 1))
        else:
            idx.append(k)
            j = k + 1
    return idx


def escena(e: dict) -> float:
    partes, palabras, subs, t = [], [], [], 0.0
    for i, f in enumerate(e["frases"]):
        texto, pausa = (f, PAUSA) if isinstance(f, str) else f
        tramos = partir(texto)
        x, ps = frase_audio(" ".join(d for _, d in tramos))
        # Un subtítulo por tramo: empieza en su primera palabra y termina donde empieza el siguiente.
        dichas = [w for _, d in tramos for w in d.split()]
        idx = alinear(dichas, ps)
        k = 0
        inicios = []
        for _, d in tramos:
            inicios.append(ps[idx[k]]["t"] if k < len(idx) else 0.0)
            k += len(d.split())
        dur = len(x) / FS
        for n, (escrito, _) in enumerate(tramos):
            t0 = t + (0.0 if n == 0 else inicios[n])
            t1 = t + (inicios[n + 1] if n + 1 < len(tramos) else dur)
            subs.append({"t0": round(t0, 3), "t1": round(t1, 3), "texto": escrito, "frase": i})
        palabras += [{"t": round(t + p["t"], 3), "d": p["d"], "w": p["w"]} for p in ps]
        partes.append(x)
        t += dur
        if i < len(e["frases"]) - 1:
            partes.append(np.zeros(int(pausa * FS), dtype=np.float32))
            t += int(pausa * FS) / FS
    audio = np.concatenate(partes)
    with wave.open(str(SALIDA / f"{e['id']}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FS)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    (SALIDA / f"{e['id']}.palabras.json").write_text(json.dumps(palabras, ensure_ascii=False, indent=0),
                                                     encoding="utf-8")
    (SALIDA / f"{e['id']}.subs.json").write_text(json.dumps(subs, ensure_ascii=False, indent=1), encoding="utf-8")
    return round(len(audio) / FS, 3)


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    dur = {}
    for e in ESCENAS:
        dur[e["id"]] = escena(e)
        print(f"{e['id']}: {dur[e['id']]:.1f} s")
    (SALIDA / "duraciones.json").write_text(json.dumps(dur, indent=1), encoding="utf-8")
    print("total", round(sum(dur.values()), 1), "s")


if __name__ == "__main__":
    main()
