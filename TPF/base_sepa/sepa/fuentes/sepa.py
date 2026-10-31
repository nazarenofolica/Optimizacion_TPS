"""
Descarga y lectura del ZIP minorista diario de SEPA (Precios Claros).

El ZIP trae un ZIP por comercio (cadena) con tres archivos separados por "|"
(especificación: Anexo II de la Disposición SSADYC, 2020):

  comercio.csv    una fila por bandera (Carrefour Hiper, Market, Express...)
  sucursales.csv  una fila por sucursal: dirección, coordenadas, horarios
  productos.csv   una fila por producto y sucursal: precio de lista, precio
                  por unidad de referencia, promociones

De productos.csv se guarda lo mínimo y en tipos compactos (14 millones de
filas en una máquina de 8 GB):

  precios         producto, tienda, precio de lista y precio de promoción
                  vigente (una fila por producto y sucursal);
  presentaciones  cómo describe cada cadena cada producto (descripción, marca,
                  cantidad y unidad, unidad de referencia) y en cuántas
                  sucursales, para elegir después la versión más confiable.

Clave del producto: el código de barras (EAN/GTIN, 13 dígitos) cuando SEPA lo
marca como EAN, el dígito verificador es correcto y no es de circulación
restringida (los que empiezan con 2 son de balanza o internos: el mismo número
es otro producto en otra cadena). El resto son códigos internos de cada cadena
y su clave es "cadena<id_comercio>-<código>".

Problemas del origen que se resuelven acá:
  - registros partidos en varias líneas (un comercio corta la latitud, la
    longitud y los horarios con saltos de línea);
  - la línea final "Última actualización: ..." de cada archivo, que además dice
    de cuándo son los precios: un comercio que repite un archivo viejo se
    excluye (config.DIAS_MAXIMOS_DESACTUALIZADO);
  - ZIPs de comercio vacíos o ilegibles;
  - el mismo producto dos veces en la misma sucursal (queda la mediana).
"""

from __future__ import annotations

import csv
import io
import logging
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from sepa import config as cfg

logger = logging.getLogger("sepa.fuentes.sepa")

URL_PAQUETE = "https://datos.produccion.gob.ar/api/3/action/package_show?id={}"
FECHA_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
ACTUALIZACION_RE = re.compile(r"actualizaci", re.IGNORECASE)
VIGENCIA_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})\D+?(\d{1,2})/(\d{1,2})/(\d{4})")
NO_DIGITOS_RE = re.compile(r"\D")

COLUMNAS_PRODUCTOS = [
    "id_comercio", "id_bandera", "id_sucursal", "id_producto", "productos_ean", "productos_descripcion",
    "productos_cantidad_presentacion", "productos_unidad_medida_presentacion", "productos_marca",
    "productos_precio_lista", "productos_precio_referencia", "productos_cantidad_referencia",
    "productos_unidad_medida_referencia", "productos_precio_unitario_promo1", "productos_leyenda_promo1",
]
FILAS_POR_BLOQUE = 250_000


# ============================================================
# DESCARGA
# ============================================================

def _sesion() -> requests.Session:
    sesion = requests.Session()
    reintentos = Retry(total=5, backoff_factor=1.5, status_forcelist=[429, 500, 502, 503, 504],
                       allowed_methods=["GET"])
    sesion.mount("https://", HTTPAdapter(max_retries=reintentos))
    # Algunos WAF devuelven 403 al User-Agent de requests.
    sesion.headers["User-Agent"] = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    return sesion


