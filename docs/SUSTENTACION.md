# Guía de sustentación

Material para presentar, demostrar y defender ElectroMarket ante la auditoría.

## 1. Antes de la presentación

- [ ] `git pull` en la rama que se va a presentar y `pip install -r requirements.txt` dentro de `backend/`.
- [ ] Base de datos al día: ejecutar `database/scripts/01` a `05` y comprobar que `99_verificar_esquema.sql` salga vacío.
- [ ] `pytest` en `backend/` → todas las pruebas pasan (mostrar el resultado si lo piden).
- [ ] `python -m scripts.datos_demo` en `backend/` para tener vendedora, comprador y productos listos. Anotar los correos que imprime (contraseña `Demo12345`).
- [ ] Reemplazar las fotos de prueba por fotos reales desde **Vender → Editar** (el script sube imágenes de 1 píxel).
- [ ] `uvicorn app.main:app --reload` y abrir http://127.0.0.1:8000 y http://127.0.0.1:8000/docs.
- [ ] Dos navegadores (o uno normal y uno privado): uno con la vendedora y otro con el comprador.
- [ ] SSMS abierto con consultas preparadas (sección 5) para mostrar que los datos cambian en la base.

## 2. Guion de la demostración (10 a 12 minutos)

| # | Quién | Acción en la interfaz | Qué explicar |
|---|---|---|---|
| 1 | — | Inicio, cambiar a tema oscuro | Paleta del proyecto, insignias de verificación en el catálogo |
| 2 | Vendedora | **Vender**: publicar un artículo con checklist, defectos y 3 fotos | Validaciones en el formulario y en la API; nivel `VERIFICADO`/`PARCIAL` |
| 3 | Comprador | Ficha del producto | Puntaje de estado, criterios esenciales, defectos declarados |
| 4 | Vendedora | Intentar agregar su propio producto al carrito | Regla de negocio: no se compran productos propios (403) |
| 5 | Comprador | Agregar 2 unidades, ir al carrito y a **Finalizar compra** | Carrito persistente, revalidación de stock |
| 6 | Comprador | Pagar con tarjeta terminada en `0000` | Pago rechazado (402): pedido `CANCELADO`, carrito e inventario intactos |
| 7 | Comprador | Pagar con **Pago simulado** | Pedido `PAGADO`, una venta por vendedor, inventario descontado (mostrar en SSMS) |
| 8 | Comprador | **Mis compras → Cancelar algunos productos** (1 unidad) | Cancelación inmediata antes del despacho; inventario devuelto |
| 9 | Comprador | **Mis reembolsos** | Reembolso `PENDIENTE`; al minuto pasa a `PROCESADO` con referencia `RMB-…` y el pago a `REEMBOLSO_PARCIAL` |
| 10 | Vendedora | **Mis ventas**: crear envío y marcar `ENVIADO` | Transiciones válidas del envío |
| 11 | Comprador | Solicitar cancelación de la venta despachada | Ya no es inmediata: queda `SOLICITADA` |
| 12 | Vendedora | Aprobar la solicitud | Inventario devuelto, pedido `CANCELADO`, nuevo reembolso; pago `REEMBOLSADO` |
| 13 | — | Swagger (`/docs`) | Endpoints, códigos HTTP y validaciones (probar un `codigo_postal` de 16 caracteres → 422) |

Si algo falla en vivo, el mismo flujo está automatizado en `backend/tests/integracion/test_flujo_sqlserver.py`.

### Presentación final: prototipo, pruebas e IA (15 a 18 minutos)

| Bloque | Tiempo | Qué mostrar |
|---|---|---|
| 1. Prototipo | 7 min | Pasos 2, 5, 6, 7, 8, 9, 12 del guion anterior (publicar, comprar, pago rechazado y aprobado, cancelar, reembolso) |
| 2. Pruebas | 4 min | En `backend/`: `$env:ELECTROMARKET_DB_TESTS="1"; pytest` en vivo (104 aprobadas); abrir `docs/evidencias/pruebas/reporte_pruebas.html`; ejecutar `node pruebas_e2e/recorrido_ia.js` y mostrar las capturas |
| 3. Servicio de IA | 5 min | Ver la tabla siguiente |

**Demostración de la IA**

