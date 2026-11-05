# SEPA 2.0 — salida

Precios minoristas del **2026-10-23** (SEPA, `sepa_viernes_2026-10-23.zip`), procesados el 2026-11-04 21:36 en 7.1 min.

## Archivos

| Archivo | Qué es | Filas |
|---|---|---:|
| `dim_producto.parquet` / `.csv` | Productos comestibles: clasificación. presentación. nutrientes y composición (sin precio) | 28.030 |
| `dim_tienda.parquet` / `.csv` | Sucursales con ubicación validada. división política y horarios | 2.666 |
| `fact_precio.parquet` / `.csv.gz` | Precio de cada producto en cada tienda. normalizado | 8.240.279 |
| `calidad/` | Lo excluido y por qué, precios descartados, ubicaciones corregidas, verificación | |

Relaciones: `fact_precio.id_producto` → `dim_producto.id_producto` y `fact_precio.id_tienda` → `dim_tienda.id_tienda` (muchos a uno). Los CSV usan `;` y coma decimal; para Power BI, pandas o R conviene el parquet.

Ejemplos: precio por kg de la banana en cada provincia → `fact_precio` (subcategoría Banana vía `dim_producto`) agrupado por `dim_tienda.provincia` con la mediana de `precio_normalizado`. Costo de 100 g de proteína → `precio_100g / parte_comestible / proteinas_g * 100`.

## Resumen de la corrida

- Productos en SEPA ese día: 78.120; comestibles en `dim_producto`: 28.030 en 218 subcategorías y 34 categorías
- Tiendas: 2.666 en 24 provincias; ubicación exacta 2.648. aproximada 2. dudosa 5. sin ubicación 10
- Precios: 8.240.279 (con promoción vigente: 727.880); descartados por anormales: 6.337

| Categoría | Productos |
|---|---:|
| Bebidas alcohólicas | 3.573 |
| Almacén | 2.527 |
| Golosinas | 2.080 |
| Galletitas | 1.991 |
| Panificados | 1.796 |
| Lácteos | 1.777 |
| Bebidas | 1.504 |
| Quesos | 1.400 |
| Infusiones | 1.161 |
| Pastas | 1.148 |
| Verduras | 834 |
| Fiambres | 776 |
| Aderezos | 770 |
| Cereales | 755 |
| Conservas | 721 |
| Snacks | 640 |
| Frutos secos | 607 |
| Pescados | 484 |
| Carne vacuna | 482 |
| Frutas | 412 |
| Carnes procesadas | 359 |
| Comidas preparadas | 358 |
| Embutidos | 305 |
| Aceites | 280 |
| Legumbres | 270 |
| Cerdo | 216 |
| Huevos | 207 |
| Harinas | 148 |
| Pollo | 134 |
| Verduras congeladas | 118 |
| Achuras | 83 |
| Otras carnes | 53 |
| Grasas | 44 |
| Frutas congeladas | 17 |

| Grupo alimentario | Productos |
|---|---:|
| Alimentos de consumo opcional | 12.787 |
| Legumbres. cereales. papa. pan y pastas | 4.318 |
| Condimentos. aderezos y edulcorantes | 2.385 |
| Leche. yogur y queso | 2.323 |
| Carnes y huevos | 2.018 |
| Verduras y frutas | 1.737 |
| Agua e infusiones | 1.395 |
| Aceites. frutas secas y semillas | 709 |
| Comidas preparadas | 358 |

| Fuente de los nutrientes | Productos |
|---|---:|
| generico: usda | 9.233 |
| rotulo_web | 5.501 |
| similar | 5.455 |
| generico: rotulos | 4.987 |
| rotulo_web+off | 1.610 |
| rotulo_off | 845 |
| rotulo_foto | 399 |

| Provincia | Tiendas |
|---|---:|
| Ciudad Autónoma de Buenos Aires | 946 |
| Buenos Aires | 904 |
| Córdoba | 157 |
| Entre Ríos | 88 |
| Mendoza | 86 |
| Río Negro | 65 |
| Neuquén | 61 |
| Salta | 50 |
| Chubut | 46 |
| Santa Fe | 46 |
| Jujuy | 31 |
| Santa Cruz | 30 |
| Tucumán | 26 |
| Corrientes | 24 |
| La Pampa | 22 |
| Tierra del Fuego. Antártida e Islas del Atlántico Sur | 14 |
| San Juan | 14 |
| (sin ubicación) | 10 |
| Misiones | 10 |
| Catamarca | 8 |
| San Luis | 8 |
| Santiago del Estero | 6 |
| Chaco | 5 |
| Formosa | 5 |
| La Rioja | 4 |

