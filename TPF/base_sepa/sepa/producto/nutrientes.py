"""
Nutrientes de cada producto, cada 100 g de parte comestible, sin vacíos.

Con nutrientes por producto (no solo por alimento genérico) dos marcas del
mismo alimento se distinguen de verdad: un cereal con más fibra o una leche
fortificada aportan distinto que otro del mismo precio. Cada producto toma la
mejor fuente disponible, en este orden de confianza:

  1. carga manual (referencia/nutricion_manual.csv);
  2. rótulo publicado por Jumbo / Disco / Vea (sepa/fuentes/catalogos_web.py);
  3. rótulo leído de la foto del envase (referencia/rotulos_fotos.csv);
  4. rótulo de Open Food Facts;
  5. los productos con rótulo más parecidos del mismo alimento (similitud.py);
  6. el alimento genérico: USDA SR Legacy o, para industrializados con
     suficientes rótulos, el rótulo más representativo (perfil_central).

Cada rótulo pasa controles antes de usarse (si falla alguno se usa la fuente
siguiente): energía entre 0 y 950 kcal y coherente con los macronutrientes
(Atwater: 4 / 4 / 9 / 7 por gramo de alcohol; la fibra a 2 como en la UE o sin
contar como en el Mercosur), kcal y kJ
coherentes, macronutrientes que no suman más de 105 g, saturadas <= grasas,
azúcares <= carbohidratos, valores no negativos, sodio posible (un rótulo con
más sodio que la sal pura tiene las unidades corridas), energía cerca de la del
alimento genérico (atrapa tablas por porción cargadas como por 100 g y
productos mal clasificados) y, en Open Food Facts, que el nombre del producto se
parezca al de SEPA (atrapa EAN mal asignados).

Los rótulos argentinos declaran energía, macronutrientes y sodio; vitaminas y
minerales casi nunca: salen del alimento genérico, salvo que el rótulo declare
un valor verosímil (no más de MAX_RATIO_MICRO veces el genérico o, en alimentos
que en Argentina se fortifican, hasta TOPE_FORTIFICADO). Las fracciones que el
rótulo no detalla (grasas mono y poliinsaturadas, azúcares) se reparten como en
el genérico, escaladas al total del rótulo, para que la fila cierre.

Todos los valores quedan por 100 g: los rótulos de líquidos (por 100 ml) se
dividen por la densidad del alimento.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from sepa import config as cfg
from sepa.fuentes import usda
from sepa.producto.composicion import SIN_TACC
from sepa.texto import nombre_coincide, normalizar

logger = logging.getLogger("sepa.producto.nutrientes")

MACROS = ["energia_kcal", "proteinas_g", "carbohidratos_g", "azucares_g", "fibra_g", "grasas_totales_g",
          "grasas_saturadas_g", "grasas_monoinsaturadas_g", "grasas_poliinsaturadas_g", "grasas_trans_g",
          "colesterol_mg", "sodio_mg"]
MICROS = ["potasio_mg", "calcio_mg", "hierro_mg", "magnesio_mg", "fosforo_mg", "zinc_mg", "cobre_mg", "selenio_ug",
          "vitamina_a_ug", "vitamina_c_mg", "vitamina_d_ug", "vitamina_e_mg", "vitamina_k_ug", "vitamina_b1_mg",
          "vitamina_b2_mg", "vitamina_b3_niacina_mg", "vitamina_b6_mg", "vitamina_b9_folato_ug", "vitamina_b12_ug"]
OTROS = ["agua_g", "alcohol_g"]
NUTRIENTES = MACROS + MICROS + OTROS
PRINCIPALES = ["energia_kcal", "proteinas_g", "carbohidratos_g", "grasas_totales_g"]

MIN_OFF_PREFERIDO = 5   # rótulos verificados para preferirlos a USDA en un genérico industrializado
MIN_OFF_RESPALDO = 3    # rótulos verificados para usarlos cuando no hay USDA
MAX_RATIO_MICRO = 3.0
# Máximo verosímil cada 100 g en un alimento fortificado (leches en polvo, cereales, harinas por ley).
TOPE_FORTIFICADO = {
    "potasio_mg": 2000, "calcio_mg": 1500, "hierro_mg": 20, "magnesio_mg": 400, "fosforo_mg": 1200, "zinc_mg": 15,
    "cobre_mg": 2, "selenio_ug": 100, "vitamina_a_ug": 1500, "vitamina_c_mg": 150, "vitamina_d_ug": 20,
    "vitamina_e_mg": 30, "vitamina_k_ug": 300, "vitamina_b1_mg": 3, "vitamina_b2_mg": 3, "vitamina_b3_niacina_mg": 30,
    "vitamina_b6_mg": 3, "vitamina_b9_folato_ug": 600, "vitamina_b12_ug": 8,
}
# Alimentos que en Argentina se venden fortificados (harina por Ley 25.630 y derivados; leches, yogures,
# cereales, jugos, bebidas vegetales, margarina, cacao): solo en ellos se acepta un micronutriente declarado muy
# por encima del genérico. En el resto (una gaseosa con 16 mg de hierro) es un error de carga.
FORTIFICABLES = {
    "leche_entera", "leche_descremada", "leche_polvo", "leche_polvo_descremada", "leche_chocolatada", "yogur",
    "yogur_descremado", "postre_lacteo", "bebida_vegetal", "cereales_desayuno", "avena", "barritas_cereal",
    "harina", "harina_integral", "premezcla", "pan_frances", "pan_lactal", "pan_lactal_integral", "pan_hamburguesa",
    "galletitas_agua", "galletitas_dulces", "galletitas_rellenas", "fideos", "fideos_integrales", "jugo",
    "jugo_polvo", "cacao_bebida", "margarina", "budin_torta", "isotonica", "agua_saborizada", "leche_infantil",
    "leche_infantil_liquida",
}
# Validación cruzada clasificación-rótulo: un producto cuyo rótulo no se parece al de su alimento genérico
# probablemente esté mal clasificado ("AMARGO SERRANO", una gaseosa, como jamón crudo).
PROTEINA_MIN_RATIO = 0.35
PROTEINA_GENERICO_ALTA = 8.0
PROTEINA_GENERICO_BAJA = 2.0
PROTEINA_ROTULO_ALTA = 10.0
# Los medallones de verduras casi no tienen proteínas; los de soja, sí: la proteína no delata nada.
PROTEINA_VARIABLE = {"milanesa_soja"}
# Una porción ínfima (un rocío vegetal de 0,25 g, un sobre de 1,6 g) se declara en 0 kcal: un rótulo de <= 4 kcal
# en un alimento de >= 100 kcal es ese redondeo, no un producto mal clasificado.
REDONDEO_CERO_KCAL = 4.0
GENERICO_DENSO_KCAL = 100.0
# Genéricos demasiado heterogéneos para usarlos de referencia (un aderezo de 360 kcal y una salsa inglesa de
# 33 son "salsas varias"; el helado de agua y el de crema, el atún al natural y en aceite): sus productos usan
# su rótulo pero no se validan contra el genérico.
EXENTOS_VALIDACION = {"salsas_varias", "barritas_cereal", "especias", "sopa_caldo", "edulcorante", "te", "cafe",
                      "helado", "atun_lata"}
# Polvos e infusiones para preparar: el rótulo puede declarar la bebida o el postre preparado, o la porción de
# polvo (1,6 g) redondeada a 0 kcal, en vez de los 100 g que se venden. Ese rótulo se descarta (queda el genérico)
# sin que delate una clasificación dudosa, y de los sellos solo se aproximan los que no dependen de la dilución.
PARA_PREPARAR = {"jugo_polvo", "gelatina", "gelatina_light", "cacao_bebida", "leche_polvo", "leche_polvo_descremada",
                 "yerba"}


# ============================================================
# CONTROLES DE UN RÓTULO
# ============================================================

def _col(df: pd.DataFrame, nombre: str) -> pd.Series:
    return df[nombre].astype(float) if nombre in df else pd.Series(np.nan, index=df.index)


def controlar_rotulo(r: pd.DataFrame, energia_generico: pd.Series, exento: pd.Series,
                     alcohol_generico: pd.Series | None = None) -> pd.Series:
    """
    Controles de consistencia de una tabla nutricional (por 100 g o 100 ml). r: columnas de MACROS (pueden
    faltar), energia_kj y alcohol_pct_vol opcionales; si el rótulo no declara el alcohol (la web no lo hace)
    se usa el del genérico para cerrar la energía de vinos y cervezas. Devuelve el motivo de rechazo ('' si pasa).
    """
    motivo = pd.Series("", index=r.index)

    def marcar(mascara: pd.Series, texto: str) -> None:
        nonlocal motivo
        motivo = motivo.mask(mascara.fillna(False).astype(bool) & motivo.eq(""), texto)

    kcal, prot, carb, grasa = (_col(r, c) for c in PRINCIPALES)
    fibra, alcohol = _col(r, "fibra_g").fillna(0), _col(r, "alcohol_pct_vol") * 0.789
    defecto = alcohol_generico if alcohol_generico is not None else pd.Series(0.0, index=r.index)
    alcohol = alcohol.fillna(defecto).fillna(0)
    marcar(kcal.isna() | prot.isna() | grasa.isna(), "incompleta")
    sin_macros = (prot.fillna(0) + grasa.fillna(0) + carb.fillna(0)) <= 0.5
    marcar((kcal < 0) | (kcal > cfg.MAX_KCAL_100) | ((kcal == 0) & ~sin_macros), "energia_imposible")
    marcar((r.reindex(columns=MACROS).astype(float) < 0).any(axis=1), "valor_negativo")
    kj = _col(r, "energia_kj")
    marcar(kj.notna() & ((kcal * 4.184 - kj).abs() > np.maximum(30, 0.15 * kj)), "kj_kcal_inconsistentes")
    marcar(_col(r, "grasas_saturadas_g") > grasa + 0.5, "saturadas_mayor_grasas")
    marcar(_col(r, "azucares_g") > carb + 0.5, "azucares_mayor_carbohidratos")
    # La fibra suma 2 kcal/g en la UE (y en Open Food Facts); el rótulo del Mercosur no la cuenta: vale cualquiera.
    atwater = 4 * carb + 4 * prot + 9 * grasa + 7 * alcohol
    dif = np.minimum((kcal - atwater).abs(), (kcal - atwater - 2 * fibra).abs())
    marcar(carb.notna() & (dif > cfg.TOLERANCIA_ENERGIA_ABS) & (dif > cfg.TOLERANCIA_ENERGIA_REL * kcal.clip(lower=1)),
           "energia_inconsistente")
    # Sin carbohidratos declarados (pasa en la web): los que cierran la energía no pueden ser negativos.
    derivados = (kcal - 4 * prot - 9 * grasa - 2 * fibra - 7 * alcohol) / 4
    marcar(carb.isna() & (derivados < -2), "energia_inconsistente")
    marcar((prot.fillna(0) + carb.fillna(derivados.clip(lower=0)) + grasa.fillna(0) + fibra
            + _col(r, "sodio_mg").fillna(0) * 2.5 / 1000) > cfg.MAX_GRAMOS_100, "suma_macros_mayor_100g")
    # 0 kcal no es la composición de algo cuyo genérico es denso (un condimento, un caldo): es la porción de
    # 1 g redondeada. Vale también para los exentos.
    marcar((kcal <= REDONDEO_CERO_KCAL) & (energia_generico >= GENERICO_DENSO_KCAL), "energia_redondeada_a_cero")
    ratio = kcal / energia_generico.where(energia_generico > 0)
    lejos = ((ratio > cfg.RATIO_ENERGIA_GENERICO) | (ratio < 1 / cfg.RATIO_ENERGIA_GENERICO)) & \
            ((kcal - energia_generico).abs() > cfg.TOLERANCIA_ENERGIA_GENERICO_ABS)
    marcar(lejos & ~exento, "energia_lejos_del_generico")
    return motivo


def sodio_verosimil(sodio: pd.Series, sodio_generico: pd.Series) -> pd.Series:
    """
    Un sodio imposible (más que la sal pura) es un error de unidades si dividido por 1.000 queda en un valor
    verosímil para el alimento (µg cargados como mg); si no, se usa el del genérico.
    """
    s = sodio.astype(float).copy()
    g = sodio_generico.astype(float).fillna(0)
    malo = s > cfg.SODIO_MAXIMO_MG
    dividido = s / 1000
    unidades = malo & (dividido <= np.maximum(5 * g, 2000))
    s[unidades] = dividido[unidades]
    s[malo & ~unidades] = g[malo & ~unidades]
    return s


COLESTEROL_MAXIMO_MG = 2000.0   # la yema de huevo tiene ~1.100 mg cada 100 g; los sesos, ~3.000


def colesterol_verosimil(colesterol: pd.Series, generico: pd.Series) -> pd.Series:
    """Colesterol de un rótulo: hasta 3 veces el del genérico (o 300 mg) y nunca más que COLESTEROL_MAXIMO_MG."""
    c = colesterol.astype(float)
    tope = np.minimum(np.maximum(3 * generico.astype(float).fillna(0), 300.0), COLESTEROL_MAXIMO_MG)
    return c.where(c.isna() | (c <= tope), generico.astype(float))


def micros_verosimiles(valores: pd.DataFrame, generico: pd.DataFrame, alimento_id: pd.Series) -> pd.DataFrame:
    """Micronutrientes declarados: se aceptan si son verosímiles para el alimento; si no, los del genérico."""
    v = valores.copy()
    fortificable = alimento_id.isin(FORTIFICABLES).to_numpy()
    for c in MICROS:
        if c not in v:
            continue
        gen = generico[c].to_numpy(dtype=float)
        tope = np.where(fortificable, np.maximum(MAX_RATIO_MICRO * gen, TOPE_FORTIFICADO[c]), MAX_RATIO_MICRO * gen + 1e-9)
        declarado = v[c].to_numpy(dtype=float)
        v[c] = np.where(np.isfinite(declarado) & (declarado > 0) & (declarado <= tope), declarado, np.nan)
    return v


# ============================================================
# OPEN FOOD FACTS: categoría
# ============================================================

def atipico_en_categoria_off(categoria: pd.Series, kcal: pd.Series) -> pd.Series:
    """Energía muy lejos de la mediana de su categoría de Open Food Facts (tabla por porción como por 100 g)."""
    cat = categoria.where(kcal.notna())
    n = cat.map(cat.value_counts())
    mediana = kcal.groupby(cat).transform("median")
    ratio = kcal / mediana.where(mediana > 0)
    return ((n >= cfg.MIN_POR_CATEGORIA_OFF) & ((kcal - mediana).abs() > cfg.TOLERANCIA_CATEGORIA_OFF_ABS)
            & ((ratio > cfg.RATIO_CATEGORIA_OFF) | (ratio < 1 / cfg.RATIO_CATEGORIA_OFF))).fillna(False)


# ============================================================
# ALIMENTO GENÉRICO
# ============================================================

def perfil_central(tabla: pd.DataFrame, columnas: list[str]) -> pd.Series:
    """
    La fila más cercana a la mediana de sus pares en energía y macronutrientes principales (cada uno en la escala
    de su dispersión). Es un rótulo real, que cierra por Atwater y respeta azúcares <= carbohidratos; las medianas
    sueltas de cada columna pueden salir de productos distintos (un caldo en cubos y uno en polvo) y no cerrar.
    Se prefieren las filas que declaran los principales; lo que la elegida no declara sale de la mediana del resto.
    """
    x = tabla[[c for c in PRINCIPALES if c in columnas]].astype(float)
    mediana = x.median()
    escala = (x - mediana).abs().median().clip(lower=1.0)
    completas = x.notna().all(axis=1)
    candidatas = x[completas] if completas.any() else x
    distancia = ((candidatas - mediana).abs() / escala).fillna(np.inf).sum(axis=1)
    return tabla.loc[distancia.idxmin(), columnas].astype(float).fillna(tabla[columnas].astype(float).median())


def genericos(catalogo: pd.DataFrame, rotulos_ok: pd.DataFrame) -> pd.DataFrame:
    """
    Nutrientes de cada alimento genérico (por 100 g comestibles) y su fuente.
    rotulos_ok: alimento_id + MACROS por 100 g de los productos con rótulo verificado.
    """
    fdc = catalogo["fdc_id"].dropna().astype(int)
    u = usda.nutrientes(fdc.unique().tolist())
    n_rot = rotulos_ok.groupby("alimento_id").size()
    filas = []
    for a in catalogo.itertuples():
        n = int(n_rot.get(a.id, 0))
        fila_usda = u.loc[int(a.fdc_id)] if pd.notna(a.fdc_id) and int(a.fdc_id) in u.index else None
        base = (fila_usda.reindex(NUTRIENTES).astype(float) if fila_usda is not None
                else pd.Series(np.nan, index=NUTRIENTES))
        if n >= MIN_OFF_PREFERIDO and (a.preferir_off or fila_usda is None) or (fila_usda is None and n >= MIN_OFF_RESPALDO):
            # Los macronutrientes salen todos del rótulo más representativo (mezclarlos con los de USDA rompe la
            # suma: una gelatina sin azúcar de USDA tiene 85 g de proteínas). Lo que ningún rótulo declara
            # (vitaminas, minerales, a veces las fracciones de la grasa) sale de USDA, escalado a los totales.
            perfil = perfil_central(rotulos_ok[rotulos_ok["alimento_id"].eq(a.id)], MACROS)
            if fila_usda is not None:
                for total, partes in (("grasas_totales_g", ("grasas_monoinsaturadas_g", "grasas_poliinsaturadas_g",
                                                            "colesterol_mg")),
                                      ("carbohidratos_g", ("azucares_g",))):
                    if pd.notna(perfil[total]) and fila_usda[total] > 0:
                        escala = perfil[total] / float(fila_usda[total])
                        for c in partes:
                            if pd.isna(perfil[c]):
                                perfil[c] = float(fila_usda[c]) * (min(escala, 3.0) if c == "colesterol_mg" else escala)
            base[MACROS] = perfil.where(perfil.notna(), base[MACROS])
            fuente = f"rótulo más representativo de {n} verificados" + (f"; resto USDA SR Legacy {int(a.fdc_id)}"
                                                                         if fila_usda is not None else "")
            calidad = "generico_rotulos"
        elif fila_usda is not None:
            fuente, calidad = f"USDA SR Legacy {int(a.fdc_id)}: {fila_usda['usda_descripcion']}", "generico_usda"
        else:
            fuente, calidad = "", "sin_datos"
        fila = base.fillna(0.0)
        fila["fuente_generico"], fila["calidad_generico"] = fuente, calidad
        fila.name = a.id
        filas.append(fila)
    gen = pd.DataFrame(filas)
    gen.index.name = "alimento_id"
    return gen


# ============================================================
# ARMADO POR PRODUCTO
# ============================================================

def _por_100g(df: pd.DataFrame, es_ml: np.ndarray, densidad: np.ndarray, columnas: list[str]) -> pd.DataFrame:
    """
    Valores por 100 ml -> por 100 g (en los productos líquidos). Una tabla "por 100 ml" que convertida pasa de
    MAX_GRAMOS_100 de sólidos ya estaba por 100 g: pasa con los aceites, que declaran 100 g de grasa "cada 100 ml".
    """
    out = df.copy()
    solidos = sum(out[c].astype(float).fillna(0) for c in ("proteinas_g", "carbohidratos_g", "grasas_totales_g",
                                                           "fibra_g") if c in out)
    convertir = es_ml & ~np.asarray(solidos / densidad > cfg.MAX_GRAMOS_100, dtype=bool)
    for c in columnas:
        if c in out:
            out[c] = np.where(convertir, out[c].astype(float) / densidad, out[c].astype(float))
    return out


def _carbohidratos_por_diferencia(tabla: pd.DataFrame, alcohol: pd.Series) -> pd.DataFrame:
    """Un rótulo sin carbohidratos (pasa en la web y en Open Food Facts): los que cierran la energía."""
    t = tabla.copy()
    derivados = ((t["energia_kcal"] - 4 * t["proteinas_g"] - 9 * t["grasas_totales_g"]
                  - 2 * _col(t, "fibra_g").fillna(0) - 7 * alcohol.fillna(0)) / 4).clip(lower=0)
    t["carbohidratos_g"] = _col(t, "carbohidratos_g").where(_col(t, "carbohidratos_g").notna(), derivados)
    return t


def _aplicar(out: pd.DataFrame, idx: pd.Index, valores: pd.DataFrame, columnas: list[str], fuente: str) -> None:
    """Pisa con los valores declarados (no vacíos) de una fuente de rótulo."""
    for c in columnas:
        if c in valores:
            v = valores.loc[idx, c].astype(float)
            out.loc[idx, c] = v.where(v.notna(), out.loc[idx, c])
    out.loc[idx, "fuente_nutrientes"] = fuente


def _cerrar(out: pd.DataFrame, gen: pd.DataFrame) -> pd.DataFrame:
    """
    Fracciones que el rótulo no detalla: se reparten como en el genérico, escaladas al total del rótulo, para
    que la fila cierre (saturadas + mono + poli <= grasas; azúcares <= carbohidratos; agua <= lo que queda).
    """
    g = gen.reindex(out["alimento_id"])
    g.index = out.index
    escala_grasa = (out["grasas_totales_g"] / g["grasas_totales_g"].where(g["grasas_totales_g"] > 0)).fillna(0)
    for c in ("grasas_monoinsaturadas_g", "grasas_poliinsaturadas_g", "colesterol_mg"):
        heredado = out[f"_{c}_heredado"]
        # El colesterol acompaña a la grasa animal, pero no se multiplica más de 3 veces.
        escala = escala_grasa.clip(upper=3.0) if c == "colesterol_mg" else escala_grasa
        out.loc[heredado, c] = (g.loc[heredado, c] * escala[heredado]).round(4)
    # Las insaturadas ocupan lo que dejan saturadas y trans (un aceite de coco con 85 g de saturadas no puede
    # heredar las insaturadas del de girasol).
    grasas = out["grasas_totales_g"]
    out["grasas_saturadas_g"] = np.minimum(out["grasas_saturadas_g"], grasas)
    out["grasas_trans_g"] = np.minimum(out["grasas_trans_g"], grasas - out["grasas_saturadas_g"])
    libre = (grasas - out["grasas_saturadas_g"] - out["grasas_trans_g"]).clip(lower=0)
    insaturadas = out["grasas_monoinsaturadas_g"] + out["grasas_poliinsaturadas_g"]
    escala = (libre / insaturadas).where(insaturadas > libre, 1.0).fillna(1.0)
    for c in ("grasas_monoinsaturadas_g", "grasas_poliinsaturadas_g"):
        out[c] = out[c] * escala
    heredado = out["_azucares_g_heredado"]
    escala_carb = (out["carbohidratos_g"] / g["carbohidratos_g"].where(g["carbohidratos_g"] > 0)).fillna(0)
    out.loc[heredado, "azucares_g"] = g.loc[heredado, "azucares_g"] * escala_carb[heredado]
    out["azucares_g"] = np.minimum(out["azucares_g"], out["carbohidratos_g"])
    secos = (out["proteinas_g"] + out["carbohidratos_g"] + out["grasas_totales_g"] + out["fibra_g"]
             + out["alcohol_g"] + out["sodio_mg"] * 2.5 / 1000)
    out["agua_g"] = np.minimum(out["agua_g"], (100 - secos).clip(lower=0))
    return out.drop(columns=[c for c in out.columns if c.endswith("_heredado")])


def armar(productos: pd.DataFrame, catalogo: pd.DataFrame, off: pd.DataFrame, web: pd.DataFrame,
          fotos: pd.DataFrame, manual: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    productos: producto, clave_producto, alimento_id, descripcion, descripciones_alternativas, marca,
    unidad_contenido. Devuelve (nutrientes por producto, nutrientes por alimento genérico, estadísticas).
    """
    from sepa.producto import similitud

    cat = catalogo.set_index("id")
    p = productos[["producto", "clave_producto", "alimento_id", "descripcion", "descripciones_alternativas", "marca",
                   "unidad_contenido"]].copy().reset_index(drop=True)
    es_ml = p["unidad_contenido"].eq("ml").to_numpy()
    densidad = p["alimento_id"].map(cat["densidad_g_ml"]).fillna(1.0).to_numpy()
    stats: dict = {}

    # --- Open Food Facts: controles sobre la tabla tal cual (por 100 g o 100 ml)
    o = p[["clave_producto"]].merge(off, left_on="clave_producto", right_on="ean", how="left")
    o.index = p.index
    tiene_off = o[[c for c in MACROS if c in o]].notna().any(axis=1)
    calculada = o["energia_kcal"].isna() & o["energia_kj"].notna()
    o.loc[calculada, "energia_kcal"] = (o.loc[calculada, "energia_kj"] / 4.184).round(1)
    sepa_txt = p["descripcion"].fillna("") + " " + p["descripciones_alternativas"].fillna("") + " " + p["marca"].fillna("")
    off_txt = o["off_nombre"].fillna("") + " " + o["off_marcas"].fillna("")
    nombre_ok = pd.Series([nombre_coincide(s, t) for s, t in zip(sepa_txt, off_txt)], index=p.index)

    # Primera pasada sin el control contra el genérico (todavía no existe): rótulos para armar las medianas.
    sin_gen = pd.Series(np.nan, index=p.index)
    exento = p["alimento_id"].isin(EXENTOS_VALIDACION)
    errores_off = o["off_errores_calidad"].fillna("").str.contains("nutrition", case=False)
    atipico = atipico_en_categoria_off(o["off_categoria_principal"], o["energia_kcal"])

    def motivo_off(tabla: pd.DataFrame, energia_generico: pd.Series, alcohol: pd.Series | None = None) -> pd.Series:
        m = controlar_rotulo(tabla, energia_generico, exento, alcohol)
        return (m.mask(m.eq("") & errores_off, "off_marca_error")
                .mask(m.eq("") & atipico, "energia_atipica_en_categoria_off")
                .mask(m.eq("") & ~nombre_ok, "nombre_no_coincide")
                .where(tiene_off, "sin_datos"))

    ok_off = motivo_off(o, sin_gen).eq("")
    off100 = _por_100g(o, es_ml, densidad, MACROS + MICROS)
    rotulos_ok = off100.loc[ok_off, MACROS]
    if len(web):
        # Los rótulos web que pasan sus controles propios también cuentan (uno por producto: el web, si hay).
        w = p[["clave_producto"]].merge(web[web["tiene_tabla"]], left_on="clave_producto", right_on="ean", how="left")
        w.index = p.index
        unidades_ok = w["unidades_ok"].astype("boolean").fillna(True).astype(bool)
        es_ml_web = w["unidad_base"].fillna("").str.lower().str.startswith("ml").to_numpy()
        w100 = _por_100g(w, es_ml_web, densidad, MACROS)
        ok_web = w["energia_kcal"].notna() & unidades_ok & controlar_rotulo(w100, sin_gen, exento).eq("")
        rotulos_ok = pd.concat([off100.loc[ok_off & ~ok_web, MACROS], w100.loc[ok_web, MACROS]])
    gen = genericos(catalogo, rotulos_ok.assign(alimento_id=p.loc[rotulos_ok.index, "alimento_id"]))
    g = gen.reindex(p["alimento_id"])
    g.index = p.index
    e_gen = g["energia_kcal"].astype(float)
    alcohol_gen = g["alcohol_g"].astype(float)

    def completar_ceros(tabla: pd.DataFrame) -> pd.DataFrame:
        """Bebidas y golosinas suelen omitir proteínas y grasas: valen 0 si el genérico casi no tiene (< 1 g)."""
        t = tabla.copy()
        con_energia = t["energia_kcal"].notna()
        for c in ("proteinas_g", "grasas_totales_g"):
            if c in t:
                t[c] = t[c].astype(float).where(t[c].notna() | ~con_energia | ~(g[c].astype(float) < 1.0), 0.0)
        return t

    # --- base: el genérico
    out = p[["producto", "clave_producto", "alimento_id", "descripcion"]].copy()
    for c in NUTRIENTES:
        out[c] = g[c].astype(float)
    out["fuente_nutrientes"] = "generico: " + g["calidad_generico"].str.replace("generico_", "", regex=False)
    for c in ("azucares_g", "grasas_monoinsaturadas_g", "grasas_poliinsaturadas_g", "colesterol_mg"):
        out[f"_{c}_heredado"] = True
    # Energía y proteínas del rótulo que pasa sus controles propios (aunque esté lejos del genérico): sirven para
    # detectar productos mal clasificados.
    out["energia_rotulo"], out["proteinas_rotulo"] = np.nan, np.nan

    def registrar_rotulo(valores: pd.DataFrame, mascara: pd.Series) -> None:
        out.loc[mascara, "energia_rotulo"] = valores.loc[mascara, "energia_kcal"].astype(float)
        out.loc[mascara, "proteinas_rotulo"] = valores.loc[mascara, "proteinas_g"].astype(float)

    def usar_rotulo(valores: pd.DataFrame, idx: pd.Index, fuente: str, micros: bool) -> None:
        _aplicar(out, idx, valores, MACROS, fuente)
        for c in ("azucares_g", "grasas_monoinsaturadas_g", "grasas_poliinsaturadas_g", "colesterol_mg"):
            if c in valores:
                out.loc[idx, f"_{c}_heredado"] &= valores.loc[idx, c].isna()
        if micros:
            m = micros_verosimiles(valores.loc[idx], g.loc[idx], p.loc[idx, "alimento_id"])
            _aplicar(out, idx, m, MICROS, fuente)

    # --- 4) Open Food Facts (ahora sí, controlado también contra el genérico)
    o = completar_ceros(o)
    off100 = _por_100g(o, es_ml, densidad, MACROS + MICROS)
    off100["sodio_mg"] = sodio_verosimil(off100["sodio_mg"], g["sodio_mg"])
    off100["colesterol_mg"] = colesterol_verosimil(off100["colesterol_mg"], g["colesterol_mg"])
    off100["alcohol_g"] = o["alcohol_pct_vol"].astype(float) * 0.789 / densidad
    registrar_rotulo(off100, motivo_off(o, sin_gen, alcohol_gen).eq(""))
    motivo = motivo_off(o, e_gen, alcohol_gen)
    idx = p.index[motivo.eq("")]
    off100 = _carbohidratos_por_diferencia(off100, off100["alcohol_g"].fillna(alcohol_gen))
    usar_rotulo(off100, idx, "rotulo_off", micros=True)
    _aplicar(out, idx, off100, ["alcohol_g"], "rotulo_off")
    stats["off"] = {"con_tabla": int(tiene_off.sum()), "aceptados": len(idx),
                    "rechazos": motivo[tiene_off & motivo.ne("")].value_counts().to_dict()}

    # --- 3) rótulo leído de la foto del envase
    if len(fotos):
        f = p[["clave_producto"]].join(fotos, on="clave_producto")
        f.index = p.index
        con = f["energia_kcal"].notna()
        es_ml_foto = f["es_ml"].astype("boolean").fillna(pd.Series(es_ml, index=p.index)).astype(bool).to_numpy()
        f100 = completar_ceros(_por_100g(f, es_ml_foto, densidad, MACROS + MICROS))
        registrar_rotulo(f100, con & controlar_rotulo(f100, sin_gen, exento, alcohol_gen).eq(""))
        motivo = controlar_rotulo(f100, e_gen, exento, alcohol_gen).where(con, "sin_datos")
        idx = p.index[motivo.eq("")]
        usar_rotulo(_carbohidratos_por_diferencia(f100, alcohol_gen), idx, "rotulo_foto", micros=True)
        stats["fotos"] = {"con_tabla": int(con.sum()), "aceptados": len(idx),
                          "rechazos": motivo[con & motivo.ne("")].value_counts().to_dict()}

    # --- 2) rótulo web (Jumbo / Disco / Vea)
    if len(web):
        con = w["energia_kcal"].notna()
        w100 = completar_ceros(_por_100g(w, es_ml_web, densidad, MACROS))
        w100["sodio_mg"] = sodio_verosimil(w100["sodio_mg"], g["sodio_mg"])
        w100["colesterol_mg"] = colesterol_verosimil(w100["colesterol_mg"], g["colesterol_mg"])
        registrar_rotulo(w100, con & unidades_ok & controlar_rotulo(w100, sin_gen, exento, alcohol_gen).eq(""))
        motivo = controlar_rotulo(w100, e_gen, exento, alcohol_gen)
        motivo = motivo.mask(motivo.eq("") & ~unidades_ok, "unidades").where(con, "sin_datos")
        w100 = _carbohidratos_por_diferencia(w100, alcohol_gen)
        idx = p.index[motivo.eq("")]
        previa = out.loc[idx, "fuente_nutrientes"]
        usar_rotulo(w100, idx, "rotulo_web", micros=False)
        out.loc[idx, "fuente_nutrientes"] = np.where(previa.eq("rotulo_off"), "rotulo_web+off", "rotulo_web")
        stats["web"] = {"con_tabla": int(con.sum()), "aceptados": len(idx),
                        "rechazos": motivo[con & motivo.ne("")].value_counts().to_dict()}

    # --- validación cruzada clasificación-rótulo (antes de imputar)
    p_gen = g["proteinas_g"].astype(float).fillna(0)
    ratio = out["energia_rotulo"] / e_gen.where(e_gen > 0)
    energia_lejos = ((ratio > cfg.RATIO_ENERGIA_GENERICO) | (ratio < 1 / cfg.RATIO_ENERGIA_GENERICO)) & \
                    ((out["energia_rotulo"] - e_gen).abs() > cfg.TOLERANCIA_ENERGIA_GENERICO_ABS)
    # Panes, galletitas y pastas sin TACC se hacen con almidones (mandioca, maíz, arroz): casi sin proteínas.
    sin_tacc = (p["descripcion"].fillna("") + " " + p["descripciones_alternativas"].fillna("")).map(normalizar) \
        .str.contains(SIN_TACC)
    proteina = (((p_gen >= PROTEINA_GENERICO_ALTA) & (out["proteinas_rotulo"] < PROTEINA_MIN_RATIO * p_gen) & ~sin_tacc)
                | ((p_gen < PROTEINA_GENERICO_BAJA) & (out["proteinas_rotulo"] > PROTEINA_ROTULO_ALTA))) \
        & ~p["alimento_id"].isin(PROTEINA_VARIABLE)
    convencion = p["alimento_id"].isin(PARA_PREPARAR) | \
        ((out["energia_rotulo"] <= REDONDEO_CERO_KCAL) & (e_gen >= GENERICO_DENSO_KCAL))
    out["clasificacion_dudosa"] = (((energia_lejos & ~convencion) | proteina) & out["energia_rotulo"].notna()
                                   & ~exento).fillna(False)

    # --- 5) imputación por similitud para los que quedan con el genérico
    referentes = out["fuente_nutrientes"].str.startswith("rotulo") & ~out["clasificacion_dudosa"]
    # light / sin azúcar según todas las descripciones: "JUGO PV NAR VIT" es un Clight para otra cadena
    out["_reducido"] = similitud.reducido(p["descripcion"].fillna("") + " " + p["descripciones_alternativas"].fillna(""))
    out, validacion = similitud.imputar(out, referentes, gen)
    stats["similitud"] = int(out["fuente_nutrientes"].eq("similar").sum())

    # --- 1) carga manual
    if len(manual):
        m = p[["clave_producto"]].join(manual, on="clave_producto")
        m.index = p.index
        idx = p.index[m["fuente"].notna()]
        _aplicar(out, idx, m, [c for c in NUTRIENTES if c in m], "manual")
        stats["manual"] = len(idx)

    out = _cerrar(out, gen)
    for c in NUTRIENTES:
        out[c] = out[c].astype(float).clip(lower=0).round(4)
    stats["fuentes"] = out["fuente_nutrientes"].value_counts().to_dict()
    stats["validacion_similitud"] = validacion
    out["fuente_generico"] = g["fuente_generico"].to_numpy()
    return out, gen, stats


