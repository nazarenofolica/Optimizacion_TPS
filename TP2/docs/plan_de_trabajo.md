# TP2 Optimización — "Sección Cocinas de TODO DECO"
## Plan de trabajo (esquema) — punto a)

> **Qué es este archivo.** Es el **plan / esquema** del trabajo: qué pide la consigna, qué hay que
> modelar, con qué datos, qué supuestos se adoptan y cómo se van a testear. **No es la bitácora de
> desarrollo.** Lo que efectivamente se haga al codificar (y lo que cambie respecto de este plan)
> va en un segundo archivo, `procedimiento.md` — ver §14.
>
> **Alcance:** este documento cubre **solamente el punto a)**. Los puntos b) y c) no se resuelven
> acá, pero **§16 tiene el checklist de todo el trabajo y §17 la guía para seguirlos**, con los
> parámetros exactos que hay que cambiar.
>
> **Estado:** modelo planteado. Todavía no resuelto. Los números que aparecen como "esperados"
> son cuentas a mano que el código tiene que confirmar.
>
> **Actualización posterior a la resolución.** Dos decisiones se cerraron después de codificar y
> están registradas en [`procedimiento.md`](procedimiento.md) §2.5 y §2.6: el supuesto **S1** se
> adopta en firme (no queda como consulta abierta) y el desempate **S3** pasó a tener **dos
> niveles** (primero categorías cubiertas, después unidades). El resto del plan se deja como
> estaba: el contraste entre lo planeado y lo que pasó es material para el informe.
>
> **Actualización — punto b) resuelto.** Siguiendo la guía de §17.1 (mismo modelo, `S1_disponibilidad`
> pasado a `"compartida"`), el punto b) ya está resuelto y verificado: **V\* = 13** combos de 20
> (contra 3 en a) y 27 artículos distintos en stock (contra 17). El detalle completo está en
> [`procedimiento.md`](procedimiento.md) §7; el checklist de §16 y la guía de §17.1 se marcaron
> como hechos.
>
> **Actualización — punto c) resuelto.** Siguiendo la guía de §17.2 (mesadas y alacenas juntas en
> 12 lugares, partiendo de b), el punto c) también está resuelto y verificado: **V\* = 16** combos
> de 20, la disposición conviene y hace falta pedir un lugar más en lavavajillas + cocinas para
> llegar a los 20. Detalle completo en [`procedimiento.md`](procedimiento.md) §8 y resumen en §18:
> **con esto, los tres incisos de la consigna están resueltos.**

---

## 0. Primero, tres aclaraciones sobre la consigna

**(1) La consigna es distinta a la del TP1.** Es una sola página, **sin lista de "informe
esperable" y sin criterios de evaluación**. Tiene una única lista a) b) c), y los tres incisos son
**escenarios encadenados sobre el mismo problema**:

| Inciso | Qué cambia | Estado en este plan |
|---|---|---|
| **a)** | Caso base: reposición **una vez al mes**, depósito actual | **se resuelve acá** |
| **b)** | La reposición pasa a ser **automática** | fuera de alcance |
| **c)** | Mesadas y alacenas comparten un espacio de **12 lugares**, partiendo de b) | fuera de alcance |

Como la consigna no dice cómo presentar el informe, **se toma como referencia la estructura del
TP1** (supuestos, variables, función objetivo, parámetros, restricciones, resolución). Es una
decisión nuestra, y se sostiene en que **esa es la estructura que la misma cátedra pidió
explícitamente en el TP1**: se declara así en el informe.

**(2) "Formular y resolver un modelo lineal" no quiere decir PL continua.** Las funciones son
lineales, pero no se puede tener media cocina en stock ni medio combo disponible: las variables
tienen que ser **enteras y binarias** (el título del TP es *"Programación entera y binaria"*). Es
un problema de **programación lineal entera** (Clase 06).

**(3) Eso cambia el tipo de análisis.** La Clase 06 lo dice explícito: con variables enteras se
resuelve por Branch & Bound y **"no hay análisis post-óptimo"**. No hay precios sombra ni rangos
como en el TP1. El análisis se hace **re-resolviendo escenarios** — ver §10.

---

## 1. El problema, en palabras

TODO DECO abre una **Sección Cocinas** en una sucursal del interior. Vende **20 combos de
cocina**; cada combo es una lista de **7 u 8 artículos** de ocho categorías (baldosas, empapelado,
apliques, alacenas, mesada, bacha y grifería, lavavajillas, cocina).

La regla comercial que define todo el problema:

> *"Los clientes pueden adquirir un combo completo a precio promocional **si todos los artículos
> se encuentran disponibles en stock** en el momento del pedido."*

El depósito es chico y **compartido con otras secciones**: tiene un tope de lugares por tipo de
artículo. Y la mercadería **se repone una vez por mes**.

La tensión es esta: **los combos comparten artículos y compiten por los mismos lugares del
depósito.** Cada combo que se quiere ofrecer ocupa lugar en siete espacios distintos, y basta con
que falte uno solo de sus artículos para que el combo deje de estar disponible.

---

## 2. Qué se decide, qué se sabe, qué se busca

**Lo que se decide:** cuántas unidades de cada uno de los **30 artículos** guardar en el depósito.
De esa decisión se desprende la segunda: **qué combos quedan disponibles**.

**La cadena del modelo:**

```
   STOCK                        COMBOS COMPLETOS                   RESULTADO
   ─────                        ────────────────                   ─────────
   x_p unidades del      ──►    y_c = 1 si todos los       ──►    VARIEDAD
   artículo p                   artículos del combo c              Σ y_c
      │                         tienen unidad reservada
      ▼
   lugares ocupados  ≤  capacidad de cada espacio del depósito
```

En criollo: **el stock que entra en el depósito determina qué combos se pueden armar completos, y
la cantidad de combos distintos que se pueden armar es la variedad.**

**Lo que se busca:** maximizar esa variedad. La consigna **no da precios, márgenes ni demanda**,
así que "éxito" es solamente cantidad de combos distintos disponibles (supuesto S5).

---

## 3. Los datos, ordenados

### 3.1. Catálogo de artículos

