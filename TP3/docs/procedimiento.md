# TP3 CarroMenos — Procedimiento (bitácora de desarrollo)

> **Qué es este archivo.** El registro de lo que **efectivamente se hizo** al codificar y
> resolver el modelo, incluyendo **en qué se apartó del plan y por qué**. El plan está en
> [`plan_de_trabajo.md`](plan_de_trabajo.md) y **no se reescribe** para que coincida con esto.
>
> **Estado:** trabajo completo. Las 31 tareas están hechas: preguntas a) a e), sensibilidad, tests
> de supuestos e informe (`informe/informe.pdf`, 21 páginas). Pendiente fuera del alcance del código:
> confirmar el CCT 40/89 en el acta oficial (P2, ver §4.3).

---

## 0. Preparación

- Estructura de carpetas creada replicando la del TP2 (`docs/`, `src/`, `scripts/`,
  `resultados/`, `informe/`, `.vscode/` para compilar el informe con LaTeX Workshop).
- **Coordenadas del mapa.** El mapa de Google My Maps del link de la consigna se descargó como KML
  con `https://www.google.com/maps/d/kml?mid=1KwVJvlsJ7qTp8yZByaEoPnjC-mIak7s&forcekml=1` y se
  guardó en [`../datos/ubicaciones.kml`](../datos/ubicaciones.kml). De ahí se armó
  [`../datos/ubicaciones.csv`](../datos/ubicaciones.csv) (21 puntos). Si la cátedra modifica el
  mapa, volver a bajarlo con el mismo link.
- Hallazgo al bajar el mapa: **hay dos plantas de Fideos y dos de Leche** (plan §2.4).
- La página del portafolio de redes (`mim.com.ar/redes`) carga su contenido por JavaScript: no se
  pudo leer automáticamente. Pendiente revisarla a mano (tarea T05).
- **Plan completo.** Las 14 decisiones abiertas de la preparación se cerraron como supuestos S1–S15
  con un valor por defecto y su test (plan §5). Se planteó el modelo (§6–§8), la enumeración de
  control (§9), la sensibilidad (§10), la guía por pregunta (§12) y los tests (§13). El trabajo
  quedó dividido en 31 tareas en [`tareas.md`](tareas.md). Desde acá el plan no se reescribe.

---

- **Portafolio de redes (T05).** Consultado el 20/10/2026: la página `https://mim.com.ar/redes/`
  es el "Hub de Recursos" de Web QSB y muestra *"Aún no hay herramientas en este Hub"*. No aporta
  nada al plan por ahora. Volver a mirar antes de entregar, por si la cátedra sube algo.
  **Revisado otra vez el 23/10/2026:** sigue sin herramientas.

---

## 1. Implementación

### 1.1. Datos externos (F0, criterio "Explorar")

Todas las fuentes consultadas el **20/10/2026**.

| Parámetro | Valor adoptado | Default del plan | Fuente |
|---|---:|---:|---|
| `Q` pallets por camión (T01) | **26** | 26 | DSV, *¿Cuántos palets caben en un camión?*: semirremolque estándar, *"palet americano (1,20 × 1,00 m) no remontable: máximo 26"* (33 si son europeos 1,20 × 0,80). https://www.dsv.com/es-es/ayuda/faq/cuantos-palets-caben-en-un-camion-dsv-estandar |
| `W` costo mensual de un conductor (T02) | **$1.600.000** | a definir | Ver cuenta abajo |
| `K_max` km por conductor y mes (T03) | **7.700** | 9.000 | Ver cuenta abajo (desvío, §2) |
| `φ` kg CO₂ por litro de gasoil (T04) | **2,68** | 2,68 | IPCC 2006, Vol. 2, Cap. 3, Cuadro 3.2.1 (pág. 3.16): gas/diésel oil **74.100 kg CO₂/TJ** (rango 72.600–74.800); VCN 43,0 TJ/Gg (Vol. 2, Cap. 1, Cuadro 1.2). https://www.ipcc-nggip.iges.or.jp/public/2006gl/spanish/pdf/2_Volume2/V2_3_Ch3_Mobile_Combustion.pdf |
| Precio del carbono (T06, opcional) | **USD 10 / t CO₂** | — | Ley 27.430 (2017), impuesto al dióxido de carbono, tasa de diseño USD 10/tCO₂e (efectiva ≈ USD 6 tras la devaluación de 2018). IEA, https://www.iea.org/policies/19277 ; World Bank Carbon Pricing Dashboard |

**Cuenta de W (T02).**
- Básico del **conductor de primera categoría**, CCT 40/89 (Federación de Camioneros), vigente desde
  el 01/10/2026: **$1.126.149,40** (Contala, https://www.contala.com.ar/escalas/camioneros; coincide
  con Asistente Laboral e Ignacio Online; Mundo Empresarial da $1.113.896,53 — diferencia ≈ 1 %).
- Aguinaldo proporcional: × 13/12 → $1.219.995.
- Cargas del empleador: contribuciones 20,4 % (Ley 27.541, empresa grande: CarroMenos es una cadena
  de supermercados) + obra social 6 % + ART ≈ 5 % (supuesto, transporte de cargas) ≈ **31,4 %**.
