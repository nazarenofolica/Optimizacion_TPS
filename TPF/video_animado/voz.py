"""
La locución del reel. Cada beat del guion se sintetiza entero (edge-tts), se recorta a sus palabras y se une al
siguiente con la pausa del guion. Escribe:

  public/audio/voz.wav        la voz completa (24 kHz, mono)
  src/datos/tiempos.json      escenas, beats, palabras (lo escrito, con su tiempo) y subtítulos de 1 a 3 palabras
  salida/reel.srt             los mismos subtítulos, para subirlos aparte si hace falta

Las síntesis quedan en salida/cache_voz/ (por voz, velocidad, tono y texto): cambiar un beat solo rehace ese.

Uso (desde TPF/video_animado):  python voz.py            (VOZ=es-AR-ElenaNeural python voz.py para otra voz)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
import unicodedata
import wave
from pathlib import Path

import edge_tts
import numpy as np

import guion

AQUI = Path(__file__).parent
CACHE = AQUI / "salida" / "cache_voz"
AUDIO = AQUI / "public" / "audio"
DATOS = AQUI / "src" / "datos"
FS = 24000
ANTES, DESPUES = 0.04, 0.16

VOZ = os.environ.get("VOZ", guion.VOZ)
VELOCIDAD = os.environ.get("VELOCIDAD", guion.VELOCIDAD)
TONO = os.environ.get("TONO", guion.TONO)


def normal(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9ñ ]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def tokens(texto: str) -> list[tuple[str, list[str]]]:
    """[(escrito, [palabras dichas])]: una palabra suelta es su propio token; {escrito|dicho} es un token."""
    out = []
    for m in re.finditer(r"\{([^|}]*)\|([^}]*)\}([^\s{]*)|(\S+)", texto):
        if m.group(4) is not None:
            out.append((m.group(4), [m.group(4)]))
        else:                                   # la puntuación pegada a la llave ("{37|treinta y siete}.") va al escrito
            out.append((m.group(1) + m.group(3), m.group(2).split()))
    return out


async def sintetizar(texto: str, mp3: Path, js: Path, velocidad: str) -> None:
    com = edge_tts.Communicate(texto, VOZ, rate=velocidad, pitch=TONO, boundary="WordBoundary")
    audio, palabras = bytearray(), []
    async for parte in com.stream():
        if parte["type"] == "audio":
            audio += parte["data"]
        elif parte["type"] == "WordBoundary":
            palabras.append({"t": parte["offset"] / 1e7, "d": parte["duration"] / 1e7, "w": parte["text"]})
    mp3.write_bytes(bytes(audio))
    js.write_text(json.dumps(palabras, ensure_ascii=False), encoding="utf-8")


def ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def beat_audio(dicho: str, velocidad: str = VELOCIDAD) -> tuple[np.ndarray, list[dict]]:
    clave = hashlib.sha1(f"{VOZ}|{velocidad}|{TONO}|{dicho}".encode()).hexdigest()[:16]
    mp3, js = CACHE / f"{clave}.mp3", CACHE / f"{clave}.json"
    if not mp3.exists() or not js.exists():
        asyncio.run(sintetizar(dicho, mp3, js, velocidad))
        print("  voz:", dicho[:72])
    crudo = subprocess.run([ffmpeg(), "-v", "error", "-i", str(mp3), "-f", "s16le", "-ac", "1", "-ar", str(FS), "-"],
                           capture_output=True, check=True).stdout
    x = np.frombuffer(crudo, dtype=np.int16).astype(np.float32) / 32768
    ps = json.loads(js.read_text(encoding="utf-8"))
    a = max(0.0, ps[0]["t"] - ANTES)
    b = min(len(x) / FS, ps[-1]["t"] + ps[-1]["d"] + DESPUES)
    x = x[int(a * FS):int(b * FS)].copy()
    n = int(0.012 * FS)
    x[:n] *= np.linspace(0, 1, n)
    x[-n:] *= np.linspace(1, 0, n)
    return x, [{**p, "t": p["t"] - a} for p in ps]


def alinear(dichas: list[str], palabras: list[dict]) -> list[int]:
    """Para cada palabra dicha del guion, el índice de su palabra en el audio (edge-tts a veces junta o separa)."""
    ws = [normal(p["w"]) for p in palabras]
    idx, j = [], 0
    for d in dichas:
        nd = normal(d)
        k = next((k for k in range(j, min(j + 4, len(ws)))
                  if nd and ws[k] and (ws[k] == nd or ws[k].startswith(nd) or nd.startswith(ws[k]))), None)
        if k is None:
            idx.append(min(j, len(ws) - 1))
        else:
            idx.append(k)
            j = k + 1
    return idx


def subtitulos(palabras: list[dict]) -> list[dict]:
    """Agrupa las palabras escritas en golpes de 1 a 3 palabras, cortando en la puntuación."""
    grupos, actual = [], []
    for p in palabras:
        actual.append(p)
        largo = sum(len(q["texto"]) + 1 for q in actual)
        corta = re.search(r"[.,:;?!…]$", p["texto"]) or len(actual) >= 3 or largo >= 16
        if corta:
            grupos.append(actual)
            actual = []
    if actual:
        grupos.append(actual)
    subs = []
    for i, g in enumerate(grupos):
        t1 = g[-1]["t1"] + 0.35
        if i + 1 < len(grupos):
            t1 = min(t1, grupos[i + 1][0]["t0"]) if grupos[i + 1][0]["t0"] - g[-1]["t1"] > 0.45 \
                else grupos[i + 1][0]["t0"]
        subs.append({"t0": g[0]["t0"], "t1": round(t1, 3), "beat": g[0]["beat"],
                     "palabras": [{"texto": q["texto"], "t0": q["t0"], "t1": q["t1"]} for q in g]})
    return subs


def srt(subs: list[dict]) -> str:
    def ts(t: float) -> str:
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    return "\n".join(f"{i}\n{ts(s['t0'])} --> {ts(s['t1'])}\n{' '.join(p['texto'] for p in s['palabras'])}\n"
                     for i, s in enumerate(subs, 1))


def main() -> None:
    for d in (CACHE, AUDIO, DATOS):
        d.mkdir(parents=True, exist_ok=True)
    partes, t = [], 0.0
    escenas, beats, palabras = [], {}, []
    for ie, e in enumerate(guion.ESCENAS):
        e_t0 = t
        for ib, beat in enumerate(e["beats"]):
            bid, texto = beat[0], beat[1]
            opc = {**e.get("opciones", {}), **(beat[2] if len(beat) > 2 else {})}
            toks = tokens(texto)
            x, ps = beat_audio(" ".join(w for _, ds in toks for w in ds), opc.get("velocidad", VELOCIDAD))
            idx = alinear([w for _, ds in toks for w in ds], ps)
            k = 0
            for escrito, ds in toks:
                i0, i1 = idx[k], idx[k + len(ds) - 1]
                k += len(ds)
                palabras.append({"texto": escrito, "beat": bid, "t0": round(t + ps[i0]["t"], 3),
                                 "t1": round(t + ps[i1]["t"] + ps[i1]["d"], 3)})
            dur = len(x) / FS
            beats[bid] = {"escena": e["id"], "t0": round(t, 3), "t1": round(t + dur, 3)}
            partes.append(x)
            t += dur
            ultimo = ie == len(guion.ESCENAS) - 1 and ib == len(e["beats"]) - 1
            if not ultimo:
                pausa = guion.PAUSA_ESCENA if ib == len(e["beats"]) - 1 else opc.get("pausa", guion.PAUSA_BEAT)
                partes.append(np.zeros(int(pausa * FS), dtype=np.float32))
                t += int(pausa * FS) / FS
        escenas.append({"id": e["id"], "titulo": e["titulo"], "t0": round(e_t0, 3), "t1": round(t, 3)})
    audio = np.concatenate(partes)
    audio *= 0.89 / max(1e-6, float(np.max(np.abs(audio))))           # pico a -1 dB; la mezcla final normaliza
    with wave.open(str(AUDIO / "voz.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FS)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    subs = subtitulos(palabras)
    total = round(len(audio) / FS, 3)
    DATOS.joinpath("tiempos.json").write_text(json.dumps(
        {"voz": VOZ, "duracion": total, "url": guion.URL, "nombre": guion.NOMBRE, "escenas": escenas, "beats": beats,
         "palabras": palabras, "subtitulos": subs}, ensure_ascii=False, indent=1), encoding="utf-8")
    (AQUI / "salida").mkdir(exist_ok=True)
    (AQUI / "salida" / "reel.srt").write_text(srt(subs), encoding="utf-8")
    for e in escenas:
        print(f"{e['id']} {e['titulo']:<14} {e['t1'] - e['t0']:5.1f} s")
    print(f"total {total:.1f} s · {len(subs)} subtítulos · voz {VOZ}")


if __name__ == "__main__":
    main()
