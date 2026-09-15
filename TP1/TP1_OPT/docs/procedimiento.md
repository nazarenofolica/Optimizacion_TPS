# TP1 Pastarazzi — Procedimiento (bitácora de desarrollo)

> **Qué es este archivo.** El registro de lo que **efectivamente se hizo** al codificar y
> resolver el modelo, incluyendo **en qué se apartó del plan y por qué**. El plan está en
> [`plan_de_trabajo.md`](plan_de_trabajo.md) y **no se reescribe** para que coincida con esto.
>
> **Estado:** TP completo. Puntos a), b) y c) resueltos (§3, §5.1, §5.2),
> pregunta d) resuelta (§5.3) y tests de supuestos corridos (§4). El informe
> final está redactado en [`informe/informe.tex`](../informe/informe.tex),
> compilado a `informe/informe.pdf`.

---

## 1. Implementación

### 1.1. Entorno

Python 3.10.11. Se instaló `pulp 3.3.2` (solver **CBC**, el único disponible en el equipo);
`pandas 2.3.3`, `matplotlib 3.10.9` y `scipy 1.12.0` ya estaban. Ver `requirements.txt`.

### 1.2. Estructura

```
TP1_OPT/
├── plan_de_trabajo.md            esquema (lo que se planeó)
├── procedimiento.md              este archivo (lo que pasó)
├── requirements.txt
├── src/
│   ├── config.py                 datos del enunciado + supuestos S1..S9 + reglas
│   ├── datos.py                  tablas derivadas (mercado, base, coeficientes, cupos)
│   ├── modelo.py                 construcción y resolución del LP
│   ├── reportes.py               tablas de salida
│   └── graficos.py               gráficos (matplotlib) para el informe
├── scripts/
│   ├── 00_verificar_datos.py     31 asserts contra los valores calculados a mano
│   ├── 01_modelo_base.py         resuelve el punto a)
│   ├── 02_pregunta_b.py          resuelve la pregunta b) (barrido de S6/R2)
│   └── 03_pregunta_c.py          resuelve la pregunta c) (fronteras de Pareto)
└── resultados/
    ├── tablas/*.csv
    └── graficos/*.png
```

### 1.3. Diseño del modelo parametrizado

Todo se resuelve con **una sola función**, tal como preveía el plan §13:

```python
modelo.resolver(params, objetivo="neta", epsilon=None, desactivar=())
```

- `params` viene de `config.construir_params(**overrides)`. Los overrides pisan cualquier
  supuesto o regla, y **fallan con `KeyError` si el nombre no existe** — decisión deliberada:
  un typo silencioso en un barrido de 40 corridas es un error caro de encontrar.
- `objetivo` elige entre los tres funcionales del plan §6.
- `desactivar` omite restricciones por nombre → es lo que van a usar las preguntas b) y d).
- `epsilon` agrega el piso de facturación del método ε-constraint → pregunta c).

Las restricciones se declaran **con nombre** (`R1_presupuesto`, `R3_triguetti_min`, …) para
poder leer `.pi` (precio sombra) y `.slack` (holgura) por nombre.

**Detalle de modelado:** los topes de tramo (R7, R8) se codificaron como **restricciones con
nombre y no como cotas superiores de la variable**. Como bounds el solver no devuelve precio
sombra sino costo reducido; como restricciones sí, y eso hace falta para el análisis
post-óptimo.

---

## 2. Desvíos respecto del plan de trabajo

### 2.1. ⚠ Se agregó una restricción que no estaba en el plan: **R10, saturación del mercado**

**Qué pasó.** La primera corrida del modelo tal como estaba planeado dio un resultado
imposible:

```
Segmento   Share inicial   Share final
Alto           14,00 %       123,03 %
```

Rena Speziale captaba **1.308.333 clientes nuevos en un segmento que tiene 1.200.000 personas
en total**. El modelo permitía captar más gente de la que existe.

**Por qué pasó.** El enunciado da un techo de participación **solo para la gama baja** (*"la
suma de ambas no supere aproximadamente el 65 % de participación en el mercado de menor poder
adquisitivo"*, → R5). Para los segmentos medio y alto no dice nada, y el plan tomó esa
ausencia al pie de la letra. Pero la ausencia de un techo *comercial* no elimina el techo
*físico*: ningún segmento puede superar el 100 % de su TAM.

**Qué se hizo.**

1. **Nueva restricción R10**, una por segmento:
   `clientes nuevos del segmento ≤ (tope − share ya ocupado) × TAM`
   con `tope = R10_tope_saturacion = 1.00` (100 % del TAM), parametrizado en `config.REGLAS`.
   Cupos resultantes: bajo 10.105.000 · medio 5.300.000 · alto 1.032.000 clientes.

2. **Tramo de "desperdicio"** para cada marca: un último tramo de tasa 0 y sin tope.
   Sin él el problema se volvía **infactible**: R4 exige `x_RS ≥ 10.200`, pero el segmento
   alto se llena con $8.570MM, así que no había forma de cumplir la regla del directorio.
   Con el tramo de desperdicio, esa plata se puede invertir pero no capta a nadie — que es
   exactamente lo que pasa en la realidad y, además, **el hallazgo más fuerte del punto a)**
   (§3.4).

