"""
Entrena y evalúa el inspector de estado; deja las métricas como evidencia.

1. Validación interna: 80 % de los datos sintéticos para entrenar y 20 %
   para probar (división estratificada).
2. Evaluación externa: el modelo final (entrenado con todos los datos
   sintéticos) se prueba con evaluacion_manual.csv, escrito a mano y que
   nunca se usa para entrenar.
3. Coherencia: casos con checklist que contradice el texto.

Resultados: docs/evidencias/ia/metricas_modelo.md y metricas_modelo.json

Uso (desde backend/):
    python -m app.ia.evaluar
"""

import csv
import json
from datetime import datetime
from pathlib import Path

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from app.ia import inspector

RAIZ = Path(__file__).resolve().parents[3]
SALIDA = RAIZ / "docs" / "evidencias" / "ia"
MANUAL = Path(__file__).resolve().parent / "datos" / "evaluacion_manual.csv"
CLASES = list(inspector.CONDICIONES)

CASOS_COHERENCIA = [
    {
        "caso": "Checklist dice pantalla sin daños, el texto dice pantalla rota",
        "descripcion": "Celular con la pantalla rota en la esquina, funciona.",
        "checklist": {"enciende": True, "pantalla_sin_danos": True, "bateria_ok": True},
        "condicion": "BUENO", "esperado": "REVISAR",
    },
    {
        "caso": "Declara Como nuevo con batería deteriorada",
        "descripcion": "Portátil como nuevo, la batería dura poco y se recalienta.",
        "checklist": {"enciende": True, "pantalla_sin_danos": True, "bateria_ok": True},
        "condicion": "COMO_NUEVO", "esperado": "REVISAR",
    },
    {
        "caso": "Negación: 'sin golpes ni rayones' no es contradicción",
        "descripcion": "Televisor en perfecto estado, sin golpes ni rayones, con control y caja.",
        "checklist": {"enciende": True, "pantalla_sin_danos": True, "bateria_ok": True,
                      "accesorios_completos": True},
        "condicion": "COMO_NUEVO", "esperado": "COHERENTE",
    },
    {
        "caso": "Marca 'sin reparaciones' pero fue reparado",
        "descripcion": "Consola en buen estado, le cambiaron la fuente en un taller.",
        "checklist": {"enciende": True, "pantalla_sin_danos": True, "bateria_ok": True, "sin_reparaciones": True},
        "condicion": "BUENO", "esperado": "REVISAR",
    },
    {
        "caso": "Descripción coherente con Buen estado",
        "descripcion": "Celular con un año de uso, funciona perfectamente, rayones leves en el borde.",
        "checklist": {"enciende": True, "pantalla_sin_danos": True, "bateria_ok": True},
        "condicion": "BUENO", "esperado": "COHERENTE",
    },
]


def _tabla_confusion(reales, predichas) -> str:
    matriz = confusion_matrix(reales, predichas, labels=CLASES)
    filas = ["| Real \\ Predicha | " + " | ".join(CLASES) + " |", "|---|" + "---|" * len(CLASES)]
    for clase, fila in zip(CLASES, matriz):
        filas.append(f"| **{clase}** | " + " | ".join(str(v) for v in fila) + " |")
    return "\n".join(filas)


def _reporte(reales, predichas) -> dict:
    return classification_report(reales, predichas, labels=CLASES, output_dict=True, zero_division=0)


def _tabla_reporte(reporte: dict) -> str:
    filas = ["| Clase | Precisión | Exhaustividad (recall) | F1 | Casos |", "|---|---|---|---|---|"]
    for clase in CLASES:
        r = reporte[clase]
        filas.append(f"| {clase} | {r['precision']:.2f} | {r['recall']:.2f} | {r['f1-score']:.2f} | {int(r['support'])} |")
    return "\n".join(filas)


