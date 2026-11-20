# Roadmap: de POC a MVP y a producción

Estado al 20/11/2026. Las herramientas citadas están evaluadas, con enlaces y estrellas, en
[GITHUB_RESEARCH.md](GITHUB_RESEARCH.md). Los pendientes de datos y de nutrición que ya se conocían siguen en
[../base_sepa/PLAN_DE_TRABAJO.md](../base_sepa/PLAN_DE_TRABAJO.md); la lista para tildar, en
[../CHECKLIST.md](../CHECKLIST.md).

## Dónde estamos

### POC estabilizado (14/11/2026)

- Página estática autosuficiente (`datos/sepa/canasta.html`): motor en el navegador (HiGHS en WebAssembly), espejo
  del motor Python, con test de paridad.
- Búsqueda por tiempo caminando con rutas peatonales reales (OpenRouteService, matriz 1 × N), límite configurable
  (15 min por defecto; 15, 30, 45 o 60), "ver si conviene caminar más" que recalcula sucursales y canasta y muestra
  el ahorro, recorrido a pie en el mapa y respaldo con tiempos estimados, avisado como tal.
- Mapas arreglados (teselas, `localhost`, superposición en el celular, mapas que no se liberaban), ticket con minutos
  caminando, columnas alineadas, promociones como "no aplicadas", resumen nutricional e impresión.
- Límites del POC que siguen: la clave de rutas queda visible en la copia local de la página; la cuota gratuita de
  ORS (500 matrices por día) alcanza para pruebas, no para público; datos de un solo día; promociones sin aplicar;
  compra en una sola sucursal; lo más barato no siempre es lo habitual (harina, hígado); 10 a 18 s por cálculo.

### Etapa 1 del MVP (20/11/2026): lo que se pidió después de la presentación

- **Objetivo "Aumentar de peso"**, distinto de "Ganar masa muscular": +500 kcal/día sobre el gasto, proteína
  1,2 g/kg y aviso si el IMC ya es de sobrepeso. Perfil `bajo_peso` (mujer de 22 años, 46 kg, 165 cm, IMC 16,9):
  2.310 kcal/día.
- **El agua como restricción, con tres modos** (`AGUA_MODOS`, `?agua=` en la página y `--agua` en la consola):
  `canilla` (predeterminado; informativo: dice cuánta tomar de la canilla, no cuesta nada y los resultados de antes
  no cambian), `compra` (agua total de NASEM 2004, 2,7 L mujer y 3,7 L varón, contando la de los alimentos; se compra
  agua o soda envasada) y `bebidas` (los 8 vasos ≈ 2 L de las Guías Alimentarias, sin contar la de los alimentos).
  En el caso de la demo (oficinista en el Microcentro, 15 min, rutas reales) la semana pasa de $23.406 a $33.223 con
  el agua comprada y cumple las 38 metas.
- **Un caso que no llega a las 37 metas**, precargado: perfil `restricciones_extremas` (celíaca y alérgica a leche,
  huevo, soja, maní y frutos secos), solo listos para comer, centro de Córdoba, 15 min. Ninguna de las 10 sucursales
  llega; la mejor cubre 35 de 37 (calcio 76 %, lácteos 0 % porque no hay bebida vegetal apta), $205.550 la semana.
  La página lo avisa, muestra cuánto cubre cada meta y sugiere qué probar.
- Tests: 114 en Python y 2 de paridad entre el navegador y Python, con 8 casos (incluidos el agua y el caso que no
  llega a las 37).

## Lógica de negocio: cómo se optimiza

El objetivo es **la compra más barata que cumple lo que necesita cada persona**, y la arquitectura tiene que separar
qué es obligatorio de qué es preferencia.

**Restricciones duras (definen el conjunto factible):** energía de cada persona (±5 %), restricciones alimentarias,
alergias y trazas, disponibilidad en la sucursal, **tiempo caminando ≤ límite elegido**, el agua si el hogar la
compra y, cuando exista, presupuesto máximo.

**Objetivo principal:** minimizar el costo total.

**Metas nutricionales:** ya se resuelven de forma lexicográfica en dos etapas: (1) minimizar el déficit ponderado de
nutrientes y reglas de las Guías; (2) con ese déficit fijo (holgura 1e-4), minimizar el costo. Es *goal programming*
preventivo y conviene mantenerlo: nunca se cambia nutrición por plata.

**Objetivos secundarios (tiempo, variedad, cadena preferida, promociones).** No se suman con pesos arbitrarios. Se
agregan como pasos lexicográficos con **tolerancia de costo** explícita:

1. Pasos 1 y 2 del modelo, como hoy → costo mínimo C*.
2. Paso 3 (opcional, lo elige el usuario): optimizar el criterio secundario sujeto a `costo ≤ (1 + τ) · C*`, con τ
   visible ("hasta 3 % más caro"). Por ejemplo, máxima variedad (mínimo de porciones repetidas) o mínima caminata.

