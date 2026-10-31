"""
Contenido neto de cada producto: cuántos gramos o mililitros trae, cuántas
unidades (huevos x 12) y si se vende a granel (el precio es por kilo).

Cada cadena informa el contenido a su manera, y con errores:

  - campos estructurados de SEPA (cantidad y unidad de presentación): "500 GR",
    "0.11 KG", "1 UNI" (Carrefour pone "1 UNI" a casi todo), ".50 gr" para
    500 g (coma corrida);
  - unidad de referencia (precio por kg, por litro, por 100 g): Carrefour pone
    ahí el contenido real ("190 GRM", con precio por kilo); las demás, la base
    del precio de referencia ("1 KG", "1000 GR", "PRECIO X 100 GR");
  - la descripción: "X 500 GRS", "6 X 354 ML", "BOT-1000-ml." (Cencosud),
    "1/2 KG", "X KG" (granel), "X 12 UNI", "MAPLE".

Para cada forma en que una cadena describe un producto se arma un candidato
(estructurado, referencia o descripción, con reglas para detectar las comas
corridas y los "1 UNI") y después cada producto se queda con el contenido que
más sucursales respaldan. contenido_acuerdo es la fracción de sucursales que
coinciden con el elegido.
"""

from __future__ import annotations

import math
import re

import numpy as np
import pandas as pd

from sepa.texto import sin_tildes

# unidad (mayúsculas, sin puntos) -> (dimensión, factor a g / ml / un)
UNIDADES = {
    **{u: ("g", 1.0) for u in ("G", "GR", "GRS", "GRM", "GRAMO", "GRAMOS", "GR1")},
    **{u: ("g", 1000.0) for u in ("KG", "KGS", "KGM", "KGR", "KILO", "KILOS")},
    "MG": ("g", 0.001),
    **{u: ("ml", 1.0) for u in ("ML", "MLT", "ML1", "MI", "CC", "CM3", "CMQ")},
    "CL": ("ml", 10.0),
    **{u: ("ml", 1000.0) for u in ("L", "LT", "LTS", "LTR", "LITRO", "LITROS", "LM1", "DM3")},
    **{u: ("un", 1.0) for u in ("U", "UN", "UNI", "UNID", "UNIDA", "UNIDAD", "UNIDADES", "UD", "UDS", "EA", "CU",
                                "PC", "PZA", "UN1")},
}
_MEDIDA = r"KILOS|KILO|KGS|KGM|KGR|KG|GRAMOS|GRAMO|GRS|GRM|GR|G|MG|MLT|ML|MI|CC|CM3|CMQ|CL|LITROS|LITRO|LTS|LTR|LT|L"
_UNIDAD = r"UNIDADES|UNIDAD|UNIDA|UNID|UNI|UDS|UD|UN|U"
_NUM = r"\d+(?:\.\d+)?"
# Cencosud agrega al final un código de envase: "BOT-1000-ml.", "PAQ-500-gr.", "BSA-114-gr."
ENVASE_RE = re.compile(rf"\b[A-Z]{{2,4}}-({_NUM})-(GR|G|KG|ML|MI|LT|L|CC|UN|U)\b")
PACK_RE = re.compile(rf"\b(\d{{1,3}})\s*X\s*({_NUM})\s*({_MEDIDA})\b")
# "3UX26G" son 78 g, pero "x 4 uni x 276 grs CJA-276-gr." son 276: ambiguo. Vale el tamaño escrito y el
# producto por la cantidad queda como alternativo.
PACK_UNIDADES_RE = re.compile(rf"\b(\d{{1,4}})\s*(?:{_UNIDAD})\s*X\s*({_NUM})\s*({_MEDIDA})\b")
# "2.250CC", "1,125CC", "x 2.755 Gr": el punto (o la coma) separa miles, no decimales.
MILES_RE = re.compile(r"^[1-9]\.\d{3}$")
SIMPLE_RE = re.compile(rf"(?<![\d.])({_NUM})\s*({_MEDIDA})\b")
FRACCION_RE = re.compile(r"\b([1-3])/([248])\s*(?:KILOS?|KGS?|K)\b")
GRANEL_RE = re.compile(r"\b(?:X|POR|XX)\s*(?:KILO|KGS?|KGM|KGR)\b|\bXKG\b|\bA GRANEL\b|\bGRANEL\b|\bKG\s*$")
UNIDADES_RE = re.compile(rf"\bX\s*(\d{{1,3}})\s*(?:{_UNIDAD}|HUEVOS)\b|\b(\d{{1,3}})\s*(?:{_UNIDAD})\b|\bX\s*(\d{{1,2}})\s*$")
REFERENCIA_EXPLICITA_RE = re.compile(rf"PRECIO X\s*({_NUM})?\s*({_MEDIDA})\b")
# Un pack que se vende como tal: "354cc sixpack PCK-6-un.", "473cc 6un", "20 Saq x 1 gr". El tamaño que dice la
# descripción es el de cada unidad.
SIXPACK_RE = re.compile(r"\bSIX ?PACK\b|\b6 ?PACK\b")
CODIGO_UNIDADES_RE = re.compile(r"\b[A-Z]{2,4}-(\d{1,2})-(?:UN|U)\b")
UNIDADES_SUELTAS_RE = re.compile(r"\b(\d{1,2}) ?(?:UN|UNI|UNID|UNIDADES)\b")
SAQUITOS_RE = re.compile(rf"\b(\d{{1,3}}) ?(?:SAQ\w*|SOBRES|SOBRECITOS|SOB|CAPSULAS|CAPS)\b.*?\bX ?({_NUM}) ?(G|GR|GRS|GRM)\b")
BOTELLA_RE = re.compile(r"\b(?:BOT|PET)-")
TOLERANCIA_REDONDEO = 0.06
# Dos contenidos que difieren en más que esto son presentaciones distintas, no un redondeo (500 g y 5 kg).
RATIO_ALTERNATIVO = 2.5
TOLERANCIA_REFERENCIA = 0.03


