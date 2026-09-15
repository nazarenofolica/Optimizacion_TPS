# TP1 Optimización — "Portafolio de Productos Pastarazzi"
## Plan de trabajo (esquema)

> **Qué es este archivo.** Es el **plan / esquema** del trabajo: qué pide la consigna, qué hay que
> modelar, con qué datos, qué supuestos se adoptan y cómo se van a testear. **No es la bitácora de
> desarrollo.** Cuando escribamos el código, lo que efectivamente se haga (y lo que cambie
> respecto de este plan) va en un segundo archivo, `procedimiento.md` — ver §14.
>
> **Alcance:** este documento cubre **el TP completo (preguntas a, b, c y d)**, no solamente el
> punto a). En §4.6 hay una tabla que mapea cada supuesto contra la pregunta que lo necesita.
>
> **Estado:** modelo planteado y parametrizado. Todavía no resuelto.

---

## 0. Primero, una aclaración sobre la consigna

El PDF de la consigna **no tiene puntos "1, 2, 3, 4"**. Tiene **dos listas distintas, ambas
numeradas a) b) c) d)**, y confundirlas es el error más fácil de cometer:

| | Dónde está | Qué es |
|---|---|---|
| **Lista 1 — "Informe esperable por la cátedra"** | Página 1 | **Cómo hay que presentar** el trabajo (la estructura del informe) |
| **Lista 2 — Preguntas del caso** | Página 4 | **Qué hay que responder** (las consultas del directorio) |

**Lista 1 — estructura del informe:**
- **a)** Modelo de programación lineal → i) supuestos, ii) variables, iii) función objetivo,
  iv) parámetros, v) restricciones, vi) resolución del modelo
- **b)** Análisis de sensibilidad → i) rangos de nivel de actividad, ii) rangos de soluciones posibles
- **c)** Representación gráfica del proceso
- **d)** Librerías utilizadas

**Lista 2 — preguntas a responder:**
- **a)** Determinar el plan de asignación de presupuesto que equilibre captación de clientes y
  rentabilidad; justificar el mix, la composición de la facturación, la rentabilidad global y la
  distribución por canales.
- **b)** Escenarios en que Agnellis aumente su participación: ¿cómo debería cambiar la inversión
  en Don Carlo para que no pierda presencia, y qué efecto tiene en la utilidad total?
- **c)** Informe sobre la posibilidad de crecimiento de **market share** contra el crecimiento en
  **rentabilidad**.
- **d)** Un gerente dice que invertir al menos 30 % del presupuesto en Triguetti es un error.
  ¿Qué opinás?

Los **criterios de evaluación** (página 1) condicionan qué se espera del trabajo:

- **Modelar** → formalizar el modelo matemático.
- **Analizar** → comparación crítica de los distintos resultados (no alcanza con una corrida).
- **Explorar** → *búsqueda de nuevos modelos y datos no provistos* ← **la consigna deja huecos a
  propósito** y espera que los completemos con criterio explícito.
- **Informar** → presentación, estilo, claridad, bibliografía.

---

## 1. El problema, en palabras

Pastarazzi vende **pastas secas en paquetes de 500 g** con cinco marcas: Don Carlo, Agnellis,
Triguetti, Candealix y Rena Speziale. Va a lanzar su campaña anual y tiene que decidir **cómo
repartir $17.000 millones de presupuesto de marketing** entre esas cinco marcas.

No hay presupuesto para productos nuevos: **la única palanca es cómo se reparte esa plata.**

Y hay un conflicto político explícito en el directorio:

- **Los accionistas** vienen de trimestres flojos y quieren **rentabilidad inmediata**.
- **El equipo directivo** quiere una ofensiva comercial sostenida, y —dato importante— **sus bonos
  dependen de los ingresos totales**, no de la ganancia.

Ese conflicto no es color narrativo: **es el problema matemático**. Maximizar utilidad y maximizar
facturación son dos funciones objetivo distintas que dan planes distintos. Esto convierte al TP en
un **problema bicriterio**, y es exactamente lo que la pregunta **c)** pide analizar.

---

## 2. Qué se decide, qué se sabe, qué se busca

**Lo que se decide (variables):** cuántos millones de pesos poner en marketing de cada marca.

**La cadena causal del modelo** — esta es la columna vertebral de todo el planteo:

```
   inversión           tasa de              gasto anual         precio
   en marketing   ──►  captación      ──►   por persona   ──►   unitario
   ($ millones)        (clientes/MM)        del segmento        del producto
        │                    │                    │                  │
        ▼                    ▼                    ▼                  ▼
      x_j            clientes nuevos N_j    facturación F_j     unidades Q_j
                                                  │
                                                  ▼
                                          margen_j · F_j = utilidad U_j
```

En criollo: **la plata de marketing compra clientes, los clientes gastan plata en pastas, esa
plata es facturación, y la facturación por el margen es utilidad.**

**Lo que se busca:** el reparto `x_j` que optimice… ¿qué? Ahí está el conflicto del punto 1, y por
eso §6 es la sección más importante del documento.

---

## 3. Los datos, ordenados

Siguiendo el estilo "Organización de los datos" de la Clase 2.

### 3.1. Precios y márgenes (Fig. 1 de la consigna)

| Producto | Precio ($/paquete) | Margen operativo | Margen neto |
|---|---:|---:|---:|
| Don Carlo | 700 | 9,0 % | 5,0 % |
| Agnellis | 850 | 10,0 % | 7,5 % |
| Triguetti | 1.200 | 11,2 % | 9,0 % |
| Candealix | 1.800 | 11,1 % | 8,0 % |
| Rena Speziale | 3.500 | 16,0 % | 10,0 % |

### 3.2. Market share inicial por segmento (Fig. 2)

| Producto | Bajo | Medio | Alto |
|---|---:|---:|---:|
| Don Carlo | 35 % | 2 % | — |
| Agnellis | 18 % | 5 % | 2 % |
| Triguetti | — | 30 % | 1 % |
| Candealix | — | 12 % | 3 % |
| Rena Speziale | — | 1 % | 8 % |

### 3.3. Mercado (Fig. 3)

| Segmento | TAM (personas) | Gasto en pastas ($/persona-año) |
|---|---:|---:|
| Bajo | 21.500.000 | 41.000 |
| Medio | 10.600.000 | 58.000 |
| Alto | 1.200.000 | 134.000 |

### 3.4. **Tabla derivada 1 — tamaño de cada mercado en pesos**

`TAM × gasto por persona`:

