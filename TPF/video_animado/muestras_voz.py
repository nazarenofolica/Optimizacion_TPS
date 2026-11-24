"""
Muestras para elegir la voz: el mismo fragmento del guion con varias voces, en salida/muestras/<voz>.mp3.
Escuchalas y poné la que más te guste en guion.VOZ (o corré `VOZ=<voz> python voz.py`).

Uso (desde TPF/video_animado):  python muestras_voz.py
"""

import asyncio
from pathlib import Path

import edge_tts

from guion import VELOCIDAD

VOCES = [
    "es-AR-TomasNeural", "es-AR-ElenaNeural", "es-UY-ValentinaNeural", "es-UY-MateoNeural",
    "en-US-EmmaMultilingualNeural", "en-US-AvaMultilingualNeural", "en-US-AndrewMultilingualNeural",
]
TEXTO = ("En mil novecientos cuarenta y cinco, un economista calculó la dieta más barata del mundo. "
         "¿El resultado? Harina, repollo y espinaca. Todo el año. Barata, sí. Pero nadie la querría comer.")

SALIDA = Path(__file__).parent / "salida" / "muestras"


async def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    for v in VOCES:
        await edge_tts.Communicate(TEXTO, v, rate=VELOCIDAD).save(str(SALIDA / f"{v}.mp3"))
        print(SALIDA / f"{v}.mp3")


if __name__ == "__main__":
    asyncio.run(main())
