# TP2 TODO DECO — Procedimiento (bitácora de desarrollo) — puntos a) y b)

> **Qué es este archivo.** El registro de lo que **efectivamente se hizo** al codificar y
> resolver el modelo, incluyendo **en qué se apartó del plan y por qué**. El plan está en
> [`plan_de_trabajo.md`](plan_de_trabajo.md) y **no se reescribe** para que coincida con esto:
> lo único que se le agregó son notas de "Actualización" que apuntan a §2.5, §2.6 y §8.
>
> **Estado:** punto a) resuelto y verificado (§3), tests de supuestos corridos (§4) y las dos
> decisiones que habían quedado abiertas, cerradas con justificación (§2.5 y §2.6). Punto b)
> resuelto y verificado (§8). Punto c) sin empezar. Informe sin redactar.

---

## 1. Implementación

### 1.1. Entorno

Python 3.10.11, `pulp 3.3.2` (solver **CBC**) y `pandas 2.3.3`, las mismas versiones del TP1.
No hizo falta instalar nada. Ver `requirements.txt`.

### 1.2. Estructura

```
TP2/
├── requirements.txt
├── docs/
│   ├── plan_de_trabajo.md        esquema (lo que se planeó)
│   ├── procedimiento.md          este archivo (lo que pasó)
│   └── esquema_proceso.tex       esquema del proceso en TikZ, para el informe
├── Consigna/                     el enunciado del TP
├── Material/                     clases 05 (metas) y 06 (entera y binaria)
├── src/
│   ├── config.py                 datos del enunciado + supuestos S1..S3
│   ├── datos.py                  tablas derivadas + enumeración exhaustiva
│   ├── modelo.py                 construcción y resolución del PLE
│   ├── reportes.py               tablas de salida
│   └── graficos.py               gráficos del informe (matplotlib)
├── scripts/
│   ├── 00_verificar_datos.py     46 chequeos contra la consigna y las tablas del plan
│   ├── 01_punto_a.py             resuelve el punto a)
│   └── 02_tests_supuestos.py     tests del plan §11
└── resultados/
    ├── tablas/*.csv              12 tablas
    └── graficos/*.png            la figura del punto a)
```

### 1.3. Cómo correrlo

```bash
cd "C:\Users\Leandro\Desktop\Ciencia de datos\3_anio\Optimizacion\TPS\TP2"

python scripts/00_verificar_datos.py   # correr siempre primero
python scripts/01_punto_a.py           # punto a): etapas, óptimos alternativos, relajación + gráfico 1
python scripts/02_tests_supuestos.py   # tests de supuestos (~30 segundos) + gráfico 2
```

### 1.4. Diseño del modelo parametrizado

Igual que en el TP1, todo pasa por **una sola función**:

```python
modelo.resolver(params, objetivo="variedad", variedad_min=None, categorias_min=None,
                combos_fijos=None, relajar=False)
modelo.resolver_lexicografico(params)   # todas las etapas, según el criterio S3
```

- `params` viene de `config.construir_params(capacidades=None, **supuestos)`. Un supuesto, un
  espacio o una categoría inexistente **falla con `KeyError`**, y un valor fuera de las opciones
  con `ValueError`. La razón es la misma del TP1: un typo silencioso devolvería el caso base
  haciéndose pasar por el escenario pedido.
- **El depósito es una lista de espacios**, cada uno con las categorías que guarda y su capacidad
  (como anticipaba la nota del plan §7). "Lavavajillas + cocinas" es un espacio con dos categorías.
  El inciso c) va a ser un cambio de datos, no de modelo.
- **S1 es un parámetro**: con `"exclusiva"` la cobertura es una restricción por artículo
  (`x_p ≥ Σ u·y_c`); con `"compartida"`, una por par artículo–combo (`x_p ≥ u·y_c`). El inciso b)
  va a ser este mismo modelo con la otra lectura.
- **Las etapas del desempate son llamadas a la misma función**, atadas entre sí por
  `variedad_min` y `categorias_min` (§2.5).
- Las restricciones tienen nombre (`R1_cob_B2`, `R2_cap_mesadas`, `CAT_W`, …) para leer holguras
  y, en la relajación, precios sombra.
- **La enumeración exhaustiva** (`datos.enumerar_factibles`) no usa el solver: arma el stock
  necesario de cada conjunto de combos y lo compara contra las capacidades. Es el control
  independiente del plan §8.

---

## 2. Desvíos respecto del plan de trabajo

### 2.1. ⚠ El reporte de la relajación lineal marcaba los siete espacios como limitantes

**Qué pasó.** La primera corrida de la relajación mostró esto:

```
Espacio                Capacidad  Ocupado  Holgura  Limita  Precio sombra
Baldosas                   5       5,00     0,00     Sí        0
Empapelado vinílico        8       8,00     0,00     Sí        0
…                                                    Sí
Mesadas                    3       3,00     0,00     Sí        1
```

Todo el depósito lleno y todos los espacios "limitando", pero con precio sombra 0 en seis de
siete. Las dos cosas juntas no tienen sentido.

**Por qué pasó.** Es el mismo problema que el plan identificó para la etapa 1 (supuesto S3): el
funcional `Max Σ y_c` **no penaliza el stock**, así que el solver puede guardar unidades de más
sin costo. En la relajación, CBC llenó los 33 lugares con 21 unidades necesarias y **12 que no usa
ningún combo**. El plan lo había anticipado para la etapa 1, pero **no lo trasladó a la relajación**
(§6.4 solo habla de la cota y los duales).

**Qué se hizo.** `modelo.resolver()` ahora devuelve también `ocupacion_necesaria`: la ocupación
que exigen los `y_c` obtenidos, calculada con `datos.stock_requerido()`, que admite `y_c`
fraccionarios. La tabla de la relajación usa esa ocupación.

**Impacto.** Los precios sombra estaban bien desde el principio (1 en mesadas, 0 en el resto).
Solo cambiaron las columnas de holgura: ahora **limita únicamente mesadas**, coherente con su
dual.

### 2.2. Se agregó el argumento `combos_fijos`

El plan §13 preveía `resolver(params, objetivo, variedad_min, relajar)`. Para el desempate
"ninguno" del test D hacía falta **respetar la terna que eligió el solver y solo quitarle el stock
sobrante**, y eso no se puede expresar con `variedad_min`. `combos_fijos` fija los `y_c` y deja que
la última etapa minimice el stock.