| Segmento | Mercado ($ millones/año) |
|---|---:|
| Bajo | 881.500 |
| Medio | 614.800 |
| Alto | 160.800 |
| **Mercado total de pastas** | **1.657.100** |

### 3.5. **Tabla derivada 2 — facturación base de cada marca**

`Σ_segmento (share × mercado del segmento)`. Es de dónde parte la empresa **antes de invertir un
solo peso**: el marketing agrega ventas *sobre* esta base.

| Producto | Facturación base ($MM/año) | % de la facturación total |
|---|---:|---:|
| Don Carlo | 320.821 | 40,2 % |
| Agnellis | 192.626 | 24,2 % |
| Triguetti | 186.048 | 23,3 % |
| Candealix | 78.600 | 9,9 % |
| Rena Speziale | 19.012 | 2,4 % |
| **Total** | **797.107** | 100 % |

*Market share global de Pastarazzi: 797.107 / 1.657.100 = **48,10 %** del mercado de pastas.*

### 3.6. **Tabla derivada 3 — eficiencia de captación por tramo**

| Marca | Tramo | Tasa (clientes nuevos / $MM) | Fuente |
|---|---|---:|---|
| Don Carlo | sin caída de eficiencia | 400 | enunciado |
| Agnellis | sin caída de eficiencia | 500 | enunciado |
| Triguetti | 0 → 6.000 | **200** | **supuesto S1** (§4.1) |
| Triguetti | > 6.000 | 0 | enunciado |
| Candealix | 0 → 5.000 | 300 | enunciado |
| Candealix | > 5.000 | 200 | enunciado |
| Rena Speziale | 0 → 3.500 | 150 | enunciado |
| Rena Speziale | > 3.500 | 100 | enunciado |

### 3.7. **Tabla derivada 4 — rendimiento económico de cada peso invertido**

`facturación por $MM invertido = tasa de captación × gasto anual del segmento`

| Marca (tramo) | Facturación por $MM | Utilidad **neta** por $MM | Utilidad **operativa** por $MM |
|---|---:|---:|---:|
| Rena Speziale (1º) | 20,10 | **2,010** | 3,216 |
| Agnellis | 20,50 | **1,538** | 2,050 |
| Candealix (1º) | 17,40 | **1,392** | 1,931 |
| Rena Speziale (2º) | 13,40 | **1,340** | 2,144 |
| Triguetti (1º) | 11,60 | **1,044** | 1,299 |
| Candealix (2º) | 11,60 | **0,928** | 1,288 |
| Don Carlo | 16,40 | **0,820** | 1,476 |
| Triguetti (2º) | 0 | **0** | 0 |

**Tres lecturas que ya se pueden hacer sin resolver nada:**

1. **Agnellis es el rey de la facturación** (20,50 por millón) pero **Rena Speziale es el rey de la
   utilidad** (2,01 por millón): capta poquísimos clientes, pero cada cliente del segmento alto
   gasta $134.000 al año y deja 10 % de margen neto. **Ahí está, en una sola tabla, el conflicto
   entre accionistas y dirección.**
2. **Don Carlo es el peor negocio marginal** en utilidad neta (0,82): capta bien pero con un margen
   de apenas 5 %. Y sin embargo el modelo lo obliga a recibir plata (restricción R2).
3. **El orden cambia según el margen que se use.** Con margen operativo, Don Carlo (1,476) le pasa
   a Triguetti (1,299) y a Candealix 2º tramo (1,288). Es decir: **elegir margen neto u operativo
   no es inocuo, cambia el ranking**. Por eso §6 lo trata como una decisión explícita.

---

## 4. Registro de supuestos

Esta sección corresponde al ítem **a.i)** del informe y al criterio **"Explorar"**.

**La regla que seguimos:** se pueden adoptar todos los supuestos que hagan falta, **siempre que
cada uno responda a tres preguntas**:

1. **¿Para qué lo necesito?** (qué cálculo es imposible sin él)
2. **¿Por qué ese valor y no otro?** (justificación anclada en el enunciado o en la lógica de negocio)
3. **¿Cómo sé si importa?** (cómo se testea y en qué rango)

Todos los valores adoptados acá son **parámetros del modelo, no constantes del código**: van en un
diccionario de configuración para poder barrerlos sin tocar la formulación (§13).

> **Los valores propuestos son puntos de partida defendibles, no verdades.** Todos están sujetos a
> cambio si el test empírico de §11 muestra que el resultado es sensible a ellos, o si el profesor
> indica otro criterio.

### 4.1. Supuestos numéricos (se testean con barridos ±30 %)

#### **S1 — Tasa de captación de Triguetti, primer tramo = 200 clientes / $MM**

- **Para qué lo necesito:** sin este número **no se puede calcular nada de Triguetti** — ni sus
  clientes captados, ni su facturación incremental, ni su coeficiente en la función objetivo. Y
  Triguetti es obligatorio por R3, así que el modelo no corre sin él.
- **Por qué falta:** el enunciado da el **punto de saturación** de Triguetti (*"tras un refuerzo de
  aproximadamente $6.000 millones no se producen incrementos relevantes"*) pero **nunca da la tasa
  antes de saturar**. Es el único parámetro estructural ausente.
- **Por qué 200:** Triguetti compite en el **mismo segmento (medio) que Candealix**, que capta 300
  clientes/$MM en su primer tramo. El enunciado dice que Triguetti tiene *"menor elasticidad a la
  inversión"* → su tasa debe ser **menor que 300**. Pero no puede ser 0, porque entonces no tendría
  sentido hablar de un punto de saturación a los $6.000MM. **200 es el valor intermedio
  conservador**: dos tercios de la eficiencia de su competidor directo de segmento.
- **Rango de test:** **140 – 260** (±30 %). Cota superior dura: 300 (no puede superar a Candealix
  sin contradecir el enunciado).
- **Qué esperamos:** que **no cambie el plan óptimo**, porque R3 obliga a invertir en Triguetti
  independientemente de su rendimiento. Si se confirma, es un resultado fuerte: *la conclusión no
  depende del dato que falta*.

#### **S2 — Tasa de captura de billetera = 100 %**

- **Para qué lo necesito:** para convertir "clientes captados" en "pesos facturados". Sin esto la
  cadena `clientes → facturación` se corta.
- **Supuesto:** un cliente nuevo destina **todo** su gasto anual en pastas ($41.000 / $58.000 /
  $134.000 según segmento) a la marca que lo captó.
- **Por qué es discutible:** en la realidad un consumidor reparte entre marcas. Este supuesto
  **sobreestima la facturación incremental**, y por lo tanto todo el retorno del marketing.
- **Rango de test:** **70 % – 100 %** (asimétrico: no puede superar el 100 %).
- **Qué esperamos:** que escale toda la facturación incremental proporcionalmente. Como afecta a
  **todas las marcas por igual**, el mix óptimo no debería cambiar; sí cambia el nivel de Z y, con
  él, el precio sombra del presupuesto (R1). **Importa para la pregunta a) pero no para la d).**

