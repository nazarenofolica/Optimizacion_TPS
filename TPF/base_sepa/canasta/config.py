"""
Parámetros de la canasta saludable. Todo lo discutible (factores de actividad, proteína, rangos de macronutrientes,
radio de búsqueda, cuánto se puede repetir un alimento) está acá, con su unidad y su fuente.
"""

from __future__ import annotations

from sepa import config as cfg_sepa

# ============================================================
# ARCHIVOS
# ============================================================

DIR_REFERENCIA = cfg_sepa.DIR_REFERENCIA
DIR_SALIDA = cfg_sepa.DIR_SALIDA
RUTA_REQUERIMIENTOS = DIR_REFERENCIA / "requerimientos_nutricionales.csv"
RUTA_GUIAS = DIR_REFERENCIA / "guias_alimentarias.csv"
RUTA_PERFILES = DIR_REFERENCIA / "perfiles.csv"
RUTA_DIM_PRODUCTO = cfg_sepa.RUTA_DIM_PRODUCTO.with_suffix(".parquet")
RUTA_DIM_TIENDA = cfg_sepa.RUTA_DIM_TIENDA.with_suffix(".parquet")
RUTA_FACT_PRECIO = cfg_sepa.RUTA_FACT_PRECIO.with_suffix(".parquet")
URL_GEOREF = cfg_sepa.URL_GEOREF
LAT_ARGENTINA, LON_ARGENTINA = cfg_sepa.LAT_ARGENTINA, cfg_sepa.LON_ARGENTINA

# ============================================================
# PERSONA
# ============================================================

EDAD_MINIMA = 4          # años: antes la alimentación depende de la lactancia o de fórmulas, no de una canasta
EDAD_MAXIMA = 100
PESO_RANGO_KG = (12.0, 250.0)
ALTURA_RANGO_CM = (90.0, 230.0)

# Gasto energético en reposo (FAO/OMS/UNU 2004, ecuaciones de Schofield): kcal/día = a * peso + b.
# (edad desde, edad hasta exclusive, a, b)
SCHOFIELD = {
    "M": [(18, 30, 15.057, 692.2), (30, 60, 11.472, 873.1), (60, 200, 11.711, 587.7)],
    "F": [(18, 30, 14.818, 486.6), (30, 60, 8.126, 845.6), (60, 200, 9.082, 658.5)],
}
# Gasto total de chicos y adolescentes (FAO/OMS/UNU 2004, actividad moderada): kcal/día = c + a * peso + b * peso².
FAO_INFANTIL = {"M": (310.2, 63.3, -0.263), "F": (263.4, 65.3, -0.454)}
CRECIMIENTO_INFANTIL = 0.02    # energía depositada al crecer, ~1-2 % del total después del primer año (FAO 2004)

# Nivel de actividad física (PAL, múltiplo del gasto en reposo, FAO/OMS/UNU 2004: sedentario o liviano 1,40-1,69;
# activo 1,70-1,99; vigoroso 2,00-2,40). En chicos, la ecuación ya es de actividad moderada: se ajusta ±15 %.
ACTIVIDAD = {
    "sedentaria": {"nombre": "Sedentaria", "pal": 1.40, "ajuste_infantil": 0.85,
                   "descripcion": "Trabajo sentado, sin ejercicio"},
    "liviana": {"nombre": "Liviana", "pal": 1.55, "ajuste_infantil": 0.85,
                "descripcion": "Caminatas o tareas de pie; ejercicio 1 o 2 veces por semana"},
    "moderada": {"nombre": "Moderada", "pal": 1.75, "ajuste_infantil": 1.00,
                 "descripcion": "Ejercicio 3 a 5 veces por semana o trabajo de pie todo el día"},
    "intensa": {"nombre": "Intensa", "pal": 1.95, "ajuste_infantil": 1.15,
                "descripcion": "Entrenamiento casi todos los días o trabajo físico pesado"},
    "muy_intensa": {"nombre": "Muy intensa", "pal": 2.20, "ajuste_infantil": 1.15,
                    "descripcion": "Deporte de competencia, doble turno de entrenamiento"},
}

