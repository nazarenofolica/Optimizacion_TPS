"""
Qué se puede comprar y dónde: lee las tablas del modelo estrella una sola vez y responde

  - qué productos son aptos para una persona (restricciones: celiaquía, vegano, alergias...), con el criterio
    explicado para mostrarlo;
  - qué sucursales tiene cerca (la más cercana de cada cadena primero, para comparar cadenas);
  - qué productos aptos vende cada sucursal y a qué precio, con lo que aporta cada gramo.

Las restricciones son estrictas: "desconocido" no es apto. Para un celíaco o un alérgico, un producto sin rótulo
que lo confirme no se ofrece.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from canasta import config as cfg

logger = logging.getLogger("canasta.oferta")

NUTRIENTES = [
    "energia_kcal", "proteinas_g", "carbohidratos_g", "azucares_g", "fibra_g", "grasas_totales_g",
    "grasas_saturadas_g", "grasas_monoinsaturadas_g", "grasas_poliinsaturadas_g", "grasas_trans_g", "colesterol_mg",
    "sodio_mg", "potasio_mg", "calcio_mg", "hierro_mg", "magnesio_mg", "fosforo_mg", "zinc_mg", "cobre_mg",
    "selenio_ug", "vitamina_a_ug", "vitamina_c_mg", "vitamina_d_ug", "vitamina_e_mg", "vitamina_k_ug",
    "vitamina_b1_mg", "vitamina_b2_mg", "vitamina_b3_niacina_mg", "vitamina_b6_mg", "vitamina_b9_folato_ug",
    "vitamina_b12_ug",
]
DERIVADOS = ["azucares_libres_g", "vitamina_a_preformada_ug"]
COLUMNAS_PRODUCTO = [
    "id_producto", "nombre", "marca", "categoria", "subcategoria", "grupo_alimentario", "alimento_id", "forma_venta",
    "contenido", "unidad_contenido", "unidades", "gramos_envase", "parte_comestible", "porcion_g", "nova",
    "fuente_nutrientes", "fuente_composicion", "contiene_gluten", "contiene_leche", "contiene_huevo", "contiene_mani",
    "contiene_frutos_secos", "contiene_soja", "contiene_pescado", "contiene_mariscos", "contiene_sesamo",
    "puede_contener", "apto_vegetariano", "apto_vegano", "sin_tacc", "sin_lactosa", "azucar_agregada",
    "exceso_azucares", "exceso_sodio",
] + NUTRIENTES
COLUMNAS_TIENDA = [
    "id_tienda", "comercio", "bandera", "formato", "tipo_sucursal", "sucursal_nombre", "direccion", "localidad",
    "barrio", "departamento", "provincia", "lat", "lon", "ubicacion_precision", "es_web", "cuit",
    "horario_lunes", "horario_martes", "horario_miercoles", "horario_jueves", "horario_viernes", "horario_sabado",
    "horario_domingo",
]
NOMBRE_ALERGENO = {"leche": "leche", "huevo": "huevo", "mani": "maní", "frutos_secos": "frutos secos",
                   "soja": "soja", "pescado": "pescado", "mariscos": "mariscos", "sesamo": "sésamo", "gluten": "gluten"}
ALIMENTOS_AZUCAR_LIBRE = {"azucar", "azucar_mascabo", "miel", "jugo", "mermelada", "dulce_de_leche",
                          "leche_condensada", "dulce_membrillo", "caramelos"}


@dataclass
class Datos:
    productos: pd.DataFrame        # índice id_producto: los de los grupos de la canasta, con derivados
    tiendas: pd.DataFrame          # índice id_tienda
    precios: pd.DataFrame          # id_producto (código en productos), precio, precio_promocion; ordenado por tienda
    rangos: dict[str, tuple[int, int]]   # id_tienda -> [desde, hasta) en precios
    fecha: str
    total_productos: int


_DATOS: Datos | None = None
_CANDADO = threading.Lock()


def _derivados(p: pd.DataFrame) -> pd.DataFrame:
    # Azúcares libres (OMS): los agregados, la miel y los de los jugos. Se cuentan los azúcares totales de los productos
    # con azúcar agregada (sobreestima un poco en un yogur endulzado, que también trae lactosa).
    libre = ((p["azucar_agregada"] == "si") | p["alimento_id"].isin(ALIMENTOS_AZUCAR_LIBRE)
             | ((p["grupo_alimentario"] == "Alimentos de consumo opcional") & (p["azucar_agregada"] != "no")))
    p["azucares_libres_g"] = np.where(libre, p["azucares_g"], 0.0)
    animal = (p["grupo_alimentario"].isin(cfg.GRUPOS_VITAMINA_A_PREFORMADA)
              & (p["subcategoria"] != "Bebidas vegetales (soja, almendra, avena, arroz)")
              | p["alimento_id"].isin(cfg.ALIMENTOS_VITAMINA_A_PREFORMADA))
    p["vitamina_a_preformada_ug"] = np.where(animal, p["vitamina_a_ug"], 0.0)
    return p


def cargar() -> Datos:
    """Lee dim_producto, dim_tienda y fact_precio (una vez por proceso; ~700 MB, con un pico de ~1 GB al cargar)."""
    global _DATOS
    with _CANDADO:
        if _DATOS is not None:
            return _DATOS
        for ruta in (cfg.RUTA_DIM_PRODUCTO, cfg.RUTA_DIM_TIENDA, cfg.RUTA_FACT_PRECIO):
            if not ruta.exists():
                raise FileNotFoundError(f"Falta {ruta}: primero hay que correr python -m sepa")
        todos = pd.read_parquet(cfg.RUTA_DIM_PRODUCTO, columns=COLUMNAS_PRODUCTO)
        p = todos[todos["grupo_alimentario"].isin(cfg.GRUPOS_CANASTA)
                  & ~todos["alimento_id"].isin(cfg.ALIMENTOS_EXCLUIDOS)
                  & ~todos["nombre"].str.upper().str.contains(cfg.NOMBRES_EXCLUIDOS, regex=True)].copy()
        p = _derivados(p).set_index("id_producto")
        t = pd.read_parquet(cfg.RUTA_DIM_TIENDA, columns=COLUMNAS_TIENDA).set_index("id_tienda")
        fecha = pq.read_table(cfg.RUTA_FACT_PRECIO, columns=["fecha"]).column(0)
        fecha = str(fecha[0].as_py().date()) if len(fecha) else ""
        # Se trabaja con los códigos de las categorías del parquet: pasar 8 millones de claves a texto cuesta ~1,5 GB.
        f = pd.read_parquet(cfg.RUTA_FACT_PRECIO, columns=["id_producto", "id_tienda", "precio", "precio_promocion"])
        cat_prod, cat_tienda = f["id_producto"].astype("category"), f["id_tienda"].astype("category")
        a_prod = p.index.get_indexer(cat_prod.cat.categories.astype(str))       # categoría -> fila de p (-1: afuera)
        prod = a_prod[cat_prod.cat.codes.to_numpy()]
        tienda = cat_tienda.cat.codes.to_numpy()
        quedan = prod >= 0
        orden = np.lexsort((prod[quedan], tienda[quedan]))      # por tienda y, dentro, por producto (determinista)
        f = pd.DataFrame({"prod": prod[quedan][orden].astype(np.int32),
                          "precio": f["precio"].to_numpy()[quedan][orden],
                          "precio_promocion": f["precio_promocion"].to_numpy()[quedan][orden]})
        tienda = tienda[quedan][orden]
        del cat_prod, quedan, orden
        # Precio de referencia de cada subcategoría: mediana (entre productos) de la mediana de cada producto, cada
        # 100 g comestibles. Sirve para no ofrecer precios mal cargados.
        gramos = (p["gramos_envase"].to_numpy(float) * p["parte_comestible"].to_numpy(float))[f["prod"].to_numpy()]
        por_100g = pd.Series(f["precio"].to_numpy() / gramos * 100).groupby(f["prod"].to_numpy()).median()
        sub = p["subcategoria"].to_numpy()[por_100g.index]
        p["precio_referencia_100g"] = p["subcategoria"].map(por_100g.groupby(sub).median())
        cortes = np.flatnonzero(tienda[1:] != tienda[:-1]) + 1
        desde, hasta = np.r_[0, cortes], np.r_[cortes, len(f)]
        nombres = cat_tienda.cat.categories.astype(str)
        rangos = {nombres[tienda[a]]: (int(a), int(b)) for a, b in zip(desde, hasta)}
        _DATOS = Datos(p, t, f, rangos, fecha, len(todos))
        logger.info("Datos: %d productos de la canasta, %d tiendas, %d precios (%s)", len(p), len(t), len(f), fecha)
        return _DATOS


# ------------------------------------------------------------
# Restricciones
# ------------------------------------------------------------

def _sin_trazas(p: pd.DataFrame, alergeno: str) -> pd.Series:
    nombre = NOMBRE_ALERGENO[alergeno]
    trazas = p["puede_contener"].fillna("").str.contains(nombre, regex=False)
    # Un procesado sin rótulo propio (composición del alimento genérico) no informa sus trazas: no es seguro.
    sin_rotulo = (p["nova"] >= 3) & (p["fuente_composicion"] == "alimento genérico")
    return ~trazas & ~sin_rotulo


def criterios(restricciones: list[str]) -> list[dict]:
    """Qué exige cada restricción, en palabras (para mostrarlo)."""
    textos = {
        "celiaquia": "Solo productos sin TACC: los que lo declaran en el rótulo o el catálogo (logo sin TACC) y los "
                     "alimentos naturales sin gluten (frutas, verduras, carnes, huevos, legumbres secas envasadas); "
                     "sin trazas de gluten declaradas. Nada suelto a granel salvo frutas, verduras y carnes frescas: "
                     "los secos sueltos se contaminan con harina de trigo (ANMAT).",
        "vegetariano": "Sin carnes, pescados ni mariscos (sí lácteos, huevo y miel).",
        "vegano": "Sin ningún ingrediente de origen animal: ni carne, pescado, lácteos, huevo ni miel.",
        "sin_lactosa": "Solo productos sin lactosa: los que no tienen leche o están certificados sin lactosa "
                       "(leche deslactosada).",
        "sin_ultraprocesados": "Sin productos ultraprocesados (grupo NOVA 4).",
        "hipertension": "Sin productos con sello de exceso en sodio y con el sodio del día por debajo de 1.500 mg.",
        "diabetes": "Sin productos con sello de exceso en azúcares y con los azúcares libres por debajo del 5 % de la "
                    "energía.",
    }
    salida = []
    for r in restricciones:
        if r in cfg.ALERGIAS:
            a = NOMBRE_ALERGENO[cfg.ALERGIAS[r]]
            texto = (f"Sin {a} entre los ingredientes ni como traza declarada (\"puede contener\"). Los procesados "
                     f"sin rótulo propio no informan sus trazas y se excluyen.")
        else:
            texto = textos[r]
        salida.append({"clave": r, "nombre": cfg.RESTRICCIONES[r], "criterio": texto})
    return salida


def aptos(p: pd.DataFrame, restricciones: list[str]) -> tuple[pd.Series, list[dict]]:
    """Máscara de productos aptos y, por restricción, cuántos productos deja afuera."""
    apto = pd.Series(True, index=p.index)
    efecto = []
    for r in restricciones:
        if r == "celiaquia":
            # A granel solo lo fresco: los secos sueltos (arroz, legumbres, harinas, frutos secos) se contaminan.
            granel = p["forma_venta"].str.startswith("Granel") & ~p["grupo_alimentario"].isin(cfg.GRANEL_APTO_CELIACOS)
            m = ((p["sin_tacc"] == "si") & ~p["puede_contener"].fillna("").str.contains("gluten", regex=False)
                 & ~granel)
        elif r == "vegetariano":
            m = p["apto_vegetariano"] == "si"
        elif r == "vegano":
            m = p["apto_vegano"] == "si"
        elif r == "sin_lactosa":
            m = p["sin_lactosa"] == "si"
        elif r in cfg.ALERGIAS:
            a = cfg.ALERGIAS[r]
            m = (p[f"contiene_{a}"] == "no") & _sin_trazas(p, a)
        elif r == "sin_ultraprocesados":
            m = p["nova"] < 4
        elif r == "hipertension":
            m = ~p["exceso_sodio"].astype(bool)
        elif r == "diabetes":
            m = ~p["exceso_azucares"].astype(bool)
        else:
            raise ValueError(f"Restricción desconocida: {r}")
        efecto.append({"clave": r, "nombre": cfg.RESTRICCIONES[r], "excluye": int((apto & ~m).sum())})
        apto &= m
    return apto, efecto


# ------------------------------------------------------------
# Sucursales
# ------------------------------------------------------------

def distancia_km(lat1: float, lon1: float, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    r = 6371.0
    f1, f2 = np.radians(lat1), np.radians(lat2)
    df, dl = f2 - f1, np.radians(lon2 - lon1)
    a = np.sin(df / 2) ** 2 + np.cos(f1) * np.cos(f2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def sucursales_cercanas(d: Datos, lat: float, lon: float, n: int = cfg.SUCURSALES_A_EVALUAR,
                        radio_km: float = cfg.RADIO_KM) -> pd.DataFrame:
    """Las n sucursales a evaluar: la más cercana de cada cadena dentro del radio y, si faltan, las que siguen."""
    t = d.tiendas
    t = t[t["formato"].isin(cfg.FORMATOS_SUCURSAL) & ~t["es_web"].astype(bool) & t["lat"].notna()
          & (t["ubicacion_precision"] != "sin_ubicacion") & t.index.isin(list(d.rangos))].copy()
    t["distancia_km"] = distancia_km(lat, lon, t["lat"].to_numpy(), t["lon"].to_numpy())
    t = t.sort_values("distancia_km", kind="stable")
    radio = radio_km
    cerca = t[t["distancia_km"] <= radio]
    while len(cerca) < n and radio < cfg.RADIO_MAXIMO_KM:
        radio = min(radio * 2, cfg.RADIO_MAXIMO_KM)
        cerca = t[t["distancia_km"] <= radio]
    if cerca.empty:
        return cerca
    una_por_cadena = cerca.drop_duplicates("bandera")
    resto = cerca.drop(una_por_cadena.index)
    elegidas = pd.concat([una_por_cadena, resto]).head(n)
    return elegidas.sort_values("distancia_km", kind="stable")


def _podar(o: pd.DataFrame) -> np.ndarray:
    """En cada subcategoría, los más baratos cada 100 g comestibles y el envase más barato (posiciones en o)."""
    pos = np.arange(len(o))
    sub = o["subcategoria"].to_numpy()
    orden = np.lexsort((pos, o["precio_100g_comestible"].to_numpy()))
    barato = pd.Series(pos[orden]).groupby(sub[orden], sort=False).head(cfg.PRODUCTOS_POR_SUBCATEGORIA)
    orden = np.lexsort((pos, o["precio_compra"].to_numpy()))
    chico = pd.Series(pos[orden]).groupby(sub[orden], sort=False).head(1)
    return np.union1d(barato.to_numpy(), chico.to_numpy())


def oferta_tienda(d: Datos, id_tienda: str, aptos: list[np.ndarray]) -> tuple[pd.DataFrame, list[np.ndarray]]:
    """Productos de la sucursal que le sirven a alguien del hogar, con el precio y lo que compra cada unidad de
    compra (envase o 100 g), y para cada persona qué filas son aptas para ella. La poda se hace por persona (los más
    baratos entre lo que ella puede comer) y se unen: un celíaco y un vegano tienen cada uno sus mejores opciones."""
    a, b = d.rangos[id_tienda]
    f = d.precios.iloc[a:b]
    alguno = np.logical_or.reduce(aptos)
    f = f[alguno[f["prod"].to_numpy()]]
    o = d.productos.iloc[f["prod"].to_numpy()].copy()
    o["precio"] = f["precio"].to_numpy()
    o["precio_promocion"] = f["precio_promocion"].to_numpy()
    granel = o["forma_venta"].str.startswith("Granel").to_numpy()
    paso = np.where(granel, cfg.PASO_GRANEL_G, o["gramos_envase"].to_numpy())
    o["granel"] = granel
    o["gramos_compra"] = paso                                     # gramos que compra una unidad de compra
    o["precio_compra"] = np.where(granel, o["precio"] * cfg.PASO_GRANEL_G / 1000, o["precio"])
    o["gramos_comestibles_compra"] = o["gramos_compra"] * o["parte_comestible"]
    o = o[(o["gramos_comestibles_compra"] > 0) & (o["precio_compra"] > 0)]
    o["precio_100g_comestible"] = o["precio_compra"] / o["gramos_comestibles_compra"] * 100
    o = o[o["precio_100g_comestible"] >= cfg.FRACCION_PRECIO_MINIMO * o["precio_referencia_100g"]]
    filas = d.productos.index.get_indexer(o.index)
    por_persona = [apto[filas] for apto in aptos]
    quedan = np.zeros(len(o), dtype=bool)
    for m in por_persona:
        pos = np.flatnonzero(m)
        quedan[pos[_podar(o.iloc[pos])]] = True
    return o[quedan], [m[quedan] for m in por_persona]
