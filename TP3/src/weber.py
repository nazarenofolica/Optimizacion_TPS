"""
Pregunta b): un único centro de distribución de capacidad infinita y sin costos de apertura ni de
operación (plan §12 b). Es el único cálculo del trabajo que no usa `modelo.resolver`: el centro
puede estar en cualquier punto del mapa, así que la ubicación es una variable continua.

Sin capacidad ni costos fijos, el problema es un problema de Weber (un punto que minimiza una suma
de distancias ponderadas):

    Min  C(X) =  Σ_k  a · (dem_k / Q) · min_{p ∈ P_k} d(p, X)        tramo 1 (planta -> centro)
               + Σ_i  b · (dem_i / Q) · 2 · d(X, i)                  tramo 2 (centro -> súper)

con dos juegos de pesos:

    "economico"  a = T (tarifa por km de ida)        b = CK + W / K_max ($ por km físico propio)
    "ambiental"  a = 2 (km físicos, ida y vuelta)    b = 1  -> C(X) = km físicos totales

d(·,·) es la distancia en línea recta × factor de ruta (S1, respaldo): OSRM no se puede consultar
para cada punto de una grilla. El punto final se verifica con OSRM en scripts/04_punto_b.py.

Los conductores entran como costo por km (W / K_max): en un punto continuo su cantidad entera es
una función escalonada que no se puede minimizar con métodos de gradiente. El número entero de
conductores se informa después, para el punto elegido.

El `min` sobre plantas (Fideos y Leche tienen dos) hace que C no sea convexa: se busca en una grilla
y se refina con Nelder–Mead desde los mejores puntos. Weiszfeld, con las plantas ya elegidas, es el
control independiente.
"""

import math

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src import datos

KM_POR_GRADO_LAT = 111.32
PASO_GRILLA = 0.004          # grados (≈ 400 m)
MARGEN_GRILLA = 0.03         # grados alrededor de los puntos del mapa
SEMILLAS = 8                 # mejores puntos de la grilla desde los que se refina


def pesos(params, criterio):
    """Pesos por km de cada tramo: (a: tramo 1 por km de ida, b: tramo 2 por km físico)."""
    s = params["supuestos"]
    if criterio == "economico":
        return s["tarifa_T"], params["combustible_km"] + s["W"] / s["K_max"]
    if criterio == "ambiental":
        return 2.0, 1.0
    raise ValueError(f"criterio={criterio!r}: tiene que ser 'economico' o 'ambiental'")


def _haversine_vec(lat, lon, lat2, lon2):
    """Haversine vectorizado [km]; lat/lon pueden ser arrays (grilla) y lat2/lon2 escalares."""
    f1, f2 = np.radians(lat), math.radians(lat2)
    df, dl = f2 - f1, np.radians(lon2 - lon)
    a = np.sin(df / 2) ** 2 + np.cos(f1) * math.cos(f2) * np.sin(dl / 2) ** 2
    return 2 * datos.RADIO_TIERRA_KM * np.arcsin(np.sqrt(a))


class Problema:
    """Datos del problema de Weber para un juego de parámetros y un criterio."""

    def __init__(self, params, criterio="economico", factor=None):
        self.params = params
        self.criterio = criterio
        self.ubic = datos.cargar_ubicaciones()
        self.factor = datos.factor_ruta() if factor is None else factor
        self.Q = params["supuestos"]["Q"]
        self.a, self.b = pesos(params, criterio)
        self.plantas = datos.plantas_por_producto(self.ubic)
        self.dem_k = datos.demanda_por_producto(params).to_dict()
        self.dem_i = datos.demanda_por_super(params).to_dict()

    # --- distancias ----------------------------------------------------------------
    def _d(self, lat, lon, punto):
        p = self.ubic.loc[punto]
        return self.factor * _haversine_vec(lat, lon, p.lat, p.lon)

    def planta_elegida(self, lat, lon):
        """{producto: planta más cercana a X}."""
        return {k: min(ps, key=lambda p: float(self._d(lat, lon, p))) for k, ps in self.plantas.items()}

    # --- función objetivo ------------------------------------------------------------
    def costo(self, lat, lon):
        """C(X). Acepta escalares o arrays (grilla)."""
        total = 0.0
        for k, ps in self.plantas.items():
            d = np.minimum.reduce([self._d(lat, lon, p) for p in ps])
            total = total + self.a * self.dem_k[k] / self.Q * d
        for i, dem in self.dem_i.items():
            total = total + self.b * dem / self.Q * 2 * self._d(lat, lon, i)
        return total

    def desglose(self, lat, lon):
        """km, litros, CO2 y costo económico real del punto (siempre en $, aunque el criterio sea
        ambiental), con los conductores enteros."""
        p = self.params
        s = p["supuestos"]
        elegidas = self.planta_elegida(lat, lon)
        km1 = sum(self.dem_k[k] / self.Q * 2 * float(self._d(lat, lon, elegidas[k])) for k in self.dem_k)
        km2 = sum(dem / self.Q * 2 * float(self._d(lat, lon, i)) for i, dem in self.dem_i.items())
        return evaluar(p, km1 / 2, km2, elegidas)


