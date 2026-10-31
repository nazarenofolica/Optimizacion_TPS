"""
Clasificación de cada producto en un alimento genérico del catálogo
referencia/alimentos.csv (pollo entero, nalga, banana, leche entera, galletitas
de agua... ~200 en total), que define su categoría y subcategoría.

SEPA no trae categoría: solo la descripción que escribe cada cadena. Cada
alimento del catálogo tiene una regla "incluir" y una "excluir" (expresiones
regulares sobre la descripción en mayúsculas, sin tildes ni signos) y gana la
primera regla que coincide: por eso lo compuesto va antes que el ingrediente
("yogur de banana" es yogur, "medallones de pollo" no es pollo, "vino Cordero"
es vino). Además:

  - se descarta lo que no es comida aunque nombre un alimento (limpieza,
    perfumería, mascotas, bazar: "shampoo manzana", "lavavajillas limón");
  - en los rubros frescos (verduras, frutas, carnes, pollo) un producto
    procesado no cuenta ("papas tubo", "cebolla en escamas", "nuggets");
  - en frutas y verduras, un producto con código de barras tiene que mostrar
    alguna señal de fresco ("x kg", granel, bandeja, unidad) o ser una
    descripción corta: "naranja" también es un color ("ojota naranja");
  - si la descripción principal no alcanza, se prueba con las de otras
    cadenas para el mismo código, siempre que la principal no contradiga al
    alimento.
"""

from __future__ import annotations

import re
import warnings

import numpy as np
import pandas as pd

from sepa import config as cfg
from sepa.texto import normalizar

# Las reglas usan grupos (A|B); pandas avisa que no se extraen, y no hace falta.
warnings.filterwarnings("ignore", "This pattern is interpreted as a regular expression")