| Categoría | Artículos |
|---|---|
| Baldosas | B1 Blanco · B2 Marfil · B3 Blanco y azul a cuadros · B4 Blanco y amarillo a cuadros |
| Empapelado vinílico | E1 Símil marfil blanco · E2 Símil marfil a rayas celestes · E3 Símil mármol azul · E4 Símil mármol amarillo claro |
| Apliques de luz | L1 Plafón único rectangular · L2 Plafones led ovalados · L3 Bombillas de filamentos · L4 Globos de luz fría |
| Alacenas | A1 Madera clara · A2 Madera oscura · A3 Madera clara con puertas traslúcidas · A4 Madera oscura con puertas traslúcidas |
| Mesadas | M1 Madera laqueada · M2 Cemento alisado · M3 Mármol sintético oscuro · M4 Granito |
| Bacha y grifería | G1 Bacha dividida con grifo mono-comando · G2 Bacha dividida con grifos separados · G3 Bacha única con grifo mono-comando · G4 Bacha única con grifos separados |
| Lavavajillas | W1 Blanco · W2 Gris |
| Cocinas | C1 Eléctrica blanca · C2 Eléctrica negra · C3 A gas blanca · C4 A gas negra |

**30 artículos en total** (7 categorías de 4 variantes + lavavajillas con 2).

### 3.2. Composición de los 20 combos (el "listado" de la consigna)

| Combo | Baldosa | Empap. | Aplique | Alacena | Mesada | Bacha | Lavav. | Cocina | Artículos |
|---:|---|---|---|---|---|---|---|---|---:|
| 1 | B2 | E2 | L4 | A2 | M4 | G2 | W2 | C2 | 8 |
| 2 | B1 | E1 | L1 | A4 | M4 | G4 | W1 | C2 | 8 |
| 3 | B1 | E2 | L2 | A1 | M1 | G4 | W1 | C3 | 8 |
| 4 | B3 | E3 | L3 | A3 | M3 | G1 | W1 | C1 | 8 |
| 5 | B4 | E4 | L1 | A2 | M2 | G2 | W1 | C1 | 8 |
| 6 | B2 | E2 | L2 | A4 | M4 | G3 | W2 | C4 | 8 |
| 7 | B1 | E3 | L4 | A3 | M2 | G1 | W1 | C1 | 8 |
| 8 | B2 | E1 | L3 | A1 | M1 | G3 | W2 | C4 | 8 |
| 9 | B4 | E1 | L2 | A3 | M2 | G2 | W2 | C2 | 8 |
| 10 | B1 | E4 | L1 | A1 | M3 | G4 | W1 | C3 | 8 |
| 11 | B3 | E4 | L3 | A3 | M1 | G1 | W1 | C3 | 8 |
| 12 | B2 | — | L1 | A2 | M2 | G4 | W2 | C2 | 7 |
| 13 | B4 | — | L3 | A3 | M1 | G2 | W1 | C3 | 7 |
| 14 | B4 | E1 | L4 | A1 | M3 | G1 | — | C1 | 7 |
| 15 | B3 | E2 | L1 | A1 | M1 | G3 | — | C3 | 7 |
| 16 | B3 | E3 | L4 | A1 | M3 | G2 | — | C1 | 7 |
| 17 | B1 | E3 | L2 | A3 | M3 | G4 | — | C3 | 7 |
| 18 | B2 | E3 | L3 | A2 | M4 | G1 | — | C2 | 7 |
| 19 | B2 | E2 | L4 | A4 | M4 | G2 | — | C4 | 7 |
| 20 | B2 | E2 | L1 | A1 | M2 | G3 | — | C4 | 7 |

⚠ **Dos detalles fáciles de pasar por alto:** los combos **12 y 13 no llevan empapelado**, y los
combos **14 a 20 no llevan lavavajillas**. Todos los combos llevan exactamente una baldosa, un
aplique, una alacena, una mesada, una bacha y una cocina.

### 3.3. Capacidad del depósito

| Espacio | Qué guarda | Capacidad | Frase del enunciado |
|---|---|---:|---|
| Baldosas | B1–B4 | 5 juegos | *"hasta 5 juegos de baldosas"* |
| Empapelado | E1–E4 | 8 rollos | *"8 rollos de empapelado vinílico"* |
| Apliques | L1–L4 | 4 | *"4 apliques de luz"* |
| Alacenas | A1–A4 | 4 juegos | *"4 juegos de alacenas"* |
| Mesadas | M1–M4 | **3** | *"3 mesadas"* |
| Bacha y grifería | G1–G4 | 4 juegos | *"4 juegos de bacha y grifería"* |
| **Lavavajillas + cocinas** | W1–W2 y C1–C4 | **5 en total** | *"tienen el mismo tamaño así que pueden almacenarse juntos, con un máximo de 5 unidades en total"* |
| **Total** | | **33 lugares** | |

### 3.4. **Tabla derivada 1 — en cuántos combos aparece cada artículo**

| Categoría | Var. 1 | Var. 2 | Var. 3 | Var. 4 | Total |
|---|---:|---:|---:|---:|---:|
| Baldosas | B1: 5 | B2: **7** | B3: 4 | B4: 4 | 20 |
| Empapelado | E1: 4 | E2: 6 | E3: 5 | E4: 3 | 18 |
| Apliques | L1: 6 | L2: 4 | L3: 5 | L4: 5 | 20 |
| Alacenas | A1: **7** | A2: 4 | A3: 6 | A4: 3 | 20 |
| Mesadas | M1: 5 | M2: 5 | M3: 5 | M4: 5 | 20 |
| Bacha y grifería | G1: 5 | G2: 6 | G3: 4 | G4: 5 | 20 |
| Lavavajillas | W1: **8** | W2: 5 | | | 13 |
| Cocinas | C1: 5 | C2: 5 | C3: 6 | C4: 4 | 20 |
| **Total** | | | | | **151** |

*Control: 11 combos × 8 artículos + 9 combos × 7 artículos = 151.* Estos números son los
coeficientes de la restricción de cobertura (§7): por ejemplo, reservar B2 para todos los combos
que lo usan exigiría 7 juegos de baldosas.

### 3.5. **Tabla derivada 2 — cuántos lugares ocupa cada combo**

Los 20 combos se agrupan en **tres tipos** según lo que ocupan:

