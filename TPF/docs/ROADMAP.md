# Roadmap: de POC a MVP y a producción

Estado al 14/11/2026. Las herramientas citadas están evaluadas, con enlaces y estrellas, en
[GITHUB_RESEARCH.md](GITHUB_RESEARCH.md). Los pendientes de datos y de nutrición que ya se conocían siguen en
[../base_sepa/PLAN_DE_TRABAJO.md](../base_sepa/PLAN_DE_TRABAJO.md).

## Dónde estamos (POC estabilizado)

- Página estática autosuficiente (`datos/sepa/canasta.html`): motor en el navegador (HiGHS en WebAssembly), espejo
  del motor Python, con test de paridad.
- **Nuevo:** búsqueda por tiempo caminando con rutas peatonales reales (OpenRouteService, matriz 1 × N), límite
  configurable (15 min por defecto; 15, 30, 45 o 60), "ver si conviene caminar más" que recalcula sucursales y
  canasta y muestra el ahorro, recorrido a pie en el mapa y respaldo con tiempos estimados, avisado como tal.
- Mapas arreglados (teselas, `localhost`, superposición en el celular, mapas que no se liberaban), ticket con minutos
  caminando, columnas alineadas, promociones como "no aplicadas", resumen nutricional e impresión.
- Límites del POC: la clave de rutas queda visible en la copia local de la página; la cuota gratuita de ORS
  (500 matrices por día) alcanza para pruebas, no para público; datos de un solo día; promociones sin aplicar.

## Lógica de negocio: cómo se optimiza

El objetivo es **la compra más barata que cumple lo que necesita cada persona**, y la arquitectura tiene que separar
qué es obligatorio de qué es preferencia.

**Restricciones duras (definen el conjunto factible):** energía de cada persona (±5 %), restricciones alimentarias,
alergias y trazas, disponibilidad en la sucursal, **tiempo caminando ≤ límite elegido** y, cuando exista, presupuesto
máximo.

**Objetivo principal:** minimizar el costo total.

**Metas nutricionales:** ya se resuelven de forma lexicográfica en dos etapas: (1) minimizar el déficit ponderado de
nutrientes y reglas de las Guías; (2) con ese déficit fijo (holgura 1e-4), minimizar el costo. Es *goal programming*
preventivo y conviene mantenerlo: nunca se cambia nutrición por plata.

**Objetivos secundarios (tiempo, variedad, cadena preferida, promociones).** No se suman con pesos arbitrarios. Se
agregan como etapas lexicográficas con **tolerancia de costo** explícita:

1. Etapa 1 y 2 como hoy → costo mínimo C*.
2. Etapa 3 (opcional, la elige el usuario): optimizar el criterio secundario sujeto a `costo ≤ (1 + τ) · C*`, con τ
   visible ("hasta 3 % más caro"). Por ejemplo, máxima variedad (mínimo de porciones repetidas) o mínima caminata.

Con eso cada preferencia tiene un precio que se puede mostrar ("más variedad te cuesta $X").

**Distancia.** Es una restricción del espacio de búsqueda, no un objetivo: primero se filtran las sucursales
alcanzables y después se optimiza. "Caminar más" amplía el conjunto factible y se reoptimiza; el resultado se
presenta como un **frente costo vs. minutos** (15, 30, 45 y 60 min con su mejor costo), que es la forma honesta de
mostrar el intercambio sin inventar cuánto vale un minuto para cada persona. En el MVP se calcula el frente completo
de una vez (una matriz con el radio de 60 min y un modelo por sucursal, cacheado) y se muestra como una lista
escalonada: "15 min: $23.406 · 30 min: $21.900 (−6 %)".

**Comprar en varias sucursales.** Hoy la compra es en una sola. La extensión es un MILP con variables binarias de
"visito la sucursal s" y un costo fijo en minutos u horas por visita; con dos sucursales se resuelve rápido. Si se
quiere el recorrido óptimo entre varias, es un problema de ruteo (OR-Tools).

## MVP (siguiente etapa, 2 a 4 semanas)

1. **Actualización diaria automática (ETL).**
   - GitHub Actions con cron a la mañana (SEPA exige que los comercios publiquen antes de las 6:00): `python -m sepa
     --descargar` y `python -m canasta --exportar`; publicar la página en GitHub Pages o Cloudflare Pages.
   - Controles: si `sepa/verificacion.py` falla, no se publica y queda la versión del día anterior (ya se detiene sin
     tocar la base); avisar por mail o issue.
   - Sin historial por ahora: cada corrida reemplaza el día anterior (son ~8 millones de precios por día y nada del
     producto los usa). Si más adelante hace falta mostrar tendencias, guardar solo un resumen por producto, cadena y
     día (mediana), no las filas completas.
   - Detección de cambios: comparar contra el día anterior (precios que saltan más de x3, sucursales que desaparecen,
     comercios con archivo viejo: ya se excluyen).
   - Faltantes: un producto sin precio hoy no se arrastra de ayer; una sucursal sin datos del día no se ofrece.
   - Equivalencias entre cadenas: ya existe por EAN y "gemelos"; documentar y testear el emparejamiento.
   - Entorno reproducible con `uv` (hoy hay dos `requirements.txt`).