- W = 1.219.995 × 1,314 ≈ **$1.603.000 → $1.600.000**.
- No incluye antigüedad, horas extras ni viáticos (dependen del caso). El test E (W ± 30 %) cubre
  de $1.120.000 a $2.080.000.
- ⚠ **W > $500.000** (plan §12 e): en la pregunta e) pagar la penalidad de 500 km sale más barato
  que contratar un conductor más. Con R6 reemplazada por R7, el modelo pondría `n = 0` (camiones sin
  conductor). Ver §2.

**Cuenta de K_max (T03).**
- CCT 40/89: jornada de 8 h de lunes a viernes + 4 h el sábado (44 h semanales), **22 días de
  trabajo garantizados por mes**; para viajes, el convenio toma como mínimo **350 km por día de
  viaje** para el viático (resumen del convenio en HRUseful,
  https://hruseful.com/convenios-colectivos-de-trabajo/cct-40-89-camioneros-transporte-de-cargas-argentina/).
- K_max = 22 días × 350 km = **7.700 km/mes**. Equivale a unas 7 h de manejo a 50 km/h por día,
  razonable para distribución en el AMBA con tiempo de carga y descarga.
- No se encontró en la normativa nacional (Ley 24.449 / Decreto 779/95) un tope numérico de horas
  de conducción para el transporte urbano de cargas: el límite que se usa es el de la jornada.

**Cuenta de φ (T04).** 74.100 kg/TJ × 43,0 TJ/Gg = 3,186 kg CO₂ por kg de gasoil; con densidad
0,84 kg/l → **2,68 kg CO₂/l**. Con 0,82–0,86 kg/l el rango es 2,61–2,74. No se descuenta el corte
con biodiésel (en Argentina el gasoil lleva un porcentaje de biodiésel): se declara.

**Q (T01), nota.** Se usa el mismo camión en los dos tramos: la consigna da un único rendimiento
(4 km/l), que corresponde a un camión pesado. Un camión urbano más chico (menos pallets) quedaría
cubierto por el test C (Q de 20 a 30).

### 1.2. Base de código (F1)

Entorno: Python 3.10.11, PuLP 3.3.2, pandas 2.3.3, numpy 1.26.4, scipy 1.12.0, requests 2.34.2.
F4 a F6 se corrieron además en Python 3.12.4 (PuLP 3.3.2, scipy 1.15.3, numpy 2.2.4, highspy): los
scripts 00, 02 y 03 reprodujeron los mismos resultados en los dos entornos.

| Archivo | Qué hace |
|---|---|
| `src/modelo.py` | `resolver(...)`: el único modelo (a, d, e, d + e, configuración fija, frontera, Goyito) |
| `src/sensibilidad.py` | PL de flujos en highspy: rangos de lado derecho, de costos y costos reducidos |
| `src/weber.py` | Pregunta b): función de Weber, grilla + Nelder–Mead, Weiszfeld, centro de gravedad |
| `src/reportes.py`, `src/graficos.py` | Tablas y gráficos |
| `scripts/02_punto_a.py` … `08_tests_supuestos.py` | Un script por pregunta, más sensibilidad y tests (§3 y §4) |
| `src/config.py` | Datos de la consigna + supuestos con defaults (§1.1). `construir_params(**overrides)` falla con `KeyError` (supuesto inexistente) o `ValueError` (opción inválida o fuera de rango) |
| `src/datos.py` | Ubicaciones, plantas por producto, matrices de distancia (OSRM / haversine × factor), coeficientes por arco, enumeración de configuraciones |
| `scripts/01_distancias.py` | Baja la matriz de OSRM una vez y la guarda; calcula haversine y el factor de ruta |
| `scripts/00_verificar_datos.py` | 27 asserts contra la consigna y el plan; guarda `01_costo_por_pallet_arco.csv` |

**Distancias (T08).** OSRM `table`, perfil *driving*, consultado el 20/10/2026 →
`datos/distancias_osrm.csv` (21 × 21) y `datos/distancias_meta.json`.
- **Factor de ruta = 1,268** (mediana de OSRM / haversine sobre los 138 arcos del modelo; p10–p90:
  1,14–1,51). Es el que usan el test A y la pregunta b).
- Todos los pares cumplen ruta ≥ línea recta. Todos los puntos "enganchan" a una calle a menos de
  103 m.
- **La matriz no es simétrica:** hasta 7,7 km de diferencia entre ida y vuelta (calles de una mano,
  accesos a autopista). Ver desvío D4.
- OSRM público solo tiene perfil de auto: no considera restricciones para camiones (ya declarado en S1).

**Coeficientes por arco** (`resultados/tablas/01_costo_por_pallet_arco.csv`, Q = 26). Medianas:
tramo 1 ≈ 28 km, $531 por pallet tercerizado; tramo 2 ≈ 22 km, $597 por pallet de combustible.
Frente a $5–12 por pallet de operación del centro, **se confirma la predicción de plan §6.2**: el
transporte (≈ $60 M/mes en total) domina sobre los fijos ($4–7 M/mes), así que la ubicación va a
decidir la configuración.

