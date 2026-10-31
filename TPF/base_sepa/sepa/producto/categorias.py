"""
Categoría de góndola de cada producto, como segunda opinión independiente de
las reglas de clasificación.

Los catálogos online de Jumbo, Disco y Vea categorizan ~100 mil productos
("Almacén > Desayuno y Merienda > Galletitas Saladas", "Limpieza > Insecticidas").
Cada producto de SEPA toma:

  - la categoría exacta, si su EAN está publicado en esos catálogos;
  - si no, la que predice un clasificador de texto (TF-IDF de n-gramas de
    caracteres y palabras + modelo lineal) entrenado con los nombres de esos
    productos y con las descripciones SEPA de los que tienen categoría exacta.
    En validación (15 % de los EAN reservados) acierta la categoría hoja en el
    93 % de los casos y el departamento en el 96 %. La confianza sale del margen
    del modelo (confianza()), no de repartir una probabilidad entre categorías:
    con >= 0,5 (90 % de los productos) acierta la hoja en el 97 % y el
    departamento en el 99 %; con >= 0,8 (85 %), en el 98 % y el 99,5 %.
    Si la marca arrastra la predicción a un departamento que no es comida (una
    marca de perfumería que también vende golosinas), vale la lectura sin la
    marca cuando es más segura.

La categoría se usa en clasificacion.py: define qué alimentos genéricos son
compatibles con el producto (referencia/categorias_web.csv) y descarta lo que
no es comida (limpieza, perfumería, bazar, mascotas...).
"""

from __future__ import annotations

import logging
import time

import joblib
import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier

from sepa import config as cfg
from sepa.fuentes import catalogos_web
from sepa.texto import nombre_coincide, normalizar

logger = logging.getLogger("sepa.producto.categorias")

RUTA_MODELO = cfg.DIR_WEB / "modelo_categorias.joblib"


# Departamentos que no son comida: basta con reconocer el departamento (se colapsan sus categorías y se limita
# la cantidad de ejemplos, que si no dominan el entrenamiento: hay 90 mil productos de bazar y textil).
NO_ALIMENTARIOS = {"Electro", "Hogar y textil", "Limpieza", "Perfumería", "Tiempo Libre", "Mascotas",
                   "Felices Fiestas", "Luces c/toma", "Mundo Bebe"}
MAX_EJEMPLOS_NO_ALIMENTARIOS = 3000
# Tope de ejemplos de la web por categoría de alimentos: con 400 nombres una categoría ya está bien descripta y
# el entrenamiento entra en la memoria de una máquina chica.
MAX_EJEMPLOS_POR_CATEGORIA = 400


def _categoria_entrenamiento(categoria: pd.Series) -> pd.Series:
    depto = categoria.str.split(" > ").str[0]
    colapsar = depto.isin(NO_ALIMENTARIOS) & ~categoria.str.startswith("Mundo Bebe > Alimentación")
    return categoria.where(~colapsar, depto)


def _textos_entrenamiento(web: pd.DataFrame, productos: pd.DataFrame) -> pd.DataFrame:
    """Nombre + marca de la web y descripciones SEPA (principal y alternativas) de los EAN con categoría."""
    web = web.assign(categoria=_categoria_entrenamiento(web["categoria"]))
    publicados = web[web["ean"].ne("")].drop_duplicates("ean").set_index("ean")
    cat, nombre_web = publicados["categoria"], publicados["nombre"] + " " + publicados["marca"]
    tope = np.where(web["categoria"].isin(NO_ALIMENTARIOS), MAX_EJEMPLOS_NO_ALIMENTARIOS, MAX_EJEMPLOS_POR_CATEGORIA)
    orden = web.sample(frac=1.0, random_state=0).groupby("categoria").cumcount()
    web = web[orden.reindex(web.index).to_numpy() < tope]
    w = pd.DataFrame({"texto": web["nombre"] + " " + web["marca"], "categoria": web["categoria"]})
    s = productos[productos["clave_producto"].isin(cat.index)]
    filas = []
    for clave, desc, alt, marca in zip(s["clave_producto"], s["descripcion"], s["descripciones_alternativas"],
                                       s["marca"].fillna("")):
        textos = [desc] + (alt.split(" | ") if isinstance(alt, str) else [])
        if not nombre_coincide(" ".join(textos) + " " + marca, nombre_web[clave]):
            continue   # EAN reusado por otro producto
        for t in textos:
            filas.append((f"{t} {marca}", cat[clave]))
    return pd.concat([w, pd.DataFrame(filas, columns=["texto", "categoria"])], ignore_index=True)