# Objetivo de peso (solo adultos fuera del embarazo y la lactancia). Bajar: déficit moderado, sin bajar del gasto en
# reposo × 1,2. Subir: superávit chico para ganar músculo, con la proteína del deportista.
OBJETIVO = {
    "mantener": {"nombre": "Mantener el peso", "factor": 1.00},
    "bajar": {"nombre": "Bajar de peso", "factor": 0.85},
    "subir": {"nombre": "Ganar masa muscular", "factor": 1.10},
}
PISO_ENERGIA_REPOSO = 1.2

# Energía adicional del embarazo por trimestre y de la lactancia (FAO/OMS/UNU 2004), kcal/día.
ENERGIA_EMBARAZO = {1: 85, 2: 285, 3: 475}
ENERGIA_LACTANCIA = 505

# Con obesidad (IMC >= 30) el peso real sobreestima la energía y la proteína: se usa el peso ajustado
# (peso con IMC 25 más el 25 % del exceso), práctica habitual en nutrición clínica.
IMC_OBESIDAD = 30.0
IMC_REFERENCIA = 25.0
FRACCION_EXCESO_PESO = 0.25

# Proteína, g por kg de peso por día. Base: RDA de NASEM (0,95 de 4 a 13 años, 0,85 de 14 a 18, 0,8 adultos); 1,0
# desde los 65 (PROT-AGE / ESPEN); embarazo 1,1 (2.º y 3.er trimestre) y lactancia 1,3 (NASEM). Con entrenamiento,
# ACSM e ISSN recomiendan 1,2 a 2,0: se usa 1,0 / 1,4 / 1,6 según la actividad, 1,6 para ganar músculo y 1,2 al bajar
# de peso (preserva la masa magra).
PROTEINA_BASE = [(4, 13, 0.95), (14, 18, 0.85), (19, 64, 0.80), (65, 200, 1.00)]
PROTEINA_ACTIVIDAD = {"moderada": 1.0, "intensa": 1.4, "muy_intensa": 1.6}
PROTEINA_SUBIR = 1.6
PROTEINA_BAJAR = 1.2
PROTEINA_EMBARAZO = 1.1
PROTEINA_LACTANCIA = 1.3

# Rangos aceptables de distribución de la energía (AMDR, NASEM 2005), % de las kcal.
CARBOHIDRATOS_PCT = (45.0, 65.0)
GRASAS_PCT_ADULTO = (20.0, 35.0)
GRASAS_PCT_INFANTIL = (25.0, 35.0)       # 4 a 18 años
PROTEINA_PCT_MAX_ADULTO = 35.0
PROTEINA_PCT_MAX_INFANTIL = 30.0
SATURADAS_PCT_MAX = 10.0                 # OMS 2023
TRANS_PCT_MAX = 1.0                      # OMS 2023
AZUCARES_LIBRES_PCT_MAX = 10.0           # OMS 2015 (5 % con diabetes)
AZUCARES_LIBRES_PCT_DIABETES = 5.0
FIBRA_G_POR_1000_KCAL = 14.0             # AI de NASEM
SODIO_HIPERTENSION_MG = 1500.0           # AHA: meta ideal con hipertensión

# Dieta vegetariana: el hierro y el zinc de los vegetales se absorben peor; NASEM indica 1,8 veces el hierro y
# hasta 1,5 veces el zinc.
FACTOR_VEGETARIANO = {"hierro_mg": 1.8, "zinc_mg": 1.5}

# Tolerancia de la energía alrededor de la meta (la única restricción que no se negocia).
TOLERANCIA_ENERGIA = 0.05

# ============================================================
# RESTRICCIONES
# ============================================================

