# TP1 Optimización — "Portafolio de Productos Pastarazzi"

Modelo de programación lineal para asignar los **$17.000 millones** de presupuesto de
marketing de Pastarazzi entre sus cinco marcas de pasta seca.

Investigación de Operaciones I · UCA · 2026 2C

---

## ⚡ Si recién llegás, leé esto primero

**Orden de lectura obligatorio.** Saltearse el paso 2 es el error más fácil de cometer:

| # | Archivo | Por qué |
|---|---|---|
| 0 | [`docs/guia-rapida.md`](docs/guia-rapida.md) | Resumen sin tecnicismos: qué es el problema, qué se hizo y qué falta. 5 minutos |
| 1 | [`docs/plan_de_trabajo.md`](docs/plan_de_trabajo.md) | El problema, los datos, los supuestos y el modelo. Empezá por **§0** (aclara una trampa de la consigna) |
| 2 | [`docs/procedimiento.md`](docs/procedimiento.md) **§2** | **Los desvíos respecto del plan.** El plan quedó desactualizado en cuatro secciones y la corrección vive acá |
| 3 | [`docs/procedimiento.md`](docs/procedimiento.md) §3 y §5 | Los resultados obtenidos y las llamadas exactas para lo que falta |

> ⚠️ **El plan NO se corrige.** Es a propósito: el contraste entre lo que planeamos y lo que
> pasó es material para el informe (criterio "Analizar" de la cátedra). Todo cambio se anota
> en `docs/procedimiento.md` §2, nunca reescribiendo el plan.

---

## Los dos documentos

| | [`docs/plan_de_trabajo.md`](docs/plan_de_trabajo.md) | [`docs/procedimiento.md`](docs/procedimiento.md) |
|---|---|---|
| **Qué es** | El **esquema**: lo que pensamos hacer | La **bitácora**: lo que efectivamente pasó |
| **Cuándo se escribió** | Antes de codificar | Durante y después de codificar |
| **Contiene** | Datos, 9 supuestos justificados, función objetivo, 9 restricciones, protocolo de tests, guía de las 4 preguntas | Estructura del código, desvíos, resultados, verificaciones, conclusiones |
| **¿Se modifica?** | Solo si cambia una decisión de modelado | Permanentemente, es un log |

**Secciones que más se consultan del plan:** §0 (las dos listas a-d de la consigna), §4 (los
supuestos), §6 (la función objetivo explícita), §7 (las restricciones), §12 (guía de las 4
preguntas).

---

## Cómo correrlo

Requiere Python 3.10+. Los scripts resuelven la raíz del proyecto solos, así que se pueden
ejecutar desde cualquier carpeta.

```bash
cd "C:\Users\Leandro\Desktop\Ciencia de datos\3_anio\Optimizacion\TP1_OPT"

pip install -r requirements.txt      # solo la primera vez

python scripts/00_verificar_datos.py # 31 asserts contra los números calculados a mano
python scripts/01_modelo_base.py     # resuelve el punto a) e imprime todo
python scripts/02_pregunta_b.py      # pregunta b): barrido de la paridad Don Carlo/Agnellis
python scripts/03_pregunta_c.py      # pregunta c): fronteras de Pareto por escenario
python scripts/04_pregunta_d.py      # pregunta d): piso mínimo de Triguetti
python scripts/05_tests_supuestos.py # tests ±30 % (tornado) + escenarios estructurales
```

**Corré siempre `00` antes que `01`.** Verifica que las tablas derivadas (mercado,
facturación base, coeficientes del funcional) coincidan con los valores calculados a mano.
Un share mal tipeado produce un óptimo perfectamente plausible y completamente equivocado;
esos asserts lo detectan al instante.

Salidas: por consola, 13 CSVs en [`resultados/tablas/`](resultados/tablas/) y los
gráficos en [`resultados/graficos/`](resultados/graficos/). El informe final, ya redactado
con estos resultados, está en [`informe/informe.tex`](informe/informe.tex)
(compilado en `informe/informe.pdf`).

---

## Estructura