def evaluar(params, km_ida_t1, km_t2, elegidas=None, extra=None):
    """Costo y emisiones de una ubicación a partir de los km de cada tramo.

    km_ida_t1: km de ida del tramo 1 (la tarifa se cobra sobre la ida, S10); los km físicos son
    el doble. km_t2: km físicos del tramo 2 (ida y vuelta).
    """
    s = params["supuestos"]
    km1 = 2 * km_ida_t1
    conductores = math.ceil(km_t2 / s["K_max"] - 1e-9)
    tramo1 = s["tarifa_T"] * km_ida_t1
    combustible = params["combustible_km"] * km_t2
    litros = (km1 + km_t2) / params["rendimiento"]
    fila = {
        "km_tramo1": km1,
        "km_tramo2": km_t2,
        "km_total": km1 + km_t2,
        "costo_tramo1": tramo1,
        "costo_combustible_t2": combustible,
        "conductores": conductores,
        "costo_conductores": conductores * s["W"],
        "costo_total": tramo1 + combustible + conductores * s["W"],
        "litros": litros,
        "co2_kg": litros * s["phi"],
    }
    if elegidas is not None:
        fila["plantas"] = ", ".join(elegidas[k] for k in sorted(elegidas))
    if extra:
        fila.update(extra)
    return fila


# ---------------------------------------------------------------------------
# Búsqueda del óptimo
# ---------------------------------------------------------------------------


def grilla(problema):
    """C(X) sobre una grilla que cubre todos los puntos del mapa. Devuelve (lats, lons, C)."""
    u = problema.ubic
    lats = np.arange(u["lat"].min() - MARGEN_GRILLA, u["lat"].max() + MARGEN_GRILLA, PASO_GRILLA)
    lons = np.arange(u["lon"].min() - MARGEN_GRILLA, u["lon"].max() + MARGEN_GRILLA, PASO_GRILLA)
    LON, LAT = np.meshgrid(lons, lats)
    return LAT, LON, problema.costo(LAT, LON)


def optimizar(problema):
    """Grilla + Nelder–Mead desde los SEMILLAS mejores puntos. Devuelve (lat, lon, C, grilla)."""
    LAT, LON, C = grilla(problema)
    orden = np.argsort(C, axis=None)[:SEMILLAS]
    mejor = None
    for idx in orden:
        x0 = (LAT.flat[idx], LON.flat[idx])
        r = minimize(lambda v: float(problema.costo(v[0], v[1])), x0, method="Nelder-Mead",
                     options={"xatol": 1e-7, "fatol": 1e-6, "maxiter": 4000})
        if mejor is None or r.fun < mejor.fun:
            mejor = r
    return mejor.x[0], mejor.x[1], float(mejor.fun), (LAT, LON, C)


def weiszfeld(problema, elegidas, lat0, lon0, iteraciones=2000, tol=1e-10):
    """Control independiente: algoritmo de Weiszfeld con las plantas fijas, en una proyección
    plana local (equirectangular). Cada punto pesa (peso por km) × (viajes) × (km por viaje)."""
    coslat = math.cos(math.radians(lat0))
    u = problema.ubic

    def xy(lat, lon):
        return np.array([lon * KM_POR_GRADO_LAT * coslat, lat * KM_POR_GRADO_LAT])

    puntos, w = [], []
    for k, p in elegidas.items():
        puntos.append(xy(u.at[p, "lat"], u.at[p, "lon"]))
        w.append(problema.a * problema.dem_k[k] / problema.Q * problema.factor)
    for i, dem in problema.dem_i.items():
        puntos.append(xy(u.at[i, "lat"], u.at[i, "lon"]))
        w.append(problema.b * dem / problema.Q * 2 * problema.factor)
    puntos, w = np.array(puntos), np.array(w)

    x = xy(lat0, lon0)
    for _ in range(iteraciones):
        d = np.maximum(np.linalg.norm(puntos - x, axis=1), 1e-9)
        nuevo = (w / d) @ puntos / (w / d).sum()
        if np.linalg.norm(nuevo - x) < tol:
            x = nuevo
            break
        x = nuevo
    return x[1] / KM_POR_GRADO_LAT, x[0] / (KM_POR_GRADO_LAT * coslat)


def centro_de_gravedad(problema, elegidas):
    """Promedio de coordenadas ponderado con los mismos pesos (la respuesta "ingenua")."""
    u = problema.ubic
    filas = [(u.at[p, "lat"], u.at[p, "lon"], problema.a * problema.dem_k[k])
             for k, p in elegidas.items()]
    filas += [(u.at[i, "lat"], u.at[i, "lon"], problema.b * 2 * dem) for i, dem in problema.dem_i.items()]
    t = pd.DataFrame(filas, columns=["lat", "lon", "w"])
    return float((t.lat * t.w).sum() / t.w.sum()), float((t.lon * t.w).sum() / t.w.sum())


def distancia_km(lat1, lon1, lat2, lon2):
    """Distancia en línea recta entre dos puntos [km]."""
    return datos.haversine_km(lat1, lon1, lat2, lon2)
