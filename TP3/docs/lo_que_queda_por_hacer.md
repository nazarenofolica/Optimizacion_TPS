# TP3 CarroMenos — Lo que queda por hacer

> Para quien sigue el trabajo. Hechas F0 a F3 (17 de 31 tareas): datos externos, código base,
> modelo, pregunta a) y sensibilidad. Faltan las preguntas b) a e), los tests de supuestos, el
> informe y el cierre. El detalle de cada tarea está en [`tareas.md`](tareas.md); acá va lo que
> conviene saber para no repetir trabajo ni pisar decisiones ya tomadas.

---

## 1. Antes de empezar (10 minutos)

```bash
pip install -r requirements.txt
python scripts/00_verificar_datos.py   # 27 chequeos: tienen que pasar todos
python scripts/02_punto_a.py           # pregunta a)  -> óptimo A+C+D, $ 56.055.516
python scripts/03_sensibilidad.py      # informe b)   -> 9 controles cruzados OK
```

Si algo de esto falla, no sigas: algo cambió en el entorno o en los datos.

Leer, en este orden:
1. [`plan_de_trabajo.md`](plan_de_trabajo.md) §0, §5 y §12: qué pide la consigna, los supuestos y
   la guía por pregunta.
2. [`procedimiento.md`](procedimiento.md) §1.1 (valores de Q, W, K_max, φ con fuente), §2
   (desvíos D1 a D10) y §3 (resultados de a) y de la sensibilidad).

**Reglas del trabajo (las mismas del TP1 y TP2):**
- El plan **no se reescribe**. Si algo se hace distinto, se anota como desvío en
  `procedimiento.md` §2 (número, qué decía el plan, qué se hizo, por qué).
- Se avanza fase por fase. Al terminar una tarea: tildarla en `tareas.md` (☐ → ☑) y anotar
  resultados en `procedimiento.md` §3.
- Todo número que vaya al informe tiene que salir de un CSV de `resultados/tablas/`.

---

## 2. Lo que ya está hecho

| Fase | Tareas | Resultado principal |
|---|---|---|
| F0 Datos externos | T01–T06 ☑ | Q = 26 pallets, W = $1.600.000, K_max = 7.700 km, φ = 2,68 kg CO₂/l, carbono USD 10/t |
| F1 Base de código | T07–T10 ☑ | `config.py`, `datos.py`, distancias OSRM (factor de ruta 1,268), 27 chequeos |
| F2 Modelo y a) | T11–T15 ☑ | **Abrir A, C y D** (gerente, 6 conductores), $56,06 M/mes, 95,1 t CO₂/mes |
| F3 Sensibilidad | T16–T17 ☑ | D y los conductores son los cuellos de botella; la decisión es robusta (solo cambia con tarifa > $891/km) |

**Hallazgos que condicionan lo que sigue:**
- **La restricción de conductores está siempre activa**: los km del tramo 2 son exactamente
  K_max × n. El modelo reacomoda flujos para no pagar un conductor más. Por eso W y K_max pueden
  cambiar resultados (test E).
- **W ($1,6 M) > $500.000**: en e) contratar un conductor más para "cubrir" 500 km sale más caro
  que pagar la penalidad. Por eso se decidió (desvío D2) **mantener** la restricción de capacidad
  real de los conductores y **agregar** el tope de 500 km, no reemplazarla.
- Errores del plan ya corregidos: los costos fijos de 3 centros (D5: B+C+D = $6,6 M, A+C+D =
  $7,1 M) y la cantidad de configuraciones del test B (D6: son 7, no 8).

---

## 3. Cómo se usa el código (no hace falta tocar el modelo)

Todo pasa por **un solo modelo**, `src/modelo.py → resolver(params, ...)`:

```python
from src.config import construir_params
from src import modelo

p = construir_params()                       # caso base; supuestos: construir_params(Q=20, W=...)
r = modelo.resolver(p)                       # pregunta a)
r = modelo.resolver(p, escenario="d")        # flota propia también planta -> centro
r = modelo.resolver(p, escenario="e")        # tope 500 km + penalidad $1.000/km
r = modelo.resolver(p, escenario="de")       # d + e
r = modelo.resolver(p, goyito={"Arroz": 900})  # Goyito puede llevar Arroz directo a $900/pallet
r = modelo.resolver(p, config_fija=["A", "C"]) # configuración fija -> PL de flujos
```