```
TP1_OPT/
├── README.md                     este archivo (el único .md de la raíz)
├── requirements.txt
│
├── docs/
│   ├── guia-rapida.md            el resumen sin tecnicismos
│   ├── plan_de_trabajo.md        el esquema (lo que se planeó)
│   └── procedimiento.md          la bitácora (lo que pasó)
│
├── Consigna/                     el enunciado del TP
├── Material/                     clases 1, 2 y 3 de la cátedra
│
├── src/
│   ├── config.py                 datos del enunciado + supuestos S1..S9 + reglas
│   ├── datos.py                  tablas derivadas (mercado, base, coeficientes, cupos)
│   ├── modelo.py                 construcción y resolución del LP
│   ├── reportes.py               tablas de salida
│   └── graficos.py               gráficos (matplotlib) para el informe
│
├── scripts/
│   ├── 00_verificar_datos.py     verificación de datos (correr primero)
│   ├── 01_modelo_base.py         punto a): plan de asignación
│   ├── 02_pregunta_b.py          pregunta b): escenarios de Agnellis
│   ├── 03_pregunta_c.py          pregunta c): market share vs. rentabilidad
│   ├── 04_pregunta_d.py          pregunta d): piso mínimo de Triguetti
│   └── 05_tests_supuestos.py     tests ±30 % (tornado) + escenarios estructurales
│
├── resultados/
│   ├── tablas/                   CSVs generados
│   └── graficos/                 PNGs generados
│
└── informe/
    ├── informe.tex                informe final (LaTeX)
    └── informe.pdf                informe final compilado — el entregable
```

**Regla de oro de `config.py`:** están separados los **datos del enunciado** (no se tocan) de
los **supuestos propios** (S1..S9, con su justificación en el comentario). Esa distinción es lo
que se defiende ante la cátedra.

---

## Estado del trabajo

### ✅ Hecho — Punto a) del caso / ítem a) del informe

Modelo formalizado, codificado y resuelto con los tres funcionales. Resultados verificados.

**Plan óptimo:** Don Carlo $850MM · Agnellis $850MM · Triguetti $5.100MM · **Candealix $0** ·
Rena Speziale $10.200MM
**Utilidad neta:** $76.578,60MM · **Market share:** 48,10 % → 61,91 %

Tres hallazgos que van al informe:

1. **Las reglas del directorio obligan a quemar $1.630MM** (9,59 % del presupuesto) sin captar
   un solo cliente. El segmento alto se satura con $8.570MM en Rena, pero R4 exige $10.200MM.
2. **Los tres objetivos dan el mismo plan.** La frontera de Pareto colapsa en un punto: bajo
   las reglas actuales no hay conflicto entre accionistas y directivos que resolver.
3. **R3 (el 30 % de Triguetti) es la restricción más cara**: −$2,49 de utilidad por millón,
   por el arrastre de R4.

Detalle completo en [`docs/procedimiento.md`](docs/procedimiento.md) §3.

### ✅ Hecho — Pregunta b) del caso (escenarios de Agnellis)

`x_DonCarlo = x_Agnellis` (S6) generalizado a `x_DonCarlo = k · x_Agnellis`,
barriendo k de 1,0 a 0,0 con el mismo modelo (`scripts/02_pregunta_b.py`).

**Hallazgo:** soltar del todo la paridad vale **+0,80 % de utilidad**
(+$609,88MM). Y le cuesta a Don Carlo mucho menos presencia de lo que parece:
medida sobre el mercado real (base instalada + campaña) cae solo **3,2 puntos**;
lo que se derrumba (44,4 → 0) es la presencia *dentro de la campaña de este año*,
que es una métrica engañosa porque Don Carlo ya tiene 7,5 millones de clientes y
la campaña entera mueve 340.000.

**Conclusión:** ni mantener la paridad ni romperla mueve la aguja. Se puede
relajar para acompañar a Agnellis sin poner en riesgo real a Don Carlo.
Detalle en [`docs/procedimiento.md`](docs/procedimiento.md) §5.1.

### ✅ Hecho — Pregunta c) del caso (market share vs. rentabilidad)

