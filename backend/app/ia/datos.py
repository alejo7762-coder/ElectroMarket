"""
Generador del conjunto de datos de entrenamiento del inspector de estado.

Crea descripciones de productos electrónicos usados, en español, con su
condición real (COMO_NUEVO, BUENO o ACEPTABLE). Se construyen combinando
frases típicas de cada condición, mezcladas con frases neutras y, a veces,
con una frase de otra condición (ruido) para que el modelo no dependa de
una sola palabra.

Los datos son sintéticos: sirven para entrenar el prototipo. Para medir el
modelo de forma honesta se usa además evaluacion_manual.csv, escrito a mano
y que el modelo nunca ve durante el entrenamiento.

Uso (desde backend/):
    python -m app.ia.datos
"""

import csv
import random
from pathlib import Path

CARPETA = Path(__file__).resolve().parent / "datos"
ARCHIVO = CARPETA / "entrenamiento.csv"

PRODUCTOS = [
    "Celular Samsung Galaxy A54", "iPhone 12 de 128 GB", "Xiaomi Redmi Note 11", "Motorola G32",
    "Portátil Lenovo IdeaPad", "MacBook Air M1", "Portátil HP Pavilion", "Tablet Samsung Tab A8",
    "iPad de novena generación", "Televisor LG 50 pulgadas", "Smart TV Samsung 43 pulgadas",
    "Monitor Dell 24 pulgadas", "Nevera Mabe 300 litros", "Lavadora Whirlpool 18 kg",
    "Horno microondas Haceb", "PlayStation 4 Slim", "Xbox One S", "Nintendo Switch",
    "Audífonos Sony WH-1000XM4", "Parlante JBL Flip 5", "Cámara Canon EOS Rebel", "Licuadora Oster",
]

FRASES = {
    "COMO_NUEVO": [
        "como nuevo", "prácticamente nuevo", "sin uso", "lo usé muy pocas veces", "está impecable",
        "en perfecto estado", "en su caja original", "sin rayones ni golpes", "no tiene ningún detalle",
        "con garantía vigente", "con factura de compra", "batería al 100 %", "batería al 98 %",
        "incluye todos los accesorios originales", "pantalla con protector desde el primer día",
        "solo lo saqué de la caja para probarlo", "se ve y funciona como recién comprado",
        "tiene menos de dos meses de uso", "sellado de fábrica", "estado de exhibición, sin marcas",
        "conserva los plásticos protectores", "cero detalles estéticos",
    ],
    "BUENO": [
        "en buen estado", "uso normal", "tiene rayones leves", "detalles mínimos de uso",
        "funciona perfectamente", "batería al 85 %", "batería al 88 %", "un pequeño rayón en la carcasa",
        "marcas de uso en los bordes", "incluye cargador genérico", "tiene un año de uso",
        "desgaste normal por el uso", "pantalla en buen estado", "leve desgaste en las teclas",
        "algunos rayones finos que no se notan con la pantalla encendida", "funciona bien en general",
        "detalle estético pequeño en la parte de atrás", "la pintura está un poco gastada",
        "todo funciona, solo tiene marcas de uso", "se ha cuidado bien", "dos años de uso con cuidado",
        "pequeña marca en la esquina",
    ],
    "ACEPTABLE": [
        "pantalla rota", "tiene la pantalla quebrada", "tiene un golpe fuerte", "la batería dura poco",
        "fisura en la pantalla", "se reinicia a veces", "rayones profundos", "carcasa despegada",
        "tiene un pixel muerto", "manchas en la pantalla", "el botón de encendido falla",
        "funciona con detalles", "fue reparado", "le cambiaron la pantalla por una genérica",
        "el puerto de carga está flojo", "no incluye accesorios", "tiene una abolladura",
        "hace ruido al funcionar", "se calienta mucho", "falla el wifi", "la bisagra está floja",
        "tiene óxido en la parte de atrás", "líneas en la pantalla", "no carga bien",
        "batería al 60 %", "le falta una tecla", "la puerta no cierra bien", "se apaga solo",
    ],
}

NEUTRAS = [
    "Lo vendo porque compré otro", "Entrega en Bogotá", "Se puede probar antes de comprar",
    "Precio negociable", "Envío a todo el país", "Me mudé y no lo necesito", "Color negro",
    "Color gris", "Ideal para estudiantes", "Acepto preguntas",
]

DEFECTOS = {
    "COMO_NUEVO": ["Ninguno", "Ninguno.", "No tiene defectos", "Sin defectos"],
    "BUENO": ["Rayones leves", "Pequeña marca de uso", "Desgaste normal", "Rayón pequeño en la tapa"],
    "ACEPTABLE": ["Pantalla con fisura", "Batería deteriorada", "Golpe visible", "Falla intermitente",
                  "Reparado por técnico"],
}

OTRA = {"COMO_NUEVO": "BUENO", "BUENO": "ACEPTABLE", "ACEPTABLE": "BUENO"}

# Vendedores que exageran: frases positivas junto a fallas reales.
# Enseñan al modelo que las fallas pesan más que "como nuevo".
EXAGERACIONES = ["como nuevo", "excelente estado", "impecable", "en perfecto estado", "buen estado"]


def generar_ejemplo(condicion: str, rnd: random.Random) -> dict:
    frases = rnd.sample(FRASES[condicion], k=rnd.randint(2, 4))

    # Ruido: a veces aparece una frase de una condición vecina
    if rnd.random() < 0.15:
        frases.append(rnd.choice(FRASES[OTRA[condicion]]))

    # Exageración: fallas graves descritas con palabras positivas
    if condicion == "ACEPTABLE" and rnd.random() < 0.3:
        frases.insert(0, rnd.choice(EXAGERACIONES))
    if not frases[0] in EXAGERACIONES:
        rnd.shuffle(frases)

    texto = f"{rnd.choice(PRODUCTOS)} {frases[0]}. " + ", ".join(frases[1:]).capitalize() + "."
    if rnd.random() < 0.5:
        texto += f" {rnd.choice(NEUTRAS)}."

    return {"texto": texto, "defectos": rnd.choice(DEFECTOS[condicion]), "condicion": condicion}


def generar(cantidad_por_clase: int = 300, semilla: int = 2026) -> list[dict]:
    rnd = random.Random(semilla)
    ejemplos = [generar_ejemplo(c, rnd) for c in FRASES for _ in range(cantidad_por_clase)]
    rnd.shuffle(ejemplos)
    return ejemplos


def guardar(ejemplos: list[dict], archivo: Path = ARCHIVO):
    CARPETA.mkdir(parents=True, exist_ok=True)
    with open(archivo, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=["texto", "defectos", "condicion"])
        escritor.writeheader()
        escritor.writerows(ejemplos)


if __name__ == "__main__":
    datos = generar()
    guardar(datos)
    print(f"{len(datos)} ejemplos guardados en {ARCHIVO}")
