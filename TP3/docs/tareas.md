# TP3 CarroMenos — Tareas

> **Qué es este archivo.** El [`plan_de_trabajo.md`](plan_de_trabajo.md) dividido en tareas
> concretas, en el orden en que conviene hacerlas. Cada tarea dice **qué depende de qué**, **qué se
> entrega** y **cuándo está hecha**. Las referencias "§" son al plan.
>
> **Cómo se usa:** al terminar una tarea, tildarla en el índice y anotar en
> [`procedimiento.md`](procedimiento.md) lo que pasó, sobre todo si algo se apartó del plan.
>
> **Estado (23/10/2026): las 31 tareas están hechas.** Los resultados de cada una están en
> `procedimiento.md` §3 a §6 y el informe en `informe/informe.pdf`. Solo falta el commit.

---

## Índice

| # | Tarea | Fase | Depende de | Hecho |
|---|---|---|---|:---:|
| T01 | Capacidad del camión (Q) | F0 Datos externos | — | ☑ |
| T02 | Sueldo de un conductor (W) | F0 | — | ☑ |
| T03 | km máximos por conductor y mes (K_max) | F0 | — | ☑ |
| T04 | Factor de emisión del gasoil (φ) | F0 | — | ☑ |
| T05 | Revisar el portafolio de redes (mim.com.ar) | F0 | — | ☑ |
| T06 | Precio del carbono *(opcional)* | F0 | — | ☑ |
| T07 | `config.py`: datos y supuestos | F1 Base de código | T01–T04 | ☑ |
| T08 | `01_distancias.py`: matriz OSRM + haversine | F1 | — | ☑ |
| T09 | `datos.py`: lectura y coeficientes por arco | F1 | T07, T08 | ☑ |
| T10 | `00_verificar_datos.py` | F1 | T09 | ☑ |
| T11 | `modelo.resolver` | F2 Modelo y a) | T10 | ☑ |
| T12 | Enumeración de configuraciones | F2 | T11 | ☑ |
| T13 | `02_punto_a.py`: óptimo e indicadores | F2 | T12 | ☑ |
| T14 | Frontera costo–CO₂ | F2 | T13 | ☑ |
| T15 | `graficos.py`: mapa de flujos | F2 | T13 | ☑ |
| T16 | Rangos de sensibilidad con highspy | F3 Sensibilidad | T13 | ☑ |
| T17 | Barridos que cambian la configuración | F3 | T13 | ☑ |
| T18 | Pregunta b): punto de Weber | F4 Preguntas | T09 | ☑ |
| T19 | Pregunta c): umbral de Goyito por producto | F4 | T13 | ☑ |
| T20 | Pregunta d): flota propia en el tramo 1 | F4 | T13 | ☑ |
| T21 | Pregunta e): tope de 500 km | F4 | T13, T20 | ☑ |
| T22 | Tests de supuestos | F5 Tests | T13 | ☑ |
| T23 | Esqueleto de `informe.tex` | F6 Informe | — | ☑ |
| T24 | Informe a): modelo (a.i a a.vi) | F6 | T13, T23 | ☑ |
| T25 | Informe b): sensibilidad | F6 | T16, T17 | ☑ |
| T26 | Informe c): gráficos de flujo | F6 | T15 | ☑ |
| T27 | Informe d): librerías | F6 | T23 | ☑ |
| T28 | Informe: preguntas a) a e) | F6 | T14, T18–T22 | ☑ |
| T29 | Bibliografía | F6 | T01–T06 | ☑ |
| T30 | Revisión final y compilación | F6 | T24–T29 | ☑ |
| T31 | Cierre: procedimiento, README, commit | F7 | T30 | ☑ (el commit lo hace el equipo al revisar) |

**Camino crítico:** T01–T04 → T07 → T09 → T10 → T11 → T13 → (T16, T19, T20, T21, T22) → T28 → T30.
T08, T18, T23 y T05 se pueden hacer en paralelo con cualquier cosa.

---

## F0 — Datos externos (criterio "Explorar")

Todos llevan **fuente citable** (título, organismo o empresa, link, fecha de consulta). Se anotan en
`procedimiento.md` §1 y van a la bibliografía (T29).

### T01 — Capacidad del camión (Q)
- **Objetivo:** confirmar los pallets por viaje de un camión de distribución (plan S8).
- **Pasos:** buscar capacidad de un semirremolque estándar con pallet ARLOG/universal (1,00 × 1,20 m);
  ver si conviene distinguir camión de distribución urbana (menos pallets) para el tramo CD → súper.
