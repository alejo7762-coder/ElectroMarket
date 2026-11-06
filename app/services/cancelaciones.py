"""
Etapa 10 - Cancelaciones parciales y totales.

Las solicitudes se almacenan en:
- SolicitudesCancelacion
- DetalleSolicitudCancelacion
- Reembolsos

Compatibilidad:
- La base de datos utiliza PENDIENTE.
- La API conserva SOLICITADA para el frontend.
- El pago original conserva el estado APROBADO.
"""

from decimal import Decimal, ROUND_HALF_UP

from app.db.connection import get_connection
from app.services.envios import _sincronizar_estado_pedido
from app.services.pedidos import _registrar_historial
from app.services.utilidades import (
    a_float,
    iso,
    verificar_usuario_activo
)


CENTAVOS = Decimal("0.01")

ESTADOS_PEDIDO_CANCELABLES = (
    "PAGADO",
    "EN_PROCESO",
    "PARCIALMENTE_ENVIADO"
)

ESTADOS_VENTA_SIN_DESPACHAR = ("PENDIENTE", "PREPARANDO")
ESTADOS_ENVIO_FINALES = ("ENTREGADO", "CANCELADO")


class CancellationNotFound(Exception):
    pass


class OrderNotFound(Exception):
    pass


class SaleNotFound(Exception):
    pass


class CancellationConflict(Exception):
    pass


class CancellationForbidden(Exception):
    pass


# ----------------------------------------------------------------------
# Lógica pura
# ----------------------------------------------------------------------

def calcular_lineas_a_cancelar(lineas: list, solicitados: dict | None):
    """
    lineas:
        [{id_detalle_pedido, id_producto, nombre, vigente, precio}]

    solicitados:
        {id_producto: cantidad | None}
        None significa todas las unidades vigentes.
    """
    if solicitados is None:
        resultado = [
            (linea, linea["vigente"])
            for linea in lineas
            if linea["vigente"] > 0
        ]

        if not resultado:
            raise CancellationConflict(
                "No hay unidades vigentes para cancelar."
            )

        return resultado

    por_producto = {
        linea["id_producto"]: linea
        for linea in lineas
    }

    resultado = []

    for id_producto, cantidad in solicitados.items():
        linea = por_producto.get(id_producto)

        if linea is None:
            raise CancellationConflict(
                f"El producto {id_producto} no hace parte de esta venta."
            )

        if linea["vigente"] <= 0:
            raise CancellationConflict(
                f"El producto '{linea['nombre']}' ya fue cancelado."
            )

        cantidad = (
            linea["vigente"]
            if cantidad is None
            else cantidad
        )

        if cantidad <= 0:
            raise CancellationConflict(
                "La cantidad debe ser mayor que cero."
            )

        if cantidad > linea["vigente"]:
            raise CancellationConflict(
                f"Solo puedes cancelar {linea['vigente']} unidad(es) "
                f"de '{linea['nombre']}'."
            )

        resultado.append((linea, cantidad))

    return resultado


def recortar(texto: str, maximo: int = 250) -> str:
    """Limita el texto para los historiales."""
    texto = texto or ""
    return texto if len(texto) <= maximo else texto[:maximo - 3] + "..."


def monto_linea(precio, cantidad: int) -> Decimal:
    return (
        Decimal(str(precio)) * cantidad
    ).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def _estado_api(estado: str) -> str:
    """Convierte el estado de SQL Server al estado esperado por el frontend."""
    return "SOLICITADA" if estado == "PENDIENTE" else estado


def _estado_bd(estado: str) -> str:
    """Convierte el estado recibido por la API al estado de SQL Server."""
    return "PENDIENTE" if estado == "SOLICITADA" else estado


# ----------------------------------------------------------------------
# Apoyo con base de datos
# ----------------------------------------------------------------------

def _bloquear_pedido(cursor, id_pedido: int):
    cursor.execute(
        """
        SELECT IdPedido, IdComprador, Estado
        FROM Pedidos WITH (UPDLOCK, ROWLOCK)
        WHERE IdPedido = ?;
        """,
        (id_pedido,)
    )

    return cursor.fetchone()


