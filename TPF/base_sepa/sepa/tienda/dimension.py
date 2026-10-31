"""
dim_tienda: una fila por sucursal con precios ese día, ubicada y validada.

SEPA trae, por sucursal, la dirección, la localidad, la provincia (ISO 3166-2)
y la coordenada. La coordenada a veces está mal: sin signo (cae en el océano
Índico), con los ejes invertidos, sin punto decimal, sobre la dirección de otro
local de la misma empresa o directamente en otra provincia. Cada sucursal pasa
por estos pasos:

  1. arreglos mecánicos de la coordenada (signo, ejes, coma corrida);
  2. Georef ubica la coordenada: provincia, departamento y municipio oficiales;
  3. la dirección se geocodifica (normalizador USIG en CABA, Georef en el
     resto) y se compara con la coordenada de SEPA:
       - si la coordenada cae en la provincia declarada y a menos de
         TOLERANCIA (300 m en CABA, 2 km en el interior, donde la
         geocodificación por altura es menos precisa) de la dirección, se
         mantiene ("sepa");
       - si cae lejos y la dirección es unívoca, se reemplaza por la de la
         dirección ("direccion_usig" / "direccion_georef");
       - si la coordenada está fuera de la provincia declarada y la dirección
         no se encuentra, se usa el centroide de la localidad
         ("centroide_localidad", precisión aproximada);
  4. con la coordenada final se asignan provincia, departamento y municipio
     (Georef) y, en CABA, barrio y comuna oficiales.

Los horarios de cada día se normalizan a "HH:MM-HH:MM" (varios turnos
separados por coma; "" si está cerrado; un cierre después de medianoche se
escribe con hora > 24).
"""

from __future__ import annotations

import logging
import re

import numpy as np
import pandas as pd

from sepa import config as cfg
from sepa.fuentes import geografia
from sepa.fuentes.sepa import DatosSEPA
from sepa.texto import normalizar

logger = logging.getLogger("sepa.tienda")

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
TIPOS = {"HIPERMERCADO": "Hipermercado", "SUPERMERCADO": "Supermercado", "AUTOSERVICIO": "Autoservicio",
         "TRADICIONAL": "Tradicional", "WEB": "Web"}
RANGO_HORARIO_RE = re.compile(r"(\d{1,2})[:.](\d{2})\s*(?:[aA]|-|hasta)\s*(\d{1,2})[:.](\d{2})")
CANDIDATOS_UNIVOCOS_M = 500.0
DISTANCIA_LOCALIDAD_M = 15_000.0


def normalizar_horario(texto: object) -> str | None:
    """'8:00 a 22:00', '09.00 a 13.00 - 17.00 a 21.00', 'Cerrado' -> '08:00-22:00', '09:00-13:00,17:00-21:00', ''."""
    if not isinstance(texto, str) or not texto.strip():
        return None
    t = texto.strip()
    if re.search(r"(?i)cerrad", t):
        return ""
    rangos = []
    for h1, m1, h2, m2 in RANGO_HORARIO_RE.findall(t):
        abre, cierra = int(h1) * 60 + int(m1), int(h2) * 60 + int(m2)
        if abre >= 24 * 60 or cierra > 24 * 60 or int(m1) >= 60 or int(m2) >= 60:
            return None
        if cierra <= abre:
            cierra += 24 * 60
        rangos.append(f"{abre // 60:02d}:{abre % 60:02d}-{cierra // 60:02d}:{cierra % 60:02d}")
    return ",".join(rangos) if rangos else None


def _numero(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie.astype(str).str.strip().str.replace(",", ".", regex=False), errors="coerce")