## Verificación

Todos los controles críticos pasan (si alguno fallara, la corrida se detiene). Detalle en `calidad/verificacion.csv`.

| Control | Filas que fallan | Crítico |
|---|---:|:---:|
| producto: id_producto único y no vacío | 0 | sí |
| producto: nombre completo | 0 | sí |
| producto: categoria completo | 0 | sí |
| producto: subcategoria completo | 0 | sí |
| producto: grupo_alimentario completo | 0 | sí |
| producto: forma_venta completo | 0 | sí |
| producto: unidad_normalizada completo | 0 | sí |
| producto: unidad_normalizada en kg / l / unidad | 0 | sí |
| producto: cantidad_normalizada > 0 | 0 | sí |
| producto: gramos_envase > 0 | 0 | sí |
| producto: parte_comestible entre 0 y 1 | 0 | sí |
| nutrientes: sin vacíos | 0 | sí |
| nutrientes: sin negativos | 0 | sí |
| nutrientes: energía <= 950 kcal | 0 | sí |
| nutrientes: proteínas + carbohidratos + grasas + fibra + alcohol <= 105 g | 0 | sí |
| nutrientes: saturadas <= grasas totales | 0 | sí |
| nutrientes: saturadas + mono + poli + trans <= grasas totales (+5 %) | 0 | sí |
| nutrientes: azúcares <= carbohidratos | 0 | sí |
| nutrientes: sodio <= 40.000 mg | 0 | sí |
| nutrientes: agua + sólidos <= 105 g | 0 | sí |
| nutrientes: energía coherente con los macronutrientes (Atwater, ±25 %) | 0 |  |
| composición: contiene_gluten en si/no/desconocido | 0 | sí |
| composición: contiene_leche en si/no/desconocido | 0 | sí |
| composición: contiene_huevo en si/no/desconocido | 0 | sí |
| composición: contiene_mani en si/no/desconocido | 0 | sí |
| composición: contiene_frutos_secos en si/no/desconocido | 0 | sí |
| composición: contiene_soja en si/no/desconocido | 0 | sí |
| composición: contiene_pescado en si/no/desconocido | 0 | sí |
| composición: contiene_mariscos en si/no/desconocido | 0 | sí |
| composición: contiene_sesamo en si/no/desconocido | 0 | sí |
| composición: apto_vegetariano en si/no/desconocido | 0 | sí |
| composición: apto_vegano en si/no/desconocido | 0 | sí |
| composición: sin_tacc en si/no/desconocido | 0 | sí |
| composición: sin_lactosa en si/no/desconocido | 0 | sí |
| composición: azucar_agregada en si/no/desconocido | 0 | sí |
| composición: vegano implica vegetariano | 0 | sí |
| composición: con leche, huevo, pescado o mariscos no es vegano | 0 | sí |
| composición: con gluten no es sin TACC | 0 | sí |
| tienda: id_tienda único y no vacío | 0 | sí |
| tienda: coordenada dentro de la Argentina | 0 | sí |
| tienda: ubicada tiene provincia y departamento | 0 |  |
| tienda: sin ubicación (sin ficha de sucursal en SEPA) | 10 |  |
| tienda: ubicación dudosa (se conserva la de SEPA) | 5 |  |
| fact: id_producto existe en dim_producto | 0 | sí |
| fact: id_tienda existe en dim_tienda | 0 | sí |
| fact: un precio por producto y tienda | 0 | sí |
| fact: precio > 0 | 0 | sí |
| fact: precio_normalizado > 0 | 0 | sí |
| fact: precio_100g > 0 | 0 | sí |
| fact: promoción menor al precio de lista | 0 | sí |
| producto: tiene al menos un precio en fact_precio | 0 | sí |
| tienda: tiene al menos un precio en fact_precio | 0 |  |

## Diccionario de datos

### dim_producto

