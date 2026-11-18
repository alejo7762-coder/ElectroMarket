# ElectroMarket

Sistema transaccional de compraventa de productos electrónicos usados (celulares, televisores, neveras, etc.). Cualquier usuario puede comprar y vender. Los pagos son simulados. Incluye dos servicios de IA: **precio sugerido** con una red neuronal 9-6-1 e **inspector de estado** que revisa cada publicación ([`docs/SERVICIO_IA.md`](docs/SERVICIO_IA.md)).

> Entrega final (prototipo, pruebas e IA): [`docs/ENTREGA.md`](docs/ENTREGA.md)

| Elemento | Tecnología |
|---|---|
| Lenguaje | Python 3.10 o superior |
| Framework | FastAPI |
| Base de datos | SQL Server Express (SSMS) |
| Conexión | pyodbc + ODBC Driver for SQL Server |
| Contraseñas | Argon2 |
| Autenticación | JWT (Bearer) |
| Inteligencia artificial | scikit-learn (modelo local) |
| Pruebas | pytest, pytest-html, pytest-cov y Playwright (interfaz) |

---

## Estructura del proyecto

```
ElectroMarket/
├── backend/                     API FastAPI
│   ├── app/
│   │   ├── main.py              aplicación, rutas y manejo global de errores
│   │   ├── errores.py           errores de negocio y su código HTTP
│   │   ├── security.py          tokens JWT
│   │   ├── db/connection.py     conexión a SQL Server
│   │   ├── ia/                  servicios de IA: red de precio e inspector de estado
│   │   ├── routes/              endpoints: validan la entrada (Pydantic)
│   │   └── services/            lógica de negocio y consultas SQL
│   ├── tests/                   pruebas (pytest)
│   ├── scripts/datos_demo.py    datos de demostración
│   ├── storage/productos/       fotos subidas de los productos
│   ├── requirements.txt
│   └── .env.example
├── frontend/                    interfaz web (HTML, CSS y JS sin dependencias)
│   ├── css/estilos.css          paleta, temas, componentes y utilidades
│   ├── js/                      api.js, iconos.js y tema.js (comunes) y un archivo por página
│   └── *.html
├── docs/
│   ├── ENTREGA.md               índice de la entrega final
│   ├── Documento_Maestro_*.pdf  Documento Maestro final (PDF y Word)
│   ├── SERVICIO_IA.md           servicio de inteligencia artificial
│   ├── SUSTENTACION.md          guion de demostración y decisiones técnicas
│   └── evidencias/              reportes de pruebas, métricas de IA y capturas
├── pruebas_e2e/                 pruebas de interfaz con Playwright
├── database/
│   ├── README.md                modelo, estados y orden de los scripts
│   └── scripts/                 scripts SQL (00 a 05 y 99)
└── commits/                     bitácora del historial de commits
```

Todos los comandos de Python se ejecutan dentro de `backend/`.

### Arquitectura

- **Rutas** (`routes/`): reciben la petición, validan los datos con Pydantic (los límites coinciden con las columnas de la base de datos) y llaman al servicio.
- **Servicios** (`services/`): reglas de negocio, transacciones y SQL parametrizado. Ante una regla incumplida lanzan un error de `app/errores.py`.
- **Errores**: cada error de negocio pertenece a una categoría con su código (`DatosInvalidos` 400, `NoAutorizado` 401, `AccesoDenegado` 403, `NoEncontrado` 404, `Conflicto` 409). `main.py` los convierte en `{"detail": ...}`. Un error inesperado se registra en el log y el cliente recibe un 500 sin detalles internos.

## 1. Instalación

```powershell
git clone https://github.com/<usuario>/ElectroMarket.git
cd ElectroMarket/backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Copia `backend/.env.example` como `backend/.env` y completa los valores:

```env
DB_SERVER=.\SQLEXPRESS
DB_NAME=ElectroMarket
DB_DRIVER=ODBC Driver 18 for SQL Server
DB_TRUST_CERTIFICATE=yes
JWT_SECRET_KEY=una-clave-larga-y-secreta
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

