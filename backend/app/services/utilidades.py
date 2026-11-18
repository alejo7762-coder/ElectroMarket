"""
Funciones de apoyo compartidas por los módulos de pedidos, pagos,
ventas y cancelaciones.
"""

from decimal import Decimal

from app.services.carrito import UserNotActive


# Posibles nombres de la columna de fecha de creación en cada tabla.
# Se consulta con SELECT * para no depender del nombre exacto.
COLUMNAS_FECHA = (
    "FechaPedido",
    "FechaVenta",
    "FechaCreacion",
    "FechaRegistro",
    "Fecha"
)


def iso(valor):
    return valor.isoformat() if valor else None


def a_float(valor):
    if valor is None:
        return 0.0

    return float(Decimal(str(valor)))


def fecha_creacion(fila):
    for columna in COLUMNAS_FECHA:
        try:
            valor = getattr(fila, columna)
        except AttributeError:
            continue

        return iso(valor)

    return None


def verificar_usuario_activo(cursor, id_usuario: int):
    cursor.execute(
        "SELECT Estado FROM Usuarios WHERE IdUsuario = ?;",
        (id_usuario,)
    )

    usuario = cursor.fetchone()

    if usuario is None or usuario.Estado != "ACTIVO":
        raise UserNotActive("El usuario no existe o no está activo.")
