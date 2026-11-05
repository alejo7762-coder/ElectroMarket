import pyodbc
from argon2 import PasswordHasher
from argon2.exceptions import HashingError

from app.db.connection import get_connection


password_hasher = PasswordHasher()


class EmailAlreadyExists(Exception):
    pass


def registrar_usuario(nombre, apellido, correo, contrasena, telefono=None):
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
                (Nombre, Apellido, Correo, ContrasenaHash, Telefono)
            OUTPUT INSERTED.IdUsuario
            VALUES (?, ?, ?, ?, ?);
        """

        cursor.execute(
            consulta,
            nombre,
            apellido,
            correo,
            contrasena_hash,
            telefono
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
from argon2.exceptions import (
    VerifyMismatchError,
    VerificationError,
    InvalidHashError
)


class InvalidCredentials(Exception):
    pass


class AccountInactive(Exception):
    pass


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