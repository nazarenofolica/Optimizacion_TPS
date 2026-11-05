"""
De lo que escribe la persona a una coordenada, con la API Georef (Servicio de Normalización de Datos Geográficos de
Argentina): primero la dirección (calle y altura, interpolada sobre la cartografía de calles); si no aparece, el
centroide de la localidad.
"""

from __future__ import annotations

import logging

import requests

from canasta import config as cfg

logger = logging.getLogger("canasta.ubicacion")

PROVINCIAS = [
    "Ciudad Autónoma de Buenos Aires", "Buenos Aires", "Catamarca", "Chaco", "Chubut", "Córdoba", "Corrientes",
    "Entre Ríos", "Formosa", "Jujuy", "La Pampa", "La Rioja", "Mendoza", "Misiones", "Neuquén", "Río Negro", "Salta",
    "San Juan", "San Luis", "Santa Cruz", "Santa Fe", "Santiago del Estero",
    "Tierra del Fuego, Antártida e Islas del Atlántico Sur", "Tucumán",
]


def _get(recurso: str, params: dict) -> dict:
    r = requests.get(f"{cfg.URL_GEOREF}/{recurso}", params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def buscar(direccion: str, provincia: str = "", localidad: str = "") -> list[dict]:
    """Hasta 5 lugares candidatos: {nombre, lat, lon, precision}."""
    direccion, provincia, localidad = direccion.strip(), provincia.strip(), localidad.strip()
    filtros = {k: v for k, v in (("provincia", provincia), ("localidad", localidad)) if v}
    salida = []
    if direccion:
        try:
            j = _get("direcciones", {"direccion": direccion, "max": 5, **filtros})
            for d in j.get("direcciones", []):
                u = d.get("ubicacion") or {}
                if u.get("lat") is not None:
                    salida.append({"nombre": d["nomenclatura"], "lat": u["lat"], "lon": u["lon"],
                                   "precision": "dirección"})
        except requests.RequestException as e:
            logger.warning("Georef direcciones: %s", e)
    if not salida and (localidad or (direccion and not filtros)):
        try:
            j = _get("localidades", {"nombre": localidad or direccion, "max": 5,
                                     **({"provincia": provincia} if provincia else {})})
            for loc in j.get("localidades", []):
                c = loc["centroide"]
                nombre = f"{loc['nombre']}, {loc['departamento']['nombre']}, {loc['provincia']['nombre']}"
                salida.append({"nombre": nombre, "lat": c["lat"], "lon": c["lon"], "precision": "localidad"})
        except requests.RequestException as e:
            logger.warning("Georef localidades: %s", e)
    return salida
