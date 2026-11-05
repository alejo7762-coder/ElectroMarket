import pyodbc
from decimal import Decimal

from app.db.connection import get_connection


class CategoryNotFound(Exception):
    pass


class CategoryInactive(Exception):
    pass


def publicar_producto(
    id_vendedor: int,
    id_categoria: int,
    nombre: str,
    descripcion: str,
    precio: Decimal,
    stock: int,
    condicion: str
):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        # Verificar que la categoría exista y esté activa
        cursor.execute(
            """
            SELECT Estado
            FROM Categorias
            WHERE IdCategoria = ?;
            """,
            id_categoria
        )

        categoria = cursor.fetchone()

        if categoria is None:
            raise CategoryNotFound(
                "La categoría seleccionada no existe."
            )

        if not categoria.Estado:
            raise CategoryInactive(
                "La categoría seleccionada no está activa."
            )

        # Registrar el producto
        cursor.execute(
            """
            INSERT INTO Productos (
                IdVendedor,
                IdCategoria,
                Nombre,
                Descripcion,
                Precio,
                Stock,
                Condicion
            )
            OUTPUT INSERTED.IdProducto
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            id_vendedor,
            id_categoria,
            nombre,
            descripcion,
            precio,
            stock,
            condicion
        )

        resultado = cursor.fetchone()
        id_producto = resultado[0]

        connection.commit()

        return id_producto

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
def listar_productos(id_categoria=None):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        consulta = """
            SELECT
                P.IdProducto,
                P.Nombre,
                P.Descripcion,
                P.Precio,
                P.Stock,
                P.Condicion,
                P.Estado,
                P.FechaPublicacion,
                C.IdCategoria,
                C.Nombre AS Categoria,
                U.IdUsuario AS IdVendedor,
                U.Nombre + ' ' + U.Apellido AS Vendedor
            FROM Productos P
            INNER JOIN Categorias C
                ON P.IdCategoria = C.IdCategoria
            INNER JOIN Usuarios U
                ON P.IdVendedor = U.IdUsuario
            WHERE P.Estado = 'PUBLICADO'
              AND P.Stock > 0
              AND U.Estado = 'ACTIVO'
        """

        parametros = []

        if id_categoria is not None:
            consulta += " AND P.IdCategoria = ?"
            parametros.append(id_categoria)

        consulta += " ORDER BY P.FechaPublicacion DESC;"

        cursor.execute(consulta, parametros)

        productos = []

        for fila in cursor.fetchall():
            productos.append({
                "id_producto": fila.IdProducto,
                "nombre": fila.Nombre,
                "descripcion": fila.Descripcion,
                "precio": float(fila.Precio),
                "stock": fila.Stock,
                "condicion": fila.Condicion,
                "estado": fila.Estado,
                "fecha_publicacion": fila.FechaPublicacion.isoformat(),
                "id_categoria": fila.IdCategoria,
                "categoria": fila.Categoria,
                "id_vendedor": fila.IdVendedor,
                "vendedor": fila.Vendedor
            })

        return productos

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def obtener_producto(id_producto: int):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        consulta = """
            SELECT
                P.IdProducto,
                P.Nombre,
                P.Descripcion,
                P.Precio,
                P.Stock,
                P.Condicion,
                P.Estado,
                P.FechaPublicacion,
                C.IdCategoria,
                C.Nombre AS Categoria,
                U.IdUsuario AS IdVendedor,
                U.Nombre + ' ' + U.Apellido AS Vendedor
            FROM Productos P
            INNER JOIN Categorias C
                ON P.IdCategoria = C.IdCategoria
            INNER JOIN Usuarios U
                ON P.IdVendedor = U.IdUsuario
            WHERE P.IdProducto = ?;
        """

        cursor.execute(consulta, id_producto)
        fila = cursor.fetchone()

        if fila is None:
            return None

        return {
            "id_producto": fila.IdProducto,
            "nombre": fila.Nombre,
            "descripcion": fila.Descripcion,
            "precio": float(fila.Precio),
            "stock": fila.Stock,
            "condicion": fila.Condicion,
            "estado": fila.Estado,
            "fecha_publicacion": fila.FechaPublicacion.isoformat(),
            "id_categoria": fila.IdCategoria,
            "categoria": fila.Categoria,
            "id_vendedor": fila.IdVendedor,
            "vendedor": fila.Vendedor
        }

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
class ProductNotFound(Exception):
    pass


class ProductForbidden(Exception):
    pass


class ProductDeleted(Exception):
    pass

class ProductInvalidState(Exception):
    pass


class ProductOutOfStock(Exception):
    pass

def modificar_producto(
    id_producto: int,
    id_vendedor: int,
    id_categoria: int,
    nombre: str,
    descripcion: str,
    precio: Decimal,
    stock: int,
    condicion: str
):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        # Bloquear temporalmente el producto mientras se valida y modifica
        cursor.execute(
            """
            SELECT IdVendedor, Estado
            FROM Productos WITH (UPDLOCK, ROWLOCK)
            WHERE IdProducto = ?;
            """,
            id_producto
        )

        producto = cursor.fetchone()

        if producto is None:
            raise ProductNotFound(
                "El producto solicitado no existe."
            )

        if producto.IdVendedor != id_vendedor:
            raise ProductForbidden(
                "No tienes permiso para modificar este producto."
            )

        if producto.Estado == "ELIMINADO":
            raise ProductDeleted(
                "No se pueden modificar productos eliminados."
            )

        # Verificar que la categoría exista y esté activa
        cursor.execute(
            """
            SELECT Estado
            FROM Categorias
            WHERE IdCategoria = ?;
            """,
            id_categoria
        )

        categoria = cursor.fetchone()

        if categoria is None:
            raise CategoryNotFound(
                "La categoría seleccionada no existe."
            )

        if not categoria.Estado:
            raise CategoryInactive(
                "La categoría seleccionada no está activa."
            )

        # Actualizar el producto
        cursor.execute(
            """
            UPDATE Productos
            SET
                IdCategoria = ?,
                Nombre = ?,
                Descripcion = ?,
                Precio = ?,
                Stock = ?,
                Condicion = ?,
                Estado = CASE
                    WHEN Estado = 'PAUSADO' THEN 'PAUSADO'
                    WHEN ? > 0 THEN 'PUBLICADO'
                    ELSE 'AGOTADO'
                END
            WHERE IdProducto = ?
              AND IdVendedor = ?
              AND Estado <> 'ELIMINADO';
            """,
            id_categoria,
            nombre,
            descripcion,
            precio,
            stock,
            condicion,
            stock,
            id_producto,
            id_vendedor
        )

        if cursor.rowcount != 1:
            raise ProductNotFound(
                "No fue posible actualizar el producto."
            )

        connection.commit()

        return id_producto

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def gestionar_estado_producto(
    id_producto: int,
    id_vendedor: int,
    accion: str
):
    connection = None
    cursor = None

    try:
        accion = accion.upper()

        if accion not in ("PAUSAR", "REACTIVAR", "ELIMINAR"):
            raise ValueError("Acción no válida.")

        connection = get_connection()
        cursor = connection.cursor()

        # Bloquear el producto mientras se valida la operación
        cursor.execute(
            """
            SELECT IdVendedor, Estado, Stock
            FROM Productos WITH (UPDLOCK, ROWLOCK)
            WHERE IdProducto = ?;
            """,
            id_producto
        )

        producto = cursor.fetchone()

        if producto is None:
            raise ProductNotFound(
                "El producto solicitado no existe."
            )

        if producto.IdVendedor != id_vendedor:
            raise ProductForbidden(
                "No tienes permiso para gestionar este producto."
            )

        estado_actual = producto.Estado
        stock_actual = producto.Stock

        if estado_actual == "ELIMINADO":
            raise ProductDeleted(
                "El producto ya fue eliminado."
            )

        # Pausar producto
        if accion == "PAUSAR":

            if estado_actual != "PUBLICADO":
                raise ProductInvalidState(
                    "Solo se pueden pausar productos publicados."
                )

            nuevo_estado = "PAUSADO"

        # Reactivar producto
        elif accion == "REACTIVAR":

            if estado_actual not in ("PAUSADO", "AGOTADO"):
                raise ProductInvalidState(
                    "El producto no se encuentra pausado o agotado."
                )

            if stock_actual <= 0:
                raise ProductOutOfStock(
                    "No se puede reactivar un producto sin stock."
                )

            nuevo_estado = "PUBLICADO"

        # Eliminación lógica
        else:
            nuevo_estado = "ELIMINADO"

        cursor.execute(
            """
            UPDATE Productos
            SET Estado = ?
            WHERE IdProducto = ?
              AND IdVendedor = ?
              AND Estado <> 'ELIMINADO';
            """,
            nuevo_estado,
            id_producto,
            id_vendedor
        )

        if cursor.rowcount != 1:
            raise ProductInvalidState(
                "No fue posible cambiar el estado del producto."
            )

        connection.commit()

        return {
            "id_producto": id_producto,
            "estado_anterior": estado_actual,
            "estado_nuevo": nuevo_estado
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