# Lo que no es comida, aunque mencione un alimento ("shampoo de manzana", "alimento para perros pollo").
NO_ALIMENTO = re.compile(
    r"\b(?:(PARA|P) (PERROS?|GATOS?)|(SNACKS?|BOCADITOS?|GALLETAS?|ALIM\w*|HUESOS?) (P |PARA )?(PERROS?|GATOS?)|(PERROS?|GATOS?) (ADULTOS?|CACHORROS?|RAZA|SENIOR)|(PARA |DE )MASCOTAS?|MASCOTAS? (ADULTOS?|CACHORROS?)|CANINO|FELINO|CACHORRO|PEDIGREE|WHISKAS|DOG ?CHOW|CAT ?CHOW|PURINA|EUKANUBA|"
    r"ROYAL CANIN|DOGUI|GATI|GATITOS?|FELIX|CACHORROS?|SIEGER|VITAL ?CAN|OLD PRINCE|EXCELLENT|BALANCEADO|ALPISTE|PAJAROS?|BIRD|PECES|REPELENTE|"
    # "Colonia Caroya" y "Colonia Las Liebres" son un salame y un vino; "panal de membrillo", un dulce
    r"SHAMPOO|ACONDICIONADOR|JABON|DETERGENTE|LAVANDINA|DESODORANTE|ANTITRANSPIRANTE|PERFUMES?|COLONIA(?! (CAROYA|LAS LIEBRES|SUIZA|ESPERANZA|TIROLESA))|"
    r"TOALLITAS?|PANALES|PANAL(?! (DE )?(MEMBRILLO|VAINILLA|CHOCOLATE|COCO|MIEL|DULCE))|PROTECTOR (DIARIO|SOLAR)|TOALLAS?|MAQUILLAJE|LABIAL|ESMALTE|TINTURA|TINTA (PARA|DE IMPRESORA)|CARTUCHO|CEPILLO|"
    r"PASTA DENTAL|DENTIFRIC\w*|ENJUAGUE|AFEITAR|DEPILA\w*|INSECTICIDA|LIMPIADOR|DESINFECTANTE|SUAVIZANTE|"
    r"QUITAMANCHAS|ESPONJA|REJILLA|ESCOBA|SERVILLETAS?|PAPEL HIGIENICO|ROLLO DE COCINA|PAPEL (ALUMINIO|MANTECA)|"
    r"VELAS?|SAHUMERIO|AROMATIZANTES? (DE |PARA )?(AMBIENTES?|AUTO|ROPA|TEXTIL)|DIFUSOR|PILAS?|LAMPARA|CARGADOR|AURICULAR|(?<!PASTILLAS )(?<!CHICLES )(?<!CARAMELOS )JUGUETES?|MACETA|FERTILIZANTE|"
    # un aerosol es aromatizante ("AEROSOL PAPAYA") salvo el rocío vegetal y la crema para cocinar
    r"^(?!.*\b(ACEITE|ROCIO|CREMA|COCINA|VEGETAL|GIRASOL|OLIVA|CHANTILLY|MANTECA|DESMOLDANTE|LIRA|COCO)\b).*\bAEROSOL|"
    r"CARBON (VEGETAL )?(X |DE )?\d+ ?KG|BOLSA (DE )?(CARBON|LENA)|(CARBON|LENA) (DE )?(QUEBRACHO|ESPINILLO|ALGARROBO)|LENA (X )?\d+ ?KG|ENCENDEDOR|FOSFOROS?|CIGARRILLOS?|TABACO|(JUEGO|SET) DE CUBIERTOS|CUBIERTOS (DE )?(ACERO|MESA|X \d)|SARTEN|CACEROLA|TUPPER|TAPER|"
    r"CREMA (CORPORAL|FACIAL|DE MANOS|HIDRATANTE|ANTIARRUGAS|DE PEINAR|PARA PEINAR)|LOCION|GEL (DE DUCHA|CAPILAR)|"
    r"ALCOHOL EN GEL|AGUA OXIGENADA|ALGODON|CURITAS?|PRESERVATIVOS?|TAMPON(ES)?|BRONCEADOR|EXFOLIANTE|"
    r"MASCARILLA|SERUM|TALCO|QUITAESMALTE|DESMAQUILLANTE|SPRAY PARA|LUSTRA\w*|CERA PARA|PINTURA|LATEX|"
    r"ADHESIVO|PEGAMENTO|CUADERNO|LAPIZ|LAPICERA|REMERAS?|PANTALON|ZAPATILLAS?|MEDIAS DE|PELUCHE|DISFRAZ|"
    r"SUPLEMENTOS?|COMPRIMIDOS|CAPSULAS BLANDAS|VITAMINAS EN|MEMBRANA|AIRPERF|MUFFINERA\w*|FEEL Y SMELL|"
    r"CARTEL(ES)?|SAHU\w*|CAPILAR|MARY STUART|FREESUR|LECHE (DE LIMPIEZA|DESMAQUILLANTE|CORPORAL|HIDRATANTE)|CORTADOR(ES)?|"
    # bazar, hogar, textil, librería, electrónica: sobre todo los que mencionan un alimento
    # ("cuchara mango madera", "lavavajillas limón", "copa agua", "lego cerdo")
    r"CUCHARAS?|CUCHARITAS?|CUCHARON|TENEDOR(ES)?|UTENSILIOS?|OLLAS?|PELADOR|PELAPAPAS|RODILLO|PROVOLETERA|"
    r"ESPATULA|ESPUMADERA|CUCHILL(A|AS|O|OS)(?! DE PALO)|COLADOR|RALLADOR|TABLAS?|BOWL|MOLDES? (PARA|PAN|CON TAPA|DE SILICONA|SILICONA|DESMONTABLE|DE ALUMINIO|ALUMINIO|ANTIADHERENTE)|ASADERA|WOK (ANTIADHERENTE|DE ACERO|DE HIERRO|\d+ ?CM)|TERMOS?|"
    r"CESTA|CANASTA|ORGANIZADOR|ESCALERA|BOLSOS?|CUADROS?|ADORNOS?|DECO(?! PREMIUM)|REPUESTO|CUBIERTERO|COLCHON (DE )?(INFLABLE|ESPUMA|RESORTES|\d PLAZAS?)|COLCHONETA|"
    r"SOMMIER|ALMOHADAS?|ALMOHADON\w*|ACOLCHADO|SABANAS?|CORTINAS?|MANOPLA|JUMPER|CAMISAS?|BERMUDA|CHALECO|BUZO|CAMPERA|"
    r"SHORT|JEAN|WIDE LEG|CORDEROY|MOCHILA|RINONERA|CONJUNTO|PEINES?|ASPIRADORA|DIFU\w*|DESODOR\w*|"
    r"GLADE|SAPHIRUS|LYSOL|PROCENEX|CIF|ASURIN|RESIDUOS|INODOROS?|DETERGEN\w*|DET|DESENG\w*|ANTIGRASA|"
    r"ANTIHUMEDAD|MAGISTRAL|LIMPIAVIDRIOS|LAVAV\w*|LAVAJILLA\w*|LIMP|JAB|AROMATIZADOR\w*|AMBIENTAL|"
    r"AUTOMATIC\w*|VELON|FRUCTIS|SEDAL|DERMAGLOS|NEUTROGENA|NTG|NIVEA|MICELAR|KERATINA|COLORACION|SEMIPERM|"
    r"EDP|EDT|HILO DENT\w*|FLOSS\w*|CREMA DENTAL|ACOND|CORTA PIZZA|PIZZA MAKER|SET DE TE|PLATSET|COPAS? (DE )?(VINO|VIDRIO|CRISTAL|CHAMPAGNE|FLAUTA|TRAGO|CERVEZA)|(JUEGO|SET) DE COPAS|"
    r"JUEGOS? DE AGUA|FUENTE DE AGUA|SELLADOR|SILICONA|AUTOADHESIVO|ANTICORROSIVO|REFRIGERANTE|LANZADOR|"
    r"PELOTAS?|MUNECOS?(?! REBELDE)|LEGO|PLAYSET|STICKERS|COLOREA|COLOREO|LIBROS?|LB|"
    r"TEX|HG|REGLA|FIBRON|MARCADOR|CRAYON|PLASTILINA|SQUISHY|MAQUINA (DE|PARA)|PURIFICADOR|CAFETERA|"
    r"FILTROS? (DE |PARA )?(CAFE|AGUA|AIRE|ACEITE|PILETA)|RECARGABLES?|REUTILIZABLES?|PAVA ELECTRICA|LICUADORA|BATIDORA|TOSTADORA|HORNO (DE )?MICROONDAS|MICROONDAS \d+ ?(L|LTS|LITROS)|HELADERA|"
    r"CELULAR|SAMSUNG|MOTOROLA|LIMAS? (DE UNAS|PARA UNAS|BANANA|JESSAMY|TAO)|HASBRO|PYREX|FUENTE|VERTEDOR|JARRA|PETS|VALIJA|PISA ?PAPAS?|GUIRLANDA|FRANELAS?|AERO|ENJ|MASK|MICROFIBRA|TRAPOS?|PANOS?|AFEIT\w*|PLUME\w*|TIJERAS?|SAHUM\w*|ENTONADOR|COLORIN|BIDON (TERMICO|VACIO|PLASTICO|DE PLASTICO)|RASQUETA|PISAPAPAS|DEO|PA COLOR|PLANTIN|FLORERO|FLORES (ARTIFICIALES|SECAS|DE TELA|PLASTICAS)|PLANTAS? (DE INTERIOR|ARTIFICIAL\w*)|BAZAR|"
    # Encontrados al revisar los productos más baratos de cada alimento (optimizacion/): limpieza,
    # automotor, mascotas, suplementos y bazar que mencionan una fruta, un pescado o un queso.
    r"REVIVIDOR|REVIGAL|ACONDICIONAD\w*|ANTI GRASA|MUSCULO|MR MUSCUL\w*|SANITARIO|ABSORSOL|"
    r"SALES MINERALES|SALES DE BANO|QUARTZ|LUBRICANTE|\d+W ?\d+|WHI|ESTERIL|PALITA METAL|FOAMY|COLAGENO HIDROLIZADO|"
    r"CREATIN\w*|HORNO DE PAN|BLUESKY|L LIQ|BOTELLA CON|TAPA PLASTICA|SISTEMA RECT|TEMP CREAMY|TEMPTATIONS|"
    r"AHUMADOR\w*|HERMET\w*|BLEM|LIMPIA PISOS|TAPA ROSCA|"
    # Encontrados al revisar los que el clasificador de góndola no reconoce y una regla toma por comida: un
    # gazebo azul no es queso azul, una manta ("MANT SHERP 120X150CM") no es manteca, un aceite 20W 50 no es
    # de girasol, una silla "Milo" no es cacao.
    r"ELAION|LUBRI\w*|FREIDORA\w*|JOHNSONS?|JHONSONS?|HORNILLO|DOBLE COCIDO|MICELA\w*|MORDILLO|VOGUE|POLVO COMPACTO|"
    r"SILLON\w*|SILLAS?|REPOSERA\w*|GAZEBO|SOMBRILLA|PARASOL|CORTADORA\w*|ESPEJO\w*|SECADOR\w*|ESCOBILLA|"
    r"FELPUDO\w*|LIJAS?|HEBILLA\w*|CHINELA\w*|PANTUFLA\w*|OJOTA\w*|VEHICULOS?|MOTOCICLETA|FUNDAS?|ESQUELETO|PALLET|"
    r"REPASADOR\w*|REAPASADOR\w*|MAMADERAS?|MAMADER|TETINAS?|CHUPETES?|PACIFIER|BATIDOR\w*|SALIDA (DE )?BANO|"
    r"PERCHAS?|PERCHITAS?|MASCARAS?|LIPIKAR|UREA\d*|ARENA|BENTONITA|MARTILLO|TULIPAN(ES)?|PEONIAS?|RAMO DE|MUG|"
    r"CAMARAS?|INSTAX|FUJIFILM|VINCHAS?|PARKA|EVERLAST|BURBUJERO|STYLING|MODELADORA|TORNILLOS?|SOPAPA|ESQUINERO|"
    r"TOBOGAN|PORTAVELAS?|TOALL|BANO DE LUZ|DETER|CAMAS?|CORTA ?QUESO\w*|JUEGO DE MESA|LED|\d+ ?W|"
    r"BOLIGRAFO\w*|PENDRIVE|ANTIPARRA\w*|ABRELATA\w*|CORREA|PULSERA\w*|BULBOS?|BRILLOSPRAY|LAUNDRY|"
    r"PLOTEO|GUANTES?|CARPETA|CHINCHES|ETIQUETAS ESCOLARES|PUNTAL|SKATEBOARD|BLUSAS?|VESTIDOS?|MONOPATIN|"
    r"BOLSA (DE )?REGALO|ROBOT\w*|COLGARTE|KERAMIKA|CERAMIC\w*|NECESER|AGITADOR(ES)?|TRAGO LARG\w*|SETX\d+|"
    r"AROM|DENT ?STICK\w*|DENTASTIX|HARINA DE HUESO|AMPK|PLASUTIL|PORTA ?GALLET\w*|SERVER|VASELIN\w*|REVLON|RUBOR|LENOVO|"
    r"XIAOMI|HUAWEI|NOTEBOOK|TABLET|HUGGIES|PAMPERS|BABYSEC|VAITA|GRAFITAD\w*|\d+X\d+X\d+|"
    # el envase retornable que se cobra aparte ("ENVASE STELLA ARTOIS X 985 CC")
    r"^ENVASE)\b"
)

