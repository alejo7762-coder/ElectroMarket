"""
Devoluciones de pedidos ya entregados.

Flujo:
    SOLICITADA --(vendedor aprueba)--> APROBADA --(comprador envía)--> ENVIADA
               --(vendedor recibe)--> RECIBIDA: reembolso y, si el vendedor
                                      lo decide, unidades al inventario.
    SOLICITADA --(vendedor rechaza)--> RECHAZADA

Reglas:
- Solo el comprador de una venta ENTREGADA, dentro de DIAS_PLAZO días
  desde la entrega.
- Se devuelven unidades vigentes: no canceladas ni ya devueltas en otra
  devolución que no fue rechazada.
- Una sola devolución en curso por venta.
- Al recibir el producto se registra un reembolso PENDIENTE ligado a la
  devolución, que la pasarela simulada procesa (app/services/reembolsos.py).

Tablas: Devoluciones y DetalleDevolucion (database/scripts/07_devoluciones.sql)
"""

from decimal import Decimal, ROUND_HALF_UP

from app.errores import ReturnConflict, ReturnForbidden, ReturnNotFound
from app.services.cancelaciones import _devolver_inventario
from app.services.devoluciones_plazo import DIAS_PLAZO, dias_restantes
from app.services.pedidos import _registrar_historial
from app.services.resenas import _cursor
from app.services.utilidades import ESTADOS_PAGO_COBRADO, a_float, iso, verificar_usuario_activo

CENTAVOS = Decimal("0.01")
ESTADOS_EN_CURSO = ("SOLICITADA", "APROBADA", "ENVIADA")

MOTIVOS = {
    "DEFECTUOSO": "El producto presenta fallas",
    "NO_COINCIDE": "No coincide con la descripción",
    "LLEGO_DANADO": "Llegó dañado",
    "EQUIVOCADO": "Recibí un producto equivocado",
    "ARREPENTIMIENTO": "Ya no lo quiero",
}


# ----------------------------------------------------------------------
# Lógica pura
# ----------------------------------------------------------------------

def calcular_lineas_devolucion(lineas: list, solicitados: dict | None):
    """
    lineas: [{id_detalle_pedido, id_producto, nombre, disponible, precio}]
    solicitados: {id_producto: cantidad | None}; None devuelve todo lo disponible.
    Devuelve ([(linea, cantidad)], monto).
    """
    por_producto = {l["id_producto"]: l for l in lineas}
    elegidas = []

    if solicitados is None:
        elegidas = [(l, l["disponible"]) for l in lineas if l["disponible"] > 0]
    else:
        for id_producto, cantidad in solicitados.items():
            linea = por_producto.get(id_producto)
            if linea is None:
                raise ReturnConflict(f"El producto {id_producto} no pertenece a esta compra.")
            cantidad = linea["disponible"] if cantidad is None else cantidad
            if cantidad <= 0 or cantidad > linea["disponible"]:
                raise ReturnConflict(
                    f"Solo puedes devolver hasta {linea['disponible']} unidad(es) de «{linea['nombre']}»."
                )
            elegidas.append((linea, cantidad))

    if not elegidas:
        raise ReturnConflict("No hay unidades disponibles para devolver en esta compra.")

    monto = sum(
        (Decimal(str(l["precio"])) * c for l, c in elegidas), Decimal("0")
    ).quantize(CENTAVOS, rounding=ROUND_HALF_UP)
    return elegidas, monto


# ----------------------------------------------------------------------
# Apoyo con base de datos
# ----------------------------------------------------------------------

def _lineas_venta(cursor, id_venta: int) -> list:
    cursor.execute(
        """
        SELECT DP.IdDetallePedido, DP.IdProducto, P.Nombre, DP.Cantidad, DP.PrecioUnitario,
               COALESCE((SELECT SUM(DSC.CantidadSolicitada)
                         FROM DetalleSolicitudCancelacion DSC
                         INNER JOIN SolicitudesCancelacion SC ON SC.IdSolicitud = DSC.IdSolicitud
                         WHERE DSC.IdDetallePedido = DP.IdDetallePedido AND SC.Estado = 'APROBADA'), 0) AS Cancelada,
               COALESCE((SELECT SUM(DD.Cantidad)
                         FROM DetalleDevolucion DD
                         INNER JOIN Devoluciones D ON D.IdDevolucion = DD.IdDevolucion
                         WHERE DD.IdDetallePedido = DP.IdDetallePedido AND D.Estado <> 'RECHAZADA'), 0) AS Devuelta
        FROM DetalleVenta DV
        INNER JOIN DetallesPedido DP ON DP.IdDetallePedido = DV.IdDetallePedido
        INNER JOIN Productos P ON P.IdProducto = DP.IdProducto
        WHERE DV.IdVenta = ?
        ORDER BY DP.IdDetallePedido;
        """,
        (id_venta,),
    )
    return [
        {"id_detalle_pedido": f.IdDetallePedido, "id_producto": f.IdProducto, "nombre": f.Nombre,
         "disponible": f.Cantidad - f.Cancelada - f.Devuelta, "precio": f.PrecioUnitario}
        for f in cursor.fetchall()
    ]


