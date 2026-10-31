"""
Rótulos de los catálogos online de Jumbo, Disco y Vea (Cencosud, plataforma VTEX).

Open Food Facts cubre solo una parte de los productos argentinos. Estos sitios
publican, por producto, la tabla nutricional del rótulo estructurada (cada 100 g
o 100 ml: energía, proteínas, carbohidratos, grasas totales, saturadas, trans,
mono y poliinsaturadas, colesterol, azúcares, fibra, sodio), los ingredientes,
los alérgenos y trazas declarados, las certificaciones (sin TACC, vegano,
kosher...) y si contiene azúcar agregada. Se cruzan con SEPA por EAN.

El catálogo se recorre por categoría (la API pública de búsqueda devuelve 50
productos por página) y después se buscan por código de barras los EAN que
faltan: unas pocas centenas de consultas con pausa entre pedidos. Las respuestas
crudas quedan en cache/web/<sitio>.jsonl.gz; sin --actualizar-web se reutilizan.
"""

from __future__ import annotations

import ast
import gzip
import json
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

from sepa import config as cfg
from sepa.texto import sin_tildes

logger = logging.getLogger("sepa.fuentes.web")

SITIOS = {"jumbo": "https://www.jumbo.com.ar", "disco": "https://www.disco.com.ar", "vea": "https://www.vea.com.ar"}
DEPARTAMENTOS = {"almacen", "bebidas", "frutas y verduras", "carnes", "pescados y mariscos", "quesos y fiambres",
                 "lacteos", "congelados", "panaderia y pasteleria", "rotiseria", "panaderia", "pastas frescas",
                 "desayuno y merienda", "frescos", "lacteos y productos frescos", "carniceria", "verduleria"}
POR_PAGINA = 50
MAX_RESULTADOS = 2500        # la API no devuelve más allá de _from = 2500
HILOS = 3
PAUSA_S = 0.25
CABECERAS = {"User-Agent": "Mozilla/5.0 (proyecto academico; consultas de catalogo publico)"}

CAMPOS = {   # campo de la tabla -> columna (cada 100 g o 100 ml)
    "energy_value": "energia_kcal", "protein_value": "proteinas_g", "carb_value": "carbohidratos_g",
    "sugars_value": "azucares_g", "fiber_value": "fibra_g", "fat_total_value": "grasas_totales_g",
    "fat_sat_value": "grasas_saturadas_g", "fat_trans_value": "grasas_trans_g",
    "fat_mono_value": "grasas_monoinsaturadas_g", "fat_poli_value": "grasas_poliinsaturadas_g",
    "fat_cholesterol_value": "colesterol_mg", "sodium_value": "sodio_mg",
}
UNIDAD_ESPERADA = {"energy": "kcal", "sodium": "mg", "fat_cholesterol": "mg"}


def _ruta(sitio: str) -> Path:
    return cfg.DIR_WEB / f"{sitio}.jsonl.gz"


class _Cliente:
    def __init__(self) -> None:
        self.sesion = requests.Session()
        self.sesion.headers.update(CABECERAS)
        self.lock = threading.Lock()
        self.ultimo = 0.0
        self.pedidos = 0

    def get(self, url: str, params=None) -> requests.Response | None:
        for intento in range(4):
            with self.lock:
                espera = self.ultimo + PAUSA_S - time.time()
                if espera > 0:
                    time.sleep(espera)
                self.ultimo = time.time()
                self.pedidos += 1
            try:
                r = self.sesion.get(url, params=params, timeout=40)
                if r.status_code in (429, 503):
                    time.sleep(5 * (intento + 1))
                    continue
                if r.status_code in (200, 206):
                    return r
            except requests.RequestException:
                time.sleep(2 * (intento + 1))
        return None


# ============================================================
# DESCARGA (solo con --actualizar-web)
# ============================================================

def _hojas(cliente: _Cliente, base: str, alimentos: bool = True) -> list[tuple[str, str]]:
    """
    Categorías hoja (ruta de ids "1/17/134", ruta de nombres) de los departamentos de alimentos y bebidas o,
    con alimentos=False, de los demás (limpieza, perfumería, hogar...): estos últimos solo sirven como
    ejemplos de lo que no es comida para el clasificador de categorías.
    """
    arbol = cliente.get(f"{base}/api/catalog_system/pub/category/tree/4").json()
    hojas = []

    def recorrer(nodo, ids, ruta):
        ids, ruta = ids + [str(nodo["id"])], ruta + [nodo["name"]]
        hijos = nodo.get("children") or []
        if not hijos:
            hojas.append(("/".join(ids), " > ".join(ruta)))
        for h in hijos:
            recorrer(h, ids, ruta)

    for dep in arbol:
        if (sin_tildes(dep["name"]).lower().strip() in DEPARTAMENTOS) == alimentos:
            recorrer(dep, [], [])
    return hojas