### 2.3. Corrección de redacción en el plan §7.1

La frase decía que una terna de los combos 14 a 20 ocupa 3 lugares "en cada espacio **salvo**
lavavajillas + cocinas y empapelado", cuando en esos dos también ocupa 3. Se corrigió la redacción.
**No cambia ningún número ni decisión**: se anota acá para que quede constancia de que el plan se
tocó.

### 2.4. El test B tarda más de lo previsto

La lectura compartida tiene V\* = 13, así que la fuerza bruta revisa C(20,13) + C(20,14) = 116.280
conjuntos. El script completo tarda unos 30 segundos. Es aceptable y no se optimizó.

### 2.5. ⚠ Cambio de decisión de modelado: S3 pasa a tener dos niveles

**Qué pasó.** Con el desempate del plan (mínimo de unidades), la solución era la terna **14 – 18 –
20**: tres combos **sin lavavajillas**. El stock quedaba con **cero lavavajillas**, cuando la
consigna abre la sección diciendo qué vende:

> *"se ofrecen a la venta una serie de combos de cocina que combinan distintos artículos: Cocina,
> **lavavajillas**, alacenas, mesadas, bacha, grifería, baldosas y papel vinílico decorativo"*.

Un plan de stock que deja una de esas categorías en cero contradice la descripción de la propia
sección.

**Qué se hizo.** S3 pasó de un nivel a dos, y el modelo quedó con **tres etapas lexicográficas**
(la lógica de metas por prioridad de la Clase 05):

```
Etapa 1:   Max  Σ_c y_c                                    variedad de combos
Etapa 2:   Max  Σ_k z_k     s.a. Σ_c y_c ≥ V*              categorías del catálogo cubiertas
Etapa 3:   Min  Σ_p x_p     s.a. Σ_c y_c ≥ V*, Σ_k z_k ≥ K*   unidades en stock
```

con `z_k ∈ {0,1}` = 1 si la categoría *k* está en algún combo ofrecido, atada por
`z_k ≤ Σ_{c que traen k} y_c`. **La atadura es con los combos y no con el stock**: si fuera con el
stock, el solver podría "cubrir" una categoría guardando una unidad suelta que no usa ningún combo,
que es justamente el problema de §2.1.

**Tres decisiones dentro del cambio, con su porqué:**

1. **Criterio general y no una regla puntual.** Se maximizan **las categorías del catálogo**, no
   "que haya un lavavajillas". Así el criterio sale de la consigna (la lista de artículos que vende
   la sección) y sirve igual en b) y c), donde el combo que falte puede ser otro.
2. **Como objetivo y no como restricción.** Una restricción del tipo *"al menos un combo con
   lavavajillas"* puede volver el modelo **infactible**. El test C lo muestra con un caso real: con
   9 rollos de empapelado por combo, **ningún** combo con empapelado entra en el depósito, así que
   exigir esa categoría no tendría solución. Como etapa de desempate, el modelo simplemente informa
   que cubre 7 categorías en vez de 8 y sigue resolviendo. Hay un control automático que lo
   verifica.
3. **Categorías antes que unidades.** Primero la sección tiene que poder ofrecer lo que dice que
   vende; ahorrar lugar beneficia a **otras** secciones y es secundario. En este caso la discusión
   es teórica: **el cambio no cuesta ni una unidad** (21 lugares en los dos criterios, §4.5).

**Impacto en el resultado.** La terna pasa de 14 – 18 – 20 a **12 – 15 – 18**: mismas 21 unidades,
las 8 categorías cubiertas, un lugar más ocupado en lavavajillas + cocinas (4 de 5 en vez de 3).

**Impacto en el modelo.** Las etapas 2 y 3 agregan 8 variables binarias `z_k` y 8 restricciones
`CAT_k`, que el plan §5.1 y §7 no contaban (ahí eran 50 variables y 37 restricciones). La etapa 1,
que es la que define V\*, **no cambió**.

**Compatibilidad con b) y c).** El criterio es un parámetro del mismo modelo, así que se aplica
igual en los otros incisos. Ya se verificó en el test B: con la lectura compartida (la de b) el
modelo resuelve sin problemas, sigue dando **V\* = 13** y cubre las 8 categorías. **No invalida
nada de lo establecido para b).**

### 2.6. Decisiones que estaban abiertas y quedaron cerradas

El plan dejaba dos cosas "a validar". Se cierran acá, como supuestos declarados y justificados,
que es el criterio del equipo: un supuesto vale si está justificado y escrito.

| Qué estaba abierto | Decisión | Justificación |
|---|---|---|
| **S1** — lectura de "disponible" (plan §4.1 y §16) | Se adopta la **reserva exclusiva** | Las tres razones del plan §4.1: la consigna pide tener en cuenta la reposición mensual (con la otra lectura ese dato no cambiaría nada), la lectura compartida **es** el escenario del inciso b) —y entonces a) y b) serían el mismo modelo—, y "disponible" con reposición mensual tiene que valer durante todo el mes. El test B (§4.3) muestra cuánto pesa: 3 combos contra 13. Va al informe como supuesto, con el test al lado |
| **Estructura del informe** (plan §0) | Se usa la del **TP1** | La consigna del TP2 no la especifica, y esa es la estructura que la misma cátedra pidió explícitamente en el TP1 |

En el plan quedaron notas de "Actualización" que apuntan acá; el resto del plan no se tocó.

---

## 3. Resultados del punto a)

Corrida: `python scripts/01_punto_a.py` · estado **Optimal** en las tres etapas y en la relajación.

### 3.1. Variedad máxima: 3 combos de 20

**V\* = 3**, el 15 % del catálogo de combos. Coincide con la cota de las mesadas que el plan dedujo
a mano (§7.1).

### 3.2. Etapa 1 sola: el solver llena el depósito

Sin desempate, CBC devolvió los combos **15, 17 y 20** con **33 unidades en stock**: el depósito
completo. Esos tres combos necesitan 21. **Los otros 12 lugares están ocupados con mercadería que
no usa ningún combo ofrecido.**

Es exactamente el riesgo que justificó las etapas siguientes (plan §6.2). Si se reportara la etapa 1
sola, la respuesta a *"cuántas unidades de cada producto tener en stock"* sería **equivocada**,
aunque la variedad estuviera bien.

### 3.3. La solución que se presenta

Con el desempate de §2.5 (categorías y después unidades):

