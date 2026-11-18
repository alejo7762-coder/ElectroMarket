from decimal import Decimal

from app.db.connection import get_connection
from app.services.productos import (
    ProductNotFound,
    ProductInvalidState,
    ProductOutOfStock
)


class UserNotActive(Exception):
    pass


class OwnProduct(Exception):
    pass


class CartProcessed(Exception):
    pass


def obtener_carrito(id_usuario: int):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        # Verificar que el usuario exista y esté activo
        cursor.execute("""
            SELECT Estado
            FROM Usuarios
            WHERE IdUsuario = ?;
        """, (id_usuario,))

        usuario = cursor.fetchone()

        if usuario is None or usuario.Estado != "ACTIVO":
            raise UserNotActive(
                "El usuario no existe o no está activo."
            )

        # Buscar el carrito del usuario
        cursor.execute("""
            SELECT IdCarrito, Estado
            FROM Carritos
            WHERE IdUsuario = ?;
        """, (id_usuario,))

        carrito = cursor.fetchone()

        if carrito is None:
            return {
                "id_carrito": None,
                "estado": "SIN_CARRITO",
                "productos": [],
                "total": 0.0
            }

        # Consultar los productos incluidos en el carrito
        cursor.execute("""
            SELECT
                DC.IdDetalleCarrito,
                P.IdProducto,
                P.Nombre,
                P.Descripcion,
                DC.Cantidad,
                P.Precio,
                P.Stock,
                P.Estado AS EstadoProducto,
                P.Condicion,
                U.IdUsuario AS IdVendedor,
                U.Nombre + ' ' + U.Apellido AS Vendedor,
                IP.RutaImagen
            FROM DetallesCarrito DC
            INNER JOIN Productos P
                ON DC.IdProducto = P.IdProducto
            INNER JOIN Usuarios U
                ON P.IdVendedor = U.IdUsuario
            LEFT JOIN ImagenesProducto IP
                ON P.IdProducto = IP.IdProducto
                AND IP.EsPrincipal = 1
            WHERE DC.IdCarrito = ?
            ORDER BY DC.FechaAgregado DESC;
        """, (carrito.IdCarrito,))

        productos = []
        total = Decimal("0.00")

        for fila in cursor.fetchall():
            precio = Decimal(str(fila.Precio))
            subtotal = precio * fila.Cantidad

            productos.append({
                "id_detalle": fila.IdDetalleCarrito,
                "id_producto": fila.IdProducto,
                "nombre": fila.Nombre,
                "descripcion": fila.Descripcion,
                "cantidad": fila.Cantidad,
                "precio_unitario": float(precio),
                "subtotal": float(subtotal),
                "stock_disponible": fila.Stock,
                "estado_producto": fila.EstadoProducto,
                "condicion": fila.Condicion,
                "id_vendedor": fila.IdVendedor,
                "vendedor": fila.Vendedor,
                "imagen_principal": fila.RutaImagen
            })

            total += subtotal

        return {
            "id_carrito": carrito.IdCarrito,
            "estado": carrito.Estado,
            "productos": productos,
            "total": float(total)
        }

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def agregar_producto(
    id_usuario: int,
    id_producto: int,
    cantidad: int
):
    connection = None
    cursor = None

    try:
        if cantidad <= 0:
            raise ValueError(
                "La cantidad debe ser mayor que cero."
            )

        connection = get_connection()
        cursor = connection.cursor()

        # Verificar y bloquear el usuario
        cursor.execute("""
            SELECT Estado
            FROM Usuarios WITH (UPDLOCK, ROWLOCK)
            WHERE IdUsuario = ?;
        """, (id_usuario,))

        usuario = cursor.fetchone()

        if usuario is None or usuario.Estado != "ACTIVO":
            raise UserNotActive(
                "El usuario no existe o no está activo."
            )

        # Buscar y bloquear el carrito del usuario
        cursor.execute("""
            SELECT IdCarrito, Estado
            FROM Carritos WITH (UPDLOCK, HOLDLOCK)
            WHERE IdUsuario = ?;
        """, (id_usuario,))

        carrito = cursor.fetchone()

        if carrito is None:
            # Crear el carrito si todavía no existe
            cursor.execute("""
                INSERT INTO Carritos (IdUsuario)
                OUTPUT INSERTED.IdCarrito
                VALUES (?);
            """, (id_usuario,))

            carrito = cursor.fetchone()
            id_carrito = carrito.IdCarrito

        else:
            id_carrito = carrito.IdCarrito

            if carrito.Estado == "PROCESADO":
                raise CartProcessed(
                    "El carrito ya fue procesado."
                )

            if carrito.Estado == "INACTIVO":
                cursor.execute("""
                    UPDATE Carritos
                    SET Estado = 'ACTIVO',
                        FechaActualizacion = SYSDATETIME()
                    WHERE IdCarrito = ?;
                """, (id_carrito,))

        # Consultar y bloquear el producto
        cursor.execute("""
            SELECT
                P.IdVendedor,
                P.Nombre,
                P.Precio,
                P.Stock,
                P.Estado,
                U.Estado AS EstadoVendedor
            FROM Productos P WITH (UPDLOCK, ROWLOCK)
            INNER JOIN Usuarios U
                ON P.IdVendedor = U.IdUsuario
            WHERE P.IdProducto = ?;
        """, (id_producto,))

        producto = cursor.fetchone()

        if producto is None:
            raise ProductNotFound(
                "El producto solicitado no existe."
            )

        if producto.IdVendedor == id_usuario:
            raise OwnProduct(
                "No puedes agregar tus propios productos al carrito."
            )

        if producto.EstadoVendedor != "ACTIVO":
            raise ProductInvalidState(
                "El vendedor no tiene una cuenta activa."
            )

        if producto.Estado != "PUBLICADO":
            raise ProductInvalidState(
                "El producto no está disponible para la compra."
            )

        if producto.Stock <= 0:
            raise ProductOutOfStock(
                "El producto no tiene unidades disponibles."
            )

        # Buscar si el producto ya está en el carrito
        cursor.execute("""
            SELECT IdDetalleCarrito, Cantidad
            FROM DetallesCarrito WITH (UPDLOCK, ROWLOCK)
            WHERE IdCarrito = ?
              AND IdProducto = ?;
        """, (id_carrito, id_producto))

        detalle = cursor.fetchone()

        if detalle:
            nueva_cantidad = detalle.Cantidad + cantidad
        else:
            nueva_cantidad = cantidad

        # Validar que no se supere el stock
        if nueva_cantidad > producto.Stock:
            raise ProductOutOfStock(
                f"Solo hay {producto.Stock} unidades disponibles."
            )

        if detalle:
            # Actualizar cantidad del producto existente
            cursor.execute("""
                UPDATE DetallesCarrito
                SET Cantidad = ?
                WHERE IdDetalleCarrito = ?;
            """, (nueva_cantidad, detalle.IdDetalleCarrito))

        else:
            # Insertar un nuevo producto en el carrito
            cursor.execute("""
                INSERT INTO DetallesCarrito (
                    IdCarrito,
                    IdProducto,
                    Cantidad
                )
                VALUES (?, ?, ?);
            """, (id_carrito, id_producto, cantidad))

        # Actualizar fecha de modificación del carrito
        cursor.execute("""
            UPDATE Carritos
            SET FechaActualizacion = SYSDATETIME()
            WHERE IdCarrito = ?;
        """, (id_carrito,))

        connection.commit()

        return {
            "mensaje": "Producto agregado correctamente al carrito.",
            "id_carrito": id_carrito,
            "id_producto": id_producto,
            "nombre": producto.Nombre,
            "cantidad": nueva_cantidad,
            "precio_unitario": float(producto.Precio),
            "subtotal": float(
                Decimal(str(producto.Precio)) * nueva_cantidad
            )
        }

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()