def _bloquear(cursor, id_devolucion: int):
    cursor.execute(
        """
        SELECT IdDevolucion, IdVenta, IdPedido, IdComprador, IdVendedor, Estado, MontoReembolso
        FROM Devoluciones WITH (UPDLOCK, ROWLOCK)
        WHERE IdDevolucion = ?;
        """,
        (id_devolucion,),
    )
    devolucion = cursor.fetchone()
    if devolucion is None:
        raise ReturnNotFound("Devolución no encontrada.")
    return devolucion


def _historial(cursor, devolucion, estado: str, observacion: str):
    _registrar_historial(cursor, "VENTA", devolucion.IdVenta, "ENTREGADA",
                         f"DEVOLUCION_{estado}", f"Devolución #{devolucion.IdDevolucion}: {observacion}"[:500])


_SELECT = """
    SELECT D.IdDevolucion, D.IdVenta, D.IdPedido, D.IdComprador, D.IdVendedor, D.Motivo, D.Descripcion,
           D.Estado, D.MontoReembolso, D.ObservacionVendedor, D.Transportadora, D.NumeroGuia,
           D.ReintegradoInventario, D.FechaSolicitud, D.FechaRespuesta, D.FechaEnvio, D.FechaRecepcion,
           UC.Nombre + ' ' + UC.Apellido AS Comprador, UV.Nombre + ' ' + UV.Apellido AS Vendedor,
           R.Estado AS EstadoReembolso, R.Referencia AS ReferenciaReembolso
    FROM Devoluciones D
    INNER JOIN Usuarios UC ON UC.IdUsuario = D.IdComprador
    INNER JOIN Usuarios UV ON UV.IdUsuario = D.IdVendedor
    LEFT JOIN Reembolsos R ON R.IdDevolucion = D.IdDevolucion
"""


def _a_diccionario(cursor, fila, id_usuario: int) -> dict:
    cursor.execute(
        """
        SELECT DD.IdDetallePedido, DP.IdProducto, P.Nombre, DD.Cantidad, DP.PrecioUnitario
        FROM DetalleDevolucion DD
        INNER JOIN DetallesPedido DP ON DP.IdDetallePedido = DD.IdDetallePedido
        INNER JOIN Productos P ON P.IdProducto = DP.IdProducto
        WHERE DD.IdDevolucion = ?;
        """,
        (fila.IdDevolucion,),
    )
    productos = [
        {"id_producto": p.IdProducto, "nombre": p.Nombre, "cantidad": p.Cantidad,
         "subtotal": a_float(p.PrecioUnitario * p.Cantidad)}
        for p in cursor.fetchall()
    ]
    return {
        "id_devolucion": fila.IdDevolucion,
        "id_venta": fila.IdVenta,
        "id_pedido": fila.IdPedido,
        "rol": "COMPRADOR" if fila.IdComprador == id_usuario else "VENDEDOR",
        "comprador": fila.Comprador,
        "vendedor": fila.Vendedor,
        "motivo": fila.Motivo,
        "motivo_texto": MOTIVOS.get(fila.Motivo, fila.Motivo),
        "descripcion": fila.Descripcion,
        "estado": fila.Estado,
        "monto_reembolso": a_float(fila.MontoReembolso),
        "observacion_vendedor": fila.ObservacionVendedor,
        "transportadora": fila.Transportadora,
        "numero_guia": fila.NumeroGuia,
        "reintegrado_inventario": None if fila.ReintegradoInventario is None else bool(fila.ReintegradoInventario),
        "estado_reembolso": fila.EstadoReembolso,
        "referencia_reembolso": fila.ReferenciaReembolso,
        "fecha_solicitud": iso(fila.FechaSolicitud),
        "fecha_respuesta": iso(fila.FechaRespuesta),
        "fecha_envio": iso(fila.FechaEnvio),
        "fecha_recepcion": iso(fila.FechaRecepcion),
        "productos": productos,
    }


