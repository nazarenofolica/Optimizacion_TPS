# SEPA 2.0 — la base de datos del TPF

> En el TPF este proyecto escribe la base en [`../datos/sepa/`](../datos/sepa/) (no en `salida/`): es la
> carpeta que van a leer los modelos. Todo lo demás funciona igual que en el proyecto original.

Convierte un día de precios minoristas de **SEPA** (Precios Claros, Secretaría de Comercio) en un **modelo
estrella** listo para usar en Power BI, pandas o R:

| Tabla | Una fila por | Clave | Contenido |
|---|---|---|---|
| `dim_producto` | producto comestible | `id_producto` (EAN o código interno de cadena) | Nombre, marca, categoría, subcategoría, grupo alimentario, presentación, 33 nutrientes cada 100 g, ingredientes, alérgenos, aptitudes (vegano, sin TACC...), NOVA, sellos. **Sin precio** |
| `dim_tienda` | sucursal | `id_tienda` (`comercio-bandera-sucursal`) | Cadena, bandera, formato, tipo, dirección, coordenada validada, provincia / departamento / municipio (códigos INDEC), barrio y comuna en CABA, horarios |
| `fact_precio` | producto × tienda | `id_producto` + `id_tienda` | Precio publicado, promoción vigente, presentación (500 g, 1 l, 12 unidades, 1 kg a granel) y **precio normalizado** por kg, litro o unidad (y cada 100 g) |

"1 kg de banana a $x" y "500 g de banana a $y" no son comparables tal como se publican: el hecho lleva cada
precio a la misma unidad dentro de cada subcategoría (kg para la banana, litro para la leche, unidad para los
huevos). No es una serie histórica: cada corrida toma un solo día y pisa las salidas.

## Cómo se usa

```powershell
pip install -r requirements.txt

python -m sepa --descargar     # baja el ZIP del día (~320 MB) y arma todo
python -m sepa                 # vuelve a procesar el ZIP que ya está en datos/entrada/
```

| Opción | Qué hace |
|---|---|
| `--descargar` | Baja el último ZIP minorista de la API de datos.produccion.gob.ar y borra el anterior |
| `--zip RUTA` | Usa ese ZIP |
| `--actualizar-off` | Vuelve a bajar el dump de Open Food Facts (si no, se reutiliza 30 días) |
| `--actualizar-web` | Vuelve a recorrer los catálogos online de Jumbo, Disco y Vea |

La primera corrida baja a `datos/cache/` Open Food Facts (~1,2 GB), USDA (~6 MB) y consulta las APIs
geográficas; las siguientes reutilizan todo y tardan unos minutos. El resultado queda en `../datos/sepa/`, con
un `LEEME.md` que trae el **diccionario de datos** de las tres tablas y el resumen de la corrida.

Tests: `python -m unittest discover -s tests -v`

## Estructura

```
SEPA 2.0/
├── sepa/                     el pipeline (python -m sepa)
│   ├── __main__.py           orquesta los pasos
│   ├── config.py             rutas y todos los umbrales, con su porqué
│   ├── fuentes/              descarga y lectura: SEPA, Open Food Facts, USDA, catálogos web, geografía
│   ├── producto/             dim_producto: identificación, contenido, categoría, clasificación,
│   │                         nutrientes, similitud, composición
│   ├── tienda/               dim_tienda: coordenadas, división política, horarios
│   ├── precio/               fact_precio: precios anormales y normalización
│   ├── verificacion.py       controles que las tres tablas cumplen siempre
│   └── salida.py             escritura, reportes de calidad y LEEME
├── referencia/               tablas curadas a mano (se editan para corregir o ampliar)
│   ├── alimentos.csv         alimentos genéricos: reglas de clasificación, equivalencia USDA, densidad,
│   │                         parte comestible, unidad de precio, grupo alimentario
│   ├── categorias_web.csv    categoría de góndola -> alimentos compatibles
│   ├── composicion_alimentos.csv   alérgenos y aptitudes "por naturaleza" de cada alimento
│   ├── rotulos_fotos.csv     tablas nutricionales leídas de fotos de envases
│   └── nutricion_manual.csv  correcciones puntuales de nutrientes
├── tests/
├── datos/                    (no se versiona) entrada/ con el ZIP del día y cache/ con las fuentes
└── (../datos/sepa/)         la salida: dim_producto, dim_tienda, fact_precio (parquet y CSV), calidad/, LEEME.md
```

## Cómo se arma cada tabla

### dim_producto