## 2. Desvíos respecto del plan de trabajo

| # | Plan | Lo que se hizo | Por qué |
|---|---|---|---|
| D1 | S11: `K_max` = 9.000 km (22 días × 400 km) | **7.700 km** (22 días × 350 km) | 350 km/día es el mínimo que toma el propio CCT 40/89; 400 no tenía fuente. Sigue dentro del test E (6.000–12.000) |
| D2 | §8, e): R6 se **reemplaza** por R7 | R6 se **mantiene** y se **agrega** R7 (aplicado en `modelo.py`) | Con W ≈ $1,6 M > $500.000, sin R6 el óptimo de e) es `n = 0` y todos los km como exceso: no tiene sentido físico. Con R6, `n` lo fija la capacidad real y la penalidad cae sobre los km por encima de 500·n |
| D3 | §10: PL de flujos con `y` fija | Se fija también `n = n*` (aplicado con `fijar_n`) | `n` es entera; con `n` libre el problema de flujos no es un PL y highspy no da rangos |
| D4 | §6.2: km físicos = `2·d` | km físicos = `d(ida) + d(vuelta)` de OSRM; la tarifa del tercerizado sigue sobre `d(ida)` | La matriz de OSRM no es simétrica (hasta 7,7 km). Con haversine las dos fórmulas coinciden |
| D5 | §4.2 y §9: fijos de B+C+D = $8,6 M y de A+C+D = $9,1 M | **B+C+D = $6,6 M, A+C+D = $7,1 M** (y A+B+C = 8,7, A+B+D = 8,4, A+B+C+D = 9,6) | **Error de cuenta del plan**: la columna "Apertura" ya incluía el gerente y "Fijo total" lo volvió a sumar. Lo detectó `00_verificar_datos.py`. La diferencia con A+C ($4,2 M) baja de $4,4 M a $2,4 M: las configuraciones de 3 centros están más cerca de competir |
| D6 | §9: con el test B "la tabla crece a 8 configuraciones" | Son **7** (A+C, A+B, B+C+D, A+C+D, A+B+C, A+B+D, A+B+C+D) | Error de conteo del plan |
| D7 | §12 a.4: frontera con ~10 valores de ε y gráfico de línea | 30 valores de ε, se dejan las soluciones distintas (7) y se grafica **en escalones** | Con `n` entera, muchos ε dan la misma solución y entre dos puntos no hay soluciones intermedias: una línea recta sugeriría combinaciones que no existen |
| D8 | §11: un mapa con flechas proveedor → CD y CD → súper, con etiquetas de pallets | El tramo 2 va en un **mapa** ampliado a la zona de los súper (color = centro, grosor = pallets, sin números). El tramo 1 va como **tabla de calor** planta × centro (`03_tabla_tramo1_a.png`), con lo que recibe cada centro, su capacidad y el uso | Con todo en un mapa, las ~30 flechas se cruzaban y los números se pisaban. Los 15 flujos planta → centro se leen mejor como tabla; el mapa queda para lo geográfico: qué centro atiende a cada súper |
| D9 | §10.3: armar el PL de flujos en highspy "desde los coeficientes de `datos.py`" | Se exporta a MPS el mismo modelo de PuLP con `config_fija`, `fijar_n` y **sin la restricción fuerte** (`fuerte=False`) | Un solo modelo, sin duplicar código. La restricción fuerte es redundante con y fija y, si queda, al perturbar la demanda cada flujo sigue atado a la demanda vieja: daba precios distintos al subir (p. ej. $1.415) y al bajar ($566). Sin ella coinciden (lo confirma el control cruzado) |
| D10 | §10.3: control cruzado "re-resolver perturbando un coeficiente, 2 o 3 casos"; T17: `03_barridos.png` | 9 casos (capacidad dentro/fuera del rango, km, demanda ±5, costo de arco dentro/fuera); umbrales afinados por bisección. El gráfico es `04_barridos.png` (el 03 pasó a ser la tabla del tramo 1) | Más casos cuestan segundos. Con ±1 pallet el ruido de CBC sobre $56 M pesa ~$0,05; con ±5 se diluye |
| D11 | §12 b: Weber con línea recta × factor de ruta; "al final, verificar el punto elegido con OSRM" | La verificación **no confirmó** el punto: por calle, el Weber económico sale +10,7 % sobre el mejor. Se agregó una **etapa 2**: grilla de 336 candidatos cada 0,01° (≈ 1 km) en la zona central, evaluada con OSRM (`table`, en lotes de 80); 33 descartados por quedar a más de 300 m de una calle. La respuesta de b) es el mejor punto por calle | El factor de ruta (1,27) es una mediana: alrededor del Weber las calles dan 1,49 veces la línea recta y alrededor del óptimo por calle, 1,24. La red real no es uniforme y decide el punto concreto. Las consultas quedan en `datos/osrm_grilla_punto_b.csv` y `datos/osrm_zonas_punto_b.json` |
| D12 | §12 b: pesos "económicos" = $ por km de cada tramo | El tramo propio pesa $325 + W/K_max = **$533 por km físico** (conductor como costo por km) | Sin los conductores, el criterio económico ignoraría el 17 % del costo. Como función de una ubicación continua, el entero `n` es escalonado y no se puede minimizar con Nelder–Mead; se informa el `n` entero del punto elegido |
| D13 | §12 c.2: "barrer `g_k`" hasta que `u_k` cambie | El umbral se calcula **exacto**: `(Z* − Z*(sin k)) / dem_k`, con `Z*(sin k)` = `resolver(goyito={k: 0})`. La bisección queda como control (±$2 alrededor del umbral) | El costo con Goyito es `min(Z*, Z*(sin k) + g·dem_k)`: lineal en `g`, el quiebre se calcula directo. Barrer costaba ~30 corridas por producto para obtener lo mismo |
| D14 | §12 c.3: el viaje directo "puede hacer menos km o más" | Hace **18,2 % menos km** que la red (116.152 vs. 141.910) | Resultado, no desvío de método. Va al informe como advertencia: el centro propio no se justifica por eficiencia de transporte |
| D15 | §13 test F: precio del carbono en $/kg "con un tipo de cambio citado" | Dólar oficial BNA venta 23/10/2026 = **$1.550** → USD 10/t = **$15,5 por kg**. Se agregaron USD 50 y 100 por t | Mostrar que el óptimo no cambia ni con 10 veces el precio de la ley |
| D16 | §13 test G: apertura ×0,5 a ×2 | **×0,05 a ×2** | Cierra el pendiente P1 (apertura como inversión amortizada en muchos meses): la configuración no cambia en ningún valor |