def _preparar(texto: str) -> str:
    t = sin_tildes(texto or "").upper()
    t = re.sub(r"(?<=\d),(?=\d)", ".", t)          # 1,5 L -> 1.5 L
    return re.sub(r"\s+", " ", t)


def unidad(texto: str) -> tuple[str, float] | None:
    return UNIDADES.get(re.sub(r"[\s.]", "", sin_tildes(texto or "")).upper())


def _medida_texto(numero: str, uni: str) -> tuple[float, str] | None:
    """Medida escrita en el texto libre: "2.250 CC" son 2250 cc (separador de miles en gramos o mililitros)."""
    u = unidad(uni)
    if not u or u[0] == "un" or not float(numero) > 0:
        return None
    valor = float(numero) * u[1]
    if u[1] == 1.0 and MILES_RE.match(numero):
        valor *= 1000
    return valor, u[0]


LATA_MAXIMA_ML = 1000.0   # "sixpack 473 cc" es el tamaño de cada lata; "six pack 2838 cm3", el del pack


def _unidades_del_pack(t: str) -> tuple[int | None, bool]:
    """
    (unidades de un pack que se vende como tal, si lo dice el código de envase de Cencosud): "PCK-6-un."
    (código), "sixpack" o "6un" (texto). (None, False) si no es un pack.
    """
    if (m := CODIGO_UNIDADES_RE.search(t)) and 2 <= int(m.group(1)) <= 24:
        return int(m.group(1)), True
    if SIXPACK_RE.search(t):
        return 6, False
    if (m := UNIDADES_SUELTAS_RE.search(t)) and 2 <= int(m.group(1)) <= 24:
        return int(m.group(1)), False
    return None, False


