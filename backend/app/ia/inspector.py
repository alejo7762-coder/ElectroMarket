"""
Inspector de estado con IA (modelo local, sin servicios externos).

Qué hace con una publicación (título, descripción, defectos y checklist):

1. Clasificación (aprendizaje automático): un modelo de regresión logística
   sobre TF-IDF de palabras y fragmentos de palabras predice la condición
   real del producto (COMO_NUEVO, BUENO o ACEPTABLE) y su confianza.
2. Explicación: muestra las expresiones del texto que más pesaron en la
   predicción, para que el resultado se pueda entender y discutir.
3. Coherencia: compara el texto con el checklist del vendedor y con la
   condición declarada. Si encuentra contradicciones, el resultado es
   REVISAR y el producto no puede quedar como VERIFICADO.

El modelo se entrena con app/ia/datos/entrenamiento.csv y se guarda en
app/ia/modelo/. Si el archivo no existe o fue creado con otra versión de
scikit-learn, se vuelve a entrenar automáticamente (tarda un par de segundos).
"""

import csv
import logging
import re
import threading
import unicodedata
from pathlib import Path

import joblib
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

logger = logging.getLogger("electromarket.ia")

VERSION_MODELO = "inspector-estado-1.0"
CONDICIONES = ("ACEPTABLE", "BUENO", "COMO_NUEVO")  # de peor a mejor
TEXTO_CONDICION = {"COMO_NUEVO": "Como nuevo", "BUENO": "Buen estado", "ACEPTABLE": "Aceptable"}

CARPETA = Path(__file__).resolve().parent
DATOS = CARPETA / "datos" / "entrenamiento.csv"
ARCHIVO_MODELO = CARPETA / "modelo" / "inspector.joblib"

# Confianza mínima para alertar que la condición declarada no coincide
UMBRAL_CONDICION = 0.60

# Expresiones del texto que contradicen cada punto del checklist
CONTRADICCIONES = {
    "enciende": (
        "Enciende y funciona correctamente",
        r"no (enciende|prende|arranca|funciona)|se apaga|se reinicia|reinicia solo|falla al encender|"
        r"boton de encendido falla|se recalienta|se calienta mucho",
    ),
    "pantalla_sin_danos": (
        "Pantalla o carcasa sin daños",
        r"(pantalla|carcasa|tapa|vidrio) (esta |se ve |quedo |viene |tiene |con )?(la )?"
        r"(rota|quebrada|partida|rayada|manchada|danada|despegada|astillada)|fisura|grieta|pixel(es)? muerto|"
        r"manchas? en la pantalla|lineas (en la pantalla|verticales|horizontales)|golpe|abolladura|"
        r"rayones profundos",
    ),
    "bateria_ok": (
        "Batería o alimentación en buen estado",
        r"bateria (esta |se ve )?(dura poco|que no dura|hinchada|danada|mala|viciada|deteriorada)|"
        r"no carga|no dura nada|"
        r"bateria al ([1-6]\d|\d) ?%|se descarga rapido|toca tenerlo conectado|puerto de carga (danado|flojo)",
    ),
    "sin_reparaciones": (
        "Sin reparaciones ni piezas cambiadas",
        r"reparad[oa]|le cambiaron|se le cambio|cambio de (pantalla|bateria|tapa|fuente)|pieza(s)? generica|"
        r"pantalla generica|repuesto|servicio tecnico|en un taller",
    ),
    "accesorios_completos": (
        "Incluye accesorios originales",
        r"sin cargador|no incluye (cargador|accesorios|caja|control|cable)|sin caja|sin control|"
        r"cargador generico|sin accesorios|cargador no (es el )?original",
    ),
    "con_garantia": (
        "Conserva garantía o factura",
        r"sin garantia|garantia vencida|sin factura|no tiene factura",
    ),
}

NEGACION = re.compile(r"\b(sin|ningun[ao]?|no tiene|nunca|cero|ni)\b[^.,;]{0,15}$")

_modelo = None
_candado = threading.Lock()


# ----------------------------------------------------------------------
# Texto
# ----------------------------------------------------------------------