| Columna | Tipo | Descripción |
|---|---|---|
| `id_producto` | texto | Clave. EAN de 13 dígitos (con ceros a la izquierda) o, para lo que la cadena identifica con un código propio (frescos, balanza), 'cadena<id_comercio>-<código>' |
| `tipo_codigo` | texto | EAN o Interno de cadena |
| `id_comercio_interno` | entero | Para códigos internos, el comercio (cadena) dueño del código |
| `nombre` | texto | Nombre legible (la descripción más completa entre las cadenas, sin tamaños ni códigos de envase) |
| `marca` | texto | Marca |
| `descripcion_sepa` | texto | Descripción tal como la publica la mayoría de las sucursales |
| `categoria` | texto | Rubro (Lácteos, Carne vacuna, Frutas, Bebidas...) |
| `subcategoria` | texto | Alimento genérico (Leche entera, Nalga, Banana...): el nivel para comparar precios |
| `grupo_alimentario` | texto | Grupo de las Guías Alimentarias para la Población Argentina (más agua e infusiones, condimentos y comidas preparadas) |
| `forma_venta` | texto | Envase, Granel (precio por kg) o Por unidad |
| `contenido` | número | Contenido neto del envase (en unidad_contenido); a granel, 1000 g |
| `unidad_contenido` | texto | g o ml |
| `unidades` | número | Unidades que trae (huevos x 12, alfajores x 6); vacío si no aplica |
| `unidad_normalizada` | texto | Unidad común de su subcategoría para comparar precios: kg, l o unidad |
| `cantidad_normalizada` | número | Cuántos kg, l o unidades compra el precio publicado (precio / cantidad_normalizada = precio por unidad normalizada) |
| `gramos_envase` | número | Gramos que compra el precio publicado (líquidos con su densidad) |
| `base_normalizacion` | texto | directa, densidad (g <-> ml) o peso_unidad_estimado (se vende por unidad sin peso informado: se usa el peso típico de la unidad, aproximado) |
| `parte_comestible` | número | Fracción comestible (1 en envasados; banana 0,64; pollo entero 0,70) |
| `densidad_g_ml` | número | Densidad usada para los líquidos (g por ml) |
| `porcion_g` | entero | Porción de referencia del alimento genérico (g o ml) |
| `energia_kcal` | número | Energia, kcal cada 100 g comestibles |
| `proteinas_g` | número | Proteinas, g cada 100 g comestibles |
| `carbohidratos_g` | número | Carbohidratos, g cada 100 g comestibles |
| `azucares_g` | número | Azucares, g cada 100 g comestibles |
| `fibra_g` | número | Fibra, g cada 100 g comestibles |
| `grasas_totales_g` | número | Grasas totales, g cada 100 g comestibles |
| `grasas_saturadas_g` | número | Grasas saturadas, g cada 100 g comestibles |
| `grasas_monoinsaturadas_g` | número | Grasas monoinsaturadas, g cada 100 g comestibles |
| `grasas_poliinsaturadas_g` | número | Grasas poliinsaturadas, g cada 100 g comestibles |
| `grasas_trans_g` | número | Grasas trans, g cada 100 g comestibles |
| `colesterol_mg` | número | Colesterol, mg cada 100 g comestibles |
| `sodio_mg` | número | Sodio, mg cada 100 g comestibles |
| `potasio_mg` | número | Potasio, mg cada 100 g comestibles |
| `calcio_mg` | número | Calcio, mg cada 100 g comestibles |
| `hierro_mg` | número | Hierro, mg cada 100 g comestibles |
| `magnesio_mg` | número | Magnesio, mg cada 100 g comestibles |
| `fosforo_mg` | número | Fosforo, mg cada 100 g comestibles |
| `zinc_mg` | número | Zinc, mg cada 100 g comestibles |
| `cobre_mg` | número | Cobre, mg cada 100 g comestibles |
| `selenio_ug` | número | Selenio, µg cada 100 g comestibles |
| `vitamina_a_ug` | número | Vitamina a, µg cada 100 g comestibles |
| `vitamina_c_mg` | número | Vitamina c, mg cada 100 g comestibles |
| `vitamina_d_ug` | número | Vitamina d, µg cada 100 g comestibles |
| `vitamina_e_mg` | número | Vitamina e, mg cada 100 g comestibles |
| `vitamina_k_ug` | número | Vitamina k, µg cada 100 g comestibles |
| `vitamina_b1_mg` | número | Vitamina b1, mg cada 100 g comestibles |
| `vitamina_b2_mg` | número | Vitamina b2, mg cada 100 g comestibles |
| `vitamina_b3_niacina_mg` | número | Vitamina b3 niacina, mg cada 100 g comestibles |
| `vitamina_b6_mg` | número | Vitamina b6, mg cada 100 g comestibles |
| `vitamina_b9_folato_ug` | número | Vitamina b9 folato, µg cada 100 g comestibles |
| `vitamina_b12_ug` | número | Vitamina b12, µg cada 100 g comestibles |
| `agua_g` | número | Agua, g cada 100 g comestibles |
| `alcohol_g` | número | Alcohol, g cada 100 g comestibles |
| `fuente_nutrientes` | texto | Origen de los nutrientes: rotulo_web, rotulo_web+off, rotulo_off, rotulo_foto, manual, similar (productos parecidos con rótulo) o generico: usda / rotulos |
| `ingredientes` | texto | Lista de ingredientes del rótulo, si se conoce |
| `contiene_gluten` | texto | Contiene gluten: si / no / desconocido |
| `contiene_leche` | texto | Contiene leche: si / no / desconocido |
| `contiene_huevo` | texto | Contiene huevo: si / no / desconocido |
| `contiene_mani` | texto | Contiene mani: si / no / desconocido |
| `contiene_frutos_secos` | texto | Contiene frutos secos: si / no / desconocido |
| `contiene_soja` | texto | Contiene soja: si / no / desconocido |
| `contiene_pescado` | texto | Contiene pescado: si / no / desconocido |
| `contiene_mariscos` | texto | Contiene mariscos: si / no / desconocido |
| `contiene_sesamo` | texto | Contiene sesamo: si / no / desconocido |
| `puede_contener` | texto | Alérgenos declarados como trazas |
| `apto_vegetariano` | texto | si / no / desconocido |
| `apto_vegano` | texto | si / no / desconocido |
| `sin_tacc` | texto | si / no / desconocido (apto celíacos) |
| `sin_lactosa` | texto | si / no / desconocido |
| `nova` | entero | Grado de procesamiento NOVA (1 sin procesar ... 4 ultraprocesado) |
| `aditivos` | entero | Cantidad de aditivos (Open Food Facts), si se conoce |
| `azucar_agregada` | texto | si / no / desconocido |
| `edulcorantes` | texto | si / no / desconocido |
| `aceite_palma` | texto | si / no / desconocido |
| `fuente_composicion` | texto | rótulo (catálogo web), rótulo (Open Food Facts), ingredientes o alimento genérico |
| `exceso_azucares` | booleano | Sello de advertencia aproximado: exceso azucares (verdadero / falso) |
| `exceso_grasas_saturadas` | booleano | Sello de advertencia aproximado: exceso grasas saturadas (verdadero / falso) |
| `exceso_grasas_totales` | booleano | Sello de advertencia aproximado: exceso grasas totales (verdadero / falso) |
| `exceso_sodio` | booleano | Sello de advertencia aproximado: exceso sodio (verdadero / falso) |
| `exceso_calorias` | booleano | Sello de advertencia aproximado: exceso calorias (verdadero / falso) |
| `sellos` | entero | Cantidad de sellos de advertencia (Ley 27.642), aproximada a partir de los nutrientes (en los polvos para preparar, solo azúcares y grasas: la ley los evalúa sobre lo preparado) |
| `categoria_web` | texto | Categoría de góndola (catálogos de Jumbo, Disco y Vea): la publicada para ese EAN o la que predice el clasificador con confianza >= 0,5; vacía si no hay una confiable |
| `clasificacion_origen` | texto | Cómo se clasificó: reglas y categoría, categoría y reglas acotadas, categoría (alimento predeterminado) o reglas (sin categoría confiable) |
| `contenido_fuente` | texto | De dónde sale el contenido: sepa (campos estructurados), descripcion, referencia (precio de referencia de la cadena), granel o precio (las cadenas informan tamaños distintos y se eligió el que deja el precio por kilo dentro de lo habitual) |
| `contenido_acuerdo` | número | Fracción de las sucursales que informan ese mismo contenido |
| `alimento_id` | texto | Identificador del alimento genérico (referencia/alimentos.csv) |