- **Entregable:** valor de Q (default 26) con fuente; si hay dos camiones distintos, un Q por tramo.
- **Hecho cuando:** el valor y la fuente están en `procedimiento.md`.

### T02 — Sueldo de un conductor (W)
- **Objetivo:** costo mensual de un chofer de camión, con cargas sociales (plan S11).
- **Pasos:** escala del convenio de camioneros vigente (CCT 40/89, categoría chofer de primera);
  sumar cargas patronales (aprox. 25–30 %, citar).
- **Entregable:** W en $ por mes, con fuente y la cuenta de cargas.
- **Hecho cuando:** W está anotado. **Comparar con $500.000**: define el resultado de e) (plan §12 e).

### T03 — km máximos por conductor y mes (K_max)
- **Objetivo:** cuántos km por mes puede hacer un conductor en condiciones normales (plan S11).
- **Pasos:** jornada legal, días hábiles, velocidad media urbana / periurbana; o un dato del sector.
- **Entregable:** K_max (default 9.000) con la cuenta o la fuente.

### T04 — Factor de emisión del gasoil (φ)
- **Objetivo:** kg de CO₂ por litro de gasoil (plan S12).
- **Pasos:** IPCC 2006 o inventario nacional de GEI / Secretaría de Energía.
- **Entregable:** φ (default 2,68) con fuente.

### T05 — Revisar el portafolio de redes
- **Objetivo:** ver qué tiene `https://mim.com.ar/redes/` (link de [`Ubicaciones link.txt`](../Ubicaciones%20link.txt)); la
  consigna dice "usar para el TP".
- **Pasos:** abrirlo en el navegador; si tiene modelos o simuladores de redes / localización,
  anotar cuáles sirven y para qué pregunta.
- **Entregable:** nota en `procedimiento.md` §0. Si cambia algo del plan, registrarlo como desvío.

### T06 — Precio del carbono *(opcional)*
- **Objetivo:** valor en $ por tonelada de CO₂ para el test F (plan S13) y para monetizar el CO₂ en c).
- **Pasos:** impuesto al dióxido de carbono argentino (Ley 27.430) o precio de referencia
  internacional; convertir a $.
- **Entregable:** precio con fuente.

---

## F1 — Base de código

### T07 — `src/config.py`: datos y supuestos
- **Depende de:** T01–T04 (se puede arrancar con los defaults y actualizar después).
- **Pasos:**
  1. Datos de la consigna: demanda (§2.3), centros (§2.1), tarifa, combustible, gerente.
  2. Supuestos S1–S15 como diccionario con defaults y valores permitidos.
  3. `construir_params(**supuestos)`: falla con `KeyError` si el supuesto no existe y `ValueError`
     si el valor no es válido (patrón de `TP2/src/config.py`).
- **Entregable:** `src/config.py`.
- **Hecho cuando:** `construir_params()` devuelve el caso base y `construir_params(Qq=20)` falla.

### T08 — `scripts/01_distancias.py`: matriz de distancias
- **Pasos:**
  1. Leer [`datos/ubicaciones.csv`](../datos/ubicaciones.csv).
  2. Pedir a OSRM `table` (`router.project-osrm.org/table/v1/driving/...?annotations=distance`) la
     matriz 21 × 21 en km; guardar `datos/distancias_osrm.csv` con la fecha de consulta.
  3. Calcular la matriz haversine y el **factor de ruta** = mediana de (OSRM / haversine) en los
     arcos que usa el modelo (planta → centro, centro → súper, planta → súper).
  4. Agregar `requests` a `requirements.txt`.
- **Entregable:** `datos/distancias_osrm.csv`, factor de ruta anotado en `procedimiento.md`.
- **Hecho cuando:** la matriz tiene 21 × 21 valores, diagonal 0, todos los OSRM ≥ haversine.

### T09 — `src/datos.py`: lectura y coeficientes por arco
- **Depende de:** T07, T08.
- **Pasos:** cargar ubicaciones y distancias (OSRM o haversine × factor, según S1); armar los
  coeficientes por pallet de §6.2 (costo tramo 1, combustible tramo 2, km físicos); tablas
  derivadas (demanda por súper y por producto, plantas por producto).
- **Entregable:** funciones que devuelven DataFrames; tabla `01_costo_por_pallet_arco.csv`.