**Impacto en el resultado.** Cambió el plan óptimo por completo:

| | Sin R10 (incorrecto) | Con R10 (correcto) |
|---|---:|---:|
| Don Carlo / Agnellis | $0 / $0 | **$850 / $850** |
| Candealix | $566,7 | **$0** |
| Rena Speziale | $11.333,3 | **$10.200** |
| Utilidad neta | $79.066,39 MM | **$76.578,60 MM** |
| Share del segmento alto | 123,03 % (imposible) | 100,00 % |

**Limitación que queda abierta.** Un 100 % del segmento alto sigue siendo comercialmente
absurdo: implica que Pastarazzi se queda con **todos** los clientes premium del país. El techo
realista es más bajo. Por eso `R10_tope_saturacion` quedó parametrizado: es un candidato
directo para el barrido de sensibilidad (§4), probando 60 %, 70 %, 80 %.

### 2.2. Cambio de estructura de datos en los tramos

El plan preveía los tramos como tuplas `(límite, tasa)`. Al agregar el tramo de desperdicio
las tuplas se volvieron ilegibles en los reportes, así que pasaron a diccionarios
`{"limite", "tasa", "etiqueta"}`. La etiqueta es la que aparece en la tabla de plan de
inversión ("1er tramo", "hasta saturar", "desperdicio").

### 2.3. Un valor esperado del plan estaba mal calculado

El plan §3.5 informa un market share inicial de "48,10 %" y en el script de verificación se
escribió como `48,1043`. El valor correcto es **48,1025 %** (797.107 / 1.657.100). Error de
redondeo al transcribir, no del modelo: lo detectó `00_verificar_datos.py` en su primera
corrida, que es exactamente para lo que existe ese script.

### 2.4. Validación de nombres en `desactivar`

Detectado al revisar el código, no al escribirlo. `modelo.resolver(desactivar=[...])`
aceptaba cualquier string: un nombre mal escrito no daba error, simplemente no desactivaba
nada y **devolvía el caso base disfrazado de contrafactual**.

Es grave porque las preguntas b) y d) se responden justamente desactivando restricciones:

```
desactivar=["R3_triguetti_min"]  ->  Z = 80.100,96   x_TRI = 0        (correcto)
desactivar=["R3_triguetti"]      ->  Z = 76.578,60   x_TRI = 5.100    (caso base!)
```

Se agregó `_validar_desactivar()`, que levanta `KeyError` con la lista de nombres válidos.
Ahora el comportamiento es coherente con `construir_params()`, que ya validaba sus overrides
por la misma razón.

### 2.5. Tolerancia de los controles cruzados

CBC devuelve las variables con ~7 cifras significativas, así que sobre valores del orden de
$10.000MM arrastra errores de hasta 1e-4. El control manual estaba escrito con tolerancia
1e-6 y marcaba como violada una restricción que se cumplía (`11.333,3333` vs `11.333,33334`).
Se subió la tolerancia a **1e-3 $MM** (mil pesos), muy por debajo de cualquier magnitud
relevante del problema.

---

## 3. Resultados del punto a)

Corrida: `python scripts/01_modelo_base.py` · estado **Optimal** en las tres corridas.

### 3.1. Plan de asignación del presupuesto

| Marca | Tramo | Inversión ($MM) | % del presupuesto |
|---|---|---:|---:|
| Don Carlo | captación | 850,00 | 5,00 % |
| Agnellis | captación | 850,00 | 5,00 % |
| Triguetti | hasta saturar | 5.100,00 | 30,00 % |
| Candealix | — | **0,00** | 0,00 % |
| Rena Speziale | 1er tramo (150 cl/MM) | 3.500,00 | 20,59 % |
| Rena Speziale | 2do tramo (100 cl/MM) | 5.070,00 | 29,82 % |
| Rena Speziale | **desperdicio (0 cl/MM)** | **1.630,00** | **9,59 %** |
| **Total** | | **17.000,00** | 100 % |

### 3.2. Mix comercial resultante

| Marca | Inversión | Clientes nuevos | Fact. base | Fact. increm. | Fact. total | Crec. | Utilidad neta | % de la fact. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Don Carlo | 850 | 340.000 | 320.821 | 13.940 | 334.761 | +4,3 % | 16.738,05 | 32,6 % |
| Agnellis | 850 | 425.000 | 192.626 | 17.425 | 210.051 | +9,1 % | 15.753,83 | 20,5 % |
| Triguetti | 5.100 | 1.020.000 | 186.048 | 59.160 | 245.208 | +31,8 % | 22.068,72 | 23,9 % |
| Candealix | 0 | 0 | 78.600 | 0 | 78.600 | 0,0 % | 6.288,00 | 7,7 % |
| Rena Speziale | 10.200 | 1.032.000 | 19.012 | 138.288 | 157.300 | **+727,4 %** | 15.730,00 | 15,3 % |
| **TOTAL** | **17.000** | **2.817.000** | **797.107** | **228.813** | **1.025.920** | **+28,7 %** | **76.578,60** | 100 % |