| Combo | Artículos | Unidades | Lugares lavav. + cocinas |
|---:|---|---:|---:|
| 12 | B2 L1 A2 M2 G4 W2 C2 | 7 | 2 |
| 15 | B3 E2 L1 A1 M1 G3 C3 | 7 | 1 |
| 18 | B2 E3 L3 A2 M4 G1 C2 | 7 | 1 |
| **Total** | | **21** | **4** |

**Cubre las 8 categorías del catálogo:** el combo 12 aporta el lavavajillas (no trae empapelado) y
los combos 15 y 18 aportan el empapelado.

### 3.4. Plan de stock — cuántas unidades de cada artículo

| Categoría | Artículo | Unidades | Para los combos |
|---|---|---:|---|
| Baldosas | B2 Marfil | **2** | 12, 18 |
| Baldosas | B3 Blanco y azul a cuadros | 1 | 15 |
| Empapelado | E2 Símil marfil a rayas celestes | 1 | 15 |
| Empapelado | E3 Símil mármol azul | 1 | 18 |
| Apliques | L1 Plafón único rectangular | **2** | 12, 15 |
| Apliques | L3 Bombillas de filamentos | 1 | 18 |
| Alacenas | A1 Madera clara | 1 | 15 |
| Alacenas | A2 Madera oscura | **2** | 12, 18 |
| Mesadas | M1 Madera laqueada | 1 | 15 |
| Mesadas | M2 Cemento alisado | 1 | 12 |
| Mesadas | M4 Granito | 1 | 18 |
| Bacha y grifería | G1 Bacha dividida con grifo mono-comando | 1 | 18 |
| Bacha y grifería | G3 Bacha única con grifo mono-comando | 1 | 15 |
| Bacha y grifería | G4 Bacha única con grifos separados | 1 | 12 |
| Lavavajillas | W2 Gris | 1 | 12 |
| Cocinas | C2 Eléctrica negra | **2** | 12, 18 |
| Cocinas | C3 A gas blanca | 1 | 15 |
| **Total** | **17 artículos** | **21** | |

**En cero (13 artículos):** B1, B4, E1, E4, L2, L4, A3, A4, M3, G2, W1, C1 y C4. La tabla completa
de 30 filas está en `resultados/tablas/04_plan_stock.csv`.

Los cuatro artículos con 2 unidades (B2, L1, A2, C2) son los que comparten dos de los combos
elegidos: es la reserva exclusiva del supuesto S1 en acción.

### 3.5. Ocupación del depósito

| Espacio | Capacidad | Ocupado | Holgura | Limita |
|---|---:|---:|---:|:---:|
| Baldosas | 5 | 3 | 2 | No |
| Empapelado vinílico | 8 | 2 | 6 | No |
| Apliques de luz | 4 | 3 | 1 | No |
| Alacenas | 4 | 3 | 1 | No |
| **Mesadas** | **3** | **3** | **0** | **Sí** |
| Bacha y grifería | 4 | 3 | 1 | No |
| Lavavajillas + cocinas | 5 | 4 | 1 | No |
| **Total** | **33** | **21** | **12** | |

### 3.6. ⚠ Hallazgo principal: tres lugares de mesada deciden todo el plan

**Una sola restricción limita, y limita en todas las soluciones óptimas.** Mesadas está llena en
las 854 ternas óptimas (§3.7), y el test A.1 (§4.1) confirma que es el único espacio donde un lugar
más suma un combo. Mientras tanto, **12 de los 33 lugares (36 %) quedan libres**.

En lenguaje de negocio: con reposición mensual, la Sección Cocinas no está limitada por un
depósito chico en general, sino por **tres lugares de mesada**. El resto del depósito está en buena
parte ocioso.

### 3.7. ⚠ Hallazgo 2: la solución no es única — 854 ternas óptimas

Enumeración exhaustiva, sin solver (`06_optimos_alternativos.csv`):

```
Conjuntos de 3 combos que entran en el depósito :  854 de 1.140
Conjuntos de 4 combos que entran en el depósito :    0 de 4.845
```

Los dos números coinciden con los que el plan dedujo a mano en §7.2 (1.140 − 286 = 854).

**Distribución de las 854 ternas:**

| Unidades totales | Ternas | | Lugares en lavav. + cocinas | Ternas | | Categorías cubiertas | Ternas |
|---:|---:|---|---:|---:|---|---:|---:|
| 21 | 84 | | 3 | 35 | | 7 | 35 |
| 22 | 385 | | 4 | 273 | | 8 | **819** |
| 23 | 385 | | 5 (lleno) | 546 | | | |

- Con el desempate completo (8 categorías y 21 unidades) **siguen empatadas 49 ternas**. La que se
  presenta es una de ellas.
- **Las 35 ternas que cubren solo 7 categorías son exactamente las 35 que ocupan 3 lugares de
  lavavajillas + cocinas**: son las ternas formadas únicamente por combos 14 a 20, los que no traen
  lavavajillas. Es el problema que motivó §2.5.
- Lavavajillas + cocinas es el **único otro espacio que se llega a llenar**, y solo en 546 de las
  854 ternas: depende de la elección. Los otros cinco espacios no se llenan en ninguna.

**Consecuencia para el informe:** hay que presentar la terna 12 – 15 – 18 como **una solución
representativa**, no como "la" solución, y decir cuántas hay.

### 3.8. El desempate por categorías sale gratis

Conviene mostrarlo con números, porque es el argumento de §2.5:

| Criterio | Terna | Categorías | Unidades | Lugares libres |
|---|---|---:|---:|---:|
| Mínimo de unidades (plan) | 14 – 18 – 20 | 7 (sin lavavajillas) | 21 | 12 |
| **Categorías y después unidades (final)** | **12 – 15 – 18** | **8** | **21** | **12** |

Cubrir las 8 categorías **no cuesta ni un lugar de depósito**: cambia qué combos se ofrecen, no
cuánto ocupan. Lo único que se mueve es el reparto interno (un lugar más en lavavajillas + cocinas
y uno menos en empapelado).

### 3.9. Relajación lineal

| | Resultado |
|---|---|
| Cota de la relajación | **3,0000 combos** (igual a V\*) |
| Solución de la relajación | `y_15 = y_17 = y_20 = 1`: **ya es entera** |
| Precio sombra de mesadas | **1 combo por lugar** |
| Precio sombra del resto de los espacios | 0 |