def desde_descripcion(descripcion: str) -> tuple[tuple[float, str] | None, int | None, bool, int | None,
                                                    tuple[float, str] | None, tuple[float, str] | None]:
    """
    (medida en g o ml, unidades, granel, pack, código, otra) que dice el texto de la descripción. pack:
    cuántas unidades multiplicaron al tamaño de cada una ("6 X 354 ML", "354cc sixpack"), si la medida es la
    de un pack. código: la medida del código de envase de Cencosud ("BOT-1000-ml."), también por separado.
    otra: la otra lectura posible de un "N UN X M g" (N x M).
    """
    t = _preparar(descripcion)
    # El texto libre manda sobre el código de envase de Cencosud, que a veces arrastra el error del campo
    # estructurado ("Pure ZUMMY 90g DOY-900-gr.").
    m = ENVASE_RE.search(t)
    codigo = (float(m.group(1)) * u[1], u[0]) if m and (u := unidad(m.group(2))) and u[0] != "un" else None
    if codigo and u[1] == 1.0 and codigo[0] < 1:
        codigo = (codigo[0] * 1000, codigo[1])   # "LAT-0.354-ml.": litros (o kilos) rotulados ml (o gr)
    if codigo and codigo[1] == "ml" and BOTELLA_RE.search(t) and round(codigo[0], 3) == 75.0:
        codigo = (750.0, "ml")   # "vino CRUX Malbec BOT-75-ml." y "BOT-0.075-ml.": botellas de 75 cl
    libre = ENVASE_RE.sub(" ", t)
    medida, pack = None, None
    en_pack, por_codigo = _unidades_del_pack(t)
    if packs := PACK_RE.findall(libre):
        n, tam, uni = packs[-1]
        unitario = _medida_texto(tam, uni)
        if unitario and int(n) > 0:
            if en_pack is None and int(n) > 1 and codigo == unitario:
                # "12X500G PAQ-500-gr.": el 12 es el bulto; lo que se vende (y su precio) es el paquete.
                medida = unitario
            else:
                medida = (int(n) * unitario[0], unitario[1])
                pack = int(n) if en_pack else None
    if medida is None and (s := SAQUITOS_RE.search(libre)) and int(s.group(1)) >= 2:
        medida, pack = (int(s.group(1)) * float(s.group(2)), "g"), int(s.group(1))   # "20 Saq x 1 gr"
    if medida is None and (f := FRACCION_RE.search(libre)):
        medida = (1000.0 * int(f.group(1)) / int(f.group(2)), "g")
    if medida is None and (simples := SIMPLE_RE.findall(libre)):
        medida = _medida_texto(*simples[-1])
        # Las bebidas en pack se describen por lata: "473cc sixpack" son 6 latas.
        if medida and medida[1] == "ml" and en_pack and (por_codigo or medida[0] <= LATA_MAXIMA_ML):
            medida, pack = (en_pack * medida[0], "ml"), en_pack
    if medida is None and codigo:
        medida = codigo
    otra = None
    if (pu := PACK_UNIDADES_RE.search(libre)) and int(pu.group(1)) > 1 and (m2 := _medida_texto(*pu.group(2, 3))):
        otra = (int(pu.group(1)) * m2[0], m2[1])

    unidades = None
    if "MEDIA DOCENA" in t:
        unidades = 6
    elif "DOCENA" in t:
        unidades = 12
    elif "MAPLE" in t:
        unidades = 30
    elif m and (u := unidad(m.group(2))) and u[0] == "un" and float(m.group(1)) >= 2:
        unidades = int(float(m.group(1)))
    else:
        for x, y, z in UNIDADES_RE.findall(t):
            n = int(x or y or z)
            if 2 <= n <= 60:
                unidades = n
                break
    # "X KG" / "POR KG" es siempre precio por kilo; "GRANEL" o un "KG" final, solo si no hay otro tamaño.
    granel = bool(re.search(r"\b(?:X|POR)\s*KG\b|\bXKG\b", t)) or (medida is None and bool(GRANEL_RE.search(t)))
    return medida, unidades, granel, pack, codigo, otra


