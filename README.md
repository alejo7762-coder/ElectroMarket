# ElectroMarket

Sistema transaccional de compraventa de productos electrónicos usados (celulares, televisores, neveras, etc.). Cualquier usuario puede comprar y vender. Los pagos son simulados.

| Elemento | Tecnología |
|---|---|
| Lenguaje | Python 3.10 o superior |
| Framework | FastAPI |
| Base de datos | SQL Server Express (SSMS) |
| Conexión | pyodbc + ODBC Driver for SQL Server |
| Contraseñas | Argon2 |
| Autenticación | JWT (Bearer) |
| Pruebas | pytest |

---

## 1. Instalación

```powershell
git clone https://github.com/<usuario>/ElectroMarket.git
cd ElectroMarket

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Copia `.env.example` como `.env` y completa los valores:

```env
DB_SERVER=.\SQLEXPRESS
DB_NAME=ElectroMarket
DB_DRIVER=ODBC Driver 18 for SQL Server
DB_TRUST_CERTIFICATE=yes
JWT_SECRET_KEY=una-clave-larga-y-secreta
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

La conexión usa autenticación de Windows (`Trusted_Connection=yes`).

Prueba la conexión:

```powershell
python -m app.db.connection
```

## 2. Base de datos

1. Crea la base de datos y sus tablas con el script del modelo relacional.
2. Ejecuta en SSMS, en este orden:
   - `sql/01_cancelaciones.sql`: crea `Cancelaciones` y `DetallesCancelacion` (etapa 10). Puedes ejecutarlo varias veces sin problema.
   - `sql/03_perfil_usuarios.sql`: agrega `FechaNacimiento` y `Genero` a `Usuarios` (necesario para el registro y el perfil).
   - `sql/02_verificar_esquema.sql`: solo lectura. Comprueba que las restricciones `CHECK` acepten todos los estados que usa el código. Si las tres consultas salen vacías, el esquema es compatible.

## 3. Ejecutar la aplicación

```powershell
uvicorn app.main:app --reload
```

- Tienda (interfaz gráfica): http://127.0.0.1:8000/ (redirige a `/web/`)
- Swagger: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

En Swagger usa **Authorize** y pega el `access_token` que devuelve `/usuarios/login`.

### Interfaz gráfica

La interfaz está en `frontend/` (HTML, CSS y JavaScript sin dependencias) y la sirve FastAPI en `/web/`, por lo que no necesita un servidor aparte. Las fotos de los productos se sirven en `/storage/`.

| Página | Archivo | Qué hace |
|---|---|---|
| Inicio | `index.html` | Productos destacados, catálogo por categoría y búsqueda |
| Crear cuenta | `registro.html` | Registro con fecha de nacimiento y género |
| Ingresar | `login.html` | Inicio de sesión |
| Producto | `producto.html` | Fotos, detalle y agregar al carrito |
| Carrito | `carrito.html` | Cambiar cantidades, quitar y vaciar |
| Finalizar compra | `checkout.html` | Dirección, método de pago simulado y pago |
| Mis compras | `pedidos.html` | Pedidos, seguimiento y cancelaciones parciales o totales |
| Mi perfil | `perfil.html` | Datos personales, contraseña y direcciones |
| Vender | `vender.html` | Publicar y editar artículos con fotos; pausar, reactivar y eliminar |
| Mis ventas | `ventas.html` | Envíos, cambios de estado y respuesta a solicitudes de cancelación |

La sesión se guarda en el navegador (token JWT). Si el token vence, la interfaz pide ingresar de nuevo.

---

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
- Al aplicar una cancelación se devuelven las unidades al inventario (un producto `AGOTADO` vuelve a `PUBLICADO`) y se registra el reembolso simulado. El pago original conserva su estado `APROBADO`.
- No se implementan devoluciones después de la entrega.
- Las fotos se guardan en `storage/productos/{id_producto}/` y la base de datos guarda la ruta.

## 7. Estados

| Entidad | Estados |
|---|---|
| Pedido | `PENDIENTE_PAGO`, `PAGADO`, `EN_PROCESO`, `PARCIALMENTE_ENVIADO`, `COMPLETADO`, `CANCELADO` |
| Pago | `PENDIENTE`, `APROBADO`, `RECHAZADO` |
| Venta | `PENDIENTE`, `PREPARANDO`, `ENVIADA`, `ENTREGADA`, `CANCELACION_SOLICITADA`, `CANCELADA` |
| Envío | `PREPARANDO`, `ENVIADO`, `EN_TRANSITO`, `ENTREGADO`, `PROBLEMA`, `CANCELADO` |
| Cancelación | `SOLICITADA`, `APROBADA`, `RECHAZADA` (tipo `TOTAL` o `PARCIAL`) |

El estado del pedido se recalcula a partir de sus ventas: todas entregadas -> `COMPLETADO`; todas canceladas -> `CANCELADO`; unas despachadas y otras no -> `PARCIALMENTE_ENVIADO`.

---

## 8. Pruebas

```powershell
# Pruebas unitarias y de rutas (no necesitan SQL Server)
pytest -v

# Prueba de integración del flujo completo contra SQL Server
# (escribe datos reales: usa preferiblemente una copia de la base)
$env:ELECTROMARKET_DB_TESTS = "1"
$env:ELECTROMARKET_ID_CATEGORIA = "1"
pytest tests/integracion -v
```

## 9. Estructura

```
ElectroMarket/
├── app/
│   ├── main.py              # Aplicación FastAPI y registro de rutas
│   ├── security.py          # JWT
│   ├── db/connection.py     # Conexión a SQL Server
│   ├── routes/              # Endpoints (validación y códigos HTTP)
│   └── services/            # Lógica de negocio y consultas SQL
├── frontend/                # Interfaz gráfica (se sirve en /web/)
│   ├── css/estilos.css
│   ├── js/                  # api.js (común) y un archivo por página
│   └── *.html
├── sql/                     # Scripts de base de datos
├── storage/productos/       # Fotos de productos
├── tests/                   # Pruebas
├── .env.example
└── requirements.txt
```
