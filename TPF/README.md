# TPF Optimización — El problema de la dieta con precios de SEPA

¿Cuál es la combinación de alimentos más barata que cubre los requerimientos nutricionales de una
persona en Argentina, con los precios reales de todo el país? Es el **problema de la dieta** de
Stigler (1945), el ejemplo fundacional de la programación lineal, con datos de hoy. Como
**complemento**, dónde comprarla: a qué tiendas cercanas a un hogar conviene ir, equilibrando precio
y distancia.

Investigación de Operaciones I · UCA · 2026 2C · Pedro Naón

---

## Estado: base de datos lista, modelo pendiente

| Parte | Estado |
|---|---|
| Base de datos (precios, productos con nutrientes, tiendas) | ✅ Terminada y verificada: [`datos/`](datos/) |
| Introducción: el problema de la dieta original y nuestro planteo | ✅ [`docs/introduccion.md`](docs/introduccion.md) |
| Fuentes | ✅ [`docs/fuentes.md`](docs/fuentes.md) |
| Consigna, plan, modelo, resultados e informe | ⏳ Pendiente |

## Orden de lectura

| # | Archivo | Por qué |
|---|---|---|
| 1 | [`docs/introduccion.md`](docs/introduccion.md) | Qué es el problema de la dieta, cómo lo planteó Stigler, cómo se resolvió con el símplex, qué enseñó y cómo lo vamos a plantear con datos argentinos |
| 2 | [`datos/README.md`](datos/README.md) | La base: las tres tablas, cómo se cruzan, cómo leerlas y su calidad |
| 3 | [`datos/sepa/LEEME.md`](datos/sepa/LEEME.md) | Diccionario de datos completo, columna por columna |
| 4 | [`base_sepa/README.md`](base_sepa/README.md) | Cómo se construye la base, paso a paso, y sus límites conocidos |
| 5 | [`docs/fuentes.md`](docs/fuentes.md) | Todas las fuentes: historia del problema, datos y requisitos nutricionales |

## La base en números

Precios minoristas del **viernes 23 de octubre de 2026** (SEPA, Secretaría de Comercio Interior):

| Tabla | Una fila por | Filas |
|---|---|---:|
| `dim_producto` | producto comestible, con 33 nutrientes cada 100 g, composición, alérgenos, NOVA y sellos (sin precio) | 28.036 |
| `dim_tienda` | sucursal (15 cadenas, 24 jurisdicciones), con coordenada validada y división política | 2.666 |
| `fact_precio` | producto × tienda, con precio publicado y normalizado por kg, litro, unidad y cada 100 g | 8.241.172 |

Los productos se agrupan en **218 alimentos genéricos** ("leche entera", "lentejas secas", "nalga"),
que van a ser los alimentos del modelo.

## Estructura

```
TPF/
├── README.md                 este archivo
├── requirements.txt          para leer la base (pandas, pyarrow)
│
├── Consigna/                 el enunciado (pendiente)
├── Material/                 clases de la cátedra (pendiente)
│
├── datos/
│   ├── README.md             qué es cada tabla y cómo usarla
│   └── sepa/                 LA BASE: dim_producto, dim_tienda, fact_precio (parquet), LEEME.md, calidad/
│
├── base_sepa/                el pipeline que arma la base (proyecto SEPA 2.0)
│   ├── sepa/                 código: lectura de SEPA, productos, nutrientes, tiendas, precios, verificación
│   ├── referencia/           tablas curadas a mano (alimentos genéricos, rótulos de fotos, categorías)
│   └── tests/                57 tests
│
├── docs/
│   ├── introduccion.md       el problema de la dieta: historia, formulación y nuestro planteo
│   ├── fuentes.md            referencias y fuentes de datos
│   ├── plan_de_trabajo.md    el esquema (pendiente de la consigna)
│   └── procedimiento.md      la bitácora (por ahora, la base de datos)
│
├── src/                      código del modelo (pendiente)
├── scripts/                  scripts por pregunta (pendiente)
├── resultados/
│   ├── tablas/               CSVs generados (pendiente)
│   └── graficos/             PNGs generados (pendiente)
└── informe/                  informe.tex + informe.pdf (pendiente; se compila con .vscode/settings.json)
```

## Cómo usar la base

```powershell
pip install -r requirements.txt
```

```python
import pandas as pd
producto = pd.read_parquet("datos/sepa/dim_producto.parquet")
tienda = pd.read_parquet("datos/sepa/dim_tienda.parquet")
precio = pd.read_parquet("datos/sepa/fact_precio.parquet")
```

Para **regenerarla** con el archivo de SEPA del día (baja ~320 MB y, la primera vez, Open Food Facts):

```powershell
cd base_sepa
pip install -r requirements.txt
python -m sepa --descargar      # rehace datos/sepa/
```

## Fuentes principales

- **Historia del problema:** Stigler (1945), *The Cost of Subsistence*; Dantzig (1990), *The Diet
  Problem*; Garille y Gass (2001), *Stigler's Diet Problem Revisited*.
- **Datos:** SEPA (Precios Claros, CC BY 4.0), Open Food Facts (ODbL), USDA FoodData Central SR Legacy
  (dominio público), catálogos online de Jumbo, Disco y Vea, API Georef y datos abiertos del GCBA.
- **Requisitos nutricionales:** Código Alimentario Argentino, Cap. V (Res. GMC 46/03 y 31/06), y Guías
  Alimentarias para la Población Argentina (Ministerio de Salud, 2016).

El detalle, con enlaces, está en [`docs/fuentes.md`](docs/fuentes.md).