# Comidas listas que no son un alimento de la canasta, como las góndolas "Sandwiches de Miga" y "Rotisería"
# (fuera de alcance en referencia/categorias_web.csv): sin esto, "SAND. DE MILANESA" sería una milanesa y
# "MILA CARN PAP O ENS" (milanesa con papas o ensalada), carne.
COMIDA_PREPARADA = re.compile(
    r"\b(?:SANDWICH(ES)? (DE |C |CON )?(MIGA|JAMON|J Y Q|JYQ|QUESO|MILANESA|POLLO|LOMITO|ATUN|SALAME|TERNERA|"
    r"VEGETAL\w*|PALMITO|LEBERWURST|PAVITA|ROAST|BONDIOLA|MORTADELA|TRIPLES?|SIMPLES?|COMPLETO|ESPECIAL|MIXTO|"
    r"BAGUETTIN)|SAND (DE|BAGUETTIN)|SIMPLES DE|TRIPLES? (DE|ESPEC\w*)|PEBETE DE (JAMON|SALAME|QUESO|MILANESA|J ?CRUDO|"
    r"J Y Q|JYQ)|BAGUET\w* (DE |C )?(JAMON|J Y Q|JYQ|SALAME|QUESO|MILANESA|POLLO|TERNERA|LOMITO|ATUN|HUMMUS|CAESAR|"
    r"SUPREM\w*|J ?CRUDO)|WRAPS? (INTEGRAL(ES)? )?(CAESAR|VEGETARIANO|POLLO|TERNERA|JAMON|ATUN|DE (POLLO|CARNE|JAMON|ATUN|VEGETALES))|"
    r"SC WRAP|PAP O ENS|PA O ENS|C ?PAP S MEN|MILA\w* .*\b(S ?MENU|SM MENU|SMART MENU)|"
    r"^(SC |HP )?(MILA\w*|HAMB\w*|SUPREMA|BIFE|POLLO|PATAMUSLO|PATA|CARNE|PESC\w*|WRAP|TERN\w*|NUGGETS?) .*"
    r"\b(CON|C|Y) PAPAS|"
    r"(PECETO|POLLO|MATAMBRE|NALGA|LOMO|CERDO|CARNE|PESCADO|MERLUZA|BONDIOLA|LENGUA|PATAMUSLO|SUPREMA) .*"
    r"A LA (CRIOLLA|CAZADORA|PROVENZAL|PORTUGUESA|VINAGRETA)|COMIDAS? (FRIAS?|CALIENT\w*)|VITTEL TONNE|"
    r"^(SC |HP )?(BIFE|POLLO|CARNE|MILA\w*|CERD\w*|TERN\w*|PESC\w*|SALT\w*) .*\b(C|CON|CN) (ARROZ|ARR)|BIFE CRIOLL\w*|"
    r"ENSALADA\b.*\b(CON|C|Y) (PAVITA|POLLO|JAMON|QUESO|HUEVOS?)|ENSALADA (CAESAR|CESAR|RUSA)|BOCADITOS? DE HUEVO)\b"
)


