"""Normalización de texto compartida por los distintos pasos."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

_NO_ALFANUMERICO = re.compile(r"[^A-Z0-9%]")
_ESPACIOS = re.compile(r"\s+")
PALABRAS_VACIAS = {"con", "sin", "las", "los", "del", "para", "por", "and", "the", "with", "de", "la", "el"}


def sin_tildes(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def normalizar(texto: object) -> str:
    """Mayúsculas, sin tildes ni signos, espacios simples: la forma sobre la que se aplican las reglas."""
    if not isinstance(texto, str):
        return ""
    return _ESPACIOS.sub(" ", _NO_ALFANUMERICO.sub(" ", sin_tildes(texto.upper()))).strip()


def _tokens(texto: str) -> set[str]:
    return {t for t in re.findall(r"[a-z]{3,}", sin_tildes(texto.lower())) if t not in PALABRAS_VACIAS}


def nombre_coincide(sepa: str, otro: str) -> bool:
    """
    Alguna palabra en común entre cómo describe SEPA el producto (sus descripciones y la marca) y el nombre que le
    da otra fuente (Open Food Facts, un catálogo web); se acepta que una sea abreviatura de la otra ("yog" ~
    "yogur"). Sirve para detectar un EAN mal asignado.
    """
    a, b = _tokens(sepa), _tokens(otro)
    if not a or not b:
        return True   # sin texto para comparar no se acusa
    return any(x.startswith(y) or y.startswith(x) or SequenceMatcher(None, x, y).ratio() >= 0.8 for x in a for y in b)


def numero(texto: object) -> float | None:
    """'1,5' -> 1.5; '00750' -> 750.0; vacío o ilegible -> None."""
    if texto is None:
        return None
    t = str(texto).strip().replace(",", ".")
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return None