def desde_referencia(cantidad_ref: str, unidad_ref: str, ratio: float, presentacion_es_unidad: bool,
                     segun_texto: tuple[float, str] | None = None) -> tuple[float, str, bool] | None:
    """
    Contenido según el precio de referencia (precio de lista / precio de referencia = contenido / base):
    (valor, unidad, confirmado). Carrefour informa en cantidad_referencia el contenido real, con precio por kilo
    o litro (o, en el 6 % de los casos, por 100 g: ese solo vale si la descripción no dice otra cosa), y el
    precio lo confirma; las demás cadenas, la base del precio de referencia (1 kg, 1000 g, 100 g).
    segun_texto: el contenido que dice la descripción.
    """
    if not (isinstance(ratio, float) and math.isfinite(ratio) and ratio > 0):
        return None
    texto = _preparar(unidad_ref)
    explicita = REFERENCIA_EXPLICITA_RE.search(texto)
    if explicita:
        u = unidad(explicita.group(2))
        if not u or u[0] == "un":
            return None
        base = float(explicita.group(1) or 1) * u[1]
        return round(ratio * base, 3), u[0], False
    u = unidad(texto)
    try:
        cant = float((cantidad_ref or "").replace(",", "."))
    except ValueError:
        return None
    if not u or u[0] == "un" or not cant > 0:
        return None
    contenido_declarado = cant * u[1]
    # Carrefour: cantidad_referencia es el contenido, si el precio lo confirma ("1 GRM" no: es "una unidad").
    def confirma(base: float) -> bool:
        return abs(ratio * base - contenido_declarado) <= TOLERANCIA_REFERENCIA * contenido_declarado
    texto_coincide = segun_texto is None or (
        segun_texto[1] == u[0] and abs(segun_texto[0] - contenido_declarado) <= TOLERANCIA_REDONDEO * segun_texto[0])
    if presentacion_es_unidad and contenido_declarado > 1 and (confirma(1000) or (confirma(100) and texto_coincide)):
        return round(contenido_declarado, 3), u[0], True
    if cant in (1, 10, 100, 1000):
        return round(ratio * contenido_declarado, 3), u[0], False   # precio por 1 kg, 100 g, 1000 g...
    return None


def unidades_referencia(unidad_ref: str, ratio: float) -> int | None:
    """Unidades según un precio de referencia por unidad ("30 UNI" con el precio de cada huevo)."""
    u = unidad(unidad_ref)
    if not (u and u[0] == "un" and isinstance(ratio, float) and math.isfinite(ratio)):
        return None
    n = round(ratio)
    return n if 2 <= n <= 60 and abs(ratio - n) <= 0.05 else None


def _muy_distinto(a: float, b: float) -> bool:
    return a > RATIO_ALTERNATIVO * b or b > RATIO_ALTERNATIVO * a


def _es_cantidad_de_unidades(valor: float, descripcion: str) -> bool:
    """El valor es la cantidad de unidades que dice la descripción ("25" en "X 25 UNI", "18" en "CAJA 18U.")."""
    n = int(valor)
    return valor == n and bool(re.search(rf"\b{n}\s*(?:{_UNIDAD})\b", _preparar(descripcion)))


def _decimal_corrido(a: float, b: float) -> bool:
    """a y b difieren en una potencia de 10 (x10, x100, x1000): una coma corrida en uno de los dos."""
    k = math.log10(a / b)
    return abs(k) >= 0.9 and abs(k - round(k)) <= 0.02


