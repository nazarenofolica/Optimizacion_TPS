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

# Aumentar de peso (por ejemplo, con bajo peso): se suma un superávit fijo al gasto, no un porcentaje. La práctica
# habitual en nutrición clínica para recuperar peso en adultos es comer 300 a 500 kcal/día más de lo que se gasta,
# para subir de a poco, unos 0,25 a 0,5 kg por semana (~7.700 kcal por kg ganado); el NHS (Reino Unido), en su
# consejo para adultos con bajo peso, también recomienda subir gradualmente y con comida nutritiva, no con
# ultraprocesados. Se usa el extremo alto del rango: ~0,45 kg por semana.
SUPERAVIT_AUMENTAR_KCAL = 500

# Objetivo de peso (solo adultos fuera del embarazo y la lactancia). Bajar: déficit moderado, sin bajar del gasto en
# reposo × 1,2. Subir: superávit chico para ganar músculo, con la proteína del deportista. Aumentar: superávit sumado
# (superavit_kcal, en lugar de factor) para recuperar peso, con proteína moderada; si la persona tiene sobrepeso
# (IMC >= 25), se aplica igual pero se avisa que no se recomienda.
OBJETIVO = {
    "mantener": {"nombre": "Mantener el peso", "factor": 1.00},
    "bajar": {"nombre": "Bajar de peso", "factor": 0.85},
    "subir": {"nombre": "Ganar masa muscular", "factor": 1.10},
    "aumentar": {"nombre": "Aumentar de peso", "superavit_kcal": SUPERAVIT_AUMENTAR_KCAL},
}
PISO_ENERGIA_REPOSO = 1.2

# Energía adicional del embarazo por trimestre y de la lactancia (FAO/OMS/UNU 2004), kcal/día.
ENERGIA_EMBARAZO = {1: 85, 2: 285, 3: 475}
ENERGIA_LACTANCIA = 505

# Con obesidad (IMC >= 30) el peso real sobreestima la energía y la proteína: se usa el peso ajustado
# (peso con IMC 25 más el 25 % del exceso), práctica habitual en nutrición clínica.
IMC_OBESIDAD = 30.0
IMC_SOBREPESO = 25.0     # desde acá no se recomienda aumentar de peso (OMS)
IMC_REFERENCIA = 25.0
FRACCION_EXCESO_PESO = 0.25

# Proteína, g por kg de peso por día. Base: RDA de NASEM (0,95 de 4 a 13 años, 0,85 de 14 a 18, 0,8 adultos); 1,0
# desde los 65 (PROT-AGE / ESPEN); embarazo 1,1 (2.º y 3.er trimestre) y lactancia 1,3 (NASEM). Con entrenamiento,
# ACSM e ISSN recomiendan 1,2 a 2,0: se usa 1,0 / 1,4 / 1,6 según la actividad, 1,6 para ganar músculo y 1,2 al bajar
# de peso (preserva la masa magra). Para aumentar de peso, las guías de nutrición clínica (ESPEN) usan 1,2 a 1,5 g/kg
# al recuperar a un adulto desnutrido: se toma 1,2, el extremo bajo, porque lo que se busca es energía (que lo ganado
# no sea solo grasa) y no músculo como en "subir"; más proteína encarece la canasta sin cambiar el objetivo.
PROTEINA_BASE = [(4, 13, 0.95), (14, 18, 0.85), (19, 64, 0.80), (65, 200, 1.00)]
PROTEINA_ACTIVIDAD = {"moderada": 1.0, "intensa": 1.4, "muy_intensa": 1.6}
PROTEINA_SUBIR = 1.6
PROTEINA_BAJAR = 1.2
PROTEINA_AUMENTAR = 1.2
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

