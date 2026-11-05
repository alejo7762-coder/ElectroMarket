import random
import uuid

from app.db.connection import get_connection
from app.services.carrito import UserNotActive
from app.services.pedidos import _registrar_historial


TRANSPORTADORAS_SIMULADAS = [
    "Servientrega",
    "Coordinadora",
    "Interrapidisimo",
    "Envia",
    "Deprisa"
]

# Estados del pedido en los que todavía se pueden gestionar envíos
ESTADOS_PEDIDO_ENVIABLES = (
    "PAGADO",
    "EN_PROCESO",
    "PARCIALMENTE_ENVIADO"
)

# Transiciones permitidas del envío (CANCELADO se reserva al módulo de cancelaciones)
TRANSICIONES_ENVIO = {
    "PREPARANDO": ("ENVIADO", "PROBLEMA"),
    "ENVIADO": ("EN_TRANSITO", "PROBLEMA"),
    "EN_TRANSITO": ("ENTREGADO", "PROBLEMA"),
    "PROBLEMA": ("PREPARANDO", "ENVIADO"),
    "ENTREGADO": (),
    "CANCELADO": ()
}

# Estado de la venta según el estado del envío
ESTADO_VENTA_POR_ENVIO = {
    "PREPARANDO": "PREPARANDO",
    "ENVIADO": "ENVIADA",
    "EN_TRANSITO": "ENVIADA",
    "ENTREGADO": "ENTREGADA"
}


class SaleNotFound(Exception):
    pass


class ShipmentNotFound(Exception):
    pass


class OrderNotFound(Exception):
    pass


class ShipmentConflict(Exception):
    pass


def _iso(valor):
    return valor.isoformat() if valor else None


def _verificar_usuario_activo(cursor, id_usuario: int):
    cursor.execute(
        "SELECT Estado FROM Usuarios WHERE IdUsuario = ?;",
        (id_usuario,)
    )

    usuario = cursor.fetchone()

    if usuario is None or usuario.Estado != "ACTIVO":
        raise UserNotActive("El usuario no existe o no está activo.")


def _bloquear_pedido(cursor, id_pedido: int) -> str:
    cursor.execute(
        """
        SELECT Estado
        FROM Pedidos WITH (UPDLOCK, ROWLOCK)
        WHERE IdPedido = ?;
        """,
        (id_pedido,)
    )

    return cursor.fetchone().Estado


def _sincronizar_estado_pedido(cursor, id_pedido: int, estado_actual: str):
    """
    Recalcula el estado del pedido según el estado de sus ventas
    (ignorando las canceladas). Devuelve el estado final.
    """
    cursor.execute(
        """
        SELECT Estado
        FROM Ventas
        WHERE IdPedido = ?
          AND Estado <> 'CANCELADA';
        """,
        (id_pedido,)
    )

    estados = [fila.Estado for fila in cursor.fetchall()]

    if not estados:
        # Sin ventas vigentes: si el pedido tenía ventas, todas se cancelaron
        cursor.execute(
            "SELECT COUNT(*) FROM Ventas WHERE IdPedido = ?;",
            (id_pedido,)
        )

        if cursor.fetchone()[0] == 0:
            return estado_actual

        estados = None

    if estados is None:
        nuevo_estado = "CANCELADO"

        if nuevo_estado != estado_actual:
            cursor.execute(
                "UPDATE Pedidos SET Estado = ? WHERE IdPedido = ?;",
                (nuevo_estado, id_pedido)
            )

            _registrar_historial(
                cursor, "PEDIDO", id_pedido,
                estado_actual, nuevo_estado,
                "Todas las ventas del pedido fueron canceladas."
            )

        return nuevo_estado

    todas_entregadas = all(e == "ENTREGADA" for e in estados)
    # Una venta con cancelación solicitada ya había sido despachada
    hay_despachada = any(
        e in ("ENVIADA", "ENTREGADA", "CANCELACION_SOLICITADA")
        for e in estados
    )
    hay_sin_despachar = any(e in ("PENDIENTE", "PREPARANDO") for e in estados)
    hay_preparando = any(e == "PREPARANDO" for e in estados)

    if todas_entregadas:
        nuevo_estado = "COMPLETADO"
    elif hay_despachada and hay_sin_despachar:
        nuevo_estado = "PARCIALMENTE_ENVIADO"
    elif hay_despachada or hay_preparando:
        nuevo_estado = "EN_PROCESO"
    else:
        nuevo_estado = "PAGADO"

    if nuevo_estado != estado_actual:
        cursor.execute(
            "UPDATE Pedidos SET Estado = ? WHERE IdPedido = ?;",
            (nuevo_estado, id_pedido)
        )

        _registrar_historial(
            cursor, "PEDIDO", id_pedido,
            estado_actual, nuevo_estado,
            "Actualizado por el estado de los envíos."
        )

    return nuevo_estado


