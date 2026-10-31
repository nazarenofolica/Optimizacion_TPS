"""
Imputación de macronutrientes por similitud de producto.

Un producto sin rótulo propio (marcas propias de cadenas que no publican su
tabla, como DIA o Carrefour Classic) se parece mucho más a sus pares con rótulo
que al promedio de su alimento genérico: un "yogur bebible frutilla" se parece
a otros yogures bebibles de frutilla, no a la mediana de todos los yogures.

Dentro de cada alimento genérico: descripciones normalizadas sin tamaños ni
siglas de envase, TF-IDF de n-gramas de caracteres (3 a 5) y similitud coseno;
cada producto sin rótulo toma el rótulo más representativo (el más cercano a
la mediana, nutrientes.perfil_central) de hasta K_VECINOS productos con rótulo
con similitud >= UMBRAL: un perfil real, que cierra por Atwater. Un producto
light, diet o sin azúcar solo toma vecinos que también lo son (y al revés): la
mermelada sin azúcar de una marca se parece más que ninguna a la común.

Validación (leave-one-out sobre los productos con rótulo): se oculta el rótulo
de cada uno, se lo predice con sus vecinos y se compara el error con el de
usar el genérico (salida/calidad/validacion_similitud.csv).
"""

from __future__ import annotations

import logging
import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from sepa.producto.nutrientes import perfil_central
from sepa.texto import normalizar

logger = logging.getLogger("sepa.producto.similitud")

K_VECINOS = 5
UMBRAL = 0.5
MIN_CON_ROTULO = 5
IMPUTABLES = ["energia_kcal", "proteinas_g", "carbohidratos_g", "azucares_g", "fibra_g", "grasas_totales_g",
              "grasas_saturadas_g", "grasas_trans_g", "sodio_mg"]
TAMANO_RE = re.compile(r"\b\d+([.,]\d+)?\s*(X\s*)?(KG|KGS|KGM|GR|GRS|GRM|G|ML|CC|CM3|L|LT|LTS|LTR|UN|UNI|U|UDS)?\b"
                       r"|\b(X|PAQ|BSA|BOT|CJA|DOY|POT|EST|SCH|PET|BRK|TTB|LAT|FCO|BLI|FWP|POU|BDE|BOB|CUB)\b")
# "CLIGHT" y la línea "BC" (bajas calorías) son light por la marca; hay descripciones cortadas en "LIGH".
REDUCIDO_RE = re.compile(r"\b(C?LIGHT?|LIVIAN\w*|DIET\w*|ZERO|CERO|SIN AZ(UC\w*)?|S AZ(UC\w*)?|REDUCID\w*|SUGAR FREE|BC)\b"
                         r"|\b0 ?%")


def limpiar(texto: str) -> str:
    return re.sub(r"\s+", " ", TAMANO_RE.sub(" ", normalizar(texto))).strip()


def reducido(textos: pd.Series) -> np.ndarray:
    """Light, diet, sin azúcar o reducido en algo, según la descripción."""
    return np.array([bool(REDUCIDO_RE.search(normalizar(t))) for t in textos])


def _vecinos(objetivos: list[str], referentes: list[str], compatibles: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
    vec.fit(referentes + objetivos)
    sim = (vec.transform(objetivos) @ vec.transform(referentes).T).toarray()
    sim = np.where(compatibles, sim, -1.0)
    orden = np.argsort(-sim, axis=1)[:, :K_VECINOS]
    return orden, np.take_along_axis(sim, orden, axis=1)


def imputar(out: pd.DataFrame, con_rotulo: pd.Series, gen: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    out: nutrientes por producto (descripcion, alimento_id, fuente_nutrientes, IMPUTABLES y, si se conoce,
    _reducido: light / sin azúcar según todas sus descripciones). con_rotulo: los referentes. Devuelve (out con
    las imputaciones, validación leave-one-out por alimento y nutriente).
    """
    out = out.copy()
    if "_reducido" not in out:
        out["_reducido"] = reducido(out["descripcion"])
    out["similar_a"], out["similitud"] = None, np.nan
    validacion = []
    for alimento, g in out.groupby("alimento_id"):
        ref = g[con_rotulo.loc[g.index]]
        obj = g[g["fuente_nutrientes"].str.startswith("generico")]
        # Las bebidas alcohólicas no: sus rótulos casi nunca declaran el alcohol y la energía de un vecino no
        # cierra con el alcohol del genérico.
        if len(ref) < MIN_CON_ROTULO or gen.loc[alimento, "alcohol_g"] > 0:
            continue
        t_ref = [limpiar(d) for d in ref["descripcion"]]
        r_ref = ref["_reducido"].to_numpy(dtype=bool)
        orden, sim = _vecinos(t_ref, t_ref, r_ref[:, None] == r_ref[None, :])
        g_val = gen.loc[alimento, IMPUTABLES].astype(float)
        for i in range(len(ref)):
            idx = [j for j, s in zip(orden[i], sim[i]) if j != i and s >= UMBRAL]
            if idx:
                pred = perfil_central(ref.iloc[idx], IMPUTABLES)
                real = ref.iloc[i][IMPUTABLES]
                validacion.append({"alimento_id": alimento,
                                   **{f"error_similitud_{c}": abs(pred[c] - real[c]) for c in IMPUTABLES},
                                   **{f"error_generico_{c}": abs(g_val[c] - real[c]) for c in IMPUTABLES}})
        if obj.empty:
            continue
        r_obj = obj["_reducido"].to_numpy(dtype=bool)
        orden, sim = _vecinos([limpiar(d) for d in obj["descripcion"]], t_ref, r_obj[:, None] == r_ref[None, :])
        for fila, (o, s) in enumerate(zip(orden, sim)):
            usar = o[s >= UMBRAL]
            if len(usar) == 0:
                continue
            i = obj.index[fila]
            out.loc[i, IMPUTABLES] = perfil_central(ref.iloc[usar], IMPUTABLES).to_numpy(dtype=float)
            out.loc[i, ["fuente_nutrientes", "similar_a", "similitud"]] = [
                "similar", ref.iloc[usar[0]]["descripcion"], float(s[0])]
            out.loc[i, "_azucares_g_heredado"] = False
    logger.info("Imputación por similitud: %d productos", int(out["fuente_nutrientes"].eq("similar").sum()))
    return out, _resumir(pd.DataFrame(validacion))


def _resumir(val: pd.DataFrame) -> pd.DataFrame:
    if val.empty:
        return val
    filas = []
    for c in IMPUTABLES:
        sim, gen = val[f"error_similitud_{c}"], val[f"error_generico_{c}"]
        filas.append({"nutriente": c, "productos": int(sim.notna().sum()), "error_mediano_similitud": sim.median(),
                      "error_mediano_generico": gen.median(),
                      "mejora_pct": (1 - sim.median() / gen.median()) * 100 if gen.median() else np.nan})
    return pd.DataFrame(filas).round(3)