def descargar_ultimo(carpeta: Path = cfg.DIR_ENTRADA) -> Path:
    """
    Baja el ZIP minorista más reciente de la API (ventana rotativa de 7 días) y borra los anteriores de
    la carpeta: SEPA 2.0 trabaja siempre sobre un solo día.
    """
    with _sesion() as sesion:
        r = sesion.get(URL_PAQUETE.format(cfg.DATASET_SEPA_MINORISTA), timeout=30)
        r.raise_for_status()
        recursos = []
        for rec in r.json()["result"]["resources"]:
            fecha = FECHA_RE.search(rec.get("description") or "")
            if fecha and (rec.get("url") or "").lower().endswith(".zip"):
                recursos.append((fecha.group(1), rec["url"]))
        if not recursos:
            raise RuntimeError("La API de SEPA no devolvió ningún ZIP con fecha.")
        fecha, url = max(recursos)
        carpeta.mkdir(parents=True, exist_ok=True)
        destino = carpeta / f"sepa_{fecha}.zip"
        if destino.exists():
            logger.info("El ZIP del %s ya está en %s", fecha, carpeta)
        else:
            logger.info("Bajando SEPA minorista del %s (~320 MB)...", fecha)
            tmp = destino.with_suffix(".zip.part")
            with sesion.get(url, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                with open(tmp, "wb") as f:
                    for bloque in resp.iter_content(chunk_size=4 * 1024 * 1024):
                        f.write(bloque)
            tmp.replace(destino)
    for viejo in carpeta.glob("*.zip"):
        if viejo != destino:
            viejo.unlink()
            logger.info("Se borró la descarga anterior %s", viejo.name)
    return destino


def zip_del_dia(carpeta: Path = cfg.DIR_ENTRADA) -> Path:
    """El ZIP más reciente de la carpeta (por la fecha del nombre)."""
    zips = sorted(carpeta.glob("*.zip"), key=lambda p: (FECHA_RE.search(p.name) or [""])[0])
    if not zips:
        raise FileNotFoundError(f"No hay ningún ZIP de SEPA en {carpeta}: correr con --descargar o dejarlo ahí.")
    return zips[-1]


# ============================================================
# CÓDIGOS DE BARRAS
# ============================================================

def digito_verificador_ok(digitos: str) -> bool:
    """Dígito verificador GS1 (vale para EAN-8, UPC-A, EAN-13 y GTIN-14)."""
    cuerpo, verificador = digitos[:-1], int(digitos[-1])
    suma = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(cuerpo)))
    return (10 - suma % 10) % 10 == verificador


def ean_global(codigo: str) -> str | None:
    """
    El EAN con ceros a la izquierda hasta 13 dígitos (14 si es GTIN-14) si es un código de barras global
    válido; None si el dígito verificador no cierra, es demasiado corto o es de circulación restringida.
    """
    digitos = NO_DIGITOS_RE.sub("", codigo or "").lstrip("0")
    if len(digitos) < 8 or len(digitos) > 14 or not digito_verificador_ok(digitos):
        return None
    if len(digitos) == 8 and digitos[0] in "02":
        return None   # EAN-8 restringido
    if len(digitos) == 13 and digitos[0] == "2":
        return None   # EAN-13 de balanza o uso interno
    if len(digitos) == 12 and digitos[0] in "24":
        return None   # UPC-A de peso variable o uso interno (EAN-13 02x / 04x)
    return digitos.zfill(13)


# ============================================================
# LECTURA
# ============================================================

@dataclass
class DatosSEPA:
    fecha: date
    archivo: str
    comercios: pd.DataFrame       # una fila por bandera
    sucursales: pd.DataFrame      # sucursales.csv tal cual (texto), de los comercios leídos
    precios: pd.DataFrame         # producto, tienda, precio, precio_promocion (códigos enteros)
    productos: pd.DataFrame       # producto (código entero) -> clave_producto
    tiendas: pd.DataFrame         # tienda (código entero) -> id_tienda, id_comercio, id_bandera, id_sucursal
    presentaciones: pd.DataFrame  # producto, comercio, descripción, marca, cantidades y unidades, veces
    archivos: pd.DataFrame        # estado de lectura de cada comercio
    filas_leidas: int = 0
    filas_sin_precio: int = 0
    repetidos: int = 0
    promociones_invalidas: int = 0
    omitidos: list[str] = field(default_factory=list)


