# Plan de trabajo

Estado al 2026-11-21 y lo que queda por revisar o construir. Lo que ya está hecho se describe en el
[README](README.md); acá van los avances en resumen, los problemas conocidos y los próximos pasos, en orden de
prioridad dentro de cada bloque.

## Avances

**Modelo estrella** (`python -m sepa`): dim_producto (28.030 alimentos, 33 nutrientes, composición y aptitudes),
dim_tienda (2.666 sucursales con ubicación validada) y fact_precio (8,2 millones de precios normalizados) de un día
de SEPA, con 52 controles que se verifican en cada corrida. En esta etapa se corrigieron reglas de
`referencia/alimentos.csv` por abreviaturas que se colaban en alimentos básicos ("GALL" de galletitas en leche, "CHO"
de chocolate en maní, "EDULC" de edulcorante en frutos secos).

**Canasta saludable** (`python -m canasta`):

- Requerimientos por persona: energía (FAO/OMS/UNU 2004), proteína, macronutrientes, 19 vitaminas y minerales por
  etapa de la vida (NASEM), reglas de las Guías Alimentarias, embarazo, lactancia, objetivo de peso, peso ajustado
  con obesidad. 20 perfiles de ejemplo; la página ofrece cinco (columna `visible` de `referencia/perfiles.csv`) y los
  demás se cargan por enlace o desde la consola.
- Restricciones estrictas: celiaquía (incluido nada seco a granel), vegetariano, vegano, sin lactosa, ocho alergias
  con trazas, sin ultraprocesados, hipertensión, diabetes; y la opción de solo alimentos listos para comer.
- Hogar: hasta 8 personas, cada una con su dieta y sus restricciones, con la compra en común.
- Modelo de la dieta en dos etapas (primero cumplir, después lo más barato) con envases enteros, en seis sucursales
  cercanas; ticket, cobertura por persona, comparación de sucursales y mapa.
- Página autosuficiente (`../datos/sepa/canasta.html`, 4,7 MB): datos del día adentro, motor en JavaScript con HiGHS en
  WebAssembly y workers en paralelo, ubicación por Georef, GPS o mapa; funciona sin servidor y se puede embeber en
  Streamlit.
- Tests: 81 en Python (24 de la canasta) y uno opcional que compara el motor del navegador con el de Python.

**Estabilización del POC (2026-11-14)**: búsqueda por tiempo caminando con rutas reales de OpenRouteService
(`canasta/rutas.py` y `web/rutas.js`), ampliación del límite con comparación de ahorro, recorrido en el mapa, arreglos
de mapas (teselas, servidor local, superposición en el celular), ticket rediseñado (minutos caminando, columnas,
promociones "no aplicadas", resumen nutricional, impresión), página versionada sin clave. Tests: 101 en Python más
dos de paridad con el navegador (también por tiempo caminando).

**Etapa 1 del MVP (2026-11-20)**, con lo que se pidió después de la presentación: objetivo "Aumentar de peso"
(+500 kcal/día sobre el gasto, proteína 1,2 g/kg, aviso si el IMC es de sobrepeso; perfil `bajo_peso`, 2.310
kcal/día), distinto de "Ganar masa muscular"; el agua como restricción con tres modos (`AGUA_MODOS`: `canilla`, la
predeterminada e informativa, que no cambia los resultados de antes; `compra`, agua total de NASEM 2004 contando la de
los alimentos; `bebidas`, los 8 vasos de las Guías), y un caso precargado que no llega a las 37 metas
(`restricciones_extremas`: celíaca con cinco alergias, solo listos, Córdoba, 15 min; la mejor sucursal cubre 35) que
la página explica meta por meta. Tests: 114 en Python más dos de paridad con el navegador, ahora con 8 casos.