# Grupos alimentarios que se compran para comer. Quedan afuera el grupo "Agua e infusiones" (yerba, café, té y agua
# saborizada: sin nutrientes que cuenten), los condimentos (van a gusto, aportan poco) y las comidas preparadas. El
# agua y la soda envasadas (ALIMENTOS_AGUA, más abajo) se cargan aparte y solo se ofrecen si el hogar compra el agua.
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

# ============================================================
# AGUA
# ============================================================

# Agua y soda envasadas (grupo "Agua e infusiones"): entran a la oferta solo si el hogar compra el agua.
ALIMENTOS_AGUA = {"agua", "soda"}
# Cómo toma agua el hogar (uno para todos). Cada modo combina de dónde sale el agua ("compra": el agua y la soda
# envasadas entran a la oferta y la meta se le exige a la compra; si no, es la de la canilla, gratis, y la meta solo
# se informa) con qué cuenta para la meta ("total": el agua de todo lo que se come y se toma, columna agua_g;
# "bebidas": solo el agua y la soda que se compran, sin la de los alimentos). En la página son tres opciones.
AGUA_MODOS = {
    "canilla": {"nombre": "Tomo de la canilla", "corto": "agua de la canilla", "compra": False, "cuenta": "total",
                "descripcion": "No se compra. Te decimos cuánta tomar por día, descontando la que traen los "
                               "alimentos."},
    "compra": {"nombre": "La compro", "corto": "agua comprada", "compra": True, "cuenta": "total",
               "descripcion": "Agua o soda envasada hasta cubrir el agua del día, contando la que traen los "
                              "alimentos."},
    "bebidas": {"nombre": "Tomo 2 litros de bebida", "corto": "2 litros de bebida", "compra": True,
                "cuenta": "bebidas",
                "descripcion": "Agua o soda envasada: 8 vasos (2 litros) por día para un adulto, sin contar la de los "
                               "alimentos."},
}
AGUA_MODO_PREDETERMINADO = "canilla"
# Ingesta adecuada (AI) de agua total por día, en litros: la de las bebidas más la de los alimentos (NASEM/IOM 2004,
# Dietary Reference Intakes for Water, Potassium, Sodium, Chloride, and Sulfate). (edad desde, edad hasta, litros);
# el embarazo y la lactancia, de 14 a 50 años.
AGUA_TOTAL_L = {
    "F": [(4, 8, 1.7), (9, 13, 2.1), (14, 18, 2.3), (19, 200, 2.7)],
    "M": [(4, 8, 1.7), (9, 13, 2.4), (14, 18, 3.3), (19, 200, 3.7)],
    "embarazo": 3.0, "lactancia": 3.8,
}
# Agua de las bebidas por día, en litros. Adultos fuera del embarazo y la lactancia: 8 vasos de 250 ml (Guías
# Alimentarias para la Población Argentina 2016, mensaje 1: "tomar a diario 8 vasos de agua segura"). Menores,
# embarazo y lactancia: la parte de la AI de NASEM/IOM 2004 que viene de las bebidas.
AGUA_BEBIDAS_L = {
    "F": [(4, 8, 1.2), (9, 13, 1.6), (14, 18, 1.8), (19, 200, 2.0)],
    "M": [(4, 8, 1.2), (9, 13, 1.8), (14, 18, 2.6), (19, 200, 2.0)],
    "embarazo": 2.3, "lactancia": 3.1,
}

# Alimentos de origen animal: su vitamina A es retinol (preformada), la que tiene máximo tolerable.
GRUPOS_VITAMINA_A_PREFORMADA = {"Carnes y huevos", "Leche, yogur y queso"}
ALIMENTOS_VITAMINA_A_PREFORMADA = {"manteca", "crema_leche", "dulce_de_leche", "leche_condensada", "helado",
                                   "postre_lacteo", "pate", "morcilla"}

# Variedad: ningún alimento genérico (subcategoría) pasa de estas porciones por día, escaladas por la energía
# (porción de referencia de cada alimento, porcion_g: 200 ml de leche, 60 g de arroz, 150 g de carne). El agua y la
# soda (ALIMENTOS_AGUA) no tienen este tope (2 vasos no alcanzan para la meta de agua): cada una puede llegar a la meta
# de agua del día de la persona.
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