def fuera_de_canasta(texto_normalizado: str) -> bool:
    """No es comida, o es una comida preparada que no es un alimento de la canasta."""
    return bool(NO_ALIMENTO.search(texto_normalizado) or COMIDA_PREPARADA.search(texto_normalizado))


# Rubros de alimentos frescos: un producto procesado que menciona el alimento ("papas tubo cheddar",
# "nuggets de pollo", "cebolla en escamas") no cuenta como el alimento fresco.
RUBROS_FRESCOS = {"Verduras", "Frutas", "Carne vacuna", "Cerdo", "Pollo", "Achuras", "Otras carnes"}
PROCESADO = re.compile(
    r"\b(?:TUBO|SNACKS?|CHIPS|CROQ\w*|CHEDDAR|SABOR|SAB|FRITAS?|FRIT|PREFRIT\w*|HORNEABLES?|AIR FRYER|ONDEADAS?|"
    r"RUSTIC\w*|DESHIDRAT\w*|ESCAMAS|POLVO|CINTITAS|DETOX|JUGOS?(?!.*\b(X ?KG|KGM?|COSECHA|BSA)\b)|COLESLAW|PURE|"
    r"SOPA|SALSA|ADEREZO|CONDIMENTO|"
    r"ADOBO|NUGG\w*|MEDAL\w*|MILANE\w*|SADINESA|PALITOS?|FORM|AJINOMEN|RELLENO|ROSTIZAD\w*|AL VERDEO|CASERITOS|"
    r"FELPA|CON PAPAS?|O ENS|TACOS|EMPANAD\w*|TARTA|PIZZA|CONSERVA|ALMIBAR|MERMELADA|HELADO|YOGUR|ESCABECHE|"
    r"VINAGRE|PICKLES?|DESECAD\w*|BOCADITOS?|BARRITAS?|CEREAL|GALLETITAS?|BUDIN|ALFAJOR|CHOCOLATE|BANAD\w*|"
    r"GOURMET|CINTAS|BASTONES|LISTO|LISTA|COCID\w*|HERVID\w*|AL VAPOR|TAFI|SLICES|HAMBURG\w*|JARRO|PASTEL|"
    r"ESPANOLAS|HASSELBACK|ONDEADAS?|J|GIO|CHOCOMANI|PANC|POUCH|ZUMMY|NUTRIBABY|ALIM|PORCION|DISC|TOMATETINA|"
    r"CONCENTRADO|PEL|LAT|LATA|FCO|DAUCY|EN RODAJAS|MERMEL\w*|BIZCOCH\w*|ENERG\w*|CRUSH|HELA|PAST|BC|PF|"
    r"REINA MORA|CUBOS|GLASE|SMUDIS|PDT|RINDE2|TIRAS|ARO|AROS|GYOZAS?|HUMMUS|PASTA DE|CHUTNEY|BOC|PANQUEQUES?|"
    r"WOK|PEBETE|SANDWICH|CRISPY|CONDIMENT\w*)\b"
)
# Frutas y verduras: "naranja", "mango", "granada" también son colores, aromas y marcas ("ojota naranja",
# "tintura granada", "creatina sabor naranja"). Un producto con código de barras entra solo si muestra
# alguna señal de producto fresco o si la descripción es corta (el nombre del alimento y poco más).
RUBROS_FRUTIHORTICOLAS = {"Verduras", "Frutas"}
SENAL_FRESCO = re.compile(
    r"\b(?:X ?KG|XKG|KG|KGM|KGR|KILO|GRANEL|X UNI|X UNIDAD|X UN|X UD|UNIDAD|BSA|BOLSA|BOLSITA|MALLA|BANDEJA|BJA|"
    r"ATADO|PAQUETE|PAQ|COMERCIAL|ELEGIDA|SELECCION\w*|DE CAMPO|ORGANIC\w*|HUELLA NATURAL|COSECHA|ESPECIAL|"
    r"HIDRO\w*|LAVADA|T|PAX|PUX|SAX|BEX|FRESC\w*)\b|\bX ?\d+ ?(?:G|GR|GRS|GRM|KG|KGM|KGR)\b"
)


