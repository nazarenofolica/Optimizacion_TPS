# Despliegue: ETL diario y CI

Etapa 3 del [ROADMAP](ROADMAP.md). Tres workflows de GitHub Actions, en la raíz del repositorio
(`.github/workflows/`, donde GitHub los busca), que solo se ocupan de `TPF/`:

| Workflow | Cuándo corre | Qué hace |
|---|---|---|
| [`tpf-tests.yml`](../../.github/workflows/tpf-tests.yml) · "TPF · tests" | En cada push y pull request que toque `TPF/` (TP1 a TP3 no lo disparan) y a mano | La suite de Python; la paridad con el navegador, solo a mano |
| [`tpf-diario.yml`](../../.github/workflows/tpf-diario.yml) · "TPF · ETL diario y página" | Todos los días a las 07:30 y a las 18:00 (Argentina) y a mano | Baja SEPA, rearma la base, exporta la página y la publica en GitHub Pages |
| [`pages.yml`](../../.github/workflows/pages.yml) · "Demo en GitHub Pages" | Solo a mano | Respaldo: publica la `canasta.html` versionada (la base del repo). No corre en cada push porque pisaría la página del día; como no publica `fecha.txt`, la corrida siguiente del diario vuelve a publicar la del día |

La página pública queda en **https://nazarenofolica.github.io/Optimizacion_TPS/**. Hoy (21/11/2026) muestra la
versionada, que publicó `pages.yml` con el merge a `main`; la del día llega con la primera corrida del diario.

## El ETL diario

Cada corrida, en un runner Ubuntu limpio:

1. Instala Python 3.10 y `base_sepa/requirements.txt` (con caché de pip).
2. **¿Hay un día nuevo?** `python -m sepa --ultima-fecha` pregunta a la API de SEPA la fecha del último ZIP (sin
   bajarlo) y la compara con `fecha.txt` del sitio publicado. Si el sitio ya tiene ese día, la corrida termina **bien y
   sin cambios**, con el aviso "Sin novedades" en el resumen. Si la API de SEPA no responde, la corrida falla (es un
   error real). **Salvo un 403**: `datos.produccion.gob.ar` bloquea las IPs de los runners de GitHub (desde noviembre
   de 2026), así que la corrida termina bien, con el aviso "SEPA bloqueó al runner", sin publicar y sin abrir ni cerrar
   el issue. Mientras dure el bloqueo, la página se actualiza corriendo el ETL desde una máquina en Argentina.
3. Restaura de la caché de Actions las fuentes que no cambian a diario (ver "Modo diario").
4. `python -m sepa --diario`: baja el ZIP del día (~330 MB) y rearma `TPF/datos/sepa/` con los 71 controles de
   `sepa/verificacion.py`. **Si un control crítico falla, la corrida se detiene antes de escribir la base**, el job
   falla y la página publicada sigue siendo la del último día bueno. Las tablas que no pasaron quedan en el artefacto
   `corrida-fallida` (7 días) y el resumen de la corrida dice qué control falló.
5. `python -m canasta --exportar`: la página con los datos del día. Se controla que lleve `{"clave": ""}`: la clave
   de OpenRouteService nunca se publica (en Actions no hay ninguna) y la página estima los minutos caminando por
   distancia, como ya hace sin clave.
6. Arma el sitio (`_site/`): la página como `index.html` (es un único HTML autosuficiente, así que la URL del sitio
   abre la canasta sin redirección y los enlaces con `?perfiles=...&lat=...` funcionan en la raíz), la misma como
   `canasta.html` (el nombre que usan la presentación y los documentos) y `fecha.txt` con el día de los precios.
7. Publica con `actions/upload-pages-artifact` + `actions/deploy-pages`. **No se commitea nada**: la base del día
   vive en el runner y en el sitio (no hay historial de precios, que está fuera de alcance, y el repo no crece).
8. Guarda las cachés que cambiaron (solo si todo salió bien).
9. Si algo falló, abre un issue "ETL diario de la canasta: falló la corrida" (uno solo: si ya hay uno abierto, lo
   comenta) y lo cierra cuando una corrida vuelve a andar. GitHub además le manda un mail al dueño del repo.

Dos corridas por día porque SEPA sube el ZIP de cada día a su API recién a la tarde (el del viernes 20/11/2026 figura
modificado a las 16:20). La de las 18:00 publica el día; la de las 07:30 es el reintento: si la de la tarde anduvo,
termina en un minuto con "Sin novedades".

### Modo diario: qué se recalcula y qué se cachea

`python -m sepa --diario` es `--descargar` sin intervención: con las cachés en su lugar hace exactamente lo mismo, y si
faltan los catálogos web (un equipo nuevo) los recorre como `--actualizar-web`, en lugar de cortarse (sin ellos el
pipeline no puede armar las categorías de góndola y se corta).

| Qué | Cada día | Cómo llega al runner |
|---|---|---|
| ZIP de SEPA (~330 MB) | Se baja | API de datos.produccion.gob.ar |
| Lectura, tiendas, productos, precios, verificación | Se rehacen (dependen del día) | — |
| Open Food Facts (dump ~1,2 GB + selección) | Se reutiliza; se vuelve a bajar solo a los 30 días (`DIAS_VIGENCIA_OFF`) y se vuelve a leer si hay más de 1 % de EAN nuevos | Caché `tpf-off-*` |
| Catálogos de Jumbo, Disco y Vea + clasificador de categorías | Se reutilizan; se recorren de nuevo solo a mano (`actualizar_web`) o si faltan | Caché `tpf-web-*` |
| Georef, USIG, barrios de CABA, USDA | Se reutilizan; solo se consulta lo nuevo (una sucursal nueva) | Caché `tpf-ref-*` |
| Tablas curadas (`referencia/`) | — | Versionadas |

