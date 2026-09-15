# Qué estamos haciendo, explicado fácil

*(Este archivo es el resumen en criollo. El [`README.md`](../README.md) es el técnico.)*

---

## El problema

Hay una fábrica de fideos, **Pastarazzi**, con cinco marcas:

| Marca | Qué es |
|---|---|
| Don Carlo | la barata de toda la vida, la que más vende |
| Agnellis | parecida a Don Carlo pero un poco más cara |
| Triguetti | la del medio, "la bandera" de la empresa |
| Candealix | también del medio, pero con trigo importado |
| Rena Speziale | la cara, para pocos clientes con plata |

La empresa tiene **$17.000 millones para gastar en publicidad este año** y la pregunta es una sola:

> **¿Cuánta plata le pongo a cada marca?**

Poner plata en publicidad trae clientes nuevos. Los clientes nuevos compran fideos. Eso es
más facturación. Y de esa facturación queda una ganancia. **Cada marca convierte publicidad
en plata a un ritmo distinto**, así que el reparto importa.

## La complicación

El directorio ya puso tres reglas que hay que cumplir sí o sí:

1. A Don Carlo y a Agnellis hay que darles **lo mismo** a las dos.
2. Triguetti se lleva **como mínimo el 30 %** de la plata.
3. Rena Speziale se lleva **como mínimo el doble** de lo que se lleven Candealix y Triguetti juntos.

Y encima hay una pelea interna: **los accionistas quieren ganancia** (les fue mal últimamente)
y **los gerentes quieren vender más** (sus premios dependen de las ventas, no de la ganancia).

---

## Qué hicimos

Armamos una **calculadora**. Le cargamos todos los datos del enunciado (precios, márgenes,
tamaño del mercado, cuántos clientes trae cada millón invertido) y las reglas del directorio.
La calculadora prueba todos los repartos posibles y devuelve el mejor.

## Qué dice la calculadora

| Marca | Cuánta plata le toca |
|---|---:|
| Don Carlo | $850 millones |
| Agnellis | $850 millones |
| Triguetti | $5.100 millones |
| **Candealix** | **$0 — no le toca nada** |
| Rena Speziale | $10.200 millones |

Con ese reparto la empresa pasa de vender el **48 %** de los fideos del país al **62 %**, y gana
**$76.578 millones**.

---

## Las cuatro cosas importantes que descubrimos

### 1. Se tiran $1.630 millones a la basura

Las reglas obligan a poner $10.200 millones en Rena Speziale. Pero Rena vende en el segmento
de los clientes con plata, **y ese grupo es chico**: son 1.200.000 personas en todo el país.
Con $8.570 millones ya se les vendió a **todas**.

Los $1.630 millones que sobran hay que gastarlos igual (lo manda la regla) pero **no traen ni
un cliente más**. Es casi el 10 % del presupuesto tirado.

### 2. La pelea del directorio no tiene sentido

Acordate de la pelea: accionistas quieren ganancia, gerentes quieren ventas. Probamos las dos
cosas por separado y **dan exactamente el mismo reparto**. Con las reglas que hay no queda
margen para elegir: el directorio ya decidió todo con sus tres reglas.

Y hay algo peor. Cuando probamos qué pasaría si sacaran esas reglas, resultó que la empresa
**ganaría las dos cosas al mismo tiempo**: más ventas Y más ganancia.

```
Como está hoy         62 % del mercado   y   $76.579 millones de ganancia
Sacando dos reglas    66 % del mercado   y   $80.253 millones de ganancia
```

O sea que las reglas del directorio no están eligiendo una cosa a costa de la otra.
**Están dejando las dos sobre la mesa.** El plan actual no es "el prudente": es
sencillamente peor que las alternativas.

### 3. Y aunque saquen las reglas, hay poco para pelear

Recién ahí aparece una decisión real entre vender más o ganar más. Pero es chica:
como mucho **un punto y pico de mercado** está en juego. Los primeros pedacitos de
mercado salen unos $529 millones cada uno; los últimos, $3.365 millones —
seis veces más caros, porque para conseguirlos hay que empujar a Rena Speziale
contra ese techo del que hablamos en el punto 1.

En criollo: **la discusión vale mucho menos de lo que el directorio cree**, y la plata
que están dejando escapar por no revisar sus propias reglas es tres veces más grande
que todo lo que están discutiendo.

### 4. La regla de Triguetti es carísima

