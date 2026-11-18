# Métricas de la red de precio sugerido (IA)

Generado: 2026-11-18T05:23:42 · Modelo `precio-mlp-9-6-1-1.0` · 2000 ejemplos (1600 entrenamiento / 400 prueba)

Red: perceptrón multicapa 9-6-1 (ReLU en la capa oculta, sigmoide en la salida), **67 parámetros**.
Entrenamiento: MLPRegressor (lbfgs) sobre logit(r); se prueban 10 inicializaciones y se elige la de menor error en un
20 % de validación tomado del conjunto de entrenamiento; regularización alpha = 0,01 elegida también por validación.
Reproducir: `python -m app.ia.evaluar_precio` desde `backend/`.

## Comparación con los modelos de referencia (conjunto de prueba, 20 %)

Variable objetivo: r = precio usado / precio nuevo. MAE y RMSE en proporción; MAE en pesos sobre el precio sugerido.

| Modelo | MAE | RMSE | R² | MAE en pesos |
|---|---|---|---|---|
| Red neuronal MLP 9-6-1 | 0.0260 | 0.0343 | 0.968 | $ 63.610 |
| Regresión lineal | 0.0478 | 0.0618 | 0.897 | $ 112.327 |
| Bosque aleatorio (200 árboles) | 0.0289 | 0.0380 | 0.961 | $ 70.231 |

**Criterio de decisión:** la red se incorpora solo si su error (MAE) no es mayor que el de los dos modelos de referencia.
Resultado: **la red supera a las líneas base y se incorpora**.

## Ejemplos de sugerencia del modelo final

| Categoría | Meses | Condición | Caja | Garantía | Precio nuevo | r | Precio sugerido | Rango (±10 %) |
|---|---|---|---|---|---|---|---|---|
| Celulares | 24 | BUENO | sí | no | $ 2.400.000 | 0.40 | $ 960.000 | $ 864.000 – $ 1.056.000 |
| Celulares | 3 | COMO_NUEVO | sí | sí | $ 4.500.000 | 0.80 | $ 3.621.000 | $ 3.259.000 – $ 3.983.000 |
| Televisores | 36 | BUENO | no | no | $ 2.000.000 | 0.37 | $ 736.000 | $ 662.000 – $ 810.000 |
| Neveras | 60 | ACEPTABLE | no | no | $ 2.800.000 | 0.31 | $ 870.000 | $ 783.000 – $ 957.000 |
| Videojuegos | 12 | COMO_NUEVO | sí | no | $ 2.600.000 | 0.72 | $ 1.859.000 | $ 1.673.000 – $ 2.045.000 |

## Limitaciones

- Datos sintéticos generados con reglas de depreciación (`app/ia/precio.py`), con ruido de mercado del 6 %; no se incorporaron datos públicos ni ventas reales. Debe reentrenarse cuando ElectroMarket acumule ventas.
- No considera marca ni modelo exacto.
- Es una orientación, no un avalúo: el vendedor decide el precio.