*(cifras en $MM/año)*

- **Utilidad neta: $76.578,60 MM** = $55.421,52 de base + $21.157,08 que aporta la campaña.
- **Utilidad operativa: $112.489,49 MM**
- **Market share: 48,10 % → 61,91 %** del mercado de pastas.

### 3.3. Distribución por canales (segmentos)

| Segmento | Mercado | Fact. total | Share inicial | Share final | Clientes nuevos | Cupo usado |
|---|---:|---:|---:|---:|---:|---:|
| Bajo | 881.500 | 498.560 | 53,00 % | 56,56 % | 765.000 | 7,6 % |
| Medio | 614.800 | 366.560 | 50,00 % | 59,62 % | 1.020.000 | 19,3 % |
| Alto | 160.800 | 160.800 | 14,00 % | **100,00 %** | 1.032.000 | **100,0 %** |

El crecimiento se concentra en el segmento alto, que queda **saturado**. Los otros dos
apenas se tocan.

### 3.4. ⚠ Hallazgo principal: las reglas del directorio obligan a quemar $1.630MM

El segmento alto se llena con **$8.570MM** de inversión en Rena Speziale
($3.500 al 150 cl/MM + $5.070 al 100 cl/MM = 1.032.000 clientes, todo el cupo disponible).
Pero R4 exige `x_RS ≥ 2 × (x_CAN + x_TRI) ≥ 2 × 5.100 = 10.200`.

```
10.200 exigidos − 8.570 útiles = $1.630 MM  →  9,59 % del presupuesto
                                               que no capta a un solo cliente
```

No es un error del modelo: es la consecuencia aritmética de combinar la regla del 30 % de
Triguetti (R3) con la del doble de Rena (R4) sobre un segmento premium chico. **Es el
argumento central de la pregunta d)** y hay que llevarlo al informe.

### 3.5. Estado de las restricciones y precios sombra

| Restricción | Holgura | Activa | Precio sombra |
|---|---:|:---:|---:|
| R1 Presupuesto | 0 | **Sí** | **+1,17875** |
| R2 Paridad Don Carlo = Agnellis | 0 | **Sí** | **−0,35875** |
| R3 Triguetti ≥ 30 % | 0 | **Sí** | **−2,49225** |
| R4 Rena ≥ 2×(Can+Tri) | 0 | **Sí** | **−1,17875** |
| R5 Tope 65 % gama baja | 1.815.000 | No | 0 |
| R7 Saturación Triguetti ($6.000MM) | 900 | No | 0 |
| R8a 1er tramo Candealix | 5.000 | No | 0 |
| R8b 1er tramo Rena | 0 | Sí (degenerada) | 0 |
| R10 Saturación bajo | 9.340.000 | No | 0 |
| R10 Saturación medio | 4.280.000 | No | 0 |
| R10 Saturación alto | 0 | **Sí** | **+0,01340** |

**Lectura:**

- **R3 es la restricción más cara del modelo: −$2,49 de utilidad por cada millón** forzado a
  Triguetti. Y no es por Triguetti en sí (rinde 1,044): es por el arrastre de R4.
- **R1 = +1,179**: cada millón adicional de presupuesto daría $1,179MM de utilidad… pero
  ojo, iría al par Don Carlo/Agnellis, el único destino libre que queda.
- **R5 (el 65 % de la gama baja) no está activa**: sobran 1.815.000 clientes de cupo. El
  freno de la gama baja no es el mercado, es que las reglas del directorio no le dejan plata.
- **R2 = −0,359**: la paridad cuesta plata porque obliga a poner en Don Carlo (0,82) lo mismo
  que en Agnellis (1,54).

### 3.6. Comparación de los tres objetivos — resultado inesperado

| | Utilidad neta | Utilidad operativa | Facturación |
|---|---:|---:|---:|
| Don Carlo / Agnellis | 850 / 850 | 850 / 850 | 850 / 850 |
| Triguetti | 5.100 | 5.100 | 5.100 |
| Candealix | 0 | 0 | 0 |
| Rena Speziale | 10.200 | 10.200 | 10.200 |
| Utilidad neta ($MM) | 76.578,60 | 76.578,60 | 76.578,60 |
| Market share (%) | 61,91 | 61,91 | 61,91 |

**Los tres objetivos dan exactamente el mismo plan.** Costo de perseguir facturación en lugar
de utilidad: **$0**.

No es un bug — se verificó a mano. Con R3 y R4 activas, la única decisión libre son los
$1.700MM que sobran, y hay solo dos destinos posibles:

| Destino | Utilidad por $MM | Facturación por $MM |
|---|---:|---:|
| Par Don Carlo + Agnellis | **1,179** | **18,45** |
| Candealix (arrastra 2 $MM estériles a Rena) | 0,464 | 5,80 |

