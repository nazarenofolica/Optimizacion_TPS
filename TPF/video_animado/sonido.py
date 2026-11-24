"""
Música y efectos del reel, sintetizados con numpy (sin samples ni licencias de terceros). Escribe en public/audio/:

  musica.wav     una base lo-fi/pop a 96 BPM (piano eléctrico, bajo, batería y una melodía de marimba), del largo de
                 la voz más el cierre, que baja sola cuando habla la voz (sidechain con la envolvente de voz.wav).
  sfx/*.wav      pop, whoosh, ding, caja (registradora), error, tic, boing, brillo, golpe, zoom, swish, click,
                 teclado, tiza y pasos.

Corre después de voz.py (necesita public/audio/voz.wav y src/datos/tiempos.json).

Uso (desde TPF/video_animado):  python sonido.py
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np

AQUI = Path(__file__).parent
AUDIO = AQUI / "public" / "audio"
FS = 44100
BPM = 96
COLA = 2.4                        # segundos de música después de la última palabra
rng = np.random.default_rng(7)


def escribir(nombre: Path, x: np.ndarray) -> None:
    nombre.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(nombre), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FS)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def leer(nombre: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(nombre), "rb") as w:
        fs = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return x, fs


def hz(nota: int) -> float:                 # MIDI -> Hz
    return 440.0 * 2 ** ((nota - 69) / 12)


def t_(dur: float) -> np.ndarray:
    return np.arange(int(dur * FS)) / FS


def lowpass(x: np.ndarray, fc: float) -> np.ndarray:
    a = np.exp(-2 * np.pi * fc / FS)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):                # un polo; las señales son cortas
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


# ---------------------------------------------------------------- instrumentos

def piano(nota: int, dur: float, vel: float = 1.0) -> np.ndarray:
    t = t_(dur)
    f = hz(nota)
    x = sum(a * np.sin(2 * np.pi * f * k * t + 0.3 * k) * np.exp(-t * (1.6 + 1.2 * k))
            for k, a in ((1, 1.0), (2, 0.45), (3, 0.18), (4, 0.08)))
    x *= 1 + 0.08 * np.sin(2 * np.pi * 4.5 * t)                     # trémolo suave
    ataque = np.minimum(1, t / 0.006)
    return (x * ataque * vel * 0.16).astype(np.float32)


def bajo(nota: int, dur: float, vel: float = 1.0) -> np.ndarray:
    t = t_(dur)
    f = hz(nota)
    x = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
    x = np.tanh(1.6 * x) * np.exp(-t * 3.2) * np.minimum(1, t / 0.004)
    return (x * vel * 0.30).astype(np.float32)


def marimba(nota: int, vel: float = 1.0) -> np.ndarray:
    t = t_(0.7)
    f = hz(nota)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 7) + 0.25 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 22)
    return (x * np.minimum(1, t / 0.002) * vel * 0.12).astype(np.float32)


def bombo(vel: float = 1.0) -> np.ndarray:
    t = t_(0.35)
    f = 48 + 90 * np.exp(-t * 28)
    x = np.sin(2 * np.pi * np.cumsum(f) / FS) * np.exp(-t * 9)
    return (x * vel * 0.55).astype(np.float32)


def palmas(vel: float = 1.0) -> np.ndarray:
    t = t_(0.22)
    n = rng.standard_normal(len(t)).astype(np.float32)
    n = n - lowpass(n, 900)                                          # sin graves
    env = np.exp(-t * 26) + 0.5 * np.exp(-np.maximum(0, t - 0.012) * 30) * (t > 0.012)
    return (n * env * vel * 0.16).astype(np.float32)


def hat(vel: float = 1.0) -> np.ndarray:
    t = t_(0.06)
    n = rng.standard_normal(len(t)).astype(np.float32)
    n = n - lowpass(n, 6000)
    return (n * np.exp(-t * 70) * vel * 0.07).astype(np.float32)


# ---------------------------------------------------------------- música

ACORDES = [  # I - vi - IV - V con séptimas, en Do: alegre pero tranquila
    ([60, 64, 67, 71], 48),   # Cmaj7
    ([57, 60, 64, 67], 45),   # Am7
    ([53, 57, 60, 64], 41),   # Fmaj7
    ([55, 59, 62, 65], 43),   # G7
]
PENTA = [72, 74, 76, 79, 81, 84]


def pegar(buf: np.ndarray, x: np.ndarray, t: float) -> None:
    i = int(t * FS)
    if i >= len(buf):
        return
    n = min(len(x), len(buf) - i)
    buf[i:i + n] += x[:n]


def musica(dur: float) -> np.ndarray:
    buf = np.zeros(int(dur * FS) + FS, dtype=np.float32)
    negra = 60 / BPM
    compas = 4 * negra
    n_compases = int(np.ceil(dur / compas)) + 1
    for c in range(n_compases):
        t0 = c * compas
        notas, raiz = ACORDES[c % 4]
        entra_bateria = c >= 2                                     # dos compases de intro solo con piano
        for golpe, vel in ((0.0, 1.0), (1.5, 0.6), (2.5, 0.75)):   # acordes con síncopa
            for k, n in enumerate(notas):
                pegar(buf, piano(n, 1.6, vel * (0.9 + 0.2 * rng.random())), t0 + golpe * negra + 0.008 * k)
        if entra_bateria:
            for b in (0, 2):
                pegar(buf, bajo(raiz, 0.9), t0 + b * negra)
            pegar(buf, bajo(raiz + 12, 0.4, 0.6), t0 + 3.5 * negra)
            for b in (0, 2):
                pegar(buf, bombo(), t0 + b * negra)
            pegar(buf, bombo(0.5), t0 + 2.75 * negra)
            for b in (1, 3):
                pegar(buf, palmas(), t0 + b * negra)
            for k in range(8):                                     # corcheas con swing
                tt = t0 + (k // 2) * negra + (0.58 * negra if k % 2 else 0)
                pegar(buf, hat(0.55 + 0.45 * (k % 2 == 0) * rng.random() + 0.2), tt)
        if c >= 4 and c % 2 == 0:                                  # una melodía corta cada dos compases
            for k in range(5):
                if rng.random() < 0.75:
                    pegar(buf, marimba(int(rng.choice(PENTA)), 0.7 + 0.3 * rng.random()),
                          t0 + (k * 0.75 + 0.5) * negra)
    buf = buf[:int(dur * FS)]
    fin = t_(dur)
    buf *= np.minimum(1, fin / 0.4) * np.clip((dur - fin) / 2.2, 0, 1)   # entrada y salida
    return buf


def envolvente_voz(voz: np.ndarray, fs: int, n: int) -> np.ndarray:
    """0..1: cuánto está hablando la voz, con ataque rápido y salida lenta (para el ducking)."""
    hop = fs // 100
    rms = np.sqrt(np.convolve(voz ** 2, np.ones(hop) / hop, mode="same"))[::hop]
    activo = (rms > 0.02).astype(np.float32)
    env = np.zeros_like(activo)
    acc = 0.0
    for i, a in enumerate(activo):
        acc = acc + (a - acc) * (0.5 if a > acc else 0.04)        # 20 ms de ataque, ~250 ms de salida
        env[i] = acc
    tt = np.arange(n) / FS
    return np.interp(tt, np.arange(len(env)) / 100, env, right=0).astype(np.float32)


# ---------------------------------------------------------------- efectos

def sfx() -> dict[str, np.ndarray]:
    s = {}
    t = t_(0.12)
    s["pop"] = np.sin(2 * np.pi * np.cumsum(900 * np.exp(-t * 30) + 260) / FS) * np.exp(-t * 38) * 0.6

    t = t_(0.55)
    n = rng.standard_normal(len(t)).astype(np.float32)
    env = np.sin(np.pi * np.clip(t / 0.55, 0, 1)) ** 2
    banda = lowpass(n, 2200) - lowpass(n, 350)
    s["whoosh"] = banda * env * 1.4

    t = t_(1.2)
    f = 1318.5
    s["ding"] = (np.sin(2 * np.pi * f * t) * np.exp(-t * 4) + 0.4 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 9)
                 + 0.15 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 16)) * 0.28

    t = t_(0.9)
    ruido = rng.standard_normal(len(t)) * np.exp(-t * 40) * 0.25
    campana = sum(np.sin(2 * np.pi * f0 * (t - d)) * np.exp(-(t - d) * 5) * (t >= d)
                  for f0, d in ((2093, 0.06), (2637, 0.14)))
    s["caja"] = (ruido + campana * 0.22)

    t = t_(0.42)
    cuadrada = np.sign(np.sin(2 * np.pi * 140 * t)) * 0.5 + np.sign(np.sin(2 * np.pi * 147 * t)) * 0.5
    puertas = ((t % 0.21) < 0.16).astype(np.float32)
    s["error"] = lowpass(cuadrada.astype(np.float32), 1400) * puertas * 0.22

    t = t_(0.03)
    s["tic"] = np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 220) * 0.35

    t = t_(0.45)
    s["boing"] = np.sin(2 * np.pi * np.cumsum(220 + 160 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 6)) / FS) \
        * np.exp(-t * 6) * 0.35

    t = t_(0.9)
    s["brillo"] = sum(np.sin(2 * np.pi * hz(n) * (t - d)) * np.exp(-(t - d) * 7) * (t >= d)
                      for n, d in ((84, 0.0), (88, 0.06), (91, 0.12), (96, 0.18))) * 0.12

    t = t_(0.4)
    s["golpe"] = (np.sin(2 * np.pi * np.cumsum(50 + 70 * np.exp(-t * 25)) / FS) * np.exp(-t * 10) * 0.7
                  + rng.standard_normal(len(t)) * np.exp(-t * 50) * 0.1)

    # Zoom: ruido que sube de brillo y de volumen, con un tono que sube debajo (acercarse).
    t = t_(0.6)
    n = rng.standard_normal(len(t)).astype(np.float32)
    env = (t / 0.6) ** 1.6 * np.clip((0.6 - t) / 0.06, 0, 1)
    brillo = lowpass(n, 3200) - lowpass(n, 500)
    tono = np.sin(2 * np.pi * np.cumsum(180 + 520 * (t / 0.6) ** 2) / FS) * 0.25
    s["zoom"] = (brillo * 1.2 + tono) * env

    # Swish: un whoosh corto y suave, para lo que sale de escena.
    t = t_(0.28)
    n = rng.standard_normal(len(t)).astype(np.float32)
    s["swish"] = (lowpass(n, 2600) - lowpass(n, 700)) * np.sin(np.pi * t / 0.28) ** 2 * 0.9

    # Clic de mouse: dos golpecitos (bajar y soltar el botón).
    t = t_(0.09)
    clic = lambda f0: np.sin(2 * np.pi * f0 * t) * np.exp(-t * 400)  # noqa: E731
    golpe = np.zeros(len(t), dtype=np.float32)
    golpe += clic(3200) * 0.5
    d = int(0.045 * FS)
    golpe[d:] += clic(2600)[: len(t) - d] * 0.35
    s["click"] = golpe + rng.standard_normal(len(t)) * np.exp(-t * 600) * 0.15

    # Teclado: seis teclas en medio segundo, cada una distinta.
    t = t_(0.6)
    tec = np.zeros(len(t), dtype=np.float32)
    for k in range(6):
        i = int((0.02 + k * 0.085 + rng.random() * 0.02) * FS)
        tt = t[: len(t) - i]
        tec[i:] += (np.sin(2 * np.pi * (1800 + 500 * rng.random()) * tt) * np.exp(-tt * 350) * 0.3
                    + rng.standard_normal(len(tt)) * np.exp(-tt * 500) * 0.12)
    s["teclado"] = tec

    # Tiza: un raspado con textura (para el pizarrón).
    t = t_(0.9)
    n = rng.standard_normal(len(t)).astype(np.float32)
    raspa = n - lowpass(n, 2500)
    trazos = 0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 7 * t))
    s["tiza"] = raspa * trazos * np.clip(t / 0.03, 0, 1) * np.clip((0.9 - t) / 0.1, 0, 1) * 0.22

    # Pasos: cuatro pisadas suaves.
    t = t_(1.2)
    pas = np.zeros(len(t), dtype=np.float32)
    for k in range(4):
        i = int(k * 0.3 * FS)
        tt = t[: len(t) - i]
        pas[i:] += (np.sin(2 * np.pi * np.cumsum(70 + 60 * np.exp(-tt * 40)) / FS) * np.exp(-tt * 22) * 0.45
                    + rng.standard_normal(len(tt)) * np.exp(-tt * 60) * 0.06)
    s["pasos"] = pas
    return {k: v.astype(np.float32) for k, v in s.items()}


def main() -> None:
    tiempos = json.loads((AQUI / "src" / "datos" / "tiempos.json").read_text(encoding="utf-8"))
    dur = tiempos["duracion"] + COLA
    m = musica(dur)
    voz, fs = leer(AUDIO / "voz.wav")
    env = envolvente_voz(voz, fs, len(m))
    m *= 0.62 / max(1e-6, float(np.max(np.abs(m))))
    m *= (1.0 - 0.62 * env)                                       # con voz, la música baja unos 8 dB
    escribir(AUDIO / "musica.wav", m)
    for k, v in sfx().items():
        escribir(AUDIO / "sfx" / f"{k}.wav", v)
    print(f"musica.wav {dur:.1f} s · {len(sfx())} efectos")


if __name__ == "__main__":
    main()
