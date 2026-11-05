"""
Ventas del vendedor.

Las ventas se crean automáticamente en procesar_compra
(una venta por cada vendedor del pedido) cuando el pago es aprobado,
y en ese mismo momento se descuenta el inventario.
Este módulo permite al vendedor consultarlas.
"""

from app.db.connection import get_connection
from app.services.utilidades import (
    a_float,
    fecha_creacion,
    iso,
    verificar_usuario_activo
)


ESTADOS_VENTA = (
    "PENDIENTE",
    "PREPARANDO",
    "ENVIADA",
    "ENTREGADA",
    "CANCELACION_SOLICITADA",
    "CANCELADA"
)


class SaleNotFound(Exception):
    pass


_SUBCONSULTA_CANCELADO = """
    (
        SELECT COALESCE(SUM(C.MontoReembolso), 0)
        FROM Cancelaciones C
        WHERE C.IdVenta = V.IdVenta
          AND C.Estado = 'APROBADA'
    )
"""


def listar_ventas(id_vendedor: int, estado: str | None = None):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        verificar_usuario_activo(cursor, id_vendedor)

        consulta = f"""
            SELECT
                V.*,
                P.Estado AS EstadoPedido,
                P.CiudadEntrega,
                U.Nombre + ' ' + U.Apellido AS Comprador,
                E.IdEnvio,
                E.Estado AS EstadoEnvio,
                E.NumeroGuia,
                {_SUBCONSULTA_CANCELADO} AS MontoCancelado
            FROM Ventas V
            INNER JOIN Pedidos P ON P.IdPedido = V.IdPedido
            INNER JOIN Usuarios U ON U.IdUsuario = P.IdComprador
            LEFT JOIN Envios E ON E.IdVenta = V.IdVenta
            WHERE V.IdVendedor = ?
        """
        parametros = [id_vendedor]

        if estado:
            consulta += " AND V.Estado = ?"
            parametros.append(estado)

        consulta += " ORDER BY V.IdVenta DESC;"

        cursor.execute(consulta, parametros)

        ventas = []

        for fila in cursor.fetchall():
            subtotal = a_float(fila.Subtotal)
            cancelado = a_float(fila.MontoCancelado)

            ventas.append({
                "id_venta": fila.IdVenta,
                "id_pedido": fila.IdPedido,
                "fecha": fecha_creacion(fila),
                "estado": fila.Estado,
                "estado_pedido": fila.EstadoPedido,
                "comprador": fila.Comprador,
                "ciudad_entrega": fila.CiudadEntrega,
                "subtotal": subtotal,
                "monto_cancelado": cancelado,
                "subtotal_neto": round(subtotal - cancelado, 2),
                "envio": None if fila.IdEnvio is None else {
                    "id_envio": fila.IdEnvio,
                    "estado": fila.EstadoEnvio,
                    "numero_guia": fila.NumeroGuia
                }
            })

        return ventas

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def obtener_venta(id_vendedor: int, id_venta: int):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            f"""
            SELECT
                V.*,
                P.Estado AS EstadoPedido,
                P.DireccionEntrega,
                P.CiudadEntrega,
                P.DepartamentoEntrega,
                P.CodigoPostalEntrega,
                U.Nombre + ' ' + U.Apellido AS Comprador,
                U.Telefono AS TelefonoComprador,
                {_SUBCONSULTA_CANCELADO} AS MontoCancelado
            FROM Ventas V
            INNER JOIN Pedidos P ON P.IdPedido = V.IdPedido
            INNER JOIN Usuarios U ON U.IdUsuario = P.IdComprador
            WHERE V.IdVenta = ?
              AND V.IdVendedor = ?;
            """,
            (id_venta, id_vendedor)
        )

        venta = cursor.fetchone()

        if venta is None:
            raise SaleNotFound("Venta no encontrada.")

        cursor.execute(
            """
            SELECT
                DP.IdDetallePedido,
                DP.IdProducto,
                PR.Nombre,
                DP.Cantidad,
                DP.PrecioUnitario,
                DP.Subtotal,
                COALESCE(CAN.Cancelada, 0) AS CantidadCancelada
            FROM DetalleVenta DV
            INNER JOIN DetallesPedido DP
                ON DP.IdDetallePedido = DV.IdDetallePedido
            INNER JOIN Productos PR ON PR.IdProducto = DP.IdProducto
            LEFT JOIN (
                SELECT DC.IdDetallePedido, SUM(DC.Cantidad) AS Cancelada
                FROM DetallesCancelacion DC
                INNER JOIN Cancelaciones C
                    ON C.IdCancelacion = DC.IdCancelacion
                WHERE C.Estado = 'APROBADA'
                GROUP BY DC.IdDetallePedido
            ) CAN ON CAN.IdDetallePedido = DP.IdDetallePedido
            WHERE DV.IdVenta = ?
            ORDER BY DP.IdDetallePedido;
            """,
            (id_venta,)
        )

        productos = [
            {
                "id_detalle_pedido": f.IdDetallePedido,
                "id_producto": f.IdProducto,
                "nombre": f.Nombre,
                "cantidad": f.Cantidad,
                "cantidad_cancelada": f.CantidadCancelada,
                "cantidad_vigente": f.Cantidad - f.CantidadCancelada,
                "precio_unitario": a_float(f.PrecioUnitario),
                "subtotal": a_float(f.Subtotal)
            }
            for f in cursor.fetchall()
        ]

        cursor.execute(
            """
            SELECT
                IdEnvio,
                Transportadora,
                NumeroGuia,
                Estado,
                FechaDespacho,
                FechaEntrega
            FROM Envios
            WHERE IdVenta = ?;
            """,
            (id_venta,)
        )

        envio = cursor.fetchone()

        cursor.execute(
            """
            SELECT IdCancelacion, Tipo, Estado, Motivo, MontoReembolso,
                   FechaSolicitud, FechaResolucion
            FROM Cancelaciones
            WHERE IdVenta = ?
            ORDER BY IdCancelacion;
            """,
            (id_venta,)
        )

        cancelaciones = [
            {
                "id_cancelacion": c.IdCancelacion,
                "tipo": c.Tipo,
                "estado": c.Estado,
                "motivo": c.Motivo,
                "monto_reembolso": a_float(c.MontoReembolso),
                "fecha_solicitud": iso(c.FechaSolicitud),
                "fecha_resolucion": iso(c.FechaResolucion)
            }
            for c in cursor.fetchall()
        ]

        subtotal = a_float(venta.Subtotal)
        cancelado = a_float(venta.MontoCancelado)

        return {
            "id_venta": venta.IdVenta,
            "id_pedido": venta.IdPedido,
            "fecha": fecha_creacion(venta),
            "estado": venta.Estado,
            "estado_pedido": venta.EstadoPedido,
            "subtotal": subtotal,
            "monto_cancelado": cancelado,
            "subtotal_neto": round(subtotal - cancelado, 2),
            "comprador": {
                "nombre": venta.Comprador,
                "telefono": venta.TelefonoComprador
            },
            "entrega": {
                "direccion": venta.DireccionEntrega,
                "ciudad": venta.CiudadEntrega,
                "departamento": venta.DepartamentoEntrega,
                "codigo_postal": venta.CodigoPostalEntrega
            },
            "productos": productos,
            "envio": None if envio is None else {
                "id_envio": envio.IdEnvio,
                "transportadora": envio.Transportadora,
                "numero_guia": envio.NumeroGuia,
                "estado": envio.Estado,
                "fecha_despacho": iso(envio.FechaDespacho),
                "fecha_entrega": iso(envio.FechaEntrega)
            },
            "cancelaciones": cancelaciones
        }

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def resumen_ventas(id_vendedor: int):
    """
    Totales del vendedor: ventas por estado, unidades vendidas
    (descontando cancelaciones) e ingresos netos.
    """
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        verificar_usuario_activo(cursor, id_vendedor)

        cursor.execute(
            """
            SELECT Estado, COUNT(*) AS Cantidad
            FROM Ventas
            WHERE IdVendedor = ?
            GROUP BY Estado;
            """,
            (id_vendedor,)
        )

        por_estado = {e: 0 for e in ESTADOS_VENTA}

        for fila in cursor.fetchall():
            por_estado[fila.Estado] = fila.Cantidad

        cursor.execute(
            """
            SELECT
                COALESCE(SUM(V.Subtotal), 0) AS Bruto,
                COALESCE((
                    SELECT SUM(C.MontoReembolso)
                    FROM Cancelaciones C
                    INNER JOIN Ventas V2 ON V2.IdVenta = C.IdVenta
                    WHERE V2.IdVendedor = ?
                      AND C.Estado = 'APROBADA'
                ), 0) AS Cancelado
            FROM Ventas V
            WHERE V.IdVendedor = ?;
            """,
            (id_vendedor, id_vendedor)
        )

        montos = cursor.fetchone()

        cursor.execute(
            """
            SELECT
                COALESCE(SUM(DP.Cantidad), 0) AS Unidades,
                COALESCE(SUM(CAN.Cancelada), 0) AS Canceladas
            FROM DetallesPedido DP
            INNER JOIN Pagos PG
                ON PG.IdPedido = DP.IdPedido
               AND PG.Estado = 'APROBADO'
            LEFT JOIN (
                SELECT DC.IdDetallePedido, SUM(DC.Cantidad) AS Cancelada
                FROM DetallesCancelacion DC
                INNER JOIN Cancelaciones C
                    ON C.IdCancelacion = DC.IdCancelacion
                WHERE C.Estado = 'APROBADA'
                GROUP BY DC.IdDetallePedido
            ) CAN ON CAN.IdDetallePedido = DP.IdDetallePedido
            WHERE DP.IdVendedor = ?;
            """,
            (id_vendedor,)
        )

        unidades = cursor.fetchone()

        bruto = a_float(montos.Bruto)
        cancelado = a_float(montos.Cancelado)

        return {
            "ventas_por_estado": por_estado,
            "total_ventas": sum(por_estado.values()),
            "unidades_vendidas": unidades.Unidades - unidades.Canceladas,
            "unidades_canceladas": unidades.Canceladas,
            "ingresos_brutos": bruto,
            "monto_cancelado": cancelado,
            "ingresos_netos": round(bruto - cancelado, 2)
        }

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()
