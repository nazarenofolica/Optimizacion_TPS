# Investigación de GitHub: qué reutilizar para llevar la canasta de POC a producción

Relevamiento del 14/11/2026. Estrellas, licencia y última actividad (`pushed_at`) salen de la API de GitHub (`gh api
repos/<owner>/<repo>`) el mismo día; las cuotas de los servicios, de sus páginas oficiales o de terceros cuando lo
oficial no se pudo leer (está marcado). Nada de esto se eligió por estrellas: el criterio es qué problema concreto de
la canasta resuelve, con el stack que tiene hoy.

**Stack actual, para leer las recomendaciones:** pipeline en Python (pandas, pyarrow, scipy/HiGHS), tablas en parquet,
y una página HTML estática autosuficiente en JavaScript sin framework: el motor (`motor.js`) resuelve el modelo con
HiGHS en WebAssembly dentro de un Web Worker; mapas con Leaflet + OpenStreetMap; geocodificación con Georef. No hay
backend ni base de datos.

Recomendación: **Incorporar** (ya o en el MVP), **Estudiar** (sirve, pero más adelante o con dudas) o **Descartar**.

---

## 1. Skills incorporadas ahora (en `TPF/.claude/skills/`)

Se eligieron cuatro, sin solaparse: una de diseño, dos de método y una propia del proyecto.