La conexión usa autenticación de Windows (`Trusted_Connection=yes`). Para usar un usuario de SQL Server, completa `DB_USER` y `DB_PASSWORD`.

Prueba la conexión:

```powershell
python -m app.db.connection
```

## 2. Base de datos

Ejecuta en SSMS los scripts de `database/scripts/` en orden:

1. `00_modelo.sql`: crea la base y todas las tablas (omítelo si ya la tienes).
2. `01_perfil_usuarios.sql`, `02_reembolsos.sql` y `03_verificacion_productos.sql`: cambios sobre el modelo; se pueden ejecutar varias veces.
3. `04_datos_iniciales.sql`: categorías de productos.
4. `05_inspeccion_ia.sql`: tabla con los resultados del inspector de IA.
5. `99_verificar_esquema.sql`: solo lectura; si sus consultas salen vacías, el esquema es compatible.

El diagrama del modelo, los estados y las reglas del esquema están en [`database/README.md`](database/README.md).

## 3. Ejecutar la aplicación

```powershell
uvicorn app.main:app --reload
```

- Tienda (interfaz gráfica): http://127.0.0.1:8000/ (redirige a `/web/`)
- Swagger: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

En Swagger usa **Authorize** y pega el `access_token` que devuelve `/usuarios/login`.

### Interfaz gráfica

Paleta: `#1E1E1C` (carbón), `#D8CBB3` (arena) y `#2F6BFF` (azul eléctrico). Tiene tema claro y oscuro; el botón de luna/sol del encabezado cambia entre ellos y la elección se recuerda en el navegador. Los iconos son SVG propios definidos en `js/iconos.js` (no dependen de internet): los botones reciben su icono según el texto y en el HTML se puede usar `data-icono="nombre"`.

La interfaz está en `frontend/` (HTML, CSS y JavaScript sin dependencias) y la sirve FastAPI en `/web/`, por lo que no necesita un servidor aparte. Las fotos de los productos se sirven en `/storage/`.

| Página | Archivo | Qué hace |
|---|---|---|
| Inicio | `index.html` | Productos destacados, catálogo por categoría y búsqueda |
| Crear cuenta | `registro.html` | Registro con fecha de nacimiento y género |
| Ingresar | `login.html` | Inicio de sesión |
| Producto | `producto.html` | Fotos, detalle, verificación del estado y agregar al carrito |
| Carrito | `carrito.html` | Cambiar cantidades, quitar y vaciar |
| Finalizar compra | `checkout.html` | Dirección, método de pago simulado y pago |
| Mis compras | `pedidos.html` | Pedidos, seguimiento, cancelaciones parciales o totales y seguimiento de reembolsos |
| Mi perfil | `perfil.html` | Datos personales, contraseña y direcciones |
| Vender | `vender.html` | Publicar y editar artículos con checklist de estado y mínimo 3 fotos; pausar, reactivar y eliminar |
| Mis ventas | `ventas.html` | Envíos, cambios de estado y respuesta a solicitudes de cancelación |

La sesión se guarda en el navegador (token JWT). Si el token vence, la interfaz pide ingresar de nuevo.

---

### Datos de demostración

```powershell
python -m scripts.datos_demo
```

Crea una vendedora con productos publicados y un comprador con dirección, e imprime sus correos (contraseña `Demo12345`). La guía de la presentación está en [`docs/SUSTENTACION.md`](docs/SUSTENTACION.md).

## 4. Flujo de uso

```
Registro -> Login -> (Vendedor) Publicar producto + fotos
                  -> (Comprador) Registrar dirección -> Agregar al carrito
                  -> Comprar (pago simulado)
                         ├─ Rechazado -> pedido CANCELADO, el carrito se conserva
                         └─ Aprobado  -> pedido PAGADO, se crea una venta por vendedor
                                         y se descuenta el inventario
                  -> (Vendedor) Crear envío -> ENVIADO -> EN_TRANSITO -> ENTREGADO
                  -> (Antes de la entrega) Cancelación parcial o total
```