| # | Acción | Qué explicar |
|---|---|---|
| 0 | Vender: categoría Celulares, antigüedad 24 meses, precio nuevo $ 2.400.000, **Sugerir precio con IA** → **Usar precio sugerido** | Primer servicio: la red 9-6-1 estima el precio (problema, 9 entradas, salida r, rango ±10 %, uso consultivo); métricas en `metricas_precio.md` |
| 1 | Vender: escribir «iPhone como nuevo, la pantalla está rota y la batería dura poco», marcar todo el checklist y declarar «Como nuevo» | **Problema:** el vendedor puede exagerar el estado |
| 2 | Pulsar **Analizar con IA** | **Integración:** el formulario llama a `POST /ia/inspeccionar`; el modelo corre dentro del backend |
| 3 | Mostrar el panel: «Aceptable», confianza, alertas y expresiones clave | **Información que procesa** (texto, checklist, condición) y **resultado** (condición, confianza, coherencia, alertas, explicación) |
| 4 | **Usar condición sugerida**, corregir el checklist, volver a analizar → «Coherente» | El vendedor decide; la IA solo sugiere |
| 5 | Mis productos: la publicación incoherente de los datos demo muestra «IA: revisar» y no tiene «Estado verificado» | **Cómo usa el sistema el resultado:** se guarda en `InspeccionesIA` y condiciona la insignia |
| 6 | Ficha del producto con la sesión del comprador | El comprador ve el análisis («El vendedor marcó…») |
| 7 | `docs/evidencias/ia/metricas_modelo.md` | 94,4 % con descripciones escritas a mano; limitaciones |

## 3. Dónde está la evidencia de cada criterio

| Criterio | Evidencia |
|---|---|
| Prototipo, pruebas e IA (entrega final) | [`ENTREGA.md`](ENTREGA.md), [`SERVICIO_IA.md`](SERVICIO_IA.md), `docs/evidencias/` |
| Funcionamiento del sistema transaccional | Demostración; `tests/integracion` (flujo completo contra SQL Server); `pytest` |
| Repositorio y código fuente | Estructura `backend/`, `frontend/`, `database/`; historial de Git y bitácora `commits/`; pull requests |
| Calidad técnica | Capas rutas → servicios → BD; `app/errores.py`; validaciones Pydantic iguales a las columnas; transacciones con bloqueo; `database/README.md` (modelo y restricciones) |
| Conocimiento y trabajo en equipo | Sección 6 de esta guía (responsables por módulo); commits de cada integrante |
| Sustentación y demostración | Guion de la sección 2 y respuestas de la sección 4 |

## 4. Decisiones técnicas y preguntas probables

**¿Por qué el sistema es transaccional? ¿Cómo se evita vender más unidades de las que hay?**
La compra se hace en una sola transacción de SQL Server: se bloquean las filas del producto (`UPDLOCK, ROWLOCK`), se revalidan stock, estado del producto y del vendedor, se crean pedido, pago, ventas y detalles, y se descuenta el inventario. Si algo falla se hace `rollback` y no queda nada a medias. Dos compradores simultáneos no pueden tomar la misma última unidad.

**¿Por qué el pedido copia el precio y la dirección?**
Para conservar lo que se compró: si el vendedor cambia el precio o el comprador edita su dirección, los pedidos ya hechos no cambian.

**¿Por qué una venta por vendedor?**
Un pedido puede tener productos de varios vendedores; cada uno despacha, cancela y cobra su parte. El estado del pedido se recalcula a partir de sus ventas.

**¿Cuáles son las reglas de cancelación?**
Antes del despacho, la cancelación (total o parcial) es inmediata. Después del despacho, el comprador solo puede solicitarla y el vendedor la aprueba o la rechaza. Una venta entregada no se cancela.

**¿Cómo funciona el reembolso?**
Al aprobarse una cancelación se registra un reembolso `PENDIENTE` por el valor cancelado. La pasarela es simulada: pasado un minuto, al consultar, el reembolso pasa a `PROCESADO` (con referencia y fecha) y el pago a `REEMBOLSO_PARCIAL` o `REEMBOLSADO`. Se hace al consultar para no necesitar un proceso en segundo plano.

**¿Por qué en la base todas las solicitudes con venta son `PARCIAL`?**
La restricción `CK_Solicitudes_Tipo` del modelo exige `TOTAL` sin venta y `PARCIAL` con venta. Como cada solicitud corresponde a una venta, se guarda `PARCIAL` y la API calcula si cubrió todas las unidades vigentes (`SQL_TIPO_CANCELACION`).

**¿Cómo se valida la información?**
En tres niveles: el formulario web (experiencia de usuario), Pydantic en la API (tipos, longitudes iguales a las columnas, formatos) y la base de datos (`CHECK`, claves foráneas, únicos). Las reglas de negocio están en los servicios.

**¿Cómo se manejan los errores?**
Cada error de negocio está en `app/errores.py` y pertenece a una categoría con su código HTTP (400, 401, 403, 404, 409). Un manejador global responde `{"detail": ...}`. Un error inesperado se registra en el log y el usuario recibe un 500 sin detalles internos.

**¿Cómo se protegen las contraseñas y la sesión?**
Contraseñas con Argon2 (nunca en texto plano). La sesión es un token JWT firmado que vence (`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`). Las consultas SQL son parametrizadas (sin inyección SQL). El número de tarjeta nunca se guarda.

**¿Cómo se asegura el estado del producto?**
El vendedor completa un checklist y describe los defectos (obligatorio). El producto es `VERIFICADO` solo si cumple los tres criterios esenciales, tiene al menos 3 fotos y declara defectos; si no, `PARCIAL`. El puntaje de 0 a 100 combina checklist, condición y fotos.