def actualizar_cantidad(
    id_usuario: int,
    id_producto: int,
    cantidad: int
):
    connection = None
    cursor = None

    try:
        if cantidad <= 0:
            raise ValueError(
                "La cantidad debe ser mayor que cero."
            )

        connection = get_connection()
        cursor = connection.cursor()

        # Buscar y bloquear el carrito del usuario
        cursor.execute("""
            SELECT IdCarrito, Estado
            FROM Carritos WITH (UPDLOCK, HOLDLOCK)
            WHERE IdUsuario = ?;
        """, (id_usuario,))

        carrito = cursor.fetchone()

        if carrito is None:
            raise ProductNotFound(
                "El usuario no tiene un carrito registrado."
            )

        if carrito.Estado != "ACTIVO":
            raise CartProcessed(
                "El carrito no se encuentra activo."
            )

        # Buscar y bloquear el producto
        cursor.execute("""
            SELECT
                IdVendedor,
                Nombre,
                Precio,
                Stock,
                Estado
            FROM Productos WITH (UPDLOCK, ROWLOCK)
            WHERE IdProducto = ?;
        """, (id_producto,))

        producto = cursor.fetchone()

        if producto is None:
            raise ProductNotFound(
                "El producto solicitado no existe."
            )

        if producto.IdVendedor == id_usuario:
            raise OwnProduct(
                "No puedes comprar tus propios productos."
            )

        if producto.Estado != "PUBLICADO":
            raise ProductInvalidState(
                "El producto no está disponible para la compra."
            )

        if producto.Stock <= 0:
            raise ProductOutOfStock(
                "El producto no tiene unidades disponibles."
            )

        # Verificar que el producto esté en el carrito
        cursor.execute("""
            SELECT IdDetalleCarrito
            FROM DetallesCarrito WITH (UPDLOCK, ROWLOCK)
            WHERE IdCarrito = ?
              AND IdProducto = ?;
        """, (carrito.IdCarrito, id_producto))

        detalle = cursor.fetchone()

        if detalle is None:
            raise ProductNotFound(
                "El producto no está incluido en el carrito."
            )

        # Validar stock
        if cantidad > producto.Stock:
            raise ProductOutOfStock(
                f"Solo hay {producto.Stock} unidades disponibles."
            )

        # Actualizar cantidad
        cursor.execute("""
            UPDATE DetallesCarrito
            SET Cantidad = ?
            WHERE IdDetalleCarrito = ?;
        """, (cantidad, detalle.IdDetalleCarrito))

        # Actualizar fecha del carrito
        cursor.execute("""
            UPDATE Carritos
            SET FechaActualizacion = SYSDATETIME()
            WHERE IdCarrito = ?;
        """, (carrito.IdCarrito,))

        connection.commit()

        return {
            "mensaje": "Cantidad actualizada correctamente.",
            "id_carrito": carrito.IdCarrito,
            "id_producto": id_producto,
            "nombre": producto.Nombre,
            "cantidad": cantidad,
            "precio_unitario": float(producto.Precio),
            "subtotal": float(
                Decimal(str(producto.Precio)) * cantidad
            )
        }

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()

