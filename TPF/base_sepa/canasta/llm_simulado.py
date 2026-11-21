"""
Respuestas de ejemplo del LLM, sin red: las usan los tests y el modo de desarrollo `python -m canasta --llm-simulado`
(la página dice que es una simulación). Cada una es lo que devolvería Groq, tal cual, antes de validarla
(canasta/llm.validar): son datos de prueba, no interpretaciones reales del texto que se escriba.
"""

from __future__ import annotations

import copy


def _persona(**campos) -> dict:
    base = {"nombre": None, "sexo": None, "edad": None, "peso_kg": None, "altura_cm": None, "actividad": None,
            "objetivo": None, "etapa": None, "trimestre": None, "restricciones": [], "no_reconocidas": []}
    return {**base, **campos}


def _salida(personas: list[dict], **hogar) -> dict:
    base = {"dias": None, "agua": None, "listos": None, "promos": None, "caminata_minutos": None, "preguntas": [],
            "notas": []}
    return {"personas": personas, **base, **hogar}


TEXTOS = {
    "hogar": ("Somos mi hija de 8 años celíaca y yo, mujer de 40, con anemia; compramos para dos semanas y tomamos "
              "agua de la canilla."),
    "vegano": "Soy vegano, 30 años, 75 kg, entreno todos los días y quiero ganar músculo.",
    "receta": ("Paciente de 67 años, DBT2, HTA, LDL elevado: dieta hiposódica, evitar azúcares simples, 1.200 kcal "
               "diarias fraccionadas en 6 comidas, evitar picantes."),
}

SALIDAS = {
    "hogar": _salida(
        [_persona(nombre="Mi hija", sexo="F", edad=8, restricciones=["celiaquia"]),
         _persona(nombre="Yo", sexo="F", edad=40)],
        dias=14, agua="canilla",
        preguntas=["¿La anemia es por falta de hierro? Si es así, marcá «Anemia por falta de hierro» en tus datos."]),
    "vegano": _salida(
        [_persona(nombre="Yo", sexo=None, edad=30, peso_kg=75, actividad="intensa", objetivo="subir",
                  restricciones=["vegano"])],
        preguntas=[]),
    "receta": _salida(
        [_persona(nombre="Paciente", edad=67, restricciones=["diabetes", "hipertension", "colesterol_alto"],
                  no_reconocidas=["picantes"])],
        preguntas=["¿El paciente es mujer o varón, y cuánto pesa?"],
        notas=["La indicación de 1.200 kcal por día no se aplica: la canasta calcula la energía con la edad, el peso y "
               "la actividad. Si el médico indicó otra cifra, seguí la suya.",
               "Fraccionar en 6 comidas no cambia la compra: es cómo repartir lo que se compra.",
               "«Evitar azúcares simples» ya lo cubre la diabetes (azúcares libres por debajo del 5 % de la energía)."]),
}


def responder(texto: str) -> dict:
    """La salida de ejemplo que más se parece al texto (por palabras clave): una prescripción, una persona vegana o,
    si no, el hogar de la hija celíaca."""
    t = texto.lower()
    if any(p in t for p in ("paciente", "dbt", "hta", "prescrip", "indicación", "indicacion")):
        clave = "receta"
    elif "vegan" in t:
        clave = "vegano"
    else:
        clave = "hogar"
    return copy.deepcopy(SALIDAS[clave])
