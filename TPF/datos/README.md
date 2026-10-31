# Datos del TPF

La base de datos del trabajo está en [`sepa/`](sepa/): un **modelo estrella** con los precios
minoristas de todo el país del **viernes 23 de octubre de 2026**, publicados por el sistema SEPA
(Precios Claros) de la Secretaría de Comercio, cruzados con nutrientes y composición de cada producto.

Está lista para usar: no hace falta correr nada para leerla. La arma el pipeline de
[`../base_sepa/`](../base_sepa/), que explica paso a paso cómo se construye cada tabla.

## Las tres tablas

| Archivo | Una fila por | Filas | Clave |
|---|---|---:|---|
| [`sepa/dim_producto.parquet`](sepa/dim_producto.parquet) | producto comestible | 28.036 | `id_producto` (EAN de 13 dígitos o código interno de cadena) |
| [`sepa/dim_tienda.parquet`](sepa/dim_tienda.parquet) | sucursal | 2.666 | `id_tienda` (`comercio-bandera-sucursal`) |
| [`sepa/fact_precio.parquet`](sepa/fact_precio.parquet) | producto × tienda | 8.241.172 | `id_producto` + `id_tienda` |

```
              dim_producto (28.036)                      dim_tienda (2.666)
   nutrientes cada 100 g, composición,            cadena, formato, dirección, coordenada
   grupo alimentario, presentación — SIN precio   validada, provincia / departamento / municipio
                     │ 1                                   1 │
                     │                                       │
                     └────────── N  fact_precio  N ──────────┘
                         precio publicado, promoción, presentación,
                         precio normalizado por kg / l / unidad y cada 100 g
```

**`dim_producto`** (86 columnas). Nombre, marca, categoría y subcategoría; grupo de las Guías
Alimentarias para la Población Argentina; alimento genérico (`alimento_id`: 218, como "leche
entera", "lentejas secas" o "nalga"); presentación (contenido, gramos del envase, parte comestible,
densidad); **33 nutrientes cada 100 g comestibles** sin vacíos (energía, macronutrientes, fibra,
sodio, 8 minerales y 13 vitaminas) con su fuente (`fuente_nutrientes`); ingredientes, alérgenos,
aptitud vegetariana, vegana, sin TACC y sin lactosa, grado NOVA y sellos de advertencia aproximados.

**`dim_tienda`** (39 columnas). Comercio (15 cadenas, 23 banderas), formato, dirección, coordenada
validada contra la API Georef (2.648 exactas, 2 aproximadas, 5 dudosas, 10 sin ubicación), provincia,
departamento y municipio con códigos INDEC, barrio y comuna en CABA, y horarios. Cubre las 24
jurisdicciones.

**`fact_precio`**. Precio de lista, precio de promoción vigente (cuando hay), presentación (500 g,
1 l, 12 unidades, 1 kg a granel) y dos precios comparables:

- `precio_normalizado`: por kg, litro o unidad, según la subcategoría (kg para la banana, litro para la
  leche, unidad para los huevos). Así "1 kg de banana a $x" y "500 g de banana a $y" se comparan.
- `precio_100g`: cada 100 g tal como se compra. Dividido por `dim_producto.parte_comestible` da el
  precio de 100 g comestibles, que es la base de los nutrientes.

El diccionario completo, columna por columna, está en [`sepa/LEEME.md`](sepa/LEEME.md).

## Cómo leerla

```python
import pandas as pd

producto = pd.read_parquet("datos/sepa/dim_producto.parquet")
tienda = pd.read_parquet("datos/sepa/dim_tienda.parquet")
precio = pd.read_parquet("datos/sepa/fact_precio.parquet")

# precio de 100 g comestibles de cada producto en cada tienda, con sus nutrientes
p = precio.merge(producto, on="id_producto").merge(tienda[["id_tienda", "provincia"]], on="id_tienda")
p["precio_100g_comestible"] = p["precio_100g"] / p["parte_comestible"]
```

`fact_precio` tiene 8,2 millones de filas: con poca memoria conviene leer solo las columnas que se
usan (`pd.read_parquet(..., columns=[...])`).

## Calidad

[`sepa/calidad/`](sepa/calidad/) documenta lo que no entró y por qué:

| Archivo | Contenido |
|---|---|
| `productos_excluidos.csv` | 3.502 productos que parecían comida y quedaron afuera, cada uno con su motivo |
| `precios_descartados.csv` | precios anormales descartados (6.337) |
| `tiendas_ubicacion.csv` | coordenadas corregidas o dudosas |
| `nutrientes_genericos.csv` | perfil nutricional de cada uno de los 218 alimentos genéricos y su fuente |
| `validacion_similitud.csv` | error de la imputación de nutrientes por productos parecidos |
| `verificacion.csv` | los 52 controles que la base cumple en cada corrida (ningún crítico falla) |
| `lectura_comercios.csv` | archivos de cada cadena leídos, omitidos o desactualizados |

Origen de los nutrientes: el 30 % de los productos tiene rótulo propio (catálogos web, Open Food
Facts o foto del envase), el 19 % toma el de productos casi iguales con rótulo y el 51 % usa el de su
alimento genérico (sobre todo frescos y marcas propias). Los límites conocidos de la base están al
final de [`../base_sepa/README.md`](../base_sepa/README.md).

## Regenerarla

```powershell
cd base_sepa
pip install -r requirements.txt
python -m sepa --descargar     # baja el ZIP del día de SEPA (~320 MB) y rehace datos/sepa/
```

La primera corrida baja además Open Food Facts (~1,2 GB) y USDA a `base_sepa/datos/cache/` (no se
versiona). Cada corrida **pisa** `datos/sepa/`: la base es de un solo día, no una serie histórica.