`r` es un dict: `estado`, `costo`, `desglose` (por rubro), `configuracion`, `conductores`,
`exceso_km`, `goyito` ({producto: True/False}), `km_tramo1`, `km_tramo2`, `km_goyito`,
`km_total`, `litros`, `co2_kg`, `flujos_tramo1`, `flujos_tramo2`, `ocupacion`.

- `src/reportes.py`: `fila_resumen(r)` (una fila para comparar escenarios), `tabla_desglose`,
  `tabla_indicadores`, `guardar({nombre: df}, carpeta)`.
- `src/graficos.py`: `mapa_asignacion(r, ubic, titulo, archivo)` y `tabla_tramo1(r, titulo,
  archivo)` sirven tal cual para d) y e). `frontera_costo_co2` y `barridos` como referencia de estilo.
- `src/datos.py`: `cargar_distancias("osrm" | "haversine")`, `factor_ruta()`,
  `coeficientes_por_arco(p)` (incluye los arcos planta → súper que usa Goyito).
- Cada pregunta va en su script: `scripts/04_punto_b.py` … `07_punto_e.py`, con la misma forma que
  `02_punto_a.py` (resolver → asserts → `reportes.guardar` → gráficos → resumen en consola).

---

## 4. Lo que falta

### F4 — Preguntas b) a e)

#### ☐ T18 — Pregunta b): un único centro de capacidad infinita (punto de Weber)
- Script nuevo `scripts/04_punto_b.py` y módulo `src/weber.py`. Es el único que **no** usa
  `modelo.resolver`: el centro puede estar en cualquier punto del mapa (plan §12 b).
- Función a minimizar en (lat, lon): tramo 1 `(T/Q) · dem_k · min_p d(p, X)` (la planta más cercana
  de cada producto) + tramo 2 `(CK/Q) · dem_i · 2·d(X, i)`.
- Distancias: haversine × **1,268** (`datos.haversine_km` y `datos.factor_ruta()`), porque OSRM no se
  puede consultar para cada punto de una grilla. Al final, verificar el punto elegido con OSRM.
- El `min` sobre plantas hace la función no convexa: grilla sobre la zona + `scipy.optimize.minimize`
  desde los mejores puntos de la grilla. Weiszfeld como control.
- Dos versiones: económica ($) y ambiental (km físicos). Comparar con A, B, C, D y con el centro de
  gravedad.
- Entregables: `13_punto_b.csv`, gráfico del punto óptimo sobre el mapa.

#### ☐ T19 — Pregunta c): precio mínimo de Goyito por producto
- `scripts/05_punto_c.py`. El modelo ya acepta `goyito={producto: precio}` (binaria `u_k`; si
  Goyito lleva el producto, sale de la demanda y se paga `precio × demanda del producto`).
- Umbral global: `Z* / 51.850` = 56.055.516 / 51.850 ≈ **$1.081 por pallet**.
- Por producto: barrer el precio de cada producto (bisección) hasta que `u_k` pase de 0 a 1.
- Control: `(Z*(con k) − Z*(sin k)) / dem_k`. Para "sin k": correr con un precio de Goyito 0 para
  ese producto y restarle lo que paga a Goyito. Ojo: sacar Fideos (20.300 pallets) deja la
  demanda en 31.550 y **alcanza A solo** (S2 lo permite), así que el modelo puede cerrar C y D:
  el umbral de Fideos incluye ese ahorro de fijos. Es justamente lo que el barrido captura y la
  cuenta promedio no.
- Ambiental: `km_goyito`, litros y CO₂ del viaje directo contra vía centro.
- Entregables: `14_umbral_goyito.csv`, gráfico.

#### ☐ T20 — Pregunta d): flota propia también planta → centro
- `scripts/06_punto_d.py`: `modelo.resolver(p, escenario="d")`.
- Ya se corrió de prueba: **A+C+D, $80,9 M, 18 conductores, 92,0 t CO₂** (contra $56,1 M y 6
  conductores en a). Confirmar con el script y explicar: el tramo 1 pasa de $500 por km de ida a
  $325 × 2 (ida y vuelta) + conductores.
- Comparar con a): costo y desglose, configuración, conductores, km, litros, CO₂.
- Entregables: `15_comparacion_a_d.csv`, mapa con `graficos.mapa_asignacion`.