### T10 — `scripts/00_verificar_datos.py`
- **Depende de:** T09.
- **Chequeos (asserts):**
  - Demanda total 51.850; por producto 20.300 / 8.550 / 9.950 / 4.550 / 8.500; por súper la fila
    Total de §2.3.
  - 21 puntos: 10 supermercados, 4 centros, 7 plantas; Fideos y Leche con 2 plantas, el resto con 1.
  - Capacidades, aperturas y costos por pallet = §2.1. Combustible = $325/km.
  - Tabla §4.2: exactamente 3 configuraciones factibles con S2.
  - Distancias: simétricas aproximadamente, sin ceros fuera de la diagonal, OSRM ≥ haversine.
  - Un coeficiente por pallet calculado a mano coincide con el del código.
- **Hecho cuando:** todos los chequeos dan OK. **Se corre siempre antes que lo demás.**

---

## F2 — Modelo y pregunta a)

### T11 — `src/modelo.py`: `resolver(params, ...)`
- **Depende de:** T10.
- **Pasos:** variables §6.3, funcional §7, restricciones R1–R8 de §8 con nombre; parámetros
  `escenario`, `config_fija`, `epsilon_co2`, `goyito` (§14). Devolver un `dict` con estado, costo,
  desglose por rubro, centros abiertos, flujos (DataFrames), km, litros, CO₂, `n`, `exc`.
- **Entregable:** `src/modelo.py`.
- **Hecho cuando:** el caso base resuelve con estado `Optimal`, la demanda se cumple exactamente y
  ningún centro supera su capacidad.

### T12 — Enumeración de configuraciones (control §9)
- **Pasos:** para cada configuración factible, `resolver(params, config_fija=...)`; tabla con
  costo, desglose, km, litros, CO₂.
- **Entregable:** `resultados/tablas/02_configuraciones.csv`.
- **Hecho cuando:** el mínimo de la tabla coincide con el óptimo del entero (assert).

### T13 — `scripts/02_punto_a.py`
- **Pasos:** resolver la base; exportar flujos por tramo y producto, ocupación de centros,
  desglose de costos, indicadores; imprimir resumen. Verificar las predicciones de §6.2 (la
  operación del centro pesa poco frente al transporte).
- **Entregables:** tablas `03_flujos_tramo1.csv`, `04_flujos_tramo2.csv`, `05_ocupacion_centros.csv`,
  `06_desglose_costos.csv`, `07_indicadores_ambientales.csv`.
- **Hecho cuando:** resultados anotados en `procedimiento.md` §3 con su interpretación.

### T14 — Frontera costo–CO₂
- **Pasos:** minimizar CO₂ (extremo); barrer `epsilon_co2` entre los dos extremos (~10 puntos);
  graficar costo vs. CO₂ marcando qué configuración aparece en cada tramo.
- **Entregables:** `08_frontera_costo_co2.csv`, `01_frontera_costo_co2.png`.

### T15 — `src/graficos.py`: mapa de flujos
- **Pasos:** función `mapa_flujos(resultado, titulo, archivo)` según §11; probar con el resultado
  de T13.
- **Entregable:** `02_mapa_flujos_a.png` (y después, `_d`, `_e`).
- **Hecho cuando:** se leen bien los centros abiertos, las plantas usadas y los flujos grandes.

---

## F3 — Sensibilidad (informe b)

### T16 — Rangos con highspy
- **Depende de:** T13.
- **Pasos:**
  1. Instalar `highspy`, agregarlo a `requirements.txt`.
  2. `src/sensibilidad.py`: armar el PL de flujos con `y*` fija (desde los coeficientes de
     `datos.py`), resolver en highspy y leer `getRanging()`, duales y costos reducidos.
  3. Control cruzado: comparar 2 o 3 rangos con re-resolución perturbando el coeficiente (y que el
     costo del PL de highspy coincida con el de PuLP).
- **Entregables:** `09_rangos_lado_derecho.csv` (b.i), `10_rangos_costos.csv` (b.ii),
  `11_costos_reducidos.csv`.

### T17 — Barridos que cambian la configuración
- **Pasos:** barridos de §10.4 (tarifa T, Q, F_j, demanda total) re-resolviendo el entero; marcar
  el valor en que cambia la configuración.
- **Entregables:** `12_barridos.csv` y gráfico `03_barridos.png`.

---

## F4 — Preguntas b) a e)

### T18 — Pregunta b): punto de Weber
- **Depende de:** T09 (solo distancias y demanda).
- **Pasos (§12 b):** `src/weber.py` con la función de costo; grilla + `scipy.optimize.minimize`;
  Weiszfeld como control; ponderación económica y ambiental; comparar con A–D y centro de gravedad;
  verificar el punto final con OSRM.
- **Entregables:** `13_punto_b.csv` (punto óptimo, A–D, centroide: costo, km, CO₂), `04_mapa_punto_b.png`.