class _Registro:
    """Asigna códigos enteros estables dentro de la corrida a productos y tiendas."""

    def __init__(self) -> None:
        self.ean: dict[str, str | None] = {}
        self.productos: dict[str, int] = {}
        self.tiendas: dict[str, int] = {}

    def _codificar(self, claves: pd.Series, mapa: dict[str, int]) -> np.ndarray:
        for c in claves.unique():
            if c not in mapa:
                mapa[c] = len(mapa)
        return claves.map(mapa).to_numpy(dtype=np.int32)

    def producto(self, bloque: pd.DataFrame) -> np.ndarray:
        codigo = bloque["id_producto"].fillna("").str.strip()
        es_ean = bloque["productos_ean"].fillna("").str.strip().eq("1")
        for c in codigo[es_ean].unique():
            if c not in self.ean:
                self.ean[c] = ean_global(c)
        clave = codigo.where(es_ean).map(self.ean)
        falta = clave.isna()
        clave[falta] = "cadena" + bloque.loc[falta, "id_comercio"] + "-" + codigo[falta]
        return self._codificar(clave, self.productos)

    def tienda(self, bloque: pd.DataFrame) -> np.ndarray:
        return self._codificar(bloque["id_comercio"] + "-" + bloque["id_bandera"] + "-" + bloque["id_sucursal"],
                               self.tiendas)


def _texto(serie: pd.Series) -> pd.Series:
    return serie.fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()


def _numero(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie.str.strip().str.replace(",", ".", regex=False), errors="coerce")


def _fecha_actualizacion(texto: str) -> date | None:
    m = FECHA_RE.search(texto or "")
    return date.fromisoformat(m.group(1)) if m else None


def leer_tabla_chica(datos: bytes) -> tuple[pd.DataFrame, date | None]:
    """
    comercio.csv o sucursales.csv: rearma los registros partidos en varias líneas (se juntan líneas hasta
    completar los campos del encabezado) y devuelve (tabla de texto, fecha de "Última actualización").
    """
    lineas = datos.decode("utf-8-sig", errors="replace").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    encabezado = [c.strip() for c in lineas[0].split("|")]
    registros, buffer, actualizacion = [], "", None
    for linea in lineas[1:]:
        if not buffer:
            if not linea.strip() or linea.strip("\x00 ") == "":
                continue
            if ACTUALIZACION_RE.search(linea) and "|" not in linea:
                actualizacion = _fecha_actualizacion(linea)
                continue
            buffer = linea
        else:
            buffer += linea if linea.startswith("|") else " " + linea
        campos = next(csv.reader([buffer], delimiter="|"))
        if len(campos) >= len(encabezado):
            registros.append([c.strip() for c in campos[:len(encabezado)]])
            buffer = ""
    tabla = pd.DataFrame(registros, columns=encabezado)
    return tabla.mask(tabla.eq("")), actualizacion


def _vigente(leyenda: pd.Series, dia: date) -> np.ndarray:
    """True si la leyenda incluye el día ("DEL dd/mm/aaaa AL dd/mm/aaaa"); sin fechas legibles se acepta."""
    partes = leyenda.fillna("").str.extract(VIGENCIA_RE)
    resultado = np.ones(len(leyenda), dtype=bool)
    con_fecha = partes.notna().all(axis=1).to_numpy()
    if con_fecha.any():
        p = partes[con_fecha].astype(int)
        desde = pd.to_datetime(dict(year=p[2], month=p[1], day=p[0]), errors="coerce")
        hasta = pd.to_datetime(dict(year=p[5], month=p[4], day=p[3]), errors="coerce")
        d = pd.Timestamp(dia)
        resultado[con_fecha] = ((desde <= d) & (d <= hasta)).fillna(True).to_numpy()
    return resultado


