import pyodbc
from argon2 import PasswordHasher
from argon2.exceptions import (
    VerifyMismatchError,
    VerificationError,
    InvalidHashError
)

from app.db.connection import get_connection


password_hasher = PasswordHasher()


class EmailAlreadyExists(Exception):
    pass


class InvalidCredentials(Exception):
    pass


class AccountInactive(Exception):
    pass


class UserNotFound(Exception):
    pass


def registrar_usuario(
    nombre,
    apellido,
    correo,
    contrasena,
    telefono=None,
    fecha_nacimiento=None,
    genero=None
):
    """
    Registra un usuario en SQL Server.
    La contraseña se almacena mediante un hash Argon2.
    """

    contrasena_hash = password_hasher.hash(contrasena)

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        consulta = """
            INSERT INTO Usuarios
                (Nombre, Apellido, Correo, ContrasenaHash, Telefono,
                 FechaNacimiento, Genero)
            OUTPUT INSERTED.IdUsuario
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """

        cursor.execute(
            consulta,
            nombre,
            apellido,
            correo,
            contrasena_hash,
            telefono,
            fecha_nacimiento,
            genero
        )

        resultado = cursor.fetchone()
        connection.commit()

        return resultado[0]

    except pyodbc.IntegrityError as error:
        if connection:
            connection.rollback()

        mensaje = str(error)

        if "2627" in mensaje or "2601" in mensaje:
            raise EmailAlreadyExists(
                "Ya existe una cuenta registrada con ese correo."
            )

        raise

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def autenticar_usuario(correo, contrasena):
    """
    Busca al usuario y verifica su contraseña mediante Argon2.
    """

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                IdUsuario,
                Nombre,
                Apellido,
                Correo,
                ContrasenaHash,
                Estado
            FROM Usuarios
            WHERE Correo = ?;
        """, correo)

        usuario = cursor.fetchone()

        if usuario is None:
            raise InvalidCredentials()

        try:
            password_hasher.verify(
                usuario.ContrasenaHash,
                contrasena
            )
        except (
            VerifyMismatchError,
            VerificationError,
            InvalidHashError
        ):
            raise InvalidCredentials()

        if usuario.Estado != "ACTIVO":
            raise AccountInactive()

        return {
            "id_usuario": usuario.IdUsuario,
            "nombre": usuario.Nombre,
            "apellido": usuario.Apellido,
            "correo": usuario.Correo
        }

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ----------------------------------------------------------------------
# Perfil
# ----------------------------------------------------------------------

def _perfil_a_diccionario(fila):
    return {
        "id_usuario": fila.IdUsuario,
        "nombre": fila.Nombre,
        "apellido": fila.Apellido,
        "correo": fila.Correo,
        "telefono": fila.Telefono,
        "fecha_nacimiento": (
            fila.FechaNacimiento.isoformat()[:10]
            if fila.FechaNacimiento else None
        ),
        "genero": fila.Genero,
        "fecha_registro": (
            fila.FechaRegistro.isoformat() if fila.FechaRegistro else None
        ),
        "estado": fila.Estado
    }


def obtener_perfil(id_usuario: int):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT IdUsuario, Nombre, Apellido, Correo, Telefono,
                   FechaNacimiento, Genero, FechaRegistro, Estado
            FROM Usuarios
            WHERE IdUsuario = ?;
            """,
            (id_usuario,)
        )

        fila = cursor.fetchone()

        if fila is None:
            raise UserNotFound("Usuario no disponible.")

        if fila.Estado != "ACTIVO":
            raise AccountInactive()

        return _perfil_a_diccionario(fila)

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def actualizar_perfil(
    id_usuario: int,
    nombre: str,
    apellido: str,
    telefono=None,
    fecha_nacimiento=None,
    genero=None
):
    """El correo no se modifica: es el identificador de inicio de sesión."""
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE Usuarios
            SET Nombre = ?,
                Apellido = ?,
                Telefono = ?,
                FechaNacimiento = ?,
                Genero = ?
            WHERE IdUsuario = ?
              AND Estado = 'ACTIVO';
            """,
            (nombre, apellido, telefono, fecha_nacimiento, genero, id_usuario)
        )

        if cursor.rowcount != 1:
            raise UserNotFound("Usuario no disponible.")

        connection.commit()

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()

    return obtener_perfil(id_usuario)


def cambiar_contrasena(id_usuario: int, actual: str, nueva: str):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT ContrasenaHash, Estado
            FROM Usuarios WITH (UPDLOCK, ROWLOCK)
            WHERE IdUsuario = ?;
            """,
            (id_usuario,)
        )

        fila = cursor.fetchone()

        if fila is None or fila.Estado != "ACTIVO":
            raise UserNotFound("Usuario no disponible.")

        try:
            password_hasher.verify(fila.ContrasenaHash, actual)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            raise InvalidCredentials()

        cursor.execute(
            "UPDATE Usuarios SET ContrasenaHash = ? WHERE IdUsuario = ?;",
            (password_hasher.hash(nueva), id_usuario)
        )

        connection.commit()

        return {"mensaje": "Contraseña actualizada correctamente."}

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()