#### **S3 — Los márgenes de la Fig. 1 son exactos**

- **Para qué lo necesito:** son los coeficientes de la función objetivo de utilidad.
- **Por qué es discutible:** el enunciado dice textualmente *"un **estimado** de los márgenes"*.
- **Rango de test:** ±30 % sobre cada margen, **de a uno por vez** (los coeficientes del funcional
  son justamente lo que el ítem **b.ii) "rangos de soluciones posibles"** pide analizar).
- **Qué esperamos:** que exista un umbral en el margen de Rena Speziale a partir del cual deja de
  convenir. Ese umbral es un resultado interesante para reportar.

#### **S4 — Las tasas de captación del enunciado son exactas**

- **Por qué es discutible:** el enunciado usa lenguaje deliberadamente vago en **todas**:
  *"alrededor de 500"*, *"cerca de 400"*, *"una captación media de 300"*, *"unos 150"*,
  *"aproximadamente $6.000 millones"*, *"aproximadamente el 65 %"*.
- **Rango de test:** ±30 % sobre cada tasa y sobre cada umbral de tramo, de a uno por vez.
- **Qué esperamos:** identificar cuál de todos los parámetros es el que más mueve la aguja. Eso se
  ve de una en el gráfico tornado de §11.

### 4.2. Supuestos estructurales (se testean con escenarios discretos, no con ±30 %)

Estos no tienen un valor numérico que se pueda barrer: son **decisiones de interpretación**. Se
testean resolviendo el modelo con cada lectura alternativa y comparando.

#### **S5 — Cada marca capta clientes en su segmento de posicionamiento**

- **Para qué lo necesito:** la Fig. 2 dice que cada marca vende en **varios** segmentos, pero las
  tasas de captación son **un solo número por marca**. Sin decidir a qué segmento pertenece el
  cliente captado, no sé si gasta $41.000 o $134.000 al año. **Es el supuesto que más cambia los
  números de todo el modelo.**
- **Decisión (Opción A):**

  | Marca | Segmento de captación | Frase que lo sostiene |
  |---|---|---|
  | Don Carlo | Bajo | *"el segmento de gama baja está dominado por Don Carlo"* |
  | Agnellis | Bajo | *"apunta a un público similar"* |
  | Triguetti | Medio | *"Triguetti, en la gama media"* |
  | Candealix | Medio | *"también de gama media"* |
  | Rena Speziale | Alto | *"en la gama alta, Rena Speziale"* |

- **Confirmación adicional:** el propio enunciado mide el tope de Don Carlo + Agnellis contra *"el
  mercado de menor poder adquisitivo"*, o sea el segmento bajo. Coherente con la Opción A.
- **Alternativa a testear (Opción B):** repartir los clientes captados según el mix normalizado de
  la Fig. 2 (p. ej. Agnellis: 18/25 al bajo, 5/25 al medio, 2/25 al alto). Es más fina pero no está
  sostenida por ningún dato.
- **Test:** correr el modelo completo bajo A y bajo B y comparar mix óptimo y Z. **Es el escenario
  estructural más importante del trabajo.**

#### **S6 — R2 se interpreta como igualdad de inversión: `x_DC = x_AG`**

- **Para qué lo necesito:** la frase *"el otro debe recibir un refuerzo de igual magnitud de
  inversión"* admite al menos dos lecturas.
- **Lecturas posibles:** (i) las inversiones totales son iguales → `x_DC = x_AG`; (ii) solo los
  *incrementos* respecto de una campaña anterior son iguales → no computable, porque el enunciado
  no da la inversión histórica.
- **Decisión:** lectura (i), que es la única formulable con los datos disponibles.
- **Test:** **es exactamente lo que pide la pregunta b)** — relajar R2 y ver qué pasa. Ver §12.b.

#### **S7 — R4 se interpreta como `≥` y R3 sobre el presupuesto total**

- **R4:** *"las inversiones sean el doble que Candealix y Triguetti combinados"* →
  `x_RS ≥ 2·(x_CAN + x_TRI)`. Se usa `≥` en lugar de `=` porque *"el doble"* es un piso exigido por
  la dirección, no una cuota exacta. **Alternativa a testear:** con `=`, que reduce el espacio
  factible.
- **R3:** *"su peso en el presupuesto debe superar siempre el 30 %"* → `x_TRI ≥ 0,30 × 17.000`.
  **Alternativa a testear:** `x_TRI ≥ 0,30 × Σx_j` (30 % de lo efectivamente asignado). Solo
  difieren si el presupuesto no se agota; hay que verificar si se agota.

#### **S8 — El presupuesto es un recurso a asignar, no un costo del funcional**

- **Para qué lo necesito:** para decidir si los $17.000MM se restan de la utilidad o no.
- **El problema:** si el margen operativo ya contempla el gasto comercial, restar además la
  inversión sería **doble conteo**.
- **Decisión:** tratar el presupuesto como recurso fijo a asignar (como las "horas disponibles" del
  caso Coaching de la Clase 2), **no** como término negativo del funcional. Como el monto total es
  el mismo en todos los planes, **no altera la comparación entre planes** ni el óptimo.
- **Consecuencia a declarar:** el Z reportado es una utilidad **antes** de descontar la campaña. Si
  se quisiera el número "limpio", se le restan $17.000MM a todos los escenarios por igual.

#### **S9 — Supuestos de menor impacto**

- **La facturación base no se pierde:** la campaña agrega ventas sobre la base de la Fig. 2, no la
  reemplaza. (Sin esto no habría término constante en el funcional.)
- **"Canales de venta"** —que pide la pregunta a)— **no está definido en ningún dato**. Se usa el
  **segmento de mercado (bajo / medio / alto)** como proxy de canal, declarándolo.
- **Horizonte de un año**, datos anualizados, sin estacionalidad.
- Los cinco supuestos generales de PL de la Clase 2 — **proporcionalidad, aditividad,
  divisibilidad, certidumbre, no negatividad**. Dos salvedades honestas: la **divisibilidad** se
  rompe en el umbral de Candealix (§8) y la **proporcionalidad** se rompe a propósito con los
  rendimientos decrecientes, que es lo que se resuelve con tramos (§5.2).