Las cachés se guardan con una huella del contenido en la clave (nombre, tamaño y fecha de cada archivo): solo se sube
una nueva cuando algo cambió, y cada corrida restaura la más reciente. Se guardan solo si la corrida salió bien, para
que un catálogo cortado a la mitad no quede guardado.

**Tiempos, memoria y disco** (estimados: el workflow no se pudo correr en GitHub desde acá):

- Corrida diaria con cachés: ~20 a 40 min (restaurar ~1,5 GB de caché, bajar el ZIP, el pipeline y la exportación).
- Primera corrida, sin cachés: bastante más (baja Open Food Facts, lo lee en una pasada de ~4 min, recorre los tres
  catálogos web con pausas entre pedidos y consulta Georef y USIG por todas las sucursales). El límite del job es de
  3 horas.
- "Sin novedades": ~2 min.
- Memoria: el pipeline está pensado para una máquina de 8 GB; los runners de un repo público tienen 16 GB (los de uno
  privado, 7 GB).
- Disco: pico de ~5 GB (dependencias, cachés, ZIP, precios intermedios y salidas) sobre ~14 GB libres.

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

Python 3.10 en los dos workflows, el mismo que se usa en la máquina, para que lo que pasa en uno pase en el otro.
Python 3.10 dejó de tener soporte en octubre de 2026: conviene pasar la máquina y los workflows juntos a 3.12
(variable `PYTHON_VERSION` al principio de cada workflow). Las dependencias tienen rangos, no versiones fijas: Actions
instala las últimas que entran (por ejemplo numpy 2 y scikit-learn 1.7, contra numpy 1.26 y scikit-learn 1.4 en la
máquina del equipo). La etapa "entorno reproducible con `uv`" las fijaría.

## Activarlo (una sola vez)

Estado al 21/11/2026: los pasos 1 a 3 están hechos (merge del PR #2; Pages con origen "GitHub Actions"; los tests ya
corren y pasan en Actions). Falta el 4: la primera corrida del diario.

1. Commitear y pushear los cambios. El workflow de tests ya corre en ese push (pestaña **Actions**).
2. Llevar los cambios a `main` (merge del pull request). El cron solo corre con el workflow de la rama principal, y el
   entorno `github-pages`, por defecto, solo deja publicar desde ella.
3. **Settings → Pages → Build and deployment → Source: "GitHub Actions"**.
4. **Actions → "TPF · ETL diario y página" → Run workflow** (rama `main`) para la primera corrida, que arma las cachés
   y tarda más. Al terminar, el job "Publicar en GitHub Pages" muestra la URL.
5. Abrir https://nazarenofolica.github.io/Optimizacion_TPS/ y `.../fecha.txt` (el día de los precios publicados).

Desde ahí corre solo. "Run workflow" tiene dos opciones: **forzar** (rearmar y publicar aunque el sitio ya tenga el
último día) y **actualizar_web** (volver a recorrer los catálogos de Jumbo, Disco y Vea; conviene cada tanto, por
ejemplo una vez por mes, porque aparecen productos nuevos).

## Ver qué pasó

- **Actions → "TPF · ETL diario y página"**: cada corrida tiene un resumen (día publicado, "Sin novedades" o en qué
  paso falló) y el log completo de cada paso; el de "Armar la base" es el de `python -m sepa`, con los 71 controles.
- Si falló la verificación: artefacto `corrida-fallida` de esa corrida (las tres tablas en parquet).
- **Issues**: "ETL diario de la canasta: falló la corrida", abierto mientras siga fallando.
- Las cachés: **Actions → Caches** (se pueden borrar para obligar a rearmarlas).

## Límites

- **Repo público** (como está hoy): los minutos de Actions en runners estándar y GitHub Pages son gratis.
- **Si el repo pasara a privado**: GitHub Pages en un repo privado requiere un plan pago (Pro, Team o Enterprise), o
  volver a hacerlo público; y los minutos de Actions dejan de ser ilimitados (el plan gratis trae 2.000 por mes; dos
  corridas por día, casi siempre "Sin novedades" una de ellas, entran, pero los runners privados tienen 7 GB de
  memoria).
- GitHub **desactiva los cron** de un repo público después de 60 días sin actividad en el repositorio: avisa por mail
  y se reactivan con un clic en Actions (o con cualquier commit).
- Los cron de GitHub pueden demorarse (de minutos a más de una hora en horas pico) y no están garantizados.
- Caché de Actions: 10 GB por repositorio; lo que no se usa en 7 días se borra. Con una corrida por día, las cachés en
  uso no vencen; si vencen, la corrida siguiente las rearma (como la primera).
- La cuota gratuita de rutas de OpenRouteService no aplica: la página publicada no lleva clave.

## Texto libre con Groq (etapa 6): solo en la página local

"Contalo con tus palabras" necesita la clave de Groq, y una clave no puede ir en una página estática: cualquiera que
la abra la ve. Por eso la traducción la hace un servidor, y **en GitHub Pages no hay servidor** (sirve archivos, no
ejecuta código): la página publicada no muestra el bloque ni consulta nada. Funciona en la página local, servida por
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
- Open Food Facts: el dump de ~1,2 GB viaja en la caché aunque casi todos los días alcanza con la selección guardada;
  usar solo la selección cambiaría el resultado los días con más de 1 % de EAN nuevos.
- Entorno reproducible con `uv`, tests de la página con Playwright y del motor JavaScript con Node.
