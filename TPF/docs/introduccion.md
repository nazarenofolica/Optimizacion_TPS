# El problema de la dieta

> **Qué es este archivo.** La introducción del TPF: de dónde viene el problema de la dieta, cómo se
> planteó y resolvió originalmente, qué enseñó, y cómo lo vamos a plantear nosotros con precios
> reales de Argentina. **No contiene resultados del trabajo**: la base de datos está lista y el
> modelo está pendiente (ver [`plan_de_trabajo.md`](plan_de_trabajo.md)). Las referencias completas
> están en [`fuentes.md`](fuentes.md).

---

## 1. El problema, en una frase

**¿Cuál es la combinación de alimentos más barata que cubre todos los requerimientos nutricionales
de una persona?**

Es el ejemplo fundacional de la programación lineal. Si $x_j$ es la cantidad que se compra del
alimento $j$, $c_j$ su precio por unidad, $a_{ij}$ la cantidad del nutriente $i$ que aporta una
unidad del alimento $j$ y $b_i$ el requerimiento mínimo de ese nutriente:

$$
\min \; \sum_{j} c_j \, x_j
\qquad \text{s.a.} \qquad
\sum_{j} a_{ij} \, x_j \;\ge\; b_i \quad \forall i,
\qquad x_j \ge 0 \quad \forall j
$$

Todo es lineal: el costo crece proporcionalmente con lo que se compra y cada nutriente es la suma de
lo que aporta cada alimento. Las extensiones agregan **máximos** (sodio, grasas saturadas, energía),
**topes por alimento** (para que la dieta sea comible) o **variables enteras** (comprar en unidades,
elegir en qué tienda comprar).

---

## 2. Cómo se pensó originalmente: Stigler (1945)

En 1945 el economista **George Stigler** (premio Nobel de Economía en 1982) publicó *The Cost of
Subsistence* en el *Journal of Farm Economics*. Se preguntó cuánto costaba, como mínimo, alimentar a
un hombre de 70 kg (154 libras) moderadamente activo cumpliendo las raciones diarias recomendadas por
el **National Research Council** de Estados Unidos en 1943.

**Los datos.** Armó una tabla de **77 alimentos** con sus precios de agosto de 1939 y los expresó de
una forma ingeniosa: en vez de dar los nutrientes por kilo, dio **cuánto de cada nutriente compra un
dólar** gastado en ese alimento. Así la variable de decisión es directamente cuántos dólares por día se
gastan en cada alimento y el costo total es la suma de las variables.

**Los requisitos.** Nueve nutrientes, todos como mínimos diarios:

| Nutriente | Mínimo diario | | Nutriente | Mínimo diario |
|---|---:|---|---|---:|
| Calorías | 3.000 kcal | | Tiamina (B1) | 1,8 mg |
| Proteínas | 70 g | | Riboflavina (B2) | 2,7 mg |
| Calcio | 0,8 g | | Niacina | 18 mg |
| Hierro | 12 mg | | Ácido ascórbico (C) | 75 mg |
| Vitamina A | 5.000 UI | | | |

El problema tiene **9 restricciones y 77 variables**. En 1945 no existía ningún algoritmo para
resolverlo.

**Cómo lo resolvió.** Por "prueba y error, intuición matemática y agilidad", en sus palabras. Descartó
62 de los 77 alimentos porque otros los dominaban (daban más de todo por el mismo dólar) y, entre los
15 que quedaron, armó una dieta de solo cinco: **harina de trigo, leche evaporada, repollo, espinaca y
porotos blancos secos**. Costaba **US\$ 39,93 por año** a precios de 1939, unos 11 centavos por día.

Stigler sabía que su respuesta podía no ser la mejor, y también que nadie debía comerla: *"No one
recommends these diets for anyone, let alone everyone"* ("nadie recomienda estas dietas para nadie, y
menos para todos").

---

