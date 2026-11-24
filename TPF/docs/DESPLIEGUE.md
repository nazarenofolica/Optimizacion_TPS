# Despliegue: ETL diario y CI

Etapa 3 del [ROADMAP](ROADMAP.md). Tres workflows de GitHub Actions, en la raíz del repositorio
(`.github/workflows/`, donde GitHub los busca), que solo se ocupan de `TPF/`:

| Workflow | Cuándo corre | Qué hace |
|---|---|---|
| [`tpf-tests.yml`](../../.github/workflows/tpf-tests.yml) · "TPF · tests" | En cada push y pull request que toque `TPF/` (TP1 a TP3 no lo disparan) y a mano | La suite de Python; la paridad con el navegador, solo a mano |
| [`tpf-diario.yml`](../../.github/workflows/tpf-diario.yml) · "TPF · ETL diario y página" | Todos los días a las 07:30 y a las 18:00 (Argentina) y a mano | Baja SEPA, rearma la base, exporta la página y la publica en Cloudflare Pages. Corre en el **runner propio** (ver abajo) |
| [`pages.yml`](../../.github/workflows/pages.yml) · "Demo en Cloudflare Pages" | Solo a mano | Respaldo: publica la `canasta.html` versionada (la base del repo) desde un runner de GitHub. No corre en cada push porque pisaría la página del día; como no publica `fecha.txt`, la corrida siguiente del diario vuelve a publicar la del día |

La página pública es **Changuito sano: https://changuito-sano.pages.dev/** (Cloudflare Pages, proyecto
`changuito-sano`). La dirección anterior, https://nazarenofolica.github.io/Optimizacion_TPS/, quedó como redirección
(rama `gh-pages`: `index.html`, `canasta.html` y `404.html` mandan a la nueva y conservan `?perfiles=...&lat=...`), así
que los enlaces de la presentación, el informe y el video siguen andando.

### Por qué un runner propio y Cloudflare Pages

Desde noviembre de 2026 la API de SEPA (`datos.produccion.gob.ar`) responde **403** a las IPs de los runners de
GitHub, y lo mismo es de esperar de cualquier servicio en la nube del exterior (Cloudflare, Netlify y Vercel compilan
en AWS o Google, y además cortan la compilación a los 15 o 20 minutos). Desde una conexión en Argentina responde bien.
Por eso el ETL corre en una **PC del equipo**, registrada como runner de GitHub Actions, y publica con una subida
directa (`wrangler pages deploy`) sin commitear la página del día. Cloudflare Pages da, además, una dirección sin
"github" en el nombre.

- **Runner:** `pc-canasta`, etiquetas `self-hosted, Windows, X64, canasta`, instalado en
  `C:\Users\Leandro\actions-runner` (se arranca con `run.cmd`; ver "Activarlo"). Usa el Python 3.10 de la PC en un
  entorno propio (`base_sepa/.venv`), Node para `wrangler` y el bash de Git for Windows.
- **Cloudflare:** el secreto `CLOUDFLARE_API_TOKEN` del repo (un token con un solo permiso, *Account → Cloudflare
  Pages → Edit*). El Account ID no es secreto (aparece en las URLs del dashboard) y está en los workflows.
- **Seguridad:** el repo es público, así que los workflows de pull requests de forks piden aprobación para **todo**
  colaborador externo (*Settings → Actions → General → Approval for running fork pull request workflows*), para que
  nadie pueda correr código en la PC con un PR.

## El ETL diario

Cada corrida, en el runner propio:

1. Hace el checkout **sin limpiar los archivos ignorados** (`clean: false`): `base_sepa/datos/` (cachés y ZIP) y
   `base_sepa/.venv/` quedan de una corrida a la otra. Instala `base_sepa/requirements.txt` en ese entorno (con todo ya
   instalado, tarda segundos).