def _bloquear_ventas(cursor, id_pedido: int):
    cursor.execute(
        """
        SELECT
            V.IdVenta,
            V.IdVendedor,
            V.Estado,
            E.IdEnvio,
            E.Estado AS EstadoEnvio
        FROM Ventas V WITH (UPDLOCK, ROWLOCK)
        LEFT JOIN Envios E WITH (UPDLOCK, ROWLOCK)
            ON E.IdVenta = V.IdVenta
        WHERE V.IdPedido = ?
        ORDER BY V.IdVenta;
        """,
        (id_pedido,)
    )

    return cursor.fetchall()


def _lineas_venta(cursor, id_venta: int):
    """
    Obtiene las líneas de una venta y descuenta únicamente las cantidades
    pertenecientes a solicitudes que ya fueron aprobadas.
    """
    cursor.execute(
        """
        SELECT
            DP.IdDetallePedido,
            DP.IdProducto,
            PR.Nombre,
            DP.Cantidad,
            DP.PrecioUnitario,
            COALESCE((
                SELECT SUM(DSC.CantidadSolicitada)
                FROM DetalleSolicitudCancelacion DSC
                INNER JOIN SolicitudesCancelacion SC
                    ON SC.IdSolicitud = DSC.IdSolicitud
                WHERE DSC.IdDetallePedido = DP.IdDetallePedido
                  AND SC.Estado = 'APROBADA'
            ), 0) AS Cancelada
        FROM DetalleVenta DV
        INNER JOIN DetallesPedido DP
            ON DP.IdDetallePedido = DV.IdDetallePedido
        INNER JOIN Productos PR
            ON PR.IdProducto = DP.IdProducto
        WHERE DV.IdVenta = ?
        ORDER BY DP.IdDetallePedido;
        """,
        (id_venta,)
    )

    return [
        {
            "id_detalle_pedido": fila.IdDetallePedido,
            "id_producto": fila.IdProducto,
            "nombre": fila.Nombre,
            "cantidad": fila.Cantidad,
            "vigente": fila.Cantidad - fila.Cancelada,
            "precio": fila.PrecioUnitario
        }
        for fila in cursor.fetchall()
    ]


def _obtener_pago(cursor, id_pedido: int):
    """Obtiene el pago asociado al pedido para registrar el reembolso."""
    cursor.execute(
        """
        SELECT IdPago, Estado
        FROM Pagos
        WHERE IdPedido = ?;
        """,
        (id_pedido,)
    )

    pago = cursor.fetchone()

    if pago is None:
        raise CancellationConflict(
            "No se encontró el pago asociado al pedido. "
            "No es posible registrar el reembolso."
        )

    if pago.Estado != "APROBADO":
        raise CancellationConflict(
            "El pago original no está aprobado. "
            "No es posible registrar el reembolso."
        )

    return pago


def _registrar_reembolso(
    cursor,
    id_pedido: int,
    id_solicitud: int,
    monto: Decimal
):
    """
    Registra un reembolso pendiente.

    No modifica el estado del pago original.
    El estado de Reembolsos utiliza el valor predeterminado PENDIENTE.
    """
    if monto <= 0:
        raise CancellationConflict(
            "El valor del reembolso debe ser mayor que cero."
        )

    pago = _obtener_pago(cursor, id_pedido)

    cursor.execute(
        """
        INSERT INTO Reembolsos (
            IdPago,
            IdSolicitud,
            Valor
        )
        VALUES (?, ?, ?);
        """,
        (pago.IdPago, id_solicitud, monto)
    )


