# Reel animado

La versión para redes del video explicativo (`../video`), para presentar **Changuito Sano**
(https://changuito-sano.pages.dev): un reel vertical (1080×1920) de casi tres minutos y una versión horizontal
(1920×1080) para LinkedIn o una presentación, con stickmans, procesos animados, subtítulos palabra por palabra, música y efectos. Cuenta el problema de la
dieta con los capítulos del video largo y sus mismos números (que salen del informe), y suma uno propio: las tres
formas de pagar menos. Todo se genera con código: si cambia una frase, se vuelve a correr y la animación se
resincroniza sola.

## Capítulos

| # | Escena | Qué se ve |
|---|---|---|
| 1 | La pregunta | Stigler en 1945, la dieta de harina, repollo y espinaca, y el salto al súper de hoy con Sofi. |
| 2 | Los datos | 8 millones de precios, el mapa hecho con las sucursales reales y 28.000 productos. |
| 3 | La página | La grabación real de la página (con sus clics y su tipeo), el ticket, $24.000 por semana y 37/37 metas. |
| 4 | El modelo | Dos objetivos, λ tachada, metas lexicográficas; etapa 1 (rango L–U, Δ déficit y exceso, mín Φ) y etapa 2 (tres condiciones). |
| 5 | Un ejemplo | Más despacio y en cinco pasos, con un marcador que se tilda y "Tu compra" en vivo (el punto del plano): las tarjetas de lentejas y arroz se vuelven los ejes, la franja de energía, la recta de proteína, la región factible, la recta de costo que baja al vértice ($1.420), el precio sombra explicado (+1 g → +$21) y 300 g: la región desaparece y el modelo llega a 150 g. |
| 6 | Casos reales | Tres hogares que cumplen todo, la persona celíaca y alérgica a la leche en Córdoba (los gráficos de bala de la página) y los precios sombra: calcio y lácteos. |
| 7 | Tu bolsillo | Un marcador con tres formas de pagar menos (mes −26 %, caminar −25 %, dos súper −62 %), con el mismo gráfico de antes y después. |
| 8 | Cierre | La moraleja y la página, con Stigler y Sofi juntos. |

## Cómo se arma

| Paso | Archivo | Qué hace |
|---|---|---|
| 1 | [`guion.py`](guion.py) | El guion: ocho escenas, cada una con sus *beats* (una a tres oraciones que se dicen de corrido). `{escrito\|dicho}` para cifras. Es la fuente única. |
| 2 | [`voz.py`](voz.py) | Sintetiza cada beat entero (edge-tts), une con pausas y escribe la voz, el tiempo de cada palabra (`src/datos/tiempos.json`) y el `.srt`. |
| 3 | [`sonido.py`](sonido.py) | Sintetiza la música (lo-fi/pop a 96 BPM, que baja sola cuando habla la voz) y 15 efectos. Sin samples de terceros. |
| 4 | [`datos.py`](datos.py) | El mapa con las sucursales reales (de `datos/sepa`), dos cortes de la grabación real de la página (`../video/salida/pagina`) y cuándo hace clic y tipea el cursor en ella. |
| 5 | [`src/`](src) | Las escenas en [Remotion](https://www.remotion.dev) (React). Cada animación se engancha a una palabra dicha: `cuadro("b05", "sucursales")`. |
| 6 | [`render.py`](render.py) | Renderiza y normaliza el audio a −14 LUFS (el nivel de Instagram). `--horizontal` hace la versión 1920×1080. |

```powershell
cd TPF/video_animado
npm install                       # una vez
python voz.py                     # pide internet (edge-tts)
python sonido.py
python datos.py                   # necesita ../video/salida/pagina (correr ../video/grabar.py si no está)
npm run dev                       # vista previa interactiva (Remotion Studio)
python render.py                  # salida/canasta_reel.mp4  (--borrador: a media resolución)
python render.py --horizontal     # salida/canasta_horizontal.mp4
```

Salida (no versionada): `salida/canasta_reel.mp4`, `salida/canasta_horizontal.mp4` y `salida/reel.srt` (por si se
quieren subir los subtítulos aparte; ya van quemados en el video).

La versión horizontal ([`src/Horizontal.tsx`](src/Horizontal.tsx)) usa las mismas escenas: las recorta a su zona de
animación y las pone en un escenario a la derecha; a la izquierda va un panel con la marca, el capítulo actual y el
índice, y abajo los subtítulos a lo ancho. Cualquier cambio en una escena sale en las dos.

## La voz

`es-AR-TomasNeural`, rioplatense, a +12 % (el ejemplo, a +6 % y con pausas más largas, para que se entienda). Lo que la aleja de "robótica": se sintetiza por bloques de una a tres
oraciones (y no frase por frase), el guion está escrito para decirse (preguntas, voseo, oraciones cortas) y va con
música debajo. Se verificó transcribiéndola con Whisper contra el guion: todas las palabras se entienden.

Para escuchar otras voces y cambiarla:

```powershell
python muestras_voz.py            # salida/muestras/<voz>.mp3
$env:VOZ="es-AR-ElenaNeural"; python voz.py; python sonido.py   # o cambiar guion.VOZ
```

Las Multilingual (por ejemplo `en-US-EmmaMultilingualNeural`) entonan más, pero con acento neutro.

## Diseño

- **Una cosa a la vez.** Cada escena se arma en partes (`Parte`): la siguiente entra recién cuando la anterior terminó
  de irse. Nada se dibuja encima de otra cosa (ni una cruz sobre un objeto): lo que cambia, cambia en su lugar.
- **Los gráficos se calculan.** Las rectas, la región factible y la recta de costo del ejemplo salen de las ecuaciones;
  cuando se piden 300 g, el eje se agranda para que la recta siga a la vista (como en el video largo).
- **Todo suena.** Cada elemento que entra hace "pop" y cada uno que sale, "swish"; los sellos golpean, los zooms suenan
  a zoom, los contadores hacen tic, y los clics y el tipeo de la grabación tienen su sonido.
- **Gancho en los primeros 3 segundos**: el titular ("La dieta más barata del mundo") y el sello de 1945 están desde el
  primer cuadro.
- **Una protagonista que cruza el video**: Sofi (el caso de la oficinista), que entra al final de 1945 con el changuito.
- **Algo se mueve siempre**: el fondo se desplaza, las stickmans respiran y parpadean, y cada palabra clave dispara un
  elemento.
- **Lenguaje de movimiento único**: entradas con resorte y un poco de rebote, salidas que aceleran, transiciones de dos
  paneles en diagonal.
- **Zona segura de Reels**: nada importante arriba de 230 px ni debajo de 1470 px, para que no lo tapen los botones de
  Instagram. Los subtítulos van entre 1260 y 1460.
- Reglas tomadas de las skills de Remotion (`remotion-dev/skills`), Motion Design (`iart-ai/motion-design-skills`),
  Claude Animation Base y Anidoodle.

## Créditos

- Voz: Microsoft Edge TTS, vía [edge-tts](https://github.com/rany2/edge-tts).
- Animación: [Remotion](https://www.remotion.dev) (gratis para equipos de hasta 3 personas).
- Tipografías: Fredoka, Montserrat e Inter (SIL Open Font License), vía Google Fonts.
- Música y efectos: sintetizados en `sonido.py`.