### T19 — Pregunta c): umbral de Goyito por producto
- **Pasos (§12 c):** umbral global `Z*/51.850`; binaria `u_k` en el modelo; barrido de `g_k` por
  producto; control `(Z*(con k) − Z*(sin k)) / dem_k`; km/CO₂ del viaje directo vs. vía CD.
- **Entregables:** `14_umbral_goyito.csv`, `05_umbral_goyito.png`.
- **Hecho cuando:** barrido y control coinciden en los 5 productos (o la diferencia está explicada).

### T20 — Pregunta d): flota propia en el tramo 1
- **Pasos (§12 d):** `resolver(params, escenario="d")`; comparar con a) en costo, configuración,
  conductores, km, litros, CO₂; verificar la predicción de §12 d.
- **Entregables:** `15_comparacion_a_d.csv`, `06_mapa_flujos_d.png`.

### T21 — Pregunta e): tope de 500 km
- **Depende de:** T13, T20.
- **Pasos (§12 e):** `escenario="e"` sobre la base y sobre d); reportar `n`, `exc`, costo y CO₂;
  explicar el trade-off W vs. $500.000; opcional barrido del tope y de la penalidad.
- **Entregables:** `16_comparacion_e.csv`, `07_mapa_flujos_e.png`.

---

## F5 — Tests de supuestos

### T22 — `scripts/08_tests_supuestos.py`
- **Pasos:** tests A a G de §13; asserts de las propiedades de §13; tabla resumen.
- **Entregables:** `17_tests_supuestos.csv`; resumen en `procedimiento.md` §4.
- **Hecho cuando:** todos los asserts dan OK y la tabla tiene la columna "¿cambia la conclusión?"
  completa.

---

## F6 — Informe

### T23 — Esqueleto de `informe/informe.tex`
- **Pasos:** copiar preámbulo, carátula y bibliografía manual de `TP2/informe/informe.tex`; armar
  las secciones según la lista "Informe esperable" + una sección por pregunta. Compila con la
  receta de `.vscode/settings.json` (pdflatex ×2).
- **Hecho cuando:** compila sin errores con secciones vacías.

### T24 — Informe a): el modelo
- Supuestos (tabla §5.5 + justificación de los importantes), variables, funcional, parámetros
  (incluye la tabla de coeficientes por pallet), restricciones con la frase del enunciado,
  resolución (óptimo + tabla de configuraciones).

### T25 — Informe b): sensibilidad
- b.i rangos de lados derechos y precios sombra; b.ii rangos de costos y costos reducidos;
  barridos que cambian la configuración; advertencia de validez fuera de rango.

### T26 — Informe c): representación gráfica
- Mapas de a), d), e) y el de b), con lectura de cada uno.

### T27 — Informe d): librerías
- PuLP/CBC, highspy, pandas, matplotlib, scipy, requests/OSRM: para qué se usó cada una y versión.

### T28 — Informe: preguntas a) a e)
- Una sección por pregunta con la respuesta concreta primero y la justificación después, incluyendo
  los indicadores ambientales en todas.

### T29 — Bibliografía
- Fuentes de T01–T06, OSRM / OpenStreetMap, links útiles de la consigna usados, clases de la
  cátedra (09, 05, 06, 03), Hillier & Lieberman.

### T30 — Revisión final
- Releer contra la consigna (las dos listas), números del informe = CSVs, compilar el PDF final.

---

## F7 — Cierre

### T31 — Procedimiento, README y commit
- Completar `procedimiento.md` (desvíos, verificaciones, conclusiones), actualizar el estado del
  README y del plan (solo notas de "Actualización", sin reescribirlo) y hacer commit.

---

## Trazabilidad: consigna → tareas

| Consigna | Tareas |
|---|---|
| Informe a) Modelo de PL (i–vi) | T07, T11, T12, T13, T24 |
| Informe b) Sensibilidad (i–ii) | T16, T17, T25 |
| Informe c) Gráfico de flujos | T15, T26 |
| Informe d) Librerías | T27 |
| Bibliografía | T01–T06, T29 |
| Pregunta a) Localización + ambiental | T12, T13, T14 |
| Pregunta b) Centro único | T18 |
| Pregunta c) Umbral de Goyito | T19 |
| Pregunta d) Flota propia | T20 |
| Pregunta e) Tope de km | T21 |
| Criterio "Explorar" | T01–T06, T08, T14, T22 |
| Criterio "Analizar" | T12, T17, T22, `procedimiento.md` §2 |