# Búsqueda por tiempo caminando (la página y python -m canasta --caminata). El tiempo máximo es una restricción del
# espacio de búsqueda, no un objetivo que compita con el precio: primero se eligen las sucursales a las que se llega
# caminando en ese tiempo (rutas peatonales reales de OpenRouteService) y recién ahí se optimiza la compra. Ampliar el
# tiempo agrega sucursales y se vuelve a optimizar.
CAMINATA_MINUTOS = 15                    # valor inicial, provisorio
CAMINATA_OPCIONES = [15, 30, 45, 60]     # lo que se puede elegir (y el orden en que se amplía)
# Velocidad de referencia: la de foot-walking en OpenRouteService (5 km/h). Con ella, el radio en línea recta
# minutos × velocidad contiene todas las sucursales alcanzables (una ruta nunca es más corta que la recta).
VELOCIDAD_CAMINATA_KMH = 5.0
# Si el servicio de rutas no responde, el tiempo se estima con la distancia en línea recta por este desvío típico de
# las calles; se muestra como estimado, nunca como ruta real.
FACTOR_DESVIO_CAMINATA = 1.3
# Cuántas sucursales candidatas (dentro del radio) se mandan a la matriz de rutas: la más cercana de cada cadena y las
# que siguen. El plan gratuito de OpenRouteService admite 3.500 pares origen-destino por consulta.
CANDIDATAS_MAXIMAS_RUTEO = 50
# Cuántas de las alcanzables se optimizan: la más cercana de cada cadena (y, si faltan, las que siguen). Es más que
# SUCURSALES_A_EVALUAR para que ampliar el tiempo sume cadenas nuevas en lugar de dejar todo igual.
SUCURSALES_A_EVALUAR_CAMINATA = 10
# Compra en dos supermercados (resultado.dos_super, a pedido después del resultado): a la sucursal elegida A se le
# puede sumar una vecina B para comprar ahí lo que convenga. No se le pone precio al minuto: se informa el ahorro y los
# minutos de más, y la persona decide. Vecinas: las que quedan a lo sumo DOS_SUPER_MINUTOS_ENTRE de A caminando
# (estimado: línea recta × FACTOR_DESVIO_CAMINATA a VELOCIDAD_CAMINATA_KMH) y dentro del límite de caminata (o entre
# las evaluadas, si no se buscó por tiempo); se prueban hasta DOS_SUPER_VECINAS, la más cercana a A de cada otra cadena
# primero. Se propone si la combinación cubre mejor las metas (aunque cueste más: nunca se cambia nutrición por plata)
# o, si las cubre igual, si ahorra al menos el DOS_SUPER_AHORRO_MINIMO_PCT % del costo de A y al menos
# DOS_SUPER_AHORRO_MINIMO_PESOS: en la canasta de una semana (~$23.000) el 3 % son ~$700, poco para caminar 10 minutos
# más y hacer dos colas; en la de un mes o de un hogar grande, el 3 % ya es plata. El 3 % también tiene que quedar
# bien por encima de GAP_RELATIVO (1 %): un "ahorro" del tamaño del gap del solver es ruido, no un precio mejor.
DOS_SUPER_MAXIMO = 2                     # sucursales por compra (la enumeración de pares supone 2)
DOS_SUPER_MINUTOS_ENTRE = 10
DOS_SUPER_VECINAS = 4
DOS_SUPER_AHORRO_MINIMO_PCT = 3.0
DOS_SUPER_AHORRO_MINIMO_PESOS = 1000.0
RUTEO_SERVIDOR = "https://api.openrouteservice.org"
RUTEO_PERFIL = "foot-walking"
RUTEO_TIEMPO_ESPERA_S = 12

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