## 3. Resultados por pregunta

### 3.0. El modelo (F2, T11)

`src/modelo.py` → `resolver(params, escenario, config_fija, epsilon_co2, goyito, objetivo, fijar_n)`.
Un solo modelo para todo: escenarios `"a"`, `"d"`, `"e"`, `"de"`; `config_fija` deja el PL de
flujos; `epsilon_co2` arma la frontera; `goyito` queda listo para la pregunta c). 234 variables
(5 binarias, 1 entera y 228 continuas; + `u_k` si hay Goyito) y 277 restricciones; resuelve en
menos de 1 s con CBC.

- Se incluyó la **formulación fuerte** `z_jik <= dem_ik · y_j` (plan §8, nota). El óptimo coincide
  con la enumeración, que no la necesita (la configuración ya está fija).
- **D2 aplicado:** en e) `CONDUCTORES` se mantiene y se agrega `TOPE_KM`.
- Controles del óptimo (asserts en `02_punto_a.py`): demanda cumplida exacta en los 50 pares,
  ningún centro sobre su capacidad, centros cerrados sin flujo, lo que sale de las plantas = demanda
  por producto.

### 3.1. Pregunta a) (T12 a T15)

`python scripts/02_punto_a.py` → tablas 02 a 08, gráficos 01 y 02.

**Óptimo: abrir A, C y D (con gerente), 6 conductores. Costo $56.055.516 por mes.**

| Rubro | $ / mes | % |
|---|---:|---:|
| Apertura (A + C + D) | 5.100.000 | 9,1 |
| Gerente | 2.000.000 | 3,6 |
| Operación de centros | 446.654 | 0,8 |
| Tramo 1 tercerizado | 23.893.862 | 42,6 |
| Tramo 2 combustible | 15.015.000 | 26,8 |
| Conductores (6) | 9.600.000 | 17,1 |
| **Total** | **56.055.516** | 100 |

- Ocupación: A 31.481 / 40.000 (79 %), C 10.369 / 15.000 (69 %), **D 10.000 / 10.000 (lleno)**.
- Ambiental: 141.910 km/mes → 35.478 l de gasoil → **95.080 kg CO₂/mes** (tramo 1: 64.126; tramo 2: 30.954).
- Asignación: C atiende S2 y S3 (noroeste); D atiende S9 y casi todo S7 y parte de S1 (sur de CABA);
  A el resto. Fideos y Leche usan las dos plantas: Fideos 2 → A y D, Fideos 1 → C; Leche 1 (sur) → D,
  Leche 2 (norte) → A y C.

**Enumeración (control, plan §9).** El mínimo coincide con el modelo entero.

| Configuración | Costo [$] | km | kg CO₂ | Conductores |
|---|---:|---:|---:|---:|
| **A+C+D** | **56.055.516** | 141.910 | 95.080 | 6 |
| A+C | 57.730.244 (+1,67 M) | 142.371 | 95.389 | 8 |
| B+C+D | 59.502.152 (+3,45 M) | 147.701 | 98.960 | 7 |

**Por qué A+C+D y no A+C (el más barato en fijos).** Abrir D acorta 15.400 km/mes del tramo propio
→ ahorra $5,0 M de combustible y 2 conductores ($3,2 M). Cuesta $0,9 M de apertura + $2,0 M de
gerente y $3,6 M más de tramo 1 (las plantas quedan más lejos de D). Neto: −$1,67 M (3 %). **La
predicción del plan §4.2 ("A + C es la cota") no se cumple**: el transporte pesa más que los fijos.
A+C+D es además la de menos CO₂ de las tres.