### 4.3. Tabla resumen de supuestos

| ID | Supuesto | Valor base | Rango de test | Tipo de test |
|---|---|---|---|---|
| **S1** | Tasa Triguetti 1º tramo | 200 cl/$MM | 140 – 260 | barrido ±30 % |
| **S2** | Tasa de captura de billetera | 100 % | 70 – 100 % | barrido asimétrico |
| **S3** | Márgenes Fig. 1 | tabla §3.1 | ±30 % c/u | barrido OAT |
| **S4** | Tasas de captación y umbrales | tabla §3.6 | ±30 % c/u | barrido OAT |
| **S5** | Segmento de captación | Opción A | A vs. B | escenario estructural |
| **S6** | Lectura de R2 | `x_DC = x_AG` | igualdad vs. relajada | escenario (= pregunta b) |
| **S7** | Lectura de R3 y R4 | `≥`, sobre 17.000 | `=`, sobre Σx | escenario estructural |
| **S8** | Presupuesto fuera del funcional | sí | con/sin descuento | verificación |
| **S9** | Base se mantiene, canal ≈ segmento, 1 año | — | — | se declara |

### 4.4. ¿Estos supuestos alcanzan para todo el TP, o solo para el punto a)?

**Alcanzan para el TP completo.** Esta tabla lo muestra explícitamente:

| Supuesto | Pregunta a) | Pregunta b) | Pregunta c) | Pregunta d) |
|---|:---:|:---:|:---:|:---:|
| S1 — tasa Triguetti | ● | ○ | ● | **●●** |
| S2 — captura de billetera | **●●** | ● | ● | ○ |
| S3 — márgenes | ● | ● | **●●** | ● |
| S4 — tasas de captación | ● | **●●** | ● | ● |
| S5 — segmento de captación | **●●** | **●●** | **●●** | ● |
| S6 — lectura de R2 | ● | **●●** | ○ | ○ |
| S7 — lectura de R3/R4 | ● | ○ | ● | **●●** |
| S8 — presupuesto en el funcional | ● | ○ | ● | ○ |

`●●` crítico · `●` relevante · `○` indiferente

**Lectura:** no hay ningún supuesto que sirva solo para el punto a). Los que más peso tienen son
**S5** (afecta las cuatro preguntas) y, para cada pregunta específica, **S6 para la b)** y **S7 +
S1 para la d)**.

**No hacen falta supuestos adicionales** para b), c) ni d): esas preguntas son **experimentos sobre
el mismo modelo** (relajar una restricción, barrer un parámetro, trazar una frontera), no modelos
nuevos.

---

## 5. Variables de decisión

### 5.1. Variables principales

`x_j` = inversión en marketing en la marca *j*, en **millones de pesos**.

```
x_DC   inversión en Don Carlo
x_AG   inversión en Agnellis
x_TRI  inversión en Triguetti
x_CAN  inversión en Candealix
x_RS   inversión en Rena Speziale
```

**Unidad elegida: millones de pesos.** No es un detalle menor: las tasas vienen dadas en "clientes
por millón invertido", así que trabajar en millones evita arrastrar factores de 10⁶ por todo el
modelo y hace las cuentas legibles.

### 5.2. Variables por tramo (rendimientos decrecientes)

```
x_TRI = x_TRI1 + x_TRI2       con  x_TRI1 ≤ 6.000   (200 cl/MM)  y  x_TRI2 → 0 cl/MM
x_CAN = x_CAN1 + x_CAN2       con  x_CAN1 ≤ 5.000   (300 cl/MM)  y  x_CAN2 → 200 cl/MM
x_RS  = x_RS1  + x_RS2        con  x_RS1  ≤ 3.500   (150 cl/MM)  y  x_RS2  → 100 cl/MM
```

> **¿Por qué esto NO necesita variables binarias?**
>
> Porque la curva de captación es **cóncava**: cada tramo rinde *menos* que el anterior
> (300 → 200, 150 → 100). Como estamos **maximizando**, el solver nunca va a poner plata en el
> tramo malo teniendo lugar en el bueno —sería tirar utilidad. El orden correcto (llenar primero el
> tramo eficiente) **sale solo**, sin obligarlo.
>
> Si las tasas fueran crecientes (economías de escala), la función sería convexa y **sí** harían
> falta binarias. Vale la pena decirlo en el informe: muestra que se entendió por qué funciona.

### 5.3. Variables derivadas (para reportar, no para decidir)

```
N_j = Σ_tramos (tasa_tramo × x_j,tramo)        clientes nuevos captados por la marca j
F_j = F_base_j + N_j × gasto_segmento(j) × β   facturación total de la marca j  [$MM]
U_j = margen_j × F_j                            utilidad de la marca j  [$MM]
Q_j = F_j × 10^6 / precio_j                     unidades vendidas (paquetes de 500 g)
```

donde `β` es la tasa de captura de billetera del supuesto **S2** (base: 1,0).

---

## 6. La función objetivo — el core del simulador

Esta es **la sección más importante del documento**. Todo lo demás (datos, restricciones) define el
espacio de lo posible; la función objetivo define **qué se persigue**, y en este TP no hay una
respuesta obvia.

### 6.1. La forma general

```
Max  Z = Σ_j  margen_j × F_j
       = Σ_j  margen_j × ( F_base_j  +  Σ_tramos tasa × x_j,tramo × gasto_seg(j) × β )
```

Al distribuir, el funcional se parte en **dos pedazos**:

```
Z  =  [ Σ_j margen_j × F_base_j ]   +   [ Σ_tramos c_tramo × x_tramo ]
      └──────── constante ────────┘     └──── lo que se optimiza ────┘
```

- **El término constante** es la utilidad que la empresa gana **aunque no invierta un peso**. No
  afecta al óptimo (es una constante), pero **sí hay que reportarlo**, porque sin él las cifras de
  utilidad total no tienen sentido de negocio.
- **El término variable** es lo único que el solver decide. Sus coeficientes `c_tramo` son
  exactamente la columna "utilidad por $MM" de la Tabla 3.7.

### 6.2. El funcional explícito — versión margen NETO

Este es literalmente el modelo que se va a codificar:

