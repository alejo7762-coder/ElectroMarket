"""
Precio sugerido con una red neuronal simple (perceptrón multicapa 9-6-1).

Estima r = precio usado / precio nuevo de un artículo y sugiere
precio = r × precio nuevo, con un rango de ±10 %. Es consultivo: el
vendedor decide el precio y la base de datos solo guarda el que confirma.

Arquitectura (Documento Maestro, sección del servicio de IA):
    entrada (9) -> capa oculta (6, ReLU) -> salida (1, sigmoide)
    67 parámetros: 9×6 + 6 y 6×1 + 1.

Implementación: MLPRegressor de scikit-learn entrenado sobre logit(r);
al predecir se aplica la sigmoide, de modo que la salida es
y = σ(W2 · ReLU(W1 · x + b1) + b2), siempre entre 0 y 1.

Entradas:
    x1-x4  categoría one-hot (CELULAR, TELEVISOR, NEVERA, OTRO)
    x5     antigüedad en meses / 120 (tope 120)
    x6     condición: ACEPTABLE 0, BUENO 0.5, COMO_NUEVO 1
    x7     incluye caja y accesorios (0/1)
    x8     garantía vigente (0/1)
    x9     precio nuevo: logaritmo escalado a [0, 1]
"""

import csv
import logging
import math
import random
import threading
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.neural_network import MLPRegressor

from app.ia.inspector import normalizar

logger = logging.getLogger("electromarket.ia")

VERSION_MODELO = "precio-mlp-9-6-1-1.0"
GRUPOS = ("CELULAR", "TELEVISOR", "NEVERA", "OTRO")
CONDICION_ORDINAL = {"ACEPTABLE": 0.0, "BUENO": 0.5, "COMO_NUEVO": 1.0}
MESES_TOPE = 120
PRECIO_MIN, PRECIO_MAX = 100_000, 20_000_000
MARGEN_RANGO = 0.10
EPSILON = 1e-3

CARPETA = Path(__file__).resolve().parent
DATOS = CARPETA / "datos" / "precios.csv"
ARCHIVO_MODELO = CARPETA / "modelo" / "precio.joblib"

_modelo = None
_candado = threading.Lock()


# ----------------------------------------------------------------------
# Variables de entrada
# ----------------------------------------------------------------------

def grupo_categoria(nombre: str | None) -> str:
    """Agrupa las categorías del sistema en las cuatro de la red."""
    texto = normalizar(nombre)
    if "celular" in texto or "telefono" in texto:
        return "CELULAR"
    if "televisor" in texto or "monitor" in texto or texto.strip() == "tv":
        return "TELEVISOR"
    if "nevera" in texto or "refrigerador" in texto or "congelador" in texto:
        return "NEVERA"
    return "OTRO"


def vector_entrada(grupo: str, meses: int, condicion: str, caja: bool, garantia: bool, precio_nuevo: float) -> list[float]:
    x = [1.0 if grupo == g else 0.0 for g in GRUPOS]
    x.append(min(max(meses, 0), MESES_TOPE) / MESES_TOPE)
    x.append(CONDICION_ORDINAL[condicion])
    x.append(1.0 if caja else 0.0)
    x.append(1.0 if garantia else 0.0)
    precio = min(max(precio_nuevo, PRECIO_MIN), PRECIO_MAX)
    x.append((math.log(precio) - math.log(PRECIO_MIN)) / (math.log(PRECIO_MAX) - math.log(PRECIO_MIN)))
    return x


def _logit(r):
    r = np.clip(r, EPSILON, 1 - EPSILON)
    return np.log(r / (1 - r))


def _sigmoide(z):
    return 1 / (1 + np.exp(-z))


# ----------------------------------------------------------------------
# Datos sintéticos (reglas de depreciación)
# ----------------------------------------------------------------------