def main():
    textos, etiquetas = inspector.leer_datos()

    # 1. Validación interna
    x_ent, x_pru, y_ent, y_pru = train_test_split(textos, etiquetas, test_size=0.2, stratify=etiquetas, random_state=7)
    modelo_validacion = inspector.construir_modelo().fit(x_ent, y_ent)
    pred_pru = modelo_validacion.predict(x_pru)

    # 2. Modelo final y evaluación externa
    modelo = inspector.entrenar(guardar=True)
    inspector._modelo = modelo
    with open(MANUAL, encoding="utf-8") as f:
        manual = list(csv.DictReader(f))
    textos_manual = [inspector.unir_texto(None, m["texto"], m["defectos"]) for m in manual]
    reales_manual = [m["condicion"] for m in manual]
    pred_manual = list(modelo.predict(textos_manual))

    # 3. Coherencia
    coherencia = []
    for c in CASOS_COHERENCIA:
        r = inspector.analizar(None, c["descripcion"], None, c["checklist"], c["condicion"])
        coherencia.append({**c, "obtenido": r["coherencia"], "alertas": r["alertas"],
                           "condicion_sugerida": r["condicion_sugerida"], "confianza": r["confianza"]})

    resultado = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "version_modelo": inspector.VERSION_MODELO,
        "ejemplos_entrenamiento": len(textos),
        "validacion_interna": {"casos": len(y_pru), "exactitud": accuracy_score(y_pru, pred_pru),
                               "reporte": _reporte(y_pru, pred_pru)},
        "evaluacion_manual": {"casos": len(reales_manual), "exactitud": accuracy_score(reales_manual, pred_manual),
                              "reporte": _reporte(reales_manual, pred_manual)},
        "coherencia": {"casos": len(coherencia), "aciertos": sum(c["obtenido"] == c["esperado"] for c in coherencia)},
    }

    errores = [
        f"| {m['texto'][:90]}… | {real} | {pred} |"
        for m, real, pred in zip(manual, reales_manual, pred_manual) if real != pred
    ]

    md = f"""# Métricas del inspector de estado (IA)

Generado: {resultado['fecha']} · Modelo `{inspector.VERSION_MODELO}` · {len(textos)} ejemplos de entrenamiento

Modelo: regresión logística sobre TF-IDF de palabras (1-2) y fragmentos de palabras (3-5 caracteres).
Reproducir: `python -m app.ia.evaluar` desde `backend/`.

## 1. Validación interna (datos sintéticos, 80/20)

Exactitud: **{resultado['validacion_interna']['exactitud']:.1%}** sobre {len(y_pru)} casos.
Es alta porque los datos sintéticos son muy regulares; la medida realista es la de la sección 2.

{_tabla_reporte(resultado['validacion_interna']['reporte'])}

{_tabla_confusion(y_pru, pred_pru)}

## 2. Evaluación con descripciones escritas a mano (nunca vistas)

Exactitud: **{resultado['evaluacion_manual']['exactitud']:.1%}** sobre {len(reales_manual)} casos.
Es la medida más realista: frases y productos distintos a los del entrenamiento.

{_tabla_reporte(resultado['evaluacion_manual']['reporte'])}

{_tabla_confusion(reales_manual, pred_manual)}

### Casos fallados

| Descripción | Real | Predicha |
|---|---|---|
{chr(10).join(errores) if errores else '| (ninguno) | | |'}

## 3. Detección de inconsistencias

Aciertos: **{resultado['coherencia']['aciertos']} de {resultado['coherencia']['casos']}**

| Caso | Esperado | Obtenido | Condición sugerida | Alertas |
|---|---|---|---|---|
{chr(10).join(f"| {c['caso']} | {c['esperado']} | {c['obtenido']} | {c['condicion_sugerida']} ({c['confianza']:.0%}) | {' '.join(c['alertas']) or '—'} |" for c in coherencia)}

## Limitaciones

- Los datos de entrenamiento son sintéticos (plantillas); con publicaciones reales el modelo se puede reentrenar con `python -m app.ia.evaluar`.
- Analiza solo texto: no revisa las fotos.
- Es una ayuda: la decisión final la toma el vendedor y la insignia la informa al comprador.
"""

    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "metricas_modelo.md").write_text(md, encoding="utf-8")
    (SALIDA / "metricas_modelo.json").write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Validación interna: {resultado['validacion_interna']['exactitud']:.1%}")
    print(f"Evaluación manual:  {resultado['evaluacion_manual']['exactitud']:.1%}")
    print(f"Coherencia:         {resultado['coherencia']['aciertos']}/{resultado['coherencia']['casos']}")
    print(f"Métricas en {SALIDA}")


if __name__ == "__main__":
    main()