| Grupo | Combos | Artículos | Lugares en lavavajillas + cocinas | Qué no traen |
|---|---|---:|---:|---|
| **Completos** | 1 a 11 | 8 | **2** | — |
| **Sin empapelado** | 12 y 13 | 7 | **2** | empapelado |
| **Sin lavavajillas** | 14 a 20 | 7 | **1** | lavavajillas |

### 3.6. **Tabla derivada 3 — cota trivial por espacio**

Si **todos** los combos ocupan al menos *u* lugares de un espacio de capacidad *K*, entonces no
se pueden reservar más de ⌊K / u⌋ combos, se elijan como se elijan:

| Espacio | Capacidad | Lugares mínimos por combo | Cota: combos como máximo |
|---|---:|---:|---:|
| Baldosas | 5 | 1 | 5 |
| Empapelado | 8 | 0 (12 y 13 no llevan) | sin cota |
| Apliques | 4 | 1 | 4 |
| Alacenas | 4 | 1 | 4 |
| **Mesadas** | **3** | **1** | **3** |
| Bacha y grifería | 4 | 1 | 4 |
| Lavavajillas + cocinas | 5 | 1 | 5 |

**Tres lecturas que ya se pueden hacer sin resolver nada** (todas bajo el supuesto S1, §4):

1. **Las mesadas mandan.** Todos los combos llevan una mesada y hay lugar para 3: **no se pueden
   ofrecer más de 3 combos**. El problema de optimización se reduce a *cuáles* 3.
2. **Lavavajillas + cocinas es el segundo filtro.** Tres combos de los grupos "completos" o "sin
   empapelado" ocupan 2 + 2 + 2 = 6 lugares, y hay 5. Por lo tanto, **de cada 3 combos elegidos, a
   lo sumo 2 pueden salir de los combos 1 a 13.**
3. **El empapelado nunca limita.** Con 3 combos como máximo se usan 3 rollos de 8. Lo mismo pasa
   con baldosas, apliques, alacenas y bachas: con 3 combos les sobra al menos un lugar.

---

## 4. Registro de supuestos

**La regla que seguimos** (la misma del TP1): se pueden adoptar todos los supuestos que hagan
falta, **siempre que cada uno responda tres preguntas**:

1. **¿Para qué lo necesito?** (qué no se puede escribir sin él)
2. **¿Por qué ese valor o esa lectura y no otra?** (anclado en el enunciado o en la lógica del negocio)
3. **¿Cómo sé si importa?** (cómo se testea)

Todos los supuestos son **parámetros del modelo, no constantes del código**: van en un
diccionario de configuración para poder cambiarlos sin tocar la formulación (§13).

> **Diferencia con el TP1:** allá la consigna usaba lenguaje vago en casi todos los números
> (*"alrededor de 500"*, *"aproximadamente 65 %"*) y tenía sentido barrerlos ±30 %. Acá los datos
> son **conteos exactos** (lugares del depósito, artículos de cada combo). Lo discutible no son los
> números sino **cómo se interpreta la consigna**, así que casi todos los tests son de escenario.

### 4.1. Supuestos de interpretación (se testean con escenarios)

#### **S1 — "Disponible" con reposición mensual = reserva exclusiva de unidades**

- **Para qué lo necesito:** es la restricción que liga el stock con los combos. Sin decidir esto
  no se puede escribir el modelo.
- **Las dos lecturas posibles:**
  - **(i) Exclusiva.** Cada combo ofrecido tiene **su propio juego de unidades reservado para el
    mes**. Si dos combos llevan B2, hacen falta 2 juegos de B2. Garantiza que cualquier combo
    ofrecido se pueda vender aunque ya se hayan vendido los demás.
  - **(ii) Compartida.** Alcanza con **1 unidad de cada artículo**: al empezar el mes todos los
    combos que usan esos artículos están "disponibles", pero apenas se vende uno, los que
    compartían artículos con él dejan de estarlo hasta la reposición siguiente.
- **Decisión: (i).** Tres razones:
  1. La consigna pide *"tener en cuenta que la reposición se realiza una vez al mes"*. Con la
     lectura (ii) ese dato **no cambiaría nada** en el modelo, y la consigna no lo mencionaría.
  2. La lectura (ii) es **exactamente el escenario b)**: con reposición automática, lo que se vende
     vuelve enseguida y alcanza con una unidad de cada artículo. Si a) usara (ii), **a) y b) serían
     el mismo modelo** y la pregunta de b) (*"¿la variedad se ve beneficiada?"*) no tendría sentido.
  3. "Disponible para la venta" con reposición mensual tiene que valer **durante el mes**, no solo
     el día 1.
- **Test:** resolver con la lectura (ii) y comparar. **Qué esperamos:** mucha más variedad (una
  cuenta exploratoria da **13 combos contra 3**). Esa diferencia es lo que muestra que la lectura
  importa, y adelanta el resultado de b).
- **Actualización (procedimiento §2.6):** el test se corrió y confirmó los 3 contra 13. La lectura
  exclusiva **queda adoptada en firme**, con estas tres razones como justificación en el informe.
  No se deja como consulta abierta: es un supuesto declarado, como todos los demás.

#### **S2 — Cada combo lleva 1 unidad de cada artículo que lista**

- **Para qué lo necesito:** es el coeficiente de la restricción de cobertura.
- **Por qué falta:** la consigna lista **qué** artículos trae cada combo, no **cuántos**. Las
  capacidades vienen en "juegos", "rollos" y "unidades".
- **Decisión:** 1 juego / 1 rollo / 1 unidad por artículo. Para baldosas, alacenas y bachas la
  propia consigna habla de "juegos", así que 1 juego por combo es la lectura natural. **El único
  dudoso es el empapelado**: una cocina real puede necesitar más de un rollo.
- **Test:** barrer los rollos por combo de 1 a 9. **Qué esperamos:** que no cambie nada hasta
  valores absurdos, porque los combos 12 y 13 no llevan empapelado y pueden completar la terna.

#### **S3 — Desempate entre óptimos: mínimo de unidades en stock**

- **Para qué lo necesito:** el funcional de variedad (§6.1) **no mira el stock**, lo que genera
  dos problemas:
  1. **Muchos conjuntos de 3 combos son igual de buenos** (§7.2 estima 854). El solver devuelve
     uno cualquiera sin avisar.
  2. **El solver puede guardar unidades de más** sin ninguna penalidad (por ejemplo, 5 juegos de B1
     que no usa ningún combo ofrecido). Y la consigna pide justamente *"cuántas unidades de cada
     producto tener en stock"*: hace falta un número único.