## 5. Endpoints

### Usuarios
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/usuarios/registro` | Registrar usuario (correo duplicado -> 409) |
| POST | `/usuarios/login` | Iniciar sesión y obtener el token |
| GET | `/usuarios/me` | Perfil del usuario autenticado |
| PUT | `/usuarios/me` | Editar nombre, apellido, celular, fecha de nacimiento y género |
| PUT | `/usuarios/me/contrasena` | Cambiar la contraseña |

El registro acepta además `telefono`, `fecha_nacimiento` (mayor de 18 años) y `genero` (`MASCULINO`, `FEMENINO`, `OTRO`, `PREFIERO_NO_DECIRLO`).

### Direcciones
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/direcciones/` | Mis direcciones |
| POST | `/direcciones/` | Registrar dirección |
| GET | `/direcciones/{id}` | Consultar una dirección |
| PUT | `/direcciones/{id}` | Actualizar (no altera pedidos ya hechos) |
| DELETE | `/direcciones/{id}` | Eliminar (409 si ya se usó en un pedido) |

### Productos
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/categorias/` | Categorías activas |
| GET | `/mis-productos/` | Productos del vendedor autenticado (todos los estados menos eliminados) |
| POST | `/productos/publicar` | Publicar producto |
| GET | `/productos/` | Catálogo con foto principal (filtro `id_categoria`) |
| GET | `/productos/{id}` | Detalle con todas sus fotos |
| PUT | `/productos/{id}` | Modificar |
| PATCH | `/productos/{id}/estado` | Pausar, reactivar o eliminar |
| POST | `/productos/{id}/imagenes` | Subir foto |
| GET | `/productos/{id}/imagenes` | Fotos del producto |
| PATCH | `/productos/{id}/imagenes/{id_imagen}/principal` | Cambiar foto principal |
| DELETE | `/productos/{id}/imagenes/{id_imagen}` | Eliminar foto |

### Carrito
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/carrito/` | Consultar carrito |
| POST | `/carrito/agregar` | Agregar producto |
| PUT | `/carrito/actualizar/{id_producto}` | Cambiar cantidad |
| DELETE | `/carrito/eliminar/{id_producto}` | Quitar producto |
| DELETE | `/carrito/vaciar` | Vaciar carrito |

### Pedidos y pagos
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/pedidos/comprar` | Comprar el carrito (201 aprobado, 402 rechazado) |
| GET | `/pedidos/` | Mis pedidos (filtro `estado`) |
| GET | `/pedidos/{id}` | Detalle: productos, pagos, ventas, envíos y cancelaciones |
| GET | `/pedidos/{id}/historial` | Historial de cambios de estado |
| GET | `/pagos/` | Mis pagos |
| GET | `/pagos/{id}` | Detalle del pago y valor reembolsado |

Métodos de pago simulados: `SIMULADO`, `TRANSFERENCIA_SIMULADA` y `TARJETA_SIMULADA` (requiere `numero_tarjeta` de 16 dígitos; si termina en `0000` se rechaza). El número de tarjeta nunca se guarda.

### Reembolsos
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/reembolsos/` | Mis reembolsos con totales devuelto y en proceso (filtro `id_pedido`) |
| GET | `/reembolsos/{id}` | Detalle: valor, estado, referencia y fechas |

Cuando se aprueba una cancelación (inmediata o por el vendedor) se registra un reembolso `PENDIENTE` por el valor cancelado. La pasarela simulada lo pasa a `PROCESADO` (con referencia `RMB-########` y `FechaReembolso`) un minuto después, y el pago queda en `REEMBOLSO_PARCIAL` o `REEMBOLSADO`; el cambio se aplica al consultar reembolsos o pagos. `GET /pagos/` y `GET /pagos/{id}` incluyen `reembolsado`, `reembolso_pendiente` y `estado_reembolso` (`SIN_REEMBOLSO`, `REEMBOLSO_PARCIAL`, `REEMBOLSADO`).

### Verificación del estado del producto
Al publicar o editar, el cuerpo debe incluir:

```json
{
  "checklist": {
    "enciende": true, "pantalla_sin_danos": true, "bateria_ok": true,
    "sin_reparaciones": false, "accesorios_completos": true, "con_garantia": false
  },
  "descripcion_defectos": "Rayón leve en la esquina. Escribe «Ninguno» si no tiene."
}
```

`GET /productos/{id}` devuelve `verificacion` (nivel, puntaje 0-100, criterios, defectos y requisitos faltantes); los listados devuelven `nivel_verificacion`. Es `VERIFICADO` si cumple los tres criterios esenciales, tiene al menos 3 fotos y defectos declarados; `PARCIAL` si falta algo; `SIN_VERIFICAR` si no hay checklist.

### Inteligencia artificial
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/productos/precio-sugerido` | Red neuronal 9-6-1: precio sugerido y rango ±10 % a partir de categoría, antigüedad, condición, caja, garantía y precio nuevo (no se guarda) |
| POST | `/ia/inspeccionar` | Analiza un borrador de publicación (descripción, defectos, checklist, condición) sin guardarlo |
| GET | `/ia/modelo` | Versión, descripción y métricas del modelo |

Al publicar o editar un producto, el análisis se guarda en `InspeccionesIA` y aparece en `GET /productos/{id}` como `inspeccion_ia`. Si la coherencia es `REVISAR`, el producto no puede quedar `VERIFICADO`. Los modelos se entrenan solos la primera vez; para reentrenarlos y regenerar las métricas: `python -m app.ia.evaluar` (inspector) y `python -m app.ia.evaluar_precio` (red de precio).

### Ventas (vendedor)
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/ventas/` | Mis ventas (filtro `estado`) |
| GET | `/ventas/resumen` | Totales: ventas por estado, unidades e ingresos netos |
| GET | `/ventas/{id}` | Detalle con comprador, dirección de entrega y envío |