#### ☐ T21 — Pregunta e): tope de 500 km por conductor
- `scripts/07_punto_e.py`: `escenario="e"` y `escenario="de"`.
- Pruebas ya corridas: e) **$98,8 M, 42.608 km de exceso** (≈ $42,6 M de penalidad); d+e) **$209,2 M**.
- Explicar el trade-off: un conductor más cuesta W = $1,6 M y "cubre" 500 km = $500.000 de
  penalidad, así que nunca conviene contratar por el tope: se paga la penalidad.
- Señalar la inconsistencia de la consigna ("al día" vs. "mensuales", supuesto S14). Opcional:
  correrlo con 500 km por día (≈ 11.000 km por mes) para mostrar la diferencia.
- Entregables: `16_comparacion_e.csv`, mapa.

### F5 — Tests de supuestos

#### ☐ T22 — `scripts/08_tests_supuestos.py`
- Tests A a G del plan §13: un supuesto por vez con `construir_params(...)`, re-resolver el entero y
  comparar con la base. Todos los supuestos ya están parametrizados en `config.py`
  (`distancias="haversine"`, `principal="al_menos_uno"`, `Q`, `tarifa_ida_vuelta=True`, `W`,
  `K_max`, `precio_co2`, `factor_apertura`).
- **El test E (W ± 30 %, K_max 6.000 a 12.000) es el más importante**: la restricción de
  conductores está activa y puede cambiar la configuración.
- Test B: con A y B juntos son 7 configuraciones (`datos.configuraciones_factibles`).
- Test F: el precio del carbono está en USD 10/t; pasarlo a $ por kg con un tipo de cambio citado.
- Asserts del plan §13 (relajar S2 nunca sube el costo, más Q nunca sube el transporte, etc.).
- Entregable: `17_tests_supuestos.csv` con la columna "¿cambia la conclusión?".

### F6 — Informe (`informe/informe.tex`)

- ☐ T23 Esqueleto: copiar preámbulo, carátula y bibliografía de `TP2/informe/informe.tex`. Compila
  con la receta de `.vscode/settings.json`.
- ☐ T24 a) Modelo: supuestos (tabla del plan §5.5 + los desvíos que cambian el modelo: D1, D2, D4),
  variables, función objetivo, parámetros, restricciones, resolución (tabla de las 3
  configuraciones, `02_configuraciones.csv`).
- ☐ T25 b) Sensibilidad: todo está en `procedimiento.md` §3.2 y en las tablas 09 a 12b. Explicar por
  qué se fija la configuración (binarias → no hay precios sombra) y la degeneración.
- ☐ T26 c) Gráficos: `02_mapa_flujos_a.png` (qué centro atiende a cada súper) +
  `03_tabla_tramo1_a.png` (de qué planta se abastece cada centro), y los de d) y e).
- ☐ T27 d) Librerías: PuLP 3.3.2 (CBC), highspy 1.15.1, pandas 2.3.3, numpy 1.26.4, matplotlib, scipy
  1.12.0, requests 2.34.2 + OSRM. Para qué se usó cada una.
- ☐ T28 Preguntas a) a e): respuesta primero, justificación después, indicadores ambientales en
  todas.
- ☐ T29 Bibliografía: fuentes de `procedimiento.md` §1.1 (DSV, CCT 40/89, IPCC 2006, Ley 27.430),
  OSRM / OpenStreetMap, clases de la cátedra (03, 05, 06, 09), links útiles de la consigna.
- ☐ T30 Revisión final: releer contra las DOS listas de la consigna (plan §0), números del informe
  = CSVs, compilar el PDF.

### F7 — Cierre
- ☐ T31 Completar `procedimiento.md` (§4 tests, §5 verificaciones, §6 conclusiones), actualizar el
  README y hacer commit.

---

## 5. Pendientes para analizar

Dos dudas sobre los datos que quedaron abiertas. Ninguna frena las tareas de F4, pero hay que
cerrarlas antes del informe (T24 y T29). Lo que se decida se anota como desvío en
`procedimiento.md` §2.

### ☐ P1 — ¿La apertura es un costo mensual o una inversión única?

- **Qué dice la consigna:** "costo estimado de apertura" del centro, sin unidad de tiempo. El
  gerente sí es "mensual".