# En carnes alcanza con un peso ("bife ancho 1 kg"); en frutas y verduras no ("creatina naranja 378 g").
PESO_EN_TEXTO = re.compile(r"\b\d+ ?(?:G|GR|GRS|GRM|KG|KGM|KGR)\b")


def parece_fresco(texto_normalizado: str, acepta_peso: bool = False) -> bool:
    return (bool(SENAL_FRESCO.search(texto_normalizado)) or len(texto_normalizado.split()) <= 3
            or (acepta_peso and bool(PESO_EN_TEXTO.search(texto_normalizado))))


# Un producto que se vende en mililitros no es un polvo: pasa a su par líquido (o, si no tiene, se excluye).
POLVO_A_LIQUIDO = {"jugo_polvo": "jugo", "leche_infantil": "leche_infantil_liquida", "leche_polvo": "leche_entera",
                   "leche_polvo_descremada": "leche_descremada", "edulcorante": "edulcorante_liquido",
                   "cacao_bebida": "leche_chocolatada", "gelatina": None, "premezcla": None}
# Y una leche que se vende en gramos es leche en polvo; un "jugo" de pocos gramos, un sobre de jugo en polvo
# (hay jugos listos que se venden por peso: el smoothie de 450 g).
LIQUIDO_A_POLVO = {"leche_entera": ("leche_polvo", np.inf), "leche_descremada": ("leche_polvo_descremada", np.inf),
                   "leche_infantil_liquida": ("leche_infantil", np.inf), "jugo": ("jugo_polvo", 200.0)}