2. **¿Hay un día nuevo?** `python -m sepa --ultima-fecha` pregunta a la API de SEPA la fecha del último ZIP (sin
   bajarlo) y la compara con `fecha.txt` del sitio publicado. Si el sitio ya tiene ese día, la corrida termina **bien y
   sin cambios**, con el aviso "Sin novedades" en el resumen. Si la API de SEPA no responde, la corrida falla (es un
   error real). **Salvo un 403** (SEPA bloquea al runner): la corrida termina bien, con el aviso "SEPA bloqueó al
   runner", sin publicar y sin abrir ni cerrar el issue.
3. Las fuentes que no cambian a diario ya están en el disco del runner (ver "Modo diario").
4. `python -m sepa --diario`: baja el ZIP del día (~330 MB) y rearma `TPF/datos/sepa/` con los 71 controles de
   `sepa/verificacion.py`. **Si un control crítico falla, la corrida se detiene antes de escribir la base**, el job
   falla y la página publicada sigue siendo la del último día bueno. Las tablas que no pasaron quedan en el artefacto
   `corrida-fallida` (7 días) y el resumen de la corrida dice qué control falló.
5. `python -m canasta --exportar`: la página con los datos del día. Se controla que lleve `{"clave": ""}`: la clave
   de OpenRouteService nunca se publica (la carpeta del runner no tiene `.env`) y la página estima los minutos
   caminando por distancia, como ya hace sin clave.
6. Arma el sitio (`_site/`): la página como `index.html` (es un único HTML autosuficiente, así que la URL del sitio
   abre la canasta sin redirección y los enlaces con `?perfiles=...&lat=...` funcionan en la raíz), la misma como
   `canasta.html` (el nombre que usan la presentación y los documentos; Cloudflare la sirve también como `/canasta`)
   y `fecha.txt` con el día de los precios.
7. Publica con `npx wrangler pages deploy` en el proyecto `changuito-sano`. **No se commitea nada**: la base del día
   vive en el runner y en el sitio (no hay historial de precios, que está fuera de alcance, y el repo no crece).
8. Si algo falló, abre un issue "ETL diario de la canasta: falló la corrida" (uno solo: si ya hay uno abierto, lo
   comenta) y lo cierra cuando una corrida vuelve a andar. GitHub además le manda un mail al dueño del repo.

Dos corridas por día porque SEPA sube el ZIP de cada día a su API recién a la tarde (el del viernes 20/11/2026 figura
modificado a las 16:20). La de las 18:00 publica el día; la de las 07:30 es el reintento: si la de la tarde anduvo,
termina en un minuto con "Sin novedades".

### Modo diario: qué se recalcula y qué se cachea

`python -m sepa --diario` es `--descargar` sin intervención: con las cachés en su lugar hace exactamente lo mismo, y si
faltan los catálogos web (un equipo nuevo) los recorre como `--actualizar-web`, en lugar de cortarse (sin ellos el
pipeline no puede armar las categorías de góndola y se corta).

| Qué | Cada día | Dónde está |
|---|---|---|
| ZIP de SEPA (~330 MB) | Se baja (y se borra el del día anterior) | API de datos.produccion.gob.ar → `base_sepa/datos/entrada/` |
| Lectura, tiendas, productos, precios, verificación | Se rehacen (dependen del día) | — |
| Open Food Facts (dump ~1,2 GB + selección) | Se reutiliza; se vuelve a bajar solo a los 30 días (`DIAS_VIGENCIA_OFF`) y se vuelve a leer si hay más de 1 % de EAN nuevos | `base_sepa/datos/cache/openfoodfacts/` |
| Catálogos de Jumbo, Disco y Vea + clasificador de categorías | Se reutilizan; se recorren de nuevo solo a mano (`actualizar_web`) o si faltan | `base_sepa/datos/cache/web/` |
| Georef, USIG, barrios de CABA, USDA | Se reutilizan; solo se consulta lo nuevo (una sucursal nueva) | `base_sepa/datos/cache/geo/` y `usda/` |
| Tablas curadas (`referencia/`) | — | Versionadas |

