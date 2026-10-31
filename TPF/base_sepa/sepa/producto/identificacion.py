"""
Descripción, marca y nombre legible de cada producto.

Cada cadena escribe la descripción y la marca a su manera ("GASEO POMELO",
"Gaseosa Pomelo 2,25 L", "LECH DESC LIVIAN L/V"). Se toma como descripción
la que aparece en más sucursales, se guardan las alternativas (sirven para
clasificar cuando la principal está cortada) y se arma un nombre legible: la
descripción más completa entre las de todas las cadenas, sin tamaños, códigos
de envase ni etiquetas internas, y con las abreviaturas más comunes
expandidas ("Merm light naranja BOT-390-gr." -> "Mermelada light naranja").
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

MARCAS_VACIAS = {"", "S/D", "SD", "SIN MARCA", "GENERICO", "GENÉRICO", "VARIOS", ".", "-", "SIN DEFINIR", "NO APLICA"}


def _marca_completa(presentaciones: pd.DataFrame, principal: pd.Series) -> pd.Series:
    """
    Hay cadenas que cortan la marca ("LA SE", "MOLIN"): si otra cadena informa una versión más larga que
    empieza igual ("LA SERENISIMA") se usa esa. Si la marca más usada está vacía, la más usada no vacía.
    """
    m = presentaciones.assign(m=presentaciones["marca"].fillna("").str.strip())
    m = m[~m["m"].str.upper().isin(MARCAS_VACIAS)]
    votos = (m.groupby(["producto", "m"])["veces"].sum().reset_index()
             .sort_values(["producto", "veces"], ascending=[True, False]))
    opciones = votos.groupby("producto")["m"].agg(list)

    def elegir(producto, actual):
        lista = opciones.get(producto, [])
        vacia = not isinstance(actual, str) or actual.strip().upper() in MARCAS_VACIAS
        if not lista:
            return "" if vacia else actual
        base = lista[0] if vacia else actual
        mas_largas = [x for x in lista if x.upper().startswith(base.strip().upper()) and len(x) > len(base)]
        return max(mas_largas, key=len) if mas_largas else base

    return pd.Series([elegir(p, a) for p, a in principal.items()], index=principal.index)


def armar(presentaciones: pd.DataFrame) -> pd.DataFrame:
    """presentaciones -> una fila por producto: descripcion, descripciones_alternativas, marca, nombre."""
    pres = presentaciones[["producto", "descripcion", "marca", "veces"]]
    por_desc = (pres.groupby(["producto", "descripcion"])["veces"].sum().reset_index()
                .sort_values(["producto", "veces"], ascending=[True, False]))
    principal = por_desc.drop_duplicates("producto").set_index("producto")["descripcion"]
    alternativas = (por_desc[por_desc["descripcion"].ne("")].groupby("producto")["descripcion"]
                    .agg(lambda s: " | ".join(list(s)[1:4])).replace("", np.nan))
    marcas = (pres.groupby(["producto", "marca"])["veces"].sum().reset_index()
              .sort_values(["producto", "veces"], ascending=[True, False])
              .drop_duplicates("producto").set_index("producto")["marca"])
    out = pd.DataFrame({"descripcion": principal})
    out["descripciones_alternativas"] = alternativas.reindex(out.index)
    out["marca"] = _marca_completa(pres, marcas.reindex(out.index))
    out["nombre"] = [mejor_nombre(d, a, m) for d, a, m in
                     zip(out["descripcion"], out["descripciones_alternativas"], out["marca"])]
    return out.reset_index()


# ============================================================
# NOMBRE LEGIBLE
# ============================================================

_CODIGO_ENVASE = re.compile(r"\b[A-Za-z/]{2,4}-\d+(?:[.,]\d+)?-[A-Za-z0-9]{1,3}\.?", re.IGNORECASE)
_ETIQUETA_CADENA = re.compile(r"\((?:T|PAX|PUX|SAX|BEX|GA|E|C3|AV|M|MP|BR|SC|CTO)\)\s*(?:G\b)?", re.IGNORECASE)
_TAMANO = re.compile(
    r"\b(?:X\s*)?\d+(?:[.,]\d+)?\s*(?:KG|KGM|KGR|KGS|G|GR|GRS|GRM|GRAMOS|MG|ML|CC|CM3|L|LT|LTS|LTR|LITROS?|"
    r"U|UN|UNI|UNID|UNIDADES|UDS|UD|CU|SAQ|SAQUITOS)\b\.?|\bX\s*(?:KG|KILO|UNI|UNIDAD|UN|\d+)\b\.?|"
    r"\bPOR\s+KG\b|\bXKG\b|\bX\b\s*$|\b\d+/\d+\s*(?:KG|K)\b",
    re.IGNORECASE,
)
_ANONIMA_FINAL = re.compile(r",\s*[\d.,]+\s*(?:gr|kgr|kg|cm3|ml|cc|un|cu|lt|l)\s*$", re.IGNORECASE)
_PREFIJO_CADENA = re.compile(r"^(?:DISC[:\s]+\w+\s+|DISC\s+)", re.IGNORECASE)   # Axion: "DISC:AR ALIM LIQ ..."
# Siglas de envase que agregan las cadenas ("bot", "paq", "doy", "tub") y no dicen nada del producto.
_ENVASE = {"bot", "botella", "tub", "paq", "pet", "fra", "fco", "frco", "frasco", "dp", "doy", "doypack", "bsa",
           "bja", "cja", "est", "estuche", "sob", "sobre", "lat", "pot", "sch", "sachet", "brk", "ttb", "bli",
           "ev", "atm", "pck", "pza", "hma", "sc", "s/e", "tetra", "cartón", "carton", "bolsa", "caja", "pvc",
           "pou", "fwp", "bde", "bob", "cub", "aer", "eti"}
# Abreviaturas frecuentes de las descripciones de SEPA.
_ABREVIATURAS = {
    "c": "con", "s": "sin", "d": "de", "p": "para", "merm": "mermelada", "inst": "instantáneo", "orig": "original",
    "gall": "galletitas", "gallet": "galletitas", "galletit": "galletitas", "lech": "leche", "lche": "leche",
    "desc": "descremada", "descr": "descremada", "ent": "entera", "choc": "chocolate", "cho": "chocolate",
    "chocol": "chocolate", "dce": "dulce", "qso": "queso", "yog": "yogur", "beb": "bebible", "sab": "sabor",
    "gaseo": "gaseosa", "gase": "gaseosa", "cerv": "cerveza", "vno": "vino", "fid": "fideos", "arr": "arroz",
    "hna": "harina", "mant": "manteca", "jam": "jamón", "pol": "polvo", "acond": "acondicionado",
    "ddl": "dulce de leche", "rell": "relleno", "integr": "integral", "tom": "tomate", "trit": "triturado",
    "cong": "congelado", "ahum": "ahumado", "fet": "feteado", "fetead": "feteado", "nat": "natural",
    "frut": "frutilla", "vain": "vainilla", "mzna": "manzana", "nja": "naranja", "dur": "durazno", "azuc": "azúcar",
    "ac": "aceite", "acei": "aceite", "galle": "galletitas", "bco": "blanco", "ngo": "negro", "pque": "paquete",
    "salch": "salchichas", "hamb": "hamburguesa", "mila": "milanesa", "boc": "bocaditos", "verd": "verdura",
    "espin": "espinaca", "crem": "cremoso", "ultrap": "ultrapasteurizada", "uat": "larga vida", "lv": "larga vida",
}


def _expandir(texto: str) -> str:
    palabras = []
    for palabra in texto.split():
        clave = palabra.strip(".")
        if clave in _ENVASE:
            continue
        if len(clave) == 1 and clave not in _ABREVIATURAS and clave not in {"a", "y", "e", "o", "u"}:
            continue   # letras sueltas que quedan de "l/v", "c/s"
        palabras.append(_ABREVIATURAS.get(clave, clave if palabra.endswith("..") else palabra.rstrip(".")))
    return " ".join(palabras)


def limpiar_nombre(texto: str, marca: str = "") -> str:
    t = texto if isinstance(texto, str) else ""
    t = _PREFIJO_CADENA.sub("", t)
    t = _ANONIMA_FINAL.sub("", t)
    t = _CODIGO_ENVASE.sub(" ", t)
    t = _ETIQUETA_CADENA.sub(" ", t)
    t = re.sub(r",\s*\.\s*,?", " ", t)           # "POMELO, ., 1 kgr"
    t = _TAMANO.sub(" ", t)
    t = re.sub(r"\*+|\"|\(\s*\)", " ", t)
    t = t.replace(",", " ").replace("/", " ").replace(".", ". ")
    t = re.sub(r"\s+", " ", t).strip(" .-_")
    if not t:
        return ""
    t = _expandir(t.lower())
    t = re.sub(r"\s+", " ", t).strip(" .-_")
    if not t:
        return ""
    # La marca, si aparece, con mayúsculas iniciales ("Gallo Oro", "La Serenísima").
    for palabra in (marca if isinstance(marca, str) else "").lower().split():
        if len(palabra) > 2:
            t = re.sub(rf"\b{re.escape(palabra)}\b", palabra.capitalize(), t)
    return t[0].upper() + t[1:]


def mejor_nombre(descripcion: str, alternativas: str | None, marca: str) -> str:
    """
    Entre cómo lo describen las distintas cadenas, la descripción más legible: más palabras completas y
    menos abreviaturas (hay cadenas que cortan en 20 caracteres: "LECH DESC LIVIAN L/V").
    """
    candidatos = [descripcion if isinstance(descripcion, str) else ""]
    if isinstance(alternativas, str) and alternativas:
        candidatos += alternativas.split(" | ")

    def puntaje(c: str) -> tuple[int, int]:
        palabras = re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]+", c)
        completas = sum(len(p) >= 4 for p in palabras)
        abreviadas = c.count(".") + sum(len(p) <= 2 for p in palabras)
        return completas - abreviadas, -abs(len(c) - 40)

    elegido = max(candidatos, key=puntaje)
    return limpiar_nombre(elegido, marca)[:80]