**¿Cómo se probó?**
Pruebas unitarias y de rutas sin base de datos (`pytest`) y pruebas de integración que recorren el flujo completo contra SQL Server real (`ELECTROMARKET_DB_TESTS=1`).

**¿Cómo funciona la red de precio?**
Perceptrón multicapa 9-6-1: h = ReLU(W1·x + b1) y y = σ(W2·h + b2), con 67 parámetros. La salida sigmoide impide precios negativos o mayores que el precio nuevo. Se entrenó con retropropagación (lbfgs) y se comparó con regresión lineal y bosque aleatorio: la red obtuvo el menor error (MAE 0,026; R² 0,968).

**¿Qué tipo de IA es el inspector y por qué esa?**
Aprendizaje automático supervisado: clasificación de texto con regresión logística sobre TF-IDF (scikit-learn), más reglas de coherencia. Es liviana, explicable (muestra qué expresiones influyeron), corre localmente sin costo ni internet y se entrena en segundos.

**¿Con qué datos se entrenó? ¿Cómo saben que funciona?**
Con 900 descripciones sintéticas generadas con plantillas (`app/ia/datos.py`). Para medirlo de forma honesta se usaron 36 descripciones escritas a mano que el modelo nunca vio: acierta el 94,4 %. Los errores están listados en `metricas_modelo.md`.

**¿Qué pasa si la IA se equivoca o falla?**
Solo sugiere y alerta: no rechaza publicaciones. Si el modelo fallara, la publicación sigue y el error queda en el log. El vendedor puede corregir y volver a analizar.

**¿Cómo se mejoraría?**
Reentrenarla con publicaciones reales etiquetadas (`python -m app.ia.evaluar`) y agregar análisis de las fotos.

## 5. Consultas útiles en SSMS durante la demo

```sql
-- Últimos pedidos con su pago
SELECT TOP 5 P.IdPedido, P.Estado, P.Total, PG.Estado AS Pago
FROM Pedidos P JOIN Pagos PG ON PG.IdPedido = P.IdPedido
ORDER BY P.IdPedido DESC;

-- Inventario de los productos
SELECT IdProducto, Nombre, Stock, Estado FROM Productos ORDER BY IdProducto DESC;

-- Cancelaciones y reembolsos
SELECT SC.IdSolicitud, SC.Estado, R.Valor, R.Estado AS Reembolso, R.Referencia
FROM SolicitudesCancelacion SC LEFT JOIN Reembolsos R ON R.IdSolicitud = SC.IdSolicitud
ORDER BY SC.IdSolicitud DESC;

-- Resultados del inspector de IA
SELECT P.Nombre, P.Condicion, II.CondicionSugerida, II.Confianza, II.Coherencia, II.Alertas
FROM InspeccionesIA II JOIN Productos P ON P.IdProducto = II.IdProducto
ORDER BY II.FechaAnalisis DESC;

-- Historial de estados
SELECT TOP 10 * FROM HistorialEstados ORDER BY IdHistorial DESC;
```

## 6. Distribución del trabajo

Roles: Alejandro Castro Alvarez (líder y backend), Maria Camila Sosa Cediel (datos e inteligencia artificial) y Manuel Santiago Osorio Feo (interfaz, pruebas y documentación). Ajusten la tabla si la distribución real fue distinta; cada persona debe poder explicar su módulo y responder preguntas de los demás.

| Integrante | Módulo | Archivos principales |
|---|---|---|
| Alejandro Castro Alvarez | Usuarios, autenticación y perfil | `routes/usuarios.py`, `services/usuarios.py`, `security.py`, `registro.html`, `login.html`, `perfil.html` |
| Manuel Santiago Osorio Feo | Productos, imágenes y verificación | `routes/productos.py`, `services/productos.py`, `services/imagenes.py`, `services/verificacion.py`, `vender.html`, `producto.html` |
| Alejandro Castro Alvarez | Carrito, compra y pagos | `services/carrito.py`, `services/pedidos.py`, `services/pagos.py`, `carrito.html`, `checkout.html` |
| Alejandro Castro Alvarez | Ventas, envíos, cancelaciones y reembolsos | `services/ventas.py`, `services/envios.py`, `services/cancelaciones.py`, `services/reembolsos.py`, `pedidos.html`, `ventas.html` |
| Maria Camila Sosa Cediel | Base de datos | `database/scripts/`, `database/README.md` |
| Maria Camila Sosa Cediel | Servicio de IA | `app/ia/`, `routes/ia.py`, `services/inspeccion_ia.py`, `docs/SERVICIO_IA.md` |

## 7. Limitaciones conocidas (decirlas antes de que las pregunten)

- Los pagos y reembolsos son simulados; no hay pasarela real.
- No hay devoluciones después de la entrega.
- El checklist de estado lo declara el vendedor; no hay revisión de un tercero.
- El procesamiento del reembolso ocurre al consultar, no con un proceso programado.