def corregir_coordenadas(lat: pd.Series, lon: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Arreglos mecánicos: coma corrida, ejes invertidos, signo faltante. Devuelve (lat, lon, corrección)."""
    lat, lon = lat.astype(float).copy(), lon.astype(float).copy()
    correccion = pd.Series("", index=lat.index, dtype=object)
    (la0, la1), (lo0, lo1) = cfg.LAT_ARGENTINA, cfg.LON_ARGENTINA

    def en_rango(a, o):
        return a.between(la0, la1) & o.between(lo0, lo1)

    for serie, limite in ((lat, 90), (lon, 180)):
        grande = serie.abs() > limite
        while grande.any():
            serie[grande] = serie[grande] / 10
            correccion[grande] = "coma_corrida"
            grande = serie.abs() > limite
    invertidas = ~en_rango(lat, lon) & en_rango(lon, lat)
    lat[invertidas], lon[invertidas] = lon[invertidas].to_numpy(), lat[invertidas].to_numpy()
    correccion[invertidas] = "ejes_invertidos"
    for serie, (a, b) in ((lat, cfg.LAT_ARGENTINA), (lon, cfg.LON_ARGENTINA)):
        sin_signo = (serie > 0) & (-serie).between(a, b)
        serie[sin_signo] = -serie[sin_signo]
        correccion[sin_signo] = correccion[sin_signo].where(correccion[sin_signo].ne(""), "signo")
    fuera = ~en_rango(lat, lon)
    correccion[fuera & lat.notna()] = "fuera_de_argentina"
    lat[fuera], lon[fuera] = np.nan, np.nan
    return lat, lon, correccion


def _elegir_candidato(cands: list, lat: float, lon: float, coord_ok: bool) -> tuple[dict | None, bool]:
    """(candidato elegido, unívoco): el más cercano a la coordenada de SEPA si esta es creíble; si no, el primero."""
    if not cands:
        return None, False
    lats = np.array([c["lat"] for c in cands], float)
    lons = np.array([c["lon"] for c in cands], float)
    univoco = len(cands) == 1 or float(np.max(geografia.distancia_m(lats, lons, lats[0], lons[0]))) <= CANDIDATOS_UNIVOCOS_M
    if coord_ok and np.isfinite(lat):
        return cands[int(np.argmin(geografia.distancia_m(lats, lons, lat, lon)))], univoco
    return cands[0], univoco


def armar(datos: DatosSEPA) -> tuple[pd.DataFrame, dict]:
    s = datos.sucursales.copy()
    for c in ("id_comercio", "id_bandera", "id_sucursal"):
        s[c] = s[c].astype(str).str.strip().str.lstrip("0").replace("", "0")
    s["id_tienda"] = s["id_comercio"] + "-" + s["id_bandera"] + "-" + s["id_sucursal"]
    s = s.drop_duplicates("id_tienda")
    con_precios = datos.tiendas[["id_tienda"]]
    stats = {"sucursales_publicadas": len(s), "sucursales_con_precios": len(con_precios),
             "publicadas_sin_precios": int((~s["id_tienda"].isin(con_precios["id_tienda"])).sum())}
    t = con_precios.merge(s, on="id_tienda", how="left", indicator=True)
    stats["con_precios_sin_ficha"] = int(t["_merge"].eq("left_only").sum())
    partes = t["id_tienda"].str.split("-", expand=True)
    t["id_comercio"], t["id_bandera"], t["id_sucursal"] = partes[0].astype(int), partes[1].astype(int), partes[2]

    com = datos.comercios.copy()
    com["id_comercio"] = pd.to_numeric(com["id_comercio"], errors="coerce").astype("Int64")
    com["id_bandera"] = pd.to_numeric(com["id_bandera"], errors="coerce").astype("Int64")
    com = com.dropna(subset=["id_comercio", "id_bandera"]).drop_duplicates(["id_comercio", "id_bandera"])
    t = t.merge(com.rename(columns={"comercio_razon_social": "comercio", "comercio_cuit": "cuit",
                                    "comercio_bandera_nombre": "bandera", "comercio_bandera_url": "bandera_url"})
                [["id_comercio", "id_bandera", "comercio", "cuit", "bandera", "bandera_url"]],
                on=["id_comercio", "id_bandera"], how="left")

    out = pd.DataFrame({"id_tienda": t["id_tienda"], "id_comercio": t["id_comercio"], "id_bandera": t["id_bandera"],
                        "id_sucursal": t["id_sucursal"]})
    out["comercio"] = t["comercio"].str.strip()
    out["cuit"] = t["cuit"].astype(str).str.replace(r"\D", "", regex=True).replace("", np.nan)
    out["bandera"] = t["bandera"].str.strip()
    out["formato"] = out["id_comercio"].map(cfg.FORMATO_COMERCIO).fillna("Supermercado")
    tipo = t["sucursales_tipo"].fillna("").map(normalizar).map(TIPOS)
    out["tipo_sucursal"] = tipo
    out["sucursal_nombre"] = t["sucursales_nombre"].str.strip()
    calle, numero = t["sucursales_calle"].fillna("").str.strip(), t["sucursales_numero"].fillna("").str.strip()
    out["direccion"] = (calle + " " + numero.where(~numero.isin(["0", "S/N", "SN", "s/n"]), "")).str.strip()
    out["direccion"] = out["direccion"].replace("", np.nan)
    out["codigo_postal"] = t["sucursales_codigo_postal"].astype(str).str.extract(r"(\d{4})", expand=False)
    out["localidad_sepa"] = t["sucursales_localidad"].str.strip()
    out["barrio_sepa"] = t["sucursales_barrio"].str.strip()
    iso = t["sucursales_provincia"].fillna("").str.strip().str.upper()
    out["provincia_iso"] = iso.where(iso.isin(geografia.PROVINCIAS.keys()))
    out["es_web"] = tipo.eq("Web")

    lat0, lon0 = _numero(t["sucursales_latitud"]), _numero(t["sucursales_longitud"])
    lat, lon, correccion = corregir_coordenadas(lat0, lon0)
    out["lat_sepa"], out["lon_sepa"] = lat0, lon0
    geo = geografia.ubicar(lat, lon)
    prov_decl = out["provincia_iso"].map(lambda x: geografia.PROVINCIAS.get(x, (None,))[0])
    valida = lat.notna() & geo["provincia_id"].notna()
    prov_ok = valida & (geo["provincia_id"].eq(prov_decl) | prov_decl.isna())

    # Coherencia con la localidad declarada: por nombre (la localidad se llama como la provincia, el departamento
    # o el municipio de la coordenada) o porque Georef conoce una localidad con ese nombre en el departamento de
    # la coordenada. Los nombres informales ("Las Lomas", "Budge", un barrio) existen también en otros lugares, así
    # que una localidad que no coincide solo pesa si es única en la provincia y queda a más de DISTANCIA_LOCALIDAD.
    locs = geografia.localidades(out["localidad_sepa"])
    nombre_loc = out["localidad_sepa"].map(normalizar)
    # Una "localidad" que repite el nombre de la calle ("SAN MARTIN 1162", localidad "SAN MARTIN") no informa nada.
    nombre_loc = nombre_loc.where([not (n and n in normalizar(d)) for n, d in zip(nombre_loc, out["direccion"])], "")
    del_depto = geografia.localidades_de_departamentos(geo["departamento_id"].dropna().unique().tolist())
    por_nombre = pd.Series(False, index=out.index)
    en_depto = pd.Series(False, index=out.index)
    unica = pd.Series(None, index=out.index, dtype=object)
    for i in out.index:
        lugares = [normalizar(geo.at[i, c]) for c in ("provincia_nombre", "departamento_nombre", "municipio_nombre")
                   if isinstance(geo.at[i, c], str)]
        n = nombre_loc[i]
        por_nombre[i] = bool(valida[i]) and len(n) >= 4 and any(n in x or x in n for x in lugares if len(x) >= 4)
        vecinas = [normalizar(x) for x in del_depto.get(geo.at[i, "departamento_id"], [])]
        en_depto[i] = bool(valida[i]) and len(n) >= 4 and (
            any(l["provincia_id"] == geo.at[i, "provincia_id"] and l["departamento_id"] == geo.at[i, "departamento_id"]
                for l in locs[i]) or any(n in v or v in n for v in vecinas if len(v) >= 4))
        prov = prov_decl[i] if isinstance(prov_decl[i], str) else geo.at[i, "provincia_id"]
        en_prov = [l for l in locs[i] if n and l["provincia_id"] == prov and l.get("lat") is not None]
        if len({l["departamento_id"] for l in en_prov}) == 1:
            unica[i] = en_prov[0]
    coherente = por_nombre | en_depto
    lejos = pd.Series([isinstance(u, dict) and bool(valida[i]) and
                       float(geografia.distancia_m(lat[i], lon[i], u["lat"], u["lon"])) > DISTANCIA_LOCALIDAD_M
                       for i, u in unica.items()], index=out.index)
    incoherente = unica.notna() & ~coherente & lejos
    plausible = valida & ((prov_ok & ~incoherente) | (~prov_ok & coherente))

    # Dónde buscar la dirección: en CABA, toda la Ciudad (USIG); en el resto, solo si la coordenada no es
    # plausible y la localidad declarada es única en su provincia (Georef, acotado a esa localidad censal).
    direccion_limpia = out["direccion"].fillna("").map(geografia.limpiar_direccion)
    con_altura = direccion_limpia.str.contains(r"\d", regex=True) & ~out["es_web"]
    caba = con_altura & ((plausible & geo["provincia_id"].eq("02")) | (~plausible & prov_decl.eq("02")))
    interior = con_altura & ~plausible & ~caba & unica.notna()
    cand = pd.Series([[] for _ in range(len(out))], index=out.index, dtype=object)
    if caba.any():
        cand[caba] = geografia.geocodificar_caba(direccion_limpia[caba], out.loc[caba, "id_comercio"])
    if interior.any():
        prov_q = unica[interior].map(lambda u: u["provincia_id"])
        loc_q = unica[interior].map(lambda u: u.get("localidad_censal_id"))
        cand[interior] = geografia.geocodificar(direccion_limpia[interior], prov_q, loc_q)

    fuente, lat_f, lon_f, dist, nomen = [], [], [], [], []
    for i in out.index:
        elegido, univoco = _elegir_candidato(cand[i], lat[i], lon[i], bool(plausible[i]))
        d = (float(geografia.distancia_m(lat[i], lon[i], elegido["lat"], elegido["lon"]))
             if elegido is not None and np.isfinite(lat[i]) else np.nan)
        etiqueta = "direccion_usig" if caba[i] else "direccion_georef"
        if out.at[i, "es_web"]:
            f, la, lo = "web", np.nan, np.nan
        elif plausible[i] and (elegido is None or d <= cfg.TOLERANCIA_DIRECCION_M):
            f, la, lo = "sepa", lat[i], lon[i]
        elif plausible[i] and univoco:
            f, la, lo = etiqueta, elegido["lat"], elegido["lon"]
        elif plausible[i]:
            f, la, lo = "sepa_dudosa", lat[i], lon[i]
        elif elegido is not None and univoco:
            f, la, lo = etiqueta, elegido["lat"], elegido["lon"]
        elif isinstance(unica[i], dict) and not coherente[i] and not prov_ok[i]:
            f, la, lo = "centroide_localidad", unica[i]["lat"], unica[i]["lon"]
        elif np.isfinite(lat[i]):
            f, la, lo = "sepa_dudosa", lat[i], lon[i]
        else:
            f, la, lo = "sin_ubicacion", np.nan, np.nan
        fuente.append(f)
        lat_f.append(la)
        lon_f.append(lo)
        dist.append(d)
        nomen.append((elegido or {}).get("nomenclatura") or (elegido or {}).get("direccion"))
    prov_q = prov_decl.where(prov_decl.notna(), geo["provincia_id"])
    out["ubicacion_fuente"] = fuente
    out["lat"], out["lon"] = lat_f, lon_f
    out["distancia_direccion_m"] = np.round(dist, 0)
    out["direccion_normalizada"] = nomen
    out["correccion_coordenada"] = correccion.replace("", np.nan)
    out["ubicacion_precision"] = out["ubicacion_fuente"].map(
        {"sepa": "exacta", "direccion_usig": "exacta", "direccion_georef": "exacta", "sepa_dudosa": "dudosa",
         "centroide_localidad": "aproximada", "web": "no_aplica", "sin_ubicacion": "sin_ubicacion"})

    # División política oficial de la coordenada final.
    final = geografia.ubicar(out["lat"].astype(float), out["lon"].astype(float))
    out["provincia_id"] = final["provincia_id"].fillna(prov_q)
    nombres = {v[0]: v[1] for v in geografia.PROVINCIAS.values()}
    out["provincia"] = final["provincia_nombre"].fillna(out["provincia_id"].map(nombres))
    out["departamento_id"], out["departamento"] = final["departamento_id"], final["departamento_nombre"]
    out["municipio_id"], out["municipio"] = final["municipio_id"], final["municipio_nombre"]
    en_caba = out["provincia_id"].eq("02") & out["lat"].notna()
    out["barrio"], out["comuna"] = out["barrio_sepa"], pd.array([pd.NA] * len(out), dtype="Int64")
    if en_caba.any():
        bc = geografia.barrios_caba(out.loc[en_caba, "lat"], out.loc[en_caba, "lon"])
        out.loc[en_caba, "barrio"] = bc["barrio"].to_numpy()
        out.loc[en_caba, "comuna"] = bc["comuna"].to_numpy()
    out["localidad"] = out["localidad_sepa"].where(~en_caba, "Ciudad Autónoma de Buenos Aires")

    for dia in DIAS:
        col = next((c for c in t.columns if c.startswith(f"sucursales_{dia}_horario")), None)
        out[f"horario_{dia}"] = t[col].map(normalizar_horario) if col else None

    stats["ubicacion"] = out["ubicacion_fuente"].value_counts().to_dict()
    stats["correcciones_coordenada"] = out["correccion_coordenada"].value_counts().to_dict()
    columnas = ["id_tienda", "id_comercio", "id_bandera", "id_sucursal", "comercio", "cuit", "bandera", "formato",
                "tipo_sucursal", "sucursal_nombre", "direccion", "direccion_normalizada", "codigo_postal", "localidad",
                "barrio", "comuna", "municipio", "municipio_id", "departamento", "departamento_id", "provincia",
                "provincia_id", "provincia_iso", "lat", "lon", "ubicacion_fuente", "ubicacion_precision",
                "distancia_direccion_m", "correccion_coordenada", "lat_sepa", "lon_sepa", "es_web"] + \
               [f"horario_{d}" for d in DIAS]
    return out[columnas].sort_values(["provincia", "comercio", "id_tienda"], ignore_index=True), stats