def _insertar_cancelacion(
    cursor,
    id_pedido: int,
    venta,
    id_solicitante: int,
    motivo: str,
    lineas_cancelar: list,
    tipo: str,
    estado: str
):
    """
    Inserta una solicitud y sus detalles.

    Si la cancelación es inmediata, se almacena como APROBADA
    y se registra su reembolso.
    Si requiere autorización, se almacena como PENDIENTE.
    """
    monto_total = sum(
        (
            monto_linea(linea["precio"], cantidad)
            for linea, cantidad in lineas_cancelar
        ),
        Decimal("0.00")
    )

    estado_bd = _estado_bd(estado)

    cursor.execute(
        """
        INSERT INTO SolicitudesCancelacion (
            IdPedido,
            IdVenta,
            IdUsuario,
            TipoSolicitud,
            Motivo,
            Estado
        )
        OUTPUT INSERTED.IdSolicitud
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (
            id_pedido,
            venta.IdVenta,
            id_solicitante,
            tipo,
            motivo,
            estado_bd
        )
    )

    id_solicitud = cursor.fetchone()[0]

    for linea, cantidad in lineas_cancelar:
        cursor.execute(
            """
            INSERT INTO DetalleSolicitudCancelacion (
                IdSolicitud,
                IdVenta,
                IdDetallePedido,
                CantidadSolicitada
            )
            VALUES (?, ?, ?, ?);
            """,
            (
                id_solicitud,
                venta.IdVenta,
                linea["id_detalle_pedido"],
                cantidad
            )
        )

    if estado_bd == "APROBADA":
        _registrar_reembolso(
            cursor,
            id_pedido,
            id_solicitud,
            monto_total
        )

    return id_solicitud, monto_total


def _devolver_inventario(cursor, lineas_cancelar: list):
    for linea, cantidad in lineas_cancelar:
        cursor.execute(
            """
            UPDATE Productos
            SET Stock = Stock + ?,
                Estado = CASE
                    WHEN Estado = 'AGOTADO' THEN 'PUBLICADO'
                    ELSE Estado
                END
            WHERE IdProducto = ?;
            """,
            (cantidad, linea["id_producto"])
        )


def _cancelar_venta_y_envio(cursor, venta, observacion: str):
    """Marca la venta y su envío como cancelados."""
    cursor.execute(
        """
        UPDATE Ventas
        SET Estado = 'CANCELADA'
        WHERE IdVenta = ?;
        """,
        (venta.IdVenta,)
    )

    _registrar_historial(
        cursor,
        "VENTA",
        venta.IdVenta,
        venta.Estado,
        "CANCELADA",
        recortar(observacion)
    )

    if (
        venta.IdEnvio is not None
        and venta.EstadoEnvio not in ESTADOS_ENVIO_FINALES
    ):
        cursor.execute(
            """
            UPDATE Envios
            SET Estado = 'CANCELADO'
            WHERE IdEnvio = ?;
            """,
            (venta.IdEnvio,)
        )

        cursor.execute(
            """
            INSERT INTO HistorialEnvios (
                IdEnvio,
                Estado,
                Observacion
            )
            VALUES (?, 'CANCELADO', ?);
            """,
            (venta.IdEnvio, recortar(observacion))
        )


def _aplicar_inmediata(
    cursor,
    id_pedido: int,
    venta,
    id_solicitante: int,
    motivo: str,
    lineas: list,
    lineas_cancelar: list
):
    """Cancela inmediatamente unidades de una venta no despachada."""
    cancelado_por_detalle = {
        linea["id_detalle_pedido"]: cantidad
        for linea, cantidad in lineas_cancelar
    }

    quedan = sum(
        linea["vigente"]
        - cancelado_por_detalle.get(linea["id_detalle_pedido"], 0)
        for linea in lineas
    )

    tipo = "TOTAL" if quedan == 0 else "PARCIAL"

    id_cancelacion, monto = _insertar_cancelacion(
        cursor,
        id_pedido,
        venta,
        id_solicitante,
        motivo,
        lineas_cancelar,
        tipo,
        "APROBADA"
    )

    _devolver_inventario(cursor, lineas_cancelar)

    estado_venta = venta.Estado

    if quedan == 0:
        _cancelar_venta_y_envio(
            cursor,
            venta,
            f"Cancelación #{id_cancelacion}: {motivo}"
        )
        estado_venta = "CANCELADA"

    return {
        "id_cancelacion": id_cancelacion,
        "id_venta": venta.IdVenta,
        "tipo": tipo,
        "estado": "APROBADA",
        "monto_reembolso": float(monto),
        "estado_venta": estado_venta,
        "productos": [
            {
                "id_producto": linea["id_producto"],
                "nombre": linea["nombre"],
                "cantidad_cancelada": cantidad
            }
            for linea, cantidad in lineas_cancelar
        ]
    }


def _crear_solicitud(
    cursor,
    id_pedido: int,
    venta,
    id_solicitante: int,
    motivo: str
):
    """Crea una solicitud de cancelación total para una venta despachada."""
    lineas = _lineas_venta(cursor, venta.IdVenta)
    lineas_cancelar = calcular_lineas_a_cancelar(lineas, None)

    id_cancelacion, monto = _insertar_cancelacion(
        cursor,
        id_pedido,
        venta,
        id_solicitante,
        motivo,
        lineas_cancelar,
        "TOTAL",
        "SOLICITADA"
    )

    cursor.execute(
        """
        UPDATE Ventas
        SET Estado = 'CANCELACION_SOLICITADA'
        WHERE IdVenta = ?;
        """,
        (venta.IdVenta,)
    )

    _registrar_historial(
        cursor,
        "VENTA",
        venta.IdVenta,
        venta.Estado,
        "CANCELACION_SOLICITADA",
        recortar(
            f"Cancelación #{id_cancelacion} solicitada: {motivo}"
        )
    )

    return {
        "id_cancelacion": id_cancelacion,
        "id_venta": venta.IdVenta,
        "tipo": "TOTAL",
        "estado": "SOLICITADA",
        "monto_reembolso": float(monto),
        "estado_venta": "CANCELACION_SOLICITADA",
        "mensaje": (
            "La venta ya fue despachada: "
            "el vendedor debe aprobar la cancelación."
        )
    }


def _validar_pedido_comprador(pedido, id_comprador: int):
    if pedido is None or pedido.IdComprador != id_comprador:
        raise OrderNotFound("Pedido no encontrado.")

    if pedido.Estado not in ESTADOS_PEDIDO_CANCELABLES:
        raise CancellationConflict(
            f"El pedido está en estado {pedido.Estado} "
            "y no se puede cancelar."
        )


def _ejecutar(funcion):
    """Ejecuta una operación dentro de una transacción."""
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        resultado = funcion(cursor)

        connection.commit()
        return resultado

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
# Operaciones públicas
# ----------------------------------------------------------------------

def cancelar_pedido_total(
    id_comprador: int,
    id_pedido: int,
    motivo: str
):
    def operacion(cursor):
        verificar_usuario_activo(cursor, id_comprador)

        pedido = _bloquear_pedido(cursor, id_pedido)
        _validar_pedido_comprador(pedido, id_comprador)

        ventas = _bloquear_ventas(cursor, id_pedido)

        entregadas = [
            venta.IdVenta
            for venta in ventas
            if venta.Estado == "ENTREGADA"
        ]

        if entregadas:
            raise CancellationConflict(
                "El pedido ya tiene entregas realizadas (ventas "
                f"{', '.join(map(str, entregadas))}). Cancela por venta "
                "las partes que aún no se han entregado."
            )

        resultados = []

        for venta in ventas:
            if venta.Estado in ESTADOS_VENTA_SIN_DESPACHAR:
                lineas = _lineas_venta(cursor, venta.IdVenta)
                lineas_cancelar = calcular_lineas_a_cancelar(
                    lineas,
                    None
                )

                resultados.append(
                    _aplicar_inmediata(
                        cursor,
                        id_pedido,
                        venta,
                        id_comprador,
                        motivo,
                        lineas,
                        lineas_cancelar
                    )
                )

            elif venta.Estado == "ENVIADA":
                resultados.append(
                    _crear_solicitud(
                        cursor,
                        id_pedido,
                        venta,
                        id_comprador,
                        motivo
                    )
                )

        if not resultados:
            raise CancellationConflict(
                "No hay partes del pedido pendientes por cancelar."
            )

        estado_pedido = _sincronizar_estado_pedido(
            cursor,
            id_pedido,
            pedido.Estado
        )

        return {
            "mensaje": "Cancelación del pedido procesada.",
            "id_pedido": id_pedido,
            "estado_pedido": estado_pedido,
            "monto_reembolsado": round(
                sum(
                    resultado["monto_reembolso"]
                    for resultado in resultados
                    if resultado["estado"] == "APROBADA"
                ),
                2
            ),
            "cancelaciones": resultados
        }

    return _ejecutar(operacion)


def cancelar_pedido_parcial(
    id_comprador: int,
    id_pedido: int,
    motivo: str,
    productos: dict
):
    """
    productos:
        {id_producto: cantidad | None}
        None significa todas las unidades vigentes de ese producto.
    """
    def operacion(cursor):
        verificar_usuario_activo(cursor, id_comprador)

        pedido = _bloquear_pedido(cursor, id_pedido)
        _validar_pedido_comprador(pedido, id_comprador)

        ventas = _bloquear_ventas(cursor, id_pedido)

        pendientes = dict(productos)
        resultados = []

        for venta in ventas:
            lineas = _lineas_venta(cursor, venta.IdVenta)

            ids_venta = {
                linea["id_producto"]
                for linea in lineas
            }

            solicitados = {
                producto: cantidad
                for producto, cantidad in pendientes.items()
                if producto in ids_venta
            }

            if not solicitados:
                continue

            for producto in solicitados:
                pendientes.pop(producto)

            if venta.Estado == "ENVIADA":
                raise CancellationConflict(
                    f"La venta {venta.IdVenta} ya fue despachada. "
                    "Solo puedes solicitar su cancelación completa en "
                    f"POST /cancelaciones/ventas/{venta.IdVenta}."
                )

            if venta.Estado not in ESTADOS_VENTA_SIN_DESPACHAR:
                raise CancellationConflict(
                    f"La venta {venta.IdVenta} está en estado "
                    f"{venta.Estado} y no admite cancelaciones."
                )

            lineas_cancelar = calcular_lineas_a_cancelar(
                lineas,
                solicitados
            )

            resultados.append(
                _aplicar_inmediata(
                    cursor,
                    id_pedido,
                    venta,
                    id_comprador,
                    motivo,
                    lineas,
                    lineas_cancelar
                )
            )

        if pendientes:
            raise CancellationConflict(
                "Estos productos no hacen parte del pedido: "
                + ", ".join(map(str, pendientes))
            )

        estado_pedido = _sincronizar_estado_pedido(
            cursor,
            id_pedido,
            pedido.Estado
        )

        return {
            "mensaje": "Cancelación parcial aplicada.",
            "id_pedido": id_pedido,
            "estado_pedido": estado_pedido,
            "monto_reembolsado": round(
                sum(
                    resultado["monto_reembolso"]
                    for resultado in resultados
                ),
                2
            ),
            "cancelaciones": resultados
        }

    return _ejecutar(operacion)


def cancelar_venta(
    id_usuario: int,
    id_venta: int,
    motivo: str
):
    """
    Cancela la parte de un vendedor dentro de un pedido.

    Comprador:
    - Inmediata si no se ha despachado.
    - Solicitud si ya fue enviada.

    Vendedor:
    - Solo puede cancelar si todavía no ha despachado.
    """
    def operacion(cursor):
        verificar_usuario_activo(cursor, id_usuario)

        cursor.execute(
            """
            SELECT
                V.IdPedido,
                V.IdVendedor,
                P.IdComprador
            FROM Ventas V
            INNER JOIN Pedidos P
                ON P.IdPedido = V.IdPedido
            WHERE V.IdVenta = ?;
            """,
            (id_venta,)
        )

        datos = cursor.fetchone()

        if datos is None or id_usuario not in (
            datos.IdComprador,
            datos.IdVendedor
        ):
            raise SaleNotFound("Venta no encontrada.")

        es_comprador = id_usuario == datos.IdComprador
        id_pedido = datos.IdPedido

        pedido = _bloquear_pedido(cursor, id_pedido)

        if pedido is None:
            raise OrderNotFound("Pedido no encontrado.")

        if pedido.Estado not in ESTADOS_PEDIDO_CANCELABLES:
            raise CancellationConflict(
                f"El pedido está en estado {pedido.Estado} "
                "y no se puede cancelar."
            )

        venta = next(
            (
                fila
                for fila in _bloquear_ventas(cursor, id_pedido)
                if fila.IdVenta == id_venta
            ),
            None
        )

        if venta is None:
            raise SaleNotFound("Venta no encontrada.")

        if venta.Estado in ESTADOS_VENTA_SIN_DESPACHAR:
            lineas = _lineas_venta(cursor, id_venta)
            lineas_cancelar = calcular_lineas_a_cancelar(
                lineas,
                None
            )

            resultado = _aplicar_inmediata(
                cursor,
                id_pedido,
                venta,
                id_usuario,
                motivo,
                lineas,
                lineas_cancelar
            )

        elif venta.Estado == "ENVIADA":
            if not es_comprador:
                raise CancellationConflict(
                    "La venta ya fue despachada; el vendedor no puede "
                    "cancelarla. Si hay un inconveniente, marca el envío "
                    "como PROBLEMA."
                )

            resultado = _crear_solicitud(
                cursor,
                id_pedido,
                venta,
                id_usuario,
                motivo
            )

        elif venta.Estado == "CANCELACION_SOLICITADA":
            raise CancellationConflict(
                "Ya existe una solicitud de cancelación pendiente "
                "para esta venta."
            )

        else:
            raise CancellationConflict(
                f"La venta está en estado {venta.Estado} "
                "y no se puede cancelar."
            )

        resultado["estado_pedido"] = _sincronizar_estado_pedido(
            cursor,
            id_pedido,
            pedido.Estado
        )

        resultado["id_pedido"] = id_pedido

        return resultado

    return _ejecutar(operacion)


def responder_solicitud(
    id_vendedor: int,
    id_cancelacion: int,
    aprobar: bool,
    observacion: str | None = None
):
    def operacion(cursor):
        verificar_usuario_activo(cursor, id_vendedor)

        # Primero se obtiene la solicitud para conocer el pedido y la venta.
        cursor.execute(
            """
            SELECT
                SC.IdPedido,
                SC.IdVenta,
                V.IdVendedor
            FROM SolicitudesCancelacion SC
            INNER JOIN Ventas V
                ON V.IdVenta = SC.IdVenta
            WHERE SC.IdSolicitud = ?;
            """,
            (id_cancelacion,)
        )

        datos = cursor.fetchone()

        if datos is None:
            raise CancellationNotFound(
                "Solicitud de cancelación no encontrada."
            )

        if datos.IdVendedor != id_vendedor:
            raise CancellationForbidden(
                "Solo el vendedor de la venta puede responder "
                "esta solicitud."
            )

        # Orden de bloqueo: pedido -> ventas/envíos -> solicitud.
        pedido = _bloquear_pedido(cursor, datos.IdPedido)

        if pedido is None:
            raise OrderNotFound("Pedido no encontrado.")

        venta = next(
            (
                fila
                for fila in _bloquear_ventas(cursor, datos.IdPedido)
                if fila.IdVenta == datos.IdVenta
            ),
            None
        )

        if venta is None:
            raise SaleNotFound("Venta no encontrada.")

        cursor.execute(
            """
            SELECT
                Estado,
                Motivo
            FROM SolicitudesCancelacion WITH (UPDLOCK, ROWLOCK)
            WHERE IdSolicitud = ?;
            """,
            (id_cancelacion,)
        )

        solicitud = cursor.fetchone()

        if solicitud is None:
            raise CancellationNotFound(
                "Solicitud de cancelación no encontrada."
            )

        if solicitud.Estado != "PENDIENTE":
            raise CancellationConflict(
                "La solicitud ya fue respondida "
                f"({solicitud.Estado})."
            )

        if venta.Estado != "CANCELACION_SOLICITADA":
            raise CancellationConflict(
                f"La venta está en estado {venta.Estado}; "
                "no se puede responder."
            )

        nuevo_estado = "APROBADA" if aprobar else "RECHAZADA"

        cursor.execute(
            """
            UPDATE SolicitudesCancelacion
            SET Estado = ?,
                FechaRespuesta = SYSDATETIME()
            WHERE IdSolicitud = ?;
            """,
            (nuevo_estado, id_cancelacion)
        )

        if aprobar:
            cursor.execute(
                """
                SELECT
                    DSC.IdDetallePedido,
                    DSC.CantidadSolicitada,
                    DP.IdProducto,
                    DP.PrecioUnitario
                FROM DetalleSolicitudCancelacion DSC
                INNER JOIN DetallesPedido DP
                    ON DP.IdDetallePedido = DSC.IdDetallePedido
                WHERE DSC.IdSolicitud = ?;
                """,
                (id_cancelacion,)
            )

            filas = cursor.fetchall()

            if not filas:
                raise CancellationConflict(
                    "La solicitud no contiene productos para cancelar."
                )

            lineas_cancelar = []
            monto_total = Decimal("0.00")

            for fila in filas:
                linea = {
                    "id_producto": fila.IdProducto
                }

                lineas_cancelar.append(
                    (linea, fila.CantidadSolicitada)
                )

                monto_total += monto_linea(
                    fila.PrecioUnitario,
                    fila.CantidadSolicitada
                )

            _registrar_reembolso(
                cursor,
                datos.IdPedido,
                id_cancelacion,
                monto_total
            )

            _devolver_inventario(
                cursor,
                lineas_cancelar
            )

            _cancelar_venta_y_envio(
                cursor,
                venta,
                f"Cancelación #{id_cancelacion} aprobada por el vendedor."
            )

            estado_venta = "CANCELADA"

        else:
            # La solicitud se rechaza y la venta vuelve a ENVIADA.
            cursor.execute(
                """
                UPDATE Ventas
                SET Estado = 'ENVIADA'
                WHERE IdVenta = ?;
                """,
                (venta.IdVenta,)
            )

            _registrar_historial(
                cursor,
                "VENTA",
                venta.IdVenta,
                "CANCELACION_SOLICITADA",
                "ENVIADA",
                recortar(
                    f"Cancelación #{id_cancelacion} rechazada: "
                    f"{observacion or 'sin observación'}"
                )
            )

            estado_venta = "ENVIADA"

        estado_pedido = _sincronizar_estado_pedido(
            cursor,
            datos.IdPedido,
            pedido.Estado
        )

        return {
            "mensaje": (
                "Cancelación aprobada: inventario devuelto "
                "y reembolso simulado registrado."
                if aprobar
                else "Solicitud de cancelación rechazada."
            ),
            "id_cancelacion": id_cancelacion,
            "estado": nuevo_estado,
            "id_venta": venta.IdVenta,
            "estado_venta": estado_venta,
            "id_pedido": datos.IdPedido,
            "estado_pedido": estado_pedido
        }

    return _ejecutar(operacion)


# ----------------------------------------------------------------------
# Consultas
# ----------------------------------------------------------------------

_SELECT_CANCELACIONES = """
    SELECT
        SC.IdSolicitud AS IdCancelacion,
        SC.IdPedido,
        SC.IdVenta,
        SC.IdUsuario AS IdSolicitante,
        SC.TipoSolicitud AS Tipo,
        CASE
            WHEN SC.Estado = 'PENDIENTE' THEN 'SOLICITADA'
            ELSE SC.Estado
        END AS Estado,
        SC.Motivo,
        COALESCE((
            SELECT SUM(R.Valor)
            FROM Reembolsos R
            WHERE R.IdSolicitud = SC.IdSolicitud
        ), 0) AS MontoReembolso,
        SC.FechaSolicitud,
        SC.FechaRespuesta AS FechaResolucion,
        CAST(NULL AS VARCHAR(500)) AS ObservacionResolucion,
        V.IdVendedor,
        P.IdComprador
    FROM SolicitudesCancelacion SC
    INNER JOIN Ventas V
        ON V.IdVenta = SC.IdVenta
    INNER JOIN Pedidos P
        ON P.IdPedido = SC.IdPedido
"""


def _cancelacion_a_diccionario(fila, id_usuario: int):
    return {
        "id_cancelacion": fila.IdCancelacion,
        "id_pedido": fila.IdPedido,
        "id_venta": fila.IdVenta,
        "rol": (
            "COMPRADOR"
            if fila.IdComprador == id_usuario
            else "VENDEDOR"
        ),
        "solicitada_por": (
            "COMPRADOR"
            if fila.IdSolicitante == fila.IdComprador
            else "VENDEDOR"
        ),
        "tipo": fila.Tipo,
        "estado": fila.Estado,
        "motivo": fila.Motivo,
        "monto_reembolso": a_float(fila.MontoReembolso),
        "fecha_solicitud": iso(fila.FechaSolicitud),
        "fecha_resolucion": iso(fila.FechaResolucion),
        "observacion_resolucion": fila.ObservacionResolucion
    }


def listar_cancelaciones(
    id_usuario: int,
    rol: str | None = None,
    estado: str | None = None
):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        verificar_usuario_activo(cursor, id_usuario)

        if rol == "COMPRADOR":
            condicion = "P.IdComprador = ?"
            parametros = [id_usuario]

        elif rol == "VENDEDOR":
            condicion = "V.IdVendedor = ?"
            parametros = [id_usuario]

        else:
            condicion = (
                "(P.IdComprador = ? OR V.IdVendedor = ?)"
            )
            parametros = [id_usuario, id_usuario]

        consulta = _SELECT_CANCELACIONES + f" WHERE {condicion}"

        if estado:
            consulta += " AND SC.Estado = ?"
            parametros.append(_estado_bd(estado))

        consulta += " ORDER BY SC.IdSolicitud DESC;"

        cursor.execute(consulta, parametros)

        return [
            _cancelacion_a_diccionario(fila, id_usuario)
            for fila in cursor.fetchall()
        ]

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def obtener_cancelacion(
    id_usuario: int,
    id_cancelacion: int
):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        verificar_usuario_activo(cursor, id_usuario)

        cursor.execute(
            _SELECT_CANCELACIONES + """
            WHERE SC.IdSolicitud = ?
              AND (
                  P.IdComprador = ?
                  OR V.IdVendedor = ?
              );
            """,
            (id_cancelacion, id_usuario, id_usuario)
        )

        fila = cursor.fetchone()

        if fila is None:
            raise CancellationNotFound(
                "Cancelación no encontrada."
            )

        resultado = _cancelacion_a_diccionario(
            fila,
            id_usuario
        )

        cursor.execute(
            """
            SELECT
                DSC.IdDetallePedido,
                DP.IdProducto,
                PR.Nombre,
                DSC.CantidadSolicitada AS Cantidad,
                DP.PrecioUnitario * DSC.CantidadSolicitada AS Monto
            FROM DetalleSolicitudCancelacion DSC
            INNER JOIN DetallesPedido DP
                ON DP.IdDetallePedido = DSC.IdDetallePedido
            INNER JOIN Productos PR
                ON PR.IdProducto = DP.IdProducto
            WHERE DSC.IdSolicitud = ?
            ORDER BY DSC.IdDetalleSolicitud;
            """,
            (id_cancelacion,)
        )

        resultado["productos"] = [
            {
                "id_detalle_pedido": detalle.IdDetallePedido,
                "id_producto": detalle.IdProducto,
                "nombre": detalle.Nombre,
                "cantidad": detalle.Cantidad,
                "monto": a_float(detalle.Monto)
            }
            for detalle in cursor.fetchall()
        ]

        return resultado

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()