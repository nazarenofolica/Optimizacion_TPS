# Plan de trabajo

Estado al 2026-11-04 y lo que queda por revisar o construir. Lo que ya está hecho se describe en el
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
  con obesidad. 14 perfiles de ejemplo.
- Restricciones estrictas: celiaquía (incluido nada seco a granel), vegetariano, vegano, sin lactosa, ocho alergias
  con trazas, sin ultraprocesados, hipertensión, diabetes; y la opción de solo alimentos listos para comer.
- Hogar: hasta 8 personas, cada una con su dieta y sus restricciones, con la compra en común.
- Modelo de la dieta en dos etapas (primero cumplir, después lo más barato) con envases enteros, en seis sucursales
  cercanas; ticket, cobertura por persona, comparación de sucursales y mapa.
- Página autosuficiente (`salida/canasta.html`, 4,7 MB): datos del día adentro, motor en JavaScript con HiGHS en
  WebAssembly y workers en paralelo, ubicación por Georef, GPS o mapa; funciona sin servidor y se puede embeber en
  Streamlit.
- Tests: 81 en Python (24 de la canasta) y uno opcional que compara el motor del navegador con el de Python.

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
   proteína, sal y condimentos que se agregan al cocinar, agua, menores de 4 años.
5. **Promociones**: se muestran pero no se aplican al total (muchas exigen condiciones).

### Página

1. **Probar en Streamlit de verdad.** Dentro del iframe de `components.html` el GPS suele estar bloqueado (la página
   lo avisa y ofrece buscar o marcar en el mapa); falta confirmarlo y ajustar el alto.
2. Probar en Firefox y Safari (DecompressionStream, workers anidados) y en celulares de gama baja (memoria: ~60 MB
   de datos en el worker).
3. Accesibilidad: revisión con lector de pantalla y teclado.

## Próximos pasos

1. **Actualización diaria automática**: `python -m sepa --descargar` y `python -m canasta --exportar` en una tarea
   programada, y publicar la página (por ejemplo en GitHub Pages, ya que es un archivo estático).
2. **Velocidad**: una persona tarda ~10 s y un hogar de tres para dos semanas ~18 s. Ideas: resolver primero solo la
   sucursal más prometedora, cachear la oferta por cadena, acotar el modelo entero a los productos que usa la
   relajación.
3. **Ticket para llevar**: imprimir o descargar en PDF, y compartir el enlace con los datos cargados.
4. **Comparar contra la Canasta Básica Alimentaria del INDEC** (costo por adulto equivalente) como referencia en la
   página.
5. **Tests del motor JavaScript sin navegador** (Node) y una integración continua que corra los tests en cada push.