- **Decisión:** una **segunda etapa lexicográfica** (Clase 05, "metas lexicográficas": las metas se
  alcanzan en orden de prioridad). Con la variedad fija en su máximo, **minimizar las unidades
  totales en stock**.
- **Por qué ese criterio:** el enunciado dice que el espacio **"es compartido con otras
  secciones"**. A igual variedad, conviene el plan que menos lugar le quita al resto de la sucursal.
- **Consecuencia a declarar:** el criterio **favorece combos de 7 artículos** (12 a 20), que son
  los que no traen empapelado o lavavajillas. Sin precios no se puede decir si eso es bueno o malo
  comercialmente.
- **Test:** comparar contra (a) **sin desempate** (lo que elija el solver, con el stock ajustado
  después) y (b) **máximo de artículos** (preferir los combos más completos).
- **Actualización (procedimiento §2.5):** al resolver, este criterio eligió tres combos **sin
  lavavajillas**, o sea que dejaba afuera una de las categorías que la consigna dice que la sección
  vende. Por eso S3 pasó a tener **dos niveles**: primero maximizar las categorías del catálogo que
  quedan en algún combo ofrecido y después minimizar las unidades. El criterio de este plan queda
  como una de las alternativas del test D, y **no cuesta ninguna unidad**: el plan final ocupa los
  mismos 21 lugares.

### 4.2. Supuestos que se declaran (no se testean)

#### **S4 — Todas las variantes de una categoría ocupan el mismo lugar**

La capacidad se mide en unidades, sin distinguir variante: un juego de baldosas B1 ocupa lo mismo
que uno B4. La consigna habla de *"5 juegos de baldosas"* sin más detalle, y lo confirma para
lavavajillas y cocinas: *"tienen el mismo tamaño"*.

#### **S5 — Todos los combos valen lo mismo y no hay demanda**

"Variedad" = **cantidad de combos distintos disponibles**, con peso 1 cada uno. La consigna no da
precios ni pronósticos de venta. Ofrecer un combo significa **poder venderlo al menos una vez en el
mes** (coherente con S1). Si la cátedra diera precios, el funcional se podría ponderar.

#### **S6 — Supuestos menores**

- **Horizonte de un mes.** El stock al inicio del mes es el pico de ocupación (después solo baja
  con las ventas), así que la capacidad se controla contra el stock inicial.
- **El depósito arranca vacío:** no hay stock previo ni pedidos pendientes.
- **Los artículos no se venden sueltos** fuera de los combos (o esas ventas no afectan la reserva).
- **Supuestos de PL de la Clase 2:** proporcionalidad, aditividad, certidumbre y no negatividad se
  mantienen. **La divisibilidad se rompe a propósito**: por eso el modelo es entero (Clase 06).

### 4.3. Tabla resumen de supuestos

| ID | Supuesto | Valor base | Alternativas a probar | Tipo de test |
|---|---|---|---|---|
| **S1** | Lectura de "disponible" | exclusiva | compartida | escenario estructural |
| **S2** | Unidades por artículo | 1 | empapelado: 1 a 9 rollos | barrido |
| **S3** | Desempate entre óptimos | mínimo de unidades *(pasó a: categorías y después unidades, §4.1)* | sin desempate · máximo de artículos · solo mínimo de unidades | escenario |
| **S4** | Mismo lugar por variante | sí | — | se declara |
| **S5** | Combos de igual valor, sin demanda | sí | — | se declara |
| **S6** | Un mes, depósito vacío, sin venta suelta | — | — | se declara |

### 4.4. ¿Estos supuestos sirven para b) y c)?

Casi todos sí, con una excepción que **la propia consigna fuerza**:

| Supuesto | a) | b) | c) |
|---|:---:|:---:|:---:|
| S1 — lectura de disponible | exclusiva | **cambia a compartida** (reposición automática) | compartida (parte de b) |
| S2, S4, S5, S6 | ● | ● | ● |
| S3 — desempate | ● | ● | ● |

Por eso el código tiene que dejar S1 como parámetro: **b) y c) van a ser el mismo modelo con otra
lectura de S1 y otras capacidades**, no modelos nuevos.

---

## 5. Variables de decisión

### 5.1. Variables

```
y_c ∈ {0, 1}      c = 1 … 20      1 si el combo c queda disponible (sus unidades están reservadas)
x_p ∈ ℤ, x_p ≥ 0  p ∈ {B1 … C4}   unidades del artículo p en stock
```

**50 variables:** 20 binarias + 30 enteras.

**¿Por qué dejar `x_p` explícita, si se puede deducir de los `y_c`?** Por tres razones: (1) la
consigna pregunta literalmente *"cuántas unidades de cada producto tener en stock"*; (2) la
capacidad del depósito se escribe naturalmente sobre el stock, no sobre los combos; (3) en b) y c)
cambia la relación entre stock y combos, y con `x_p` explícita alcanza con cambiar la restricción
de cobertura.

> **Detalle técnico:** bajo S1, la integralidad de `x_p` es **redundante**: si los `y_c` son 0 o
> 1, el stock mínimo necesario es una suma de enteros. Igual se declara entera para que el modelo
> diga lo que el problema es (Clase 06: "productos que solo admiten números naturales").

### 5.2. Parámetros

```
a_pc ∈ {0, 1}   1 si el combo c incluye el artículo p          (matriz de §3.2)
u_p             unidades del artículo p que lleva un combo     (supuesto S2; base 1)
K_e             capacidad del espacio e del depósito           (§3.3)
P_e             artículos que se guardan en el espacio e       (§3.3)
```

---

## 6. La función objetivo

### 6.1. La forma general

```
Max  V = Σ_c y_c          (cantidad de combos distintos disponibles)
```

Es la traducción directa de *"maximizar la variedad de combos disponibles para la venta"*. Todos
los combos pesan 1 (supuesto S5).

### 6.2. Por qué con esto solo no alcanza

Como vimos en S3, este funcional deja **dos grados de libertad sin decidir**: *qué* conjunto de
combos (hay muchos empatados) y *cuánto* stock extra guardar (no cuesta nada). Una respuesta del
tipo "3 combos" no dice cuántas unidades comprar, que es lo que pregunta la consigna.