El par gama baja **domina a Candealix en los dos criterios a la vez**, así que no hay nada que
negociar.

**Implicancia para la pregunta c):** bajo las reglas actuales, la frontera de Pareto entre
rentabilidad y market share **colapsa en un solo punto**. La discusión entre accionistas y
directivos es, con estas reglas, una discusión sin objeto: no hay trade-off que resolver
porque el directorio ya fijó el plan. El trade-off recién aparece cuando se relajan R3 y R4 —
y eso es justamente lo que hay que mostrar en c).

---

## 4. Tests de supuestos [RESUELTO]

Corrida: `python scripts/05_tests_supuestos.py`. Dos protocolos, tal como preveía
`plan_de_trabajo.md` §11:

**A. Barrido OAT ±30 %** sobre los 14 parámetros numéricos de S1 a S4 más
`R10_tope_saturacion` (agregada en el punto a), no prevista en el plan original;
se la barrió 70 %–100 %, ya que 100 % es cota dura). Salida: tabla
`resultados/tablas/12_tornado_oat.csv` y gráfico
`resultados/graficos/05_tornado_supuestos.png`.

- **De los 14 parámetros, uno solo cambia el plan óptimo** dentro del rango, y en
  un caso límite: el tope del 65 % de la gama baja (R5), solo en su extremo
  inferior. El −30 % teórico (45,5 %) resultó **infactible** porque Don Carlo +
  Agnellis ya ocupan el 53 % del segmento sin invertir un peso — el verdadero
  piso de esa regla es el share ya instalado, no un −30 % genérico. Se ajustó el
  extremo inferior del barrido a 55 % (el mínimo plausible por encima de ese
  piso) y se documentó el motivo en la tabla.
- Los que más mueven el **nivel** de la utilidad (sin tocar el mix): margen neto
  de Triguetti (hasta ±8,65 %), tasa de captura de billetera S2 (±8,29 %,
  asimétrico) y margen neto de Don Carlo (±6,56 %).
- Conclusión para el informe: el plan del punto a) no depende de forma frágil de
  los datos que había que completar con criterio propio.

**B. Escenarios estructurales** (S5, S7, S8; R6 ya verificado en §6.4): se
resolvió el modelo completo bajo cada lectura alternativa. Salida:
`resultados/tablas/13_escenarios_estructurales.csv`.

| Escenario | ΔZ vs. base | ¿Cambia el mix? |
|---|---:|:---:|
| S5 — mix Fig. 2 en vez de posicionamiento | +0,51 % | No |
| S7a — R3 sobre lo asignado en vez de sobre $17.000MM | 0,00 % | No |
| S7b — R4 en igualdad en vez de piso | 0,00 % | No |
| S8 — presupuesto descontado del funcional | −22,20 %* | No |

\* Mismo plan óptimo; solo cambia el número reportado ($Z - $17.000MM$).

**Nota de implementación:** probar S5 en su lectura alternativa ("mix_fig2")
exigió generalizar `datos.facturacion_por_millon` y la restricción R10 de
`modelo.construir` para repartir la captación de cada marca entre varios
segmentos con pesos (antes asumían un único segmento por marca). Con el
supuesto base ("posicionamiento") el comportamiento es idéntico al de antes
—verificado contra los resultados de §3 y §5.1, que no cambiaron un solo
decimal—, así que no es un desvío del modelo, es una generalización que lo
deja listo para las dos lecturas de S5.

## 5. Preguntas b), c) y d)

### 5.1. Pregunta b) — Escenarios de crecimiento de Agnellis [RESUELTO]

Corrida: `python scripts/02_pregunta_b.py` · 10 corridas del barrido, todas
**Optimal**, y 6 controles cruzados en verde.

**Cómo se armó.** R2 (supuesto S6) se generalizó de `x_DC = x_AG` a
`x_DC = k · x_AG`, y se barrió `k` de 1,00 (paridad total, el caso base del punto
a) a 0,00 (toda la plata libre del par gama baja va a Agnellis), reutilizando
`modelo.resolver()` sin tocar el modelo. Es literalmente el test del supuesto S6.

| k | Don Carlo ($MM) | Agnellis ($MM) | Presencia DC solo campaña (%) | Presencia DC base+campaña (%) | Utilidad neta ($MM) |
|---:|---:|---:|---:|---:|---:|
| 1,00 (base) | 850,00 | 850,00 | 44,44 | 64,68 | 76.578,60 |
| 0,75 | 728,57 | 971,43 | 37,50 | 64,22 | 76.665,72 |
| 0,50 | 566,67 | 1.133,33 | 28,57 | 63,60 | 76.781,89 |
| 0,30 | 392,31 | 1.307,69 | 19,35 | 62,94 | 76.906,99 |
| 0,00 | 0,00 | 1.700,00 | 0,00 | 61,45 | 77.188,47 |