def _leer_productos(archivo, registro: _Registro, dia: date, datos: DatosSEPA
                    ) -> tuple[pd.DataFrame, pd.DataFrame, date | None]:
    precios, presentaciones, actualizacion = [], [], None
    lector = pd.read_csv(
        archivo, sep="|", dtype=str, usecols=lambda c: c.strip() in COLUMNAS_PRODUCTOS,
        chunksize=FILAS_POR_BLOQUE, encoding="utf-8-sig", encoding_errors="replace", on_bad_lines="skip",
        keep_default_na=False, na_values=[""],
    )
    for bloque in lector:
        bloque.columns = [c.strip() for c in bloque.columns]
        es_dato = pd.to_numeric(bloque["id_comercio"], errors="coerce").notna()
        for pie in bloque.loc[~es_dato, "id_comercio"].dropna():
            actualizacion = _fecha_actualizacion(pie) or actualizacion
        bloque = bloque.loc[es_dato].copy()
        for c in ("id_comercio", "id_bandera", "id_sucursal"):
            bloque[c] = bloque[c].str.strip().str.lstrip("0").replace("", "0")
        datos.filas_leidas += len(bloque)
        precio = _numero(bloque["productos_precio_lista"])
        valido = precio.gt(0)
        datos.filas_sin_precio += int((~valido).sum())
        bloque, precio = bloque[valido], precio[valido]
        if bloque.empty:
            continue

        producto = registro.producto(bloque)
        promo = _numero(bloque["productos_precio_unitario_promo1"])
        con_promo = promo.notna().to_numpy()
        if con_promo.any():
            p, lista = promo.to_numpy(), precio.to_numpy()
            ok = con_promo & (p < lista) & (p >= cfg.PROMO_FRACCION_MINIMA * lista)
            vigente = np.ones(len(p), dtype=bool)
            vigente[con_promo] = _vigente(bloque["productos_leyenda_promo1"][con_promo], dia)
            ok &= vigente
            datos.promociones_invalidas += int((con_promo & ~ok).sum())
            promo = promo.where(ok)
        precios.append(pd.DataFrame({
            "producto": producto,
            "tienda": registro.tienda(bloque),
            "precio": precio.to_numpy(dtype=np.float64),
            "precio_promocion": promo.to_numpy(dtype=np.float64),
        }))
        ref = _numero(bloque["productos_precio_referencia"])
        pres = pd.DataFrame({
            "producto": producto,
            "descripcion": _texto(bloque["productos_descripcion"]).to_numpy(),
            "marca": _texto(bloque["productos_marca"]).to_numpy(),
            "cantidad": _texto(bloque["productos_cantidad_presentacion"]).to_numpy(),
            "unidad": _texto(bloque["productos_unidad_medida_presentacion"]).to_numpy(),
            "cantidad_referencia": _texto(bloque["productos_cantidad_referencia"]).to_numpy(),
            "unidad_referencia": _texto(bloque["productos_unidad_medida_referencia"]).to_numpy(),
            "ratio_referencia": (precio / ref.where(ref > 0)).to_numpy(dtype=np.float64),
        })
        claves = [c for c in pres.columns if c != "ratio_referencia"]
        presentaciones.append(pres.groupby(claves, sort=False, dropna=False)["ratio_referencia"]
                              .agg(veces="size", ratio_referencia="median").reset_index())

    if not precios:
        return pd.DataFrame(), pd.DataFrame(), actualizacion
    obs = pd.concat(precios, ignore_index=True)
    n = len(obs)
    # El mismo producto dos veces en la misma sucursal: un solo precio (la mediana) y la menor promoción.
    obs = obs.groupby(["producto", "tienda"], as_index=False, sort=False).agg(
        precio=("precio", "median"), precio_promocion=("precio_promocion", "min"))
    datos.repetidos += n - len(obs)
    pres = pd.concat(presentaciones, ignore_index=True)
    claves = [c for c in pres.columns if c not in ("veces", "ratio_referencia")]
    pres = pres.groupby(claves, sort=False, dropna=False).agg(
        veces=("veces", "sum"), ratio_referencia=("ratio_referencia", "median")).reset_index()
    return obs, pres, actualizacion