def _bajar_categoria(cliente: _Cliente, base: str, cat_id: str) -> list[dict]:
    """Todos los productos de una categoría (si pasa de MAX_RESULTADOS, también en orden de precio inverso)."""
    productos = []
    for orden in (None, "OrderByPriceDESC"):
        desde, total = 0, 0
        while desde < MAX_RESULTADOS:
            params = {"fq": f"C:/{cat_id}/", "_from": desde, "_to": desde + POR_PAGINA - 1}
            if orden:
                params["O"] = orden
            r = cliente.get(f"{base}/api/catalog_system/pub/products/search", params)
            if r is None:
                break
            pagina = r.json()
            productos += pagina
            total = int((r.headers.get("resources") or "0/0").split("/")[-1] or 0)
            desde += POR_PAGINA
            if desde >= total or not pagina:
                break
        if total <= MAX_RESULTADOS:
            break
    return productos


def _categoria_de(producto: dict) -> str:
    cats = producto.get("categories") or []
    if not cats:
        return ""
    mas_larga = max(cats, key=lambda c: c.count("/"))
    return " > ".join(x for x in mas_larga.strip("/").split("/") if x)


def descargar(sitio: str, eans_faltantes: list[str]) -> None:
    """Recorre el catálogo de alimentos del sitio y busca por código de barras los EAN que faltan."""
    base, ruta = SITIOS[sitio], _ruta(sitio)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    cliente = _Cliente()
    hojas = _hojas(cliente, base)
    vistos = set()
    with gzip.open(ruta, "wt", encoding="utf-8") as f, ThreadPoolExecutor(HILOS) as ex:
        for (_, nombre), productos in zip(hojas, ex.map(lambda h: _bajar_categoria(cliente, base, h[0]), hojas)):
            for p in productos:
                if p.get("productId") not in vistos:
                    vistos.add(p.get("productId"))
                    p["_categoria"] = nombre
                    f.write(json.dumps(p, ensure_ascii=False) + "\n")
        lotes = [eans_faltantes[i:i + 50] for i in range(0, len(eans_faltantes), 50)]

        def buscar(grupo):
            params = [("fq", f"alternateIds_Ean:{e}") for e in grupo] + [("_from", 0), ("_to", 49)]
            r = cliente.get(f"{base}/api/catalog_system/pub/products/search", params)
            return r.json() if r is not None else []

        for productos in ex.map(buscar, lotes):
            for p in productos:
                if p.get("productId") not in vistos:
                    vistos.add(p.get("productId"))
                    p["_categoria"] = _categoria_de(p)
                    f.write(json.dumps(p, ensure_ascii=False) + "\n")
    logger.info("%s: %d productos en %d pedidos", sitio, len(vistos), cliente.pedidos)


def descargar_no_alimentos(sitio: str = "jumbo") -> None:
    """Productos de los departamentos que no son comida (solo nombre y categoría, para el clasificador)."""
    base, ruta = SITIOS[sitio], cfg.DIR_WEB / f"{sitio}_no_alimentos.jsonl.gz"
    cliente = _Cliente()
    hojas = _hojas(cliente, base, alimentos=False)
    vistos = set()
    with gzip.open(ruta, "wt", encoding="utf-8") as f, ThreadPoolExecutor(HILOS) as ex:
        for (_, nombre), productos in zip(hojas, ex.map(lambda h: _bajar_categoria(cliente, base, h[0]), hojas)):
            for p in productos:
                if p.get("productId") not in vistos:
                    vistos.add(p.get("productId"))
                    f.write(json.dumps({"productName": p.get("productName"), "brand": p.get("brand"),
                                        "_categoria": nombre,
                                        "items": [{"ean": i.get("ean")} for i in p.get("items") or []]},
                                       ensure_ascii=False) + "\n")
    logger.info("%s (no alimentos): %d productos en %d pedidos", sitio, len(vistos), cliente.pedidos)