*(tabla completa de 10 puntos en `resultados/tablas/07_pregunta_b_escenarios_agnellis.csv`;
gráfico en `resultados/graficos/02_utilidad_vs_k_paridad.png`)*

#### Hallazgo 1 — el efecto en la utilidad es chico

De paridad total (k=1) a soltar el 100 % a Agnellis (k=0), la utilidad sube
**+$609,88MM (+0,796 %)**. Es coherente con el precio sombra de R2 en el caso
base (−0,35875, §3.5): la paridad es barata de mantener porque Don Carlo (0,82 de
utilidad por $MM) y Agnellis (1,5375) no son tan distintos entre sí — la brecha
de rendimiento del par gama baja es la más chica de las cinco marcas.

**R5 (tope 65 % de la gama baja) no se activa en ningún punto del barrido**, ni
siquiera en k=0. El freno nunca es el mercado (sobran >1,7 millones de clientes
de cupo en todos los casos): es que R3+R4 le dejan al par gama baja solo
$1.700MM para repartirse, muy por debajo de lo que el segmento podría absorber.

#### Hallazgo 2 — "presencia" significa dos cosas distintas, y solo una responde la pregunta

El enunciado pide *"evitar una pérdida significativa de su presencia"*. Según cómo
se mida esa presencia, la respuesta se da vuelta:

| Cómo se mide la presencia de Don Carlo | k=1,00 | k=0,00 | Cae |
|---|---:|---:|---:|
| Solo entre los clientes que capta la campaña | 44,44 % | 0,00 % | **44,44 pts** |
| Sobre el mercado real (base instalada + campaña) | 64,68 % | 61,45 % | **3,23 pts** |
| Participación en el segmento bajo | 36,58 % | 35,00 % | **1,58 pts** |

La razón es de escala: **Don Carlo arranca con 7.525.000 clientes y la campaña
entera mueve 340.000 — el 4,5 % de su base.** Medir la presencia solo sobre los
clientes nuevos equivale a evaluar a una marca líder mirando únicamente lo que
ganó este mes, e infla el efecto de la publicidad en un orden de magnitud.

La segunda métrica es la que responde lo que pregunta el enunciado, y su
conclusión es contundente: **aunque a Don Carlo no se le dé un solo peso, sigue
siendo la marca dominante de la gama baja.** Su posición la sostiene la base
instalada, no la campaña de este año.

El panel derecho del gráfico muestra las dos curvas juntas a propósito: la brecha
entre la línea punteada (se derrumba) y la sólida (casi plana) *es* la respuesta.

#### Respuesta a las dos preguntas del enunciado

1. **¿Cuánto necesita Don Carlo para no perder presencia significativa?**
   Medido sobre el mercado real, **no necesita nada**: en el peor escenario del
   barrido pierde 3,2 puntos de presencia relativa y 1,6 puntos de participación
   en su segmento. Si aun así se quiere sostener la presencia *dentro de la
   campaña*, esa métrica sigue la hipérbola `400k / (400k + 500)`, así que con
   `k ≈ 0,5–0,6` Don Carlo retiene 29–32 puntos (64–73 % de su presencia
   original de 44,44 %) a cambio de +$152 a +$203MM de utilidad.
2. **¿Qué efecto tiene en la utilidad total?** Positivo pero marginal: relajar
   completamente la paridad vale menos de **1 punto porcentual** de utilidad.
   Es decir, **ni mantener la paridad ni romperla mueve la aguja**. La decisión
   no es económica: con estos números se puede relajar la paridad para acompañar
   a Agnellis sin poner en riesgo real a Don Carlo, o mantenerla por prolijidad
   comercial. El modelo no da un argumento fuerte en ninguna dirección, y decirlo
   es más honesto que fabricar una recomendación.

#### Correcciones aplicadas sobre la primera versión de esta respuesta

**(a) La presencia no es lineal en k.** La primera versión afirmaba que *"la
relación es prácticamente lineal (`presencia_DC ≈ 44,44 % · k`)"*. No lo es: la
forma cerrada es

```
presencia_campaña(k) = r_DC · k / (r_DC · k + r_AG) = 400k / (400k + 500)
```

una hipérbola. En k=0,5 la fórmula lineal predice 22,22 % contra un valor real de
28,57 % — un error del 29 %. El código siempre estuvo bien; el error estaba en la
lectura. Se agregó al script un control cruzado que compara cada punto del barrido
contra la forma cerrada (error máximo actual: 7,2e-07).

El error iba **a favor** de la conclusión: la curva es cóncava, así que Don Carlo
retiene presencia *mejor* de lo que sugería la fórmula lineal.

**(b) Faltaba la base instalada.** La primera versión medía la presencia solo
sobre los clientes captados por la campaña, lo que exageraba la caída de 3,2 a
44,4 puntos y llevaba a la recomendación opuesta ("defender la paridad"). Se
agregó `reportes.clientes_base()` y las dos métricas nuevas a la tabla y al
gráfico.

