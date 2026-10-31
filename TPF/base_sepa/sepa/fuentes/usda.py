"""
USDA FoodData Central, SR Legacy: tabla de composición de laboratorio (~7.800
alimentos, dominio público). Da los nutrientes completos (vitaminas y
minerales incluidos) de los alimentos simples y frescos, que los rótulos
argentinos no declaran. La equivalencia de cada alimento genérico (nalga = top
round, vacío = flank...) está en referencia/alimentos.csv (fdc_id).
"""

from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path

import pandas as pd
import requests

from sepa import config as cfg

logger = logging.getLogger("sepa.fuentes.usda")

# id de nutriente de USDA -> (columna, factor desde la unidad de USDA)
NUTRIENTES = {
    1008: ("energia_kcal", 1), 1003: ("proteinas_g", 1), 1005: ("carbohidratos_totales_g", 1),
    1079: ("fibra_g", 1), 2000: ("azucares_g", 1), 1004: ("grasas_totales_g", 1), 1258: ("grasas_saturadas_g", 1),
    1292: ("grasas_monoinsaturadas_g", 1), 1293: ("grasas_poliinsaturadas_g", 1), 1257: ("grasas_trans_g", 1),
    1253: ("colesterol_mg", 1), 1093: ("sodio_mg", 1), 1092: ("potasio_mg", 1), 1087: ("calcio_mg", 1),
    1091: ("fosforo_mg", 1), 1089: ("hierro_mg", 1), 1090: ("magnesio_mg", 1), 1095: ("zinc_mg", 1),
    1098: ("cobre_mg", 1), 1103: ("selenio_ug", 1), 1106: ("vitamina_a_ug", 1), 1107: ("beta_caroteno_ug", 1),
    1114: ("vitamina_d_ug", 1), 1109: ("vitamina_e_mg", 1), 1185: ("vitamina_k_ug", 1), 1162: ("vitamina_c_mg", 1),
    1165: ("vitamina_b1_mg", 1), 1166: ("vitamina_b2_mg", 1), 1167: ("vitamina_b3_niacina_mg", 1),
    1175: ("vitamina_b6_mg", 1), 1177: ("vitamina_b9_folato_ug", 1), 1178: ("vitamina_b12_ug", 1),
    1018: ("alcohol_g", 1), 1051: ("agua_g", 1),
}


def asegurar() -> Path:
    ruta = cfg.DIR_USDA
    if (ruta / "food_nutrient.csv").exists():
        return ruta
    logger.info("Bajando USDA FoodData Central SR Legacy (~6 MB)...")
    r = requests.get(cfg.URL_USDA_SR_LEGACY, timeout=120)
    r.raise_for_status()
    ruta.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        for nombre in ("food.csv", "food_nutrient.csv"):
            miembro = next(m for m in z.namelist() if m.endswith("/" + nombre))
            (ruta / nombre).write_bytes(z.read(miembro))
    return ruta


def nutrientes(fdc_ids: list[int]) -> pd.DataFrame:
    """Una fila por fdc_id con los nutrientes cada 100 g (lo que USDA no informa vale 0)."""
    ruta = asegurar()
    fn = pd.read_csv(ruta / "food_nutrient.csv", usecols=["fdc_id", "nutrient_id", "amount"])
    fn = fn[fn["fdc_id"].isin(fdc_ids) & fn["nutrient_id"].isin(NUTRIENTES)]
    tabla = fn.pivot_table(index="fdc_id", columns="nutrient_id", values="amount", aggfunc="first")
    salida = pd.DataFrame(index=tabla.index)
    for nid, (col, factor) in NUTRIENTES.items():
        salida[col] = tabla[nid] * factor if nid in tabla else 0.0
    salida = salida.fillna(0.0)
    # USDA informa carbohidratos totales (con fibra); los rótulos argentinos, los disponibles.
    salida["carbohidratos_g"] = (salida["carbohidratos_totales_g"] - salida["fibra_g"]).clip(lower=0)
    nombres = pd.read_csv(ruta / "food.csv", usecols=["fdc_id", "description"]).set_index("fdc_id")["description"]
    salida["usda_descripcion"] = nombres.reindex(salida.index)
    return salida.round(4)