- **Qué hace hoy el modelo:** suma la apertura como costo **por mes**, junto con el resto
  (plan §7.1). Es el supuesto más cómodo, pero no está confirmado.
- **Por qué importa:** si fuera una inversión única, habría que mensualizarla (amortización:
  inversión / meses de vida útil, o con tasa). Los costos fijos bajarían mucho frente al
  transporte (~$40 M/mes).
- **Lo que ya sabemos:** el barrido de `factor_apertura` entre ×0,5 y ×2
  (`resultados/tablas/12_barridos.csv`) **no cambia la configuración**: A+C+D sigue óptima.
  Con un costo mensual de apertura menor (que es lo que pasaría si fuera una inversión
  amortizada), D y el gerente pesan aún menos. Así que lo esperable es que **la respuesta de a)
  no cambie**; sí cambian el costo total y el desglose.
- **Qué hacer:**
  1. Consultarlo con la cátedra.
  2. Mientras tanto, extender el barrido hacia abajo (×0,05 a ×0,5, el rango de una amortización a
     varios años) con `construir_params(factor_apertura=...)`. Verificar que A+C+D se mantiene y
     anotar desde qué valor cambiaría, si cambia.
  3. En el informe: declararlo como supuesto (S16) con el barrido como respaldo.

### ☐ P2 — Confirmar los datos del convenio de camioneros en el acta oficial

- **Qué se usó:** dos datos salen del CCT 40/89 (detalle y fuentes en `procedimiento.md` §1.1).
  - **W = $1.600.000**: básico del conductor de primera de octubre 2026 ($1.126.149,40), más
    aguinaldo y cargas del empleador (≈ 31,4 %; el 5 % de ART es un supuesto propio).
  - **K_max = 7.700 km**: 22 días garantizados × 350 km por día (el mínimo de viático por día de
    viaje).
- **El problema:** las fuentes son sitios que resumen el convenio (Contala, Asistente Laboral,
  HRUseful), no el acta homologada. Además no coinciden del todo: Mundo Empresarial da
  $1.113.896,53 para octubre (≈ 1 % menos).
- **Por qué importa:** la restricción de conductores está activa en el óptimo. W y K_max deciden
  cuántos conductores se contratan, la frontera costo–CO₂ y el resultado de e) (W contra los
  $500.000 de penalidad).
- **Qué hacer:**
  1. Buscar el acta o la resolución de homologación en `convenios.trabajo.gob.ar` o en la web de la
     Federación de Camioneros. Confirmar el básico, la jornada y los 22 días garantizados.
  2. Confirmar las alícuotas del empleador (contribuciones 20,4 %, obra social 6 %, ART del
     transporte de cargas).
  3. Si los valores cambian, actualizar `W` o `K_max` en `src/config.py`, volver a correr los
     scripts 00, 02 y 03, y anotar el cambio.
  4. Haga falta o no, el **test E** (T22: W ± 30 %, K_max de 6.000 a 12.000) muestra si la
     conclusión depende de estos números. Es el respaldo para el informe.

---

## 6. Cosas que ya nos hicieron perder tiempo (evitarlas)

- **No uses la restricción fuerte en el análisis de sensibilidad.** `resolver(..., fuerte=False)`
  cuando la configuración está fija y se perturba la demanda (desvío D9). En el modelo entero sí va.
- **CBC tiene un error de centavos sobre $56 M.** Para medir un precio por re-resolución, perturbar
  ±5 o más, no ±1.
- **Los `$` en matplotlib** se leen como fórmulas: `graficos.py` ya lo desactiva
  (`text.parse_math = False`); si hacés gráficos fuera de ese módulo, hacé lo mismo.
- **Gráficos**: un solo mensaje por figura y poco texto. Si hay muchos flujos que se cruzan, mejor
  una tabla (así quedó el tramo 1). Colores de los centros fijos (`COLOR_CENTRO` en `graficos.py`):
  A azul, B violeta, C naranja, D verde.
- **La consola de Windows** no imprime "→" ni "≈" sin configurar: los scripts ya hacen
  `sys.stdout.reconfigure(encoding="utf-8")`; copiá esas líneas en los scripts nuevos.
- **OSRM** ya está bajado (`datos/distancias_osrm.csv`): no hace falta internet. Solo
  `01_distancias.py --forzar` lo vuelve a consultar.