def corregir_forma(alimento: pd.Series, contenido: pd.Series, unidad_contenido: pd.Series
                   ) -> tuple[pd.Series, pd.Series]:
    """(alimento corregido, motivo de exclusión) para los polvos que se venden en mililitros y viceversa."""
    liquido = unidad_contenido.eq("ml") & alimento.isin(list(POLVO_A_LIQUIDO))
    nuevo = alimento.where(~liquido, alimento.map(POLVO_A_LIQUIDO))
    tope = alimento.map({a: t for a, (_, t) in LIQUIDO_A_POLVO.items()})
    polvo = unidad_contenido.eq("g") & (contenido <= tope).fillna(False)
    nuevo = nuevo.where(~polvo, alimento.map({a: p for a, (p, _) in LIQUIDO_A_POLVO.items()}))
    motivo = pd.Series(np.where(liquido & nuevo.isna(), "se vende en mililitros pero es un polvo", ""),
                       index=alimento.index)
    return nuevo, motivo


def cargar_catalogo() -> pd.DataFrame:
    cat = pd.read_csv(cfg.RUTA_ALIMENTOS, sep=";", dtype=str, encoding="utf-8-sig", keep_default_na=False)
    for col in ("parte_comestible", "densidad_g_ml"):
        cat[col] = pd.to_numeric(cat[col]).fillna(1.0)
    for col in ("peso_unidad_g", "porcion"):
        cat[col] = pd.to_numeric(cat[col], errors="coerce")
    cat["fdc_id"] = pd.to_numeric(cat["fdc_id"], errors="coerce").astype("Int64")
    cat["preferir_off"] = cat["preferir_off"].str.lower().isin(["true", "1", "si"])
    return cat


def clasificar(textos: pd.Series, catalogo: pd.DataFrame) -> pd.Series:
    """id del alimento para cada texto (o vacío). Gana la primera regla del catálogo que coincide."""
    norm = textos.fillna("").map(normalizar).to_numpy(dtype=object)
    resultado = np.full(len(norm), None, dtype=object)
    pendiente = np.array([t != "" and not fuera_de_canasta(t) for t in norm], dtype=bool)
    procesado = np.array([bool(PROCESADO.search(t)) for t in norm], dtype=bool)
    for fila in catalogo.itertuples():
        posiciones = np.flatnonzero(pendiente)
        if fila.rubro in RUBROS_FRESCOS:
            posiciones = posiciones[~procesado[posiciones]]
        if len(posiciones) == 0:
            continue
        incluir = re.compile(fila.incluir)
        excluir = re.compile(fila.excluir) if fila.excluir else None
        for i in posiciones:
            if incluir.search(norm[i]) and not (excluir and excluir.search(norm[i])):
                resultado[i] = fila.id
                pendiente[i] = False
    return pd.Series(resultado, index=textos.index, dtype="object")