⚠ **Hallazgo: la restricción de conductores está activa en las tres configuraciones.** Los km del
tramo 2 son exactamente 6, 8 y 7 × 7.700. El modelo reacomoda flujos para no pagar un conductor
más (pasa km del tramo 2 al tramo 1 tercerizado). La decisión depende de `K_max` y `W`: el test E
(T22) es clave.

**Frontera costo–CO₂ (T14).** ε-restricción con 30 valores entre el mínimo CO₂ (91.973 kg) y el
óptimo de costo (95.080 kg); quedan 7 soluciones distintas, **todas A+C+D**. Es una **escalera**:
cada escalón es un conductor más (6 → 9). Bajar el CO₂ obliga a pasar km del tramo 1 (tercerizado,
$500 por km de ida ≈ $250 por km físico) al tramo 2 (propio, $325 por km físico + conductores).
Reducir 3,3 % el CO₂ (−3,1 t/mes) cuesta +8,7 % ($4,85 M/mes) ≈ **$1.560 por kg de CO₂**; el
primer escalón (−2,7 t por +$1,13 M) sale ≈ $420 por kg. Ver `01_frontera_costo_co2.png`.

### 3.2. Sensibilidad — informe b) (F3, T16 y T17)

`python scripts/03_sensibilidad.py` → tablas 09 a 12b, gráfico `04_barridos.png`.

**Cómo se hizo (T16).** Se fijan A, C, D abiertos, el gerente y los 6 conductores (D3) y queda el
PL de flujos. Es el mismo modelo de `modelo.resolver` (`config_fija`, `fijar_n`, `fuerte=False`)
exportado a MPS y resuelto con **highspy 1.15.1** (`getRanging`). Costo HiGHS = costo PuLP/CBC
($56.055.516; diferencia < 1 centavo).

**b.i — Recursos (precio = cambio del costo por una unidad más del recurso).**

| Recurso | Usado / disponible | Precio sombra | Rango de validez |
|---|---|---:|---|
| Capacidad de A | 31.481 / 40.000 | 0 | [31.481, ∞) |
| Capacidad de C | 10.369 / 15.000 | 0 | [10.369, ∞) |
| **Capacidad de D** | 10.000 / 10.000 | **−$265,8 por pallet** | [9.820, 10.670] |
| **km de los 6 conductores** | 46.200 / 46.200 | **−$222,3 por km** | [45.960, 47.273] |

- D y los conductores son los dos cuellos de botella. Un pallet más de capacidad en D ahorra
  $266/mes (hasta +670 pallets); un km más de manejo ahorra $222 (hasta +1.073 km).
- Lectura del precio de los conductores: 7.700 km × $222 = $1,71 M > W = $1,6 M, pero el precio
  vale solo hasta +1.073 km: por eso el entero no contrata un 7.º conductor.
- **Demanda** (precio sombra de `DEM_i_k`, el "costo marginal de servir"): entre **$470** (Gaseosas
  en S8 y S9: la planta está al lado de D) y **$2.228** (Arroz en S1: planta en el extremo
  noroeste, súper en el sureste). Tabla 10 × 5 en `09_rangos_lado_derecho.csv`.

**b.ii — Costos.** 67 arcos con flujo (`10_rangos_costos.csv`): costo por pallet y rango en que la
solución no cambia. Hay **degeneración** (típica del transbordo): 6 arcos no tienen margen para
subir y 4 no lo tienen para bajar (p. ej. Fideos 2 → A, 13.300 pallets, admite subir $38 y no
bajar). 104 arcos sin uso con su costo reducido (`11_costos_reducidos.csv`); 2 tienen costo
reducido 0 (A → S7 Fideos y Galletitas): **hay óptimos alternativos** en cómo se reparten los
productos entre un par centro–súper (el costo del tramo 2 no depende del producto). El total por
par centro–súper sí es único.

**Control cruzado** (`11b_control_cruzado.csv`, 9 casos, todos OK): se cambia el DATO en el
modelo de PuLP y se re-resuelve. Capacidad de D +603 → −$265,80/pallet (= HiGHS); +1.005 (fuera del
rango) → −$253,05 (el precio cambia, como debe). km +965 → −$222,26. Demanda S9 Leche ±5 →
$821,10; S8 Fideos ±5 → $566,31. Costo Galletitas 1 → C dentro del rango: los flujos no cambian;
fuera: cambian.

**T17 — Barridos (re-resolviendo el entero).** A+C+D es óptima en casi todo el rango:

| Parámetro | Rango barrido | Configuración | Umbral |
|---|---|---|---|
| Tarifa del tercerizado T | 250 a 1.000 $/km | A+C+D → **A+C** | **$890,8/km** (+78 % sobre $500) |
| Pallets por camión Q | 20 a 30 | A+C+D siempre | — |
| Apertura | ×0,5 a ×2 | A+C+D siempre | — |
| Demanda total | ×0,8 a ×1,3 | A+C+D → **sin solución** | **×1,254** (= 65.000 / 51.850) |