1. **Identificación.** Cada cadena describe el producto a su manera; se toma la descripción más usada y un
   nombre legible (la descripción más completa, sin tamaños ni códigos de envase).
2. **Contenido neto.** De los campos estructurados de SEPA, de la unidad del precio de referencia de cada
   cadena (Carrefour pone ahí el contenido real) o de la descripción; se corrigen las comas corridas
   (".50 gr" por 500 g, "300 ml" por 3 l) y los separadores de miles ("2.250CC" son 2250 cc), los packs
   ("354cc sixpack" son 6 latas; "12X500G" es el bulto, se vende el paquete de 500 g), las botellas de "75 ml"
   que son de 75 cl, el "1 GRM" que es "una unidad" y la cantidad de saquitos cargada como gramos ("X 25 UNI"
   con referencia "25 GRS"); gana lo que informan más sucursales. Si las fuentes dicen tamaños muy distintos
   (la caja de 50 g de cápsulas y la cápsula de 5 g; la descripción contra el precio de referencia), decide el
   precio: gana el contenido que deja el precio por kilo dentro de lo habitual de su subcategoría.
3. **Categoría de góndola.** La de los catálogos online de Jumbo, Disco y Vea si el EAN está publicado; si no, la
   predice un clasificador de texto entrenado con ~100 mil productos categorizados (acierta la categoría en el
   93 % de los casos y el departamento en el 96 %; con confianza ≥ 0,5, que alcanza al 90 % de los productos,
   en el 97 % y el 99 %).
4. **Clasificación** en ~220 alimentos genéricos por reglas sobre la descripción (`referencia/alimentos.csv`),
   **verificada con la categoría de góndola**: si no coinciden, se reclasifica dentro de lo compatible o se
   excluye; lo que la góndola dice que no es comida (limpieza, bazar, perfumería) se descarta. Una categoría
   publicada vale solo si el nombre de la web se parece al de SEPA (hay cadenas que reusan EAN de otros
   productos); una predicha no alcanza para contradecir a una regla ("bife de chorizo" no es un chorizo). Lo
   que se vende en mililitros no puede ser un polvo (un jugo listo no es un jugo en polvo). La comida
   preparada (sándwiches, platos de rotisería, ensaladas armadas) queda fuera del alcance, y nada se pierde
   sin motivo: lo que no se clasifica figura en `calidad/productos_excluidos.csv` con la razón (por ejemplo,
   "góndola de comida, pero la descripción no identifica el alimento").
5. **Presentación y normalización**: forma de venta, gramos del envase y factor a kg, litro o unidad (líquidos
   con su densidad; lo que se vende por unidad sin peso, con el peso típico, marcado como estimado).
6. **Nutrientes** (33, cada 100 g comestibles, sin vacíos). Fuente, en orden de confianza: carga manual, rótulo
   del catálogo web, rótulo leído de la foto del envase, Open Food Facts, los productos con rótulo más parecidos
   (imputación por similitud, validada) y el alimento genérico (USDA o el rótulo más representativo de los
   verificados: un perfil real, que cierra). Cada rótulo pasa controles (Atwater, kcal vs kJ, sumas,
   saturadas, azúcares, sodio y colesterol posibles, energía frente al genérico, nombre del producto en Open
   Food Facts); un rótulo que no se parece a su alimento marca el producto como mal clasificado y lo excluye,
   salvo dos convenciones conocidas en las que solo se descarta el rótulo: los polvos e infusiones para
   preparar (jugos, gelatinas, leche en polvo, yerba) que declaran lo preparado, y las porciones ínfimas
   redondeadas a 0 kcal (un rocío vegetal). Los jugos en polvo llevan los valores cada 100 g de polvo; los
   chicles y pastillas sin azúcar, las gelatinas y las mermeladas light tienen su propio genérico, y un
   producto light, diet o sin azúcar solo toma el rótulo de vecinos que también lo son.
7. **Composición**: alérgenos (sí / no / desconocido), trazas, apto vegetariano y vegano, sin TACC, sin lactosa,
   NOVA, aditivos, azúcar agregada, edulcorantes, aceite de palma; y sellos de advertencia aproximados (en los
   polvos para preparar, que la ley evalúa sobre lo preparado, solo los de azúcares y grasas).
8. **Precio plausible**: un producto cuyo precio por kg o litro está por debajo de la quinta parte del
   percentil 10 de su subcategoría o por encima de 8 veces el percentil 90, o muy por debajo del de sus
   "gemelos" (los casi iguales que venden otras cadenas), tiene el contenido mal cargado o un precio
   desactualizado y se excluye (sin poner precio en la dimensión). Percentiles y no la mediana porque hay
   subcategorías muy heterogéneas: la sal fina y la sal marina en molinillo, el vino de mesa y el de alta gama.
   Un producto de lujo (champagne, jamón ibérico) no se excluye: su envase también es caro y está en muchas
   góndolas, mientras que un contenido mal cargado deja el envase en precio normal.