def clasificar_productos(df: pd.DataFrame, catalogo: pd.DataFrame, exigir_fresco: bool = True) -> pd.Series:
    """
    df: descripcion, descripciones_alternativas, es_ean. Clasifica por la descripción principal y, si no
    alcanza, por las de las otras cadenas. Con exigir_fresco, un producto con código de barras clasificado
    como fresco tiene que mostrar alguna señal de serlo (no hace falta si la categoría de góndola lo respalda).
    """
    alimento = clasificar(df["descripcion"], catalogo)
    no_comida = df["descripcion"].fillna("").map(lambda t: fuera_de_canasta(normalizar(t)))
    falta = alimento.isna() & df["descripciones_alternativas"].notna() & ~no_comida
    if falta.any():
        alternativas = df.loc[falta, "descripciones_alternativas"].str.split(" | ", regex=False).explode()
        por_alt = clasificar(alternativas, catalogo).dropna()
        por_alt = por_alt.groupby(level=0).agg(lambda s: s.mode().iloc[0])
        # La descripción principal no puede contradecir al alimento elegido ("chocolate ... leche" no es leche).
        excluir = catalogo.set_index("id")["excluir"]
        rubro = catalogo.set_index("id")["rubro"]
        principal = df.loc[por_alt.index, "descripcion"].map(normalizar)
        valido = [not (excluir[a] and re.search(excluir[a], t))
                  and not (rubro[a] in RUBROS_FRESCOS and PROCESADO.search(t))
                  for a, t in zip(por_alt, principal)]
        alimento.loc[por_alt[valido].index] = por_alt[valido]

    if not exigir_fresco:
        return alimento
    rubro = alimento.map(catalogo.set_index("id")["rubro"])
    dudoso = rubro.isin(RUBROS_FRESCOS) & df["es_ean"]
    textos = df.loc[dudoso, "descripcion"].fillna("").map(normalizar)
    acepta_peso = ~rubro[dudoso].isin(RUBROS_FRUTIHORTICOLAS)
    sin_senal = ~pd.Series([parece_fresco(t, a) for t, a in zip(textos, acepta_peso)], index=textos.index, dtype=bool)
    alimento.loc[sin_senal[sin_senal].index] = None
    return alimento


# ============================================================
# CATEGORÍA DE GÓNDOLA COMO SEGUNDA OPINIÓN
# ============================================================

def cargar_categorias() -> list[tuple[str, frozenset[str] | None, str]]:
    """referencia/categorias_web.csv -> [(prefijo, alimentos compatibles o None si está fuera de alcance, predeterminado)]."""
    t = pd.read_csv(cfg.RUTA_CATEGORIAS_WEB, sep=";", dtype=str, comment="#", encoding="utf-8-sig",
                    keep_default_na=False)
    reglas = []
    for prefijo, alimentos, defecto in t[["categoria_web", "alimentos", "predeterminado"]].itertuples(index=False):
        compatibles = (None if alimentos.strip() == "-"
                       else frozenset(a.strip() for a in alimentos.split("|") if a.strip()))
        reglas.append((prefijo.strip(), compatibles, defecto.strip()))
    return sorted(reglas, key=lambda r: -len(r[0]))   # el prefijo más largo primero


def compatibilidad(categoria: str, reglas) -> tuple[str, frozenset[str] | None, str]:
    """(estado, alimentos compatibles, predeterminado); estado: fuera, compatibles o sin_mapa."""
    if isinstance(categoria, str):
        for prefijo, compatibles, defecto in reglas:
            if categoria == prefijo or categoria.startswith(prefijo + " >"):
                return ("fuera", None, "") if compatibles is None else ("compatibles", compatibles, defecto)
    return "sin_mapa", None, ""