**Por qué pasó:** el modelo razona en *incrementos* — todo lo que optimiza son
clientes nuevos y facturación incremental — así que es natural que al reportar se
arrastre esa lógica incremental a una pregunta que en realidad es sobre *niveles*.
Es un recordatorio para las preguntas c) y d): **antes de responder, chequear si
la pregunta es sobre el cambio o sobre el total.**

### 5.2. Pregunta c) — Market share vs. rentabilidad [RESUELTO]

Corrida: `python scripts/03_pregunta_c.py` · 40 corridas del barrido, todas
**Optimal**, y 15 controles cruzados en verde.

**El giro respecto del plan.** El plan §12.c daba por sentado que había una curva
que trazar: aplicar ε-constraint (`Max utilidad s.a. facturación ≥ ε`), barrer ε y
graficar. Pero el punto a) ya había mostrado que **con las reglas vigentes los tres
objetivos dan el mismo plan** (§3.6): la frontera de Pareto colapsa en un punto y
el barrido no tiene nada que barrer.

Eso no invalida la pregunta, la reformula. Si el directorio quiere entender su
margen entre rentabilidad y participación, primero tiene que saber que **hoy no
tiene margen ninguno**, y después ver cuánto aparecería si aflojara sus propias
reglas. Por eso el barrido se corre en **cuatro escenarios**:

| Escenario | Qué se desactiva |
|---|---|
| Reglas actuales | nada (el caso real) |
| Sin R3 | el piso del 30 % para Triguetti |
| Sin R4 | la obligación de darle a Rena el doble de Candealix + Triguetti |
| Sin R3 ni R4 | las dos |

#### Resultado

| Escenario | Share mín. | Share máx. | Puntos en juego | Utilidad máx. | Utilidad en share máx. | Costo medio por punto |
|---|---:|---:|---:|---:|---:|---:|
| **Reglas actuales** | 61,91 % | 61,91 % | **0,00** | 76.578,60 | 76.578,60 | — |
| Sin R3 | 65,56 % | 65,92 % | 0,36 | 80.100,96 | 79.817,31 | $796MM |
| Sin R4 | 63,92 % | 65,10 % | **1,18** | 79.296,92 | 78.251,11 | $883MM |
| Sin R3 ni R4 | 65,52 % | 66,22 % | 0,70 | 80.253,43 | 79.882,02 | $529MM |

*(40 puntos de frontera en `resultados/tablas/08_pregunta_c_frontera_pareto.csv`,
resumen en `09_pregunta_c_resumen_tradeoff.csv`, gráfico en
`resultados/graficos/03_frontera_pareto.png`)*

Referencia útil para leer la tabla: el mercado total de pastas es de $1.657.100MM,
así que **1 punto de market share = $16.571MM de facturación**.

#### Hallazgo 1 — hoy no hay trade-off que negociar

Con las reglas vigentes la frontera es un punto: 61,91 % de share y $76.578,60MM
de utilidad. Accionistas y gerentes quieren cosas distintas, pero **el plan óptimo
es el mismo para los dos**, porque R3 y R4 ya consumen $15.300 de los $17.000 y no
dejan margen de decisión (§7.2 del plan).

La discusión del directorio, tal como está planteada, no tiene objeto. No es que
haya que elegir entre rentabilidad y participación: es que **con estas reglas no
hay nada que elegir**.

#### Hallazgo 2 — el plan vigente está *dominado*, no es una elección conservadora

Esto es lo más fuerte del punto c) y se ve de un vistazo en el gráfico: el punto
del plan vigente queda **abajo y a la izquierda de las tres curvas**. Todos los
escenarios relajados le ganan **en los dos criterios a la vez**:

```
Reglas actuales  ->  61,91 % de share  y  $76.579MM de utilidad
Sin R3 ni R4     ->  65,52 % de share  y  $80.253MM de utilidad
                     (+3,6 puntos            +$3.675MM)
```

No hay ningún sentido en el que el plan actual sea "la opción prudente": es
sencillamente peor. Las reglas del directorio no están comprando rentabilidad a
cambio de participación ni al revés — **están dejando las dos cosas sobre la mesa**.

#### Hallazgo 3 — el precio del share no es constante: la curva "Sin R4" se quiebra

El precio sombra del piso de facturación (columna
`Costo marginal por punto de share ($MM)`) dice cuánto cuesta el punto siguiente,
no el promedio. En dos escenarios es constante, pero en **Sin R4** salta:

| Tramo | Share | Costo marginal por punto |
|---|---|---:|
| Primero | 63,92 % → 64,90 % | **$529MM** |
| Último | 65,00 % → 65,10 % | **$3.365MM** |

Un salto de **6,4 veces**. Es el "quiebre" que el plan §12.c pedía identificar, y
tiene una lectura clara: los primeros puntos de participación se compran barato
reasignando plata entre marcas, pero los últimos exigen empujar a Rena Speziale
contra el techo del segmento alto, que ya está saturado (§3.4). Ahí cada peso
adicional compra cada vez menos clientes y la utilidad se desploma.

#### Respuesta a la pregunta del enunciado