- Con tarifa alta conviene A+C: sin D, el tramo 1 es más corto (las plantas están al norte).
- Con S2 (un solo centro principal), la capacidad máxima es A+C+D = 65.000: la demanda puede
  crecer como mucho 25,4 %. Más allá habría que permitir A y B juntos (test B).
- Q es el parámetro que más mueve el costo (de $70,6 M con Q = 20 a $50,5 M con Q = 30) y el CO₂
  (122 a 80 t), pero no la configuración.
- Lo que falta barrer (W, K_max) es el test E de F5.

### 3.3. Pregunta b) — un único centro (F4, T18)

`python scripts/04_punto_b.py` → tablas 13, 13b, 13c, gráfico `05_mapa_punto_b.png`. Módulo
`src/weber.py` (el único cálculo que no usa `modelo.resolver`).

**Etapa 1 — Weber continuo** (línea recta × 1,268, grilla de 0,004° + Nelder–Mead desde los 8
mejores puntos):

| Criterio | Punto | Zona | Control Weiszfeld |
|---|---|---|---|
| Económico ($; conductor = $208/km) | −34,5729; −58,5270 | Villa Maipú (Gral. San Martín), a 0,4 km de S4 | a 10 m |
| Ambiental (km físicos) | −34,5297; −58,5454 | Villa Adelina | a 15 m |
| Centro de gravedad | −34,5740; −58,5509 | 2,2 km al oeste del Weber económico | — |

Con la misma métrica, A sale +10,2 %, B +7,2 %, C +45,9 % y D +37,3 % sobre el Weber económico.

**Etapa 2 — por calle (D11).** 336 candidatos, 303 válidos. Costo con conductores enteros:

| Ubicación | Costo $/mes | Sobre el mejor | Conductores | km | kg CO₂ |
|---|---:|---:|---:|---:|---:|
| **Óptimo por calle (−34,57; −58,48), Villa Urquiza** | **61.019.265** | — | 10 | 157.684 | 105.649 |
| Óptimo ambiental por calle (−34,51; −58,54), Villa Adelina | 65.501.331 | +7,3 % | 13 | 150.697 | 100.967 |
| Weber económico de la etapa 1 | 67.573.202 | +10,7 % | 11 | 175.607 | 117.656 |
| Centro A | 64.916.011 | +6,4 % | 10 | 172.771 | 115.757 |
| Centro B | 75.268.449 | +23,4 % | 12 | 195.775 | 131.169 |
| Centro C | 83.578.568 | +37,0 % | 17 | 188.332 | 126.183 |
| Centro D | 85.584.233 | +40,3 % | 13 | 232.012 | 155.448 |

- 4 candidatos quedan a menos de 1 % del mejor (lat −34,58 a −34,54; lon −58,50 a −58,47): la
  respuesta es una **zona** (noroeste de la Ciudad, límite con el conurbano norte), no un punto exacto.
- Desde el óptimo por calle los recorridos son 1,24 veces la línea recta; desde el Weber, 1,49.
- **Comparación con a):** el centro único, sin costos fijos, gasta en transporte $61,0 M contra
  $48,5 M de A+C+D (+25,8 %), 15.774 km más y 10,6 t más de CO₂ por mes. Aun sumándole a A+C+D sus
  $7,6 M de fijos y operación, la red de tres centros es más barata.
- Nota de nombres: Nominatim devolvió "Partido de Vicente López" para el Weber ambiental y "Partido
  de San Isidro" para el ambiental por calle (Villa Adelina está repartida entre los dos partidos).
  En el informe se nombra solo la localidad.

### 3.4. Pregunta c) — precio mínimo de Goyito (F4, T19)

`python scripts/05_punto_c.py` → tablas 14 y 14b, gráfico `06_umbral_goyito.png`.

| Producto | Umbral $/pallet | Con carbono | Directo a $500/km | Red sin el producto |
|---|---:|---:|---:|---|
| Gaseosas | 630 | 637 | 437 | A+C+D, 6 conductores |
| Fideos | 784 | 791 | 407 | A+C+D, 4 |
| Leche | 881 | 890 | 408 | A+C+D, 5 |
| Galletitas | 1.027 | 1.033 | 608 | A+C+D, 5 |
| Arroz | 1.520 | 1.527 | 1.089 | A+C+D, 5 |
| **Todo a Goyito, precio único** | **1.081** | 1.086 | 555 | sin centro |

- Bisección (±$2) con la binaria `u_k`: OK en los 5 productos.
- **La predicción del plan no se cumplió:** sacar Fideos deja 31.550 pallets y "alcanza A solo", pero
  el modelo **sigue abriendo A+C+D** en los cinco casos: el transporte manda más que los fijos.
- Suma de umbrales × demanda = $49,3 M < $56,1 M: los $6,8 M de diferencia ≈ apertura + gerente
  ($7,1 M), que no se pueden asignar a un producto.