ε-constraint (`Max utilidad s.a. facturación >= ε`) barrido en cuatro escenarios,
porque con las reglas vigentes la frontera colapsa en un punto y no hay nada que
barrer (`scripts/03_pregunta_c.py`).

**Hallazgo principal: el plan vigente está _dominado_, no es la opción prudente.**
Queda abajo y a la izquierda de las tres curvas: levantando R3 y R4 la empresa gana
**+3,6 puntos de share y +$3.675MM de utilidad a la vez**. Las reglas del directorio
no están comprando una cosa a cambio de la otra, están dejando las dos sobre la mesa.

**Y el trade-off real, cuando aparece, es chico:** como máximo 1,18 puntos de
participación negociables (sin R4), a un costo que arranca en $529MM por punto y
salta a $3.365MM en el último tramo, cuando hay que empujar a Rena contra el techo
del segmento alto ya saturado. Detalle en [`docs/procedimiento.md`](docs/procedimiento.md) §5.2.


### ✅ Hecho — Pregunta d) del caso (el 30 % obligatorio en Triguetti)

Descomposición a mano del precio sombra de R3 (95 % del costo es el arrastre de
R4 sobre Rena, no Triguetti en sí) más un barrido del piso (0–40 %)
(`scripts/04_pregunta_d.py`).

**Hallazgo no previsto en el plan:** arriba del **33,33 %** (=1/3) el modelo da
directamente **Infeasible** — R3 y R4 combinadas exigen más presupuesto del que
existe, deducible a mano sin correr el solver. La regla vigente del 30 % está a
solo 3,3 puntos de ese límite. Detalle en [`docs/procedimiento.md`](docs/procedimiento.md) §5.3.

### ✅ Hecho — Tests de supuestos (±30 %, tornado, escenarios estructurales)

Barrido OAT sobre los 14 parámetros numéricos (S1-S4, R10) más 4 escenarios
estructurales (S5, S7a, S7b, S8) (`scripts/05_tests_supuestos.py`).

**Hallazgo:** de 14 parámetros, **uno solo** cambia el plan óptimo dentro de
±30 %, y en un caso límite (R5, cuyo −30 % teórico resultó infactible porque
pisa el share ya instalado). El plan del punto a) no depende de forma frágil
de los datos que había que completar. Detalle en
[`docs/procedimiento.md`](docs/procedimiento.md) §4.

### ✅ Hecho — Informe final

Redactado en [`informe/informe.tex`](informe/informe.tex) y compilado a
`informe/informe.pdf`: cubre las 4 secciones del informe esperable por la
cátedra (modelo, sensibilidad, esquema del proceso con diagrama en TikZ,
librerías) y las 4 consultas del caso, con las tablas y los 6 gráficos de
`resultados/`. Es el documento que se entrega.

---

## ⚠️ Trampas conocidas

**1. La consigna tiene dos listas a) b) c) d) distintas.**
Página 1 = estructura del informe. Página 4 = preguntas a responder. No son lo mismo.
Ver plan §0. Cuando hables de "el punto 2", aclará de cuál lista.

**2. Cuatro secciones del plan quedaron desactualizadas** por el hallazgo de R10
(ver `docs/procedimiento.md` §2.1). El modelo real es el que está en `src/`, no el del plan:

| Sección del plan | Qué le falta |
|---|---|
| **§5.2** Variables por tramo | No tiene el tramo de **desperdicio** (tasa 0, sin tope) que lleva cada marca |
| **§7** Tabla de restricciones | Llega hasta R9. **Falta R10**, la saturación física por segmento |
| **§11** Protocolo de tests | No incluye `R10_tope_saturacion` entre los parámetros a barrer. **Hay que agregarlo** (60 %, 70 %, 80 %, 100 %): el segmento alto queda saturado, así que ese techo mueve mucho el resultado |
| **§12.c** Frontera de Pareto | Asume que hay una curva que trazar. Con las reglas actuales **colapsa en un punto**. Ya resuelto barriendo cuatro escenarios en vez de uno — ver `docs/procedimiento.md` §5.2 |