## 3. La solución exacta: el método símplex (1947)

En 1947 **George Dantzig** desarrolló el **método símplex**, y el problema de Stigler fue su primera
prueba de gran escala. Lo resolvió **Jack Laderman** en la National Bureau of Standards: repartió las
77 columnas entre **nueve empleados** que, con calculadoras mecánicas de escritorio, trabajaron unas
**120 jornadas-hombre** hasta llegar al óptimo.

El costo mínimo resultó **US\$ 39,69 por año**: la heurística de Stigler estaba apenas 24 centavos
arriba. La dieta óptima casi coincide con la suya; la diferencia es que una pequeña cantidad de hígado
vacuno reemplaza a la leche evaporada. Si además se exige cumplir cada requisito exactamente, sin
excedentes, el costo sube a US\$ 49,40.

En 1953 una **IBM 701** resolvió el mismo problema en 12 minutos; hoy tarda menos de un segundo.

---

## 4. Qué enseñó: el modelo solo sabe lo que dicen sus restricciones

La dieta óptima cumple todo lo que se le pidió y es incomible: unos pocos alimentos baratos en
cantidades enormes, siempre los mismos. El modelo no "sabe" de sabor, variedad, costumbres ni
preparación: si eso importa, hay que escribirlo como restricción.

**La anécdota de Dantzig.** Años después, Dantzig contó (en "The Diet Problem", *Interfaces*, 1990)
que su médico le pidió bajar de peso y él decidió "modelar su dieta como un programa lineal y dejar
que la computadora decidiera". Maximizó la sensación de saciedad con un tope de 1.500 calorías. La
primera solución le indicaba tomar vinagre en cantidad, porque los datos le asignaban contenido nulo
de agua y el modelo lo tomaba por un alimento llenador ("decidí que el vinagre no era un alimento");
la siguiente, 200 cubos de caldo por día, que tuvo que limitar a tres; después, casi un kilo de salvado
y, al limitarlo, casi un kilo de melaza. Al final su esposa lo puso a comer su propio menú y bajó 10 kg.

**Lo que vino después.** El problema de la dieta fue el precursor de una enorme familia de
aplicaciones de mezcla de ingredientes que sí funcionaron: raciones para ganado y pollos, fertilizantes
y mezclas industriales. En la alimentación humana evolucionó hacia la **planificación de menús**, que
agrega grupos de alimentos, porciones y variedad. En Estados Unidos, el **Thrifty Food Plan** del
Departamento de Agricultura, que define el monto de la asistencia alimentaria, y las reglas de los
almuerzos escolares descienden de este modelo.

**Revisado con datos nuevos.** Garille y Gass (2001) volvieron a resolver el problema con precios de
abril de 1998 de un supermercado de Baltimore-Washington, los requerimientos de entonces y más de 30
restricciones nutricionales: la dieta mínima costaba **US\$ 651,27 por año para un hombre** de 25 a 50
años y **US\$ 535,27 para una mujer**. El esqueleto se repetía: harina, avena, leche, manteca de maní,
grasa, un poco de hígado, frutas y verduras baratas.

---

## 5. Nuestro planteo

### 5.1. Foco: el problema de la dieta con precios reales de Argentina

El TPF retoma la pregunta de Stigler con datos de hoy:

- **Alimentos:** los 218 alimentos genéricos de la base ("leche entera", "lentejas secas",
  "nalga", "banana"...), que agrupan 28.036 productos con nutrientes cada 100 g.
- **Precios:** los publicados por 2.666 sucursales de 15 cadenas en las 24 jurisdicciones el
  **23 de octubre de 2026** (sistema SEPA), no un promedio nacional único como en 1939.
- **Requisitos:** los vigentes en Argentina: los valores de referencia del rotulado nutricional
  (Código Alimentario Argentino, Res. GMC 46/03) y las **Guías Alimentarias para la Población
  Argentina** (Ministerio de Salud, 2016), que además de nutrientes proponen cantidades diarias por grupo
  de alimentos.