**Etapa 2 del MVP (2026-11-20)**, compra en dos supermercados, pedida por el docente: a pedido (botón "¿Conviene
sumar un segundo súper?", `&dos=1`, `--dos-super`), a la sucursal elegida A se le prueba sumar una vecina B a ≤ 10 min
caminando (hasta 4, primero de otras cadenas). La formulación lleva binarias de visita (`y_A = 1`, `Σ y_s ≤ 2`,
`x_p ≤ x_max_p · y_s(p)`); como es equivalente, se resuelve enumerando los pares (A, B) con el modelo de siempre sobre
la unión de las ofertas, sin los productos de B que A vende igual o más barato (el MILP con binarias no fue más rápido
y dio compras más caras). Conviene si cubre mejor las metas o, con las mismas, si ahorra ≥ 3 % y ≥ $1.000; se informa
el ahorro y los minutos de más (tramo A → B estimado) y la persona decide. La página muestra la decisión, la
comparación, el recorrido, el ticket dividido por sucursal y el mapa. El oficinista en el Microcentro ahorra ~6 % con
~5 min más. Tests: 127 en Python más 3 de paridad con el navegador, también para dos súper. Las etapas 4 a 6
(restricciones nuevas, promociones con condiciones, Groq) están en [../docs/ROADMAP.md](../docs/ROADMAP.md).

**Etapa 3 del MVP (2026-11-21)**, ETL diario y CI, hecha en el repo y pendiente de activar
([../docs/DESPLIEGUE.md](../docs/DESPLIEGUE.md)): GitHub Actions pregunta cada día la fecha del último ZIP de SEPA
(`python -m sepa --ultima-fecha`) y, si es nueva, rearma la base (`python -m sepa --diario`: `--descargar` sin
intervención, que si faltan los catálogos web los recorre), exporta la página sin clave y la publica en GitHub Pages,
sin commitear los datos del día. Open Food Facts, los catálogos web, Georef/USIG y USDA viajan en la caché de Actions.
Si falla la verificación no se publica (queda el día anterior) y se abre un issue. Los tests de Python corren en cada
push. Tests: 142 en Python.

## Para revisar

### Datos (pipeline)

1. **Precios mal cargados de productos que vende una sola cadena.** La papa a $95 el kg (mediana $3.500) pasó los
   controles porque no hay otra cadena con qué compararla. La canasta los descarta (menos de 1/8 de la mediana de la
   subcategoría), pero el control debería estar en `sepa/precio/` para que fact_precio salga limpio.
2. **Auditoría de clasificación por abreviaturas.** Se corrigieron cuatro reglas, pero el mismo patrón (abreviaturas
   de SEPA como CHO, GALL, EDULC, COF) puede aparecer en otros alimentos. Pendiente: buscar sistemáticamente nombres que
   contradicen su subcategoría (por ejemplo, "Mani crocante tomate y oliva" en Maní; "Alimento base queso rallado",
   que es un análogo, en Queso rallado).
3. Pendientes que ya estaban: jugos concentrados tratados como jugos listos; café con convenciones de rótulo
   mezcladas.
4. Jumbo y Vea no publican frutas ni verduras frescas en SEPA en varias sucursales: la canasta lo detecta y las
   descarta, pero conviene confirmar si es un faltante de SEPA o de nuestra lectura.

### Canasta

1. **Realismo de la compra.** Lo más barato tiende a repetirse: harina de trigo, leche en polvo, legumbres secas,
   atún en lata. Es nutricionalmente correcto, pero hay que revisarlo con criterio de nutricionista: ¿pan en lugar de
   harina?, ¿un tope por "ingredientes" que requieren elaboración?, ¿más variedad dentro de verduras y frutas? Aparecen
   cortes poco habituales (sesos, hígado) por baratos.
2. **Lista de "listos para comer"** (`ALIMENTOS_A_COCINAR`): definida a mano; revisar casos dudosos (leche en polvo,
   puré de tomate, hongos).
3. **Equivalencias en gramos de las Guías** (medio plato de verduras ≈ 150 g, fruta mediana ≈ 150 g, aceite ≈ 20 g):
   son propias; validarlas con la bibliografía de las GAPA.
4. **No modelado todavía:** seguridad alimentaria en el embarazo (hígado, quesos sin pasteurizar), calidad de la
   proteína, sal y condimentos que se agregan al cocinar, menores de 4 años. (El agua ya se modela: de la canilla,
   comprada contando la de los alimentos, o 2 litros de bebida; ver `AGUA_MODOS`.)
5. **Promociones**: se muestran pero no se aplican al total (muchas exigen condiciones). Las de la cadena (2×1,
   2.ª unidad, porcentaje) son la etapa 5 del roadmap; las bancarias quedan fuera de alcance.

### Página

1. **Probar en Streamlit de verdad.** Dentro del iframe de `components.html` el GPS suele estar bloqueado (la página
   lo avisa y ofrece buscar o marcar en el mapa); falta confirmarlo y ajustar el alto.
2. Probar en Firefox y Safari (DecompressionStream, workers anidados) y en celulares de gama baja (memoria: ~60 MB
   de datos en el worker).
3. Accesibilidad: revisión con lector de pantalla y teclado.

## Próximos pasos

1. **Activar la actualización diaria** (etapa 3, ya armada): pushear, llevar a `main`, Settings → Pages → "GitHub
   Actions" y la primera corrida a mano ([../docs/DESPLIEGUE.md](../docs/DESPLIEGUE.md)). Después, controles contra el
   día anterior.
2. **Velocidad**: una persona tarda ~10 s y un hogar de tres para dos semanas ~18 s. Ideas: resolver primero solo la
   sucursal más prometedora, cachear la oferta por cadena, acotar el modelo entero a los productos que usa la
   relajación.
3. **Ticket para llevar**: imprimir o descargar en PDF, y compartir el enlace con los datos cargados.
4. **Comparar contra la Canasta Básica Alimentaria del INDEC** (costo por adulto equivalente) como referencia en la
   página.
5. **Tests del motor JavaScript sin navegador** (Node) y la paridad en cada push (los tests de Python ya corren en
   cada push: `.github/workflows/tpf-tests.yml`).