### 6.3. Cómo se resuelve — dos etapas lexicográficas

```
Etapa 1:   V* = Max  Σ_c y_c
                s.a.  R1 … R4

Etapa 2:        Min  U = Σ_p x_p          (unidades totales en stock)
                s.a.  R1 … R4
                      Σ_c y_c ≥ V*        (no se resigna variedad)
```

Es el esquema de las **metas lexicográficas** de la Clase 05: primero se asegura la meta
prioritaria (variedad) y recién después, **sin empeorarla**, se optimiza la secundaria (espacio
ocupado).

**Alternativa descartada:** un solo funcional ponderado `Max Σy − ε·Σx` con `ε < 1/33` da el mismo
resultado (ninguna reducción de stock compensa perder un combo). Se prefiere el lexicográfico
porque **deja la prioridad escrita en el modelo** en vez de esconderla en un coeficiente.

> **Actualización (procedimiento §2.5):** el esquema final tiene **tres etapas** —variedad →
> categorías del catálogo cubiertas → unidades en stock—. La lógica es la misma: cada etapa no
> puede empeorar a las anteriores.

### 6.4. La relajación lineal — el puente con el TP1

Resolviendo con `y_c ∈ [0, 1]` y `x_p` continua se obtiene un PL común, que da:

- una **cota superior** de la variedad (el entero nunca puede superarla), y
- **precios sombra** de cada espacio del depósito.

**Qué esperamos:** cota **3** (la de las mesadas; la relajación no la puede saltear porque la cota
de §3.6 se deduce sumando restricciones lineales) y precio sombra **1 combo por lugar de mesada**,
0 en el resto.

> ⚠ **Esos precios sombra valen para la relajación, no para el modelo entero.** Se usan como
> orientación y se contrastan con la re-resolución de §10.1, que es la que vale.

---

## 7. Las restricciones, una por una

| # | Frase del enunciado | Restricción matemática | Cantidad |
|---|---|---|---:|
| **R1** Cobertura | *"pueden adquirir un combo completo a precio promocional si todos los artículos se encuentran disponibles en stock"* + *"la reposición de los productos se realiza una vez al mes"* | `x_p ≥ Σ_c u_p · a_pc · y_c`   ∀ p | 30 |
| **R2** Capacidad | *"Se pueden almacenar hasta 5 juegos de baldosas, 8 rollos de empapelado vinílico, 4 apliques de luz, 4 juegos de alacenas, 3 mesadas y 4 juegos de bacha y grifería"* | `Σ_{p ∈ P_e} x_p ≤ K_e`   para los 6 espacios individuales | 6 |
| **R2′** Espacio compartido | *"Los lavavajillas y las cocinas tienen el mismo tamaño así que pueden almacenarse juntos, con un máximo de 5 unidades en total"* | `x_W1 + x_W2 + x_C1 + x_C2 + x_C3 + x_C4 ≤ 5` | 1 |
| **R3** Integralidad | naturaleza del problema (Clase 06) | `y_c ∈ {0,1}`, `x_p ∈ ℤ` | — |
| **R4** No negatividad | supuesto general | `x_p ≥ 0` | — |

**Total: 37 restricciones** más las condiciones de integralidad.

Dos ejemplos escritos completos, para que quede claro qué dice R1 y qué dice R2:

```
R1 para B2:    x_B2 ≥ y_1 + y_6 + y_8 + y_12 + y_18 + y_19 + y_20
               (B2 aparece en esos 7 combos, §3.4: si se ofrecen los 7, hacen falta 7 juegos)

R2 mesadas:    x_M1 + x_M2 + x_M3 + x_M4 ≤ 3
```

> **Nota de implementación:** R2 y R2′ son la misma restricción con distinto conjunto `P_e`. En el
> código conviene tratar al depósito como una lista de **espacios**, cada uno con las categorías
> que guarda y su capacidad. Así c) (mesadas y alacenas juntas en 12 lugares) se resuelve cambiando
> un dato, no el modelo.

### 7.1. ⚠ Hallazgo 1: la variedad máxima no puede pasar de 3

Sumando R1 para las cuatro mesadas, y como **cada combo lleva exactamente una**:

```
x_M1 + x_M2 + x_M3 + x_M4  ≥  Σ_c y_c      (cada y_c aparece una sola vez, en su mesada)
x_M1 + x_M2 + x_M3 + x_M4  ≤  3            (R2)
─────────────────────────────────────────
                    Σ_c y_c  ≤  3
```

¿Se alcanza? Sí: cualquier terna de los combos 14 a 20 ocupa exactamente 3 lugares en cada uno de
los siete espacios, y todos tienen capacidad 3 o más. Entra. **Resultado esperado: V\* = 3.**

**Lectura de negocio anticipada:** con reposición mensual, la Sección Cocinas puede ofrecer **3 de
sus 20 combos (15 %)**. Y el freno no es el depósito en general: son **tres lugares de mesada**.

### 7.2. ⚠ Hallazgo 2: la solución óptima no es única, y por mucho

Una terna entra en el depósito **si y solo si** no ocupa más de 5 lugares de lavavajillas + cocinas
(los demás espacios nunca limitan con 3 combos, §3.6). Eso descarta solo las ternas con 3 combos de
los grupos que ocupan 2 lugares (combos 1 a 13):

```
ternas posibles:                 C(20, 3) = 1.140
ternas con 3 combos de 1 a 13:   C(13, 3) =   286   ← ocupan 6 lugares, no entran
─────────────────────────────────────────────────
ternas óptimas esperadas:                     854
```

Y con el desempate S3 (mínimo de unidades): el mínimo es **21 unidades** (tres combos de 7
artículos, del 12 al 20), y las ternas que lo logran son `C(9, 3) = 84` — todas entran, porque la
peor combinación ocupa 2 + 2 + 1 = 5 lugares. **Aun con desempate quedan 84 soluciones empatadas.**

**Consecuencia para el informe:** no se puede presentar "la" solución como si fuera única. Hay que
presentar **una solución representativa y la familia completa** (§8).

---

## 8. El caso especial: óptimos alternativos

En el TP1 el caso especial era una disyunción (el umbral de Candealix). Acá es la **degeneración**:
el solver devuelve **una** de las 854 ternas óptimas sin ninguna señal de que existen las otras.