### dim_tienda

| Columna | Tipo | Descripción |
|---|---|---|
| `id_tienda` | texto | Clave: '<id_comercio>-<id_bandera>-<id_sucursal>' |
| `id_comercio` | entero | Comercio (empresa) en SEPA |
| `id_bandera` | entero | Bandera dentro del comercio |
| `id_sucursal` | texto | Sucursal dentro del comercio |
| `comercio` | texto | Razón social |
| `cuit` | texto | CUIT del comercio |
| `bandera` | texto | Nombre comercial (Carrefour Market, Disco, DIA...) |
| `formato` | texto | Supermercado, Tienda de estación de servicio o Farmacia |
| `tipo_sucursal` | texto | Hipermercado (más de 15 cajas), Supermercado (4 a 15), Autoservicio (1 a 3), Tradicional o Web |
| `sucursal_nombre` | texto | Nombre de la sucursal |
| `direccion` | texto | Calle y número como los publica SEPA |
| `direccion_normalizada` | texto | Dirección según el geocodificador (USIG o Georef), si se consultó |
| `codigo_postal` | texto | Código postal (4 dígitos) |
| `localidad` | texto | Localidad (declarada; en CABA, la Ciudad) |
| `barrio` | texto | Barrio oficial en CABA; en el resto, el declarado (si hay) |
| `comuna` | entero | Comuna (solo CABA) |
| `municipio` | texto | Municipio o gobierno local (Georef) |
| `municipio_id` | texto | Código del municipio (INDEC) |
| `departamento` | texto | Departamento o partido (Georef) |
| `departamento_id` | texto | Código del departamento (INDEC) |
| `provincia` | texto | Provincia (Georef) |
| `provincia_id` | texto | Código de provincia (INDEC) |
| `provincia_iso` | texto | Provincia tal como la declara SEPA (ISO 3166-2) |
| `lat` | número | Latitud validada (WGS84) |
| `lon` | número | Longitud validada (WGS84) |
| `ubicacion_fuente` | texto | sepa (validada), direccion_usig / direccion_georef (corregida por la dirección), centroide_localidad, sepa_dudosa, web o sin_ubicacion |
| `ubicacion_precision` | texto | exacta, aproximada, dudosa, sin_ubicacion o no_aplica (web) |
| `distancia_direccion_m` | número | Distancia entre la coordenada de SEPA y la dirección geocodificada (m) |
| `correccion_coordenada` | texto | Arreglo mecánico aplicado a la coordenada de SEPA (signo, ejes, coma) |
| `lat_sepa` | número | Latitud original de SEPA |
| `lon_sepa` | número | Longitud original de SEPA |
| `es_web` | booleano | Sucursal de venta online (sin ubicación física) |
| `horario_lunes` | texto | Horario del lunes: 'HH:MM-HH:MM' (turnos separados por coma); vacío = cerrado; nulo = no informado |
| `horario_martes` | texto | Horario del martes: 'HH:MM-HH:MM' (turnos separados por coma); vacío = cerrado; nulo = no informado |
| `horario_miercoles` | texto | Horario del miercoles: 'HH:MM-HH:MM' (turnos separados por coma); vacío = cerrado; nulo = no informado |
| `horario_jueves` | texto | Horario del jueves: 'HH:MM-HH:MM' (turnos separados por coma); vacío = cerrado; nulo = no informado |
| `horario_viernes` | texto | Horario del viernes: 'HH:MM-HH:MM' (turnos separados por coma); vacío = cerrado; nulo = no informado |
| `horario_sabado` | texto | Horario del sabado: 'HH:MM-HH:MM' (turnos separados por coma); vacío = cerrado; nulo = no informado |
| `horario_domingo` | texto | Horario del domingo: 'HH:MM-HH:MM' (turnos separados por coma); vacío = cerrado; nulo = no informado |

### fact_precio

| Columna | Tipo | Descripción |
|---|---|---|
| `fecha` | datetime64[s] | Día de los precios (fecha del ZIP de SEPA) |
| `id_producto` | texto | Producto (dim_producto) |
| `id_tienda` | texto | Tienda (dim_tienda) |
| `precio` | número | Precio de lista publicado (ARS) por la presentación |
| `precio_promocion` | número | Precio unitario de la promoción de alcance general vigente, si hay (puede exigir condiciones: llevar 2 unidades, etc.) |
| `cantidad` | número | Presentación que compra el precio: cantidad |
| `unidad` | texto | g, ml, kg (granel) o unidad |
| `precio_normalizado` | número | Precio por kg, litro o unidad (según unidad_normalizada): comparable dentro de la subcategoría |
| `unidad_normalizada` | texto | kg, l o unidad |
| `precio_100g` | número | Precio cada 100 g tal como se compra; dividido por parte_comestible da el de la parte comestible, que es la base de los nutrientes |