Se confirma lo que esperaba el plan §6.4. Dos lecturas:

1. **La relajación es exacta en este caso.** Como la cota de las mesadas se obtiene sumando
   restricciones lineales, el PL relajado no la puede saltear, y CBC encontró un vértice entero.
   El Branch & Bound no tuvo nada que ramificar. **Eso no vale en general** para programación
   entera; es una propiedad de estos datos.
2. **El precio sombra de mesadas (1) coincide con la re-resolución del test A.1** (sumar un lugar
   de mesada da +1 combo). Acá el dual del PL relajado anticipó bien el efecto en el modelo entero,
   pero **eso se sabe porque se re-resolvió**, no porque el dual lo garantice.

---

### 3.10. Material gráfico para el informe

El material gráfico **lo generan los scripts**, no se dibuja a mano: si cambia un dato o un
supuesto, se regenera solo y no queda desfasado del texto.

| Archivo | Qué muestra | Lo genera |
|---|---|---|
| `resultados/graficos/01_ocupacion_deposito.png` | Ocupación y capacidad de cada espacio, en barras, con mesadas en color | `01_punto_a.py` |
| `docs/esquema_proceso.tex` | Esquema del proceso (depósito → stock → combos → variedad) en TikZ | a mano, compila con `pdflatex` |

**Se probaron dos formas para esta figura** —barras y mancuerna (un punto en lo ocupado, otro en
la capacidad y el segmento entre ambos como holgura)—. **Se eligió la de barras** y la alternativa
se descartó, así que el script genera una sola.

**Qué se descartó y por qué.** Hubo un segundo gráfico con los resultados de los tests A.1 y
A.2. Se eliminó: A.1 es "un espacio vale +1 y los otros seis valen 0" y A.2 es un barrido de
cuatro puntos. Dibujar seis ceros no agrega nada que la tabla no diga mejor, así que esos dos
tests van como tabla al informe (§4.1 y §4.2).

**Criterios de las figuras** (`src/graficos.py` los documenta en su encabezado):

- **Adentro de la figura van solo los datos.** Sin título, sin subtítulo y sin notas: eso es
  trabajo del epígrafe del informe, que además es donde el lector lo busca. La primera versión
  tenía título, subtítulo y una nota con flecha encima de las barras, y parecía una pantalla de
  tablero en vez de una figura de informe.
- **Tipografía serif**, del tamaño del cuerpo del texto, para que la figura no desentone con el
  LaTeX.
- **Forma de énfasis, no siete colores.** La historia del punto a) es un número —las mesadas—,
  así que el espacio que limita va en color y el resto en gris. Siete colores para siete
  espacios habrían repartido la atención en partes iguales entre lo que importa y lo que no.
- **Paleta validada, no elegida a ojo.** El azul `#2a78d6` pasa banda de luminosidad, piso de
  croma y contraste (>= 3:1 sobre la superficie `#fcfcfb`); el gris secundario mide 3,5:1.
- **La referencia de colores va debajo del eje**, en una sola fila: dentro del área de datos
  queda flotando y le roba espacio a las barras.

**Sobre el esquema en TikZ:** no usa los caracteres `<` ni `>` en ningún lado (las flechas se
declaran como `-{Stealth}` y las desigualdades con `\leq`). Con `babel` en español esos dos
caracteres son atajos de comillas y rompen la compilación — se descubrió compilando, no leyendo.
Necesita las librerías `positioning`, `arrows.meta`, `calc` y `decorations.pathreplacing`, y está
verificado con `pdflatex`.

---

## 4. Tests de supuestos

Corrida: `python scripts/02_tests_supuestos.py` · 10 controles en verde (§5.3).

### 4.1. Test A.1 — Un lugar más, un espacio por vez

| Espacio | Capacidad probada | V\* | ΔV\* |
|---|---:|---:|---:|
| Baldosas | 6 | 3 | 0 |
| Empapelado vinílico | 9 | 3 | 0 |
| Apliques de luz | 5 | 3 | 0 |
| Alacenas | 5 | 3 | 0 |
| **Mesadas** | **4** | **4** | **+1** |
| Bacha y grifería | 5 | 3 | 0 |
| Lavavajillas + cocinas | 6 | 3 | 0 |

Es el reemplazo del precio sombra en el modelo entero (plan §10.1): **un lugar de mesada vale un
combo; un lugar en cualquier otro espacio no vale nada** con el depósito actual.

### 4.2. Test A.2 — Barrido de mesadas: la cadena de cuellos de botella

| Mesadas | V\* | Espacios cuyo +1 suma un combo |
|---:|---:|---|
| 3 (actual) | 3 | Mesadas |
| 4 | 4 | ninguno por sí solo |
| 5 | 4 | ninguno por sí solo |
| 6 | 4 | ninguno por sí solo |

Confirma lo esperado en el plan §10.2. Con 4 mesadas, la variedad queda frenada en 4 por **apliques,
alacenas y bachas**: los tres tienen 4 lugares y todos los combos usan uno de cada uno (cota trivial
de 4, plan §3.6). **A partir de ahí ningún lugar extra aislado suma**: para pasar de 4 combos hay que
ampliar varios espacios a la vez. Qué combinación exacta conviene es material del inciso c).

### 4.3. Test B — S1: lectura exclusiva vs. compartida

| Lectura S1 | V\* | Óptimos alternativos | Factibles con V\*+1 | Categorías | Unidades |
|---|---:|---:|---:|---:|---:|
| **exclusiva (base)** | **3** | 854 | 0 | 8 | 21 |
| compartida | **13** | 4 | 0 | 8 | 27 |

Con la lectura compartida se ofrecen los combos 3, 4, 5, 7, 9, 10, 11, 12, 13, 14, 15, 16 y 17.

**Es, por lejos, el supuesto que más mueve el resultado: la variedad se multiplica por 4,3.** La
lectura compartida es la del inciso b) (reposición automática), así que este test **adelanta que b)
va a mostrar una mejora grande**. También refuerza la razón 2 del plan para elegir la lectura
exclusiva en a): si a) usara la compartida, a) y b) darían exactamente lo mismo.

Además sirve de control del cambio de §2.5: **el desempate nuevo funciona igual con la lectura de
b)**, sin perder variedad ni volver infactible nada.

### 4.4. Test C — S2: rollos de empapelado por combo