- **Persona de referencia:** la de las Guías, una mujer adulta con 2.000 kcal diarias. Stigler usaba
  un hombre de 70 kg con 3.000 kcal.

Preguntas que guían el trabajo (todavía sin responder):

1. ¿Qué comería hoy, en Argentina, la dieta de costo mínimo "a la Stigler", y cuánto cuesta?
2. ¿Cuánto más cuesta una dieta que además respete las Guías Alimentarias (grupos, porciones, topes de
   sodio y grasas, variedad)? ¿Qué requisito encarece más la dieta?
3. ¿Cómo cambia el costo entre provincias y frente a la Canasta Básica Alimentaria del INDEC?

### 5.2. Complemento: dónde comprar (cercanía de las tiendas)

La dieta se compra en tiendas concretas, y la más barata para un alimento no suele ser la misma que
para otro, ni la más cercana. Como complemento, el TPF plantea un **modelo entero**: dado un hogar, a
qué tiendas cercanas conviene ir (una variable binaria por tienda) y qué comprar en cada una,
equilibrando lo que se ahorra en precio con lo que cuesta moverse. Es la misma familia de problemas
de localización que se trabajó en el TP3, aplicada a la canasta de la dieta.

---

## 6. Nuestros datos

La base es un **modelo estrella** armado para este trabajo a partir de los datos abiertos de SEPA, y
está completa y verificada en [`../datos/sepa/`](../datos/sepa/) (descripción en
[`../datos/README.md`](../datos/README.md)):

| Tabla | Una fila por | Filas | Contenido |
|---|---|---:|---|
| `dim_producto` | producto comestible | 28.036 | clasificación en 218 alimentos genéricos, presentación, 33 nutrientes cada 100 g, composición, alérgenos, NOVA, sellos. Sin precio |
| `dim_tienda` | sucursal | 2.666 | cadena, formato, dirección, coordenada validada, provincia, departamento y municipio |
| `fact_precio` | producto × tienda | 8.241.172 | precio publicado, promoción, presentación y precio normalizado por kg, litro, unidad y cada 100 g |

De SEPA solo vienen los precios, las descripciones de los productos y las sucursales. El resto lo arma
el pipeline de [`../base_sepa/`](../base_sepa/), que:

1. **Identifica cada producto** y su **contenido neto** (corrige comas corridas, packs y unidades mal
   cargadas).
2. Lo **clasifica en un alimento genérico** con reglas sobre la descripción y lo verifica contra la
   categoría de góndola de los catálogos online de Jumbo, Disco y Vea. Lo que no es comida (limpieza,
   perfumería, bazar, mascotas) y la comida preparada quedan afuera, cada uno con su motivo.
3. Le asigna **nutrientes** en orden de confianza: rótulo del catálogo web, rótulo leído de la foto
   del envase, Open Food Facts, productos casi iguales con rótulo y, como último recurso, el alimento
   genérico (USDA o el rótulo más representativo). Cada rótulo pasa controles de coherencia (energía
   frente a macronutrientes, valores posibles, parecido con su alimento).
4. **Limpia los precios** anormales y los normaliza para que sean comparables dentro de cada alimento.
5. **Ubica las tiendas**: corrige coordenadas y las valida con la API Georef del Estado nacional.

En cada corrida la base cumple 52 controles (claves únicas, integridad referencial, nutrientes
posibles, composición coherente, precios positivos, coordenadas dentro del país) y, si uno crítico
falla, no se publica.

**Para tener en cuenta en el modelo:** los alimentos frescos y las marcas propias sin rótulo usan los
nutrientes de su alimento genérico o de productos parecidos (`fuente_nutrientes` lo dice en cada fila);
los rótulos de café, té y yerba describen la infusión; y la base es de un solo día, no una serie
histórica.