```
Max  Z_neta  =  55.421,52                        ← utilidad de la facturación base

              + 0,8200 · x_DC                    ← Don Carlo
              + 1,5375 · x_AG                    ← Agnellis
              + 1,0440 · x_TRI1  + 0 · x_TRI2    ← Triguetti (satura a los 6.000)
              + 1,3920 · x_CAN1  + 0,9280 · x_CAN2
              + 2,0100 · x_RS1   + 1,3400 · x_RS2
```

*(unidades: $MM de utilidad; las `x` en $MM invertidos)*

De dónde sale cada coeficiente, por ejemplo Agnellis:

```
500 clientes/$MM  ×  $41.000/cliente-año  ÷  10⁶  =  20,50 $MM de facturación por $MM invertido
20,50  ×  7,5 % de margen neto                     =  1,5375 $MM de utilidad por $MM invertido
```

### 6.3. El funcional explícito — versión margen OPERATIVO

```
Max  Z_oper  =  80.740,39

              + 1,4760 · x_DC
              + 2,0500 · x_AG
              + 1,2992 · x_TRI1  + 0 · x_TRI2
              + 1,9314 · x_CAN1  + 1,2876 · x_CAN2
              + 3,2160 · x_RS1   + 2,1440 · x_RS2
```

⚠ **Comparar 6.2 con 6.3: el ranking de marcas cambia.** Con margen neto, Don Carlo (0,82) es el
peor de todos; con margen operativo (1,476) supera a Triguetti y al segundo tramo de Candealix. **La
elección de margen no es un detalle contable, cambia el plan óptimo.** Por eso se corren las dos y
se comparan (es material directo para el criterio "Analizar").

### 6.4. El funcional explícito — versión FACTURACIÓN (market share)

La mirada del equipo directivo, cuyos bonos dependen de los ingresos:

```
Max  Z_fact  =  797.107                          ← facturación base

              + 16,40 · x_DC
              + 20,50 · x_AG
              + 11,60 · x_TRI1  + 0 · x_TRI2
              + 17,40 · x_CAN1  + 11,60 · x_CAN2
              + 20,10 · x_RS1   + 13,40 · x_RS2
```

Como el mercado total ($1.657.100MM) es una constante, **maximizar facturación es idéntico a
maximizar market share**: `share = Z_fact / 1.657.100`.

### 6.5. Cómo se resuelve la tensión entre 6.2 y 6.4 — método ε-constraint

No se promedian los objetivos ni se inventan pesos arbitrarios. Se hace lo correcto:

1. Maximizar utilidad **sujeto a un piso de facturación**:
   ```
   Max  Z_neta       s.a.   Z_fact ≥ ε      (además de R1…R9)
   ```
2. **Barrer ε** desde el mínimo hasta el máximo alcanzable, resolviendo en cada paso.
3. Cada solución es un punto de la **frontera de Pareto**: planes donde no se puede mejorar la
   utilidad sin resignar facturación.
4. Graficar la curva utilidad vs. market share.

**La pendiente de esa curva es la respuesta a la pregunta c)**: cuánta utilidad cuesta cada punto
adicional de participación. Y matemáticamente esa pendiente **es el precio sombra de la restricción
`Z_fact ≥ ε`**, así que sale del propio solver sin cuentas extra.

### 6.6. Por qué esto es "el simulador"

Fijadas las tres funciones de 6.2 / 6.3 / 6.4 y las restricciones de §7, el modelo se comporta como
un simulador: se le cambia un parámetro (un margen, una tasa, el 30 % de Triguetti, el ε de la
frontera) y devuelve **plan óptimo + utilidad + facturación + clientes + precios sombra**. Todos los
experimentos de §11 y §12 son corridas de ese mismo simulador con distinta entrada. Por eso conviene
codificarlo **una sola vez, parametrizado** (§13).

---

## 7. Las restricciones, una por una

Cada restricción sale de una frase concreta del enunciado. Esta tabla es el ítem **a.v)** del informe.

| # | Frase del enunciado | Restricción matemática |
|---|---|---|
| **R1** | *"presupuesto total de $17.000 millones para invertir en la campaña"* | `x_DC + x_AG + x_TRI + x_CAN + x_RS ≤ 17.000` |
| **R2** | *"al aumentar la visibilidad de Don Carlo o Agnellis, el otro debe recibir un refuerzo de igual magnitud de inversión"* | `x_DC = x_AG` |
| **R3** | *"su peso en el presupuesto debe superar siempre el 30 %"* (Triguetti) | `x_TRI ≥ 0,30 × 17.000 = 5.100` |
| **R4** | *"las inversiones en marketing [de Rena] sean el doble que lo que se invierte en Candealix y Triguetti combinados"* | `x_RS ≥ 2 × (x_CAN + x_TRI)` |
| **R5** | *"siempre que la suma de ambas no supere aproximadamente el 65 % de participación en el mercado de menor poder adquisitivo"* | `400·x_DC + 500·x_AG ≤ 2.580.000` |
| **R6** | *"si no supera el umbral necesario de 2.500.000 unidades […] no debe ser producido"* (Candealix) | disyunción lógica — ver §8 |
| **R7** | *"tras un refuerzo de aproximadamente $6.000 millones […] su efecto marginal [es] prácticamente nulo"* | `x_TRI1 ≤ 6.000`, tasa 0 en `x_TRI2` |
| **R8** | rendimientos decrecientes de Candealix y Rena | `x_CAN1 ≤ 5.000` , `x_RS1 ≤ 3.500` |
| **R9** | supuesto general de PL | todas las variables `≥ 0` |

### 7.1. De dónde sale el 2.580.000 de R5

Don Carlo tiene el **35 %** del segmento bajo y Agnellis el **18 %** → juntas ya ocupan el **53 %**.
El techo es **65 %**. Quedan **12 puntos porcentuales** por conquistar:

```
0,12 × 21.500.000 personas = 2.580.000 clientes nuevos como máximo, entre las dos

⇒   400·x_DC + 500·x_AG ≤ 2.580.000
```

### 7.2. ⚠ Hallazgo 1: R3 + R4 casi determinan la solución

```
R3:  x_TRI ≥ 5.100
R4:  x_RS  ≥ 2 × (x_CAN + x_TRI)  ≥  2 × 5.100  =  10.200
     ─────────────────────────────────────────────────────
     Triguetti + Rena Speziale  ≥  15.300  de  17.000
```

**Quedan apenas $1.700MM** para Don Carlo, Agnellis y Candealix. Y como R2 obliga a `x_DC = x_AG`,
si toda la sobra fuera a esas dos se llevarían **$850MM cada una**.