| Rollos por combo | V\* | Terna elegida | Combos con empapelado | Categorías |
|---:|---:|---|---:|---:|
| 1 (base) | 3 | 12 – 15 – 18 | 2 | 8 |
| 2 a 8 | 3 | 12 – 13 – 15 (o 12 – 13 – 18) | 1 | 8 |
| 9 | **2** | 12 – 13 | 0 | **7** |

La variedad **no cambia hasta 8 rollos por combo**; recién con 9 un combo con empapelado deja de
entrar en los 8 rollos del depósito. Como preveía el plan, los combos 12 y 13 (sin empapelado)
completan la terna. **S2 es irrelevante en cualquier rango razonable.**

La última fila es además la prueba de por qué el criterio de §2.5 es un objetivo y no una
restricción: con 9 rollos **ninguna** solución puede cubrir el empapelado, y el modelo lo informa
(7 categorías) en lugar de quedar infactible.

### 4.5. Test D — S3: criterio de desempate

| Criterio | V\* | Terna | Categorías | Unidades | Lugares lavav. + cocinas | Lugares libres |
|---|---:|---|---:|---:|---:|---:|
| **categorías y unidades (base)** | 3 | 12 – 15 – 18 | **8** | 21 | 4 | 12 |
| mínimo de unidades (plan) | 3 | 14 – 18 – 20 | 7 | 21 | 3 | 12 |
| máximo de artículos | 3 | 5 – 9 – 15 | 8 | 23 | 5 | 10 |
| ninguno (lo que elige el solver) | 3 | 15 – 17 – 20 | 7 | 21 | 3 | 12 |

- Los cuatro criterios **mantienen la variedad**: el desempate nunca le cuesta un combo a la
  sección.
- El criterio base **es el único que garantiza las 8 categorías al mínimo costo de espacio**:
  máximo de artículos también las cubre, pero ocupando 2 lugares más.
- **"Ninguno"** cayó, por casualidad, en una terna de 21 unidades. No hay nada en el modelo que lo
  garantice: con otro solver u otra versión de CBC podría devolver cualquiera de las 854.

### 4.6. Tabla resumen (plan §11.5 completa)

| Test | Base | Alternativa | V\* base | V\* alternativa | ¿Cambia la conclusión? |
|---|---|---|---:|---:|---|
| A.1 — capacidad +1 | depósito actual | +1 por espacio | 3 | 4 solo con mesadas | No: confirma que mesadas es el único cuello |
| A.2 — mesadas | 3 | 4 a 6 | 3 | 4 | No: después de 4 mesadas limitan apliques, alacenas y bachas |
| B — S1 | exclusiva | compartida | 3 | **13** | **Sí**: es la decisión de modelado más importante |
| C — S2 | 1 rollo | 1 a 9 rollos | 3 | 3 (hasta 8 rollos) | No |
| D — S3 | categorías y unidades | otros tres | 3 | 3 | No en la variedad; sí en qué combos se ofrecen |

---

## 5. Verificaciones realizadas

### 5.1. Datos — `00_verificar_datos.py`

**46 de 46 OK.** Cubre: cantidad de combos y artículos, que todo artículo de un combo exista en el
catálogo, que ningún combo repita categoría, qué combos no traen empapelado ni lavavajillas, las
**30 apariciones** de la tabla §3.4 del plan una por una, los lugares de lavavajillas + cocinas por
combo, la capacidad total y la cota trivial de cada espacio.

### 5.2. Controles cruzados del punto a) — `01_punto_a.py` §8

**9 de 9 OK:**

- V\* no supera la cota trivial de las mesadas.
- **La fuerza bruta coincide con el solver**: hay ternas factibles y ninguna cuaterna.
- El desempate no pierde variedad.
- El stock de la solución final es exactamente el necesario (sin sobrante).
- La ocupación respeta todas las capacidades.
- La terna final está entre las 854 enumeradas.
- La relajación lineal no queda por debajo de V\*.
- **Las dos etapas de desempate se verifican contra la enumeración**, que no usa el solver: sus 8
  categorías son el máximo entre las 854 ternas, y sus 21 unidades son el mínimo entre las que
  cubren 8 categorías.

### 5.3. Controles de los tests — `02_tests_supuestos.py`

**10 de 10 OK.** Son propiedades que cualquier resultado correcto tiene que cumplir:
- sumar capacidad nunca baja la variedad;
- la lectura compartida nunca da menos que la exclusiva;
- más rollos por combo nunca suben la variedad;
- ningún criterio de desempate pierde variedad;
- el criterio base cubre al menos tantas categorías como los otros tres;
- con 9 rollos el criterio base no vuelve infactible el modelo, resigna la categoría;
- en todos los escenarios se reproduce el caso base cuando corresponde.

### 5.4. Predicciones del plan contra resultados

La verificación más fuerte: **todo lo que el plan dedujo a mano antes de codificar se confirmó.**

| Predicción del plan | Sección | Resultado |
|---|---|---|
| V\* = 3 | §7.1 | ✔ 3 |
| 854 ternas óptimas | §7.2 | ✔ 854 |
| Ninguna cuaterna factible | §8 | ✔ 0 de 4.845 |
| 84 ternas con el mínimo de unidades (21) | §7.2 | ✔ 84 (49 si además se piden las 8 categorías) |
| El solver puede dejar stock sobrante | §4.1 S3 | ✔ dejó 12 unidades de más |
| Relajación: cota 3, dual de mesadas 1 | §6.4 | ✔ |
| +1 lugar: solo mesadas suma | §10.1 | ✔ |
| 4 mesadas → 4 combos; 5 mesadas → sigue en 4 | §10.2 | ✔ |
| Lectura compartida → 13 combos | §4.1 S1 | ✔ 13 |
| Rollos de empapelado: no cambia hasta valores absurdos | §4.1 S2 | ✔ recién cae con 9 |

Dos cosas que el plan **no** anticipó: el problema de reporte de la relajación (§2.1) y que el
desempate por mínimo de unidades dejaría la sección sin lavavajillas (§2.5).

---

## 6. Conclusiones para el informe

1. **Con reposición mensual, la Sección Cocinas puede ofrecer 3 de sus 20 combos (15 %).** Es un
   resultado demostrable a mano: todos los combos llevan una mesada y hay 3 lugares.
2. **Plan de stock presentado:** combos 12, 15 y 18; 21 unidades de 17 artículos (tabla §3.4), con
   las 8 categorías del catálogo representadas.
