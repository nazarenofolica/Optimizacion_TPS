"""
Escritura de las salidas: las tres tablas del modelo estrella (parquet y CSV),
los reportes de calidad y salida/LEEME.md con el diccionario de datos y el
resumen de la corrida (generado a partir de las tablas, así nunca se
desactualiza).

CSV: separador ";" y coma decimal (se abren directo en Excel en español),
UTF-8 con BOM. El hecho también va comprimido (fact_precio.csv.gz): tiene
millones de filas, más de lo que abre Excel; para Power BI, pandas o R
conviene el parquet.
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime

import pandas as pd

from sepa import config as cfg
from sepa.producto.nutrientes import NUTRIENTES

logger = logging.getLogger("sepa.salida")

ALERGENOS = ["gluten", "leche", "huevo", "mani", "frutos_secos", "soja", "pescado", "mariscos", "sesamo"]
SELLOS = ["exceso_azucares", "exceso_grasas_saturadas", "exceso_grasas_totales", "exceso_sodio", "exceso_calorias"]

COLUMNAS_PRODUCTO = {
    "id_producto": "Clave. EAN de 13 dígitos (con ceros a la izquierda) o, para lo que la cadena identifica con un "
                   "código propio (frescos, balanza), 'cadena<id_comercio>-<código>'",
    "tipo_codigo": "EAN o Interno de cadena",
    "id_comercio_interno": "Para códigos internos, el comercio (cadena) dueño del código",
    "nombre": "Nombre legible (la descripción más completa entre las cadenas, sin tamaños ni códigos de envase)",
    "marca": "Marca",
    "descripcion_sepa": "Descripción tal como la publica la mayoría de las sucursales",
    "categoria": "Rubro (Lácteos, Carne vacuna, Frutas, Bebidas...)",
    "subcategoria": "Alimento genérico (Leche entera, Nalga, Banana...): el nivel para comparar precios",
    "grupo_alimentario": "Grupo de las Guías Alimentarias para la Población Argentina (más agua e infusiones, "
                         "condimentos y comidas preparadas)",
    "forma_venta": "Envase, Granel (precio por kg) o Por unidad",
    "contenido": "Contenido neto del envase (en unidad_contenido); a granel, 1000 g",
    "unidad_contenido": "g o ml",
    "unidades": "Unidades que trae (huevos x 12, alfajores x 6); vacío si no aplica",
    "unidad_normalizada": "Unidad común de su subcategoría para comparar precios: kg, l o unidad",
    "cantidad_normalizada": "Cuántos kg, l o unidades compra el precio publicado (precio / cantidad_normalizada = "
                            "precio por unidad normalizada)",
    "gramos_envase": "Gramos que compra el precio publicado (líquidos con su densidad)",
    "base_normalizacion": "directa, densidad (g <-> ml) o peso_unidad_estimado (se vende por unidad sin peso "
                          "informado: se usa el peso típico de la unidad, aproximado)",
    "parte_comestible": "Fracción comestible (1 en envasados; banana 0,64; pollo entero 0,70)",
    "densidad_g_ml": "Densidad usada para los líquidos (g por ml)",
    "porcion_g": "Porción de referencia del alimento genérico (g o ml)",
    "fuente_nutrientes": "Origen de los nutrientes: rotulo_web, rotulo_web+off, rotulo_off, rotulo_foto, manual, "
                         "similar (productos parecidos con rótulo) o generico: usda / rotulos",
    "ingredientes": "Lista de ingredientes del rótulo, si se conoce",
    "puede_contener": "Alérgenos declarados como trazas",
    "apto_vegetariano": "si / no / desconocido",
    "apto_vegano": "si / no / desconocido",
    "sin_tacc": "si / no / desconocido (apto celíacos)",
    "sin_lactosa": "si / no / desconocido",
    "nova": "Grado de procesamiento NOVA (1 sin procesar ... 4 ultraprocesado)",
    "aditivos": "Cantidad de aditivos (Open Food Facts), si se conoce",
    "azucar_agregada": "si / no / desconocido",
    "edulcorantes": "si / no / desconocido",
    "aceite_palma": "si / no / desconocido",
    "fuente_composicion": "rótulo (catálogo web), rótulo (Open Food Facts), ingredientes o alimento genérico",
    "sellos": "Cantidad de sellos de advertencia (Ley 27.642), aproximada a partir de los nutrientes (en los "
              "polvos para preparar, solo azúcares y grasas: la ley los evalúa sobre lo preparado)",
    "categoria_web": "Categoría de góndola (catálogos de Jumbo, Disco y Vea): la publicada para ese EAN o la que "
                     "predice el clasificador con confianza >= 0,5; vacía si no hay una confiable",
    "clasificacion_origen": "Cómo se clasificó: reglas y categoría, categoría y reglas acotadas, categoría "
                            "(alimento predeterminado) o reglas (sin categoría confiable)",
    "contenido_fuente": "De dónde sale el contenido: sepa (campos estructurados), descripcion, referencia "
                        "(precio de referencia de la cadena), granel o precio (las cadenas informan tamaños "
                        "distintos y se eligió el que deja el precio por kilo dentro de lo habitual)",
    "contenido_acuerdo": "Fracción de las sucursales que informan ese mismo contenido",
    "alimento_id": "Identificador del alimento genérico (referencia/alimentos.csv)",
}
for a in ALERGENOS:
    COLUMNAS_PRODUCTO[f"contiene_{a}"] = f"Contiene {a.replace('_', ' ')}: si / no / desconocido"
for s in SELLOS:
    COLUMNAS_PRODUCTO[s] = f"Sello de advertencia aproximado: {s.replace('_', ' ')} (verdadero / falso)"
UNIDADES_NUTRIENTE = {"kcal": "kcal", "g": "g", "mg": "mg", "ug": "µg"}
for n in NUTRIENTES:
    COLUMNAS_PRODUCTO[n] = (f"{n.rsplit('_', 1)[0].replace('_', ' ').capitalize()}, "
                            f"{UNIDADES_NUTRIENTE[n.rsplit('_', 1)[1]]} cada 100 g comestibles")

ORDEN_PRODUCTO = (["id_producto", "tipo_codigo", "id_comercio_interno", "nombre", "marca", "descripcion_sepa",
                   "categoria", "subcategoria", "grupo_alimentario", "forma_venta", "contenido", "unidad_contenido",
                   "unidades", "unidad_normalizada", "cantidad_normalizada", "gramos_envase", "base_normalizacion",
                   "parte_comestible", "densidad_g_ml", "porcion_g"] + NUTRIENTES + ["fuente_nutrientes"]
                  + ["ingredientes"] + [f"contiene_{a}" for a in ALERGENOS]
                  + ["puede_contener", "apto_vegetariano", "apto_vegano", "sin_tacc", "sin_lactosa", "nova",
                     "aditivos", "azucar_agregada", "edulcorantes", "aceite_palma", "fuente_composicion"]
                  + SELLOS + ["sellos", "categoria_web", "clasificacion_origen", "contenido_fuente",
                              "contenido_acuerdo", "alimento_id"])

COLUMNAS_TIENDA = {
    "id_tienda": "Clave: '<id_comercio>-<id_bandera>-<id_sucursal>'",
    "id_comercio": "Comercio (empresa) en SEPA", "id_bandera": "Bandera dentro del comercio",
    "id_sucursal": "Sucursal dentro del comercio", "comercio": "Razón social", "cuit": "CUIT del comercio",
    "bandera": "Nombre comercial (Carrefour Market, Disco, DIA...)",
    "formato": "Supermercado, Tienda de estación de servicio o Farmacia",
    "tipo_sucursal": "Hipermercado (más de 15 cajas), Supermercado (4 a 15), Autoservicio (1 a 3), Tradicional o Web",
    "sucursal_nombre": "Nombre de la sucursal", "direccion": "Calle y número como los publica SEPA",
    "direccion_normalizada": "Dirección según el geocodificador (USIG o Georef), si se consultó",
    "codigo_postal": "Código postal (4 dígitos)", "localidad": "Localidad (declarada; en CABA, la Ciudad)",
    "barrio": "Barrio oficial en CABA; en el resto, el declarado (si hay)", "comuna": "Comuna (solo CABA)",
    "municipio": "Municipio o gobierno local (Georef)", "municipio_id": "Código del municipio (INDEC)",
    "departamento": "Departamento o partido (Georef)", "departamento_id": "Código del departamento (INDEC)",
    "provincia": "Provincia (Georef)", "provincia_id": "Código de provincia (INDEC)",
    "provincia_iso": "Provincia tal como la declara SEPA (ISO 3166-2)",
    "lat": "Latitud validada (WGS84)", "lon": "Longitud validada (WGS84)",
    "ubicacion_fuente": "sepa (validada), direccion_usig / direccion_georef (corregida por la dirección), "
                        "centroide_localidad, sepa_dudosa, web o sin_ubicacion",
    "ubicacion_precision": "exacta, aproximada, dudosa, sin_ubicacion o no_aplica (web)",
    "distancia_direccion_m": "Distancia entre la coordenada de SEPA y la dirección geocodificada (m)",
    "correccion_coordenada": "Arreglo mecánico aplicado a la coordenada de SEPA (signo, ejes, coma)",
    "lat_sepa": "Latitud original de SEPA", "lon_sepa": "Longitud original de SEPA",
    "es_web": "Sucursal de venta online (sin ubicación física)",
}
for d in ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]:
    COLUMNAS_TIENDA[f"horario_{d}"] = (f"Horario del {d}: 'HH:MM-HH:MM' (turnos separados por coma); vacío = cerrado; "
                                      "nulo = no informado")

COLUMNAS_FACT = {
    "fecha": "Día de los precios (fecha del ZIP de SEPA)",
    "id_producto": "Producto (dim_producto)", "id_tienda": "Tienda (dim_tienda)",
    "precio": "Precio de lista publicado (ARS) por la presentación",
    "precio_promocion": "Precio unitario de la promoción de alcance general vigente, si hay (puede exigir "
                        "condiciones: llevar 2 unidades, etc.)",
    "cantidad": "Presentación que compra el precio: cantidad", "unidad": "g, ml, kg (granel) o unidad",
    "precio_normalizado": "Precio por kg, litro o unidad (según unidad_normalizada): comparable dentro de la "
                          "subcategoría",
    "unidad_normalizada": "kg, l o unidad",
    "precio_100g": "Precio cada 100 g tal como se compra; dividido por parte_comestible da el de la parte "
                   "comestible, que es la base de los nutrientes",
}


def _csv(df: pd.DataFrame, ruta, **kw) -> None:
    df.to_csv(ruta, sep=";", decimal=",", index=False, encoding="utf-8-sig", **kw)


def tablas_finales(dim_producto: pd.DataFrame, dim_tienda: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    p = dim_producto.rename(columns={"descripcion": "descripcion_sepa"})
    confiable = p["categoria_origen"].eq("exacta") | (p["categoria_probabilidad"] >= cfg.CATEGORIA_PROB_MEDIA)
    p["categoria_web"] = p["categoria_web"].where(confiable)
    p = p[ORDEN_PRODUCTO].sort_values(["categoria", "subcategoria", "nombre"], ignore_index=True)
    t = dim_tienda[list(COLUMNAS_TIENDA)]
    return p, t


def _tabla_md(serie: pd.Series, titulo: str, que: str) -> str:
    filas = "\n".join(f"| {k} | {v:,} |".replace(",", ".") for k, v in serie.items())
    return f"| {titulo} | {que} |\n|---|---:|\n{filas}\n"


def _diccionario(columnas: dict, df: pd.DataFrame) -> str:
    filas = []
    for c in df.columns:
        tipo = str(df[c].dtype).replace("object", "texto").replace("category", "texto").replace("float64", "número") \
            .replace("int64", "entero").replace("Int64", "entero").replace("bool", "booleano") \
            .replace("datetime64[ns]", "fecha").replace("float32", "número").replace("int32", "entero")
        filas.append(f"| `{c}` | {tipo} | {columnas.get(c, '')} |")
    return "| Columna | Tipo | Descripción |\n|---|---|---|\n" + "\n".join(filas) + "\n"


def leeme(p: pd.DataFrame, t: pd.DataFrame, f: pd.DataFrame, verif: pd.DataFrame, stats: dict) -> str:
    fecha = pd.Timestamp(f["fecha"].iloc[0]).date() if len(f) else ""
    ubic = t["ubicacion_precision"].value_counts()
    partes = [
        "# SEPA 2.0 — salida",
        "",
        f"Precios minoristas del **{fecha}** (SEPA, `{stats['archivo']}`), procesados el "
        f"{datetime.now():%Y-%m-%d %H:%M} en {stats['minutos']:.1f} min.",
        "",
        "## Archivos",
        "",
        "| Archivo | Qué es | Filas |",
        "|---|---|---:|",
        f"| `dim_producto.parquet` / `.csv` | Productos comestibles: clasificación, presentación, nutrientes y "
        f"composición (sin precio) | {len(p):,} |".replace(",", "."),
        f"| `dim_tienda.parquet` / `.csv` | Sucursales con ubicación validada, división política y horarios | "
        f"{len(t):,} |".replace(",", "."),
        f"| `fact_precio.parquet` / `.csv.gz` | Precio de cada producto en cada tienda, normalizado | "
        f"{len(f):,} |".replace(",", "."),
        "| `calidad/` | Lo excluido y por qué, precios descartados, ubicaciones corregidas, verificación | |",
        "",
        "Relaciones: `fact_precio.id_producto` → `dim_producto.id_producto` y `fact_precio.id_tienda` → "
        "`dim_tienda.id_tienda` (muchos a uno). Los CSV usan `;` y coma decimal; para Power BI, pandas o R conviene "
        "el parquet.",
        "",
        "Ejemplos: precio por kg de la banana en cada provincia → `fact_precio` (subcategoría Banana vía "
        "`dim_producto`) agrupado por `dim_tienda.provincia` con la mediana de `precio_normalizado`. Costo de 100 g "
        "de proteína → `precio_100g / parte_comestible / proteinas_g * 100`.",
        "",
        "## Resumen de la corrida",
        "",
        f"- Productos en SEPA ese día: {stats['producto']['productos_sepa']:,}; comestibles en `dim_producto`: "
        f"{len(p):,} en {p['subcategoria'].nunique()} subcategorías y {p['categoria'].nunique()} categorías".replace(",", "."),
        f"- Tiendas: {len(t):,} en {t['provincia'].nunique()} provincias; ubicación exacta "
        f"{ubic.get('exacta', 0):,}, aproximada {ubic.get('aproximada', 0)}, dudosa {ubic.get('dudosa', 0)}, sin "
        f"ubicación {ubic.get('sin_ubicacion', 0)}".replace(",", "."),
        f"- Precios: {len(f):,} (con promoción vigente: {f['precio_promocion'].notna().sum():,}); descartados por "
        f"anormales: {sum(stats['precio']['precios_descartados'].values()):,}".replace(",", "."),
        "",
        _tabla_md(p["categoria"].value_counts(), "Categoría", "Productos"),
        _tabla_md(p["grupo_alimentario"].value_counts(), "Grupo alimentario", "Productos"),
        _tabla_md(p["fuente_nutrientes"].value_counts(), "Fuente de los nutrientes", "Productos"),
        _tabla_md(t["provincia"].fillna("(sin ubicación)").value_counts(), "Provincia", "Tiendas"),
        "## Verificación",
        "",
        "Todos los controles críticos pasan (si alguno fallara, la corrida se detiene). Detalle en "
        "`calidad/verificacion.csv`.",
        "",
        "| Control | Filas que fallan | Crítico |",
        "|---|---:|:---:|",
    ]
    partes += [f"| {r.control} | {r.filas_que_fallan} | {'sí' if r.critico else ''} |" for r in verif.itertuples()]
    partes += ["", "## Diccionario de datos", "", "### dim_producto", "", _diccionario(COLUMNAS_PRODUCTO, p),
               "### dim_tienda", "", _diccionario(COLUMNAS_TIENDA, t), "### fact_precio", "",
               _diccionario(COLUMNAS_FACT, f)]
    return "\n".join(partes) + "\n"


def escribir(p: pd.DataFrame, t: pd.DataFrame, f: pd.DataFrame, calidad: dict[str, pd.DataFrame],
             verif: pd.DataFrame, stats: dict) -> None:
    if cfg.DIR_SALIDA.exists():
        shutil.rmtree(cfg.DIR_SALIDA)          # una sola corrida: no quedan restos de la anterior
    cfg.DIR_CALIDAD.mkdir(parents=True, exist_ok=True)
    for df, ruta in ((p, cfg.RUTA_DIM_PRODUCTO), (t, cfg.RUTA_DIM_TIENDA)):
        df.to_parquet(ruta.with_suffix(".parquet"), index=False)
        _csv(df, ruta.with_suffix(".csv"))
    f.to_parquet(cfg.RUTA_FACT_PRECIO.with_suffix(".parquet"), index=False)
    _csv(f, cfg.RUTA_FACT_PRECIO.with_suffix(".csv.gz"), compression="gzip")
    for nombre, df in calidad.items():
        _csv(df, cfg.DIR_CALIDAD / f"{nombre}.csv")
    _csv(verif, cfg.DIR_CALIDAD / "verificacion.csv")
    (cfg.DIR_SALIDA / "LEEME.md").write_text(leeme(p, t, f, verif, stats), encoding="utf-8")
    logger.info("Salidas en %s", cfg.DIR_SALIDA)