- Ambiental: el viaje directo hace **116.152 km contra 141.910 (−18,2 %)** y 17,3 t CO₂ menos por mes
  (de −3,3 % en Gaseosas a −31,8 % en Leche). Con $15,5/kg, los umbrales suben $6 a $10.
- El costo del viaje directo a la tarifa de mercado queda por debajo del umbral en todos los
  productos (total $28,8 M/mes): un operador podría cobrar menos que el umbral y cubrir su
  transporte. El centro propio no se justifica por eficiencia de transporte.

### 3.5. Pregunta d) — flota propia en el tramo 1 (F4, T20)

`python scripts/06_punto_d.py` → tablas 15 y 15b, gráficos 07 a 09.

| | a) | d) | Variación |
|---|---:|---:|---:|
| Configuración | A+C+D | A+C+D | — |
| Costo | $56.055.516 | **$80.948.592** | **+44,4 %** |
| Conductores | 6 | 18 | +12 |
| km | 141.910 | 137.274 | −3,3 % |
| kg CO₂ | 95.080 | 91.974 | **−3,3 %** |

- Por km físico: tercerizado $250 (500 por km de ida) contra propio $325 + $208 de conductor = $533.
- El CO₂ de d) coincide con el mínimo de la frontera de a) (91.973 kg), que con el tercerizado cuesta
  $60,9 M: la misma reducción sale $20 M más barata sin flota propia. Con flota propia, cada t de CO₂
  evitada cuesta ≈ $8 M.
- Enumeración: A+C queda a $94.586 de A+C+D (0,1 %); B+C+D a $4,1 M.
- Se confirma la predicción del plan §12 d (más caro por km; el CO₂ cambia solo por las rutas).

### 3.6. Pregunta e) — tope de 500 km (F4, T21)

`python scripts/07_punto_e.py` → tablas 16, 16b, 16c, gráficos 10 y 11.

| Escenario | Costo $/mes | Variación | Conductores | Exceso km | kg CO₂ |
|---|---:|---:|---:|---:|---:|
| a) Sin tope | 56.055.516 | — | 6 | 0 | 95.080 |
| **e) Con tope, se paga la penalidad** | **98.842.374** | **+76,3 %** | 6 | 42.608 | 95.665 |
| e) Con tope, cumplido contratando | 193.699.969 | +245,6 % | 92 | 0 | 95.236 |
| e) 500 km por día (11.000/mes) | 56.055.516 | 0 | 6 | 0 | 95.080 |
| d) Flota propia | 80.948.592 | +44,4 % | 18 | 0 | 91.974 |
| d + e) | 209.222.470 | +273,2 % | 18 | 128.273 | 91.973 |

- Formulación: `TOPE_KM: km_prop − 500·n ≤ exc` y `+1.000·exc` en el funcional (meta con desvío,
  Clase 05). R7 (capacidad real) se mantiene (D2).
- **Barrido de W:** con W ≤ $490.000 se contratan 91 conductores (queda un exceso residual de 108 km,
  menos que un conductor); con W ≥ $510.000 se queda en 6 y se paga la penalidad. El umbral es
  exactamente 500 km × $1.000 = $500.000.
- **La predicción del plan §12 e.3 no se cumplió:** el plan esperaba que el tope acortara km y bajara el
  CO₂. En el caso base el modelo **pasa km al tramo tercerizado** (que no está alcanzado por el tope):
  tramo 2 de 46.200 a 45.608 km, tramo 1 de 95.710 a 97.175 km → **CO₂ +0,6 %**. En d + e no hay
  tramo al cual desviar y el CO₂ no cambia.
- Enumeración en e): A+C+D, B+C+D (+$6,6 M), A+C (+$12,7 M).

## 4. Tests de supuestos (F5, T22)

`python scripts/08_tests_supuestos.py` → tabla 17, gráfico `12_tests_supuestos.png`.

### 4.1. Tabla resumen (plan §13 completa)

| Test | Supuesto | Alternativa | Configuración | Costo | CO₂ | ¿Cambia la conclusión? |
|---|---|---|---|---:|---:|---|
| A | S1 distancias | Línea recta × 1,268 | A+C+D | +1,8 % | +2,7 % | No |
| B | S2 principal | Al menos uno de A y B | A+C+D | 0 | 0 | No: A y B juntos nunca conviene |
| C | S8 camión | Q = 20 / 22 / 24 / 28 / 30 | A+C+D | +26,0 / +15,9 / +7,9 / −5,6 / −10,0 % | +28,8 a −15,7 % | No en la configuración; sí mucho en costo y CO₂ |
| D | S10 tarifa | Ida y vuelta | **A+C** | +38,9 % | +0,3 % | **Sí**: equivale a T = $1.000 > umbral $891 |
| E | S11 sueldo | W ±30 % | A+C+D | ±5,1 % | 0 | No |
| E | S11 km por conductor | K_max 6.000 / 7.000 / 9.000 / 10.000 / 12.000 | A+C+D | +5,1 / +2,2 / −0,8 / −3,6 / −6,3 % | −1,2 a −2,8 % | No (8 a 4 conductores) |
| F | S13 carbono | USD 10 / 50 / 100 por t | A+C+D | 0 (sin el término de carbono) | 0 | No: ni los flujos cambian |
| G | §7.1 apertura | ×0,05 / 0,1 / 0,25 / 0,5 / 2 | A+C+D | −8,6 a +9,1 % | 0 | No |