**Consecuencias:**
- El "plan óptimo" está **prácticamente impuesto por las reglas políticas del directorio**, no por
  la optimización. El solver casi no tiene libertad.
- El espacio factible es muy chico: conviene **verificar que sea no vacío** antes de resolver (lo es).
- Alimenta directamente la pregunta **d)**: **por R4, cada peso puesto en Triguetti arrastra dos
  pesos obligatorios a Rena Speziale.** El costo real de la regla del 30 % es **triple**, no simple.

### 7.3. ⚠ Hallazgo 2: R6 probablemente no está activa

```
2.500.000 paquetes × $1.800/paquete = $4.500 millones de facturación
```

Pero la **facturación base** de Candealix (§3.5) ya es de **$78.600 millones** — más de 17 veces el
umbral. Candealix lo supera **sin invertir un solo peso**.

Hay que **verificarlo con la corrida** y **reportarlo igual**: una restricción que resulta no activa
es un resultado válido, y decirlo demuestra que se entendió el modelo.

---

## 8. El caso especial: el umbral de Candealix (R6)

*"si no supera el umbral necesario de 2.500.000 unidades en la próxima campaña no debe ser producido"*

Esto **no es una restricción lineal**: es una **disyunción** (o vende ≥ 2.500.000 unidades, **o**
vende 0). Rompe el supuesto de divisibilidad.

**(a) Por escenarios — recomendado.** Resolver **dos modelos de PL puros** y comparar:
- Escenario 1: Candealix se produce → agregar `Q_CAN ≥ 2.500.000`
- Escenario 2: Candealix no se produce → forzar `x_CAN = 0` y sacarlo de la facturación

Se toma el que dé mejor objetivo. **Ventaja:** todo queda en PL, que es lo que pide la materia, y el
análisis de sensibilidad de cada escenario sigue siendo válido.

**(b) Con variable binaria (big-M).** `y ∈ {0,1}` (1 = se produce):
```
Q_CAN ≥ 2.500.000 · y
Q_CAN ≤ M · y
```
**Desventaja:** pasa a ser **PLEM**, y en un MILP **los precios sombra pierden su interpretación
limpia** — que es justamente lo que el TP pide analizar.

**Decisión: usar (a), mencionando (b)** para mostrar que se conoce la formulación correcta y por qué
se eligió no usarla.

---

## 9. Representación gráfica del proceso (ítem c del informe)

Adaptando el esquema "RECURSOS → PROCESO → PRODUCTOS" de la Clase 2:

```
  RECURSO              ASIGNACIÓN            CAPTACIÓN              RESULTADO
  ───────              ──────────            ─────────              ─────────

                    ┌─► x_DC  ────────┐
                    │   (400 cl/MM)   ├──► SEGMENTO BAJO  ──┐
                    ├─► x_AG  ────────┘    $41.000/pers     │
                    │   (500 cl/MM)        [tope 65 %]      │
  PRESUPUESTO       │                                        │
  $17.000 MM  ──────┤                                        ├──► FACTURACIÓN
                    ├─► x_TRI ────────┐                      │    Σ F_j
  [R1]              │   (200 → 0)     ├──► SEGMENTO MEDIO ──┤       │
                    │   [sat. 6.000]  │    $58.000/pers      │       ▼
                    ├─► x_CAN ────────┘                      │    UTILIDAD
                    │   (300 → 200)        [umbral 2,5M u.]  │    Σ margen_j·F_j
                    │                                        │
                    └─► x_RS  ──────────► SEGMENTO ALTO  ────┘
                        (150 → 100)        $134.000/pers

  Reglas del directorio que atraviesan el esquema:
    R2   x_DC = x_AG                       (paridad gama baja)
    R3   x_TRI ≥ 30 % del presupuesto      (producto bandera)
    R4   x_RS ≥ 2 × (x_CAN + x_TRI)        (apuesta premium)
```

Para el informe conviene rehacerlo prolijo (draw.io, Excel o similar), pero la estructura es esta.

---

## 10. Qué mirar en el análisis de sensibilidad (ítem b del informe)

Traducción del vocabulario de la Clase 3 a este caso. **Esta sección es la que separa un TP aprobado
de uno bueno**, porque es donde se responden de verdad las preguntas b), c) y d).

### 10.1. Precios sombra (dual price) — "¿cuánto vale relajar cada regla?"

| Restricción | Qué significa su precio sombra | Sirve para |
|---|---|---|
| **R1** Presupuesto | Cuánta utilidad extra daría **un millón más de presupuesto**. Si es alto, hay que pedirle más plata al directorio. | a) |
| **R2** `x_DC = x_AG` | El costo de la paridad. Como Don Carlo rinde 0,82 y Agnellis 1,54, **este dual debería ser claramente negativo**. | **b)** |
| **R3** `x_TRI ≥ 5.100` | Utilidad perdida por cada millón obligatorio en Triguetti. **Respuesta numérica directa a la pregunta d).** | **d)** |
| **R4** `x_RS ≥ 2(x_CAN+x_TRI)` | El costo de la regla premium. Clave para el efecto multiplicador de §7.2. | d) |
| **R5** tope 65 % gama baja | Si es ≠ 0, el techo de mercado está frenando el crecimiento y **el problema ya no es de plata sino de mercado**. | a), b) |

### 10.2. Costos reducidos — "¿qué le falta a lo que quedó afuera?"

Para cada marca o tramo que quede en **cero** en el óptimo, el costo reducido dice **cuánto habría
que mejorarle el aporte unitario** (margen, precio o eficiencia de captación) para que valga la pena
incluirla. Es la respuesta a "¿por qué el modelo no le da nada a X?".

### 10.3. Rangos — los dos ítems que pide explícitamente el informe

- **b.i) "Rangos de nivel de actividad"** → **RHS Ranges**: hasta cuánto puede variar el término
  independiente de cada restricción (presupuesto, el 30 %, el 65 %…) sin que cambie cualitativamente
  la solución. Dentro de ese rango el precio sombra se mantiene constante.
- **b.ii) "Rangos de soluciones posibles"** → **Cost Coefficient Ranges**: cuánto pueden moverse los
  coeficientes del funcional (§6.2) sin que cambie el plan óptimo. Muy relevante acá porque los
  márgenes son **estimaciones** (supuesto S3).

> ⚠ **Advertencia de la Clase 3:** fuera del rango permisible **el precio sombra deja de valer y hay
> que volver a correr el modelo**. No se puede extrapolar linealmente. (Es el ejemplo de la arcilla:
> subirla a 1.200 tn excedía el rango y la estimación quedaba corta — $57.100 estimados contra
> $60.136 reales.)