class Modelo:
    def __init__(self) -> None:
        self.caracteres = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True,
                                          max_features=60_000, dtype=np.float32)
        self.palabras = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True,
                                        max_features=30_000, dtype=np.float32)
        self.clf = SGDClassifier(loss="modified_huber", alpha=2e-6, max_iter=20, tol=1e-3, random_state=0)

    def _matriz(self, textos: pd.Series, entrenar: bool = False):
        t = textos.fillna("").map(normalizar)
        if entrenar:
            return hstack([self.caracteres.fit_transform(t), self.palabras.fit_transform(t)]).tocsr()
        return hstack([self.caracteres.transform(t), self.palabras.transform(t)]).tocsr()

    def entrenar(self, textos: pd.Series, categorias: pd.Series) -> "Modelo":
        self.clf.fit(self._matriz(textos, entrenar=True), categorias)
        # Los coeficientes en float32 ocupan la mitad.
        self.clf.coef_ = self.clf.coef_.astype(np.float32)
        return self

    def puntajes(self, textos: pd.Series, bloque: int = 20_000) -> tuple[np.ndarray, np.ndarray]:
        """Categoría de mayor puntaje (decision_function) y ese puntaje."""
        categorias, puntajes = [], []
        for i in range(0, len(textos), bloque):
            puntaje = self.clf.decision_function(self._matriz(textos.iloc[i:i + bloque]))
            categorias.append(self.clf.classes_[puntaje.argmax(axis=1)])
            puntajes.append(puntaje.max(axis=1))
        return np.concatenate(categorias), np.concatenate(puntajes)


def confianza(puntaje: np.ndarray) -> np.ndarray:
    """
    (puntaje recortado a [-1, 1] + 1) / 2: la estimación de modified_huber para la categoría ganadora sola.
    predict_proba la normaliza entre todas y, cuando el modelo no reconoce el producto (todos los puntajes
    negativos), le da 1,0 a la menos mala: "mortadela feteada" con una marca que nunca vio salía "Hogar y textil"
    con certeza total.
    """
    return (np.clip(puntaje, -1.0, 1.0) + 1.0) / 2.0


def _sin_marca(descripcion: str, marca: str) -> str:
    palabras = set(normalizar(marca).split())
    return " ".join(w for w in normalizar(descripcion).split() if w not in palabras)


def modelo(productos: pd.DataFrame, forzar: bool = False) -> Modelo:
    """Entrena el clasificador (o reutiliza el guardado si los catálogos no cambiaron)."""
    fuentes = sorted(cfg.DIR_WEB.glob("*.jsonl.gz"))
    if RUTA_MODELO.exists() and not forzar and all(RUTA_MODELO.stat().st_mtime > f.stat().st_mtime for f in fuentes):
        return joblib.load(RUTA_MODELO)
    inicio = time.time()
    web = catalogos_web.categorias()
    datos = _textos_entrenamiento(web, productos)
    m = Modelo().entrenar(datos["texto"], datos["categoria"])
    joblib.dump(m, RUTA_MODELO)
    logger.info("Clasificador de categorías: %d textos, %d categorías, %.0f s", len(datos),
                len(m.clf.classes_), time.time() - inicio)
    return m


def asignar(productos: pd.DataFrame) -> pd.DataFrame:
    """
    productos: producto, clave_producto, descripcion, descripciones_alternativas, marca.
    Devuelve producto, categoria_web, categoria_origen ('exacta' | 'predicha'), categoria_probabilidad.
    """
    web = catalogos_web.categorias()
    publicados = web[web["ean"].ne("")].drop_duplicates("ean").set_index("ean")
    m = modelo(productos)
    descripcion, marca = productos["descripcion"].fillna(""), productos["marca"].fillna("")
    texto = descripcion + " " + marca
    pred, puntaje = m.puntajes(texto)
    # Una marca que el modelo no conoce no puede sacar a un alimento de la comida: las marcas propias de las
    # cadenas solo aparecen en el entrenamiento en artículos de bazar, y "LECHE ULTRA ... CARREFOUR CLASSIC"
    # salía "Hogar y textil". Si la descripción sin la marca dice otra cosa con más seguridad, vale esa lectura.
    # En el resto se queda la que tiene la marca, que a veces informa ("BATATA COLORADA" de "VERDULERIA").
    pred_sm, puntaje_sm = m.puntajes(pd.Series([_sin_marca(d, mk) for d, mk in zip(descripcion, marca)],
                                               index=productos.index))
    usar = np.isin(pred, list(NO_ALIMENTARIOS)) & (puntaje_sm > puntaje)    # (el entrenamiento los colapsa al depto)
    pred, puntaje = np.where(usar, pred_sm, pred), np.where(usar, puntaje_sm, puntaje)
    out = pd.DataFrame({"producto": productos["producto"].to_numpy(),
                        "categoria_web": pred, "categoria_origen": "predicha",
                        "categoria_probabilidad": np.round(confianza(puntaje), 3)})
    conocida = productos["clave_producto"].map(publicados["categoria"])
    # Un EAN que la web publica con otro producto (cadenas que reusan códigos: una pintura con el EAN de un
    # caramelo) no aporta su categoría: se usa la predicha.
    nombre_web = productos["clave_producto"].map(publicados["nombre"] + " " + publicados["marca"])
    texto_sepa = texto + " " + productos["descripciones_alternativas"].fillna("")
    mismo = np.array([isinstance(w, str) and nombre_coincide(s, w) for s, w in zip(texto_sepa, nombre_web)])
    tiene = conocida.notna().to_numpy() & mismo
    logger.info("Categoría publicada: %d productos (%d EAN publicados con otro nombre se ignoran)", tiene.sum(),
                (conocida.notna().to_numpy() & ~mismo).sum())
    out.loc[tiene, "categoria_web"] = conocida[tiene].to_numpy()
    out.loc[tiene, "categoria_origen"] = "exacta"
    out.loc[tiene, "categoria_probabilidad"] = 1.0
    return out