Las rutas son dentro de la carpeta del runner
(`C:\Users\Leandro\actions-runner\_work\Optimizacion_TPS\Optimizacion_TPS\TPF\`), no de la copia de trabajo de cada
uno. La primera vez se copiaron ahí las cachés de una copia local (~1,8 GB), para no volver a bajar Open Food Facts ni
recorrer los catálogos. Si se borran, la corrida siguiente las rearma (tarda bastante más; el límite del job es de 3
horas).

**Memoria y disco:** el pipeline está pensado para una máquina de 8 GB. En disco, ~1,8 GB de cachés más un pico de
~3 GB durante la corrida (ZIP, precios intermedios y salidas).

### Que no se acumule

El runner es una PC de uso diario, así que lo que ocupa en disco **no crece con los días**:

- El ZIP de SEPA: al bajar el nuevo se borra el anterior (`sepa/fuentes/sepa.py`); hay uno solo.
- La base (`TPF/datos/sepa/` en la carpeta del runner) se borra y se rehace en cada corrida (`sepa/salida.py`).
- Open Food Facts y los catálogos web tienen nombre fijo: cuando se renuevan, se pisan.
- `corrida_fallida/` se borra en la corrida siguiente que sale bien; `_site/` se rehace en cada corrida.
- La carpeta temporal del job (log de `python -m sepa` y los de `wrangler`, por `WRANGLER_LOG_PATH`) la borra el
  runner al terminar.
- Los logs del runner (`_diag/`, uno por corrida) son lo único que se sumaría: el último paso borra los de más de 14
  días.
- pip no guarda caché (`PIP_NO_CACHE_DIR`) y `wrangler` tiene la versión fija, así que `npx` lo baja una sola vez.
- Si quedan menos de 6 GB libres (`DISCO_MINIMO_GB`), la corrida no arma la base: falla con ese aviso y se abre el
  issue.

Para sacar todo: `.\config.cmd remove --token <token>` en la carpeta del runner (el token sale de
`gh api -X POST repos/nazarenofolica/Optimizacion_TPS/actions/runners/remove-token --jq .token`), borrar
`C:\Users\Leandro\actions-runner` y, si se puso, `runner-canasta.vbs` de la carpeta Inicio.

### Si una fuente externa falla

| Fuente | Qué pasa |
|---|---|
| API o ZIP de SEPA | La corrida falla; queda la página anterior |
| API de SEPA con 403 (bloquea al runner) | La corrida termina bien con un aviso, sin publicar; queda la página anterior |
| Open Food Facts, USDA, barrios de CABA (solo sin caché) | La corrida falla; queda la página anterior |
| Georef (solo para lo que no está en la caché) | Reintenta 4 veces y falla; queda la página anterior |
| USIG (direcciones de CABA) | No corta la corrida: la dirección queda sin validar y esa respuesta vacía queda en la caché (ver pendientes) |
| Catálogos web (solo cuando se recorren) | Si no responde el árbol de categorías, la corrida falla; una página o búsqueda que falla 4 veces se saltea y el catálogo queda incompleto |
| Verificación (`sepa/verificacion.py`) | La corrida falla antes de escribir la base; queda la página anterior |

## Los tests en cada push

`tpf-tests.yml` corre, desde `TPF/base_sepa`, `python -m unittest discover -s tests -v`, igual que en la máquina. Los
tests que usan la base leen los parquet versionados de `TPF/datos/sepa/` (vienen en el checkout), no usan internet ni
la clave de rutas (sin `.env` los tiempos se estiman) y la paridad con el navegador queda omitida, como en local.

La **paridad** (Chrome headless, ~5 min) se corre a mano: Actions → "TPF · tests" → *Run workflow* → tildar
"paridad". Si la página no llega a calcular en Chrome, el test se omitiría; en ese job una omisión cuenta como falla.

Python 3.10 en los tests (variable `PYTHON_VERSION` de `tpf-tests.yml`) y en el runner propio (el de la PC: el
diario lo controla), el mismo que se usa en la máquina, para que lo que pasa en uno pase en el otro. Python 3.10 dejó
de tener soporte en octubre de 2026: conviene pasar la máquina y los workflows juntos a 3.12 (en el runner, borrar
`base_sepa/.venv` de su carpeta para que se rehaga). Las dependencias tienen rangos, no versiones fijas: Actions
instala las últimas que entran (por ejemplo numpy 2 y scikit-learn 1.7, contra numpy 1.26 y scikit-learn 1.4 en la
máquina del equipo). La etapa "entorno reproducible con `uv`" las fijaría.

## Activarlo (una sola vez)

Estado al 24/11/2026: hechos el proyecto de Cloudflare, el secreto, el runner `pc-canasta` y la redirección de GitHub
Pages. El cron corre con el workflow de `main`, así que empieza a correr solo cuando la rama `cloudflare-pages` llega a
`main`.

**Cloudflare** (una vez): crear la cuenta, un token con *Account → Cloudflare Pages → Edit* y cargarlo con
`gh secret set CLOUDFLARE_API_TOKEN` (pide el valor; no queda en ningún archivo ni en el historial). La primera
corrida de `pages.yml` crea el proyecto `changuito-sano`.

**Runner** (una vez por PC):

1. Bajar el runner de Windows x64 de https://github.com/actions/runner/releases a `C:\Users\Leandro\actions-runner`
   (controlar el SHA-256 de las notas de la versión) y descomprimirlo.
2. Registrarlo con un token de registro (dura una hora):
   ```powershell
   $t = gh api -X POST repos/nazarenofolica/Optimizacion_TPS/actions/runners/registration-token --jq .token
   .\config.cmd --unattended --url https://github.com/nazarenofolica/Optimizacion_TPS --token $t --name pc-canasta --labels canasta --work _work
   ```
3. Arrancarlo: `.\run.cmd` (queda escuchando mientras la ventana esté abierta). Para que arranque solo al iniciar
   sesión, sin ventana, poner en la carpeta Inicio (`Win+R` → `shell:startup`) un `runner-canasta.vbs` con:
   ```vb
   CreateObject("WScript.Shell").Run """C:\Users\Leandro\actions-runner\run.cmd""", 0, False
   ```
   Para dejar de usarlo, borrar ese archivo. (Como servicio de Windows también se puede, pero pide permisos de
   administrador y la contraseña de la cuenta, para que el servicio encuentre el Python del usuario.)
4. Opcional: copiar las cachés de una copia local a la carpeta del runner (ver "Modo diario").

En *Settings → Actions → Runners* figura `pc-canasta` como *Idle* (conectado) u *Offline*.

**Probar:** **Actions → "TPF · ETL diario y página" → Run workflow**. Al terminar, abrir https://changuito-sano.pages.dev/
y `.../fecha.txt` (el día de los precios publicados).

Desde ahí corre solo, **mientras la PC esté prendida y con la sesión iniciada**: si a la hora del cron está apagada, la
corrida queda en cola y arranca cuando el runner se conecta; GitHub la cancela si pasan 24 horas. "Run workflow" tiene dos opciones: **forzar** (rearmar y publicar aunque el sitio ya tenga el
último día) y **actualizar_web** (volver a recorrer los catálogos de Jumbo, Disco y Vea; conviene cada tanto, por
ejemplo una vez por mes, porque aparecen productos nuevos).

## Ver qué pasó

- **Actions → "TPF · ETL diario y página"**: cada corrida tiene un resumen (día publicado, "Sin novedades" o en qué
  paso falló) y el log completo de cada paso; el de "Armar la base" es el de `python -m sepa`, con los 71 controles.
- Si falló la verificación: artefacto `corrida-fallida` de esa corrida (las tres tablas en parquet).
- **Issues**: "ETL diario de la canasta: falló la corrida", abierto mientras siga fallando.
- El log del runner: `C:\Users\Leandro\actions-runner\_diag\`.
- Las publicaciones: dashboard de Cloudflare → *Workers & Pages* → `changuito-sano` (cada subida, con su URL propia).

## Límites

- Los minutos del runner propio no cuentan en la cuota de Actions; los de `tpf-tests.yml` y `pages.yml` (runners de
  GitHub) son gratis en un repo público. Cloudflare Pages es gratis (500 publicaciones por mes; se usan a lo sumo dos
  por día) y el repo podría pasar a privado sin afectar la página.
- La página se actualiza solo si la PC del runner está prendida en algún momento del día; si no, queda la del último
  día publicado.
- GitHub **desactiva los cron** de un repo público después de 60 días sin actividad en el repositorio: avisa por mail
  y se reactivan con un clic en Actions (o con cualquier commit).
- Los cron de GitHub pueden demorarse (de minutos a más de una hora en horas pico) y no están garantizados.
- La cuota gratuita de rutas de OpenRouteService no aplica: la página publicada no lleva clave.

## Texto libre con Groq (etapa 6): solo en la página local

"Contalo con tus palabras" necesita la clave de Groq, y una clave no puede ir en una página estática: cualquiera que
la abra la ve. Por eso la traducción la hace un servidor, y **en la página publicada no hay servidor** (Cloudflare
Pages sirve archivos, no ejecuta `canasta/servidor.py`): la página publicada no muestra el bloque ni consulta nada. Funciona en la página local, servida por
`python -m canasta`, que suma dos rutas (`/api/estado` y `/api/interpretar`, `canasta/servidor.py`) solo para esta
máquina. Para el público hace falta un backend propio (FastAPI que envuelva `canasta/llm.py`; ver "Producción" en el
[ROADMAP](ROADMAP.md)).

Para usarlo:

1. Crear una clave gratuita en https://console.groq.com/keys.
2. En `base_sepa/.env` (copiado de `.env.example`; no se versiona), poner `GROQ_API_KEY=gsk_...`.
3. Desde `base_sepa/`, `python -m canasta`: la consola dice "Texto libre: con Groq" y la página lo ofrece en el paso 1.

La clave queda solo en el servidor local: no va en `canasta.html` ni en `canasta_local.html` (`exportar.py` corta la
exportación si la encontrara) y Actions no la tiene ni la necesita. El texto se manda a Groq con la confirmación de la
persona y no se guarda ni se escribe en el log. Sin clave, `python -m canasta --llm-simulado` prueba la página con
respuestas de ejemplo (solo para desarrollo; la página avisa que es una simulación).

## Cambiar el horario

En `.github/workflows/tpf-diario.yml`, bajo `schedule`, cada `cron` es "minuto hora día mes día-de-la-semana" en
**UTC** (Argentina = UTC−3). Por ejemplo, `"0 22 * * *"` es a las 19:00 de Argentina; `"30 10 * * 1-5"`, a las 07:30
de lunes a viernes. Se cambia en `main`, porque es la que mira el cron.

## Pendientes de esta etapa

- **Controles contra el día anterior** (precios que saltan más de x3, sucursales que desaparecen): el pipeline no los
  tiene. Los comercios que no publicaron el día entran con su último archivo si tiene a lo sumo 15 días
  (`DIAS_TOLERANCIA_PRECIO`, con su fecha por sucursal); los más viejos se excluyen.
- Una respuesta vacía de USIG (por una caída del servicio) queda en la caché de geografía como "no encontrada": la
  dirección no se vuelve a consultar. Cambiarlo cambia lo que produce el pipeline, así que queda anotado.
- Open Food Facts: el dump de ~1,2 GB queda en el disco del runner aunque casi todos los días alcanza con la selección
  guardada; usar solo la selección cambiaría el resultado los días con más de 1 % de EAN nuevos.
- Un solo runner: si la PC se rompe o cambia, hay que registrar otro (ver "Activarlo"). Un servidor en Argentina (VPS)
  con el mismo runner evitaría depender de que la PC esté prendida.
- Entorno reproducible con `uv`, tests de la página con Playwright y del motor JavaScript con Node.