> *"Le han pedido un informe para poder entender cuál es la posibilidad de
> crecimiento de market share de la empresa contra el crecimiento en rentabilidad."*

1. **Con las reglas actuales, la posibilidad de crecimiento es cero en ambas
   dimensiones simultáneamente**: el plan está fijado por R3 y R4, no por la
   optimización.
2. **El conflicto entre accionistas y gerentes es aparente.** No hay que elegir un
   objetivo: hay que revisar las reglas. Levantando R3 y R4 la empresa gana
   **+3,6 puntos de participación y +$3.675MM de utilidad al mismo tiempo**.
3. **Recién después de eso aparece un trade-off real**, y es chico: como máximo
   **1,18 puntos de participación negociables** (escenario Sin R4), a un costo que
   arranca en $529MM por punto y trepa a $3.365MM en el último tramo.
4. En términos de negocio: **la pelea vale mucho menos de lo que el directorio
   cree.** Todo el margen de discusión entre las dos posturas cabe en poco más de
   un punto de participación, mientras que la plata que dejan sobre la mesa por no
   revisar sus propias reglas es tres veces más grande.

#### Detalles de implementación

- **Margen numérico en el último ε.** Pedir exactamente la facturación máxima
  devuelve `Infeasible`: el óptimo la alcanza, pero la tolerancia de factibilidad
  de CBC deja el piso unas millonésimas por encima de lo alcanzable. Medido sobre
  este modelo, con 1e-3 $MM de margen todavía falla y con 1e-2 resuelve. Se usa un
  margen **relativo** (1e-7 del valor, ~0,11 $MM) para que el borde siga
  funcionando si cambian las magnitudes. Es el mismo tipo de problema que la
  tolerancia de los controles cruzados (§2.5).
- **El dual como unidad de negocio.** El precio sombra de `EPS_facturacion` viene
  en $MM de utilidad por $MM de facturación, que no le dice nada a nadie. Se lo
  multiplica por $16.571MM (un punto de share) para reportarlo como "cuánto cuesta
  un punto de participación".
- **El primer punto de cada frontera se excluye del costo marginal**: ahí el piso
  de facturación todavía no ata y el dual es 0 por construcción, no porque el share
  sea gratis.

### 5.3. Pregunta d) — El 30 % obligatorio en Triguetti [RESUELTO]

Corrida: `python scripts/04_pregunta_d.py` · 5 controles cruzados en verde.
Salidas: `resultados/tablas/10_pregunta_d_triguetti.csv`,
`resultados/tablas/11_pregunta_d_test_s1.csv` y
`resultados/graficos/04_utilidad_vs_pct_triguetti.png`.

**Descomposición del precio sombra de R3 (−2,49225 $/$MM).** Se separó a mano
en efecto directo (ganar Triguetti, perder 1 $MM del par gama baja: −0,135) y
efecto arrastre (R4 obliga a poner 2 $MM más en Rena, ya saturada: −2,358). El
**95 % del costo sale del arrastre, no de Triguetti**: su primer tramo (1,044)
casi empata con el par gama baja (1,179).

**Barrido del piso mínimo** (0 %, 10 %, 20 %, 30 % —base—, 40 %):

| Piso | Triguetti | Rena | Estéril | Utilidad neta |
|---:|---:|---:|---:|---:|
| 0 % | 0 | 8.570 | 0 | 80.100,96 |
| 10 % | 1.700 | 8.570 | 0 | 79.509,36 |
| 20 % | 3.400 | 8.570 | 0 | 78.917,76 |
| 30 % (base) | 5.100 | 10.200 | 1.630 | 76.578,60 |
| 40 % | — | — | — | **Infeasible** |

**Hallazgo no previsto en el plan:** el 40 % da directamente infactible, y no
por casualidad. Con Candealix en su mínimo, R3+R4 exigen
`Triguetti + Rena >= 3 x Triguetti >= 3 x (piso x $17.000)`, así que el piso no
puede superar **1/3 = 33,33 %** sin que las dos reglas del directorio se
contradigan entre sí — se puede deducir sin correr el solver. La regla vigente
del 30 % está a apenas 3,3 puntos de ese límite.

**Test de robustez (S1, 140–260 cl/$MM):** el costo de la regla se mueve entre
$1.925MM y $5.120MM en todo el rango — la conclusión no depende del dato que
el enunciado no da.

**Respuesta:** el gerente tiene razón en el número (la regla cuesta ~$3.522MM/año,
+4,6 % de utilidad si se elimina, más $1.630MM de inversión estéril) pero el
diagnóstico apunta mal: la culpa es de R4 (el arrastre a Rena), no de Triguetti.
Y el modelo solo mide un año — lo que la regla protege (identidad de marca,
presencia en góndola, poder de negociación) no está en el funcional.

---

## 6. Verificaciones realizadas

### 6.1. Datos derivados — `00_verificar_datos.py`