3. **El único cuello de botella son las mesadas.** Limitan en todas las soluciones óptimas, un lugar
   más de mesada suma un combo y un lugar más en cualquier otro espacio no suma nada. Mientras
   tanto, **12 de los 33 lugares quedan libres**.
4. **La solución no es única: hay 854 ternas óptimas** (49 después del desempate completo). Hay que
   presentarla como representativa.
5. **Resolver solo la variedad da una respuesta de stock equivocada**: el solver llena el depósito
   con 12 unidades que no usa ningún combo. Las etapas de desempate son necesarias, no un adorno.
6. **La lectura de "disponible" (S1) es la decisión que más pesa**: 3 combos contra 13. Se adopta la
   reserva exclusiva y se defiende en el informe con los argumentos del plan §4.1 más el test B.
7. **Cubrir las 8 categorías del catálogo no cuesta espacio** (§3.8): es un criterio de desempate
   que mejora la oferta sin resignar variedad ni lugares.

---

## 7. Resultados del punto b)

Corrida: `python scripts/03_punto_b.py` · estado **Optimal** en las etapas y en la enumeración.
Sigue al pie de la letra la guía que el plan había dejado en §17.1: **mismo modelo de a)**, con
`S1_disponibilidad="compartida"` en vez de `"exclusiva"`. No hizo falta tocar `src/`.

### 7.1. Variedad máxima: 13 combos de 20 (contra 3 en a)

**V\* = 13**, el **65 % del catálogo**, frente al 15 % de a). Con reposición automática, lo que se
vende vuelve enseguida, así que alcanza con **una unidad de cada artículo** para que un combo esté
disponible: la restricción de cobertura R1 pasa de `x_p ≥ Σ u·y_c` a `x_p ≥ u·y_c` por cada combo
que usa `p` (una restricción por par artículo–combo en vez de una por artículo). Coincide
exactamente con lo que había anticipado el test B del punto a) (procedimiento §4.3).

### 7.2. La solución que se presenta (mismo desempate S3 que a)

Con `categorias_y_unidades`, quedan **13 combos y las 8 categorías cubiertas**, sin cambiar el
criterio de desempate del punto a):

**Combos ofrecidos:** 3, 4, 5, 7, 9, 10, 11, 12, 13, 14, 15, 16 y 17 — **27 unidades en stock**.

### 7.3. Plan de stock — una unidad por artículo usado

Bajo la lectura compartida, cada artículo que aparece en algún combo ofrecido necesita **exactamente
1 unidad**, sin importar en cuántos combos aparezca (`resultados/tablas/15_plan_stock_b.csv`).
**27 de los 30 artículos** quedan con stock (en cero: **A4, M4 y C4** — los tres artículos que no
usa ningún combo de los 13 elegidos). Es la otra lectura posible de "variedad de oferta" que pide la
consigna:
no solo combos, también **artículos distintos disponibles en el depósito**.

### 7.4. Ocupación del depósito — ahora limitan cuatro espacios a la vez

| Espacio | Capacidad | Ocupado | Holgura | Limita |
|---|---:|---:|---:|:---:|
| Baldosas | 5 | 4 | 1 | No |
| Empapelado vinílico | 8 | 4 | 4 | No |
| **Apliques de luz** | **4** | **4** | **0** | **Sí** |
| Alacenas | 4 | 3 | 1 | No |
| **Mesadas** | **3** | **3** | **0** | **Sí** |
| **Bacha y grifería** | **4** | **4** | **0** | **Sí** |
| **Lavavajillas + cocinas** | **5** | **5** | **0** | **Sí** |
| **Total** | **33** | **27** | **6** | |

### 7.5. ⚠ Hallazgo: bajo b) lo que limita no es "cuántos combos entran" sino "cuántas variantes"

Bajo la lectura compartida, la capacidad de cada espacio deja de acotar una cantidad de *combos* y
pasa a acotar una cantidad de **variantes distintas** de esa categoría (cada variante cuesta 1 lugar
una sola vez, la usen uno o diez combos). Eso separa los siete espacios en dos grupos, y explica por
qué cuatro aparecen "llenos" en la tabla anterior sin que eso signifique lo mismo en los cuatro:

| Espacio | Capacidad | Variantes que existen | ¿Puede limitar? |
|---|---:|---:|---|
| Baldosas | 5 | 4 (B1–B4) | No: sobra lugar aunque se usen todas |
| Empapelado | 8 | 4 (E1–E4) | No |
| Apliques de luz | 4 | 4 (L1–L4) | No: la capacidad **alcanza justo** para las 4, nunca sobra ni falta |
| Alacenas | 4 | 4 (A1–A4) | No: mismo caso que apliques |
| **Mesadas** | **3** | **4 (M1–M4)** | **Sí: sobra una variante afuera** |
| Bacha y grifería | 4 | 4 (G1–G4) | No: mismo caso que apliques |
| **Lavavajillas + cocinas** | **5** | **6 (W1–W2, C1–C4)** | **Sí: sobra una variante afuera** |

Apliques y bacha "limitan" en la tabla de ocupación (holgura 0) pero es una coincidencia: sus
capacidades son exactamente el número de variantes que existen, así que **nunca pudieron sobrar
lugares y nunca van a excluir un combo por sí solos**. Los dos cuellos de botella reales son
**mesadas** (3 lugares para 4 variantes) y **lavavajillas + cocinas** (5 para 6). El test de
capacidad +1 de §7.6 lo confirma con números.

### 7.6. Capacidad +1 por espacio, bajo b)

| Espacio | Capacidad probada | V\* | ΔV\* |
|---|---:|---:|---:|
| Baldosas | 6 | 13 | 0 |
| Empapelado vinílico | 9 | 13 | 0 |
| Apliques de luz | 5 | 13 | 0 |
| Alacenas | 5 | 13 | 0 |
| **Mesadas** | **4** | **16** | **+3** |
| Bacha y grifería | 5 | 13 | 0 |
| **Lavavajillas + cocinas** | **6** | **15** | **+2** |

Confirma §7.5: solo mesadas y lavavajillas + cocinas suman, y suman **de a varios combos por
lugar** (no de a uno, como en a), porque liberar la variante que faltaba habilita de golpe a todos
los combos que la usaban. Con mesadas en 4 (las 4 variantes disponibles) deja de limitar del todo;
el cuello de botella que queda es lavavajillas + cocinas, exactamente el que el plan §17.2 había
anticipado como el freno del inciso c).