def resolver_fila(cantidad: str, unidad_txt: str, cantidad_ref: str, unidad_ref: str, ratio: float,
                  descripcion: str) -> tuple[float | None, str | None, str | None, int | None, bool,
                                             tuple[float, str] | None]:
    """
    (contenido, 'g' | 'ml', fuente, unidades, granel, alternativo) para una forma de describir el producto.
    alternativo: otro contenido muy distinto que dice la misma fila (la descripción, el código de envase o el
    precio de referencia); si el elegido deja un precio por kilo imposible, decide el precio (precio/hecho.py).
    """
    u = unidad(unidad_txt)
    try:
        v = float((cantidad or "").replace(",", "."))
    except ValueError:
        v = math.nan
    est = (v * u[1], u[0]) if u and math.isfinite(v) and v > 0 else None
    desc, unidades_desc, granel, pack, codigo, otra = desde_descripcion(descripcion)
    # "1 g" o "1 ml" en el campo estructurado (y el precio de referencia calculado con él) es, como el "1 UNI",
    # "una unidad": manda la descripción ("GELATINA MORIXE X 40 GRS").
    uno = est is not None and est[1] != "un" and est[0] == 1.0 and desc is not None and desc[0] != 1.0
    if uno:
        est = None
    es_unidad = est is None or est[1] == "un"
    ref = desde_referencia(cantidad_ref, unidad_ref, ratio, es_unidad, desc)
    # Tampoco vale un "1 g" de la referencia, ni la cantidad de unidades cargada como gramos ("X 25 UNI" con
    # referencia "25 GRS": el precio de referencia se calcula con ese mismo dato, así que no lo confirma).
    if ref and (ref[0] < 1 or (uno and ref[0] == 1.0) or _es_cantidad_de_unidades(ref[0], descripcion)):
        ref = None
    # El campo estructurado con el tamaño de cada lata de un pack ("473 cc" en un "six pack 473 cc").
    if est and desc and pack and est[1] == desc[1] and abs(desc[0] - pack * est[0]) <= 0.02 * desc[0]:
        est = desc

    # Primero lo estructurado (si dice 2 o más: Carrefour pone "1 UNI" a todo), después la descripción, el
    # precio de referencia por unidad y, si no hay otra cosa, el "1 UN" (una lechuga o una palta se venden por
    # unidad, sin peso informado).
    est_un = int(est[0]) if est and est[1] == "un" and 1 <= est[0] <= 60 and est[0] == int(est[0]) else None
    unidades = est_un if est_un and est_un >= 2 else (unidades_desc or unidades_referencia(unidad_ref, ratio)
                                                      or est_un)
    if granel:
        return 1000.0, "g", "granel", unidades, True, None

    elegido, fuente = None, None
    if est and est[1] != "un":
        # Un campo estructurado corrido en una potencia de 10 respecto del texto ("300 ml" de una gaseosa de 3 l,
        # "1.50 gr" de un balde "BDE-1500-gr.") cede ante él. Si lo contradice el precio de referencia, queda
        # como alternativo: lo decide el precio.
        corrido = next((c for c in (desc, codigo) if c and c[1] == est[1] and _decimal_corrido(est[0], c[0])), None)
        if corrido:
            elegido, fuente = corrido, "descripcion"
        elif est[0] >= 1:
            # El campo estructurado redondea (".13 Kg" para "POT-0.125-Kg"): si la descripción dice lo mismo con
            # más precisión, vale la descripción.
            redondeo = desc and desc[1] == est[1] and abs(est[0] - desc[0]) <= TOLERANCIA_REDONDEO * desc[0]
            elegido, fuente = (desc if redondeo else est), "sepa"
        elif desc:
            elegido, fuente = desc, "descripcion"
        elif ref:
            elegido, fuente = ref, "referencia"
    elif ref and not ref[2] and desc and desc[1] == ref[1] and _muy_distinto(ref[0], desc[0]):
        # Una referencia que el precio no confirma ("10 GRS" leído como "precio cada 10 g") contra un texto que
        # dice otra cosa ("X 100 GRS"): vale el texto, y la referencia queda como alternativo.
        elegido, fuente = desc, "descripcion"
    elif ref:
        # La referencia redondea ("29 GRS" para "X 29.4 GRS"): si la descripción dice lo mismo con más precisión,
        # vale la descripción.
        redondeo = desc and desc[1] == ref[1] and abs(ref[0] - desc[0]) <= TOLERANCIA_REDONDEO * desc[0]
        elegido, fuente = (desc if redondeo else ref), "referencia"
    elif desc:
        elegido, fuente = desc, "descripcion"
    if elegido is None:
        return None, None, None, unidades, False, None
    alternativo = next(((c[0], c[1]) for c in (desc, otra, codigo, ref, est)
                        if c and c[1] == elegido[1] and _muy_distinto(c[0], elegido[0])), None)
    return round(elegido[0], 3), elegido[1], fuente, unidades, False, alternativo


