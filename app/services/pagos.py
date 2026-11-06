
"""
Consulta de pagos simulados.

El pago se crea y se aprueba/rechaza dentro de la compra
(app/services/pedidos.py -> procesar_compra). Este módulo solo
permite consultarlos. Nunca se almacena el número de tarjeta.
"""

from app.db.connection import get_connection
from app.services.utilidades import a_float, iso, verificar_usuario_activo


class PaymentNotFound(Exception):
    pass


def _a_diccionario(fila):
    return {
        "id_pago": fila.IdPago,
        "id_pedido": fila.IdPedido,
        "valor": a_float(fila.Valor),
        "metodo": fila.Metodo,
        "estado": fila.Estado,
        "referencia": fila.Referencia,
        "fecha_pago": iso(fila.FechaPago),
        "estado_pedido": fila.EstadoPedido
    }


_SELECT_PAGOS = """
    SELECT
        PG.IdPago,
        PG.IdPedido,
        PG.Valor,
        PG.Metodo,
        PG.Estado,
        PG.Referencia,
        PG.FechaPago,
        P.Estado AS EstadoPedido
    FROM Pagos PG
    INNER JOIN Pedidos P ON P.IdPedido = PG.IdPedido
"""


def listar_pagos(id_usuario: int):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        verificar_usuario_activo(cursor, id_usuario)

        cursor.execute(
            _SELECT_PAGOS + """
            WHERE P.IdComprador = ?
            ORDER BY PG.IdPago DESC;
            """,
            (id_usuario,)
        )

        return [_a_diccionario(fila) for fila in cursor.fetchall()]

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def obtener_pago(id_usuario: int, id_pago: int):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        verificar_usuario_activo(cursor, id_usuario)

        cursor.execute(
            _SELECT_PAGOS + """
            WHERE PG.IdPago = ?
              AND P.IdComprador = ?;
            """,
            (id_pago, id_usuario)
        )

        fila = cursor.fetchone()

        if fila is None:
            raise PaymentNotFound("Pago no encontrado.")

        resultado = _a_diccionario(fila)

        # Reembolsos simulados asociados a solicitudes aprobadas.
        # La base de datos utiliza Reembolsos.Valor y
        # SolicitudesCancelacion.Estado = 'APROBADA'.
        cursor.execute(
            """
            SELECT COALESCE(SUM(R.Valor), 0) AS Reembolsado
            FROM Reembolsos R
            INNER JOIN SolicitudesCancelacion SC
                ON SC.IdSolicitud = R.IdSolicitud
            WHERE R.IdPago = ?
              AND SC.IdPedido = ?
              AND SC.Estado = 'APROBADA';
            """,
            (fila.IdPago, fila.IdPedido)
        )

        resultado["reembolsado"] = a_float(
            cursor.fetchone().Reembolsado
        )

        return resultado

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()