def categorias() -> pd.DataFrame:
    """
    Nombre, marca y categoría de todos los productos de los catálogos (alimentos y no alimentos). Se arma una
    vez y se guarda en cache/web/categorias.parquet hasta que cambie algún catálogo.
    """
    fuentes = sorted(cfg.DIR_WEB.glob("*.jsonl.gz"))
    cache = cfg.DIR_WEB / "categorias.parquet"
    if cache.exists() and all(cache.stat().st_mtime > f.stat().st_mtime for f in fuentes):
        return pd.read_parquet(cache)
    filas = []
    for ruta in fuentes:
        with gzip.open(ruta, "rt", encoding="utf-8") as f:
            for linea in f:
                p = json.loads(linea)
                categoria = p.get("_categoria") or _categoria_de(p)
                for item in p.get("items") or [{}]:
                    ean = re.sub(r"\D", "", str(item.get("ean") or ""))
                    filas.append({"ean": ean.lstrip("0").zfill(13) if len(ean) >= 8 else "",
                                  "nombre": p.get("productName") or "", "marca": p.get("brand") or "",
                                  "categoria": categoria})
    df = pd.DataFrame(filas)
    df = df[df["categoria"].fillna("").ne("") & ~df["categoria"].str.startswith("Sin Categor")]
    df = df.drop_duplicates(["ean", "nombre", "categoria"]).reset_index(drop=True)
    df.to_parquet(cache, index=False)
    return df


# ============================================================
# PROCESAMIENTO
# ============================================================

def _tabla(producto: dict) -> dict | None:
    t = producto.get("Tabla Nutricional")
    if not t:
        return None
    try:
        return ast.literal_eval(t[0]) if isinstance(t[0], str) else t[0]
    except (ValueError, SyntaxError):
        return None


def _certificaciones(producto: dict) -> str:
    """Códigos de los sellos de aptitud ("gluten_free", "vegan", ...) separados por '|'."""
    codigos = []
    for bloque in producto.get("Sellos") or []:
        try:
            datos = ast.literal_eval(bloque) if isinstance(bloque, str) else bloque
        except (ValueError, SyntaxError):
            continue
        for s in datos if isinstance(datos, list) else [datos]:
            if isinstance(s, dict) and s.get("certification_type_code"):
                codigos.append(str(s["certification_type_code"]))
    return "|".join(sorted(set(codigos)))


def _lista(producto: dict, campo: str) -> str:
    v = producto.get(campo)
    if not v:
        return ""
    texto = v[0] if isinstance(v, list) else str(v)
    return re.sub(r"'\s*,\s*'", ", ", texto).strip("'\" ")


def procesar() -> pd.DataFrame:
    """Una fila por EAN (13 dígitos) con el rótulo, la composición y el nombre en la web."""
    filas = []
    for sitio in SITIOS:
        ruta = _ruta(sitio)
        if not ruta.exists():
            continue
        with gzip.open(ruta, "rt", encoding="utf-8") as f:
            for linea in f:
                p = json.loads(linea)
                t = _tabla(p)
                for item in p.get("items") or []:
                    ean = re.sub(r"\D", "", str(item.get("ean") or ""))
                    if len(ean) < 8:
                        continue
                    fila = {"ean": ean.lstrip("0").zfill(13), "sitio": sitio, "nombre": p.get("productName"),
                            "marca": p.get("brand"), "categoria": p.get("_categoria") or _categoria_de(p),
                            "ingredientes": _lista(p, "Ingredientes"), "trazas": _lista(p, "Trazas"),
                            "alergenos": _lista(p, "Condiciones Alimentarias"),
                            "certificaciones": _certificaciones(p),
                            "contiene_azucar": _lista(p, "Contiene Azúcar"), "tiene_tabla": t is not None}
                    if t is not None:
                        fila["unidad_base"] = t.get("basic_unit_name")
                        unidades_ok = True
                        for campo, col in CAMPOS.items():
                            v = t.get(campo)
                            unidad = str(t.get(campo.replace("_value", "_unit_name")) or "").lower()
                            esperada = UNIDAD_ESPERADA.get(campo.replace("_value", ""), "g")
                            if v is not None and unidad and not unidad.startswith(esperada):
                                if campo == "energy_value" and unidad.startswith("kj"):
                                    v = float(v) / 4.184
                                elif campo == "sodium_value" and unidad == "g":
                                    v = float(v) * 1000
                                else:
                                    unidades_ok = False
                            fila[col] = float(v) if v is not None else None
                        fila["unidades_ok"] = unidades_ok
                    filas.append(fila)
    df = pd.DataFrame(filas)
    if df.empty:
        return df
    # Un EAN puede estar en los tres sitios: se prefiere el que tiene tabla y, entre ellos, Jumbo.
    orden = {s: i for i, s in enumerate(SITIOS)}
    df["_o"] = (~df["tiene_tabla"]).astype(int) * 10 + df["sitio"].map(orden)
    return df.sort_values("_o").drop_duplicates("ean").drop(columns="_o").reset_index(drop=True)
