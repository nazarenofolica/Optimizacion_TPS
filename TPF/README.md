# TPF Optimización — El problema de la dieta con precios de SEPA

¿Cuál es la combinación de alimentos más barata que cubre los requerimientos nutricionales de una
persona en Argentina, con los precios reales de todo el país? Es el **problema de la dieta** de
Stigler (1945), el ejemplo fundacional de la programación lineal, con datos de hoy. Como
**complemento**, dónde comprarla: a qué tiendas cercanas a un hogar conviene ir, equilibrando precio
y distancia.

Investigación de Operaciones I · UCA · 2026 2C · Pedro Naón

---

## Estado

| Parte | Estado |
|---|---|
| Base de datos (precios, productos con nutrientes, tiendas) | ✅ Terminada y verificada: [`datos/`](datos/) |
| Introducción: el problema de la dieta original y nuestro planteo | ✅ [`docs/introduccion.md`](docs/introduccion.md) |
| Fuentes | ✅ [`docs/fuentes.md`](docs/fuentes.md) |
| **POC: canasta saludable** (modelo en dos etapas, página web, búsqueda por tiempo caminando) | ✅ [`base_sepa/canasta/`](base_sepa/canasta/), página en [`datos/sepa/canasta.html`](datos/sepa/canasta.html) |
| **MVP, etapa 1** (objetivo "Aumentar de peso", el agua como restricción en tres modos, un caso que no llega a las 37 metas) | ✅ 20/11/2026: [`docs/ROADMAP.md`](docs/ROADMAP.md) |
| **MVP, etapa 2** (compra en dos supermercados: binarias de visita resueltas por pares, conviene si cubre mejor las metas o ahorra ≥ 3 % y ≥ $1.000) | ✅ 20/11/2026: [`docs/ROADMAP.md`](docs/ROADMAP.md), con las etapas 4 a 6 que siguen |
| **MVP, etapa 3** (ETL diario y CI: cada día se baja SEPA, se rearma la base, se exporta la página y se publica en GitHub Pages; tests en cada push) | ✅ 21/11/2026 en el repo, falta activarla: [`docs/DESPLIEGUE.md`](docs/DESPLIEGUE.md) |
| **MVP, etapa 4** (sin cerdo, halal y kosher con lo verificable por ingredientes; seis condiciones médicas que cambian metas con su fuente y avisan si requieren supervisión) | ✅ 21/11/2026: [`docs/ROADMAP.md`](docs/ROADMAP.md) |
| **MVP, etapa 5** (promociones con condiciones: las leyendas de SEPA clasificadas, 2×1, 2.ª al 70 %, llevando n y porcentajes en el modelo; nunca las que piden banco o tarjeta; ticket con el descuento y el ahorro) | ✅ 21/11/2026: [`docs/ROADMAP.md`](docs/ROADMAP.md). Se aplican desde la próxima actualización de la base |
| **MVP, etapa 6** (contarlo en texto libre: un LLM de Groq traduce lo que escribe la persona, o una prescripción, al formulario, que ella confirma; validado contra `config.py`; en la página local) | ✅ 21/11/2026 con respuestas simuladas, falta probarlo con una clave real: [`docs/ROADMAP.md`](docs/ROADMAP.md) |
| Camino a MVP y producción; investigación de herramientas | 📄 [`docs/ROADMAP.md`](docs/ROADMAP.md), [`docs/GITHUB_RESEARCH.md`](docs/GITHUB_RESEARCH.md) |
| Presentación del POC, con la demo en vivo | ✅ [`informe/presentacion.html`](informe/presentacion.html): `python informe/presentar.py` |
| Consigna, resultados e informe | ⏳ Pendiente |

## Probar la canasta

```powershell
cd base_sepa
pip install -r requirements.txt
copy .env.example .env          # claves gratuitas: OpenRouteService (ORS_API_KEY) y Groq (GROQ_API_KEY)
python -m canasta               # abre la página en http://localhost:8765 (Ctrl+C para cerrar)
python -m unittest discover -s tests -v
```

Sin clave de rutas, la página funciona igual pero estima los tiempos caminando por distancia y lo avisa. Con la de
Groq, el paso 1 ofrece "Contalo con tus palabras" (solo en la página local). Más opciones en
[`base_sepa/README.md`](base_sepa/README.md#canasta-saludable-poc).

## Orden de lectura

| # | Archivo | Por qué |
|---|---|---|
| 1 | [`docs/introduccion.md`](docs/introduccion.md) | Qué es el problema de la dieta, cómo lo planteó Stigler, cómo se resolvió con el símplex, qué enseñó y cómo lo vamos a plantear con datos argentinos |
| 2 | [`datos/README.md`](datos/README.md) | La base: las tres tablas, cómo se cruzan, cómo leerlas y su calidad |
| 3 | [`datos/sepa/LEEME.md`](datos/sepa/LEEME.md) | Diccionario de datos completo, columna por columna |
| 4 | [`base_sepa/README.md`](base_sepa/README.md) | Cómo se construye la base, paso a paso, y sus límites conocidos |
| 5 | [`docs/fuentes.md`](docs/fuentes.md) | Todas las fuentes: historia del problema, datos y requisitos nutricionales |

## La base en números

Precios minoristas del **sábado 21 de noviembre de 2026** (SEPA, Secretaría de Comercio Interior):

| Tabla | Una fila por | Filas |
|---|---|---:|
| `dim_producto` | producto comestible, con 33 nutrientes cada 100 g, composición, alérgenos, NOVA y sellos (sin precio) | 27.949 |
| `dim_tienda` | sucursal (15 cadenas, 24 jurisdicciones), con coordenada validada, división política y fecha de sus precios | 2.651 |
| `fact_precio` | producto × tienda, con precio publicado y normalizado por kg, litro, unidad y cada 100 g | 8.309.213 |
| `promocion` | promoción de un precio (hasta 2), clasificada: si la canasta la aplica y por qué no | 1.161.802 (996.184 aplicables) |

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
│   └── tests/                254 tests (pipeline y canasta)
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
python -m sepa --diario         # lo mismo sin intervención (la primera vez también recorre los catálogos web)
```

Una vez activado el ETL diario ([`docs/DESPLIEGUE.md`](docs/DESPLIEGUE.md)), GitHub Actions hace esto todos los días
y publica la página con los precios del día en https://nazarenofolica.github.io/Optimizacion_TPS/, sin commitear la
base del día (la versionada en `datos/sepa/` queda como la del 21/11/2026).

## Fuentes principales

- **Historia del problema:** Stigler (1945), *The Cost of Subsistence*; Dantzig (1990), *The Diet
  Problem*; Garille y Gass (2001), *Stigler's Diet Problem Revisited*.
- **Datos:** SEPA (Precios Claros, CC BY 4.0), Open Food Facts (ODbL), USDA FoodData Central SR Legacy
  (dominio público), catálogos online de Jumbo, Disco y Vea, API Georef y datos abiertos del GCBA.
- **Requisitos nutricionales:** Código Alimentario Argentino, Cap. V (Res. GMC 46/03 y 31/06), y Guías
  Alimentarias para la Población Argentina (Ministerio de Salud, 2016).

El detalle, con enlaces, está en [`docs/fuentes.md`](docs/fuentes.md).
