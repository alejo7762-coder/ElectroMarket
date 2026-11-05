import uuid
from decimal import Decimal, ROUND_HALF_UP

from app.db.connection import get_connection
from app.services.carrito import UserNotActive, CartProcessed
from app.services.utilidades import (
    a_float,
    fecha_creacion,
    iso,
    verificar_usuario_activo
)


CENTAVOS = Decimal("0.01")

# Regla de simulación: tarjetas que terminan en estos dígitos se rechazan
TARJETA_RECHAZADA_TERMINACION = "0000"


class EmptyCart(Exception):
    pass


class AddressNotFound(Exception):
    pass


class PurchaseValidationError(Exception):
    def __init__(self, problemas: list):
        super().__init__(
            "El carrito contiene productos que no se pueden comprar."
        )
        self.problemas = problemas


def _simular_pago(metodo: str, numero_tarjeta: str | None):
    """
    Devuelve (aprobado, mensaje). No guarda ni registra el número de tarjeta.
    """
    if metodo == "TARJETA_SIMULADA":
        if numero_tarjeta and numero_tarjeta.endswith(
            TARJETA_RECHAZADA_TERMINACION
        ):
            return False, "Tarjeta rechazada por la entidad (simulación)."

    return True, "Pago aprobado (simulación)."


def _registrar_historial(
    cursor,
    tipo: str,
    id_operacion: int,
    estado_anterior,
    estado_nuevo: str,
    observacion=None
):
    cursor.execute(
        """
        INSERT INTO HistorialEstados (
            TipoOperacion,
            IdOperacion,
            EstadoAnterior,
            EstadoNuevo,
            Observacion
        )
        VALUES (?, ?, ?, ?, ?);
        """,
        (tipo, id_operacion, estado_anterior, estado_nuevo, observacion)
    )