**Cómo se trata:**

1. **Contar y caracterizar todas por enumeración exhaustiva.** Son 1.140 ternas: se revisan todas
   contra las capacidades. Para verificar que no hay nada mejor, se revisan también las 4.845
   cuaternas (esperado: ninguna entra).
2. **Reportar la distribución**: cuántas ternas usan 21, 22 o 23 unidades, y cuántas llenan el
   espacio de lavavajillas + cocinas.
3. **Elegir la solución a presentar con S3** (§6.3), declarando que hay 84 equivalentes.

**¿Por qué enumeración y no cortes?** La técnica de clase sería agregar un corte de exclusión
(`Σ_{c ∈ S} y_c ≤ 2` para cada terna ya encontrada) y volver a resolver hasta que dé infactible.
Funciona, pero depende del solver. La fuerza bruta **no usa el solver en absoluto**, así que sirve
de **control independiente**: si los dos caminos dan V\* = 3, el modelo está bien escrito.

---

## 9. Representación gráfica del proceso

Adaptando el esquema "RECURSOS → PROCESO → PRODUCTOS" de la Clase 2:

```
  RECURSO: DEPÓSITO             STOCK x_p                COMBOS y_c              RESULTADO
  ─────────────────             ─────────                ──────────              ─────────

  Baldosas          ≤ 5  ───►  B1 B2 B3 B4    ──┐
  Empapelado        ≤ 8  ───►  E1 E2 E3 E4    ──┤
  Apliques          ≤ 4  ───►  L1 L2 L3 L4    ──┤        ┌──► Combo 1   (8 art.)
  Alacenas          ≤ 4  ───►  A1 A2 A3 A4    ──┼─ R1 ──►├──► Combo 2   (8 art.)
  Mesadas           ≤ 3  ───►  M1 M2 M3 M4    ──┤ cober- │       …                ──►  VARIEDAD
  Bacha y grifería  ≤ 4  ───►  G1 G2 G3 G4    ──┤ tura   └──► Combo 20  (7 art.)        Σ y_c
  Lavav. + cocinas  ≤ 5  ───►  W1 W2 C1…C4    ──┘
         R2 / R2′
                                    un combo cuenta solo si TODOS sus artículos
                                    tienen una unidad reservada para él (S1)
```

Para el informe conviene rehacerlo prolijo (TikZ, como en el TP1), pero la estructura es esta.

> **Actualización:** ya está rehecho en TikZ y compilado, listo para el informe, en
> [`esquema_proceso.tex`](esquema_proceso.tex) (procedimiento §3.10).

---

## 10. Qué analizar si no hay precios sombra

La Clase 06 es clara: en programación entera **"no hay análisis post-óptimo"**. Estas son las
herramientas que lo reemplazan, cada una con su equivalente del TP1:

### 10.1. "¿Cuánto vale un lugar más?" — re-resolución por espacio

| En el TP1 (PL) | Acá (PLE) |
|---|---|
| Precio sombra de una restricción | **Sumar 1 lugar a un espacio, volver a resolver y medir ΔV\*** |

**Qué esperamos:** solo las **mesadas** suman (3 → 4 combos). En el resto ΔV\* = 0: son lugares que
hoy no valen nada.

### 10.2. La cadena de cuellos de botella

Si se sigue agregando lugar de mesada, ¿hasta dónde crece la variedad? **Qué esperamos:** con 4
mesadas pasan a limitar a la vez **apliques, alacenas y bachas** (los tres tienen 4 lugares y
todos los combos usan uno), así que con 5 mesadas la variedad **sigue en 4**. De ahí en adelante,
**ningún lugar extra aislado suma**: hay que ampliar varios espacios a la vez.

Es material directo para el inciso c), que pregunta *"¿qué otras unidades de almacenamiento
deberían solicitarse?"*.

### 10.3. Relajación lineal

Cota y precios sombra de §6.4, con la advertencia de que valen para el PL relajado.

### 10.4. Holguras

Esto sí está bien definido en el modelo entero: **cuánto lugar sobra en cada espacio** en la
solución presentada. Hay que tener presente que la holgura de lavavajillas + cocinas **depende de
cuál de las 854 ternas se elija**.

---

## 11. Protocolo de test de supuestos

El objetivo es poder escribir en el informe *"la conclusión se sostiene bajo las lecturas
razonables de la consigna"*, o decir exactamente dónde se rompe.

### 11.1. Test A — Capacidad +1 y barrido de mesadas

1. Para cada uno de los 7 espacios: capacidad + 1, resolver, registrar V\* y ΔV\*.
2. Barrer la capacidad de mesadas de 3 a 6. En cada nivel, repetir el paso 1 para ver **qué espacio
   pasa a ser el cuello de botella**.

**Control:** agregar capacidad **nunca** puede bajar la variedad.

### 11.2. Test B — S1: lectura exclusiva vs. compartida

Resolver los dos modelos completos (etapa 1 + etapa 2) y enumerar sus óptimos alternativos.
**Control:** la lectura compartida exige menos stock, así que su V\* tiene que ser **mayor o igual**.

### 11.3. Test C — S2: rollos de empapelado por combo

Barrer de 1 a 9 rollos y registrar V\*. **Control:** más rollos por combo nunca puede subir la
variedad.

### 11.4. Test D — S3: criterio de desempate

Correr las tres variantes (mínimo de unidades, sin desempate, máximo de artículos) y comparar
combos elegidos, unidades totales y ocupación de lavavajillas + cocinas. **Control:** las tres
tienen que mantener V\*.

### 11.5. Cómo se reporta

Una sola tabla, una fila por test. **Está completa en
[`procedimiento.md`](procedimiento.md) §4.6**; acá queda el formato previsto:

| Test | Base | Alternativa | V\* base | V\* alternativa | ¿Cambia la conclusión? |
|---|---|---|---:|---:|---|
| A — capacidad +1 | depósito actual | +1 por espacio | 3 | *(a completar)* | |
| B — S1 | exclusiva | compartida | 3 | | |
| C — S2 | 1 rollo | 1 a 9 rollos | 3 | | |
| D — S3 | mínimo de unidades | otras dos | 3 | | |

---

## 12. Guía del punto a) — qué hay que reportar

