"""
Tiempo caminando desde un punto hasta las sucursales candidatas, con rutas peatonales reales de OpenRouteService
(perfil foot-walking, datos de OpenStreetMap). Es el espejo en Python de canasta/web/rutas.js.

La clave va en la variable de entorno ORS_API_KEY o en base_sepa/.env (ORS_API_KEY=...). Sin clave, o si el servicio
falla (clave inválida, cuota agotada, sin conexión), el tiempo se estima con la distancia en línea recta y queda
marcado como estimado (fuente "estimado"): nunca se presenta como una ruta real.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import requests

from canasta import config as cfg
from canasta import oferta

logger = logging.getLogger("canasta.rutas")

RUTA_ENV = Path(__file__).resolve().parents[1] / ".env"


class ErrorRutas(RuntimeError):
    """El servicio de rutas no dio una respuesta usable; el mensaje se puede mostrar tal cual."""


def leer_env(ruta: Path = RUTA_ENV) -> dict[str, str]:
    """Lector mínimo de .env (CLAVE=valor por línea, # comenta); no pisa variables ya definidas."""
    valores: dict[str, str] = {}
    if not ruta.exists():
        return valores
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        valores[clave.strip()] = valor.strip().strip("'\"")
    return valores


def clave_ors() -> str:
    return (os.environ.get("ORS_API_KEY") or leer_env().get("ORS_API_KEY") or "").strip()


def mensaje_error(estado: int | None) -> str:
    if estado in (401, 403):
        return "La clave de OpenRouteService no es válida o no tiene permiso para este servicio."
    if estado == 429:
        return "Se agotó la cuota de consultas de OpenRouteService (se renueva cada día)."
    if estado is None:
        return "No se pudo conectar con OpenRouteService."
    return f"OpenRouteService respondió con un error ({estado})."


def matriz_caminando(origen: tuple[float, float], destinos: list[tuple[float, float]], clave: str,
                     sesion: requests.Session | None = None) -> list[dict | None]:
    """Minutos y metros caminando desde origen (lat, lon) hasta cada destino (lat, lon). None si no hay ruta."""
    if not destinos:
        return []
    if not clave:
        raise ErrorRutas("Falta la clave de OpenRouteService (ORS_API_KEY).")
    puntos = [[origen[1], origen[0]]] + [[lon, lat] for lat, lon in destinos]
    cuerpo = {"locations": puntos, "sources": [0], "destinations": list(range(1, len(puntos))),
              "metrics": ["duration", "distance"]}
    url = f"{cfg.RUTEO_SERVIDOR}/v2/matrix/{cfg.RUTEO_PERFIL}"
    try:
        r = (sesion or requests).post(url, json=cuerpo, headers={"Authorization": clave},
                                      timeout=cfg.RUTEO_TIEMPO_ESPERA_S)
    except requests.RequestException as err:
        raise ErrorRutas(mensaje_error(None)) from err
    if r.status_code != 200:
        raise ErrorRutas(mensaje_error(r.status_code))
    datos = r.json()
    try:
        duraciones, distancias = datos["durations"][0], datos["distances"][0]
    except (KeyError, IndexError, TypeError) as err:
        raise ErrorRutas("OpenRouteService devolvió una respuesta inesperada.") from err
    salida = []
    for seg, metros in zip(duraciones, distancias):
        if seg is None:
            salida.append(None)          # el destino no está conectado a la red peatonal
        else:
            salida.append({"minutos": round(seg / 60, 1), "metros": None if metros is None else round(metros),
                           "fuente": "ruta"})
    return salida


def tiempos_caminando(lat: float, lon: float, minutos: float, clave: str | None = None,
                      sesion: requests.Session | None = None) -> tuple[dict[str, dict], str | None]:
    """Tiempo caminando a las sucursales candidatas para ese límite: ({id_tienda: {minutos, metros, fuente}}, aviso).
    Si el servicio de rutas falla, los tiempos se estiman y el aviso dice por qué."""
    d = oferta.cargar()
    cand = oferta.candidatas_caminando(d, lat, lon, minutos)
    if cand.empty:
        return {}, None
    clave = clave_ors() if clave is None else clave
    try:
        filas = matriz_caminando((lat, lon), list(zip(cand["lat"], cand["lon"])), clave, sesion)
        return {i: f for i, f in zip(cand.index, filas) if f is not None}, None
    except ErrorRutas as err:
        logger.warning("Rutas: %s Se usan tiempos estimados.", err)
        estimados = oferta.minutos_estimados(cand["distancia_km"].to_numpy())
        tiempos = {i: {"minutos": round(float(m), 1), "metros": None, "fuente": "estimado"}
                   for i, m in zip(cand.index, estimados)}
        return tiempos, f"{err} Los tiempos son estimados por distancia en línea recta, no rutas reales."
