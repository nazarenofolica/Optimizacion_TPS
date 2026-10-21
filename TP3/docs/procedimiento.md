# TP3 CarroMenos — Procedimiento (bitácora de desarrollo)

> **Qué es este archivo.** El registro de lo que **efectivamente se hizo** al codificar y
> resolver el modelo, incluyendo **en qué se apartó del plan y por qué**. El plan está en
> [`plan_de_trabajo.md`](plan_de_trabajo.md) y **no se reescribe** para que coincida con esto.
>
> **Estado:** F0 a F3 hechas (datos, código base, modelo, pregunta a y sensibilidad). Próximo: F4 (preguntas b a e).

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

| Archivo | Qué hace |
|---|---|
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
| D3 | §10: PL de flujos con `y` fija | *(propuesto)* fijar también `n = n*` | `n` es entera; con `n` libre el problema de flujos no es un PL y highspy no da rangos |
| D4 | §6.2: km físicos = `2·d` | km físicos = `d(ida) + d(vuelta)` de OSRM; la tarifa del tercerizado sigue sobre `d(ida)` | La matriz de OSRM no es simétrica (hasta 7,7 km). Con haversine las dos fórmulas coinciden |
| D5 | §4.2 y §9: fijos de B+C+D = $8,6 M y de A+C+D = $9,1 M | **B+C+D = $6,6 M, A+C+D = $7,1 M** (y A+B+C = 8,7, A+B+D = 8,4, A+B+C+D = 9,6) | **Error de cuenta del plan**: la columna "Apertura" ya incluía el gerente y "Fijo total" lo volvió a sumar. Lo detectó `00_verificar_datos.py`. La diferencia con A+C ($4,2 M) baja de $4,4 M a $2,4 M: las configuraciones de 3 centros están más cerca de competir |
| D6 | §9: con el test B "la tabla crece a 8 configuraciones" | Son **7** (A+C, A+B, B+C+D, A+C+D, A+B+C, A+B+D, A+B+C+D) | Error de conteo del plan |
| D7 | §12 a.4: frontera con ~10 valores de ε y gráfico de línea | 30 valores de ε, se dejan las soluciones distintas (7) y se grafica **en escalones** | Con `n` entera, muchos ε dan la misma solución y entre dos puntos no hay soluciones intermedias: una línea recta sugeriría combinaciones que no existen |
| D9 | §10.3: armar el PL de flujos en highspy "desde los coeficientes de `datos.py`" | Se exporta a MPS el mismo modelo de PuLP con `config_fija`, `fijar_n` y **sin la restricción fuerte** (`fuerte=False`) | Un solo modelo, sin duplicar código. La restricción fuerte es redundante con y fija y, si queda, al perturbar la demanda cada flujo sigue atado a la demanda vieja: daba precios distintos al subir (p. ej. $1.415) y al bajar ($566). Sin ella coinciden (lo confirma el control cruzado) |
| D10 | §10.3: control cruzado "re-resolver perturbando un coeficiente, 2 o 3 casos"; T17: `03_barridos.png` | 9 casos (capacidad dentro/fuera del rango, km, demanda ±5, costo de arco dentro/fuera); umbrales afinados por bisección. El gráfico es `04_barridos.png` (el 03 pasó a ser la tabla del tramo 1) | Más casos cuestan segundos. Con ±1 pallet el ruido de CBC sobre $56 M pesa ~$0,05; con ±5 se diluye |
| D8 | §11: un mapa con flechas proveedor → CD y CD → súper, con etiquetas de pallets | El tramo 2 va en un **mapa** ampliado a la zona de los súper (color = centro, grosor = pallets, sin números). El tramo 1 va como **tabla de calor** planta × centro (`03_tabla_tramo1_a.png`), con lo que recibe cada centro, su capacidad y el uso | Con todo en un mapa, las ~30 flechas se cruzaban y los números se pisaban. Los 15 flujos planta → centro se leen mejor como tabla; el mapa queda para lo geográfico: qué centro atiende a cada súper |

## 3. Resultados por pregunta

### 3.0. El modelo (F2, T11)

`src/modelo.py` → `resolver(params, escenario, config_fija, epsilon_co2, goyito, objetivo, fijar_n)`.
Un solo modelo para todo: escenarios `"a"`, `"d"`, `"e"`, `"de"`; `config_fija` deja el PL de
flujos; `epsilon_co2` arma la frontera; `goyito` queda listo para la pregunta c). 239 variables
(6 enteras/binarias + `u_k` si hay Goyito), resuelve en menos de 1 s con CBC.

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

## 4. Tests de supuestos

*(por hacer)*

## 5. Verificaciones

*(por hacer)*

## 6. Conclusiones para el informe

*(por hacer)*