2. **Backend mínimo (FastAPI)** para: guardar la clave de rutas (deja de estar en la página), cachear las matrices por
   celda de ~100 m (las sucursales no se mueven), y servir el motor Python como API para clientes que no pueden
   correr WebAssembly. La página puede seguir siendo estática y llamar a este backend solo para rutas.
3. **Rutas para público:** autoalojar OpenRouteService u OSRM con el extracto de Argentina de Geofabrik (un VPS de
   4 a 8 GB alcanza para el perfil peatonal), o pasar a Mapbox/Google detrás del backend. Teselas de un proveedor con
   cuota (las de OpenStreetMap no son para tráfico alto).
4. **Frente costo vs. minutos** y objetivos secundarios con tolerancia (arriba).
5. **Tests de la página con Playwright** (hoy: Chrome headless con capturas y paridad) y CI que corra los tests en
   cada push.
6. **Experiencia:** autocompletado de direcciones (Photon sobre OSM; Georef no autocompleta), lista de compras para
   compartir, plan de comidas día por día (idea tomada de Mealbird), restricciones nuevas (sin cerdo, pescetariano,
   exclusión de ingredientes puntuales: salen de los mismos datos de composición).

## Promociones (MVP tardío)

SEPA publica `precio_promocion` sin condiciones. Hace falta otra fuente (catálogos web de las cadenas, que el pipeline
ya recorre) y un modelo de datos:

| Campo | Ejemplo |
|---|---|
| tipo | `porcentaje`, `nxm` (2×1, 3×2), `segunda_unidad` (2.ª al 70 %), `precio_fijo`, `llevando_x` |
| producto(s) | EAN o lista |
| vigencia | desde / hasta, días de la semana |
| condiciones | medio de pago (banco, billetera), tarjeta de la cadena, tope de unidades o de reintegro, compra mínima |
| precio habitual / precio efectivo | se guardan los dos |

En el optimizador, cada promoción es lineal o entera: `nxm` con una variable entera de "packs" (`x_p = n·k + r`),
`segunda_unidad` igual con pares, topes como cota superior, compra mínima con una binaria. El usuario declara qué medios
de pago tiene; **una promoción solo se aplica si se cumplen todas sus condiciones**, y el ticket muestra precio de
lista, descuento y precio efectivo por renglón.

## Condiciones médicas y requerimientos específicos

Anemia, deficiencias de vitaminas, embarazo de riesgo, etc. El motor ya ajusta metas (hierro y zinc vegetarianos,
sodio con hipertensión, azúcares con diabetes). Para ampliar:

- Una tabla versionada de **ajustes por condición** (`referencia/condiciones.csv`): condición → meta modificada →
  fuente bibliográfica (NASEM, OMS, guías argentinas) → "requiere supervisión profesional" sí/no.
- Solo se ofrecen condiciones con fuente; las que requieren supervisión muestran el aviso y no cambian metas por
  encima de los máximos tolerables.
- Nunca diagnóstico ni suplementación: la canasta sigue siendo comida del supermercado.

## LLM con Groq (después del MVP)

**Rol:** interpretar pedidos en lenguaje natural ("algo barato para mí y mi hija, ella es celíaca y yo tengo anemia")
y convertirlos en el **pedido estructurado** que ya consume el motor (`personas`, `restricciones`, `dias`,
`caminata_minutos`, condiciones). No elige productos, no inventa precios ni nutrientes, no reemplaza al optimizador.

**Diseño:**
1. El backend recibe el texto y llama a Groq con salida estructurada (JSON Schema del pedido; modo estricto en los
   modelos que lo soportan, según la documentación de Groq). Clave en `GROQ_API_KEY`, solo en el backend.
2. Se valida el JSON contra el mismo esquema y contra `canasta/config.py` (restricciones y condiciones conocidas); lo
   que no se reconoce se pregunta al usuario, no se adivina.
3. Se muestra el formulario ya completado para que la persona confirme antes de calcular.
4. Opcional: explicar el resultado en lenguaje simple a partir del JSON del motor (con los números del motor, sin
   recalcular nada).

**Cuándo:** cuando exista el backend (la clave no puede ir en la página) y las condiciones médicas tengan su tabla con
fuentes. Antes no aporta: el formulario actual cubre lo que el motor sabe hacer.

## Producción

| Pieza | Propuesta | Costo orientativo |
|---|---|---|
| Página | Estática en Cloudflare Pages o GitHub Pages | Gratis |
| ETL diario | GitHub Actions (o Dagster/Prefect si crecen las fuentes) | Gratis en repo público; si no, minutos de Actions |
| Backend + rutas | FastAPI + ORS/OSRM autoalojado en un VPS (Coolify para desplegar) | USD 10 a 40 por mes |
| Datos | Parquet del último día; Postgres (Supabase) recién cuando haya cuentas | Gratis al inicio |
| Monitoreo | Sentry (backend, job y página) + alerta si el job no publicó | Plan gratis al inicio |
| Entornos | `main` → producción, `develop` → previsualización (Pages las da por rama) | — |

**Cuándo dejar la página 100 % estática:** cuando haya que proteger claves (rutas, Groq), cachear rutas entre
usuarios, guardar historial consultable o cuentas de usuario. El motor puede seguir en el navegador (no cuesta
servidor) y el backend ocuparse solo de lo que necesita secreto o estado.
