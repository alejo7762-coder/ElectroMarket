"""
Entrena y evalúa la red de precio sugerido frente a los modelos de referencia.

Como establece el Documento Maestro: partición 80/20, métricas MAE, RMSE y R²,
y comparación contra regresión lineal y bosque aleatorio. Si la red no mejora
a ambos, se documenta y se usaría el modelo más simple con el mismo endpoint.

Resultados: docs/evidencias/ia/metricas_precio.md y metricas_precio.json

Uso (desde backend/):
    python -m app.ia.evaluar_precio
"""

import json
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from app.ia import precio

SALIDA = Path(__file__).resolve().parents[3] / "docs" / "evidencias" / "ia"

EJEMPLOS = [
    ("Celulares", 24, "BUENO", True, False, 2_400_000),
    ("Celulares", 3, "COMO_NUEVO", True, True, 4_500_000),
    ("Televisores", 36, "BUENO", False, False, 2_000_000),
    ("Neveras", 60, "ACEPTABLE", False, False, 2_800_000),
    ("Videojuegos", 12, "COMO_NUEVO", True, False, 2_600_000),
]


def _metricas(nombre, y_real, y_pred, precio_nuevo):
    return {
        "modelo": nombre,
        "mae": float(mean_absolute_error(y_real, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_real, y_pred))),
        "r2": float(r2_score(y_real, y_pred)),
        "mae_cop": float(mean_absolute_error(y_real * precio_nuevo, y_pred * precio_nuevo)),
    }


def main():
    x, y = precio.leer_datos()
    precio_nuevo = np.exp(x[:, 8] * (np.log(precio.PRECIO_MAX) - np.log(precio.PRECIO_MIN)) + np.log(precio.PRECIO_MIN))
    indices = np.arange(len(y))
    i_ent, i_pru = train_test_split(indices, test_size=0.2, random_state=7)

    modelos = {
        "Red neuronal MLP 9-6-1": precio.RedPrecio(),
        "Regresión lineal": LinearRegression(),
        "Bosque aleatorio (200 árboles)": RandomForestRegressor(n_estimators=200, random_state=7),
    }
    resultados = []
    for nombre, modelo in modelos.items():
        modelo.fit(x[i_ent], y[i_ent])
        pred = np.clip(modelo.predict(x[i_pru]), 0, 1)
        resultados.append(_metricas(nombre, y[i_pru], pred, precio_nuevo[i_pru]))

    red = resultados[0]
    supera = all(red["mae"] <= otro["mae"] for otro in resultados[1:])
    parametros = modelos["Red neuronal MLP 9-6-1"].parametros

    # Modelo final con todos los datos
    final = precio.entrenar(guardar=True)
    precio._modelo = final
    ejemplos = [{"entrada": dict(zip(["categoria", "meses", "condicion", "caja", "garantia", "precio_nuevo"], e)),
                 **precio.sugerir(*e)} for e in EJEMPLOS]

    resultado = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "version_modelo": precio.VERSION_MODELO,
        "ejemplos": len(y), "entrenamiento": len(i_ent), "prueba": len(i_pru),
        "parametros_red": parametros,
        "comparacion": resultados,
        "red_supera_lineas_base": supera,
        "ejemplos_sugerencia": ejemplos,
    }

    tabla = "\n".join(
        f"| {r['modelo']} | {r['mae']:.4f} | {r['rmse']:.4f} | {r['r2']:.3f} | $ {r['mae_cop']:,.0f} |".replace(",", ".")
        for r in resultados
    )
    filas_ej = "\n".join(
        f"| {e['entrada']['categoria']} | {e['entrada']['meses']} | {e['entrada']['condicion']} | "
        f"{'sí' if e['entrada']['caja'] else 'no'} | {'sí' if e['entrada']['garantia'] else 'no'} | "
        f"$ {e['entrada']['precio_nuevo']:,} | {e['proporcion']:.2f} | $ {e['precio_sugerido']:,} | "
        f"$ {e['rango_minimo']:,} – $ {e['rango_maximo']:,} |".replace(",", ".")
        for e in ejemplos
    )

    md = f"""# Métricas de la red de precio sugerido (IA)

Generado: {resultado['fecha']} · Modelo `{precio.VERSION_MODELO}` · {len(y)} ejemplos ({len(i_ent)} entrenamiento / {len(i_pru)} prueba)

Red: perceptrón multicapa 9-6-1 (ReLU en la capa oculta, sigmoide en la salida), **{parametros} parámetros**.
Entrenamiento: MLPRegressor (lbfgs) sobre logit(r); se prueban 10 inicializaciones y se elige la de menor error en un
20 % de validación tomado del conjunto de entrenamiento; regularización alpha = 0,01 elegida también por validación.
Reproducir: `python -m app.ia.evaluar_precio` desde `backend/`.

## Comparación con los modelos de referencia (conjunto de prueba, 20 %)

Variable objetivo: r = precio usado / precio nuevo. MAE y RMSE en proporción; MAE en pesos sobre el precio sugerido.

| Modelo | MAE | RMSE | R² | MAE en pesos |
|---|---|---|---|---|
{tabla}

**Criterio de decisión:** la red se incorpora solo si su error (MAE) no es mayor que el de los dos modelos de referencia.
Resultado: **{'la red supera a las líneas base y se incorpora' if supera else 'la red NO supera a las líneas base'}**.

## Ejemplos de sugerencia del modelo final

| Categoría | Meses | Condición | Caja | Garantía | Precio nuevo | r | Precio sugerido | Rango (±10 %) |
|---|---|---|---|---|---|---|---|---|
{filas_ej}

## Limitaciones

- Datos sintéticos generados con reglas de depreciación (`app/ia/precio.py`), con ruido de mercado del 6 %; no se incorporaron datos públicos ni ventas reales. Debe reentrenarse cuando ElectroMarket acumule ventas.
- No considera marca ni modelo exacto.
- Es una orientación, no un avalúo: el vendedor decide el precio.
"""
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "metricas_precio.md").write_text(md, encoding="utf-8")
    (SALIDA / "metricas_precio.json").write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")

    for r in resultados:
        print(f"{r['modelo']:<32} MAE={r['mae']:.4f} RMSE={r['rmse']:.4f} R2={r['r2']:.3f} MAE$={r['mae_cop']:,.0f}")
    print("Parámetros de la red:", parametros, "| Supera líneas base:", supera)


if __name__ == "__main__":
    main()
