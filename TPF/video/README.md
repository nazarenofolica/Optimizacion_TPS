# Video explicativo

A video of about four and a half minutes that tells the project end to end, in seven chapters. A neural voice in Rioplatense Spanish narrates it, and everything is generated with code. If a number or a sentence changes, you run it again and the video updates.

## How it is built

| Step | File | What it does |
|---|---|---|
| 1 | [`guion.py`](guion.py) | The script: the phrases of each scene, with how each one is read and how it is said (`{1945\|mil novecientos cuarenta y cinco}`) and where each subtitle is cut (`/`). It is the single source. |
| 2 | [`voz.py`](voz.py) | Synthesizes each phrase separately (edge-tts, voice `es-AR-ElenaNeural`), trims the silence and joins them with measured pauses. It writes the audio, the timing of each word and the timing of each subtitle. |
| 3 | [`datos_video.py`](datos_video.py) | Pulls the branch coordinates for the map out of the database. |
| 4 | [`escenas.py`](escenas.py) | The animated scenes (Manim), synced with the voice. The grid, transitions and components are in [`estilo.py`](estilo.py). |
| 5 | [`grabar.py`](grabar.py) | Records the real page (`datos/sepa/canasta.html`) while filling in the form. |
| 6 | [`montar.py`](montar.py) | Puts the recording inside the browser window (scene 3) with crops that follow the voice. It joins everything, normalizes the volume and writes the subtitles. |

```powershell
cd TPF/video
pip install manim edge-tts imageio-ffmpeg selenium websocket-client pillow pyarrow
python voz.py
python datos_video.py
python -m manim -qh --media_dir salida/manim escenas.py E1Pregunta E2Datos E3Marco E4Modelo E5Ejemplo E6Casos E7Cierre
python grabar.py                  # needs Chrome; only if the page changed
python montar.py
```

The output goes to `salida/` (not versioned): `canasta_saludable.mp4`, `canasta_saludable_subtitulado.mp4` and `canasta_saludable.srt`. The animations need LaTeX (MiKTeX) for the formulas. For a quick draft: `-ql --media_dir salida/manim_borrador`.

## Design

- **Grid.** Each frame is built as a single group and centered in the usable area (`estilo.encuadrar`). The chapter goes at the top left, the progress (six segments) at the top right, and the bottom strip is left free for the subtitles.
- **Transitions.** Old content rises and leaves, new content rises and appears (`Escena.cambiar`). Between scenes everything fades except the progress bar, which carries into the next scene and fills its new segment.
- **Voice.** One phrase at a time, with the pause the script asks for. Pronunciation was checked by transcribing each scene with Whisper and comparing it word by word against the script.

## Chapters

| # | Scene | What you see |
|---|---|---|
| — | The question | 1945, Stigler's question, the diet problem, flour-cabbage-spinach, and the title. |
| 1 | The data | The map of Argentina made from the real branches, the counters and the three things known about each product. |
| 2 | The page | The real page inside a browser window: the form, the calculation, the ticket, the map, the total and the 37 goals. |
| 3 | The model | Two objectives, lexicographic goals, stage 1 (deviations from a range) and stage 2 (cheapest, whole packages). |
| 4 | An example | Pasta, lentils and rice on the plane: **when the goals can be met** (60 g of protein, the optimum at a vertex, the shadow price) and **when they cannot** (300 g: the feasible region disappears, the model reaches 150 g and reports the shortfall). |
| 5 | Cases | Four households that meet everything, gaining weight, a person with celiac disease and a milk allergy who does not meet two goals, walking more and two supermarkets. |
| 6 | Sensitivity | Shadow prices, week versus month, conclusions and the page's address. |

## Credits

- Voice: Microsoft Edge TTS (`es-AR-ElenaNeural`), via [edge-tts](https://github.com/rany2/edge-tts).
- Animations: [Manim Community](https://www.manim.community/).
- Typeface: IBM Plex Sans and Plex Mono (SIL Open Font License, see `fuentes/OFL.txt`).
- Page maps: © OpenStreetMap contributors.