Con eso cada preferencia tiene un precio que se puede mostrar ("más variedad te cuesta $X").

**Distancia.** Es una restricción del espacio de búsqueda, no un objetivo: primero se filtran las sucursales
alcanzables y después se optimiza. "Caminar más" amplía el conjunto factible y se reoptimiza; el resultado se
presenta como un **frente costo vs. minutos** (15, 30, 45 y 60 min con su mejor costo), que es la forma honesta de
mostrar el intercambio sin inventar cuánto vale un minuto para cada persona. Se puede calcular el frente completo
de una vez (una matriz con el radio de 60 min y un modelo por sucursal, cacheado) y mostrarlo como una lista
escalonada: "15 min: $23.406 · 30 min: $21.900 (−6 %)".

**Comprar en varias sucursales.** Hoy la compra es en una sola. La extensión es un MILP con variables binarias de
"visito la sucursal s" y un costo fijo por visita; con dos sucursales se resuelve rápido. Es la etapa 2 (abajo).

## El camino al MVP: etapas 2 a 6

Cada etapa se planifica y se cierra por separado, con sus tests y la paridad entre los dos motores.

### Etapa 2 · Compra en varias sucursales (híbrido)

Si dos supermercados quedan cerca, puede convenir llevar casi todo de uno y algo puntual del otro (las naranjas más
baratas en B aunque la compra general convenga en A).

- MILP sobre las sucursales alcanzables: `x[p,s]` envases del producto `p` en la sucursal `s` y una binaria `y[s]`
  de "visito la sucursal s", con `x[p,s] ≤ M · y[s]`.
- Un costo por visita (en pesos, o minutos convertidos con un valor que se muestra) para que no aparezcan compras
  partidas por ahorros mínimos, y un máximo de visitas (dos, para empezar).
- Se mantiene el esquema lexicográfico: primero cumplir, después lo más barato (ahora con las visitas). Se compara
  contra la mejor sucursal sola y se muestra la diferencia ("partiendo la compra ahorrás $X").
- Ticket por sucursal y recorrido a pie entre las dos (el tiempo entre sucursales sale de la misma matriz de rutas).
  Si se quiere el recorrido óptimo entre varias, es un problema de ruteo (OR-Tools).
- Tamaño: con 10 sucursales y ~200 alimentos son unas 2.000 variables enteras más 10 binarias; hay que medir el
  tiempo en el navegador antes de permitir más de dos visitas.

### Etapa 3 · ETL diario y CI

- GitHub Actions con cron a la mañana (SEPA exige que los comercios publiquen antes de las 6:00): `python -m sepa
  --descargar` y `python -m canasta --exportar`; publicar la página en GitHub Pages o Cloudflare Pages.
- Controles: si `sepa/verificacion.py` falla, no se publica y queda la versión del día anterior (ya se detiene sin
  tocar la base); avisar por mail o issue.
- Cada corrida reemplaza el día anterior (ver "Fuera de alcance").
- Detección de cambios: comparar contra el día anterior (precios que saltan más de x3, sucursales que desaparecen,
  comercios con archivo viejo: ya se excluyen).
- Faltantes: un producto sin precio hoy no se arrastra de ayer; una sucursal sin datos del día no se ofrece.
- Equivalencias entre cadenas: ya existe por EAN y "gemelos"; documentar y testear el emparejamiento.
- Entorno reproducible con `uv` (hoy hay dos `requirements.txt`).
- **Tests en cada push:** la suite de Python y la paridad en CI; tests de la página con Playwright (hoy: Chrome
  headless con capturas y paridad); tests del motor JavaScript sin navegador (Node).

### Etapa 4 · Restricciones nuevas y condiciones médicas

Requiere recargar la base: la composición y las aptitudes salen del pipeline (`python -m sepa`), no de la página.

- **Kosher, halal y sin cerdo**, y también pescetariano y exclusión de ingredientes puntuales. Sin cerdo sale de los
  mismos datos de composición; kosher y halal necesitan una certificación del producto (etiquetas de Open Food Facts
  o listas de las entidades certificadoras), con la cobertura medida antes de ofrecerlas. Cada una entra al final de
  `RESTRICCIONES` (el orden define los bits de aptitud de la página).
- **Vitaminas y condiciones médicas** (anemia, deficiencias de vitaminas, embarazo de riesgo, etc.). El motor ya
  ajusta metas (hierro y zinc vegetarianos, sodio con hipertensión, azúcares con diabetes). Para ampliar:
  - Una tabla versionada de **ajustes por condición** (`referencia/condiciones.csv`): condición → meta modificada →
    fuente bibliográfica (NASEM, OMS, guías argentinas) → "requiere supervisión profesional" sí/no.
  - Solo se ofrecen condiciones con fuente; las que requieren supervisión muestran el aviso y no cambian metas por
    encima de los máximos tolerables.
  - Nunca diagnóstico ni suplementación: la canasta sigue siendo comida del supermercado.