---

## 11. Protocolo de test de supuestos

Acá se responde a "¿cómo sé si mis supuestos importan?". El objetivo es poder escribir en el
informe una frase del tipo: *"la conclusión se sostiene para todo el rango razonable de los
parámetros asumidos"* — o, si no se sostiene, decir exactamente dónde se rompe.

### 11.1. Test A — Barrido OAT (one-at-a-time) ±30 %

Para cada parámetro numérico de §4.1, con **todo lo demás fijo** (*ceteris paribus*, Clase 3):

1. Fijar el parámetro en `valor_base × 0,70`, resolver, registrar `Z`, mix y restricciones activas.
2. Ídem en `valor_base × 1,30`.
3. Calcular `ΔZ` y, sobre todo, verificar **si el plan óptimo cambia** (no solo el número).

**Salida:** un **gráfico tornado** — barras horizontales ordenadas por `|ΔZ|`, que muestra de un
vistazo cuáles son los 2 o 3 parámetros que realmente mueven el resultado y cuáles son ruido.

**Criterio de decisión:**
- Si el **mix óptimo no cambia** en todo el rango → el supuesto es **irrelevante**, se reporta como
  tal y es un resultado fuerte a favor de la robustez.
- Si **cambia**, hay que identificar el **valor de quiebre** y discutir si es un valor plausible.

### 11.2. Test B — Escenarios compuestos

El OAT subestima el riesgo porque los parámetros pueden moverse juntos. Tres escenarios:

| Escenario | Cómo se arma | Para qué sirve |
|---|---|---|
| **Pesimista** | todos los parámetros asumidos en su extremo desfavorable (−30 %) | piso de utilidad |
| **Base** | valores de §4.3 | el caso a reportar |
| **Optimista** | extremos favorables (+30 %) | techo de utilidad |

**Salida:** una banda `[Z_pesimista, Z_base, Z_optimista]` para la utilidad y para el market share.
Presentar un resultado como banda en lugar de un número puntual es exactamente lo que la cátedra
pide en el criterio "Analizar".

### 11.3. Test C — Escenarios estructurales

No se barren, se corren completos y se comparan:

| Test | Variante A | Variante B |
|---|---|---|
| **S5** segmento de captación | posicionamiento (base) | mix normalizado Fig. 2 |
| **S6** lectura de R2 | `x_DC = x_AG` | relajada (= pregunta b) |
| **S7** lectura de R4 | `x_RS ≥ 2(…)` | `x_RS = 2(…)` |
| **S7** lectura de R3 | 30 % de 17.000 | 30 % de Σx_j |
| **S8** presupuesto | fuera del funcional | descontado del funcional |
| **R6** Candealix | se produce | no se produce |

### 11.4. Cómo se reporta

Una sola tabla en el informe, con una fila por supuesto:

| Supuesto | Valor base | Rango probado | ¿Cambia el mix? | ΔZ (%) | Conclusión |
|---|---|---|---|---|---|
| S1 | 200 cl/$MM | 140 – 260 | *(a completar)* | | |
| S2 | β = 100 % | 70 – 100 % | | | |
| … | | | | | |

**Esa tabla es la defensa del trabajo.** Convierte "asumimos 200 porque nos pareció" en "probamos
140 a 260 y el plan no cambia".

---

## 12. Guía de las cuatro preguntas del caso

### a) Plan de asignación que equilibre captación y rentabilidad

**Qué pide realmente:** el modelo base resuelto, más una lectura de negocio del resultado.

1. Resolver con `Z_neta` (§6.2), con `Z_oper` (§6.3) y con `Z_fact` (§6.4), y comparar los tres planes.
2. Tabla con: inversión por marca, clientes nuevos, facturación (base + incremental), unidades,
   utilidad y participación de cada marca.
3. Mostrar la **composición de la facturación** antes y después (§3.5 vs. resultado).
4. **Distribución por canales** = por segmento bajo / medio / alto (recordar el supuesto S9).
5. Señalar qué restricciones quedaron **activas** (sin holgura) y cuáles con holgura.

### b) Escenarios en que Agnellis aumente su participación

**Qué pide realmente:** análisis de sensibilidad sobre **R2** (supuesto S6).

1. Reportar el **precio sombra de R2** en la solución base y sus rangos.
2. **Parametrizar**: en lugar de `x_DC = x_AG`, probar `x_DC = k · x_AG` con k bajando desde 1, o
   `x_DC ≥ x_AG − Δ` con Δ creciente. Dejar que Agnellis crezca más y ver qué pasa.
3. Graficar **utilidad total vs. k**.
4. Atención a **R5**: al volcar plata a Agnellis (500 cl/MM contra 400), el techo del 65 % del
   segmento bajo se acerca más rápido. Puede aparecer como restricción activa.
5. Responder las dos cosas que se preguntan: **cuánta inversión necesita Don Carlo** para no perder
   presencia relativa, y **cuánto cuesta eso en utilidad total**.

### c) Market share vs. rentabilidad

**Qué pide realmente:** la frontera de Pareto. Es donde el conflicto del directorio se resuelve con
números en vez de con opiniones.

1. Aplicar **ε-constraint** (§6.5), barriendo ε.
2. Graficar utilidad vs. market share.
3. Identificar el **quiebre** de la curva: hasta ahí crecer en participación es barato; pasado ese
   punto, cada punto de share cuesta mucha utilidad.
4. Traducirlo a lenguaje de directorio: *"hasta un market share de X %, cada punto adicional cuesta
   $Y de utilidad; a partir de ahí cuesta $Z. La discusión entre accionistas y dirección se resuelve
   decidiendo de qué lado de ese quiebre quiere pararse la empresa."*

### d) ¿Está mal el 30 % obligatorio en Triguetti?

**Qué pide realmente:** una opinión **fundamentada en números**.

1. Reportar el **precio sombra de R3**: cuánta utilidad cuesta cada millón obligatorio.
2. Resolver **sin R3** y comparar utilidad, facturación y mix contra el caso base.
3. Barrer el porcentaje mínimo (0 %, 10 %, 20 %, 30 %, 40 %) y graficar utilidad vs. porcentaje.
4. **No olvidar el efecto multiplicador de §7.2:** por R4, cada peso en Triguetti obliga a dos pesos
   en Rena Speziale. El costo verdadero de la regla es mucho mayor que el dual aislado, y es el
   argumento más fuerte del análisis.