# ============================================================
# ROTULOS DE FOTOS Y CARGA MANUAL
# ============================================================

COLUMNAS_FOTO = ["energia_kcal", "carbohidratos_g", "azucares_g", "proteinas_g", "grasas_totales_g",
                 "grasas_saturadas_g", "grasas_trans_g", "fibra_g", "sodio_mg"]


def leer_rotulos_fotos() -> pd.DataFrame:
    """
    Rótulos transcriptos de las fotos de Open Food Facts (productos sin tabla en la web ni en OFF), solo los
    legibles que corresponden al producto. Por clave_producto: valores por 100 g o 100 ml (es_ml) y los
    micronutrientes declarados. Una tabla por porción se lleva a 100 con el tamaño de la porción.
    """
    ruta = cfg.RUTA_ROTULOS_FOTOS
    if not ruta.exists():
        return pd.DataFrame()
    f = pd.read_csv(ruta, sep=";", dtype=str, encoding="utf-8-sig").fillna("")
    f = f[f["legible"].isin(["si", "parcial"]) & f["coincide"].eq("si") & f["energia_kcal"].ne("")]
    filas = []
    for _, r in f.iterrows():
        cant, unidad = 100.0, ""
        if r["base"] == "porcion":
            num, _, unidad = r["porcion"].strip().partition(" ")
            cant = float(num.replace(",", "."))
        fila = {"clave_producto": r["clave_producto"].strip().zfill(13),
                "es_ml": unidad.lower().startswith("ml") if unidad else None}
        factor = 100.0 / cant
        for c in COLUMNAS_FOTO:
            fila[c] = float(r[c].replace(",", ".")) * factor if r[c] != "" else np.nan
        for item in filter(None, r["otros"].split("|")):
            clave, _, valor = item.partition("=")
            if clave.strip() in MICROS:
                fila[clave.strip()] = float(valor.replace(",", ".")) * factor
        filas.append(fila)
    out = pd.DataFrame(filas, columns=["clave_producto", "es_ml"] + COLUMNAS_FOTO + MICROS)
    return out.drop_duplicates("clave_producto", keep="last").set_index("clave_producto")


