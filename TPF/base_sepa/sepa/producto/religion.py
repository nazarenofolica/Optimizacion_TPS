"""
Dieta y religión: lo que hace falta saber de cada producto para ofrecer una canasta sin cerdo, halal o kosher.

Columnas (si / no / desconocido, como los alérgenos de composicion.py):

  contiene_cerdo     carne, grasa o derivados de cerdo, o gelatina de origen no declarado (la gelatina sin origen
                     puede ser porcina: si la lista no dice "bovina", "de pescado" o "vegetal", no se sabe)
  contiene_carne     carnes rojas, aves y sus derivados (grasa bovina, caldo de carne o de pollo, jamón); el
                     pescado no cuenta
  contiene_gelatina  gelatina o colágeno de cualquier origen
  contiene_alcohol   bebidas alcohólicas o alcohol en los ingredientes (vino, licor, ron, coñac, alcohol etílico);
                     el vinagre no cuenta (la fermentación ya lo transformó)
  contiene_vino      derivados de la uva que para kosher necesitan certificación: vino, vinagre de vino, mosto,
                     jugo de uva, coñac, jerez
  contiene_carmin    colorante carmín o cochinilla (INS 120), que sale de un insecto
  rotulo_kosher      si / no: el nombre, la marca, la descripción o el rótulo dicen KOSHER, KASHER o PARVE
  rotulo_halal       si / no: dicen HALAL

Reglas, en el mismo orden que composicion.py (el texto de ingredientes manda sobre la suposición del alimento):

  1. "si" si el alimento genérico lo es (una bondiola, un salame, una cerveza), si el nombre lo dice (sin contar
     "sabor jamón": eso lo decide la lista de ingredientes) o si la lista de ingredientes lo trae (sin contar las
     trazas ni los aromatizantes sintéticos o "idénticos al natural": no salen del animal).
  2. "no" si hay lista de ingredientes y no lo trae, si el alimento no es procesado (NOVA 1 o 2) o es un pescado, o
     si ya se sabe vegetariano (lo vegetariano no tiene carne, cerdo ni gelatina). Para el alcohol, el vino y el
     carmín, un procesado sin lista también es "no", salvo en los alimentos que los traen seguido
     (POSIBLE_PCT_MINIMO).
  3. "desconocido" en el resto: un procesado sin lista que podría tenerlo.

Se puede aplicar sobre un dim_producto ya armado (lo hace canasta/oferta.py si el parquet no trae las columnas):
usa nombre, marca, descripción, ingredientes, alimento_id, nova, apto_vegetariano y alcohol_g.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from sepa.producto.composicion import TRAZAS_RE, _norm

COLUMNAS = ["contiene_cerdo", "contiene_carne", "contiene_gelatina", "contiene_alcohol", "contiene_vino",
            "contiene_carmin", "rotulo_kosher", "rotulo_halal"]

# Alimentos genéricos de cerdo o con cerdo casi siempre. Los fiambres y embutidos (salame, mortadela, salchichas,
# chorizo, morcilla, paté) se cuentan todos: aunque hay de pollo o vacunos, el rótulo casi nunca dice de qué animal
# son la grasa o la tripa.
ALIMENTOS_CERDO = {"bondiola", "carre_cerdo", "pechito_cerdo", "panceta", "jamon_cocido", "jamon_crudo", "salame",
                   "mortadela", "chorizo", "morcilla", "salchichas", "pate", "grasa"}
# Carnes rojas, aves, achuras y fiambres (además de los de cerdo). Los pescados, mariscos y huevos no son carne acá.
ALIMENTOS_CARNE = ALIMENTOS_CERDO | {
    "asado", "bife", "carne_picada", "carne_picada_especial", "cordero", "hamburguesa", "higado_vacuno",
    "higado_pollo", "lengua", "lomo", "milanesa_carne", "mollejas", "mondongo", "nalga", "nuggets_pollo", "osobuco",
    "pavo", "pollo_entero", "pollo_pata_muslo", "pollo_pechuga", "rinon", "tapa_asado", "vacio", "empanadas",
}
# Pescados y mariscos: no son carne ni cerdo aunque sean procesados sin lista (atún en lata, medallones rebozados).
ALIMENTOS_PESCADO = {"atun_lata", "caballa_lata", "sardinas_lata", "merluza", "milanesa_pescado", "salmon", "trucha",
                     "surimi", "calamar", "langostinos"}
ALIMENTOS_ALCOHOL = {"cerveza", "cerveza_sin_alcohol", "vino", "vino_espumante", "destilados", "fernet_aperitivos"}
ALIMENTOS_VINO = {"vino", "vino_espumante"}
# Un procesado sin lista de ingredientes puede traer alcohol, vino o carmín si su alimento genérico los trae seguido
# sin que el nombre lo avise ("queso al whisky" lo avisa): al menos en este porcentaje de los productos del alimento
# que sí tienen lista (se mide en cada corrida; en dim_producto del 14/11/2026, alcohol en 18 % de los budines y 4 %
# de los alfajores, carmín en 24 % de los yogures y 25 % de los helados, jugo o mosto de uva en 15 % de las
# mermeladas light). Si no llega, un procesado sin lista es "no".
POSIBLE_PCT_MINIMO = 3.0

# Aromatizantes sintéticos o "idénticos al natural" (Código Alimentario Argentino, art. 1.223): no salen del animal,
# aunque digan "sabor panceta". Se borran del texto antes de buscar.
_AROMA_SINTETICO = re.compile(r"\b(AROMATIZANTES?|SABORIZANTES?|AROMAS?|ESENCIAS?)\b[^,;()]{0,40}?"
                              r"\b(IDENTICOS? AL NATURAL|ARTIFICIAL(ES)?|SINTETICOS?)\b[^,;()]{0,30}")
_SABOR = re.compile(r"\b(SABOR|GUSTO)( A| DE)? [A-Z]+( [A-Z]+)?")
CERDO = (r"CERDO|PORCIN|\bLECHON|\bCHANCHO|BONDIOL|PANCETA|\bBACON|\bTOCINO|\bLARDO|"
         r"\bJAMON(?! (COCIDO )?DE (PAVO|POLLO))|\bSALAME|\bSALAMIN|MORTADELA|\bLONGANIZA|SOPRESAT|\bCOPPA\b|"
         r"PROSCIUTTO|(?<!BIFE DE )(?<!BIFE )\bCHORIZO")
GELATINA = r"GELATINA|GRENETINA|COLAGENO"
# Gelatina de origen declarado que no es porcino.
GELATINA_NO_PORCINA = (r"(GELATINA|GRENETINA|COLAGENO)( HIDROLIZAD[OA])?( (DE ORIGEN|DE))? ?"
                       r"(VACUN|BOVIN|DE PESCADO|VEGETAL|HALAL|KOSHER)")
CARNE = (CERDO + r"|\bCARNES?\b(?! (DE SOJA|VEGETAL))|\bVACUN|\bBOVIN|\bPOLLO|\bPAVO|\bCORDERO|\bCIERVO|\bCONEJO|"
         r"\bCABRITO|\bCHIVITO|CALDO DE (CARNE|POLLO|GALLINA|VACA)|GRASA ANIMAL|\bSEBO\b|\bHIGADO|\bSANGRE\b")
# La leche vacuna, el cuajo y la gelatina no son carne (la gelatina se mira aparte; el cuajo de los quesos es un
# límite: ver canasta/config.py).
_NO_CARNE = re.compile(r"LECHE( [A-Z]+){0,3} (VACUNA|BOVINA|DE VACA)|CUAJO( [A-Z]+){0,2}|"
                       r"(GELATINA|GRENETINA|COLAGENO)( HIDROLIZAD[OA])?( (DE ORIGEN|DE))? ?(VACUN|BOVIN)\w*")
# Los productos que dicen "sin alcohol" o traen polialcoholes (edulcorantes) no tienen alcohol etílico.
_NO_ALCOHOL = re.compile(r"VINAGRES?( DE)?( (ALCOHOL|VINO|MANZANA|ARROZ|MALTA|UVA|MODENA))?( (TINTO|BLANCO))?|"
                         r"SIN ALCOHOL|ALCOHOL(ES)? DE AZUCAR|POLIALCOHOL\w*|ALCOHOL CETILICO|LICOR DE CACAO")
ALCOHOL = (r"\bALCOHOL\b|ETANOL|\bVINOS?\b|\bLICOR|\bRON\b|COGNAC|CONAC|BRANDY|WHISK|CERVEZA|\bOPORTO\b|\bJEREZ\b|"
           r"MARSALA|AGUARDIENTE|\bSIDRA\b|GRAPPA|VODKA|AMARETTO|CHAMPAGNE|CHAMPANA|KIRSCH|\bGIN\b|TEQUILA|"
           r"\bMOSCATO\b|CACHACA|\bPISCO\b")
VINO = (r"\bVINOS?\b|VINAGRE (DE )?VINO|\bMOSTO\b|(JUGO|ZUMO)( CONCENTRADO)? DE UVAS?|COGNAC|CONAC|BRANDY|\bJEREZ\b|"
        r"\bOPORTO\b|MARSALA|GRAPPA|CHAMPAGNE|CHAMPANA|\bESPUMANTE|\bPISCO\b|ACETO BALSAMICO")
CARMIN = r"CARMIN|COCHINILLA|\bINS ?120\b|\bE ?120\b"
KOSHER = r"\bKOSHER\b|\bKASHER\b|\bPARVE\b|\bPAREVE\b"
HALAL = r"\bHALAL\b"
# Contenido de alcohol desde el que el producto lo tiene, g cada 100 g (las bebidas "sin alcohol" llegan a 0,5 %).
ALCOHOL_G_MINIMO = 0.5


def _principal(texto: str) -> str:
    """Los ingredientes sin las trazas (lo que va después de "puede contener") ni los aromatizantes sintéticos."""
    m = re.search(TRAZAS_RE, texto)
    principal = texto[:m.start()] if m else texto
    return _AROMA_SINTETICO.sub(" ", principal)


def _estado(si: pd.Series, no: pd.Series) -> pd.Series:
    return pd.Series(np.select([si.to_numpy(), no.to_numpy()], ["si", "no"], "desconocido"), index=si.index)


def _posible(oculto: pd.Series, tiene_ing: pd.Series, alimento: pd.Series) -> pd.Series:
    """Si el alimento genérico de cada fila lo trae seguido sin que el nombre lo avise (oculto: lo trae la lista y no
    el nombre), entre los productos con lista (POSIBLE_PCT_MINIMO)."""
    pct = oculto[tiene_ing].groupby(alimento[tiene_ing]).mean() * 100
    return alimento.isin(pct.index[pct >= POSIBLE_PCT_MINIMO])


def derivar(p: pd.DataFrame) -> pd.DataFrame:
    """Las columnas de COLUMNAS para cada fila de p (mismo índice)."""
    desc = p["descripcion_sepa"] if "descripcion_sepa" in p else p.get("descripcion", pd.Series("", index=p.index))
    nombre = (p["nombre"].map(_norm) + " " + desc.map(_norm)).str.strip()
    nombre_sin_sabor = nombre.str.replace(_SABOR, " ", regex=True)
    ing = p["ingredientes"].map(_norm)
    tiene_ing = ing.str.len() >= 15
    principal = ing.map(_principal)
    sin_vinagre = principal.str.replace(_NO_ALCOHOL, " ", regex=True)
    alimento = p["alimento_id"].astype("object")
    procesado = pd.to_numeric(p["nova"], errors="coerce").fillna(4).to_numpy() >= 3
    procesado = pd.Series(procesado, index=p.index)
    vegetariano = p["apto_vegetariano"].eq("si")
    # Sin lista y sin nada que agregarle: lo no procesado y los pescados.
    nadie = ~tiene_ing & (~procesado | alimento.isin(ALIMENTOS_PESCADO))

    def busca(rx: str, texto: pd.Series) -> pd.Series:
        return texto.map(re.compile(rx).search).notna()

    out = pd.DataFrame(index=p.index)
    gel_si = tiene_ing & busca(GELATINA, principal)
    gel_no_porcina = gel_si & busca(GELATINA_NO_PORCINA, principal) & ~busca(r"(GELATINA|COLAGENO)[^,;]{0,20}"
                                                                             r"(PORCIN|DE CERDO)", principal)
    out["contiene_gelatina"] = _estado(gel_si, (tiene_ing & ~gel_si) | vegetariano | nadie)

    cerdo_si = (alimento.isin(ALIMENTOS_CERDO) | busca(CERDO, nombre_sin_sabor)
                | (tiene_ing & busca(CERDO, principal)))
    cerdo_no = ((tiene_ing & ~gel_si) | gel_no_porcina | vegetariano | nadie) & ~cerdo_si
    # Gelatina sin origen declarado: puede ser porcina, no se sabe.
    out["contiene_cerdo"] = _estado(cerdo_si, cerdo_no & ~(gel_si & ~gel_no_porcina))

    sin_leche = principal.str.replace(_NO_CARNE, " ", regex=True)
    carne_si = (alimento.isin(ALIMENTOS_CARNE) | busca(CARNE, nombre_sin_sabor.str.replace(_NO_CARNE, " ", regex=True))
                | (tiene_ing & busca(CARNE, sin_leche)))
    out["contiene_carne"] = _estado(carne_si, (tiene_ing | vegetariano | nadie) & ~carne_si)

    alcohol_g = pd.to_numeric(p["alcohol_g"], errors="coerce").fillna(0) if "alcohol_g" in p else 0
    alc_nombre = alimento.isin(ALIMENTOS_ALCOHOL) | busca(ALCOHOL, nombre.str.replace(_NO_ALCOHOL, " ", regex=True))
    alc_ing = tiene_ing & busca(ALCOHOL, sin_vinagre)
    alc_si = alc_nombre | alc_ing | (alcohol_g >= ALCOHOL_G_MINIMO)
    alc_no = (tiene_ing | ~procesado | ~_posible(alc_ing & ~alc_nombre, tiene_ing, alimento)) & ~alc_si
    out["contiene_alcohol"] = _estado(alc_si, alc_no)

    vino_nombre = alimento.isin(ALIMENTOS_VINO) | busca(VINO, nombre)
    vino_ing = tiene_ing & busca(VINO, principal)
    vino_si = vino_nombre | vino_ing
    out["contiene_vino"] = _estado(vino_si, (tiene_ing | ~procesado
                                             | ~_posible(vino_ing & ~vino_nombre, tiene_ing, alimento)) & ~vino_si)

    carmin_si = tiene_ing & busca(CARMIN, principal)
    out["contiene_carmin"] = _estado(carmin_si,
                                     (tiene_ing | ~procesado | ~_posible(carmin_si, tiene_ing, alimento)) & ~carmin_si)

    marca = p["marca"].map(_norm) if "marca" in p else ""
    rotulo = nombre + " " + marca + " " + ing
    out["rotulo_kosher"] = np.where(busca(KOSHER, rotulo), "si", "no")
    out["rotulo_halal"] = np.where(busca(HALAL, rotulo), "si", "no")
    return out[COLUMNAS]
