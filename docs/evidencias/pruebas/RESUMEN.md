# Evidencias de pruebas

Resultado: **104 pruebas, 104 aprobadas, 0 fallidas**, contra SQL Server 2022 para las de integración. Cobertura del código del backend: **64 %**.

| Archivo | Evidencia |
|---|---|
| [`reporte_pruebas.html`](reporte_pruebas.html) | Reporte HTML de pytest (abrir en el navegador): cada prueba con su resultado y duración |
| [`salida_pytest.txt`](salida_pytest.txt) | Salida de la consola con la lista de pruebas y la cobertura por archivo |
| [`../capturas/`](../capturas/) | Capturas de las pruebas de interfaz (end-to-end) en un navegador real |
| [`../ia/metricas_precio.md`](../ia/metricas_precio.md) y [`../ia/metricas_modelo.md`](../ia/metricas_modelo.md) | Métricas de los dos modelos de IA |

## Pruebas automatizadas del backend (pytest)

| Archivo | Pruebas | Qué cubre |
|---|---|---|
| `tests/test_rutas.py` | 18 | Autenticación, validaciones de entrada, compra (aprobada 201 / rechazada 402 / conflicto de stock 409), cancelaciones |
| `tests/test_ia.py` | 15 | Servicio de IA: clasificación de las 3 condiciones, contradicciones, negaciones, explicación, reentrenamiento automático, efecto en la insignia, tolerancia a fallos y endpoints `/ia` |
| `tests/test_precio.py` | 12 | Servicio de IA de precio: arquitectura 9-6-1 con 67 parámetros, agrupación de categorías, escalado de entradas, rango ±10 %, comportamiento esperado (antigüedad, condición, caja) y endpoint |
| `tests/test_reembolsos_verificacion.py` | 13 | Estado de reembolso del pago, endpoints de reembolsos, niveles de verificación y puntaje del producto |
| `tests/test_perfil.py` | 12 | Registro con edad mínima, perfil, cambio de contraseña, productos del vendedor |
| `tests/test_sincronizacion_pedido.py` | 10 | Recalcular el estado del pedido a partir de sus ventas |
| `tests/test_cancelaciones.py` | 9 | Cálculo de unidades y montos al cancelar (total y parcial) |
| `tests/test_errores.py` | 8 | Manejo global de errores (códigos HTTP, sin filtrar detalles internos) y validaciones alineadas con la base de datos |
| `tests/test_pagos_simulados.py` | 4 | Pago simulado, transferencia, tarjeta aprobada y rechazada |
| `tests/integracion/test_flujo_sqlserver.py` | 3 | **Contra SQL Server real** (ver abajo) |

### Pruebas de integración (SQL Server real)

1. **Flujo transaccional completo:** registro de vendedor y comprador → publicación → dirección → carrito → pago rechazado (inventario intacto) → pago aprobado (inventario descontado) → cancelación parcial → envío → solicitud de cancelación → aprobación del vendedor → inventario restaurado, pedido cancelado, ingresos netos en 0.
2. **Verificación y reembolsos:** publicación con 3 fotos → `VERIFICADO`; no se puede comprar el propio producto; cancelación parcial → reembolso `PENDIENTE` → `PROCESADO` → pago `REEMBOLSO_PARCIAL`; cancelación del resto → pago `REEMBOLSADO`; tipos `PARCIAL` y `TOTAL`.
3. **Inspector de IA en la publicación:** publicación incoherente → `REVISAR` y la insignia queda `PARCIAL`; al corregirla → `COHERENTE` con condición sugerida `ACEPTABLE`.

## Pruebas de interfaz (end-to-end)

Scripts en `pruebas_e2e/` (Playwright, navegador Chromium) contra el backend y la base de datos reales. Ninguno registró errores de JavaScript.

| Recorrido | Capturas |
|---|---|
| Compra: registro, producto, carrito, pago, pedido, cancelación, reembolso, ventas | `capturas/compra-01` a `compra-08` |
| IA: precio sugerido, análisis incoherente, condición sugerida, publicación, alerta en Mis productos, ficha del comprador | `capturas/ia-00` a `ia-05` |

## Cómo reproducirlas

```powershell
# Desde backend/
pytest                                             # unitarias y de rutas
$env:ELECTROMARKET_DB_TESTS = "1"; pytest          # + integración con SQL Server
pytest -o addopts="" -v --html=../docs/evidencias/pruebas/reporte_pruebas.html --self-contained-html --cov=app

# Desde la raíz, con el backend en marcha
node pruebas_e2e/recorrido_compra.js
node pruebas_e2e/recorrido_ia.js
```
