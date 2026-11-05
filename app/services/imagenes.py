import os
import uuid
import pyodbc

from pathlib import Path
from datetime import datetime

from app.db.connection import get_connection


# Configuración de almacenamiento
BASE_DIR = Path(__file__).resolve().parents[2]

STORAGE_DIR = BASE_DIR / "storage" / "productos"

MAX_SIZE = 5 * 1024 * 1024

FORMATOS_PERMITIDOS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}


class ProductNotFound(Exception):
    pass


class ProductForbidden(Exception):
    pass


class ImageLimitExceeded(Exception):
    pass


class InvalidImage(Exception):
    pass


def guardar_imagen(
    id_producto: int,
    id_vendedor: int,
    contenido: bytes,
    extension: str
):
    connection = None
    cursor = None
    ruta_archivo = None

    try:
        extension = extension.lower()

        # Validar formato
        if extension not in FORMATOS_PERMITIDOS:
            raise InvalidImage(
                "Formato de imagen no permitido."
            )

        # Validar tamaño
        if not contenido or len(contenido) > MAX_SIZE:
            raise InvalidImage(
                "La imagen está vacía o supera los 5 MB."
            )

        # Validar contenido real de la imagen
        firmas = {
            ".jpg": (contenido.startswith(b"\xff\xd8\xff")),
            ".jpeg": (contenido.startswith(b"\xff\xd8\xff")),
            ".png": (contenido.startswith(b"\x89PNG\r\n\x1a\n")),
            ".webp": (
                len(contenido) >= 12
                and contenido[:4] == b"RIFF"
                and contenido[8:12] == b"WEBP"
            )
        }

        if not firmas[extension]:
            raise InvalidImage(
                "El contenido no corresponde al formato indicado."
            )

        connection = get_connection()
        cursor = connection.cursor()

        # Verificar propiedad y estado del producto
        cursor.execute(
            """
            SELECT IdVendedor, Estado
            FROM Productos WITH (UPDLOCK, ROWLOCK)
            WHERE IdProducto = ?;
            """,
            id_producto
        )

        producto = cursor.fetchone()

        if producto is None or producto.Estado == "ELIMINADO":
            raise ProductNotFound(
                "El producto no existe o fue eliminado."
            )

        if producto.IdVendedor != id_vendedor:
            raise ProductForbidden(
                "No tienes permiso para agregar imágenes a este producto."
            )

        # Máximo de 5 imágenes por producto
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM ImagenesProducto
            WHERE IdProducto = ?;
            """,
            id_producto
        )

        total_imagenes = cursor.fetchone()[0]

        if total_imagenes >= 5:
            raise ImageLimitExceeded(
                "El producto ya tiene el máximo de 5 imágenes."
            )

        # Crear carpeta del producto
        carpeta = STORAGE_DIR / str(id_producto)
        carpeta.mkdir(parents=True, exist_ok=True)

        # Generar nombre único
        nombre_archivo = f"{uuid.uuid4().hex}{extension}"

        ruta_archivo = carpeta / nombre_archivo

        # Guardar archivo físicamente
        with open(ruta_archivo, "xb") as archivo:
            archivo.write(contenido)

        # Guardar ruta relativa en SQL Server
        ruta_relativa = (
            f"storage/productos/{id_producto}/{nombre_archivo}"
        )

        es_principal = total_imagenes == 0

        cursor.execute(
            """
            INSERT INTO ImagenesProducto (
                IdProducto,
                RutaImagen,
                EsPrincipal,
                FechaRegistro
            )
            OUTPUT INSERTED.IdImagen
            VALUES (?, ?, ?, ?);
            """,
            id_producto,
            ruta_relativa,
            es_principal,
            datetime.now()
        )

        id_imagen = cursor.fetchone()[0]

        connection.commit()

        return {
            "id_imagen": id_imagen,
            "id_producto": id_producto,
            "ruta": ruta_relativa,
            "es_principal": es_principal
        }

    except Exception:
        if connection:
            connection.rollback()

        if ruta_archivo and ruta_archivo.exists():
            ruta_archivo.unlink()

        raise

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()
def listar_imagenes_producto(id_producto: int):
    conexion = get_connection()
    cursor = conexion.cursor()

    try:
        cursor.execute("""
            SELECT
                IdImagen,
                IdProducto,
                RutaImagen,
                EsPrincipal,
                FechaRegistro
            FROM ImagenesProducto
            WHERE IdProducto = ?
            ORDER BY EsPrincipal DESC, IdImagen ASC
        """, (id_producto,))

        filas = cursor.fetchall()

        return [
            {
                "id_imagen": fila.IdImagen,
                "id_producto": fila.IdProducto,
                "ruta": fila.RutaImagen,
                "es_principal": bool(fila.EsPrincipal),
                "fecha_registro": fila.FechaRegistro
            }
            for fila in filas
        ]

    finally:
        cursor.close()
        conexion.close()
def cambiar_imagen_principal(id_producto: int, id_imagen: int, id_vendedor: int):
    conexion = get_connection()
    cursor = conexion.cursor()

    try:
        cursor.execute("""
            SELECT IdVendedor, Estado
            FROM Productos WITH (UPDLOCK, ROWLOCK)
            WHERE IdProducto = ?
        """, (id_producto,))

        producto = cursor.fetchone()

        if not producto or producto.Estado == "ELIMINADO":
            raise ProductNotFound("El producto no existe.")

        if producto.IdVendedor != id_vendedor:
            raise ProductForbidden("No puedes modificar las imágenes de este producto.")

        cursor.execute("""
            SELECT IdImagen
            FROM ImagenesProducto
            WHERE IdImagen = ? AND IdProducto = ?
        """, (id_imagen, id_producto))

        imagen = cursor.fetchone()

        if not imagen:
            raise InvalidImage("La imagen no pertenece a este producto.")

        cursor.execute("""
            UPDATE ImagenesProducto
            SET EsPrincipal = CASE
                WHEN IdImagen = ? THEN 1
                ELSE 0
            END
            WHERE IdProducto = ?
        """, (id_imagen, id_producto))

        conexion.commit()

        return {
            "mensaje": "Imagen principal actualizada correctamente.",
            "id_producto": id_producto,
            "id_imagen_principal": id_imagen
        }

    except Exception:
        conexion.rollback()
        raise

    finally:
        cursor.close()
        conexion.close()

def eliminar_imagen(id_producto: int, id_imagen: int, id_vendedor: int):
    conexion = get_connection()
    cursor = conexion.cursor()

    ruta_archivo = None
    ruta_fisica = None
    era_principal = False
    siguiente = None
    archivo_eliminado = False

    try:
        # Verificar producto y propietario
        cursor.execute("""
            SELECT IdVendedor, Estado
            FROM Productos WITH (UPDLOCK, ROWLOCK)
            WHERE IdProducto = ?
        """, (id_producto,))

        producto = cursor.fetchone()

        if not producto or producto.Estado == "ELIMINADO":
            raise ProductNotFound("El producto no existe.")

        if producto.IdVendedor != id_vendedor:
            raise ProductForbidden(
                "No puedes eliminar imágenes de este producto."
            )

        # Consultar imagen
        cursor.execute("""
            SELECT RutaImagen, EsPrincipal
            FROM ImagenesProducto
            WHERE IdImagen = ? AND IdProducto = ?
        """, (id_imagen, id_producto))

        imagen = cursor.fetchone()

        if not imagen:
            raise InvalidImage(
                "La imagen no pertenece a este producto."
            )

        ruta_archivo = imagen.RutaImagen
        era_principal = bool(imagen.EsPrincipal)

        # Validar que la ruta esté dentro del almacenamiento permitido
        if ruta_archivo:
            try:
                ruta_fisica = (
                    BASE_DIR / ruta_archivo
                ).resolve()

                ruta_fisica.relative_to(STORAGE_DIR.resolve())

            except (ValueError, OSError):
                raise InvalidImage(
                    "La ruta de la imagen no es válida."
                )

        # Eliminar registro de imagen
        cursor.execute("""
            DELETE FROM ImagenesProducto
            WHERE IdImagen = ? AND IdProducto = ?
        """, (id_imagen, id_producto))

        # Si era principal, seleccionar otra automáticamente
        if era_principal:
            cursor.execute("""
                SELECT TOP 1 IdImagen
                FROM ImagenesProducto
                WHERE IdProducto = ?
                ORDER BY IdImagen ASC
            """, (id_producto,))

            siguiente = cursor.fetchone()

            if siguiente:
                cursor.execute("""
                    UPDATE ImagenesProducto
                    SET EsPrincipal = 1
                    WHERE IdImagen = ?
                """, (siguiente.IdImagen,))

        # Confirmar cambios en SQL Server
        conexion.commit()

        # Eliminar archivo físico después del commit
        if ruta_fisica:
            try:
                ruta_fisica.unlink(missing_ok=True)
                archivo_eliminado = True
            except OSError:
                archivo_eliminado = False

        return {
            "mensaje": "Imagen eliminada correctamente.",
            "id_producto": id_producto,
            "id_imagen": id_imagen,
            "nueva_principal_asignada": (
                era_principal and siguiente is not None
            ),
            "archivo_fisico_eliminado": archivo_eliminado
        }

    except Exception:
        conexion.rollback()
        raise

    finally:
        cursor.close()
        conexion.close()