def leer_zip(ruta: Path) -> DatosSEPA:
    """Lee el ZIP minorista diario completo de SEPA."""
    m = FECHA_RE.search(ruta.name)
    dia = date.fromisoformat(m.group(1)) if m else date.today()
    registro = _Registro()
    datos = DatosSEPA(fecha=dia, archivo=ruta.name, comercios=pd.DataFrame(), sucursales=pd.DataFrame(),
                      precios=pd.DataFrame(), productos=pd.DataFrame(), tiendas=pd.DataFrame(),
                      presentaciones=pd.DataFrame(), archivos=pd.DataFrame())
    precios, presentaciones, sucursales, comercios, archivos = [], [], [], [], []

    with zipfile.ZipFile(ruta) as z:
        internos = sorted(n for n in z.namelist() if n.lower().endswith(".zip"))
        if not internos:
            raise RuntimeError(f"{ruta.name} no tiene ZIPs por comercio adentro: ¿es el ZIP diario de SEPA?")
        for nombre in internos:
            corto = nombre.rsplit("/", 1)[-1]
            estado = {"archivo": corto, "id_comercio": None, "estado": "", "actualizacion": None,
                      "precios": 0, "sucursales": 0}
            try:
                zi = zipfile.ZipFile(io.BytesIO(z.read(nombre)))
                miembros = {n.lower().rsplit("/", 1)[-1]: n for n in zi.namelist()}
                com, act_com = leer_tabla_chica(zi.read(miembros["comercio.csv"]))
                suc, _ = leer_tabla_chica(zi.read(miembros["sucursales.csv"]))
                with zi.open(miembros["productos.csv"]) as f:
                    obs, pres, act = _leer_productos(f, registro, dia, datos)
            except (zipfile.BadZipFile, KeyError, pd.errors.ParserError, ValueError) as e:
                logger.warning("  %-46s omitido (ZIP vacío o ilegible: %s)", corto, e)
                datos.omitidos.append(corto)
                archivos.append(estado | {"estado": "ilegible"})
                continue
            com = com[pd.to_numeric(com.get("id_comercio"), errors="coerce").notna()]
            id_comercio = int(com["id_comercio"].iloc[0]) if len(com) else None
            act = act or act_com
            estado |= {"id_comercio": id_comercio, "actualizacion": act, "precios": len(obs),
                       "sucursales": len(suc)}
            if obs.empty:
                logger.warning("  %-46s sin precios, se omite", corto)
                archivos.append(estado | {"estado": "sin_precios"})
                continue
            if act is not None and (dia - act).days > cfg.DIAS_MAXIMOS_DESACTUALIZADO:
                logger.warning("  %-46s precios del %s (desactualizado), se excluye", corto, act)
                archivos.append(estado | {"estado": "desactualizado"})
                continue
            archivos.append(estado | {"estado": "ok"})
            precios.append(obs)
            presentaciones.append(pres.assign(comercio=np.int16(id_comercio)))
            sucursales.append(suc)
            comercios.append(com)
            logger.info("  %-46s %5d sucursales %9d precios", corto, len(suc), len(obs))

    if not precios:
        raise RuntimeError(f"No se pudo leer ningún comercio de {ruta.name}")
    datos.precios = pd.concat(precios, ignore_index=True)
    datos.presentaciones = pd.concat(presentaciones, ignore_index=True)
    datos.sucursales = pd.concat(sucursales, ignore_index=True)
    datos.comercios = pd.concat(comercios, ignore_index=True)
    datos.archivos = pd.DataFrame(archivos)
    # Solo los productos y tiendas con algún precio (un comercio excluido ya registró los suyos).
    usados_p, usados_t = set(datos.precios["producto"].unique()), set(datos.precios["tienda"].unique())
    datos.productos = pd.DataFrame({"producto": list(registro.productos.values()),
                                    "clave_producto": list(registro.productos)})
    datos.productos = datos.productos[datos.productos["producto"].isin(usados_p)].reset_index(drop=True)
    datos.presentaciones = datos.presentaciones[datos.presentaciones["producto"].isin(usados_p)]
    tiendas = pd.DataFrame({"tienda": list(registro.tiendas.values()), "id_tienda": list(registro.tiendas)})
    tiendas = tiendas[tiendas["tienda"].isin(usados_t)].reset_index(drop=True)
    partes = tiendas["id_tienda"].str.split("-", expand=True)
    datos.tiendas = tiendas.assign(id_comercio=partes[0].astype(int), id_bandera=partes[1].astype(int),
                                   id_sucursal=partes[2])
    return datos
