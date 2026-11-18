
"""
Consulta de pagos simulados.

El pago se crea y se aprueba/rechaza dentro de la compra
(app/services/pedidos.py -> procesar_compra). Este módulo solo
permite consultarlos. Nunca se almacena el número de tarjeta.
"""

from app.db.connection import get_connection
from app.services.reembolsos import estado_reembolso_pago, procesar_reembolsos_pendientes
from app.services.utilidades import a_float, iso, verificar_usuario_activo


class PaymentNotFound(Exception):
    pass


def _a_diccionario(fila):
    valor = a_float(fila.Valor)
    reembolsado = a_float(fila.Reembolsado)

    return {
        "reembolsado": reembolsado,
        "reembolso_pendiente": a_float(fila.ReembolsoPendiente),
        "estado_reembolso": estado_reembolso_pago(valor, reembolsado),
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
        P.Estado AS EstadoPedido,
        COALESCE((SELECT SUM(R.Valor) FROM Reembolsos R
                  WHERE R.IdPago = PG.IdPago AND R.Estado = 'PROCESADO'), 0) AS Reembolsado,
        COALESCE((SELECT SUM(R.Valor) FROM Reembolsos R
                  WHERE R.IdPago = PG.IdPago AND R.Estado = 'PENDIENTE'), 0) AS ReembolsoPendiente
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
        procesar_reembolsos_pendientes(cursor, id_usuario)
        connection.commit()

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
        procesar_reembolsos_pendientes(cursor, id_usuario)
        connection.commit()

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

        return resultado

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()
