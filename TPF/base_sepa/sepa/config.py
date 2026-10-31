"""
Rutas y parámetros de SEPA 2.0. Todo lo que se puede discutir o ajustar
(umbrales de limpieza de precios, controles nutricionales, tolerancias
geográficas) está acá, con su unidad y el porqué.
"""

from __future__ import annotations

import logging
import math
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================
# CARPETAS
# ============================================================

DIR_DATOS = BASE_DIR / "datos"                 # no se versiona: se baja o se regenera
DIR_ENTRADA = DIR_DATOS / "entrada"            # el ZIP de SEPA del día (uno solo)
DIR_CACHE = DIR_DATOS / "cache"                # fuentes externas, se reutilizan entre corridas
DIR_REFERENCIA = BASE_DIR / "referencia"       # tablas curadas a mano (se versionan)
# En el TPF la base va a TPF/datos/sepa/, donde la leen los modelos. Cada corrida borra y rehace esa carpeta.
DIR_SALIDA = BASE_DIR.parent / "datos" / "sepa"  # dim_producto, dim_tienda, fact_precio
DIR_CALIDAD = DIR_SALIDA / "calidad"           # reportes de control y lo excluido, con su motivo

# Open Food Facts: dump completo (~1,2 GB), se reutiliza mientras tenga menos de DIAS_VIGENCIA_OFF días.
DIR_OFF = DIR_CACHE / "openfoodfacts"
RUTA_OFF_DUMP = DIR_OFF / "products.csv.gz"
RUTA_OFF_SELECCION = DIR_OFF / "seleccion.parquet"   # solo los EAN que interesan (se arma en una pasada)
URL_OFF_DUMP = "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"
DIAS_VIGENCIA_OFF = 30

# USDA FoodData Central, SR Legacy (tabla de composición de laboratorio, dominio público).
DIR_USDA = DIR_CACHE / "usda"
URL_USDA_SR_LEGACY = "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip"

# Catálogos online de Jumbo, Disco y Vea (Cencosud, plataforma VTEX): rótulo, ingredientes, alérgenos.
DIR_WEB = DIR_CACHE / "web"

# Geografía: API Georef (Servicio de Normalización de Datos Geográficos de Argentina), normalizador de
# direcciones de la Ciudad (USIG) y barrios/comunas de CABA (datos abiertos del GCBA).
DIR_GEO = DIR_CACHE / "geo"

# Tablas de referencia curadas a mano.
RUTA_ALIMENTOS = DIR_REFERENCIA / "alimentos.csv"                       # alimentos genéricos y reglas
RUTA_COMPOSICION_ALIMENTOS = DIR_REFERENCIA / "composicion_alimentos.csv"
RUTA_ROTULOS_FOTOS = DIR_REFERENCIA / "rotulos_fotos.csv"               # rótulos leídos de fotos de envases
RUTA_NUTRICION_MANUAL = DIR_REFERENCIA / "nutricion_manual.csv"         # correcciones puntuales
RUTA_CATEGORIAS_WEB = DIR_REFERENCIA / "categorias_web.csv"           # categoría de góndola -> alimentos

# Precios del día leídos del ZIP: se bajan a disco mientras se procesan los productos (14 millones de filas)
# y se recargan filtrados para armar el hecho.
RUTA_PRECIOS_DEL_DIA = DIR_DATOS / "precios_del_dia.parquet"

# Salidas
RUTA_DIM_PRODUCTO = DIR_SALIDA / "dim_producto"
RUTA_DIM_TIENDA = DIR_SALIDA / "dim_tienda"
RUTA_FACT_PRECIO = DIR_SALIDA / "fact_precio"

# ============================================================
# SEPA
# ============================================================

# Dataset minorista de datos.produccion.gob.ar ("Precios Claros - Base SEPA"): ventana de 7 ZIPs diarios.
DATASET_SEPA_MINORISTA = "6f47ec76-d1ce-4e34-a7e1-621fe9b1d0b5"

# Un comercio cuyos precios tienen más de estos días respecto de la fecha del ZIP no publica precios
# de ese día (hay uno que repite un archivo de 2025): se excluye entero.
DIAS_MAXIMOS_DESACTUALIZADO = 7

# Comercios que no son supermercados (sí son puntos de venta de alimentos): se identifican en dim_tienda.
FORMATO_COMERCIO = {
    3: "Tienda de estación de servicio",    # DEHEZA (YPF)
    4: "Tienda de estación de servicio",    # Estación Lima
    23: "Tienda de estación de servicio",   # Axion Energy
    36: "Farmacia",                         # Farmacity
}

# ============================================================
# CLASIFICACIÓN (dim_producto)
# ============================================================

# Categoría de góndola predicha por el clasificador de texto (sepa/producto/categorias.py): desde esta
# probabilidad se trata como la categoría exacta (puede reclasificar o vetar); entre la media y la fuerte solo
# sirve para descartar un producto cuya regla la contradice.
CATEGORIA_PROB_FUERTE = 0.8
CATEGORIA_PROB_MEDIA = 0.5

