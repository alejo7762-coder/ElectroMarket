# Métricas del inspector de estado (IA)

Generado: 2026-11-18T04:57:04 · Modelo `inspector-estado-1.0` · 900 ejemplos de entrenamiento

Modelo: regresión logística sobre TF-IDF de palabras (1-2) y fragmentos de palabras (3-5 caracteres).
Reproducir: `python -m app.ia.evaluar` desde `backend/`.

## 1. Validación interna (datos sintéticos, 80/20)

Exactitud: **100.0%** sobre 180 casos.
Es alta porque los datos sintéticos son muy regulares; la medida realista es la de la sección 2.

| Clase | Precisión | Exhaustividad (recall) | F1 | Casos |
|---|---|---|---|---|
| ACEPTABLE | 1.00 | 1.00 | 1.00 | 60 |
| BUENO | 1.00 | 1.00 | 1.00 | 60 |
| COMO_NUEVO | 1.00 | 1.00 | 1.00 | 60 |

| Real \ Predicha | ACEPTABLE | BUENO | COMO_NUEVO |
|---|---|---|---|
| **ACEPTABLE** | 60 | 0 | 0 |
| **BUENO** | 0 | 60 | 0 |
| **COMO_NUEVO** | 0 | 0 | 60 |

## 2. Evaluación con descripciones escritas a mano (nunca vistas)

Exactitud: **94.4%** sobre 36 casos.
Es la medida más realista: frases y productos distintos a los del entrenamiento.

| Clase | Precisión | Exhaustividad (recall) | F1 | Casos |
|---|---|---|---|---|
| ACEPTABLE | 1.00 | 0.92 | 0.96 | 12 |
| BUENO | 0.92 | 0.92 | 0.92 | 12 |
| COMO_NUEVO | 0.92 | 1.00 | 0.96 | 12 |

| Real \ Predicha | ACEPTABLE | BUENO | COMO_NUEVO |
|---|---|---|---|
| **ACEPTABLE** | 11 | 1 | 0 |
| **BUENO** | 0 | 11 | 1 |
| **COMO_NUEVO** | 0 | 0 | 12 |

### Casos fallados

| Descripción | Real | Predicha |
|---|---|---|
| Celular Xiaomi de dos años, funciona correctamente, el cargador no es el original.… | BUENO | COMO_NUEVO |
| iPhone 11 con batería al 72 % de condición, la tapa trasera tiene una grieta.… | ACEPTABLE | BUENO |

## 3. Detección de inconsistencias

Aciertos: **5 de 5**

| Caso | Esperado | Obtenido | Condición sugerida | Alertas |
|---|---|---|---|---|
| Checklist dice pantalla sin daños, el texto dice pantalla rota | REVISAR | REVISAR | ACEPTABLE (67%) | Marcaste «Pantalla o carcasa sin daños», pero la descripción menciona «pantalla rota». Declaraste «Buen estado», pero la descripción corresponde a «Aceptable» (confianza 67%). |
| Declara Como nuevo con batería deteriorada | REVISAR | REVISAR | ACEPTABLE (66%) | Marcaste «Enciende y funciona correctamente», pero la descripción menciona «se recalienta». Marcaste «Batería o alimentación en buen estado», pero la descripción menciona «batería dura poco». Declaraste «Como nuevo», pero la descripción corresponde a «Aceptable» (confianza 66%). |
| Negación: 'sin golpes ni rayones' no es contradicción | COHERENTE | COHERENTE | COMO_NUEVO (97%) | — |
| Marca 'sin reparaciones' pero fue reparado | REVISAR | REVISAR | ACEPTABLE (48%) | Marcaste «Sin reparaciones ni piezas cambiadas», pero la descripción menciona «le cambiaron». |
| Descripción coherente con Buen estado | COHERENTE | COHERENTE | BUENO (98%) | — |

## Limitaciones

- Los datos de entrenamiento son sintéticos (plantillas); con publicaciones reales el modelo se puede reentrenar con `python -m app.ia.evaluar`.
- Analiza solo texto: no revisa las fotos.
- Es una ayuda: la decisión final la toma el vendedor y la insignia la informa al comprador.