1. **La formulación completa:** variables (§5), funcional en dos etapas (§6), restricciones con la
   frase que las origina (§7).
2. **V\* = 3, con la demostración de la cota** (§7.1). Que el resultado se pueda probar a mano es
   el mejor argumento de que el modelo está bien.
3. **El plan de stock:** tabla con los 30 artículos y sus unidades (cero incluidos), bajo S3.
4. **Qué combos quedan ofrecidos**, y la advertencia explícita de que hay 854 ternas óptimas (84
   con el desempate de este plan; **49 con el desempate final** — ver procedimiento §3.7).
5. **Ocupación del depósito:** holgura de cada espacio, cuáles limitan.
6. **Resultado de los tests** (§11.5).
7. **Lectura de negocio:** con reposición mensual la sección ofrece apenas el 15 % de su catálogo
   de combos; el freno son tres lugares de mesada y el resto del depósito queda en buena parte
   ocioso. Eso es lo que motiva los cambios que proponen b) y c).

---

## 13. Herramientas

**Stack: Python + PuLP (solver CBC)**, igual que en el TP1.

```python
import pulp                  # modelado y resolución del PLE (Branch & Bound de CBC)
import pandas as pd          # tablas de datos y de resultados
from itertools import combinations   # enumeración exhaustiva de óptimos (§8)
```

**Requisito de diseño, el mismo del TP1:** el modelo se escribe **una sola vez, en una función
parametrizada** del tipo

```python
def resolver(params, objetivo="variedad", variedad_min=None, relajar=False) -> dict:
    ...
```

de modo que las dos etapas, la relajación lineal y todos los tests de §11 sean llamadas a esa
función. Los supuestos S1–S3 y las capacidades del depósito viven en un único diccionario `params`.

**Equivalencias con lo que muestra la Clase 06 (LINDO/LINGO):**

| En la clase | En PuLP |
|---|---|
| `INT y` (binaria) | `pulp.LpVariable(..., cat=pulp.LpBinary)` |
| `GIN x` (entera general) | `pulp.LpVariable(..., cat=pulp.LpInteger)` |
| Branch & Bound | lo hace CBC internamente |
| Dual prices | `constraint.pi`, **solo en la relajación lineal** |

---

## 14. Los dos documentos del trabajo

| Archivo | Qué es | Cuándo se escribe | ¿Cambia? |
|---|---|---|---|
| **`plan_de_trabajo.md`** (este) | **Esquema / plan.** El modelo tal como se planea: datos, supuestos, funcional, restricciones, tests previstos. | Antes de codificar | Solo si cambia una **decisión de modelado**; se registra el cambio |
| **`procedimiento.md`** | **Bitácora de ejecución.** Lo que efectivamente se hizo, los resultados, y **en qué se apartó del plan y por qué**. | Durante el código | Permanentemente, es un log |

**Estructura prevista de `procedimiento.md`:**

1. Implementación — entorno, estructura del código, diseño de `params`
2. **Desvíos respecto de `plan_de_trabajo.md`** — con la justificación de cada uno
3. Resultados del punto a) — etapas 1 y 2, plan de stock, óptimos alternativos, relajación
4. Resultados de los tests de supuestos — la tabla de §11.5 completa
5. Verificaciones
6. Conclusiones para el informe

**Regla:** este documento **no se reescribe** para que coincida con lo que terminó pasando. Si el
plan estaba equivocado, eso se anota en `procedimiento.md` §2.

---

## 15. Checklist del punto a)

- [ ] **Supuestos** → §4 + tabla de tests §11.5
- [ ] **Variables** → §5
- [ ] **Función objetivo** → §6 (las dos etapas + la relajación)
- [ ] **Parámetros** → §3 (composición, capacidades, 3 tablas derivadas)
- [ ] **Restricciones** → §7 (con la frase del enunciado de cada una)
- [x] **Resolución del modelo** → corrida + plan de stock *(hecho: procedimiento §3.3 y §3.4)*
- [x] **Óptimos alternativos** → enumeración §8 *(hecho: procedimiento §3.7)*
- [x] **Análisis sin precios sombra** → §10 *(hecho: procedimiento §4.1 y §4.2)*
- [ ] **Representación gráfica** → §9, a redibujar prolijo
- [ ] **Librerías utilizadas** → §13

---

## 16. Estado del trabajo — checklist

Estado a la fecha de la última corrida. El detalle de todo lo marcado como hecho está en
[`procedimiento.md`](procedimiento.md); acá va solo el estado.

### Punto a) — hecho

- [x] Datos cargados y verificados, 46 chequeos (`scripts/00_verificar_datos.py`)
- [x] Modelo formulado: variables, funcional y restricciones (§5 a §7)
- [x] Supuestos S1 a S6 escritos y justificados (§4); los dos que estaban abiertos, cerrados
      (procedimiento §2.6)
- [x] Modelo codificado y resuelto: **3 combos** (12, 15 y 18), 21 unidades, las 8 categorías
      cubiertas (procedimiento §3.3 y §3.4)
- [x] Desempate de tres etapas: variedad → categorías → unidades (procedimiento §2.5)
- [x] Óptimos alternativos enumerados: 854 ternas, 49 después del desempate (procedimiento §3.7)
- [x] Relajación lineal: cota 3 y precio sombra de mesadas = 1 (procedimiento §3.9)
- [x] Análisis sin precios sombra: +1 lugar por espacio y barrido de mesadas (procedimiento §4.1 y §4.2)
- [x] Tests de los supuestos S1, S2 y S3, con 10 controles automáticos (procedimiento §4)
- [x] 12 tablas en `resultados/tablas/`

### Punto a) — material para el informe, también hecho

- [x] Figura de ocupación del depósito, con mesadas marcada como el espacio que limita
      (`resultados/graficos/01_ocupacion_deposito.png`)
- [x] Esquema del proceso redibujado en TikZ y compilado
      ([`esquema_proceso.tex`](esquema_proceso.tex))
- [x] Los tests A.1 y A.2 van como **tabla**, no como gráfico (procedimiento §3.10)

**Con esto el punto a) queda completo.** Lo que sigue es b), c) y la redacción del informe.

### Punto b) — reposición automática — hecho → guía en §17.1

