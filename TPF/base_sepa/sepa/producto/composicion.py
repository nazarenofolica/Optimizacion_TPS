"""
Composición de cada producto: con qué está hecho.

Para cada producto y cada atributo se decide un estado de tres valores:
"si" (lo contiene / tiene la característica), "no" (no lo contiene: declarado
o seguro por la naturaleza del alimento) o "desconocido" (sin evidencia).

  alérgenos (contiene_*): gluten (TACC), leche, huevo, maní, frutos secos,
                          soja, pescado, mariscos, sésamo
  trazas: "puede contener", como lista de alérgenos
  aptitudes: apto_vegetariano, apto_vegano, sin_tacc, sin_lactosa
  procesamiento: nova (1 a 4), aditivos (cantidad), azucar_agregada,
                 edulcorantes, aceite_palma

Fuentes, de la más a la menos confiable (una posterior pisa a una anterior):
  4. la naturaleza del alimento genérico (referencia/composicion_alimentos.csv):
     una nalga es carne, sin gluten ni leche; una galletita puede tener casi
     cualquier cosa ("desconocido");
  3. el texto de ingredientes analizado con reglas ("harina de trigo" ->
     gluten; "puede contener maní" -> trazas de maní; "sin TACC" -> sin gluten);
  2. Open Food Facts: alérgenos, trazas, etiquetas, análisis de ingredientes,
     aditivos y NOVA declarados;
  1. catálogo web de Jumbo, Disco y Vea: alérgenos y trazas declarados y
     certificaciones (gluten_free, lactose_free, vegan...).
Al final se fuerza la consistencia: lo que contiene leche, huevo, pescado o
mariscos no es vegano; lo que contiene pescado o mariscos no es vegetariano.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from sepa import config as cfg
from sepa.texto import sin_tildes

ALERGENOS = ["gluten", "leche", "huevo", "mani", "frutos_secos", "soja", "pescado", "mariscos", "sesamo"]
NOMBRE_ALERGENO = {"gluten": "gluten", "leche": "leche", "huevo": "huevo", "mani": "maní",
                   "frutos_secos": "frutos secos", "soja": "soja", "pescado": "pescado", "mariscos": "mariscos",
                   "sesamo": "sésamo"}

OFF_ALERGENOS = {"en:gluten": "gluten", "en:milk": "leche", "en:eggs": "huevo", "en:peanuts": "mani",
                 "en:nuts": "frutos_secos", "en:soybeans": "soja", "en:fish": "pescado", "en:crustaceans": "mariscos",
                 "en:molluscs": "mariscos", "en:sesame-seeds": "sesamo"}
WEB_ALERGENOS = {
    "gluten": r"TRIGO|AVENA|CEBADA|CENTENO|GLUTEN|TACC", "leche": r"LECHE|LACT|CASEIN|SUERO", "huevo": r"HUEVO",
    "mani": r"\bMANI\b|CACAHUATE",
    "frutos_secos": r"FRUTOS? SECOS|NUEZ|NUECES|ALMENDRA|AVELLANA|CASTANA|PISTACHO|CAJU|ANACARDO|PECAN",
    "soja": r"SOJA|SOYA", "pescado": r"PESCADO|PECES", "mariscos": r"MARISCO|CRUSTACEO|MOLUSCO|CAMARON|LANGOSTINO",
    "sesamo": r"SESAMO",
}
WEB_CERTIFICACIONES = {
    "gluten_free": [("contiene_gluten", "no"), ("sin_tacc", "si")], "lactose_free": [("sin_lactosa", "si")],
    "aplv_suitable": [("contiene_leche", "no")], "egg_free": [("contiene_huevo", "no")],
    "peanut_free": [("contiene_mani", "no")], "nuts_free": [("contiene_frutos_secos", "no")],
    "soy_free": [("contiene_soja", "no")], "fish_free": [("contiene_pescado", "no")],
    "seafood_free": [("contiene_mariscos", "no")], "vegan": [("apto_vegano", "si"), ("apto_vegetariano", "si")],
    "vegetarian": [("apto_vegetariano", "si")],
}
ING_ALERGENOS = {
    "gluten": r"\bTRIGO\b|HARINA(?! DE (MAIZ|ARROZ|MANDIOCA|GARBANZO|SOJA|ALMENDRA|COCO|LINO|AVENA SIN))|\bAVENA\b|"
              r"CEBADA|CENTENO|\bMALTA\b|SEMOLA|GLUTEN|SALVADO",
    "leche": r"\bLECHE\b(?! DE (COCO|ALMENDRA|SOJA|AVENA|ARROZ|CAJU|MANI))|LACTOSA|SUERO|CASEIN|\bCREMA DE LECHE|"
             r"MANTECA(?! DE (CACAO|MANI))|\bQUESO|LACTEO|LACTOSUERO",
    "huevo": r"\bHUEVO|ALBUMINA|\bYEMA|OVOPRODUCTO",
    "mani": r"\bMANI\b|CACAHUATE",
    "frutos_secos": r"ALMENDRA|AVELLANA|\bNUEZ|NUECES|CASTANA DE CAJU|\bCAJU|ANACARDO|PISTACHO|PECAN|MACADAMIA",
    "soja": r"\bSOJA\b|\bSOYA\b",
    "pescado": r"PESCADO|ATUN|MERLUZA|SALMON|SARDINA|ANCHOA|CABALLA|BACALAO",
    "mariscos": r"CAMARON|LANGOSTINO|CRUSTACEO|MOLUSCO|CALAMAR|MEJILLON|ALMEJA|PULPO",
    "sesamo": r"SESAMO",
}
ING_ANIMAL = (r"\bCARNE|\bVACUN|\bCERDO|\bPOLLO|\bPAVO|GELATINA|GRASA BOVINA|GRASA VACUNA|\bJAMON|PANCETA|TOCINO|"
              r"COLAGENO|CALDO DE (CARNE|POLLO|GALLINA)")
ING_EDULCORANTES = (r"SUCRALOSA|ASPARTAM|ACESULFAM|SACARINA|CICLAMAT|STEVIA|ESTEVIA|GLUCOSIDOS DE ESTEVIOL|"
                    r"MALTITOL|SORBITOL|ERITRITOL|XILITOL")
ING_AZUCAR = r"\bAZUCAR|JARABE|\bGLUCOSA|FRUCTOSA|DEXTROSA|SACAROSA|\bMIEL\b|AZUCAR INVERTIDO|MALTODEXTRINA"
ING_PALMA = r"\bPALMA\b|PALMISTE"
# Schär y Aglu solo hacen productos sin gluten
SIN_TACC = r"SIN TACC|LIBRE DE GLUTEN|SIN GLUTEN|\bS TACC\b|\bS ?GLU(TEN)?\b|CELIAC\w*|\bSCHAR\b|\bAGLU\b"
TRAZAS_RE = r"PUEDE CONTENER|TRAZAS|ELABORADO EN (UNA )?(PLANTA|LINEA)|COMPARTE"


def _norm(t: object) -> str:
    if not isinstance(t, str):
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9%,;.()]", " ", sin_tildes(t.upper()))).strip()


def _tags(valor: object) -> set[str]:
    return {t.strip() for t in str(valor).split(",") if t.strip()} if isinstance(valor, str) else set()


def _componer(descripcion: str, regla: dict, web: dict | None, off: dict | None) -> dict:
    v: dict = {}
    # 4) naturaleza del alimento
    procesado = int(regla.get("nova") or 1) >= 3
    for a in ALERGENOS:
        v[f"contiene_{a}"] = regla[a]
        v[f"trazas_{a}"] = "desconocido" if procesado else "no"
    v["apto_vegetariano"], v["apto_vegano"] = regla["apto_vegetariano"], regla["apto_vegano"]
    for k in ("sin_tacc", "sin_lactosa", "aceite_palma", "edulcorantes", "azucar_agregada"):
        v[k] = "desconocido"
    if not procesado:
        v["aceite_palma"] = v["edulcorantes"] = v["azucar_agregada"] = "no"
        if regla["gluten"] == "no":
            v["sin_tacc"] = "si"              # alimento natural sin gluten (fruta, carne, arroz)
    if regla["leche"] == "no":
        v["sin_lactosa"] = "si"
    v["nova"], v["aditivos"] = int(regla.get("nova") or 1), np.nan
    fuente = "alimento genérico"

    # 3) texto de ingredientes (web; si no, Open Food Facts)
    texto = ""
    if web is not None and isinstance(web.get("ingredientes"), str) and len(web["ingredientes"]) >= 15:
        texto = web["ingredientes"]
    elif off is not None and isinstance(off.get("ingredientes"), str) and len(off["ingredientes"]) >= 15:
        texto = off["ingredientes"]
    if texto:
        fuente = "ingredientes"
        norm = _norm(texto)
        m = re.search(TRAZAS_RE, norm)
        principal, trazas = (norm[:m.start()], norm[m.start():]) if m else (norm, "")
        # La lista de ingredientes del producto manda sobre la suposición del alimento, en los dos sentidos.
        for a, rx in ING_ALERGENOS.items():
            v[f"contiene_{a}"] = "si" if re.search(rx, principal) else "no"
            v[f"trazas_{a}"] = "si" if re.search(rx, trazas) else "no"
        animal = bool(re.search(ING_ANIMAL, principal))
        lacteo_huevo_miel = (v["contiene_leche"] == "si" or v["contiene_huevo"] == "si"
                             or bool(re.search(r"\bMIEL\b", principal)))
        mar = v["contiene_pescado"] == "si" or v["contiene_mariscos"] == "si"
        if animal or mar:
            v["apto_vegetariano"] = v["apto_vegano"] = "no"
        else:
            if v["apto_vegetariano"] == "desconocido":
                v["apto_vegetariano"] = "si"
            if lacteo_huevo_miel:
                v["apto_vegano"] = "no"
            elif v["apto_vegano"] == "desconocido":
                v["apto_vegano"] = "si"
        v["edulcorantes"] = "si" if re.search(ING_EDULCORANTES, principal) else "no"
        v["azucar_agregada"] = "si" if re.search(ING_AZUCAR, principal) else "no"
        v["aceite_palma"] = "si" if re.search(ING_PALMA, principal) else "no"
        if v["contiene_leche"] == "no":
            v["sin_lactosa"] = "si"
    if re.search(SIN_TACC, _norm(descripcion) + " " + _norm(texto)):
        v["sin_tacc"], v["contiene_gluten"] = "si", "no"

    # 2) Open Food Facts: lo declarado
    if off is not None:
        al, tr = _tags(off.get("alergenos_tags")), _tags(off.get("trazas_tags"))
        if al or tr:
            fuente = "rótulo (Open Food Facts)"
        for tag, a in OFF_ALERGENOS.items():
            if tag in al:
                v[f"contiene_{a}"] = "si"
            if tag in tr:
                v[f"trazas_{a}"] = "si"
        lb, an = _tags(off.get("etiquetas_tags")), _tags(off.get("analisis_ingredientes_tags"))
        if lb & {"en:no-gluten", "en:gluten-free", "es:sin-tacc", "en:sin-tacc", "es:sin-gluten"}:
            v["sin_tacc"], v["contiene_gluten"] = "si", "no"
        if lb & {"en:no-lactose", "en:lactose-free", "es:sin-lactosa"}:
            v["sin_lactosa"] = "si"
        if "en:vegan" in lb or "en:vegan" in an:
            v["apto_vegano"] = v["apto_vegetariano"] = "si"
        elif "en:non-vegan" in an:
            v["apto_vegano"] = "no"
        if "en:vegetarian" in lb or "en:vegetarian" in an:
            v["apto_vegetariano"] = "si"
        elif "en:non-vegetarian" in an:
            v["apto_vegetariano"] = v["apto_vegano"] = "no"
        if "en:palm-oil" in an:
            v["aceite_palma"] = "si"
        elif "en:palm-oil-free" in an:
            v["aceite_palma"] = "no"
        nova = pd.to_numeric(off.get("nova"), errors="coerce")
        if pd.notna(nova):
            v["nova"] = int(nova)
        aditivos = pd.to_numeric(off.get("aditivos_n"), errors="coerce")
        if pd.notna(aditivos):
            v["aditivos"] = int(aditivos)

    # 1) catálogo web: alérgenos y trazas declarados, certificaciones, azúcar
    if web is not None:
        dec, tra = _norm(web.get("alergenos")), _norm(web.get("trazas"))
        if dec or tra or web.get("certificaciones"):
            fuente = "rótulo (catálogo web)"
        for a, rx in WEB_ALERGENOS.items():
            if dec and re.search(rx, dec):
                v[f"contiene_{a}"] = "si"
            if tra:
                v[f"trazas_{a}"] = "si" if re.search(rx, tra) else "no"
        for cert in str(web.get("certificaciones") or "").split("|"):
            for atributo, valor in WEB_CERTIFICACIONES.get(cert, []):
                v[atributo] = valor
        azucar = _norm(web.get("contiene_azucar"))
        if azucar.startswith("SI"):
            v["azucar_agregada"] = "si"
        elif azucar.startswith("NO"):
            v["azucar_agregada"] = "no"

    # Consistencia final.
    if any(v[f"contiene_{a}"] == "si" for a in ("leche", "huevo", "pescado", "mariscos")):
        v["apto_vegano"] = "no"
    if any(v[f"contiene_{a}"] == "si" for a in ("pescado", "mariscos")):
        v["apto_vegetariano"] = "no"
    if v["apto_vegano"] == "si" and v["apto_vegetariano"] != "si":
        v["apto_vegetariano"] = "si"
    if v["contiene_gluten"] == "si":
        v["sin_tacc"] = "desconocido" if v["sin_tacc"] == "si" else "no"   # contradicción: no se afirma nada
    certificado_sin_lactosa = web is not None and "lactose_free" in str(web.get("certificaciones"))
    if v["contiene_leche"] == "si" and v["sin_lactosa"] == "si" and not certificado_sin_lactosa:
        v["sin_lactosa"] = "desconocido"

    trazas = [NOMBRE_ALERGENO[a] for a in ALERGENOS if v.pop(f"trazas_{a}") == "si"]
    v["puede_contener"] = ", ".join(trazas)
    v["ingredientes"] = texto.strip() or None
    v["fuente_composicion"] = fuente
    return v


def armar(productos: pd.DataFrame, off: pd.DataFrame, web: pd.DataFrame) -> pd.DataFrame:
    """productos: producto, clave_producto, descripcion, alimento_id. Una fila por producto."""
    reglas = pd.read_csv(cfg.RUTA_COMPOSICION_ALIMENTOS, sep=";", dtype=str, encoding="utf-8-sig",
                         keep_default_na=False).set_index("id").to_dict("index")
    off_d = off.set_index("ean").to_dict("index") if len(off) else {}
    web_d = web.set_index("ean").to_dict("index") if len(web) else {}
    filas = [{"producto": p, **_componer(d, reglas[a], web_d.get(c), off_d.get(c))}
             for p, c, d, a in zip(productos["producto"], productos["clave_producto"], productos["descripcion"],
                                   productos["alimento_id"])]
    out = pd.DataFrame(filas)
    out["nova"] = out["nova"].astype("Int64")
    out["aditivos"] = pd.to_numeric(out["aditivos"], errors="coerce").astype("Int64")
    return out