RESTRICCIONES = {
    "celiaquia": "Celiaquía (sin TACC)",
    "vegetariano": "Vegetariano",
    "vegano": "Vegano",
    "sin_lactosa": "Sin lactosa",
    "sin_leche": "Alergia a la leche",
    "sin_huevo": "Alergia al huevo",
    "sin_mani": "Alergia al maní",
    "sin_frutos_secos": "Alergia a frutos secos",
    "sin_soja": "Alergia a la soja",
    "sin_pescado": "Alergia al pescado",
    "sin_mariscos": "Alergia a mariscos",
    "sin_sesamo": "Alergia al sésamo",
    "sin_ultraprocesados": "Sin ultraprocesados (NOVA 4)",
    "hipertension": "Hipertensión",
    "diabetes": "Diabetes",
}
# Con celiaquía, lo único que se compra a granel es lo fresco: arroz, legumbres, harinas y frutos secos sueltos se
# contaminan con trigo en el local (ANMAT, recomendaciones para personas celíacas).
GRANEL_APTO_CELIACOS = {"Verduras y frutas", "Carnes y huevos"}
ALERGIAS = {"sin_leche": "leche", "sin_huevo": "huevo", "sin_mani": "mani", "sin_frutos_secos": "frutos_secos",
            "sin_soja": "soja", "sin_pescado": "pescado", "sin_mariscos": "mariscos", "sin_sesamo": "sesamo"}

# ============================================================
# QUÉ ENTRA EN LA CANASTA
# ============================================================

# Grupos alimentarios que se compran para comer. Quedan afuera el agua y las infusiones (sin nutrientes que
# cuenten: el agua es la de la canilla), los condimentos (van a gusto, aportan poco) y las comidas preparadas.
GRUPOS_CANASTA = [
    "Verduras y frutas", "Legumbres, cereales, papa, pan y pastas", "Leche, yogur y queso", "Carnes y huevos",
    "Aceites, frutas secas y semillas", "Alimentos de consumo opcional",
]
# Alimentos que nunca entran: alcohol, bebidas sin valor nutricional, fórmulas infantiles y gelatinas (su proteína
# es incompleta y engañaría al modelo).
ALIMENTOS_EXCLUIDOS = {
    "cerveza", "cerveza_sin_alcohol", "vino", "vino_espumante", "destilados", "fernet_aperitivos", "energizante",
    "isotonica", "gaseosa_cola", "gaseosa_lima_limon", "gaseosa_light", "tonica", "agua_saborizada", "jugo_polvo",
    "leche_infantil", "leche_infantil_liquida", "gelatina", "gelatina_light", "golosinas_sin_azucar",
}
# Productos que no son para comer como tales: huesos y carcasas para caldo, cueros, grasa, y el bofe (pulmón), que
# se vende sobre todo para mascotas. Su parte comestible real es mínima y el modelo los elegiría por baratos.
NOMBRES_EXCLUIDOS = r"CARCA[SZ]A|ESPINAZO|^HUESO|^CUERO|^CABEZA|CERDO CABEZA|TROZADO CABEZA|^GRASA|\bBOFE\b"
# Un precio por debajo de esta fracción de la mediana de su subcategoría está mal cargado (la papa a $95 el kg con
# una mediana de $3.500): el producto no se ofrece.
FRACCION_PRECIO_MINIMO = 1 / 8