def _leer(cursor, id_devolucion: int, id_usuario: int) -> dict:
    cursor.execute(_SELECT + " WHERE D.IdDevolucion = ?;", (id_devolucion,))
    return _a_diccionario(cursor, cursor.fetchone(), id_usuario)


# ----------------------------------------------------------------------
# Operaciones
# ----------------------------------------------------------------------

def solicitar_devolucion(id_usuario: int, id_venta: int, motivo: str, descripcion: str,
                         productos: dict | None) -> dict:
    with _cursor(transaccion=True) as cursor:
        verificar_usuario_activo(cursor, id_usuario)
        cursor.execute(
            """
            SELECT V.IdVenta, V.IdPedido, V.IdVendedor, V.Estado, P.IdComprador, E.FechaEntrega
            FROM Ventas V WITH (UPDLOCK, ROWLOCK)
            INNER JOIN Pedidos P ON P.IdPedido = V.IdPedido
            LEFT JOIN Envios E ON E.IdVenta = V.IdVenta
            WHERE V.IdVenta = ?;
            """,
            (id_venta,),
        )
        venta = cursor.fetchone()

        if venta is None or venta.IdComprador != id_usuario:
            raise ReturnNotFound("Compra no encontrada.")
        if venta.Estado != "ENTREGADA":
            raise ReturnConflict("Solo puedes devolver compras que ya fueron entregadas.")
        if dias_restantes(venta.FechaEntrega) <= 0:
            raise ReturnConflict(f"El plazo de {DIAS_PLAZO} días para devolver esta compra ya venció.")

        cursor.execute(
            f"SELECT COUNT(*) FROM Devoluciones WHERE IdVenta = ? AND Estado IN {ESTADOS_EN_CURSO};",
            (id_venta,),
        )
        if cursor.fetchone()[0]:
            raise ReturnConflict("Ya tienes una devolución en curso para esta compra.")

        elegidas, monto = calcular_lineas_devolucion(_lineas_venta(cursor, id_venta), productos)

        cursor.execute(
            """
            INSERT INTO Devoluciones (IdVenta, IdPedido, IdComprador, IdVendedor, Motivo, Descripcion, MontoReembolso)
            OUTPUT INSERTED.IdDevolucion
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (id_venta, venta.IdPedido, id_usuario, venta.IdVendedor, motivo, descripcion, monto),
        )
        id_devolucion = cursor.fetchone()[0]

        for linea, cantidad in elegidas:
            cursor.execute(
                "INSERT INTO DetalleDevolucion (IdDevolucion, IdDetallePedido, Cantidad) VALUES (?, ?, ?);",
                (id_devolucion, linea["id_detalle_pedido"], cantidad),
            )

        devolucion = _bloquear(cursor, id_devolucion)
        _historial(cursor, devolucion, "SOLICITADA", MOTIVOS[motivo])
        return _leer(cursor, id_devolucion, id_usuario)


def responder_devolucion(id_usuario: int, id_devolucion: int, aprobar: bool, observacion: str | None) -> dict:
    with _cursor(transaccion=True) as cursor:
        verificar_usuario_activo(cursor, id_usuario)
        devolucion = _bloquear(cursor, id_devolucion)

        if devolucion.IdVendedor != id_usuario:
            raise ReturnForbidden("Solo el vendedor puede responder esta devolución.")
        if devolucion.Estado != "SOLICITADA":
            raise ReturnConflict("La devolución ya fue respondida.")

        estado = "APROBADA" if aprobar else "RECHAZADA"
        cursor.execute(
            """
            UPDATE Devoluciones
            SET Estado = ?, ObservacionVendedor = ?, FechaRespuesta = SYSDATETIME()
            WHERE IdDevolucion = ?;
            """,
            (estado, observacion, id_devolucion),
        )
        _historial(cursor, devolucion, estado, observacion or ("Aprobada" if aprobar else "Rechazada"))
        return _leer(cursor, id_devolucion, id_usuario)


def registrar_envio(id_usuario: int, id_devolucion: int, transportadora: str, numero_guia: str) -> dict:
    with _cursor(transaccion=True) as cursor:
        verificar_usuario_activo(cursor, id_usuario)
        devolucion = _bloquear(cursor, id_devolucion)

        if devolucion.IdComprador != id_usuario:
            raise ReturnForbidden("Solo el comprador registra el envío de la devolución.")
        if devolucion.Estado != "APROBADA":
            raise ReturnConflict("El envío se registra cuando el vendedor aprueba la devolución.")

        cursor.execute(
            """
            UPDATE Devoluciones
            SET Estado = 'ENVIADA', Transportadora = ?, NumeroGuia = ?, FechaEnvio = SYSDATETIME()
            WHERE IdDevolucion = ?;
            """,
            (transportadora, numero_guia, id_devolucion),
        )
        _historial(cursor, devolucion, "ENVIADA", f"{transportadora}, guía {numero_guia}")
        return _leer(cursor, id_devolucion, id_usuario)


def confirmar_recepcion(id_usuario: int, id_devolucion: int, reintegrar_inventario: bool) -> dict:
    with _cursor(transaccion=True) as cursor:
        verificar_usuario_activo(cursor, id_usuario)
        devolucion = _bloquear(cursor, id_devolucion)

        if devolucion.IdVendedor != id_usuario:
            raise ReturnForbidden("Solo el vendedor confirma que recibió la devolución.")
        if devolucion.Estado != "ENVIADA":
            raise ReturnConflict("Solo se confirma la recepción de una devolución enviada.")

        cursor.execute("SELECT IdPago, Estado FROM Pagos WHERE IdPedido = ?;", (devolucion.IdPedido,))
        pago = cursor.fetchone()
        if pago is None or pago.Estado not in ESTADOS_PAGO_COBRADO or pago.Estado == "REEMBOLSADO":
            raise ReturnConflict("El pago de este pedido no admite más reembolsos.")

        if reintegrar_inventario:
            cursor.execute(
                """
                SELECT DP.IdProducto, DD.Cantidad
                FROM DetalleDevolucion DD
                INNER JOIN DetallesPedido DP ON DP.IdDetallePedido = DD.IdDetallePedido
                WHERE DD.IdDevolucion = ?;
                """,
                (id_devolucion,),
            )
            _devolver_inventario(cursor, [({"id_producto": f.IdProducto}, f.Cantidad) for f in cursor.fetchall()])

        cursor.execute(
            """
            UPDATE Devoluciones
            SET Estado = 'RECIBIDA', ReintegradoInventario = ?, FechaRecepcion = SYSDATETIME()
            WHERE IdDevolucion = ?;
            """,
            (1 if reintegrar_inventario else 0, id_devolucion),
        )
        cursor.execute(
            "INSERT INTO Reembolsos (IdPago, IdDevolucion, Valor) VALUES (?, ?, ?);",
            (pago.IdPago, id_devolucion, devolucion.MontoReembolso),
        )
        _historial(cursor, devolucion, "RECIBIDA",
                   "Producto recibido; reembolso registrado" + (" e inventario reintegrado" if reintegrar_inventario else ""))
        return _leer(cursor, id_devolucion, id_usuario)


# ----------------------------------------------------------------------
# Consultas
# ----------------------------------------------------------------------

def listar_devoluciones(id_usuario: int, rol: str | None = None, id_pedido: int | None = None,
                        estado: str | None = None) -> list:
    condiciones, parametros = [], []
    if rol == "COMPRADOR":
        condiciones.append("D.IdComprador = ?"); parametros.append(id_usuario)
    elif rol == "VENDEDOR":
        condiciones.append("D.IdVendedor = ?"); parametros.append(id_usuario)
    else:
        condiciones.append("(D.IdComprador = ? OR D.IdVendedor = ?)"); parametros += [id_usuario, id_usuario]
    if id_pedido is not None:
        condiciones.append("D.IdPedido = ?"); parametros.append(id_pedido)
    if estado is not None:
        condiciones.append("D.Estado = ?"); parametros.append(estado)

    with _cursor() as cursor:
        verificar_usuario_activo(cursor, id_usuario)
        cursor.execute(_SELECT + " WHERE " + " AND ".join(condiciones) + " ORDER BY D.IdDevolucion DESC;", parametros)
        filas = cursor.fetchall()
        return [_a_diccionario(cursor, f, id_usuario) for f in filas]


def obtener_devolucion(id_usuario: int, id_devolucion: int) -> dict:
    with _cursor() as cursor:
        verificar_usuario_activo(cursor, id_usuario)
        cursor.execute(_SELECT + " WHERE D.IdDevolucion = ?;", (id_devolucion,))
        fila = cursor.fetchone()
        if fila is None or id_usuario not in (fila.IdComprador, fila.IdVendedor):
            raise ReturnNotFound("Devolución no encontrada.")
        return _a_diccionario(cursor, fila, id_usuario)


def plazo_devolucion(cursor, id_venta: int) -> int:
    """Días restantes para devolver una venta (para el detalle del pedido)."""
    cursor.execute("SELECT FechaEntrega FROM Envios WHERE IdVenta = ?;", (id_venta,))
    fila = cursor.fetchone()
    return dias_restantes(fila.FechaEntrega if fila else None)