### 7.7. Óptimos alternativos: 4 (contra 854 en a)

Enumeración exhaustiva, sin solver (`17_optimos_alternativos_b.csv`):

```
Conjuntos de 13 combos que entran :   4 de 77.520
Conjuntos de 14 combos que entran :   0 de 38.760
```

Los cuatro llenan siempre apliques (4/4), mesadas (3/3), bacha y grifería (4/4) y lavavajillas +
cocinas (5/5) — son los espacios de §7.5 sin margen —, y usan 27 o 28 unidades según si además
llenan alacenas (4/4) o dejan una variante afuera (3/4). **La solución deja de ser tan degenerada
como en a)**: pasar de reserva exclusiva a compartida no solo sube la variedad, también **reduce
drásticamente los empates** (854 → 4), porque bajo la lectura compartida hay mucho menos margen
para "sobrar" stock sin usar.

### 7.8. ¿Se beneficia la variedad de oferta? — respuesta con las dos lecturas

| Métrica | a) exclusiva | b) compartida | Δ |
|---|---:|---:|---:|
| Combos ofrecidos | 3 | **13** | +10 |
| Artículos distintos en stock | 17 | **27** | +10 |
| Unidades totales en stock | 21 | 27 | +6 |
| Categorías del catálogo cubiertas | 8 | 8 | 0 |

**Sí, la variedad de oferta se ve claramente beneficiada**, se la lea como combos disponibles o
como artículos distintos en el depósito: las dos métricas más que se cuadruplican y cuadriplican
respectivamente. Tiene sentido con la razón 2 del supuesto S1 (plan §4.1): la lectura compartida
**es** el escenario de reposición automática, así que a) y b) muestran la diferencia real entre
reponer una vez al mes y reponer al instante. La contracara es que también sube el stock necesario
(21 → 27 unidades) y, sobre todo, el depósito pasa de tener un solo cuello de botella a tener dos
(§7.5): sigue habiendo margen para vender más si se resuelve **lavavajillas + cocinas**, que es
justamente lo que plantea el inciso c).

### 7.9. Controles cruzados — 8 de 8 OK

`scripts/03_punto_b.py` corre 8 controles automáticos: V\*(b) ≥ V\*(a), la fuerza bruta coincide con
el solver (hay ternas... en este caso conjuntos de 13 que entran y ninguno de 14), el desempate no
pierde variedad, el stock de la solución final es exactamente el necesario, la ocupación respeta
las capacidades, la solución final está entre los óptimos enumerados, sumar capacidad nunca baja la
variedad, y los artículos distintos en stock de b) son ≥ los de a). Los 8 dan **OK**.

### 7.10. Conclusiones del punto b) para el informe

1. **La variedad de oferta se beneficia mucho con la reposición automática**: 3 → 13 combos (15 % →
   65 % del catálogo) y 17 → 27 artículos distintos en stock.
2. **El mecanismo es el supuesto S1**: alcanza con una unidad de cada artículo en vez de una reserva
   por combo, así que un mismo artículo sirve para varios combos a la vez.
3. **El cuello de botella deja de ser uno solo.** Bajo reposición automática, lo que limita cada
   espacio no es la cantidad de combos sino la cantidad de **variantes** de esa categoría; con eso,
   **mesadas** (3 lugares para 4 variantes) y **lavavajillas + cocinas** (5 para 6) son los dos
   espacios que de verdad acotan, y los otros cinco tienen exactamente tantos lugares como variantes
   existen (nunca van a limitar, aunque queden "llenos").
4. **La solución es casi única**: 4 óptimos alternativos contra 854 en a). Reponer rápido no solo
   da más variedad, también deja mucho menos margen de elección entre planes de stock equivalentes.
5. **De cara al inciso c)**, que parte de este mismo escenario: liberar mesadas (capacidad 4) saca
   ese cuello de botella por completo; el que queda —y el que c) va a tener que resolver— es
   **lavavajillas + cocinas**.

---

## 8. Resultados del punto c)

Corrida: `python scripts/04_punto_c.py` · estado **Optimal** en las etapas y en la enumeración.
Sigue la guía del plan §17.2: parte del escenario de b) (`S1_disponibilidad="compartida"`) y funde
mesadas y alacenas en un único espacio de 12 lugares.

### 8.1. El único cambio de código: `espacios` como argumento de `construir_params`

Tal como preveía el plan, fue el único punto que tocó `src/`. `config.construir_params` ahora acepta
un argumento `espacios` que reemplaza `ESPACIOS` por completo (§17.2 daba el fragmento casi textual);
`capacidades` se sigue aplicando encima, por si hace falta combinar los dos. El resto del código
—restricciones, cotas triviales, ocupación, reportes, gráficos— recorre `params["espacios"]` de
forma genérica y **no necesitó ningún cambio**, confirmando lo que anticipaba la nota de
implementación del plan §7.

```python
def espacios_mesadas_alacenas_juntas(capacidad=12):
    espacios = deepcopy(config.ESPACIOS)
    del espacios["mesadas"], espacios["alacenas"]
    espacios["mesadas_alacenas"] = {
        "nombre": "Mesadas + alacenas",
        "categorias": ("M", "A"),
        "capacidad": capacidad,
    }
    return espacios

params_c = construir_params(espacios=espacios_mesadas_alacenas_juntas(), S1_disponibilidad="compartida")
```

### 8.2. Variedad máxima: 16 combos de 20 (contra 13 en b)

**V\* = 16**, el **80 % del catálogo**. Mesadas y alacenas juntas **dejan de limitar por completo**:
el espacio nuevo tiene 12 lugares para, como mucho, 8 variantes (4 de mesada + 4 de alacena), así que
nunca puede quedarse sin lugar bajo la lectura compartida (holgura 4 en la solución final, §8.4).

**Confirma exactamente la cuenta a mano del plan §17.2**: quedan afuera los 4 combos que llevan
**C4** (cocina a gas negra) — los combos **6, 8, 19 y 20** —, porque **lavavajillas + cocinas sigue
teniendo 6 variantes para 5 lugares** y es la única restricción real que le queda al modelo bajo
esta disposición (mismo hallazgo del punto b), §7.5, que ya lo adelantaba).

### 8.3. La solución que se presenta

