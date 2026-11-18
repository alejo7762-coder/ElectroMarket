# Pruebas de interfaz (end-to-end)

Recorren la tienda en un navegador real (Chromium, con Playwright) contra el backend en funcionamiento y guardan capturas en `docs/evidencias/capturas/`.

| Script | Qué prueba |
|---|---|
| `recorrido_compra.js` | Registro, ficha del producto, carrito, compra, cancelación, reembolso y Mis ventas |
| `recorrido_ia.js` | Inspector de IA: análisis incoherente, uso de la condición sugerida, publicación con fotos, alerta en Mis productos y análisis en la ficha |

Cada script termina con error si un paso falla e informa los errores de JavaScript de la página.

## Ejecutar

1. Base de datos lista y backend en marcha (`uvicorn app.main:app` dentro de `backend/`).
2. Desde la raíz del repositorio:

```powershell
npm install playwright
npx playwright install chromium
node pruebas_e2e/recorrido_compra.js
node pruebas_e2e/recorrido_ia.js
```

Para otra dirección del backend: `$env:ELECTROMARKET_URL = "http://127.0.0.1:8001"`.