def clasificar_con_categorias(df: pd.DataFrame, catalogo: pd.DataFrame, reglas_categoria) -> pd.DataFrame:
    """
    df: descripcion, descripciones_alternativas, es_ean, categoria_web, categoria_origen, categoria_probabilidad.
    Combina las reglas de texto con la categoría de góndola (exacta o predicha). Devuelve, por fila,
    alimento_id, clasificacion_origen y motivo_exclusion (por qué un producto que parecía comida no se clasifica):

      - categoría fuera de alcance (limpieza, perfumería...) y confiable: no es comida;
      - regla compatible con la categoría: se confirma;
      - regla incompatible con una categoría confiable: se reclasifica con las reglas acotadas a los alimentos
        compatibles; si ninguna aplica, una categoría publicada impone su alimento predeterminado y una predicha
        no alcanza para contradecir a la regla ("BIFE DE CHORIZO" no es un chorizo aunque el modelo lo crea);
      - regla incompatible con una categoría de confianza media: se excluye por dudosa;
      - sin regla: se clasifica con las reglas acotadas a la categoría (y su predeterminado si es confiable);
      - categoría poco confiable o sin mapa: vale la regla.

    Nada se pierde sin motivo: una comida preparada (sándwich, plato de rotisería) queda fuera de alcance y lo
    que la góndola dice que es comida pero ninguna regla reconoce queda registrado como tal.
    """
    regla = clasificar_productos(df, catalogo)
    prob = df["categoria_probabilidad"].fillna(0)
    exacta = df["categoria_origen"].eq("exacta")
    confiable = exacta | (prob >= cfg.CATEGORIA_PROB_FUERTE)
    media = ~confiable & (prob >= cfg.CATEGORIA_PROB_MEDIA)
    info = [compatibilidad(c, reglas_categoria) for c in df["categoria_web"]]
    estado = pd.Series([i[0] for i in info], index=df.index)
    compatibles = pd.Series([i[1] for i in info], index=df.index, dtype=object)
    defecto = pd.Series([i[2] for i in info], index=df.index)

    alimento = regla.copy()
    origen = pd.Series(np.where(regla.notna(), "reglas", ""), index=df.index, dtype=object)
    motivo = pd.Series("", index=df.index, dtype=object)

    fuera = estado.eq("fuera")
    for mascara, texto in ((fuera & confiable, "categoría de góndola no alimentaria"),
                           (fuera & media & regla.notna(), "categoría probable no alimentaria")):
        motivo[mascara & alimento.notna()] = texto
        alimento[mascara] = None
        origen[mascara] = ""

    con_mapa = estado.eq("compatibles") & (confiable | media)
    coincide = pd.Series([isinstance(r, str) and c is not None and r in c for r, c in zip(regla, compatibles)],
                         index=df.index)
    origen[con_mapa & coincide] = "reglas y categoría"
    conflicto = con_mapa & regla.notna() & ~coincide
    alimento[conflicto & media] = None
    motivo[conflicto & media] = "reglas y categoría de góndola no coinciden"
    origen[conflicto & media] = ""

    # Reglas acotadas a los alimentos compatibles con la categoría (sin exigir señal de fresco: la categoría
    # ya respalda que es un fresco). Lo que la descripción dice que no es comida no se rescata por la categoría.
    no_comida = df["descripcion"].fillna("").map(lambda t: fuera_de_canasta(normalizar(t)))
    acotar = con_mapa & ~no_comida & (regla.isna() | (conflicto & confiable))
    ids = set(catalogo["id"])
    excluir = catalogo.set_index("id")["excluir"]

    def excluido(alimento_id: str, descripcion: str) -> bool:
        """La regla del alimento lo excluye a propósito ("HUEVO EN POLVO" no es huevo): la góndola no lo impone."""
        patron = excluir.get(alimento_id, "")
        return bool(patron) and bool(re.search(patron, normalizar(descripcion)))

    for permitidos, grupo in df[acotar].groupby(compatibles[acotar].map(lambda c: tuple(sorted(c)))):
        sub = catalogo[catalogo["id"].isin(permitidos)]
        acotado = (clasificar_productos(grupo, sub, exigir_fresco=False) if len(sub)
                   else pd.Series(None, index=grupo.index, dtype=object))
        for i, a in acotado.items():
            if isinstance(a, str):
                alimento[i], origen[i], motivo[i] = a, "categoría y reglas acotadas", ""
            elif (defecto[i] in ids and confiable[i] and (exacta[i] or not isinstance(regla[i], str))
                  and not excluido(defecto[i], df.at[i, "descripcion"])):
                alimento[i], origen[i], motivo[i] = defecto[i], "categoría (alimento predeterminado)", ""
            elif isinstance(regla[i], str) and not exacta[i]:
                alimento[i], origen[i], motivo[i] = regla[i], "reglas", ""
            elif isinstance(regla[i], str):
                alimento[i], origen[i] = None, ""
                motivo[i] = "reglas y categoría de góndola no coinciden"

    preparada = df["descripcion"].fillna("").map(lambda t: bool(COMIDA_PREPARADA.search(normalizar(t))))
    sin_motivo = alimento.isna() & motivo.eq("")
    motivo[sin_motivo & preparada] = "comida preparada fuera de alcance (sándwich o plato de rotisería)"
    motivo[sin_motivo & ~preparada & con_mapa & ~no_comida] = \
        "góndola de comida, pero la descripción no identifica el alimento"
    return pd.DataFrame({"alimento_id": alimento, "clasificacion_origen": origen, "motivo_exclusion": motivo})