Obligar a poner el 30 % en Triguetti cuesta plata, pero no por Triguetti en sí. Es porque
**cada peso que va a Triguetti obliga a poner dos pesos más en Rena Speziale** (por la regla 3),
y esa plata ya vimos que no sirve para nada.

Si se sacara esa regla, la empresa ganaría unos **$3.500 millones más al año**.

---


## Un problema que encontramos y arreglamos

La primera vez que corrimos la calculadora dio un resultado imposible: decía que Rena Speziale
le vendía a **1.308.333 personas** en un grupo que tiene **1.200.000 personas**. O sea, le
vendía a más gente de la que existe.

El enunciado del TP pone un techo para las marcas baratas pero **se olvida de poner uno para
las caras**. Nosotros lo agregamos. Es un agregado nuestro, no del enunciado, **y hay que
aclararlo en el informe**.

---

## Qué falta hacer

**Nada — el TP está terminado.** El informe final ya está escrito y listo para
entregar: [`informe/informe.pdf`](../informe/informe.pdf) (fuente en
`informe/informe.tex`).

| # | Tarea | Comentario |
|---|---|---|
| ✅ | Pregunta b) — ¿qué pasa si Agnellis crece? | Don Carlo casi no pierde nada: ya tiene 7,5 millones de clientes y la campaña mueve 340.000 |
| ✅ | Pregunta c) — ventas contra ganancia | Hoy no hay nada que discutir: las tres miradas dan el mismo plan. El conflicto solo aparece si se aflojan las reglas del directorio |
| ✅ | Pregunta d) — ¿está mal la regla del 30 %? | Sí sale cara (~$3.500 millones al año), pero el culpable real es el arrastre a Rena Speziale, no Triguetti. Y pasado el 33 % del presupuesto, ¡el problema deja de tener solución! |
| ✅ | Probar si nuestras suposiciones aguantan | De 14 números que tuvimos que inventar, solo uno mueve el plan, y en un caso límite. El resultado es robusto |
| ✅ | Gráficos | 6 gráficos en total, todos en `resultados/graficos/` |
| ✅ | Esquema del proceso | Dibujado prolijo, dentro del informe (con TikZ) |
| ✅ | Escribir el informe | Redactado y compilado a PDF |

---

## Cómo ver los resultados vos mismo

**La forma fácil:** abrí los archivos de la carpeta `resultados/tablas/` con Excel. Son tablas
comunes.

**La forma completa:** abrí una terminal en la carpeta del proyecto y escribí:

```
pip install -r requirements.txt
python scripts/00_verificar_datos.py
python scripts/01_modelo_base.py
python scripts/02_pregunta_b.py
python scripts/03_pregunta_c.py
python scripts/04_pregunta_d.py
python scripts/05_tests_supuestos.py
```

El primero revisa que los datos estén bien cargados. Los otros cinco hacen las cuentas,
imprimen todo y dejan los gráficos en `resultados/graficos/`.

---

## Dónde está cada cosa

| Carpeta o archivo | Qué hay adentro |
|---|---|
| `Consigna/` | el enunciado del TP |
| `Material/` | las clases del profesor |
| `resultados/tablas/` | **las tablas con los resultados** (abrilas con Excel) |
| `resultados/graficos/` | **los gráficos** en PNG, listos para el informe |
| `informe/` | **el informe final**, en PDF y en LaTeX |
| `src/` | la calculadora |
| `scripts/` | los programas que se ejecutan |

Y cuatro documentos escritos: el `README.md` está en la raíz del repositorio y los
otros tres en la carpeta `docs/`.

| Archivo | Para qué |
|---|---|
| [`README.md`](../README.md) | el técnico: cómo correr todo, qué hay hecho, las trampas |
| **este** (`docs/guia-rapida.md`) | el resumen fácil |
| [`docs/plan_de_trabajo.md`](plan_de_trabajo.md) | lo que planeamos hacer antes de empezar |
| [`docs/procedimiento.md`](procedimiento.md) | lo que realmente pasó, con los resultados y los números |

**Si vas a tocar el código, leé el `README.md` primero** — sobre todo la parte de "trampas
conocidas". Hay cosas del plan que quedaron viejas y están corregidas ahí.

---

## Para entregar

El archivo que se sube a la cátedra es [`informe/informe.pdf`](../informe/informe.pdf).
Todo lo demás (código, tablas, gráficos) es el respaldo de cómo se llegó a esos números.
