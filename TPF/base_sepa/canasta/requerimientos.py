"""
De una persona (edad, sexo, peso, actividad, etapa, restricciones) a sus metas diarias:

  1. Energía: gasto en reposo (Schofield, FAO/OMS/UNU 2004) por el nivel de actividad; en chicos, la ecuación de
     gasto total de FAO más el crecimiento; más el embarazo o la lactancia; por el objetivo de peso.
  2. Proteína por kg de peso (ajustado si hay obesidad) según edad, etapa, actividad y objetivo.
  3. Carbohidratos, grasas, saturadas, trans y azúcares libres como porcentaje de la energía; fibra por cada
     1.000 kcal.
  4. Micronutrientes: mínimo (RDA o AI) y máximo (UL) de referencia/requerimientos_nutricionales.csv.
  5. Reglas de las Guías Alimentarias (referencia/guias_alimentarias.csv).

Cada número queda registrado en `pasos` con su fórmula y su fuente: la página muestra el cálculo completo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from canasta import config as cfg


@dataclass
class Persona:
    sexo: str                      # F o M
    edad: int
    peso_kg: float
    actividad: str = "liviana"
    altura_cm: float | None = None
    objetivo: str = "mantener"
    etapa: str = "general"         # general, embarazo o lactancia
    trimestre: int | None = None
    restricciones: list[str] = field(default_factory=list)
    nombre: str = ""

    def validar(self) -> list[str]:
        errores = []
        if self.sexo not in ("F", "M"):
            errores.append("El sexo tiene que ser F o M.")
        if not cfg.EDAD_MINIMA <= self.edad <= cfg.EDAD_MAXIMA:
            errores.append(f"La edad tiene que estar entre {cfg.EDAD_MINIMA} y {cfg.EDAD_MAXIMA} años (antes de los "
                           f"{cfg.EDAD_MINIMA}, la alimentación la indica el pediatra).")
        if not cfg.PESO_RANGO_KG[0] <= self.peso_kg <= cfg.PESO_RANGO_KG[1]:
            errores.append("El peso no es válido.")
        if self.altura_cm is not None and not cfg.ALTURA_RANGO_CM[0] <= self.altura_cm <= cfg.ALTURA_RANGO_CM[1]:
            errores.append("La altura no es válida.")
        if self.actividad not in cfg.ACTIVIDAD:
            errores.append(f"Actividad desconocida: {self.actividad}.")
        if self.objetivo not in cfg.OBJETIVO:
            errores.append(f"Objetivo desconocido: {self.objetivo}.")
        if self.etapa not in ("general", "embarazo", "lactancia"):
            errores.append(f"Etapa desconocida: {self.etapa}.")
        elif self.etapa != "general" and (self.sexo != "F" or not 14 <= self.edad <= 50):
            errores.append("Embarazo y lactancia aplican a mujeres de 14 a 50 años.")
        if self.etapa == "embarazo" and self.trimestre not in (1, 2, 3):
            errores.append("Falta el trimestre del embarazo (1, 2 o 3).")
        desconocidas = [r for r in self.restricciones if r not in cfg.RESTRICCIONES]
        if desconocidas:
            errores.append(f"Restricciones desconocidas: {', '.join(desconocidas)}.")
        return errores

    @property
    def es_menor(self) -> bool:
        return self.edad < 18

    @property
    def vegetariana(self) -> bool:
        return "vegetariano" in self.restricciones or "vegano" in self.restricciones


@dataclass
class Meta:
    """Una restricción lineal sobre lo que se come por día: sum(gramos * coeficiente) entre minimo y maximo."""
    clave: str
    nombre: str
    unidad: str
    columna: str | None            # columna de nutrientes (cada 100 g) o None si es una regla de alimentos
    minimo: float | None = None
    maximo: float | None = None
    peso: float = cfg.PESO_DEFICIT_PREDETERMINADO
    fuente: str = ""
    tipo: str = "nutriente"        # energia, macro, nutriente, regla o informativa (no se exige)
    # Para reglas: qué alimentos cuentan y cómo (g, porciones o kcal).
    alimentos: set[str] | None = None
    grupo: str | None = None
    medida: str = "g"
    semanal: bool = False          # regla semanal: se exige en promedio diario y se muestra por semana
    nota: str = ""


@dataclass
class Requerimientos:
    persona: Persona
    energia_kcal: float
    proteina_g_kg: float
    peso_referencia_kg: float
    metas: list[Meta]
    pasos: list[dict]
    avisos: list[str]


def _fmt(x: float, d: int = 0) -> str:
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ------------------------------------------------------------
# Energía y proteína
# ------------------------------------------------------------

def _peso_referencia(p: Persona, pasos: list[dict]) -> float:
    if p.altura_cm is None or p.es_menor:
        return p.peso_kg
    m = p.altura_cm / 100
    imc = p.peso_kg / m ** 2
    categoria = ("bajo peso" if imc < 18.5 else "normal" if imc < 25 else "sobrepeso" if imc < 30 else "obesidad")
    if imc < cfg.IMC_OBESIDAD or p.etapa != "general":
        pasos.append({"titulo": "Índice de masa corporal",
                      "formula": f"IMC = peso / altura² = {_fmt(p.peso_kg, 1)} / {_fmt(m, 2)}² = {_fmt(imc, 1)}",
                      "resultado": f"{_fmt(imc, 1)} ({categoria}): se usa el peso real",
                      "fuente": "OMS"})
        return p.peso_kg
    ideal = cfg.IMC_REFERENCIA * m ** 2
    ajustado = ideal + cfg.FRACCION_EXCESO_PESO * (p.peso_kg - ideal)
    pasos.append({"titulo": "Índice de masa corporal y peso ajustado",
                  "formula": (f"IMC = {_fmt(p.peso_kg, 1)} / {_fmt(m, 2)}² = {_fmt(imc, 1)} (obesidad). Peso ajustado "
                              f"= peso con IMC 25 + 25 % del exceso = {_fmt(ideal, 1)} + 0,25 × "
                              f"({_fmt(p.peso_kg, 1)} − {_fmt(ideal, 1)})"),
                  "resultado": f"{_fmt(ajustado, 1)} kg para la energía y la proteína",
                  "fuente": "Práctica clínica habitual (el peso real sobreestima el gasto con obesidad)"})
    return ajustado


def _energia(p: Persona, peso: float, pasos: list[dict], avisos: list[str]) -> float:
    act = cfg.ACTIVIDAD[p.actividad]
    if p.es_menor:
        c, a, b = cfg.FAO_INFANTIL[p.sexo]
        total = c + a * peso + b * peso ** 2
        pasos.append({"titulo": "Gasto energético total (chicos y adolescentes, actividad moderada)",
                      "formula": f"{_fmt(c, 1)} + {_fmt(a, 1)} × {_fmt(peso, 1)} − {_fmt(-b, 3)} × {_fmt(peso, 1)}²",
                      "resultado": f"{_fmt(total)} kcal/día",
                      "fuente": "FAO/OMS/UNU 2004, Human energy requirements"})
        ajustado = total * act["ajuste_infantil"] * (1 + cfg.CRECIMIENTO_INFANTIL)
        pasos.append({"titulo": "Actividad y crecimiento",
                      "formula": (f"{_fmt(total)} × {_fmt(act['ajuste_infantil'], 2)} (actividad "
                                  f"{act['nombre'].lower()}) × {_fmt(1 + cfg.CRECIMIENTO_INFANTIL, 2)} (crecimiento)"),
                      "resultado": f"{_fmt(ajustado)} kcal/día",
                      "fuente": "FAO/OMS/UNU 2004: ±15 % por actividad; ~2 % para el crecimiento"})
        energia = ajustado
    else:
        a, b = next((a, b) for d, h, a, b in cfg.SCHOFIELD[p.sexo] if d <= p.edad < h)
        reposo = a * peso + b
        pasos.append({"titulo": "Gasto energético en reposo",
                      "formula": f"{_fmt(a, 3)} × {_fmt(peso, 1)} kg + {_fmt(b, 1)}",
                      "resultado": f"{_fmt(reposo)} kcal/día",
                      "fuente": "Ecuación de Schofield (FAO/OMS/UNU 2004) para "
                                f"{'varones' if p.sexo == 'M' else 'mujeres'} de su edad"})
        energia = reposo * act["pal"]
        pasos.append({"titulo": "Nivel de actividad física",
                      "formula": f"{_fmt(reposo)} × PAL {_fmt(act['pal'], 2)} ({act['nombre'].lower()}: "
                                 f"{act['descripcion'].lower()})",
                      "resultado": f"{_fmt(energia)} kcal/día",
                      "fuente": "FAO/OMS/UNU 2004 (sedentario 1,40-1,69; activo 1,70-1,99; vigoroso 2,00-2,40)"})
        obj = cfg.OBJETIVO[p.objetivo]
        if p.objetivo != "mantener":
            if p.etapa != "general":
                avisos.append("En el embarazo y la lactancia no se busca bajar ni subir de peso: se mantiene.")
            else:
                nueva = max(energia * obj["factor"], reposo * cfg.PISO_ENERGIA_REPOSO)
                pasos.append({"titulo": f"Objetivo: {obj['nombre'].lower()}",
                              "formula": (f"{_fmt(energia)} × {_fmt(obj['factor'], 2)}"
                                          + (f" (no menos de {_fmt(cfg.PISO_ENERGIA_REPOSO, 1)} × el gasto en reposo)"
                                             if p.objetivo == "bajar" else "")),
                              "resultado": f"{_fmt(nueva)} kcal/día",
                              "fuente": "Déficit moderado (~15 %) o superávit chico (~10 %)"})
                energia = nueva
    if p.etapa == "embarazo":
        extra = cfg.ENERGIA_EMBARAZO[p.trimestre]
        pasos.append({"titulo": f"Embarazo ({p.trimestre}.º trimestre)", "formula": f"{_fmt(energia)} + {extra}",
                      "resultado": f"{_fmt(energia + extra)} kcal/día", "fuente": "FAO/OMS/UNU 2004"})
        energia += extra
    elif p.etapa == "lactancia":
        extra = cfg.ENERGIA_LACTANCIA
        pasos.append({"titulo": "Lactancia", "formula": f"{_fmt(energia)} + {extra}",
                      "resultado": f"{_fmt(energia + extra)} kcal/día",
                      "fuente": "FAO/OMS/UNU 2004 (lactancia exclusiva, primeros 6 meses)"})
        energia += extra
    if p.es_menor and p.objetivo != "mantener":
        avisos.append("En chicos y adolescentes no se ajusta la energía para bajar o subir de peso: eso lo indica el "
                      "pediatra.")
    return round(energia, -1)


def _proteina_g_kg(p: Persona, pasos: list[dict]) -> float:
    base = next(v for d, h, v in cfg.PROTEINA_BASE if d <= p.edad <= h)
    motivos = [f"{_fmt(base, 2)} por la edad"]
    valor = base
    if p.etapa == "embarazo" and p.trimestre in (2, 3):
        valor = max(valor, cfg.PROTEINA_EMBARAZO)
        motivos.append(f"{_fmt(cfg.PROTEINA_EMBARAZO, 1)} en el embarazo")
    if p.etapa == "lactancia":
        valor = max(valor, cfg.PROTEINA_LACTANCIA)
        motivos.append(f"{_fmt(cfg.PROTEINA_LACTANCIA, 1)} en la lactancia")
    if p.actividad in cfg.PROTEINA_ACTIVIDAD and not p.es_menor:
        valor = max(valor, cfg.PROTEINA_ACTIVIDAD[p.actividad])
        motivos.append(f"{_fmt(cfg.PROTEINA_ACTIVIDAD[p.actividad], 1)} por la actividad")
    if p.etapa == "general" and not p.es_menor:
        if p.objetivo == "subir":
            valor = max(valor, cfg.PROTEINA_SUBIR)
            motivos.append(f"{_fmt(cfg.PROTEINA_SUBIR, 1)} para ganar músculo")
        elif p.objetivo == "bajar":
            valor = max(valor, cfg.PROTEINA_BAJAR)
            motivos.append(f"{_fmt(cfg.PROTEINA_BAJAR, 1)} al bajar de peso")
    pasos.append({"titulo": "Proteína por kg de peso",
                  "formula": "el mayor de: " + "; ".join(motivos),
                  "resultado": f"{_fmt(valor, 2)} g por kg por día",
                  "fuente": "NASEM (RDA), PROT-AGE/ESPEN (mayores de 65), ACSM e ISSN (deportistas)"})
    return valor


# ------------------------------------------------------------
# Micronutrientes y reglas
# ------------------------------------------------------------

NOMBRES = {
    "energia_kcal": ("Energía", "kcal"), "proteinas_g": ("Proteínas", "g"), "carbohidratos_g": ("Carbohidratos", "g"),
    "grasas_totales_g": ("Grasas totales", "g"), "grasas_saturadas_g": ("Grasas saturadas", "g"),
    "grasas_trans_g": ("Grasas trans", "g"), "azucares_libres_g": ("Azúcares libres (estimados)", "g"),
    "fibra_g": ("Fibra", "g"), "sodio_mg": ("Sodio", "mg"), "potasio_mg": ("Potasio", "mg"),
    "calcio_mg": ("Calcio", "mg"), "hierro_mg": ("Hierro", "mg"), "magnesio_mg": ("Magnesio", "mg"),
    "fosforo_mg": ("Fósforo", "mg"), "zinc_mg": ("Zinc", "mg"), "cobre_mg": ("Cobre", "mg"),
    "selenio_ug": ("Selenio", "µg"), "vitamina_a_ug": ("Vitamina A", "µg"),
    "vitamina_a_preformada_ug": ("Vitamina A preformada (animal)", "µg"), "vitamina_c_mg": ("Vitamina C", "mg"),
    "vitamina_d_ug": ("Vitamina D", "µg"), "vitamina_e_mg": ("Vitamina E", "mg"), "vitamina_k_ug": ("Vitamina K", "µg"),
    "vitamina_b1_mg": ("Vitamina B1 (tiamina)", "mg"), "vitamina_b2_mg": ("Vitamina B2 (riboflavina)", "mg"),
    "vitamina_b3_niacina_mg": ("Vitamina B3 (niacina)", "mg"), "vitamina_b6_mg": ("Vitamina B6", "mg"),
    "vitamina_b9_folato_ug": ("Folato (B9)", "µg"), "vitamina_b12_ug": ("Vitamina B12", "µg"),
    "colesterol_mg": ("Colesterol", "mg"),
}


def leer_tabla(ruta) -> pd.DataFrame:
    return pd.read_csv(ruta, sep=";", comment="#", encoding="utf-8-sig", dtype=str, keep_default_na=False)


def _fila_etapa(tabla: pd.DataFrame, p: Persona, tipo: str) -> pd.Series:
    t = tabla[tabla["tipo"] == tipo]
    edad = t["edad_desde"].astype(int).le(p.edad) & t["edad_hasta"].astype(int).ge(p.edad)
    sexo = t["sexo"].isin([p.sexo, "ambos"])
    for etapa in ([p.etapa, "general"] if p.etapa != "general" else ["general"]):
        fila = t[edad & sexo & (t["etapa"] == etapa)]
        if len(fila):
            return fila.iloc[0]
    raise ValueError(f"No hay ingestas de referencia ({tipo}) para {p.sexo} de {p.edad} años")


def _micronutrientes(p: Persona, pasos: list[dict], avisos: list[str]) -> list[Meta]:
    tabla = leer_tabla(cfg.RUTA_REQUERIMIENTOS)
    minimos, maximos = _fila_etapa(tabla, p, "minimo"), _fila_etapa(tabla, p, "maximo")
    columnas = [c for c in tabla.columns if c not in ("tipo", "sexo", "edad_desde", "edad_hasta", "etapa")]
    etapa = {"general": "", "embarazo": ", embarazo", "lactancia": ", lactancia"}[p.etapa]
    grupo = f"{'mujeres' if p.sexo == 'F' else 'varones'} de {minimos['edad_desde']} a {minimos['edad_hasta']} años"
    if minimos["sexo"] == "ambos":
        grupo = f"chicos de {minimos['edad_desde']} a {minimos['edad_hasta']} años"
    pasos.append({"titulo": "Vitaminas y minerales",
                  "formula": f"Ingestas de referencia para {grupo}{etapa}",
                  "resultado": "mínimos (RDA o AI) y máximos tolerables (UL) en la tabla de cobertura",
                  "fuente": "NASEM/IOM, Dietary Reference Intakes; sodio: OMS 2012"})
    metas = []
    for c in columnas:
        mn = float(minimos[c]) if minimos[c] else None
        mx = float(maximos[c]) if maximos[c] else None
        if mn is None and mx is None:
            continue
        nota = ""
        if mn is not None and p.vegetariana and c in cfg.FACTOR_VEGETARIANO:
            f = cfg.FACTOR_VEGETARIANO[c]
            nota = f"× {_fmt(f, 1)} por dieta vegetariana (menor absorción)"
            mn *= f
        if c == "sodio_mg" and "hipertension" in p.restricciones:
            mx = min(mx, cfg.SODIO_HIPERTENSION_MG)
            nota = "tope de 1.500 mg por hipertensión (AHA)"
        tipo = "nutriente"
        if c in cfg.INFORMATIVAS:
            tipo = "informativa"
            nota = "informativa: la mayor parte se sintetiza con el sol; no se le exige a la compra"
        if c in cfg.INFORMATIVAS_VEGANO and "vegano" in p.restricciones:
            tipo = "informativa"
            nota = "informativa: solo está en alimentos de origen animal o fortificados; un vegano necesita suplemento"
            avisos.append("La vitamina B12 no se cubre con alimentos veganos comunes: hace falta un suplemento "
                          "indicado por un profesional.")
        nombre, unidad = NOMBRES[c]
        metas.append(Meta(c, nombre, unidad, c, mn, mx, nota=nota, tipo=tipo,
                          fuente="NASEM/IOM DRI" if c != "sodio_mg" else "OMS 2012 / NASEM 2019"))
    return metas


def _macros(p: Persona, energia: float, prot_g: float, pasos: list[dict]) -> list[Meta]:
    grasas = cfg.GRASAS_PCT_INFANTIL if p.es_menor else cfg.GRASAS_PCT_ADULTO
    prot_max = cfg.PROTEINA_PCT_MAX_INFANTIL if p.es_menor else cfg.PROTEINA_PCT_MAX_ADULTO
    libres = cfg.AZUCARES_LIBRES_PCT_DIABETES if "diabetes" in p.restricciones else cfg.AZUCARES_LIBRES_PCT_MAX
    e = energia
    metas = [
        Meta("energia_kcal", "Energía", "kcal", "energia_kcal", e * (1 - cfg.TOLERANCIA_ENERGIA),
             e * (1 + cfg.TOLERANCIA_ENERGIA), tipo="energia", fuente="FAO/OMS/UNU 2004",
             nota=f"meta {_fmt(e)} kcal ± {_fmt(cfg.TOLERANCIA_ENERGIA * 100)} %"),
        Meta("proteinas_g", "Proteínas", "g", "proteinas_g", prot_g, prot_max / 100 * e / 4, tipo="macro",
             fuente="NASEM; AMDR", nota=f"hasta el {_fmt(prot_max)} % de la energía"),
        Meta("carbohidratos_g", "Carbohidratos", "g", "carbohidratos_g", cfg.CARBOHIDRATOS_PCT[0] / 100 * e / 4,
             cfg.CARBOHIDRATOS_PCT[1] / 100 * e / 4, tipo="macro", fuente="AMDR (NASEM 2005)",
             nota=f"{_fmt(cfg.CARBOHIDRATOS_PCT[0])} a {_fmt(cfg.CARBOHIDRATOS_PCT[1])} % de la energía"),
        Meta("grasas_totales_g", "Grasas totales", "g", "grasas_totales_g", grasas[0] / 100 * e / 9,
             grasas[1] / 100 * e / 9, tipo="macro", fuente="AMDR (NASEM 2005)",
             nota=f"{_fmt(grasas[0])} a {_fmt(grasas[1])} % de la energía"),
        Meta("grasas_saturadas_g", "Grasas saturadas", "g", "grasas_saturadas_g", None,
             cfg.SATURADAS_PCT_MAX / 100 * e / 9, tipo="macro", fuente="OMS 2023",
             nota=f"menos del {_fmt(cfg.SATURADAS_PCT_MAX)} % de la energía"),
        Meta("grasas_trans_g", "Grasas trans", "g", "grasas_trans_g", None, cfg.TRANS_PCT_MAX / 100 * e / 9,
             tipo="macro", fuente="OMS 2023", nota=f"menos del {_fmt(cfg.TRANS_PCT_MAX)} % de la energía"),
        Meta("azucares_libres_g", "Azúcares libres (estimados)", "g", "azucares_libres_g", None,
             libres / 100 * e / 4, tipo="macro", fuente="OMS 2015",
             nota=(f"menos del {_fmt(libres)} % de la energía"
                   + (" por diabetes" if "diabetes" in p.restricciones else "")
                   + "; se cuentan los azúcares de los productos con azúcar agregada")),
        Meta("fibra_g", "Fibra", "g", "fibra_g", cfg.FIBRA_G_POR_1000_KCAL * e / 1000, None, tipo="macro",
             fuente="NASEM (AI)", nota=f"{_fmt(cfg.FIBRA_G_POR_1000_KCAL)} g cada 1.000 kcal"),
    ]
    pasos.append({"titulo": "Macronutrientes",
                  "formula": (f"Proteínas ≥ {_fmt(prot_g)} g; carbohidratos {_fmt(cfg.CARBOHIDRATOS_PCT[0])}-"
                              f"{_fmt(cfg.CARBOHIDRATOS_PCT[1])} % de la energía (÷ 4 kcal/g); grasas "
                              f"{_fmt(grasas[0])}-{_fmt(grasas[1])} % (÷ 9 kcal/g); saturadas < "
                              f"{_fmt(cfg.SATURADAS_PCT_MAX)} %; azúcares "
                              f"libres < {_fmt(libres)} %; fibra {_fmt(cfg.FIBRA_G_POR_1000_KCAL)} g cada 1.000 kcal"),
                  "resultado": (f"carbohidratos {_fmt(metas[2].minimo)}-{_fmt(metas[2].maximo)} g; grasas "
                                f"{_fmt(metas[3].minimo)}-{_fmt(metas[3].maximo)} g; "
                                f"fibra ≥ {_fmt(metas[7].minimo)} g"),
                  "fuente": "NASEM 2005 (AMDR), OMS 2015 y 2023"})
    return metas


def _reglas(energia: float) -> list[Meta]:
    metas = []
    for r in leer_tabla(cfg.RUTA_GUIAS).itertuples(index=False):
        cantidad = float(r.cantidad)
        if r.escala_energia == "si":
            cantidad *= energia / 2000
        if r.por == "semana":
            cantidad /= 7
        alimentos, grupo = None, None
        if r.alimentos.startswith("grupo:"):
            grupo = r.alimentos.removeprefix("grupo:")
        else:
            alimentos = set(r.alimentos.split("|"))
        if r.medida == "kcal_pct":
            cantidad = cantidad / 100 * energia
        unidad = {"g": "g", "porciones": "porciones", "kcal_pct": "kcal"}[r.medida]
        mn, mx = (cantidad, None) if r.sentido == "min" else (None, cantidad)
        metas.append(Meta(f"regla_{r.regla}", r.descripcion, unidad, None, mn, mx, peso=cfg.PESO_DEFICIT["reglas"],
                          fuente="Guías Alimentarias para la Población Argentina (2016)", tipo="regla",
                          alimentos=alimentos, grupo=grupo, medida=r.medida, semanal=r.por == "semana"))
    return metas


def calcular(p: Persona) -> Requerimientos:
    errores = p.validar()
    if errores:
        raise ValueError(" ".join(errores))
    pasos: list[dict] = []
    avisos: list[str] = []
    peso = _peso_referencia(p, pasos)
    energia = _energia(p, peso, pasos, avisos)
    g_kg = _proteina_g_kg(p, pasos)
    prot = g_kg * peso
    pasos.append({"titulo": "Proteína del día", "formula": f"{_fmt(g_kg, 2)} g/kg × {_fmt(peso, 1)} kg",
                  "resultado": f"{_fmt(prot)} g/día", "fuente": ""})
    metas = _macros(p, energia, prot, pasos) + _micronutrientes(p, pasos, avisos) + _reglas(energia)
    if "diabetes" in p.restricciones or "hipertension" in p.restricciones:
        avisos.append("Con diabetes o hipertensión, esta canasta es orientativa: el plan lo ajusta el médico o un "
                      "nutricionista.")
    return Requerimientos(p, energia, g_kg, peso, metas, pasos, avisos)


# ------------------------------------------------------------
# Perfiles de ejemplo
# ------------------------------------------------------------

def perfiles() -> list[dict]:
    """referencia/perfiles.csv con los tipos de cada campo."""
    salida = []
    for f in leer_tabla(cfg.RUTA_PERFILES).to_dict("records"):
        f["edad"], f["peso_kg"] = int(f["edad"]), float(f["peso_kg"])
        f["altura_cm"] = float(f["altura_cm"]) if f["altura_cm"] else None
        f["trimestre"] = int(f["trimestre"]) if f["trimestre"] else None
        f["restricciones"] = [r for r in f["restricciones"].split("|") if r]
        salida.append(f)
    return salida


def persona_desde(dic: dict) -> Persona:
    """Una Persona a partir de un perfil o de lo que carga la página."""
    def num(clave, tipo=float):
        v = dic.get(clave)
        return None if v in (None, "") else tipo(v)
    return Persona(sexo=str(dic.get("sexo", "")), edad=num("edad", int) or 0, peso_kg=num("peso_kg") or 0.0,
                   altura_cm=num("altura_cm"), actividad=str(dic.get("actividad", "liviana")),
                   objetivo=str(dic.get("objetivo", "mantener")), etapa=str(dic.get("etapa", "general")),
                   trimestre=num("trimestre", int), restricciones=[str(r) for r in dic.get("restricciones", [])],
                   nombre=str(dic.get("nombre", ""))[:40])