def procesar_compra(
    id_usuario: int,
    id_direccion: int,
    metodo_pago: str,
    numero_tarjeta: str | None = None
):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        # 1. Verificar y bloquear al usuario (evita compras duplicadas
        #    simultáneas del mismo comprador)
        cursor.execute(
            """
            SELECT Estado
            FROM Usuarios WITH (UPDLOCK, ROWLOCK)
            WHERE IdUsuario = ?;
            """,
            (id_usuario,)
        )

        usuario = cursor.fetchone()

        if usuario is None or usuario.Estado != "ACTIVO":
            raise UserNotActive(
                "El usuario no existe o no está activo."
            )

        # 2. Verificar y bloquear el carrito
        cursor.execute(
            """
            SELECT IdCarrito, Estado
            FROM Carritos WITH (UPDLOCK, HOLDLOCK)
            WHERE IdUsuario = ?;
            """,
            (id_usuario,)
        )

        carrito = cursor.fetchone()

        if carrito is None:
            raise EmptyCart("El carrito está vacío.")

        if carrito.Estado == "PROCESADO":
            raise CartProcessed("El carrito ya fue procesado.")

        if carrito.Estado != "ACTIVO":
            raise EmptyCart("El carrito no se encuentra activo.")

        id_carrito = carrito.IdCarrito

        # 3. Validar que la dirección exista y pertenezca al comprador
        cursor.execute(
            """
            SELECT
                IdDireccion,
                Direccion,
                Ciudad,
                Departamento,
                CodigoPostal
            FROM Direcciones
            WHERE IdDireccion = ?
              AND IdUsuario = ?;
            """,
            (id_direccion, id_usuario)
        )

        direccion = cursor.fetchone()

        if direccion is None:
            raise AddressNotFound(
                "La dirección no existe o no te pertenece."
            )

        # 4. Leer los productos del carrito y bloquearlos
        cursor.execute(
            """
            SELECT
                DC.IdProducto,
                DC.Cantidad,
                P.IdVendedor,
                P.Nombre,
                P.Precio,
                P.Stock,
                P.Estado,
                U.Estado AS EstadoVendedor
            FROM DetallesCarrito DC
            INNER JOIN Productos P WITH (UPDLOCK, ROWLOCK)
                ON DC.IdProducto = P.IdProducto
            INNER JOIN Usuarios U
                ON P.IdVendedor = U.IdUsuario
            WHERE DC.IdCarrito = ?
            ORDER BY DC.IdProducto;
            """,
            (id_carrito,)
        )

        items = cursor.fetchall()

        if not items:
            raise EmptyCart("El carrito está vacío.")

        # 5. Revalidar stock y disponibilidad
        problemas = []

        for item in items:
            motivo = None

            if item.IdVendedor == id_usuario:
                motivo = "No puedes comprar tus propios productos."
            elif item.EstadoVendedor != "ACTIVO":
                motivo = "El vendedor no tiene una cuenta activa."
            elif item.Estado != "PUBLICADO":
                motivo = "El producto no está disponible para la compra."
            elif item.Stock < item.Cantidad:
                motivo = (
                    f"Stock insuficiente: disponibles {item.Stock}, "
                    f"en el carrito {item.Cantidad}."
                )

            if motivo:
                problemas.append({
                    "id_producto": item.IdProducto,
                    "nombre": item.Nombre,
                    "motivo": motivo
                })

        if problemas:
            raise PurchaseValidationError(problemas)

        # 6. Calcular subtotales y total con los precios actuales
        lineas = []
        subtotales_vendedor = {}
        total = Decimal("0.00")

        for item in items:
            precio = Decimal(str(item.Precio))
            subtotal = (precio * item.Cantidad).quantize(
                CENTAVOS, rounding=ROUND_HALF_UP
            )

            lineas.append({
                "id_producto": item.IdProducto,
                "id_vendedor": item.IdVendedor,
                "nombre": item.Nombre,
                "cantidad": item.Cantidad,
                "precio": precio,
                "subtotal": subtotal
            })

            subtotales_vendedor[item.IdVendedor] = (
                subtotales_vendedor.get(item.IdVendedor, Decimal("0.00"))
                + subtotal
            )

            total += subtotal

        # 7. Crear el pedido con copia de la dirección de entrega
        cursor.execute(
            """
            INSERT INTO Pedidos (
                IdComprador,
                IdDireccion,
                DireccionEntrega,
                CiudadEntrega,
                DepartamentoEntrega,
                CodigoPostalEntrega,
                Total,
                Estado
            )
            OUTPUT INSERTED.IdPedido
            VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDIENTE_PAGO');
            """,
            (
                id_usuario,
                direccion.IdDireccion,
                direccion.Direccion,
                direccion.Ciudad,
                direccion.Departamento,
                direccion.CodigoPostal,
                total
            )
        )

        id_pedido = cursor.fetchone()[0]

        _registrar_historial(
            cursor, "PEDIDO", id_pedido,
            None, "PENDIENTE_PAGO", "Pedido creado."
        )

        # 8. Crear los detalles del pedido
        for linea in lineas:
            cursor.execute(
                """
                INSERT INTO DetallesPedido (
                    IdPedido,
                    IdProducto,
                    IdVendedor,
                    Cantidad,
                    PrecioUnitario,
                    Subtotal
                )
                OUTPUT INSERTED.IdDetallePedido
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    id_pedido,
                    linea["id_producto"],
                    linea["id_vendedor"],
                    linea["cantidad"],
                    linea["precio"],
                    linea["subtotal"]
                )
            )

            linea["id_detalle_pedido"] = cursor.fetchone()[0]

        # 9. Registrar el pago simulado
        referencia = f"SIM-{uuid.uuid4().hex[:12].upper()}"

        cursor.execute(
            """
            INSERT INTO Pagos (IdPedido, Valor, Metodo, Estado, Referencia)
            OUTPUT INSERTED.IdPago
            VALUES (?, ?, ?, 'PENDIENTE', ?);
            """,
            (id_pedido, total, metodo_pago, referencia)
        )

        id_pago = cursor.fetchone()[0]

        aprobado, mensaje_pago = _simular_pago(metodo_pago, numero_tarjeta)

        # 10. Pago rechazado: se deja evidencia y no se toca inventario
        if not aprobado:
            cursor.execute(
                """
                UPDATE Pagos
                SET Estado = 'RECHAZADO',
                    FechaPago = SYSDATETIME()
                WHERE IdPago = ?;
                """,
                (id_pago,)
            )

            cursor.execute(
                """
                UPDATE Pedidos
                SET Estado = 'CANCELADO'
                WHERE IdPedido = ?;
                """,
                (id_pedido,)
            )

            _registrar_historial(
                cursor, "PEDIDO", id_pedido,
                "PENDIENTE_PAGO", "CANCELADO", mensaje_pago
            )

            connection.commit()

            return {
                "mensaje": mensaje_pago,
                "id_pedido": id_pedido,
                "estado_pedido": "CANCELADO",
                "total": float(total),
                "pago": {
                    "id_pago": id_pago,
                    "estado": "RECHAZADO",
                    "metodo": metodo_pago,
                    "referencia": referencia
                },
                "ventas": []
            }

        # 11. Pago aprobado
        cursor.execute(
            """
            UPDATE Pagos
            SET Estado = 'APROBADO',
                FechaPago = SYSDATETIME()
            WHERE IdPago = ?;
            """,
            (id_pago,)
        )

        cursor.execute(
            """
            UPDATE Pedidos
            SET Estado = 'PAGADO'
            WHERE IdPedido = ?;
            """,
            (id_pedido,)
        )

        _registrar_historial(
            cursor, "PEDIDO", id_pedido,
            "PENDIENTE_PAGO", "PAGADO", mensaje_pago
        )

        # 12. Descontar inventario (condicional: nunca deja stock negativo)
        for linea in lineas:
            cursor.execute(
                """
                UPDATE Productos
                SET Stock = Stock - ?,
                    Estado = CASE
                        WHEN Stock - ? = 0 THEN 'AGOTADO'
                        ELSE Estado
                    END
                WHERE IdProducto = ?
                  AND Stock >= ?
                  AND Estado = 'PUBLICADO';
                """,
                (
                    linea["cantidad"],
                    linea["cantidad"],
                    linea["id_producto"],
                    linea["cantidad"]
                )
            )

            if cursor.rowcount != 1:
                raise PurchaseValidationError([{
                    "id_producto": linea["id_producto"],
                    "nombre": linea["nombre"],
                    "motivo": "El stock cambió durante la compra."
                }])

        # 13. Crear una venta por cada vendedor
        ventas = []

        for id_vendedor, subtotal in subtotales_vendedor.items():
            cursor.execute(
                """
                INSERT INTO Ventas (IdPedido, IdVendedor, Subtotal)
                OUTPUT INSERTED.IdVenta
                VALUES (?, ?, ?);
                """,
                (id_pedido, id_vendedor, subtotal)
            )

            id_venta = cursor.fetchone()[0]

            for linea in lineas:
                if linea["id_vendedor"] == id_vendedor:
                    cursor.execute(
                        """
                        INSERT INTO DetalleVenta (
                            IdVenta,
                            IdDetallePedido,
                            IdVendedor
                        )
                        VALUES (?, ?, ?);
                        """,
                        (id_venta, linea["id_detalle_pedido"], id_vendedor)
                    )

            _registrar_historial(
                cursor, "VENTA", id_venta,
                None, "PENDIENTE", "Venta creada por pedido pagado."
            )

            ventas.append({
                "id_venta": id_venta,
                "id_vendedor": id_vendedor,
                "subtotal": float(subtotal),
                "estado": "PENDIENTE"
            })

        # 14. Vaciar el carrito (queda ACTIVO para futuras compras)
        cursor.execute(
            "DELETE FROM DetallesCarrito WHERE IdCarrito = ?;",
            (id_carrito,)
        )

        cursor.execute(
            """
            UPDATE Carritos
            SET FechaActualizacion = SYSDATETIME()
            WHERE IdCarrito = ?;
            """,
            (id_carrito,)
        )

        connection.commit()

        return {
            "mensaje": "Compra realizada correctamente.",
            "id_pedido": id_pedido,
            "estado_pedido": "PAGADO",
            "total": float(total),
            "pago": {
                "id_pago": id_pago,
                "estado": "APROBADO",
                "metodo": metodo_pago,
                "referencia": referencia
            },
            "ventas": ventas,
            "productos": [
                {
                    "id_producto": l["id_producto"],
                    "nombre": l["nombre"],
                    "cantidad": l["cantidad"],
                    "precio_unitario": float(l["precio"]),
                    "subtotal": float(l["subtotal"])
                }
                for l in lineas
            ]
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

# ----------------------------------------------------------------------
# Consultas de pedidos (comprador)
# ----------------------------------------------------------------------

class OrderNotFound(Exception):
    pass


ESTADOS_PEDIDO = (
    "PENDIENTE_PAGO",
    "PAGADO",
    "EN_PROCESO",
    "PARCIALMENTE_ENVIADO",
    "COMPLETADO",
    "CANCELADO"
)


def listar_pedidos(id_comprador: int, estado: str | None = None):

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        verificar_usuario_activo(cursor, id_comprador)

        consulta = """
            SELECT
                P.*,
                (
                    SELECT COALESCE(SUM(DP.Cantidad), 0)
                    FROM DetallesPedido DP
                    WHERE DP.IdPedido = P.IdPedido
                ) AS Unidades,
                (
                    SELECT COALESCE(SUM(C.MontoReembolso), 0)
                    FROM Cancelaciones C
                    WHERE C.IdPedido = P.IdPedido
                      AND C.Estado = 'APROBADA'
                ) AS TotalCancelado,
                (
                    SELECT TOP 1 PG.Estado
                    FROM Pagos PG
                    WHERE PG.IdPedido = P.IdPedido
                    ORDER BY PG.IdPago DESC
                ) AS EstadoPago
            FROM Pedidos P
            WHERE P.IdComprador = ?
        """
        parametros = [id_comprador]

        if estado:
            consulta += " AND P.Estado = ?"
            parametros.append(estado)

        consulta += " ORDER BY P.IdPedido DESC;"

        cursor.execute(consulta, parametros)

        pedidos = []

        for fila in cursor.fetchall():
            total = a_float(fila.Total)
            cancelado = a_float(fila.TotalCancelado)
            pagado = fila.EstadoPago == "APROBADO"

            pedidos.append({
                "id_pedido": fila.IdPedido,
                "fecha": fecha_creacion(fila),
                "estado": fila.Estado,
                "estado_pago": fila.EstadoPago,
                "unidades": fila.Unidades,
                "total": total,
                "total_cancelado": cancelado,
                # Si el pago no fue aprobado no hay nada cobrado
                "total_neto": round(total - cancelado, 2) if pagado else 0.0,
                "ciudad_entrega": fila.CiudadEntrega
            })

        return pedidos

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def obtener_pedido(id_comprador: int, id_pedido: int):

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM Pedidos
            WHERE IdPedido = ?
              AND IdComprador = ?;
            """,
            (id_pedido, id_comprador)
        )

        pedido = cursor.fetchone()

        if pedido is None:
            raise OrderNotFound("Pedido no encontrado.")

        # Productos del pedido con las unidades ya canceladas
        cursor.execute(
            """
            SELECT
                DP.IdDetallePedido,
                DP.IdProducto,
                DP.IdVendedor,
                DP.Cantidad,
                DP.PrecioUnitario,
                DP.Subtotal,
                PR.Nombre,
                U.Nombre + ' ' + U.Apellido AS Vendedor,
                IP.RutaImagen,
                DV.IdVenta,
                COALESCE(CAN.Cancelada, 0) AS CantidadCancelada
            FROM DetallesPedido DP
            INNER JOIN Productos PR ON PR.IdProducto = DP.IdProducto
            INNER JOIN Usuarios U ON U.IdUsuario = DP.IdVendedor
            LEFT JOIN ImagenesProducto IP
                ON IP.IdProducto = DP.IdProducto
               AND IP.EsPrincipal = 1
            LEFT JOIN DetalleVenta DV
                ON DV.IdDetallePedido = DP.IdDetallePedido
            LEFT JOIN (
                SELECT DC.IdDetallePedido, SUM(DC.Cantidad) AS Cancelada
                FROM DetallesCancelacion DC
                INNER JOIN Cancelaciones C
                    ON C.IdCancelacion = DC.IdCancelacion
                WHERE C.Estado = 'APROBADA'
                GROUP BY DC.IdDetallePedido
            ) CAN ON CAN.IdDetallePedido = DP.IdDetallePedido
            WHERE DP.IdPedido = ?
            ORDER BY DP.IdDetallePedido;
            """,
            (id_pedido,)
        )

        productos = []

        for fila in cursor.fetchall():
            productos.append({
                "id_detalle_pedido": fila.IdDetallePedido,
                "id_producto": fila.IdProducto,
                "nombre": fila.Nombre,
                "imagen_principal": fila.RutaImagen,
                "id_vendedor": fila.IdVendedor,
                "vendedor": fila.Vendedor,
                "id_venta": fila.IdVenta,
                "cantidad": fila.Cantidad,
                "cantidad_cancelada": fila.CantidadCancelada,
                "cantidad_vigente": fila.Cantidad - fila.CantidadCancelada,
                "precio_unitario": a_float(fila.PrecioUnitario),
                "subtotal": a_float(fila.Subtotal)
            })

        # Pagos
        cursor.execute(
            """
            SELECT IdPago, Valor, Metodo, Estado, Referencia, FechaPago
            FROM Pagos
            WHERE IdPedido = ?
            ORDER BY IdPago;
            """,
            (id_pedido,)
        )

        pagos = [
            {
                "id_pago": p.IdPago,
                "valor": a_float(p.Valor),
                "metodo": p.Metodo,
                "estado": p.Estado,
                "referencia": p.Referencia,
                "fecha_pago": iso(p.FechaPago)
            }
            for p in cursor.fetchall()
        ]

        # Ventas (una por vendedor) y su envío
        cursor.execute(
            """
            SELECT
                V.IdVenta,
                V.IdVendedor,
                V.Subtotal,
                V.Estado,
                U.Nombre + ' ' + U.Apellido AS Vendedor,
                E.IdEnvio,
                E.Transportadora,
                E.NumeroGuia,
                E.Estado AS EstadoEnvio
            FROM Ventas V
            INNER JOIN Usuarios U ON U.IdUsuario = V.IdVendedor
            LEFT JOIN Envios E ON E.IdVenta = V.IdVenta
            WHERE V.IdPedido = ?
            ORDER BY V.IdVenta;
            """,
            (id_pedido,)
        )

        ventas = [
            {
                "id_venta": v.IdVenta,
                "id_vendedor": v.IdVendedor,
                "vendedor": v.Vendedor,
                "subtotal": a_float(v.Subtotal),
                "estado": v.Estado,
                "envio": None if v.IdEnvio is None else {
                    "id_envio": v.IdEnvio,
                    "transportadora": v.Transportadora,
                    "numero_guia": v.NumeroGuia,
                    "estado": v.EstadoEnvio
                }
            }
            for v in cursor.fetchall()
        ]

        # Cancelaciones
        cursor.execute(
            """
            SELECT
                IdCancelacion,
                IdVenta,
                Tipo,
                Estado,
                Motivo,
                MontoReembolso,
                FechaSolicitud,
                FechaResolucion
            FROM Cancelaciones
            WHERE IdPedido = ?
            ORDER BY IdCancelacion;
            """,
            (id_pedido,)
        )

        cancelaciones = [
            {
                "id_cancelacion": c.IdCancelacion,
                "id_venta": c.IdVenta,
                "tipo": c.Tipo,
                "estado": c.Estado,
                "motivo": c.Motivo,
                "monto_reembolso": a_float(c.MontoReembolso),
                "fecha_solicitud": iso(c.FechaSolicitud),
                "fecha_resolucion": iso(c.FechaResolucion)
            }
            for c in cursor.fetchall()
        ]

        total = a_float(pedido.Total)
        total_cancelado = sum(
            c["monto_reembolso"]
            for c in cancelaciones
            if c["estado"] == "APROBADA"
        )

        return {
            "id_pedido": pedido.IdPedido,
            "fecha": fecha_creacion(pedido),
            "estado": pedido.Estado,
            "total": total,
            "total_cancelado": round(total_cancelado, 2),
            "total_neto": (
                round(total - total_cancelado, 2)
                if any(p["estado"] == "APROBADO" for p in pagos)
                else 0.0
            ),
            "entrega": {
                "id_direccion": pedido.IdDireccion,
                "direccion": pedido.DireccionEntrega,
                "ciudad": pedido.CiudadEntrega,
                "departamento": pedido.DepartamentoEntrega,
                "codigo_postal": pedido.CodigoPostalEntrega
            },
            "productos": productos,
            "pagos": pagos,
            "ventas": ventas,
            "cancelaciones": cancelaciones
        }

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def obtener_historial_pedido(id_comprador: int, id_pedido: int):

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT 1 FROM Pedidos WHERE IdPedido = ? AND IdComprador = ?;",
            (id_pedido, id_comprador)
        )

        if cursor.fetchone() is None:
            raise OrderNotFound("Pedido no encontrado.")

        cursor.execute(
            """
            SELECT *
            FROM HistorialEstados
            WHERE (TipoOperacion = 'PEDIDO' AND IdOperacion = ?)
               OR (
                    TipoOperacion = 'VENTA'
                    AND IdOperacion IN (
                        SELECT IdVenta FROM Ventas WHERE IdPedido = ?
                    )
               )
            ORDER BY 1;
            """,
            (id_pedido, id_pedido)
        )

        historial = []

        for fila in cursor.fetchall():
            fecha = None
            for columna in ("FechaCambio", "Fecha", "FechaRegistro"):
                try:
                    fecha = iso(getattr(fila, columna))
                    break
                except AttributeError:
                    continue

            historial.append({
                "tipo": fila.TipoOperacion,
                "id_operacion": fila.IdOperacion,
                "estado_anterior": fila.EstadoAnterior,
                "estado_nuevo": fila.EstadoNuevo,
                "observacion": fila.Observacion,
                "fecha": fecha
            })

        return {"id_pedido": id_pedido, "historial": historial}

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()