DEPRECIACION_MENSUAL = {"CELULAR": 0.028, "TELEVISOR": 0.017, "NEVERA": 0.009, "OTRO": 0.015}
VALOR_INICIAL = {"CELULAR": 0.82, "TELEVISOR": 0.80, "NEVERA": 0.85, "OTRO": 0.78}
FACTOR_CONDICION = {"COMO_NUEVO": 1.0, "BUENO": 0.84, "ACEPTABLE": 0.58}
RANGO_PRECIO_NUEVO = {"CELULAR": (400_000, 6_000_000), "TELEVISOR": (900_000, 8_000_000),
                      "NEVERA": (1_000_000, 7_000_000), "OTRO": (150_000, 5_000_000)}


def proporcion_esperada(grupo, meses, condicion, caja, garantia, precio_nuevo) -> float:
    """Regla de depreciación usada para generar los datos (sin ruido)."""
    edad = min(meses, MESES_TOPE) / MESES_TOPE
    condicion_efectiva = FACTOR_CONDICION[condicion] ** (1 - 0.3 * edad)
    precio_norm = vector_entrada(grupo, meses, condicion, caja, garantia, precio_nuevo)[8]
    r = VALOR_INICIAL[grupo] * math.exp(-DEPRECIACION_MENSUAL[grupo] * meses) * condicion_efectiva
    r += 0.04 * caja + 0.05 * garantia + 0.03 * (precio_norm - 0.5)
    return min(max(r, 0.05), 0.95)


def generar_datos(cantidad: int = 2000, semilla: int = 2026) -> list[dict]:
    rnd = random.Random(semilla)
    filas = []
    for _ in range(cantidad):
        grupo = rnd.choice(GRUPOS)
        meses = int(min(MESES_TOPE, rnd.expovariate(1 / 30)))
        condicion = rnd.choices(list(FACTOR_CONDICION), weights=[2, 5, 3])[0]
        caja = rnd.random() < 0.5
        garantia = rnd.random() < max(0.05, 0.8 - meses / 24)  # más probable si es reciente
        minimo, maximo = RANGO_PRECIO_NUEVO[grupo]
        precio_nuevo = round(math.exp(rnd.uniform(math.log(minimo), math.log(maximo))), -3)
        r = proporcion_esperada(grupo, meses, condicion, caja, garantia, precio_nuevo)
        r = min(max(r * math.exp(rnd.gauss(0, 0.06)), 0.03), 0.97)  # ruido del mercado
        filas.append({"grupo": grupo, "meses": meses, "condicion": condicion, "caja": int(caja),
                      "garantia": int(garantia), "precio_nuevo": int(precio_nuevo), "proporcion": round(r, 4)})
    return filas


def guardar_datos(filas: list[dict], archivo: Path = DATOS):
    archivo.parent.mkdir(parents=True, exist_ok=True)
    with open(archivo, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)