5. Sumar el test de **S1** (§11.1): si la conclusión se sostiene para toda la banda 140–260, es
   robusta pese al dato faltante.
6. **Cerrar con honestidad intelectual:** el modelo optimiza **un año**. Lo que la regla del 30 %
   protege —identidad de marca, presencia en góndola de supermercados y almacenes, poder de
   negociación con el canal— **no está en el modelo**. La respuesta correcta no es "el gerente tiene
   razón", sino: *"cuesta $X al año; la pregunta para el directorio es si la presencia de marca que
   compra vale más de $X"*. Eso es análisis; lo otro es aritmética.

---

## 13. Herramientas (ítem d del informe)

**Stack elegido: Python + PuLP**, la línea que sugieren los links de la consigna.

```python
import pulp                      # modelado y resolución del LP
import pandas as pd              # tablas de datos y de resultados
import matplotlib.pyplot as plt  # frontera de Pareto, tornado, barridos
```

**Requisito de diseño del código, derivado de §6.6 y §11:** el modelo se escribe **una sola vez, en
una función parametrizada** del tipo

```python
def resolver(params, restricciones_activas, objetivo="neta", epsilon=None) -> dict:
    ...
```

de modo que los ~40 corridas de los tests de §11 y de las preguntas b), c) y d) sean llamadas a esa
función y no copias del modelo. Todos los supuestos de §4.3 viven en un único diccionario `params`.

**Cómo se leen los resultados y cómo se mapean al vocabulario de la Clase 3:**

| En PuLP | En la Clase 3 |
|---|---|
| `pulp.value(prob.objective)` | Z óptimo (valor del funcional) |
| `v.varValue` | valor de las variables reales `X_j` |
| `prob.constraints[c].slack` | variable de holgura `S_i` |
| `prob.constraints[c].pi` | **precio sombra / dual price** |

> ⚠ **Limitación a conocer de antemano:** PuLP **no devuelve los rangos permisibles** (ni RHS ranges
> ni cost coefficient ranges) que sí aparecen listos en el "Informe de sensibilidad" de Excel Solver
> o en LINDO.
>
> **Solución:** calcularlos **re-resolviendo paramétricamente**: barrer el término independiente de
> cada restricción y detectar en qué valor el precio sombra **cambia de escalón**; ese quiebre es el
> límite del rango. Es literalmente el gráfico *"RHS Parametrics"* de la Clase 3 (págs. 31-32) hecho
> a mano. Conviene una función auxiliar reutilizable.

**Verificación cruzada:** rehacer el modelo base en **Excel + Solver** y comparar su informe de
sensibilidad con los rangos calculados. Sirve de control y es el formato que la cátedra muestra en
clase.

---

## 14. Los dos documentos del trabajo

| Archivo | Qué es | Cuándo se escribe | Cambia? |
|---|---|---|---|
| **`plan_de_trabajo.md`** (este) | **Esquema / plan.** El modelo tal como se planea: datos, supuestos con sus valores, funcional, restricciones, experimentos previstos. | Antes de codificar | Solo si cambia una **decisión de modelado**; se registra el cambio |
| **`procedimiento.md`** | **Bitácora de ejecución.** Lo que efectivamente se hizo, los resultados de cada corrida, y **en qué se apartó del plan y por qué**. | Durante el código | Permanentemente, es un log |

**Estructura prevista de `procedimiento.md`:**

1. Implementación — estructura del código y del diccionario `params`
2. **Desvíos respecto de `plan_de_trabajo.md`** — con la justificación de cada uno *(la sección más
   importante: es lo que muestra criterio propio y no seguimiento ciego de un plan)*
3. Resultados del modelo base — las tres corridas de §12.a
4. Resultados de los tests de supuestos — la tabla de §11.4 completa
5. Resultados de las preguntas b), c) y d)
6. Verificaciones (factibilidad, R6 activa o no, control cruzado con Excel)
7. Conclusiones para volcar al informe final

**Regla:** este documento **no se reescribe** para que coincida con lo que terminó pasando. Si el
plan estaba equivocado, eso se anota en `procedimiento.md` §2. Un plan que "siempre acertó" es un
plan reescrito.

---

## 15. Checklist de entrega

**Informe esperable (lista 1):**

- [ ] **a.i) Supuestos** → §4 completa + tabla de tests §11.4
- [ ] **a.ii) Variables** → §5
- [ ] **a.iii) Función objetivo** → §6 (las tres versiones + la discusión bicriterio)
- [ ] **a.iv) Parámetros** → §3 (las 4 tablas derivadas)
- [ ] **a.v) Restricciones** → §7 (con la frase del enunciado que origina cada una)
- [ ] **a.vi) Resolución del modelo** → corrida + tabla de resultados *(pendiente)*
- [ ] **b.i) Rangos de nivel de actividad** → RHS ranges, §10.3 *(pendiente)*
- [ ] **b.ii) Rangos de soluciones posibles** → cost coefficient ranges, §10.3 *(pendiente)*
- [ ] **c) Representación gráfica del proceso** → §9, a redibujar prolijo
- [ ] **d) Librerías utilizadas** → §13

**Preguntas del caso (lista 2):**

- [ ] **a)** Plan + mix + facturación + rentabilidad + canales → §12.a
- [ ] **b)** Escenarios Agnellis / Don Carlo → §12.b
- [ ] **c)** Market share vs. rentabilidad (frontera de Pareto) → §12.c
- [ ] **d)** Opinión sobre el 30 % de Triguetti → §12.d

**Formales:**

- [ ] Carátula
- [ ] Bibliografía (mínimo: Hillier & Lieberman, *Introducción a la Investigación de Operaciones*,
      cap. 1, 3 y 6 — lo que la cátedra cita en las Clases 2 y 3)
- [ ] Presentación y formato cuidados (es un criterio de evaluación explícito)

---

## 16. Próximos pasos

1. **Validar con el profesor** los supuestos **S5** (segmento de captación) y **S1** (tasa faltante
   de Triguetti). Si el criterio de la cátedra es otro, cambia todo el modelo.
2. Codificar el modelo base parametrizado en PuLP (§13) y verificar que el óptimo respete las cotas
   deducidas en §7.2.
3. Confirmar si R6 (umbral de Candealix) queda activa o no.
4. Correr los tests de §11 y completar la tabla §11.4.
5. Recién ahí, avanzar con la sensibilidad y las cuatro preguntas.

Todo lo que salga de los pasos 2 a 5 se registra en **`procedimiento.md`**, no acá.