def eliminar_producto_carrito(id_usuario: int, id_producto: int):
    conexion = get_connection()
    cursor = conexion.cursor()

    try:
        # Verificar que el usuario esté activo
        cursor.execute("""
            SELECT Estado
            FROM Usuarios WITH (UPDLOCK, ROWLOCK)
            WHERE IdUsuario = ?
        """, (id_usuario,))

        usuario = cursor.fetchone()

        if not usuario or usuario[0] != "ACTIVO":
            raise UserNotActive()

        # Buscar y bloquear el carrito del usuario
        cursor.execute("""
            SELECT IdCarrito, Estado
            FROM Carritos WITH (UPDLOCK, HOLDLOCK)
            WHERE IdUsuario = ?
        """, (id_usuario,))

        carrito = cursor.fetchone()

        if not carrito:
            raise ValueError("El usuario no tiene un carrito.")

        id_carrito = carrito[0]
        estado_carrito = carrito[1]

        if estado_carrito == "PROCESADO":
            raise CartProcessed()

        if estado_carrito != "ACTIVO":
            raise ValueError("El carrito no se encuentra activo.")

        # Eliminar el producto del carrito
        cursor.execute("""
            DELETE FROM DetallesCarrito
            WHERE IdCarrito = ?
              AND IdProducto = ?
        """, (id_carrito, id_producto))

        if cursor.rowcount == 0:
            raise ValueError("El producto no se encuentra en el carrito.")

        # Actualizar la fecha del carrito
        cursor.execute("""
            UPDATE Carritos
            SET FechaActualizacion = SYSDATETIME()
            WHERE IdCarrito = ?
        """, (id_carrito,))

        conexion.commit()

        return {
            "mensaje": "Producto eliminado del carrito correctamente.",
            "id_carrito": id_carrito,
            "id_producto": id_producto
        }

    except Exception:
        conexion.rollback()
        raise

    finally:
        cursor.close()
        conexion.close()

def vaciar_carrito(id_usuario: int):
    conexion = get_connection()
    cursor = conexion.cursor()

    try:
        # Verificar que el usuario esté activo
        cursor.execute("""
            SELECT Estado
            FROM Usuarios WITH (UPDLOCK, ROWLOCK)
            WHERE IdUsuario = ?
        """, (id_usuario,))

        usuario = cursor.fetchone()

        if not usuario or usuario[0] != "ACTIVO":
            raise UserNotActive()

        # Buscar y bloquear el carrito
        cursor.execute("""
            SELECT IdCarrito, Estado
            FROM Carritos WITH (UPDLOCK, HOLDLOCK)
            WHERE IdUsuario = ?
        """, (id_usuario,))

        carrito = cursor.fetchone()

        if not carrito:
            raise ValueError("El usuario no tiene un carrito.")

        id_carrito = carrito[0]
        estado_carrito = carrito[1]

        if estado_carrito == "PROCESADO":
            raise CartProcessed()

        if estado_carrito != "ACTIVO":
            raise ValueError("El carrito no se encuentra activo.")

        # Eliminar todos los productos del carrito
        cursor.execute("""
            DELETE FROM DetallesCarrito
            WHERE IdCarrito = ?
        """, (id_carrito,))

        productos_eliminados = cursor.rowcount

        # Actualizar la fecha del carrito
        cursor.execute("""
            UPDATE Carritos
            SET FechaActualizacion = SYSDATETIME()
            WHERE IdCarrito = ?
        """, (id_carrito,))

        conexion.commit()

        return {
            "mensaje": "Carrito vaciado correctamente.",
            "id_carrito": id_carrito,
            "productos_eliminados": productos_eliminados
        }

    except Exception:
        conexion.rollback()
        raise

    finally:
        cursor.close()
        conexion.close()
