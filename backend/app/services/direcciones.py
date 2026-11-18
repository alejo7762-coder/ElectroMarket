import pyodbc

from app.db.connection import get_connection
from app.services.carrito import UserNotActive


class AddressNotFound(Exception):
    pass


class AddressInUse(Exception):
    pass


def _verificar_usuario_activo(cursor, id_usuario: int):
    cursor.execute(
        "SELECT Estado FROM Usuarios WHERE IdUsuario = ?;",
        (id_usuario,)
    )

    usuario = cursor.fetchone()

    if usuario is None or usuario.Estado != "ACTIVO":
        raise UserNotActive("El usuario no existe o no está activo.")


def _a_diccionario(fila):
    return {
        "id_direccion": fila.IdDireccion,
        "direccion": fila.Direccion,
        "ciudad": fila.Ciudad,
        "departamento": fila.Departamento,
        "codigo_postal": fila.CodigoPostal
    }


def listar_direcciones(id_usuario: int):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        _verificar_usuario_activo(cursor, id_usuario)

        cursor.execute(
            """
            SELECT IdDireccion, Direccion, Ciudad, Departamento, CodigoPostal
            FROM Direcciones
            WHERE IdUsuario = ?
            ORDER BY IdDireccion;
            """,
            (id_usuario,)
        )

        return [_a_diccionario(fila) for fila in cursor.fetchall()]

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def obtener_direccion(id_usuario: int, id_direccion: int):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT IdDireccion, Direccion, Ciudad, Departamento, CodigoPostal
            FROM Direcciones
            WHERE IdDireccion = ?
              AND IdUsuario = ?;
            """,
            (id_direccion, id_usuario)
        )

        fila = cursor.fetchone()

        if fila is None:
            raise AddressNotFound("La dirección no existe o no te pertenece.")

        return _a_diccionario(fila)

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def crear_direccion(
    id_usuario: int,
    direccion: str,
    ciudad: str,
    departamento: str,
    codigo_postal: str | None = None
):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        _verificar_usuario_activo(cursor, id_usuario)

        cursor.execute(
            """
            INSERT INTO Direcciones (
                IdUsuario,
                Direccion,
                Ciudad,
                Departamento,
                CodigoPostal
            )
            OUTPUT INSERTED.IdDireccion
            VALUES (?, ?, ?, ?, ?);
            """,
            (id_usuario, direccion, ciudad, departamento, codigo_postal)
        )

        id_direccion = cursor.fetchone()[0]
        connection.commit()

        return {
            "mensaje": "Dirección registrada correctamente.",
            "id_direccion": id_direccion,
            "direccion": direccion,
            "ciudad": ciudad,
            "departamento": departamento,
            "codigo_postal": codigo_postal
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


def actualizar_direccion(
    id_usuario: int,
    id_direccion: int,
    direccion: str,
    ciudad: str,
    departamento: str,
    codigo_postal: str | None = None
):
    """
    Los pedidos guardan una copia de la dirección de entrega,
    por eso editar una dirección no altera los pedidos ya realizados.
    """
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        _verificar_usuario_activo(cursor, id_usuario)

        cursor.execute(
            """
            UPDATE Direcciones
            SET Direccion = ?,
                Ciudad = ?,
                Departamento = ?,
                CodigoPostal = ?
            WHERE IdDireccion = ?
              AND IdUsuario = ?;
            """,
            (
                direccion,
                ciudad,
                departamento,
                codigo_postal,
                id_direccion,
                id_usuario
            )
        )

        if cursor.rowcount != 1:
            raise AddressNotFound("La dirección no existe o no te pertenece.")

        connection.commit()

        return {
            "mensaje": "Dirección actualizada correctamente.",
            "id_direccion": id_direccion,
            "direccion": direccion,
            "ciudad": ciudad,
            "departamento": departamento,
            "codigo_postal": codigo_postal
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


def eliminar_direccion(id_usuario: int, id_direccion: int):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        _verificar_usuario_activo(cursor, id_usuario)

        cursor.execute(
            """
            SELECT IdDireccion
            FROM Direcciones
            WHERE IdDireccion = ?
              AND IdUsuario = ?;
            """,
            (id_direccion, id_usuario)
        )

        if cursor.fetchone() is None:
            raise AddressNotFound("La dirección no existe o no te pertenece.")

        cursor.execute(
            "SELECT TOP 1 1 FROM Pedidos WHERE IdDireccion = ?;",
            (id_direccion,)
        )

        if cursor.fetchone():
            raise AddressInUse(
                "La dirección ya se usó en un pedido y no se puede eliminar."
            )

        cursor.execute(
            """
            DELETE FROM Direcciones
            WHERE IdDireccion = ?
              AND IdUsuario = ?;
            """,
            (id_direccion, id_usuario)
        )

        if cursor.rowcount != 1:
            raise AddressNotFound("La dirección no existe o no te pertenece.")

        connection.commit()

        return {
            "mensaje": "Dirección eliminada correctamente.",
            "id_direccion": id_direccion
        }

    except pyodbc.IntegrityError:
        # Otra tabla la referencia por clave foránea
        if connection:
            connection.rollback()
        raise AddressInUse(
            "La dirección está siendo usada y no se puede eliminar."
        )

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()