# ============================================================
# LIMPIEZA DE PRECIOS (fact_precio)
# ============================================================
#
# Para cada producto, la referencia es la mediana de las medianas de cada cadena (cada cadena vota una
# vez: una cadena que cargó mal un precio en todas sus sucursales no mueve la referencia). Cada precio
# de sucursal se compara con esa referencia en escala logarítmica:
#   - dentro de x2 / ÷2: queda siempre (una estación de servicio cobra una gaseosa 1,7 veces lo que un
#     supermercado; una cadena de descuento, 40 % menos: son precios reales);
#   - más allá de x3 / ÷3: se descarta siempre (pack, unidad o peso mal cargado, precio de hace años);
#   - en el medio: queda si es coherente con la dispersión del producto (3,5 desvíos robustos).
TOLERANCIA_SIEMPRE = math.log(2.0)
TOLERANCIA_MAXIMA = math.log(3.0)
Z_ROBUSTO = 3.5
PRECIO_MINIMO = 1.0              # ARS: por debajo es un error de carga
PRECIO_MAXIMO = 50_000_000.0     # ARS

# Una promoción (promo 1: alcance general, sin tarjetas ni segmentos) vale si está vigente, es menor al
# precio de lista y no menor a esta fracción de él (hay descuentos reales del 80 %; menos es un error).
PROMO_FRACCION_MINIMA = 0.1

# Precio normalizado de un producto (mediana entre sucursales) frente a la distribución de su subcategoría (todos
# sus precios: pesa lo que se vende en más tiendas). Por debajo de la quinta parte del percentil 10 o por encima
# de 8 veces el percentil 90 es un contenido mal cargado (gramos por kilos, un pack tomado como unidad) o un
# precio que no es de hoy; el producto no entra. Los percentiles, y no la mediana, porque hay subcategorías muy
# heterogéneas: la sal fina y la sal marina en molinillo, el vino de mesa y el de alta gama.
PERCENTIL_SUBCATEGORIA_BAJO = 0.10
PERCENTIL_SUBCATEGORIA_ALTO = 0.90
RATIO_SUBCATEGORIA_ABAJO = 5.0
RATIO_SUBCATEGORIA_ARRIBA = 8.0
# Salvo un producto de lujo: el precio del envase también es más de 3 veces el percentil 90 de los envases de su
# subcategoría y está en muchas góndolas (un contenido mal cargado deja el precio del envase en lo normal).
RATIO_ENVASE_LUJO = 3.0
MIN_TIENDAS_LUJO = 10
# Contenido en disputa (las cadenas informan tamaños distintos, contenido.RATIO_ALTERNATIVO): se cambia al
# alternativo si el elegido deja el precio por kilo fuera de [p10 / 2, p90 x 2] de su subcategoría y el
# alternativo, dentro de [p10, p90].
RATIO_DISPUTA = 2.0
# Gemelos de un producto (limpieza.ratio_gemelos): los casi iguales con precio de consenso. Costar menos de la
# quinta parte que ellos no es genuino (precio desactualizado; una sal común cuesta la cuarta parte que una de
# marca); costar más puede serlo (la línea premium, lo importado), salvo que sea muchísimo más.
K_GEMELOS = 5
SIMILITUD_GEMELO = 0.6
CONTENIDO_GEMELO = 1.5
MAX_TIENDAS_GEMELOS = 30
RATIO_GEMELOS_ABAJO = 5.0
RATIO_GEMELOS_ARRIBA = 12.0

# ============================================================
# CONTROLES NUTRICIONALES (cada 100 g)
# ============================================================

TOLERANCIA_ENERGIA_REL = 0.25    # energía declarada vs Atwater (4 / 4 / 9 / 7 alcohol; fibra a 2 o a 0)
TOLERANCIA_ENERGIA_ABS = 20.0    # kcal
MAX_GRAMOS_100 = 105.0           # proteínas + carbohidratos + grasas + fibra + sal
MAX_KCAL_100 = 950.0             # el aceite puro tiene ~900
SODIO_MAXIMO_MG = 40_000.0       # la sal pura tiene ~38.800 mg cada 100 g
# Energía de un rótulo frente a la de su alimento genérico: fuera de x2,5 / ÷2,5 (y a más de 50 kcal)
# es una tabla por porción cargada como por 100 g o un producto mal clasificado.
RATIO_ENERGIA_GENERICO = 2.5
TOLERANCIA_ENERGIA_GENERICO_ABS = 50.0
# Energía contra la mediana de su categoría de Open Food Facts.
MIN_POR_CATEGORIA_OFF = 5
RATIO_CATEGORIA_OFF = 2.5
TOLERANCIA_CATEGORIA_OFF_ABS = 50.0

# ============================================================
# GEOGRAFÍA (dim_tienda)
# ============================================================

URL_GEOREF = "https://apis.datos.gob.ar/georef/api"
URL_USIG = "https://servicios.usig.buenosaires.gob.ar/normalizar/"
URL_BARRIOS_CABA = ("https://cdn.buenosaires.gob.ar/datosabiertos/datasets/ministerio-de-educacion/"
                    "barrios/barrios.geojson")
# Coordenada de SEPA frente a la dirección geocodificada: hasta esta distancia se confía en SEPA.
TOLERANCIA_DIRECCION_M = 300.0
# Fuera de CABA la geocodificación por altura es menos precisa: se corrige solo si la diferencia es grande.
TOLERANCIA_DIRECCION_INTERIOR_M = 2_000.0
# Rectángulo que contiene a la Argentina continental e insular (para atrapar signos y ejes cambiados).
LAT_ARGENTINA = (-55.2, -21.7)
LON_ARGENTINA = (-73.7, -53.5)

FORMATO_LOG = "%(asctime)s [%(levelname)s] %(message)s"


def configurar_logging(verbose: bool = False) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format=FORMATO_LOG,
                        datefmt="%H:%M:%S", stream=sys.stdout)