### 4.2. Propiedades verificadas (8 de 8 OK)

Relajar S2 nunca sube el costo · más pallets por camión nunca lo suben · la tarifa ida y vuelta nunca
lo baja · con precio del carbono el CO₂ nunca sube · más precio del carbono, CO₂ no creciente · más km
por conductor nunca suben el costo · más sueldo nunca lo baja · más apertura nunca lo baja.

### 4.3. Pendientes de `lo_que_queda_por_hacer.md` §5

- **P1 (apertura mensual o inversión): cerrado.** El test G llega a ×0,05 (una inversión amortizada en
  unos 20 meses) y A+C+D sigue óptima. Va al informe como supuesto S10 con el test G de respaldo.
- **P2 (convenio en el acta oficial): no se pudo confirmar** contra el acta homologada; se mantienen
  los valores de §1.1. El test E muestra que la conclusión no depende de ellos (W ±30 %, K_max 6.000 a
  12.000: siempre A+C+D). Si se confirma otro valor, cambia el costo, no la recomendación.

## 5. Verificaciones

### 5.1. Asserts por script

| Script | Qué verifica |
|---|---|
| `00_verificar_datos.py` | 27 chequeos de datos (demanda, puntos, centros, distancias, coeficientes, validación de supuestos) |
| `02_punto_a.py` | Demanda exacta en 50 pares, capacidad, centros cerrados sin flujo, balance de plantas; enumeración = entero |
| `03_sensibilidad.py` | Costo HiGHS = PuLP; 9 controles cruzados |
| `04_punto_b.py` | Weiszfeld a menos de 50 m del óptimo; refinamiento ≤ grilla; óptimo ≤ todos los candidatos; el ambiental minimiza km; óptimo por calle fuera del borde de la zona; centro único más caro que el transporte de a) |
| `05_punto_c.py` | Goyito gratis siempre se lleva el producto; bisección en los 5 productos; km por producto suman los de a) |
| `06_punto_d.py` | Demanda, capacidad, conductores suficientes, km propios = km totales; enumeración = entero |
| `07_punto_e.py` | `exc` = exceso real; R7 respetada; con penalidad prohibitiva no hay exceso; 500 km/día no limita; umbral de W en $500.000; enumeración = entero |
| `08_tests_supuestos.py` | Las 8 propiedades de §4.2 |

### 5.2. Predicciones del plan contra resultados

| Predicción del plan | Sección | Resultado |
|---|---|---|
| El transporte domina sobre los fijos | §6.2 | ✔ 86,5 % del costo |
| "A + C es la cota" (la más barata en fijos) | §4.2 | ✘ gana A+C+D por $1,67 M |
| Sacar Fideos podría permitir cerrar centros | §12 c | ✘ sigue A+C+D |
| El viaje directo puede hacer más o menos km | §12 c.3 | Hace 18,2 % menos |
| Flota propia: más cara por km; el CO₂ solo cambia por las rutas | §12 d | ✔ +44,4 %, CO₂ −3,3 % |
| e): si W > $500.000 se paga la penalidad | §12 e.2 | ✔ umbral exacto en $500.000 |
| e): el tope acorta km y baja el CO₂ | §12 e.3 | ✘ CO₂ +0,6 % (desvío al tercerizado) |
| b): el Weber con factor de ruta es la respuesta, verificada con OSRM | §12 b | ✘ por calle sale +10,7 %; hizo falta la etapa 2 (D11) |

## 6. Conclusiones para el informe

1. **Abrir A, C y D** (gerente, 6 conductores): $56,06 M/mes, 35.478 l y 95,1 t CO₂ por mes. Es a la vez
   la configuración más barata y la de menos emisiones.
2. **La decisión es robusta**: solo cambia (a A+C) si la tarifa del tercerizado supera $891/km. No
   depende de los datos externos (camión, conductores, emisiones) ni del período de la apertura.
3. **Los cuellos de botella son la capacidad de D ($266 por pallet) y los km de los conductores
   ($222 por km).** La restricción de conductores está activa en todas las configuraciones.
4. **Reducir emisiones es caro y acotado**: −3,3 % como máximo, desde $420/kg.
5. **b)** Un centro único iría en el noroeste de la Ciudad (Villa Urquiza); aun gratis, cuesta más en
   transporte que la red de tres centros.
6. **c)** Goyito tendría que cobrar menos de $1.081 por pallet en promedio (umbrales por producto de
   $630 a $1.520) para que el centro no convenga. El viaje directo es más corto y contamina menos.
7. **d)** La flota propia cuesta +44 % y baja el CO₂ 3,3 %; la misma reducción sale $20 M más barata
   con el tercerizado.
8. **e)** El tope de 500 km por mes cuesta $42,6 M de penalidad (+76 %) y sube el CO₂: conviene
   renegociarlo en términos diarios.