### dim_tienda

Se arreglan las coordenadas con errores mecánicos (signo, ejes invertidos, coma corrida) y cada una se valida
con la API **Georef** contra la provincia y la localidad declaradas; en CABA, además, contra la dirección
(normalizador USIG, tolerancia 300 m). Una coordenada que no cierra se corrige por la dirección o, si no se
encuentra, por el centroide de la localidad; si nada es confiable, se conserva y queda marcada como dudosa.
La provincia, el departamento y el municipio salen de la coordenada final; en CABA, el barrio y la comuna
oficiales.

### fact_precio

Precios de lista de los productos y tiendas de las dimensiones. Se descartan los anormales: la referencia de
cada producto es la mediana de las medianas de cada cadena; dentro de x2 / ÷2 un precio queda siempre (una
estación de servicio cobra una gaseosa 1,7 veces lo que un supermercado; una cadena de descuento, 40 % menos),
más de 3 veces arriba o abajo se descarta siempre, y en el medio queda si es coherente con la dispersión
normal del producto. Con solo dos cadenas que no coinciden no hay mayoría: gana la que tiene un precio posible
para su subcategoría (una cadena publica el precio de una caja de six-packs como si fuera uno). Los comercios
cuyo archivo no es del día (uno repite un archivo de 2025) se excluyen enteros.

Lo que vende una sola cadena no tiene con quién compararse: se compara con sus gemelos de otras cadenas
(descripción casi igual, contenido parecido, precio con consenso de al menos dos cadenas, ponderado por
tiendas). Así aparecen las cadenas chicas que siguen publicando precios de hace años para códigos viejos (una
mayonesa a $156 el litro, un jugo en polvo a $25): esos productos quedan afuera con su motivo.

## Calidad

`../datos/sepa/calidad/` tiene todo lo excluido con su motivo (`productos_excluidos.csv`), los precios descartados,
las ubicaciones corregidas o dudosas, los nutrientes de cada alimento genérico y la validación de la
imputación por similitud. `sepa/verificacion.py` controla en cada corrida que las tablas cumplan reglas que
nunca deben romperse (claves únicas, integridad referencial, nutrientes posibles, composición coherente,
precios positivos, coordenadas dentro del país); si una regla crítica falla, la corrida se detiene sin tocar
la base y deja sus tablas en `datos/cache/corrida_fallida/` para revisarlas.

**Para corregir o ampliar**: las reglas de clasificación y los parámetros de cada alimento están en
`referencia/alimentos.csv`; la compatibilidad con las categorías, en `referencia/categorias_web.csv`; los
umbrales, en `sepa/config.py`.

## Fuentes

- **SEPA** — Precios Claros, Secretaría de Comercio (datos.produccion.gob.ar).
- **Open Food Facts** — rótulos, ingredientes y alérgenos (licencia ODbL).
- **Catálogos online de Jumbo, Disco y Vea** — rótulos, ingredientes, certificaciones y categorías.
- **USDA FoodData Central, SR Legacy** — composición de alimentos (dominio público).
- **API Georef** (Servicio de Normalización de Datos Geográficos de Argentina) y **USIG** (GCBA) — ubicación.
- **Barrios y comunas de CABA** — datos abiertos del GCBA.

## Límites conocidos

- Los alimentos frescos (frutas, verduras, carnes a granel) y las marcas propias sin rótulo usan los nutrientes
  de su alimento genérico o de productos parecidos: es la mejor estimación disponible, no un análisis del
  producto. `fuente_nutrientes` dice cuál se usó en cada fila.
- Lo que se vende por unidad sin peso informado (una lechuga, una palta) se normaliza con un peso típico:
  `base_normalizacion = peso_unidad_estimado`.
- Los jugos concentrados para diluir se tratan como jugos listos: su precio por litro es el del concentrado y
  sus nutrientes, los del jugo genérico salvo que tengan rótulo propio.
- Café, té y yerba llevan lo que declaran sus rótulos, que en general describen la infusión (casi sin
  calorías), no el producto seco.
- Algunas cadenas publican precios de sucursales sin su ficha (sin dirección ni coordenada): quedan en
  `dim_tienda` con `ubicacion_precision = sin_ubicacion`.