def leer_manual() -> pd.DataFrame:
    """referencia/nutricion_manual.csv: clave_producto;fuente;nota;<nutrientes...> (por 100 g)."""
    ruta = cfg.RUTA_NUTRICION_MANUAL
    if not ruta.exists():
        return pd.DataFrame()
    df = pd.read_csv(ruta, sep=";", dtype=str, comment="#", encoding="utf-8-sig").dropna(how="all")
    if df.empty:
        return df
    df["clave_producto"] = df["clave_producto"].str.strip()
    for c in df.columns.difference(["clave_producto", "fuente", "nota"]):
        df[c] = pd.to_numeric(df[c].str.replace(",", ".", regex=False), errors="coerce")
    return df.set_index("clave_producto")


# ============================================================
# SELLOS DE ADVERTENCIA (Ley 27.642, aproximados)
# ============================================================

RUBROS_SIN_SELLOS = {"Frutas", "Verduras", "Carne vacuna", "Cerdo", "Pollo", "Achuras", "Pescados", "Huevos",
                     "Legumbres", "Frutas congeladas", "Verduras congeladas"}
ENERGIA_MINIMA_SELLOS = 10.0   # kcal cada 100 g o 100 ml


def sellos(n: pd.DataFrame, rubro: pd.Series, liquido: pd.Series, densidad: pd.Series, envasado: pd.Series,
           azucar_agregada: pd.Series, para_preparar: pd.Series | None = None) -> pd.DataFrame:
    """
    Sellos de advertencia aproximados con los valores de la etapa final de la ley (perfil OPS): exceso en
    azúcares (>= 10 % de la energía), grasas saturadas (>= 10 %), grasas totales (>= 30 %), sodio (>= 1 mg/kcal
    o >= 300 mg cada 100 g) y calorías (>= 275 kcal cada 100 g; 25 cada 100 ml en bebidas). La ley mira los
    azúcares agregados: se usan los totales salvo en lácteos y frutas, donde solo cuentan si el producto
    declara azúcar agregada. Es una aproximación: no reemplaza el rótulo. En los polvos para preparar
    (para_preparar) la ley mira lo preparado: valen los sellos que son una parte de la energía, que no cambian al
    diluir; los de calorías y sodio dependen de la dilución (y una bebida sin calorías tiene su propio umbral de
    sodio), así que no se aproximan. Lo que casi no aporta energía (un té, una gaseosa sin azúcar) no lleva los
    sellos que son una parte de la energía: con 2 kcal, 0,1 g de azúcar ya sería el 20 %.
    """
    e = n["energia_kcal"].where(n["energia_kcal"] >= ENERGIA_MINIMA_SELLOS)
    azuc = n["azucares_g"].where(~rubro.isin(["Lácteos", "Frutas", "Conservas"]) | azucar_agregada.eq("si"), 0.0)
    kcal_100 = np.where(liquido, n["energia_kcal"] * densidad, n["energia_kcal"])
    s = pd.DataFrame(index=n.index)
    s["exceso_azucares"] = 4 * azuc / e >= 0.10
    s["exceso_grasas_saturadas"] = 9 * n["grasas_saturadas_g"] / e >= 0.10
    s["exceso_grasas_totales"] = 9 * n["grasas_totales_g"] / e >= 0.30
    s["exceso_sodio"] = (n["sodio_mg"] / e >= 1) | (n["sodio_mg"] >= 300)
    s["exceso_calorias"] = np.where(liquido, kcal_100 >= 25, kcal_100 >= 275)
    if para_preparar is not None:
        s.loc[para_preparar.to_numpy(), ["exceso_sodio", "exceso_calorias"]] = False
    aplica = (~rubro.isin(RUBROS_SIN_SELLOS) & envasado).to_numpy()
    s = s.fillna(False).astype(bool) & aplica[:, None]
    s["sellos"] = s.sum(axis=1).astype(int)
    return s