**3. Hay una restricción que no está en el enunciado: R10.**
El enunciado pone un techo de participación solo para la gama baja (el 65 %). Sin un techo
para los demás segmentos, el modelo captaba **más clientes de los que existen** (share del
123 % en el segmento alto). R10 lo corrige. Es un agregado nuestro y hay que declararlo en el
informe.

**4. `R10_tope_saturacion = 1.00` sigue siendo comercialmente absurdo.**
Implica que Pastarazzi se queda con *todos* los clientes premium del país. Es la cota física,
no la comercial. Está parametrizado justamente para barrerlo.

**5. Tolerancia numérica.**
CBC devuelve las variables con ~7 cifras significativas. Sobre valores del orden de $10.000MM
eso arrastra errores de hasta 1e-4, así que comparar con tolerancia 1e-6 marca como violadas
restricciones que se cumplen. La tolerancia del proyecto es **1e-3 $MM**.

---

## Cómo agregar una corrida nueva

**No copies el modelo.** Todo se resuelve con una sola función parametrizada:

```python
from src.config import construir_params
from src import modelo, reportes

params = construir_params()                      # caso base
res = modelo.resolver(params, objetivo="neta")   # "neta" | "oper" | "facturacion"

print(res["Z"], res["x"], res["duales"]["R3_triguetti_min"])
```

Las tres variaciones que necesitan las preguntas que faltan:

```python
# b) Agnellis crece más que Don Carlo
construir_params(S6_paridad_dc_ag=0.5)           # x_DC = 0,5 · x_AG
modelo.resolver(params, desactivar=["R2_paridad"])

# c) frontera de Pareto (ε-constraint)
modelo.resolver(params, epsilon=1_020_000)
# OJO: la facturación máxima alcanzable con las reglas actuales es 1.025.920.
# Un epsilon mayor devuelve status "Infeasible", y uno menor no ata nada (el
# óptimo de utilidad ya alcanza esa facturación máxima). Es la misma conclusión
# del hallazgo 2: para que el ε-constraint sirva hay que relajar R3 y R4 primero.

# d) sin la regla del 30 % de Triguetti
modelo.resolver(params, desactivar=["R3_triguetti_min"])
construir_params(R3_pct_triguetti=0.10)          # o barriendo el porcentaje

# tests de supuestos
construir_params(S1_tasa_triguetti=140)          # ±30 %
construir_params(R10_tope_saturacion=0.70)
```

**Tanto `construir_params()` como `desactivar` fallan con `KeyError` si el nombre no
existe.** Es deliberado: un typo silencioso es el peor error posible acá, porque
`desactivar=["R3_triguetti"]` (sin el `_min`) devolvería el caso base **haciéndose pasar por
el contrafactual**, y la conclusión de la pregunta d) saldría al revés.

Nombres válidos: los de `config.SUPUESTOS` y `config.REGLAS` para los parámetros; las claves
de `modelo.DESCRIPCION` para las restricciones desactivables.

---

## Verificaciones vigentes

Cualquier cambio al modelo tiene que seguir pasando estas cuatro:

1. **31 asserts de datos** — `python scripts/00_verificar_datos.py`
2. **7 cotas deducidas a mano** — las imprime `01_modelo_base.py` en su sección 1
3. **Los 5 precios sombra reconstruidos con aritmética de servilleta** coinciden a cinco
   decimales (`docs/procedimiento.md` §6.3). Es la verificación más fuerte que tenemos: si un dual
   deja de cerrar, el modelo dejó de decir lo que creemos que dice.
4. **R6 (umbral de Candealix) no está activa** — 43,7 millones de paquetes contra un umbral de
   2,5 millones

---

## Bibliografía

- Hillier, F. S. y Lieberman, G. J. — *Introducción a la Investigación de Operaciones*, 9ª ed.
  Cap. 1 y 3 (introducción a la PL), Cap. 6 (dualidad y análisis de sensibilidad).
- Material de la cátedra: [`Material/`](Material/) — Clases 1, 2 y 3.