# Opción "solo alimentos listos para comer" (para quien no cocina): quedan afuera los que hay que cocinar antes
# (carnes y pescados crudos, huevos, arroz, fideos, legumbres secas, harinas, papa, verduras que se comen cocidas).
# Siguen las frutas, las verduras de ensalada, los lácteos, el pan, las galletitas, los cereales, las conservas (atún,
# legumbres y verduras en lata) y los frutos secos.
ALIMENTOS_A_COCINAR = {
    # cereales, legumbres, papa y masas
    "arroz", "arroz_integral", "arroz_preparado", "arvejas_secas", "batata", "choclo", "fideos", "fideos_integrales",
    "fideos_instantaneos", "garbanzos", "harina", "harina_integral", "harina_otras", "lentejas", "noquis", "papa",
    "papas_congeladas", "pastas_frescas", "pastas_rellenas", "polenta", "porotos", "prepizza", "pure_instantaneo",
    "quinoa", "semola", "soja", "tapas_empanada", "pan_rallado", "premezcla",
    # carnes, pescados frescos y huevos
    "asado", "bife", "bondiola", "calamar", "carne_picada", "carne_picada_especial", "carre_cerdo", "cordero",
    "hamburguesa", "higado_vacuno", "higado_pollo", "huevos", "langostinos", "lengua", "lomo", "merluza",
    "milanesa_carne", "milanesa_pescado", "mollejas", "mondongo", "nalga", "nuggets_pollo", "osobuco", "pavo",
    "pechito_cerdo", "pollo_entero", "pollo_pata_muslo", "pollo_pechuga", "rinon", "salmon", "tapa_asado", "trucha",
    "vacio", "chorizo", "morcilla", "salchichas", "panceta",
    # verduras que se comen cocidas
    "verduras_hoja", "brocoli", "coliflor", "remolacha", "verduras_congeladas", "zapallito", "zapallo", "pure_tomate",
}
LISTOS_NOMBRE = "Solo alimentos listos para comer"
LISTOS_CRITERIO = ("Sin nada que haya que cocinar: carnes, pescados frescos y huevos; arroz, fideos, legumbres secas, "
                   "harinas, papa y verduras que se comen cocidas. Quedan frutas, verduras de ensalada, lácteos, pan, "
                   "galletitas, cereales, conservas (atún, legumbres y verduras en lata) y frutos secos.")

# Hogar: hasta cuántas personas comparten la compra (cada una con sus metas y restricciones).
PERSONAS_MAXIMAS = 8

# Alimentos de origen animal: su vitamina A es retinol (preformada), la que tiene máximo tolerable.
GRUPOS_VITAMINA_A_PREFORMADA = {"Carnes y huevos", "Leche, yogur y queso"}
ALIMENTOS_VITAMINA_A_PREFORMADA = {"manteca", "crema_leche", "dulce_de_leche", "leche_condensada", "helado",
                                   "postre_lacteo", "pate", "morcilla"}

# Variedad: ningún alimento genérico (subcategoría) pasa de estas porciones por día, escaladas por la energía
# (porción de referencia de cada alimento, porcion_g: 200 ml de leche, 60 g de arroz, 150 g de carne).
PORCIONES_MAX_POR_ALIMENTO = 2.0

# Productos que se consideran en cada sucursal: los más baratos cada 100 g comestibles de cada subcategoría (y el
# envase más barato, para que haya presentaciones chicas). Reduce el modelo sin perder opciones reales.
PRODUCTOS_POR_SUBCATEGORIA = 6

# Lo que se vende a granel se compra de a 100 g.
PASO_GRANEL_G = 100

# ============================================================
# SUCURSALES
# ============================================================

RADIO_KM = 3.0                 # se buscan sucursales hasta este radio...
RADIO_MAXIMO_KM = 25.0         # ...y se amplía hasta este si no hay suficientes
SUCURSALES_A_EVALUAR = 6
FORMATOS_SUCURSAL = {"Supermercado"}     # las estaciones de servicio no tienen surtido para una canasta

# ============================================================
# MODELO
# ============================================================

DIAS_PERIODO = {7: "una semana", 14: "dos semanas", 30: "un mes"}
DIAS_PREDETERMINADO = 7

# Peso de cada déficit en la primera etapa del modelo (minimizar lo que falta): las reglas de las Guías pesan la
# mitad que un nutriente.
PESO_DEFICIT = {"reglas": 0.5}
PESO_DEFICIT_PREDETERMINADO = 1.0
# Metas informativas: se muestran en la cobertura pero no se le exigen a la compra, porque la etapa 1 las perseguiría
# a cualquier precio (con productos fortificados carísimos). La vitamina D viene sobre todo del sol (y, si falta, de
# un suplemento); la B12 de un vegano, de un suplemento.
INFORMATIVAS = {"vitamina_d_ug"}
INFORMATIVAS_VEGANO = {"vitamina_b12_ug"}
# En la segunda etapa (minimizar el costo) cada déficit puede crecer a lo sumo esto (fracción de la meta): solo
# absorbe el redondeo numérico, no es una tolerancia.
HOLGURA_DEFICIT = 1e-4
TIEMPO_MAXIMO_S = 8.0
GAP_RELATIVO = 0.01