### Etapa 5 · Promociones con condiciones

SEPA publica `precio_promocion` sin condiciones, y hoy las promociones se muestran como "no aplicadas" y quedan
fuera del total. Hace falta otra fuente (catálogos web de las cadenas, que el pipeline ya recorre) y un modelo de
datos:

| Campo | Ejemplo |
|---|---|
| tipo | `porcentaje`, `nxm` (2×1, 3×2), `segunda_unidad` (2.ª al 70 %), `precio_fijo`, `llevando_x` |
| producto(s) | EAN o lista |
| vigencia | desde / hasta, días de la semana |
| condiciones | tope de unidades o de descuento, compra mínima |
| precio habitual / precio efectivo | se guardan los dos |

En el optimizador, cada promoción es lineal o entera: `nxm` con una variable entera de "packs" (`x_p = n·k + r`),
`segunda_unidad` igual con pares, topes como cota superior, compra mínima con una binaria. **Una promoción solo se
aplica si se cumplen todas sus condiciones**, y el ticket muestra precio de lista, descuento y precio efectivo por
renglón. Las que dependen de un banco, una billetera o la tarjeta de la cadena quedan afuera (ver "Fuera de
alcance") y se siguen mostrando como no aplicadas.

### Etapa 6 · LLM con Groq (API gratuita)

**Rol:** que la persona cuente algo más en texto libre ("algo barato para mí y mi hija, ella es celíaca y yo tengo
anemia", o una prescripción médica) y traducirlo al **pedido estructurado** que ya consume el motor (`personas`,
`restricciones`, `dias`, `caminata_minutos`, `agua`, condiciones), para que la persona lo confirme. No elige
productos, no inventa precios ni nutrientes, no reemplaza al optimizador.

**Diseño:**
1. **Backend mínimo (FastAPI):** la clave de Groq (`GROQ_API_KEY`) no puede ir en la página. El mismo backend puede
   guardar la clave de rutas (deja de estar en la copia local), cachear las matrices por celda de ~100 m (las
   sucursales no se mueven) y servir el motor Python como API para clientes que no pueden correr WebAssembly. La
   página puede seguir siendo estática y llamar al backend solo para esto.
2. El backend recibe el texto y llama a Groq con salida estructurada (JSON Schema del pedido; modo estricto en los
   modelos que lo soportan, según la documentación de Groq).
3. Se valida el JSON contra el mismo esquema y contra `canasta/config.py` (restricciones y condiciones conocidas); lo
   que no se reconoce se pregunta al usuario, no se adivina.
4. Se muestra el formulario ya completado para que la persona confirme antes de calcular.
5. Opcional: explicar el resultado en lenguaje simple a partir del JSON del motor (con los números del motor, sin
   recalcular nada).

**Cuándo:** después de la etapa 4, para que las condiciones médicas tengan su tabla con fuentes. Antes aporta poco:
el formulario actual cubre lo que el motor sabe hacer.

## Otros pendientes (sin etapa asignada)

- **Frente costo vs. minutos** y objetivos secundarios con tolerancia de costo (ver "Lógica de negocio").
- **Rutas para público:** autoalojar OpenRouteService u OSRM con el extracto de Argentina de Geofabrik (un VPS de
  4 a 8 GB alcanza para el perfil peatonal), o pasar a Mapbox/Google detrás del backend. Teselas de un proveedor con
  cuota (las de OpenStreetMap no son para tráfico alto).
- **Experiencia:** autocompletado de direcciones (Photon sobre OSM; Georef no autocompleta), lista de compras para
  compartir, plan de comidas día por día (idea tomada de Mealbird).
- **Velocidad:** 10 a 18 s por cálculo; ideas en [PLAN_DE_TRABAJO.md](../base_sepa/PLAN_DE_TRABAJO.md).

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
usuarios o tener cuentas de usuario. El motor puede seguir en el navegador (no cuesta servidor) y el backend
ocuparse solo de lo que necesita secreto o estado.

## Fuera de alcance

- **Historial de precios.** Cada corrida del ETL reemplaza el día anterior: son ~8 millones de precios por día y
  nada del producto los usa. Si más adelante hiciera falta mostrar tendencias, alcanzaría con un resumen por
  producto, cadena y día (mediana), no las filas completas.
- **Promociones bancarias** (reintegros y descuentos por banco, billetera o tarjeta de la cadena): dependen de los
  medios de pago de cada persona, cambian por día y por cadena, y SEPA no las publica con sus condiciones. Se
  siguen mostrando como "no aplicadas".