| Skill | Origen | ★ | Actividad | Licencia | Para qué |
|---|---|---|---|---|---|
| `impeccable` | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | 110.144 | 14/11/2026 | Apache-2.0 | Diseño y pulido de interfaces: registro *product*, jerarquía, contraste, estados vacíos y de error, antipatrones. Se usó para rediseñar el resultado y el ticket. |
| `systematic-debugging` | [obra/superpowers](https://github.com/obra/superpowers) | 317.601 | 03/11/2026 | MIT | Encontrar la causa raíz antes de arreglar (útil con dos motores que tienen que coincidir). |
| `verification-before-completion` | [obra/superpowers](https://github.com/obra/superpowers) | 317.601 | 03/11/2026 | MIT | No dar algo por terminado sin la salida de los tests o la página funcionando. |
| `canasta-verificar` | propia | — | — | — | Cómo exportar, servir, capturar y testear la canasta (unitarios, paridad Python/JS, revisión manual). |

**Compatibilidad revisada.** `impeccable` no depende de React ni de Tailwind: sus guías sirven para HTML/CSS
plano. Sus scripts son Node, solo locales, salvo una consulta de versión a `impeccable.style` en `context.mjs`. Sus
rutas internas suponen `.agents/skills/impeccable/`; en este repo están en `.claude/skills/impeccable/`. De
superpowers se copiaron las dos carpetas tal cual (commit `22f0b463e7a5`), con la licencia en
`.claude/skills/LICENSE-superpowers`. Los ejemplos en TypeScript y el `find-polluter.sh` (que usa `npm test`) quedan
como referencia: no aplican a este proyecto.

**Evaluadas y no incorporadas**

| Repo | ★ | Licencia | Por qué no |
|---|---|---|---|
| [anthropics/skills](https://github.com/anthropics/skills) (`frontend-design`) | 194.560 | sin SPDX | Buena, pero se superpone con `impeccable`, que es más completa para UI de producto. Se queda como alternativa liviana. |
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) (`design-taste-frontend`) | 115.574 | MIT | Pensada para landings y portfolios, con dirección de arte; la canasta es una herramienta. |
| [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | 47.286 | Apache-2.0 | Directorio de plugins; nada específico que falte. |
| [affaan-m/ECC](https://github.com/affaan-m/ECC) | 302.955 | MIT | Un arnés completo (memoria, instintos, seguridad): demasiado para un POC. |
| [wshobson/agents](https://github.com/wshobson/agents) | 42.510 | MIT | Decenas de agentes genéricos; preferimos pocos y propios. |
| [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills), [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills), [travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) | 79.499 / 37.184 / 15.817 | — / MIT / — | Listas curadas: útiles para buscar, no para instalar. |

**Herramientas para agentes (estudiar):** [ChromeDevTools/chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp)
(★ 56.222, Apache-2.0) y [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) (★ 39.646, Apache-2.0)
permiten que el agente abra la página, haga clics y lea la consola. Hoy se verifica con Chrome headless
(`--screenshot`, `--dump-dom`); en el MVP, con tests de Playwright de verdad (ver §4). [anthropics/claude-code-action](https://github.com/anthropics/claude-code-action)
(★ 9.953, MIT) sirve para revisar PRs en CI.

---

## 2. Mapas, rutas y geolocalización

### 2.1 Proveedor de rutas peatonales: comparación y decisión

| | OpenRouteService | Mapbox | Google Maps Platform | GraphHopper |
|---|---|---|---|---|
| Rutas a pie | `foot-walking` (y `foot-hiking`) | `walking` | `WALK` | `foot` (en el plan gratis, "perfiles limitados": a confirmar) |
| Datos y cobertura en Argentina | OpenStreetMap: muy buena en ciudades, depende de OSM en pueblos | OSM + propios | Propios, la mejor | OpenStreetMap |
| Matriz 1 × N | `/v2/matrix`, hasta 3.500 pares por consulta | Matrix API, 25 coordenadas por consulta | Compute Route Matrix | Matrix, 5 ubicaciones por consulta en el plan gratis |
| Cuota gratis | Standard: 2.000 rutas/día, **500 matrices/día**, 40/min (página oficial sin fecha; confirmar en el panel de HeiGIT) | 100.000 elementos de matriz por mes (fuentes de terceros) | Essentials: 10.000 elementos/mes, después USD 5 cada 1.000 (precios oficiales) | 500 créditos/día, solo uso no comercial |
| Tarjeta de crédito | No | Sí, al pasar el gratis | Cuenta con facturación obligatoria | No (plan gratis) |
| Clave en una página estática | Visible; sin restricción por dominio | Token público restringible por URL | Clave restringible por referrer | Visible |
| Producción | Bien para empezar; se puede autoalojar (GPL-3.0, [GIScience/openrouteservice](https://github.com/GIScience/openrouteservice), ★ 1.993) | Muy viable | Muy viable, la más cara | Limitada por la cuota |

**Elegido: OpenRouteService.** Es gratis y sin tarjeta, tiene un perfil peatonal real sobre OSM y una matriz 1 × N
que resuelve con una sola consulta lo que la canasta necesita: los minutos caminando desde el usuario hasta todas
las sucursales candidatas. Con 500 matrices por día alcanza para un POC con pocos usuarios. Para producción hay dos
caminos sin rehacer nada: autoalojar ORS (u [OSRM](https://github.com/Project-OSRM/osrm-backend), ★ 8.221, BSD-2,
o [Valhalla](https://github.com/valhalla/valhalla), ★ 6.455) con el extracto de Argentina de Geofabrik, o pasar a
Mapbox o Google detrás de un backend que guarde la clave. `rutas.js` y `rutas.py` aíslan al proveedor: cambiarlo es
cambiar dos funciones.

### 2.2 Librerías del mapa

| Repo | ★ | Actividad | Licencia | Qué podemos usar | Recomendación |
|---|---|---|---|---|---|
| [Leaflet/Leaflet](https://github.com/Leaflet/Leaflet) | 45.925 | 14/11/2026 | BSD-2 | Ya está en uso (1.9.4); la polilínea del recorrido y los marcadores alcanzan. | Incorporar (sigue) |
| [GIScience/openrouteservice-js](https://github.com/GIScience/openrouteservice-js) | 251 | 08/05/2026 | Apache-2.0 | Cliente JS de ORS. Para dos endpoints, `fetch` directo es más chico y sin dependencias. | Descartar por ahora |
| [perliedman/leaflet-routing-machine](https://github.com/perliedman/leaflet-routing-machine) | 1.188 | 11/03/2024 | otra | Control de rutas con indicaciones; sin cambios desde 2024. | Descartar |
| [Leaflet/Leaflet.markercluster](https://github.com/Leaflet/Leaflet.markercluster) | 4.174 | 13/11/2026 | MIT | Agrupar marcadores si se muestran todas las sucursales de una ciudad. | Estudiar (MVP) |
| [maplibre/maplibre-gl-js](https://github.com/maplibre/maplibre-gl-js) | 12.088 | 13/11/2026 | otra | Mapas vectoriales con estilo propio; útil si se buscan teselas propias. | Estudiar (producción) |
| [datosgobar/georef-ar-api](https://github.com/datosgobar/georef-ar-api) | 183 | 28/10/2026 | MIT | La API de geocodificación que ya usamos; se puede autoalojar. | Incorporar (sigue) |
| [komoot/photon](https://github.com/komoot/photon), [osm-search/Nominatim](https://github.com/osm-search/Nominatim) | 3.193 / 4.563 | 14/11 / 03/11/2026 | Apache-2.0 / GPL-3.0 | Autocompletado de direcciones sobre OSM (Georef no autocompleta). | Estudiar (MVP) |

**Teselas.** La URL con subdominios `{s}.tile.openstreetmap.org` está deprecada y, abierta desde `file://`, la página
no manda `Referer`, que la política de uso de OSM exige: esa era la causa probable del mapa gris. Se pasó a
`tile.openstreetmap.org` y `python -m canasta` sirve la página por `http://localhost`. En producción conviene un
proveedor de teselas con cuota (MapTiler, Stadia, Protomaps autoalojado): las de OSM no son para tráfico alto.

---

## 3. Optimización

| Repo | ★ | Actividad | Licencia | Qué podemos usar | Recomendación |
|---|---|---|---|---|---|
| [ERGO-Code/HiGHS](https://github.com/ERGO-Code/HiGHS) | 1.927 | 14/11/2026 | MIT | El solver que ya usamos (scipy en Python, WASM en la página). | Incorporar (sigue) |
| [lovasoa/highs-js](https://github.com/lovasoa/highs-js) | 91 | 16/10/2026 | MIT | HiGHS en WebAssembly (lo carga `motor.js`). Pocas estrellas pero activo y es el único que existe. | Incorporar (sigue) |
| [coin-or/pulp](https://github.com/coin-or/pulp) | 2.498 | 13/11/2026 | otra | Modelado legible (lo usaron TP1–TP3). Para el backend del MVP si se reescribe el modelo. | Estudiar |
| [Pyomo/pyomo](https://github.com/Pyomo/pyomo) | 2.565 | 13/11/2026 | otra | Modelado algebraico con soporte de objetivos múltiples y bloques; más pesado que PuLP. | Estudiar |
| [google/or-tools](https://github.com/google/or-tools) | 14.377 | 13/11/2026 | Apache-2.0 | CP-SAT y ruteo de vehículos: sirve para "comprar en varias sucursales y volver a casa". | Estudiar (producción) |
| [cvxpy/cvxpy](https://github.com/cvxpy/cvxpy) | 6.394 | 12/11/2026 | Apache-2.0 | Convexa; no aporta sobre un MILP como el nuestro. | Descartar |
| [the-dual-space/pymoo](https://github.com/the-dual-space/pymoo) | 2.996 | 12/11/2026 | Apache-2.0 | Metaheurísticas multiobjetivo (NSGA-II). Con un MILP exacto conviene la estrategia lexicográfica o ε-restricción; pymoo solo si el modelo deja de ser lineal. | Descartar por ahora |
| [j2kun/lp-diet](https://github.com/j2kun/lp-diet) | 34 | 05/02/2026 | sin licencia | Experimentos del problema de la dieta; útil para comparar formulaciones, no para reutilizar (sin licencia). | Estudiar |

**Conclusión para el MVP:** no hace falta cambiar de solver. El modelo ya es jerárquico (primero cumplir, después
lo más barato) y los objetivos secundarios se agregan como etapas lexicográficas o con ε-restricción sobre el mismo
HiGHS (detalle en [ROADMAP.md](ROADMAP.md)).

---

## 4. Ingeniería de datos y precios

| Repo | ★ | Actividad | Licencia | Qué podemos usar | Recomendación |
|---|---|---|---|---|---|
| GitHub Actions (cron) | — | — | — | Correr `python -m sepa --descargar` y `python -m canasta --exportar` cada mañana y publicar la página. Gratis en repos públicos; el ZIP de SEPA (~320 MB) entra en el runner. | Incorporar (MVP) |
| [duckdb/duckdb](https://github.com/duckdb/duckdb) | 43.071 | 13/11/2026 | MIT | Consultar parquet con SQL sin servidor. Un historial de precios no hace falta hoy (8 millones de filas por día sin uso en el producto); queda para cuando haya tendencias que mostrar. | Estudiar |
| [pola-rs/polars](https://github.com/pola-rs/polars) | 40.340 | 14/11/2026 | MIT | Acelerar el pipeline (8 millones de precios) si pandas queda corto en el runner. | Estudiar |
| [PrefectHQ/prefect](https://github.com/PrefectHQ/prefect) | 24.158 | 14/11/2026 | Apache-2.0 | Orquestación con reintentos y observabilidad. | Estudiar (producción) |
| [dagster-io/dagster](https://github.com/dagster-io/dagster) | 16.424 | 13/11/2026 | Apache-2.0 | Orquestación por "assets" (dim_producto, fact_precio), con linaje. Encaja con el modelo estrella. | Estudiar (producción) |
| [apache/airflow](https://github.com/apache/airflow) | 47.479 | 14/11/2026 | Apache-2.0 | Estándar de la industria, pero pesado para un job diario. | Descartar |
| [dlt-hub/dlt](https://github.com/dlt-hub/dlt) | 6.094 | 14/11/2026 | Apache-2.0 | Carga incremental desde APIs (catálogos web, promociones) a parquet o DuckDB. | Estudiar (MVP) |
| [openfoodfacts/openfoodfacts-python](https://github.com/openfoodfacts/openfoodfacts-python) | 478 | 01/11/2026 | otra | Consultar productos puntuales por EAN en vez del dump de 1,2 GB. | Estudiar |
| [catdevnull/sepa-precios-metadata](https://github.com/catdevnull/sepa-precios-metadata) | 2 | 14/11/2026 | sin licencia | Historial de los metadatos del dataset SEPA (qué archivo hay cada día). Sirve para detectar si salió el ZIP del día. | Estudiar |
| [catdevnull/preciazo](https://github.com/catdevnull/preciazo) | 25 | 01/09/2026 | sin licencia | Análisis de precios de supermercados argentinos con scrapers propios; referencia de cómo otros siguen precios y promociones. | Estudiar (sin licencia: solo ideas) |
| [OpenDataCordoba/precios_claros](https://github.com/OpenDataCordoba/precios_claros) | 28 | 10/09/2022 | sin licencia | Scraper del portal Precios Claros; abandonado desde 2022 y SEPA ya publica el ZIP diario. | Descartar |

**Promociones.** SEPA trae `precio_promocion` sin las condiciones (2×1, segunda unidad, medio de pago, tope). Ningún
repo relevado las normaliza; hay que leerlas de los catálogos web (VTEX de Jumbo, Disco y Vea, que el pipeline ya
recorre) y modelarlas (ver ROADMAP).

---

## 5. Backend, infraestructura y LLM

| Repo | ★ | Actividad | Licencia | Qué podemos usar | Recomendación |
|---|---|---|---|---|---|
| [fastapi/fastapi](https://github.com/fastapi/fastapi) | 104.713 | 14/11/2026 | MIT | Backend chico que guarde las claves (rutas, Groq), cachee rutas y sirva el resultado del motor Python. | Incorporar (MVP) |
| [astral-sh/uv](https://github.com/astral-sh/uv) | 92.001 | 14/11/2026 | Apache-2.0 | Entorno y dependencias reproducibles para CI (hoy hay dos requirements.txt). | Incorporar (MVP) |
| [nektos/act](https://github.com/nektos/act) | 72.695 | 14/11/2026 | MIT | Probar los workflows de GitHub Actions en local. | Estudiar |
| [supabase/supabase](https://github.com/supabase/supabase) | 115.023 | 14/11/2026 | Apache-2.0 | Postgres gestionado con auth si hace falta guardar hogares y listas. No antes de tener usuarios. | Estudiar (producción) |
| [coollabsio/coolify](https://github.com/coollabsio/coolify) | 66.077 | 14/11/2026 | Apache-2.0 | PaaS autoalojado (un VPS chico) para backend + ORS propio. | Estudiar (producción) |
| [streamlit/streamlit](https://github.com/streamlit/streamlit) | 46.353 | 14/11/2026 | Apache-2.0 | Ya está contemplado para embeber la página; no aporta para el consumidor final. | Descartar como front |
| [getsentry/sentry-python](https://github.com/getsentry/sentry-python) | 2.219 | 14/11/2026 | MIT | Errores del backend y del job diario (y el SDK de JS para la página). | Incorporar (producción) |
| [groq/groq-python](https://github.com/groq/groq-python) | 622 | 04/09/2026 | Apache-2.0 | Cliente oficial de Groq. La API admite salidas estructuradas con JSON Schema (modo estricto en modelos seleccionados, según la documentación). | Incorporar (cuando toque el LLM) |

---

## 6. Referencia funcional: Mealbird

Se buscó cómo personaliza la dieta. Por sus fichas públicas, Mealbird se centra en **macros y calorías** (datos de
USDA FoodData Central), en que ningún día quede por debajo de la meta y en **conectar el plan con el costo** (totales
de compra y servicios de delivery). No se encontró documentación pública de sus filtros de restricciones o alergias;
no se copió nada. Lo que vale como idea para el ROADMAP: mostrar el plan día por día (no solo la compra), y la lista
de compras como salida. Las restricciones de la canasta (celiaquía con trazas, ocho alergias, vegano, hipertensión,
diabetes) ya son más estrictas que las de las apps de planificación relevadas.

---

## 7. Resumen por etapa

- **Ahora (POC):** skills `impeccable`, `systematic-debugging`, `verification-before-completion`, `canasta-verificar`;
  OpenRouteService (matriz + recorrido) con `fetch`; Leaflet con teselas OSM bien configuradas.
- **MVP:** GitHub Actions con cron diario y publicación estática; `uv`; tests de la página con Playwright; backend FastAPI chico para las claves y la caché de rutas; autocompletado de direcciones (Photon).
- **Producción:** ORS u OSRM autoalojado con el extracto de Argentina; orquestación con Dagster o Prefect si el job
  crece; Sentry; teselas con proveedor; Postgres (Supabase) solo cuando haya cuentas de usuario; Groq para
  interpretar pedidos.

## Fuentes de cuotas y precios

- OpenRouteService, planes: <https://openrouteservice.org/?p=176> (Standard) y <https://openrouteservice.org/plans/>
  (redirige a la cuenta de HeiGIT, que no se pudo leer sin iniciar sesión).
- Mapbox: <https://www.woosmap.com/blog/mapbox-pricing>, <https://superdupr.com/blog/mapbox-pricing> (terceros).
- Google Maps Platform: <https://developers.google.com/maps/billing-and-pricing/pricing>.
- GraphHopper: <https://www.graphhopper.com/pricing/>, <https://docs.graphhopper.com/openapi/section/plans-and-rate-limits>.
- Groq, salidas estructuradas: <https://console.groq.com/docs/structured-outputs>.
- Mealbird: <https://mwm.ai/apps/mealbird/6794577462>.
- SEPA en datos abiertos: <https://www.datos.gob.ar/th/dataset/produccion-precios-claros---base-sepa>.