def leer_datos(archivo: Path = DATOS) -> tuple[np.ndarray, np.ndarray]:
    if not archivo.exists():
        guardar_datos(generar_datos(), archivo)
    with open(archivo, encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    x = np.array([vector_entrada(f["grupo"], int(f["meses"]), f["condicion"], f["caja"] == "1",
                                 f["garantia"] == "1", float(f["precio_nuevo"])) for f in filas])
    y = np.array([float(f["proporcion"]) for f in filas])
    return x, y


# ----------------------------------------------------------------------
# Red neuronal
# ----------------------------------------------------------------------

class RedPrecio:
    """
    MLP 9-6-1 con salida sigmoide (entrenado sobre logit de r).

    Una red tan pequeña depende de los pesos iniciales: se entrenan varias
    inicializaciones, se elige la de menor error en un 20 % de validación
    (tomado solo de los datos de entrenamiento) y se reentrena con todos.
    La regularización (alpha = 0.01) también se eligió por validación.
    """

    ALPHA = 1e-2
    REINICIOS = 10

    def __init__(self, semilla: int = 0):
        self.semilla = semilla
        self.red = None

    def _nueva(self, semilla):
        return MLPRegressor(hidden_layer_sizes=(6,), activation="relu", solver="lbfgs",
                            alpha=self.ALPHA, max_iter=8000, random_state=semilla)

    def fit(self, x, r):
        x, r = np.asarray(x), np.asarray(r)
        rnd = np.random.RandomState(self.semilla)
        validacion = rnd.rand(len(r)) < 0.2
        mejor = None
        for semilla in range(self.REINICIOS):
            red = self._nueva(semilla).fit(x[~validacion], _logit(r[~validacion]))
            error = np.mean(np.abs(_sigmoide(red.predict(x[validacion])) - r[validacion]))
            if mejor is None or error < mejor[0]:
                mejor = (error, semilla)
        self.semilla_elegida = mejor[1]
        self.red = self._nueva(mejor[1]).fit(x, _logit(r))
        return self

    def predict(self, x):
        return _sigmoide(self.red.predict(np.asarray(x)))

    @property
    def parametros(self) -> int:
        return sum(w.size for w in self.red.coefs_) + sum(b.size for b in self.red.intercepts_)


def entrenar(guardar: bool = True) -> RedPrecio:
    x, y = leer_datos()
    modelo = RedPrecio().fit(x, y)
    if guardar:
        ARCHIVO_MODELO.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"modelo": modelo, "version": VERSION_MODELO, "sklearn": sklearn.__version__}, ARCHIVO_MODELO)
        logger.info("Red de precio entrenada con %d ejemplos (%d parámetros)", len(y), modelo.parametros)
    return modelo


def obtener_modelo() -> RedPrecio:
    global _modelo
    with _candado:
        if _modelo is None:
            try:
                paquete = joblib.load(ARCHIVO_MODELO)
                if paquete.get("version") != VERSION_MODELO or paquete.get("sklearn") != sklearn.__version__:
                    raise ValueError("modelo de otra versión")
                _modelo = paquete["modelo"]
            except Exception as error:
                logger.info("Se entrena la red de precio (%s).", error)
                _modelo = entrenar()
        return _modelo


# ----------------------------------------------------------------------
# Sugerencia
# ----------------------------------------------------------------------

def _redondear(valor: float) -> int:
    return int(round(valor / 1000.0) * 1000)


def sugerir(categoria: str | None, meses: int, condicion: str, caja: bool, garantia: bool, precio_nuevo: float) -> dict:
    """Precio sugerido, rango ±10 % y efecto de cada característica."""
    modelo = obtener_modelo()
    grupo = grupo_categoria(categoria)

    def proporcion(**cambios):
        datos = {"meses": meses, "condicion": condicion, "caja": caja, "garantia": garantia, **cambios}
        x = vector_entrada(grupo, datos["meses"], datos["condicion"], datos["caja"], datos["garantia"], precio_nuevo)
        return float(modelo.predict([x])[0])

    r = proporcion()
    precio = r * precio_nuevo

    # Efecto de cada característica frente a un artículo nuevo y completo
    factores = [
        ("Antigüedad", f"{meses} meses", r - proporcion(meses=0)),
        ("Condición", condicion, r - proporcion(condicion="COMO_NUEVO")),
        ("Caja y accesorios", "sí" if caja else "no", r - proporcion(caja=True)),
        ("Garantía vigente", "sí" if garantia else "no", r - proporcion(garantia=True)),
    ]

    return {
        "precio_sugerido": _redondear(precio),
        "rango_minimo": _redondear(precio * (1 - MARGEN_RANGO)),
        "rango_maximo": _redondear(precio * (1 + MARGEN_RANGO)),
        "proporcion": round(r, 4),
        "precio_nuevo": int(precio_nuevo),
        "grupo_categoria": grupo,
        "factores": [
            {"factor": nombre, "valor": valor, "efecto_porcentual": round(efecto * 100, 1)}
            for nombre, valor, efecto in factores
        ],
        "version_modelo": VERSION_MODELO,
    }