- [x] Resuelto con `S1_disponibilidad="compartida"`: **V\* = 13** combos de 20 (procedimiento §7.1)
- [x] La variedad de oferta se beneficia con las dos lecturas: combos 3 → 13, artículos distintos
      en stock 17 → 27 (procedimiento §7.8)
- [x] Óptimos alternativos enumerados: 4 (contra 854 en a), procedimiento §7.7)
- [x] Análisis de capacidad +1 por espacio repetido: solo mesadas (+3) y lavavajillas + cocinas
      (+2) suman; el resto ya tiene tantos lugares como variantes existen (procedimiento §7.5 y §7.6)
- [x] Todo registrado en `procedimiento.md` §7, con 8 controles automáticos en verde (§7.9)

### Punto c) — mesadas y alacenas juntas — hecho → guía en §17.2

- [x] Espacios redefinibles en `config.construir_params` (argumento `espacios`; único cambio de
      código de todo el trabajo, procedimiento §8.1)
- [x] Resuelto con mesadas + alacenas en un espacio de 12 lugares, partiendo de b): **V\* = 16**
      combos de 20 (procedimiento §8.2)
- [x] No se completan los 20 combos: quedan afuera los 4 combos con cocina C4 (6, 8, 19 y 20),
      porque lavavajillas + cocinas sigue en 6 variantes para 5 lugares (procedimiento §8.3)
- [x] La disposición conviene (variedad 13 → 16 sin pedir lugar extra) y hace falta pedir **un
      lugar más en lavavajillas + cocinas** para llegar a los 20 combos (procedimiento §8.5 y §8.6)
- [x] Todo registrado en `procedimiento.md` §8, con 8 controles automáticos en verde (§8.8)

### Informe (todo por hacer)

- [ ] Redactarlo con la estructura del TP1 (§0) y la checklist del punto a) de §15
- [ ] Bibliografía: Hillier & Lieberman cap. 11 (programación entera) y las Clases 05 y 06

---

## 17. Cómo se siguen b) y c)

Los dos incisos son **el mismo modelo con otros parámetros**: no hay que escribir un modelo nuevo.
Esta sección está para que cualquiera de los dos pueda retomar desde donde quedó a).

### 17.1. Punto b) — la reposición pasa a ser automática

**Qué cambia:** si lo que se vende se repone enseguida, **alcanza con una unidad de cada artículo**.
Es exactamente la lectura "compartida" del supuesto S1 (§4.1), que ya está implementada y probada:

```python
from src.config import construir_params
from src import modelo

params = construir_params(S1_disponibilidad="compartida")
etapa1, final = modelo.resolver_lexicografico(params)
```

**Lo que ya se sabe** por el test B (procedimiento §4.3), y que conviene reproducir como primer paso:

| | a) exclusiva | b) compartida |
|---|---:|---:|
| Combos ofrecidos | 3 | **13** |
| Unidades en stock | 21 | 27 |
| Artículos distintos en el depósito | 17 | **27** de 30 |
| Óptimos alternativos | 854 | 4 |

⚠ **Ojo con cómo está redactada la pregunta.** La consigna pide si se beneficia *"la variedad de
oferta de productos"*, que puede leerse como combos o como artículos. Conviene responder con las
dos, que acá apuntan en el mismo sentido: **combos ofrecidos** (3 → 13) y **artículos distintos**
(17 → 27). Con la lectura compartida cada artículo guardado ocupa una sola unidad, así que las
unidades coinciden con la cantidad de artículos distintos.

### 17.2. Punto c) — mesadas y alacenas comparten 12 lugares

**Qué cambia:** dos espacios del depósito se fusionan en uno de 12 lugares, **partiendo del
escenario de b)**.

Es el único punto que pide tocar el código, y es un cambio chico: hoy `construir_params` deja pisar
capacidades pero no redefinir los espacios. Hay que permitir pasar la estructura completa:

```python
# en config.construir_params, aceptar un argumento espacios=None:
base = deepcopy(espacios if espacios is not None else ESPACIOS)

# y en el script del inciso c):
espacios_c = deepcopy(config.ESPACIOS)
del espacios_c["mesadas"], espacios_c["alacenas"]
espacios_c["mesadas_alacenas"] = {
    "nombre": "Mesadas + alacenas",
    "categorias": ("M", "A"),
    "capacidad": 12,
}
params = construir_params(espacios=espacios_c, S1_disponibilidad="compartida")
```

El resto del código recorre `params["espacios"]` de forma genérica —restricciones, cotas triviales,
ocupación y reportes—, así que **no hay que tocar nada más**.

**Cuenta a mano de qué esperar, que el modelo tiene que confirmar:** con la lectura de b), mesadas
y alacenas dejan de limitar (8 tipos en 12 lugares), pero **lavavajillas + cocinas sigue teniendo 6
tipos para 5 lugares**, así que no se completarían los 20 combos. Dejando afuera la cocina C4, que
aparece en 4 combos, quedarían **16**. Para llegar a los 20 haría falta **un lugar más en el espacio
de lavavajillas y cocinas**.

Para responder *"¿qué otras unidades de almacenamiento deberían solicitarse?"* ya está la
herramienta: el test de capacidad +1 por espacio (`02_tests_supuestos.py`, función
`test_capacidad`), corrido sobre los parámetros de c).

> **Actualización — confirmado al resolver (procedimiento §8).** La cuenta a mano de este párrafo
> se cumplió exacto: **V\* = 16**, afuera los combos 6, 8, 19 y 20 (los cuatro con C4), y el test de
> capacidad +1 confirmó que alcanza con **un lugar más en lavavajillas + cocinas** para llegar a los
> 20 combos. Ningún otro espacio pide ampliación.

---

Todo lo que salga de estos pasos se registra en **`procedimiento.md`**, no acá.

---

## 18. Estado final del trabajo

Los tres incisos de la consigna están **resueltos y verificados**: a) en `scripts/01_punto_a.py`
(procedimiento §3), b) en `scripts/03_punto_b.py` (procedimiento §7) y c) en
`scripts/04_punto_c.py` (procedimiento §8). El detalle completo de cada corrida, sus hallazgos y
sus controles automáticos está en [`procedimiento.md`](procedimiento.md); este documento se deja
como el esquema original, con notas de "Actualización" donde el resultado confirmó o ajustó lo
planeado. Lo único que queda es la redacción del informe.