def resolver(presentaciones: pd.DataFrame, internos: set[int]) -> pd.DataFrame:
    """
    presentaciones: producto, descripcion, cantidad, unidad, cantidad_referencia, unidad_referencia,
    ratio_referencia, veces. internos: códigos de producto con código interno de cadena (balanza).
    Devuelve una fila por producto: contenido, unidad_contenido, contenido_fuente, contenido_acuerdo,
    unidades, granel.
    """
    p = presentaciones
    filas = [resolver_fila(*x) for x in zip(p["cantidad"], p["unidad"], p["cantidad_referencia"],
                                            p["unidad_referencia"], p["ratio_referencia"], p["descripcion"])]
    r = pd.DataFrame([f[:5] for f in filas], index=p.index,
                     columns=["contenido", "unidad_contenido", "contenido_fuente", "unidades", "granel"])
    r["alt_contenido"] = [f[5][0] if f[5] else np.nan for f in filas]
    r["alt_unidad"] = [f[5][1] if f[5] else None for f in filas]
    r["producto"], r["veces"] = p["producto"].to_numpy(), p["veces"].to_numpy()
    # "BANANA" de balanza con "1 KG" estructurado también es granel (precio por kilo).
    kilo_interno = (r["producto"].isin(internos) & r["contenido"].eq(1000) & r["unidad_contenido"].eq("g")
                    & p["unidad"].map(lambda x: (unidad(x) or ("", 0))[1] == 1000.0))
    r.loc[kilo_interno, ["contenido_fuente", "granel"]] = ["granel", True]

    # Se vota el número (200 g y 200 cc del mismo producto son la misma presentación); la unidad y la fuente
    # son las más respaldadas entre las filas que votaron al ganador.
    con = r.dropna(subset=["contenido"])
    votos = (con.groupby(["producto", "contenido"])["veces"].sum().reset_index()
             .sort_values(["producto", "veces"], ascending=[True, False]))
    total = con.groupby("producto")["veces"].sum()
    elegido = votos.drop_duplicates("producto").set_index("producto")
    elegido["contenido_acuerdo"] = (elegido["veces"] / total.reindex(elegido.index)).round(3)
    clave = list(zip(elegido.index, elegido["contenido"]))
    for col in ("unidad_contenido", "contenido_fuente"):
        mas_votado = (con.groupby(["producto", "contenido", col])["veces"].sum().reset_index()
                      .sort_values("veces", ascending=False).drop_duplicates(["producto", "contenido"])
                      .set_index(["producto", "contenido"])[col])
        elegido[col] = mas_votado.reindex(clave).to_numpy()
    # Contenido alternativo: el más respaldado de los que difieren mucho del elegido, sea lo que dice otra cadena
    # (50 g donde la más grande dice 5 g) o lo que dice otra fuente de la misma fila (la descripción contra el
    # precio de referencia). Decide el precio, en precio/hecho.py: gana el que deja el precio por kilo dentro de
    # lo habitual de su subcategoría.
    columnas = ["producto", "contenido", "unidad_contenido", "veces"]
    de_filas = r.loc[r["alt_contenido"].notna(), ["producto", "alt_contenido", "alt_unidad", "veces"]]
    cand = pd.concat([con[columnas], de_filas.set_axis(columnas, axis=1)])
    cand = (cand.groupby(["producto", "contenido", "unidad_contenido"])["veces"].sum().reset_index()
            .sort_values(["producto", "veces"], ascending=[True, False])
            .join(elegido["contenido"].rename("elegido"), on="producto"))
    cand = cand[[_muy_distinto(a, b) for a, b in zip(cand["contenido"], cand["elegido"])]]
    cand = cand.drop_duplicates("producto").set_index("producto")
    elegido["contenido_alternativo"] = cand["contenido"].reindex(elegido.index)
    elegido["unidad_alternativa"] = cand["unidad_contenido"].reindex(elegido.index)

    uni = r.dropna(subset=["unidades"])
    unidades = (uni.groupby(["producto", "unidades"])["veces"].sum().reset_index()
                .sort_values(["producto", "veces"], ascending=[True, False]).drop_duplicates("producto")
                .set_index("producto")["unidades"])
    granel = (r.assign(g=r["granel"].astype(float) * r["veces"]).groupby("producto")[["g", "veces"]].sum())
    salida = pd.DataFrame(index=pd.Index(sorted(p["producto"].unique()), name="producto"))
    salida = salida.join(elegido[["contenido", "unidad_contenido", "contenido_fuente", "contenido_acuerdo",
                                  "contenido_alternativo", "unidad_alternativa"]])
    salida["unidades"] = unidades.reindex(salida.index)
    salida["granel"] = (granel["g"] / granel["veces"]).reindex(salida.index).fillna(0) >= 0.5
    # Un granel es siempre "1 kg" (el precio publicado es por kilo).
    salida.loc[salida["granel"], ["contenido", "unidad_contenido", "contenido_fuente"]] = [1000.0, "g", "granel"]
    salida.loc[salida["granel"], ["contenido_alternativo", "unidad_alternativa"]] = np.nan
    return salida.reset_index()