**31 de 31 verificaciones OK.** Cubre: mercado por segmento y total, facturación base de las
cinco marcas y total, market share inicial, cupo de la gama baja, los 8 coeficientes de
facturación por $MM, los 8 coeficientes de utilidad neta, y los tres términos constantes.

### 6.2. Cotas deducidas a mano — `01_modelo_base.py` §1

7 de 7 OK: presupuesto agotado, R2/R3/R4 satisfechas, Triguetti+Rena ≥ 15.300,
resto ≤ 1.700, y `Z > término constante`.

### 6.3. Precios sombra contra cálculo manual

Los cinco duales no nulos se derivaron a mano y coinciden **a cinco decimales**:

| Dual | Modelo | Cálculo manual | Razonamiento |
|---|---:|---:|---|
| R1 | +1,17875 | +1,17875 | `0,5 × (0,82 + 1,5375)` — el peso extra va al par gama baja |
| R3 | −2,49225 | −2,49225 | `1,044 − 1,5 × (0,82 + 1,5375)` — gana Triguetti, pierde el par |
| R4 | −1,17875 | −1,17875 | `−0,5 × (0,82 + 1,5375)` — el $MM extra en Rena es estéril |
| R2 | −0,35875 | −0,35875 | `(0,82 − 1,5375) / 2` |
| R10 alto | +0,01340 | +0,01340 | `1,34 / 100` — un cliente más de cupo a 100 cl/$MM |

Es la verificación más fuerte que se hizo: que los duales se puedan reconstruir con
aritmética de servilleta confirma que el modelo dice lo que creemos que dice.

### 6.4. Barrido de la pregunta b) — `02_pregunta_b.py`

6 de 6 controles OK. El más importante compara cada punto del barrido contra la
**forma cerrada** de la presencia dentro de la campaña:

```
presencia(k) = 400k / (400k + 500)        error máximo: 7,2e-07
```

Los otros cinco: k=1 reproduce el caso base ($76.578,60), la utilidad es monótona
al bajar k, Don Carlo + Agnellis suman siempre $1.700MM, la ganancia de k=1 a k=0
es +$609,88MM (verificada a mano: `1.700 × 1,5375 − 850 × (0,82 + 1,5375)`), y la
presencia real se mueve menos de 5 puntos en todo el barrido.

El control de la forma cerrada se agregó **después** de haber documentado esa
relación como lineal (§5.1, corrección (a)). Es el patrón que ya apareció con R6 y
con los duales: cuando una afirmación del informe se puede escribir como una
fórmula, conviene que el script la chequee en vez de confiar en la lectura de la
tabla.

### 6.5. Fronteras de la pregunta c) — `03_pregunta_c.py`

15 de 15 controles OK. Tres son propiedades que **toda** frontera de Pareto tiene
que cumplir, y se chequean por escenario:

- la utilidad nunca sube al exigir más facturación (si subiera, el punto anterior
  no era eficiente);
- la facturación sí crece a lo largo del barrido;
- el dual del piso de facturación es <= 0 (exigir más ventas nunca puede *mejorar*
  la utilidad).

El cuarto es el más fuerte: **los dos extremos de cada barrido tienen que coincidir
con los óptimos obtenidos por separado**, resolviendo `Max utilidad` y
`Max facturación` sin ε-constraint. Si no coincidieran, el piso de facturación
estaría mal construido y toda la frontera sería ficción. Coinciden en los cuatro
escenarios.

### 6.6. R6 — umbral de Candealix

**Confirmada la hipótesis del plan §7.3: la restricción NO está activa.** Candealix vende
**43.666.667 paquetes** con inversión cero (solo su facturación base), contra un umbral de
2.500.000 → **17,5 veces** el mínimo. No hace falta el tratamiento por escenarios del plan §8:
el LP puro alcanza.

---

## 7. Conclusiones para el informe

1. **El plan óptimo es**: Don Carlo $850MM, Agnellis $850MM, Triguetti $5.100MM,
   Candealix $0, Rena Speziale $10.200MM. Utilidad neta $76.578,60MM, market share 61,91 %.
2. **Candealix queda fuera del plan** pese a ser rentable por sí sola (1,392 de utilidad por
   $MM): la mata R4, porque cada peso que recibe obliga a poner dos en Rena, que ya está
   saturada. Su costo efectivo es 0,464 por $MM, menos de la mitad que el par gama baja.
3. **$1.630MM (9,59 % del presupuesto) se invierten sin captar un solo cliente**, forzados por
   la combinación de R3 y R4.
4. **Las reglas del directorio, no la optimización, determinan el plan.** Cuatro de las once
   restricciones están activas y entre ellas consumen $15.300 de los $17.000.
5. **No hay conflicto entre accionistas y directivos bajo las reglas actuales**: los tres
   objetivos dan el mismo plan. El conflicto es real solo si se relajan las reglas.
6. **El modelo, tal como lo especificaba el enunciado, permitía captar más clientes de los que
   existen.** Hubo que agregar R10. Vale la pena contarlo en el informe: encontrar un
   resultado imposible y rastrear su causa es parte del criterio "Analizar".