### Envíos
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/envios/ventas/{id_venta}` | Crear envío (vendedor) |
| PATCH | `/envios/{id}/estado` | Cambiar estado (vendedor) |
| GET | `/envios/pedido/{id_pedido}` | Envíos de un pedido (comprador) |
| GET | `/envios/{id}` | Seguimiento con historial |

Transiciones: `PREPARANDO -> ENVIADO -> EN_TRANSITO -> ENTREGADO`, y `PROBLEMA` desde cualquiera de las tres primeras.

### Cancelaciones
| Método | Ruta | Quién | Descripción |
|---|---|---|---|
| POST | `/cancelaciones/pedidos/{id}/total` | Comprador | Cancela todo el pedido |
| POST | `/cancelaciones/pedidos/{id}/parcial` | Comprador | Cancela algunos productos o unidades |
| POST | `/cancelaciones/ventas/{id_venta}` | Comprador o vendedor | Cancela la parte de un vendedor |
| POST | `/cancelaciones/{id}/aprobar` | Vendedor | Aprueba una solicitud |
| POST | `/cancelaciones/{id}/rechazar` | Vendedor | Rechaza una solicitud |
| GET | `/cancelaciones/` | Ambos | Mis cancelaciones (filtros `rol`, `estado`) |
| GET | `/cancelaciones/{id}` | Ambos | Detalle con productos y montos |

Ejemplo de cancelación parcial:

```json
{
  "motivo": "Compré unidades de más",
  "productos": [
    { "id_producto": 12, "cantidad": 2 },
    { "id_producto": 15 }
  ]
}
```

Si se omite `cantidad`, se cancelan todas las unidades vigentes de ese producto.

---

## 6. Reglas de negocio

- Un usuario puede comprar y vender, pero no puede comprar sus propios productos.
- Los productos se venden por unidades y se pueden comprar varias unidades.
- Cada usuario tiene un carrito persistente; tras una compra aprobada se vacía.
- Al comprar se revalidan el stock, el estado del producto y el del vendedor, con bloqueo de filas para evitar sobreventas.
- El precio y la dirección de entrega se copian al pedido; cambios posteriores no lo afectan.
- Si el pago es aprobado la compra se confirma automáticamente, se crea una venta por cada vendedor y se descuenta el inventario. Un producto que llega a 0 unidades pasa a `AGOTADO`.
- Las cancelaciones solo se permiten antes de la entrega:
  - Venta no despachada (`PENDIENTE` o `PREPARANDO`): la cancelación se aplica de inmediato, parcial o total.
  - Venta despachada (`ENVIADA`): el comprador solo puede solicitar la cancelación completa de esa venta, y el vendedor la aprueba o la rechaza. Mientras está pendiente no se puede cambiar el envío.
  - Venta `ENTREGADA`: no se puede cancelar.
  - El vendedor puede cancelar su venta solo antes de despacharla.
- Al aplicar una cancelación se devuelven las unidades al inventario (un producto `AGOTADO` vuelve a `PUBLICADO`) y se registra un reembolso `PENDIENTE`. Al procesarse, el pago pasa a `REEMBOLSO_PARCIAL` o `REEMBOLSADO`.
- Un producto se publica con checklist de estado y descripción de defectos; queda `VERIFICADO` solo si cumple los criterios esenciales y tiene al menos 3 fotos.
- No se implementan devoluciones después de la entrega.
- Las fotos (JPG, PNG o WEBP, máximo 5 MB, hasta 5 por producto) se guardan en `backend/storage/productos/{id_producto}/` y la base de datos guarda la ruta.

## 7. Estados

| Entidad | Estados |
|---|---|
| Pedido | `PENDIENTE_PAGO`, `PAGADO`, `EN_PROCESO`, `PARCIALMENTE_ENVIADO`, `COMPLETADO`, `CANCELADO` |
| Pago | `PENDIENTE`, `APROBADO`, `RECHAZADO`, `REEMBOLSO_PARCIAL`, `REEMBOLSADO` |
| Reembolso | `PENDIENTE`, `PROCESADO` |
| Venta | `PENDIENTE`, `PREPARANDO`, `ENVIADA`, `ENTREGADA`, `CANCELACION_SOLICITADA`, `CANCELADA` |
| Envío | `PREPARANDO`, `ENVIADO`, `EN_TRANSITO`, `ENTREGADO`, `PROBLEMA`, `CANCELADO` |
| Cancelación | `SOLICITADA`, `APROBADA`, `RECHAZADA` (tipo `TOTAL` o `PARCIAL`) |

El estado del pedido se recalcula a partir de sus ventas: todas entregadas -> `COMPLETADO`; todas canceladas -> `CANCELADO`; unas despachadas y otras no -> `PARCIALMENTE_ENVIADO`.

---

## 8. Pruebas

```powershell
# Desde backend/: pruebas unitarias y de rutas (no necesitan SQL Server)
pytest

# Prueba de integración del flujo completo contra SQL Server
# (escribe datos reales: usa preferiblemente una copia de la base)
$env:ELECTROMARKET_DB_TESTS = "1"   # cubre compra, rechazo, cancelaciones, envíos, verificación y reembolsos
$env:ELECTROMARKET_ID_CATEGORIA = "1"
pytest tests/integracion -v

# Reporte HTML y cobertura (evidencias)
pytest -o addopts="" -v --html=../docs/evidencias/pruebas/reporte_pruebas.html --self-contained-html --cov=app
```

Pruebas de interfaz en navegador: ver [`pruebas_e2e/README.md`](pruebas_e2e/README.md). Resumen de resultados: [`docs/evidencias/pruebas/RESUMEN.md`](docs/evidencias/pruebas/RESUMEN.md).

## 9. Repositorio

- Ramas: el trabajo se hace en una rama y se integra a `main` mediante pull request.
- Mensajes de commit en español, en presente y describiendo el cambio (por ejemplo, «Agrega reembolsos al cancelar pedidos»).
- Bitácora: `commits/` tiene un archivo por commit y un índice. Actualízala después de cada commit:

```powershell
python commits/generar_bitacora.py
```

- Nunca se suben `.env`, entornos virtuales ni fotos de usuarios (ver `.gitignore`).