Con el mismo desempate S3 de a) y b) (`categorias_y_unidades`): **16 combos, 8 categorías cubiertas,
29 unidades en stock**. Bajo la lectura compartida cada artículo necesita como mucho 1 unidad
(§7.3), así que las 29 unidades son **29 de los 30 artículos con exactamente 1 unidad cada uno**
(`21_plan_stock_c.csv`). El único artículo en cero es **C4**: es justo el que se resigna para no
superar los 5 lugares de lavavajillas + cocinas.

**Combos ofrecidos:** 1, 2, 3, 4, 5, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17 y 18.
**Combos que no quedan disponibles:** 6, 8, 19 y 20.

### 8.4. Ocupación del depósito bajo c)

| Espacio | Capacidad | Ocupado | Holgura | Limita |
|---|---:|---:|---:|:---:|
| Baldosas | 5 | 4 | 1 | No |
| Empapelado vinílico | 8 | 4 | 4 | No |
| Apliques de luz | 4 | 4 | 0 | Sí* |
| Bacha y grifería | 4 | 4 | 0 | Sí* |
| **Lavavajillas + cocinas** | **5** | **5** | **0** | **Sí** |
| **Mesadas + alacenas** | **12** | **8** | **4** | **No** |
| **Total** | **38** | **29** | **9** | |

\* Igual que en b) (§7.5): apliques y bacha "limitan" solo porque su capacidad coincide con el número
de variantes que existen (4 de cada una); nunca van a excluir un combo por sí solos. El único cuello
de botella real que le queda al modelo es **lavavajillas + cocinas**.

### 8.5. ¿Qué otras unidades de almacenamiento deberían solicitarse?

Test de capacidad +1 por espacio, bajo c) (`24_test_capacidad_mas_uno_c.csv`):

| Espacio | Capacidad probada | V\* | ΔV\* |
|---|---:|---:|---:|
| Baldosas | 6 | 16 | 0 |
| Empapelado vinílico | 9 | 16 | 0 |
| Apliques de luz | 5 | 16 | 0 |
| Bacha y grifería | 5 | 16 | 0 |
| **Lavavajillas + cocinas** | **6** | **20** | **+4** |
| Mesadas + alacenas | 13 | 16 | 0 |

**Un solo lugar más en lavavajillas + cocinas alcanza para completar los 20 combos**: recupera de
golpe los 4 combos que llevan C4, porque las 6 variantes de esa categoría vuelven a entrar todas
juntas. Ningún otro espacio pide ampliación: mesadas + alacenas ya sobra (4 lugares libres) y los
demás no mueven la variedad aunque se les sume capacidad.

### 8.6. ¿Conviene la nueva disposición física?

**Sí, conviene, y por bastante**: sin tocar el depósito lavavajillas + cocinas (el único espacio que
no cambia de disposición), pasar mesadas y alacenas a un espacio compartido de 12 lugares sube la
variedad de 13 a 16 combos (+ 23 %) **sin pedir un solo lugar extra**, porque el espacio nuevo le
sobra desde el primer momento (8 variantes posibles contra 12 lugares). La reubicación es, en los
hechos, gratis.

**No alcanza para completar el catálogo por sí sola.** El freno que queda no es de disposición sino
de capacidad: **lavavajillas + cocinas** sigue teniendo 6 variantes para 5 lugares, y es el único
espacio de los seis que hoy no tiene margen. La recomendación concreta para el informe es pedir
**un lugar más en lavavajillas + cocinas** (de 5 a 6): con eso —y sin ningún otro cambio— la
Sección Cocinas puede ofrecer sus 20 combos completos.

### 8.7. Óptimos alternativos: uno solo

Enumeración exhaustiva, sin solver (`23_optimos_alternativos_c.csv`): de las `comb(20,16) = 4.845`
combinaciones de 16 combos, **una sola entra en el depósito**, y es exactamente la que reporta el
solver. Tiene sentido: al quedar solo lavavajillas + cocinas como restricción activa, la única forma
de armar 16 combos es tomar los 16 que no usan C4 — no hay margen para elegir ningún otro conjunto.
**La solución deja de ser degenerada del todo** (854 en a) → 4 en b) → 1 en c)): cuantas menos
restricciones activas quedan, menos formas hay de armar la misma variedad.

### 8.8. Controles cruzados — 8 de 8 OK

`scripts/04_punto_c.py` corre 8 controles automáticos: V\*(c) ≥ V\*(b), la fuerza bruta coincide con
el solver, el desempate no pierde variedad, el stock de la solución final es exactamente el
necesario, la ocupación respeta las capacidades, la solución final está entre los óptimos
enumerados, sumar capacidad nunca baja la variedad, y mesadas + alacenas queda con holgura positiva
(nunca limita, como predecía §8.2). Los 8 dan **OK**.

### 8.9. Conclusiones del punto c) para el informe

1. **La nueva disposición conviene**: variedad 13 → 16 combos (+ 23 %) sin pedir más lugar en
   ningún espacio, porque mesadas y alacenas juntas (12 lugares para 8 variantes posibles) dejan de
   ser un cuello de botella por completo.
2. **No alcanza para ofrecer el catálogo completo.** Quedan afuera los 4 combos con cocina C4 (6, 8,
   19 y 20), porque lavavajillas + cocinas sigue en 6 variantes para 5 lugares.
3. **Recomendación concreta:** pedir **un lugar más en lavavajillas + cocinas**. Es la única unidad
   de almacenamiento que hace falta solicitar; con eso se completan los 20 combos (confirmado con el
   test de capacidad +1, §8.5).
4. **La solución deja de tener óptimos alternativos**: de 854 (a) a 4 (b) a **1 (c)**. Cuando queda
   una sola restricción activa en todo el modelo, la solución óptima es única.
5. **Hilo conductor de los tres incisos:** cada escenario retira una restricción (primero la reserva
   exclusiva de a), después el espacio separado de mesadas y alacenas) y en los tres casos
   **lavavajillas + cocinas termina siendo lo último que limita**. Es el espacio que, si la cátedra
   preguntara "¿y después?", habría que ampliar primero.

---

## 9. Pendientes

**El checklist completo del trabajo está en [`plan_de_trabajo.md`](plan_de_trabajo.md) §16.**

**Los puntos a), b) y c) están completos**, incluido el material gráfico de cada uno (§3.10,
`02_ocupacion_deposito_b.png` y `03_ocupacion_deposito_c.png`). De acá en adelante queda solo la
redacción del informe (bibliografía y estructura: plan §0 y §16).