def crear_envio(id_vendedor: int, id_venta: int, transportadora: str | None = None):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        _verificar_usuario_activo(cursor, id_vendedor)

        # La venta debe pertenecer al vendedor
        cursor.execute(
            """
            SELECT IdPedido
            FROM Ventas
            WHERE IdVenta = ?
              AND IdVendedor = ?;
            """,
            (id_venta, id_vendedor)
        )

        venta = cursor.fetchone()

        if venta is None:
            raise SaleNotFound("Venta no encontrada.")

        id_pedido = venta.IdPedido

        # Orden de bloqueo: primero pedido, luego venta
        estado_pedido = _bloquear_pedido(cursor, id_pedido)

        cursor.execute(
            """
            SELECT Estado
            FROM Ventas WITH (UPDLOCK, ROWLOCK)
            WHERE IdVenta = ?;
            """,
            (id_venta,)
        )

        estado_venta = cursor.fetchone().Estado

        if estado_pedido not in ESTADOS_PEDIDO_ENVIABLES:
            raise ShipmentConflict(
                f"El pedido está en estado {estado_pedido} y no admite envíos."
            )

        if estado_venta != "PENDIENTE":
            raise ShipmentConflict(
                f"La venta está en estado {estado_venta}; "
                "solo se puede crear envío para ventas PENDIENTE."
            )

        cursor.execute(
            "SELECT IdEnvio FROM Envios WHERE IdVenta = ?;",
            (id_venta,)
        )

        if cursor.fetchone():
            raise ShipmentConflict("Esta venta ya tiene un envío creado.")

        transportadora = (transportadora or "").strip() or random.choice(
            TRANSPORTADORAS_SIMULADAS
        )
        numero_guia = f"SIM-{uuid.uuid4().hex[:10].upper()}"

        cursor.execute(
            """
            INSERT INTO Envios (IdVenta, Transportadora, NumeroGuia, Estado)
            OUTPUT INSERTED.IdEnvio
            VALUES (?, ?, ?, 'PREPARANDO');
            """,
            (id_venta, transportadora, numero_guia)
        )

        id_envio = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO HistorialEnvios (IdEnvio, Estado, Observacion)
            VALUES (?, 'PREPARANDO', 'Envío creado.');
            """,
            (id_envio,)
        )

        cursor.execute(
            "UPDATE Ventas SET Estado = 'PREPARANDO' WHERE IdVenta = ?;",
            (id_venta,)
        )

        _registrar_historial(
            cursor, "VENTA", id_venta,
            "PENDIENTE", "PREPARANDO", "Envío creado."
        )

        estado_pedido_final = _sincronizar_estado_pedido(
            cursor, id_pedido, estado_pedido
        )

        connection.commit()

        return {
            "mensaje": "Envío creado correctamente.",
            "id_envio": id_envio,
            "id_venta": id_venta,
            "id_pedido": id_pedido,
            "transportadora": transportadora,
            "numero_guia": numero_guia,
            "estado_envio": "PREPARANDO",
            "estado_venta": "PREPARANDO",
            "estado_pedido": estado_pedido_final
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


def actualizar_estado_envio(
    id_vendedor: int,
    id_envio: int,
    nuevo_estado: str,
    observacion: str | None = None
):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        _verificar_usuario_activo(cursor, id_vendedor)

        # El envío debe pertenecer a una venta del vendedor
        cursor.execute(
            """
            SELECT V.IdPedido
            FROM Envios E
            INNER JOIN Ventas V ON V.IdVenta = E.IdVenta
            WHERE E.IdEnvio = ?
              AND V.IdVendedor = ?;
            """,
            (id_envio, id_vendedor)
        )

        fila = cursor.fetchone()

        if fila is None:
            raise ShipmentNotFound("Envío no encontrado.")

        id_pedido = fila.IdPedido

        # Orden de bloqueo: pedido, luego venta y envío
        estado_pedido = _bloquear_pedido(cursor, id_pedido)

        cursor.execute(
            """
            SELECT
                E.Estado AS EstadoEnvio,
                E.FechaDespacho,
                V.IdVenta,
                V.Estado AS EstadoVenta
            FROM Envios E WITH (UPDLOCK, ROWLOCK)
            INNER JOIN Ventas V WITH (UPDLOCK, ROWLOCK)
                ON V.IdVenta = E.IdVenta
            WHERE E.IdEnvio = ?;
            """,
            (id_envio,)
        )

        envio = cursor.fetchone()

        if estado_pedido not in ESTADOS_PEDIDO_ENVIABLES:
            raise ShipmentConflict(
                f"El pedido está en estado {estado_pedido} y no admite cambios de envío."
            )

        if envio.EstadoVenta in ("CANCELADA", "CANCELACION_SOLICITADA"):
            raise ShipmentConflict(
                f"La venta está en estado {envio.EstadoVenta}; "
                "no se puede modificar el envío."
            )

        permitidos = TRANSICIONES_ENVIO.get(envio.EstadoEnvio, ())

        if nuevo_estado not in permitidos:
            detalle = ", ".join(permitidos) if permitidos else "ninguno"
            raise ShipmentConflict(
                f"No se puede pasar de {envio.EstadoEnvio} a {nuevo_estado}. "
                f"Estados permitidos: {detalle}."
            )

        # Actualizar el envío
        cursor.execute(
            "UPDATE Envios SET Estado = ? WHERE IdEnvio = ?;",
            (nuevo_estado, id_envio)
        )

        if nuevo_estado == "ENVIADO" and envio.FechaDespacho is None:
            cursor.execute(
                "UPDATE Envios SET FechaDespacho = SYSDATETIME() WHERE IdEnvio = ?;",
                (id_envio,)
            )

        if nuevo_estado == "ENTREGADO":
            cursor.execute(
                "UPDATE Envios SET FechaEntrega = SYSDATETIME() WHERE IdEnvio = ?;",
                (id_envio,)
            )

        cursor.execute(
            """
            INSERT INTO HistorialEnvios (IdEnvio, Estado, Observacion)
            VALUES (?, ?, ?);
            """,
            (
                id_envio,
                nuevo_estado,
                observacion or f"Estado actualizado a {nuevo_estado}."
            )
        )

        # Actualizar la venta si corresponde
        estado_venta_final = envio.EstadoVenta
        nuevo_estado_venta = ESTADO_VENTA_POR_ENVIO.get(nuevo_estado)

        if nuevo_estado_venta and nuevo_estado_venta != envio.EstadoVenta:
            cursor.execute(
                "UPDATE Ventas SET Estado = ? WHERE IdVenta = ?;",
                (nuevo_estado_venta, envio.IdVenta)
            )

            _registrar_historial(
                cursor, "VENTA", envio.IdVenta,
                envio.EstadoVenta, nuevo_estado_venta,
                f"Envío {nuevo_estado}."
            )

            estado_venta_final = nuevo_estado_venta

        estado_pedido_final = _sincronizar_estado_pedido(
            cursor, id_pedido, estado_pedido
        )

        connection.commit()

        return {
            "mensaje": "Estado del envío actualizado correctamente.",
            "id_envio": id_envio,
            "estado_anterior": envio.EstadoEnvio,
            "estado_envio": nuevo_estado,
            "estado_venta": estado_venta_final,
            "estado_pedido": estado_pedido_final
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


def obtener_seguimiento(id_usuario: int, id_envio: int):
    """
    Seguimiento de un envío. Lo puede ver el comprador del pedido
    o el vendedor de la venta.
    """
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                E.IdEnvio,
                E.IdVenta,
                E.Transportadora,
                E.NumeroGuia,
                E.Estado,
                E.FechaDespacho,
                E.FechaEntrega,
                V.IdPedido,
                V.Estado AS EstadoVenta,
                P.DireccionEntrega,
                P.CiudadEntrega,
                P.DepartamentoEntrega
            FROM Envios E
            INNER JOIN Ventas V ON V.IdVenta = E.IdVenta
            INNER JOIN Pedidos P ON P.IdPedido = V.IdPedido
            WHERE E.IdEnvio = ?
              AND (P.IdComprador = ? OR V.IdVendedor = ?);
            """,
            (id_envio, id_usuario, id_usuario)
        )

        envio = cursor.fetchone()

        if envio is None:
            raise ShipmentNotFound("Envío no encontrado.")

        cursor.execute(
            """
            SELECT Estado, FechaCambio, Observacion
            FROM HistorialEnvios
            WHERE IdEnvio = ?
            ORDER BY FechaCambio, IdHistorialEnvio;
            """,
            (id_envio,)
        )

        historial = [
            {
                "estado": h.Estado,
                "fecha": _iso(h.FechaCambio),
                "observacion": h.Observacion
            }
            for h in cursor.fetchall()
        ]

        return {
            "id_envio": envio.IdEnvio,
            "id_venta": envio.IdVenta,
            "id_pedido": envio.IdPedido,
            "transportadora": envio.Transportadora,
            "numero_guia": envio.NumeroGuia,
            "estado_envio": envio.Estado,
            "estado_venta": envio.EstadoVenta,
            "fecha_despacho": _iso(envio.FechaDespacho),
            "fecha_entrega": _iso(envio.FechaEntrega),
            "entrega": {
                "direccion": envio.DireccionEntrega,
                "ciudad": envio.CiudadEntrega,
                "departamento": envio.DepartamentoEntrega
            },
            "historial": historial
        }

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def obtener_envios_pedido(id_comprador: int, id_pedido: int):
    """
    Estado de envío de cada venta (vendedor) de un pedido del comprador.
    """
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT Estado
            FROM Pedidos
            WHERE IdPedido = ?
              AND IdComprador = ?;
            """,
            (id_pedido, id_comprador)
        )

        pedido = cursor.fetchone()

        if pedido is None:
            raise OrderNotFound("Pedido no encontrado.")

        cursor.execute(
            """
            SELECT
                V.IdVenta,
                V.IdVendedor,
                V.Subtotal,
                V.Estado AS EstadoVenta,
                E.IdEnvio,
                E.Transportadora,
                E.NumeroGuia,
                E.Estado AS EstadoEnvio
            FROM Ventas V
            LEFT JOIN Envios E ON E.IdVenta = V.IdVenta
            WHERE V.IdPedido = ?
            ORDER BY V.IdVenta;
            """,
            (id_pedido,)
        )

        envios = []

        for fila in cursor.fetchall():
            envios.append({
                "id_venta": fila.IdVenta,
                "id_vendedor": fila.IdVendedor,
                "subtotal": float(fila.Subtotal),
                "estado_venta": fila.EstadoVenta,
                "envio": None if fila.IdEnvio is None else {
                    "id_envio": fila.IdEnvio,
                    "transportadora": fila.Transportadora,
                    "numero_guia": fila.NumeroGuia,
                    "estado": fila.EstadoEnvio
                }
            })

        return {
            "id_pedido": id_pedido,
            "estado_pedido": pedido.Estado,
            "envios": envios
        }

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()