def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para comparar sin depender de la ortografía."""
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def normalizar_con_posiciones(texto: str) -> tuple[str, list[int]]:
    """Como normalizar(), pero recuerda la posición original de cada carácter."""
    normal, posiciones = [], []
    for i, caracter in enumerate((texto or "").lower()):
        for c in unicodedata.normalize("NFD", caracter):
            if unicodedata.category(c) != "Mn":
                normal.append(c)
                posiciones.append(i)
    return "".join(normal), posiciones


# "Ninguno", "sin defectos"... son afirmaciones del vendedor, no evidencia:
# no se le pasan al modelo para que no oculten lo que dice la descripción.
SIN_DEFECTOS = re.compile(r"^\W*(ningun[oa]?|no tiene( defectos)?|sin defectos|n/?a|nada)\W*$")

# Palabras que no explican la condición (no se muestran como expresiones clave)
PALABRAS_VACIAS = {
    "como", "de", "del", "la", "el", "los", "las", "en", "con", "y", "que", "pero", "por", "para", "un",
    "una", "lo", "se", "su", "sus", "al", "es", "esta", "muy", "mas", "a", "o", "le", "me", "mi", "ya",
    "iphone", "samsung", "xiaomi", "motorola", "lenovo", "hp", "dell", "lg", "sony", "apple", "huawei",
    "asus", "acer", "celular", "portatil", "televisor", "tablet", "consola", "nevera", "lavadora", "gb",
}


def unir_texto(nombre: str | None, descripcion: str | None, defectos: str | None) -> str:
    if defectos and SIN_DEFECTOS.match(normalizar(defectos)):
        defectos = None
    return " . ".join(t for t in (nombre, descripcion, defectos) if t)


# ----------------------------------------------------------------------
# Modelo
# ----------------------------------------------------------------------

def construir_modelo() -> Pipeline:
    caracteristicas = FeatureUnion([
        ("palabras", TfidfVectorizer(preprocessor=normalizar, ngram_range=(1, 2), sublinear_tf=True, min_df=1)),
        ("fragmentos", TfidfVectorizer(preprocessor=normalizar, analyzer="char_wb", ngram_range=(3, 5),
                                       sublinear_tf=True, min_df=2)),
    ])
    clasificador = LogisticRegression(C=4.0, max_iter=3000, class_weight="balanced")
    return Pipeline([("caracteristicas", caracteristicas), ("clasificador", clasificador)])


def leer_datos(archivo: Path = DATOS) -> tuple[list[str], list[str]]:
    with open(archivo, encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    textos = [unir_texto(None, fila["texto"], fila["defectos"]) for fila in filas]
    return textos, [fila["condicion"] for fila in filas]


def entrenar(guardar: bool = True) -> Pipeline:
    textos, etiquetas = leer_datos()
    modelo = construir_modelo().fit(textos, etiquetas)

    if guardar:
        ARCHIVO_MODELO.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"modelo": modelo, "version": VERSION_MODELO, "sklearn": sklearn.__version__}, ARCHIVO_MODELO)
        logger.info("Modelo de IA entrenado con %d ejemplos y guardado en %s", len(textos), ARCHIVO_MODELO)

    return modelo


def obtener_modelo() -> Pipeline:
    """Carga el modelo una sola vez; si no sirve, lo entrena de nuevo."""
    global _modelo

    with _candado:
        if _modelo is not None:
            return _modelo

        try:
            paquete = joblib.load(ARCHIVO_MODELO)
            if paquete.get("version") != VERSION_MODELO or paquete.get("sklearn") != sklearn.__version__:
                raise ValueError("modelo de otra versión")
            _modelo = paquete["modelo"]
        except Exception as error:  # archivo inexistente, dañado o de otra versión
            logger.info("Se entrena el modelo de IA (%s).", error)
            _modelo = entrenar()

        return _modelo


# ----------------------------------------------------------------------
# Análisis
# ----------------------------------------------------------------------

def _terminos_clave(modelo: Pipeline, texto: str, clase: str, cantidad: int = 5,
                    nombre: str | None = None) -> list[str]:
    """Expresiones del texto que más aportaron a la clase predicha."""
    vectorizador = modelo.named_steps["caracteristicas"].transformer_list[0][1]
    clasificador = modelo.named_steps["clasificador"]
    indice_clase = list(clasificador.classes_).index(clase)

    palabras_nombre = set(normalizar(nombre).split()) if nombre else set()
    vector = vectorizador.transform([texto])
    pesos = clasificador.coef_[indice_clase][: vector.shape[1]]
    nombres = vectorizador.get_feature_names_out()

    aportes = [
        (vector[0, i] * pesos[i], nombres[i]) for i in vector.nonzero()[1]
        if not all(p in PALABRAS_VACIAS or p in palabras_nombre for p in nombres[i].split())
    ]
    aportes = sorted((a for a in aportes if a[0] > 0), reverse=True)

    terminos = []
    for _, termino in aportes:
        if not any(termino in t or t in termino for t in terminos):
            terminos.append(termino)
        if len(terminos) == cantidad:
            break
    return terminos


def detectar_contradicciones(texto: str, checklist: dict | None) -> list[str]:
    """Puntos del checklist marcados como cumplidos que el texto contradice."""
    if not checklist:
        return []

    normal, posiciones = normalizar_con_posiciones(texto)
    alertas = []

    for clave, (criterio, patron) in CONTRADICCIONES.items():
        if not checklist.get(clave):
            continue
        for coincidencia in re.finditer(patron, normal):
            anterior = normal[max(0, coincidencia.start() - 25):coincidencia.start()]
            if NEGACION.search(anterior):
                continue  # "sin golpes", "no tiene fisuras"...
            original = texto[posiciones[coincidencia.start()]:posiciones[coincidencia.end() - 1] + 1]
            alertas.append(f"Marcaste «{criterio}», pero la descripción menciona «{original.lower()}».")
            break

    return alertas


def analizar(nombre: str | None, descripcion: str | None, defectos: str | None,
             checklist: dict | None, condicion_declarada: str | None) -> dict:
    """Analiza una publicación y devuelve la condición sugerida, la confianza y las alertas."""
    modelo = obtener_modelo()
    texto = unir_texto(nombre, descripcion, defectos)

    probabilidades = dict(zip(modelo.classes_, modelo.predict_proba([texto])[0]))
    sugerida = max(probabilidades, key=probabilidades.get)
    confianza = float(probabilidades[sugerida])

    alertas = detectar_contradicciones(texto, checklist)

    if (condicion_declarada in CONDICIONES and confianza >= UMBRAL_CONDICION
            and CONDICIONES.index(sugerida) < CONDICIONES.index(condicion_declarada)):
        alertas.append(
            f"Declaraste «{TEXTO_CONDICION[condicion_declarada]}», pero la descripción corresponde a "
            f"«{TEXTO_CONDICION[sugerida]}» (confianza {confianza:.0%})."
        )

    return {
        "condicion_sugerida": sugerida,
        "confianza": round(confianza, 4),
        "probabilidades": {c: round(float(p), 4) for c, p in probabilidades.items()},
        "coherencia": "REVISAR" if alertas else "COHERENTE",
        "alertas": alertas,
        "terminos_clave": _terminos_clave(modelo, texto, sugerida, nombre=nombre),
        "version_modelo": VERSION_MODELO,
    }
