"""
Etapa 10 - Cancelaciones parciales y totales.

Reglas implementadas:
- Solo se puede cancelar antes de la entrega (no hay devoluciones).
- Cada cancelación afecta a UNA venta (la parte de un vendedor).
  Cancelar un pedido completo genera una cancelación por cada venta.
- Venta PENDIENTE o PREPARANDO (no despachada):
    la cancelación se aplica de inmediato. Puede ser parcial
    (algunos productos o algunas unidades) o total.
- Venta ENVIADA (ya despachada, aún no entregada):
    el comprador solo puede SOLICITAR la cancelación completa de esa venta;
    el vendedor la aprueba o la rechaza.
- Venta ENTREGADA o CANCELADA: no se puede cancelar.
- Al aplicar una cancelación se devuelven las unidades al inventario
  (un producto AGOTADO vuelve a PUBLICADO) y se registra el reembolso
  simulado en Cancelaciones.MontoReembolso. El pago original conserva
  su estado APROBADO como evidencia.
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

ESTADOS_PEDIDO_CANCELABLES = ("PAGADO", "EN_PROCESO", "PARCIALMENTE_ENVIADO")
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
# Lógica pura (sin base de datos) - probada en tests/test_cancelaciones.py
# ----------------------------------------------------------------------

def calcular_lineas_a_cancelar(lineas: list, solicitados: dict | None):
    """
    lineas: [{id_detalle_pedido, id_producto, nombre, vigente, precio}]
    solicitados: {id_producto: cantidad | None}. None = todas las vigentes.

    Devuelve [(linea, cantidad_a_cancelar)] o lanza CancellationConflict.
    """
    if solicitados is None:
        resultado = [(l, l["vigente"]) for l in lineas if l["vigente"] > 0]

        if not resultado:
            raise CancellationConflict(
                "No hay unidades vigentes para cancelar."
            )

        return resultado

    por_producto = {l["id_producto"]: l for l in lineas}
    resultado = []

    for id_producto, cantidad in solicitados.items():
        linea = por_producto.get(id_producto)

        if linea is None:
            raise CancellationConflict(
                f"El producto {id_producto} no hace parte de este pedido."
            )

        if linea["vigente"] <= 0:
            raise CancellationConflict(
                f"El producto '{linea['nombre']}' ya fue cancelado."
            )

        cantidad = linea["vigente"] if cantidad is None else cantidad

        if cantidad <= 0:
            raise CancellationConflict("La cantidad debe ser mayor que cero.")

        if cantidad > linea["vigente"]:
            raise CancellationConflict(
                f"Solo puedes cancelar {linea['vigente']} unidad(es) "
                f"de '{linea['nombre']}'."
            )

        resultado.append((linea, cantidad))

    return resultado


def recortar(texto: str, maximo: int = 250) -> str:
    """Evita superar el tamaño de las columnas Observacion de los historiales."""
    texto = texto or ""
    return texto if len(texto) <= maximo else texto[: maximo - 3] + "..."


def monto_linea(precio, cantidad: int) -> Decimal:
    return (Decimal(str(precio)) * cantidad).quantize(
        CENTAVOS, rounding=ROUND_HALF_UP
    )


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
    cursor.execute(
        """
        SELECT
            DP.IdDetallePedido,
            DP.IdProducto,
            PR.Nombre,
            DP.Cantidad,
            DP.PrecioUnitario,
            COALESCE((
                SELECT SUM(DC.Cantidad)
                FROM DetallesCancelacion DC
                INNER JOIN Cancelaciones C
                    ON C.IdCancelacion = DC.IdCancelacion
                WHERE DC.IdDetallePedido = DP.IdDetallePedido
                  AND C.Estado = 'APROBADA'
            ), 0) AS Cancelada
        FROM DetalleVenta DV
        INNER JOIN DetallesPedido DP
            ON DP.IdDetallePedido = DV.IdDetallePedido
        INNER JOIN Productos PR ON PR.IdProducto = DP.IdProducto
        WHERE DV.IdVenta = ?
        ORDER BY DP.IdDetallePedido;
        """,
        (id_venta,)
    )

    return [
        {
            "id_detalle_pedido": f.IdDetallePedido,
            "id_producto": f.IdProducto,
            "nombre": f.Nombre,
            "cantidad": f.Cantidad,
            "vigente": f.Cantidad - f.Cancelada,
            "precio": f.PrecioUnitario
        }
        for f in cursor.fetchall()
    ]


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
    monto_total = sum(
        (monto_linea(l["precio"], cant) for l, cant in lineas_cancelar),
        Decimal("0.00")
    )

    if estado == "SOLICITADA":
        cursor.execute(
            """
            INSERT INTO Cancelaciones (
                IdPedido, IdVenta, IdSolicitante, Tipo, Estado,
                Motivo, MontoReembolso
            )
            OUTPUT INSERTED.IdCancelacion
            VALUES (?, ?, ?, ?, 'SOLICITADA', ?, ?);
            """,
            (id_pedido, venta.IdVenta, id_solicitante, tipo, motivo, monto_total)
        )
    else:
        cursor.execute(
            """
            INSERT INTO Cancelaciones (
                IdPedido, IdVenta, IdSolicitante, Tipo, Estado,
                Motivo, MontoReembolso, FechaResolucion, IdResolutor
            )
            OUTPUT INSERTED.IdCancelacion
            VALUES (?, ?, ?, ?, 'APROBADA', ?, ?, SYSDATETIME(), ?);
            """,
            (
                id_pedido, venta.IdVenta, id_solicitante, tipo,
                motivo, monto_total, id_solicitante
            )
        )

    id_cancelacion = cursor.fetchone()[0]

    for linea, cantidad in lineas_cancelar:
        cursor.execute(
            """
            INSERT INTO DetallesCancelacion (
                IdCancelacion, IdDetallePedido, Cantidad, Monto
            )
            VALUES (?, ?, ?, ?);
            """,
            (
                id_cancelacion,
                linea["id_detalle_pedido"],
                cantidad,
                monto_linea(linea["precio"], cantidad)
            )
        )

    return id_cancelacion, monto_total


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
    """Marca la venta como CANCELADA y su envío (si existe) como CANCELADO."""
    cursor.execute(
        "UPDATE Ventas SET Estado = 'CANCELADA' WHERE IdVenta = ?;",
        (venta.IdVenta,)
    )

    _registrar_historial(
        cursor, "VENTA", venta.IdVenta,
        venta.Estado, "CANCELADA", recortar(observacion)
    )

    if venta.IdEnvio is not None and venta.EstadoEnvio not in ESTADOS_ENVIO_FINALES:
        cursor.execute(
            "UPDATE Envios SET Estado = 'CANCELADO' WHERE IdEnvio = ?;",
            (venta.IdEnvio,)
        )

        cursor.execute(
            """
            INSERT INTO HistorialEnvios (IdEnvio, Estado, Observacion)
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
    """Cancela de inmediato unidades de una venta no despachada."""
    cancelado_por_detalle = {
        l["id_detalle_pedido"]: c for l, c in lineas_cancelar
    }

    quedan = sum(
        l["vigente"] - cancelado_por_detalle.get(l["id_detalle_pedido"], 0)
        for l in lineas
    )

    tipo = "TOTAL" if quedan == 0 else "PARCIAL"

    id_cancelacion, monto = _insertar_cancelacion(
        cursor, id_pedido, venta, id_solicitante,
        motivo, lineas_cancelar, tipo, "APROBADA"
    )

    _devolver_inventario(cursor, lineas_cancelar)

    estado_venta = venta.Estado

    if quedan == 0:
        _cancelar_venta_y_envio(
            cursor, venta, f"Cancelación #{id_cancelacion}: {motivo}"
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
                "id_producto": l["id_producto"],
                "nombre": l["nombre"],
                "cantidad_cancelada": c
            }
            for l, c in lineas_cancelar
        ]
    }


def _crear_solicitud(cursor, id_pedido: int, venta, id_solicitante: int, motivo: str):
    """Solicitud de cancelación total de una venta ya despachada."""
    lineas = _lineas_venta(cursor, venta.IdVenta)
    lineas_cancelar = calcular_lineas_a_cancelar(lineas, None)

    id_cancelacion, monto = _insertar_cancelacion(
        cursor, id_pedido, venta, id_solicitante,
        motivo, lineas_cancelar, "TOTAL", "SOLICITADA"
    )

    cursor.execute(
        "UPDATE Ventas SET Estado = 'CANCELACION_SOLICITADA' WHERE IdVenta = ?;",
        (venta.IdVenta,)
    )

    _registrar_historial(
        cursor, "VENTA", venta.IdVenta,
        venta.Estado, "CANCELACION_SOLICITADA",
        recortar(f"Cancelación #{id_cancelacion} solicitada: {motivo}")
    )

    return {
        "id_cancelacion": id_cancelacion,
        "id_venta": venta.IdVenta,
        "tipo": "TOTAL",
        "estado": "SOLICITADA",
        "monto_reembolso": float(monto),
        "estado_venta": "CANCELACION_SOLICITADA",
        "mensaje": "La venta ya fue despachada: el vendedor debe aprobar la cancelación."
    }


def _validar_pedido_comprador(pedido, id_comprador: int):
    if pedido is None or pedido.IdComprador != id_comprador:
        raise OrderNotFound("Pedido no encontrado.")

    if pedido.Estado not in ESTADOS_PEDIDO_CANCELABLES:
        raise CancellationConflict(
            f"El pedido está en estado {pedido.Estado} y no se puede cancelar."
        )


def _ejecutar(funcion):
    """Abre conexión, ejecuta la función en una transacción y la cierra."""
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

def cancelar_pedido_total(id_comprador: int, id_pedido: int, motivo: str):
    def operacion(cursor):
        verificar_usuario_activo(cursor, id_comprador)

        pedido = _bloquear_pedido(cursor, id_pedido)
        _validar_pedido_comprador(pedido, id_comprador)

        ventas = _bloquear_ventas(cursor, id_pedido)

        entregadas = [v.IdVenta for v in ventas if v.Estado == "ENTREGADA"]

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
                lineas_cancelar = calcular_lineas_a_cancelar(lineas, None)

                resultados.append(_aplicar_inmediata(
                    cursor, id_pedido, venta, id_comprador,
                    motivo, lineas, lineas_cancelar
                ))

            elif venta.Estado == "ENVIADA":
                resultados.append(_crear_solicitud(
                    cursor, id_pedido, venta, id_comprador, motivo
                ))

            # CANCELADA o CANCELACION_SOLICITADA: no hay nada que hacer

        if not resultados:
            raise CancellationConflict(
                "No hay partes del pedido pendientes por cancelar."
            )

        estado_pedido = _sincronizar_estado_pedido(
            cursor, id_pedido, pedido.Estado
        )

        return {
            "mensaje": "Cancelación del pedido procesada.",
            "id_pedido": id_pedido,
            "estado_pedido": estado_pedido,
            "monto_reembolsado": round(sum(
                r["monto_reembolso"] for r in resultados
                if r["estado"] == "APROBADA"
            ), 2),
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
    productos: {id_producto: cantidad | None}. None = todas las unidades
    vigentes de ese producto.
    """
    def operacion(cursor):
        verificar_usuario_activo(cursor, id_comprador)

        pedido = _bloquear_pedido(cursor, id_pedido)
        _validar_pedido_comprador(pedido, id_comprador)

        ventas = _bloquear_ventas(cursor, id_pedido)

        # Agrupar lo solicitado por venta
        pendientes = dict(productos)
        resultados = []

        for venta in ventas:
            lineas = _lineas_venta(cursor, venta.IdVenta)
            ids_venta = {l["id_producto"] for l in lineas}
            solicitados = {
                p: c for p, c in pendientes.items() if p in ids_venta
            }

            if not solicitados:
                continue

            for p in solicitados:
                pendientes.pop(p)

            if venta.Estado == "ENVIADA":
                raise CancellationConflict(
                    f"La venta {venta.IdVenta} ya fue despachada. Solo puedes "
                    "solicitar su cancelación completa en "
                    f"POST /cancelaciones/ventas/{venta.IdVenta}."
                )

            if venta.Estado not in ESTADOS_VENTA_SIN_DESPACHAR:
                raise CancellationConflict(
                    f"La venta {venta.IdVenta} está en estado {venta.Estado} "
                    "y no admite cancelaciones."
                )

            lineas_cancelar = calcular_lineas_a_cancelar(lineas, solicitados)

            resultados.append(_aplicar_inmediata(
                cursor, id_pedido, venta, id_comprador,
                motivo, lineas, lineas_cancelar
            ))

        if pendientes:
            raise CancellationConflict(
                "Estos productos no hacen parte del pedido: "
                + ", ".join(map(str, pendientes))
            )

        estado_pedido = _sincronizar_estado_pedido(
            cursor, id_pedido, pedido.Estado
        )

        return {
            "mensaje": "Cancelación parcial aplicada.",
            "id_pedido": id_pedido,
            "estado_pedido": estado_pedido,
            "monto_reembolsado": round(
                sum(r["monto_reembolso"] for r in resultados), 2
            ),
            "cancelaciones": resultados
        }

    return _ejecutar(operacion)


def cancelar_venta(id_usuario: int, id_venta: int, motivo: str):
    """
    Cancela la parte de un vendedor dentro de un pedido.
    - Comprador: inmediata si no se ha despachado; solicitud si ya se envió.
    - Vendedor: solo si aún no la ha despachado (por ejemplo, sin existencias).
    """
    def operacion(cursor):
        verificar_usuario_activo(cursor, id_usuario)

        cursor.execute(
            """
            SELECT V.IdPedido, V.IdVendedor, P.IdComprador
            FROM Ventas V
            INNER JOIN Pedidos P ON P.IdPedido = V.IdPedido
            WHERE V.IdVenta = ?;
            """,
            (id_venta,)
        )

        datos = cursor.fetchone()

        if datos is None or id_usuario not in (datos.IdComprador, datos.IdVendedor):
            raise SaleNotFound("Venta no encontrada.")

        es_comprador = id_usuario == datos.IdComprador
        id_pedido = datos.IdPedido

        pedido = _bloquear_pedido(cursor, id_pedido)

        if pedido.Estado not in ESTADOS_PEDIDO_CANCELABLES:
            raise CancellationConflict(
                f"El pedido está en estado {pedido.Estado} y no se puede cancelar."
            )

        venta = next(
            v for v in _bloquear_ventas(cursor, id_pedido)
            if v.IdVenta == id_venta
        )

        if venta.Estado in ESTADOS_VENTA_SIN_DESPACHAR:
            lineas = _lineas_venta(cursor, id_venta)
            lineas_cancelar = calcular_lineas_a_cancelar(lineas, None)

            resultado = _aplicar_inmediata(
                cursor, id_pedido, venta, id_usuario,
                motivo, lineas, lineas_cancelar
            )

        elif venta.Estado == "ENVIADA":
            if not es_comprador:
                raise CancellationConflict(
                    "La venta ya fue despachada; el vendedor no puede "
                    "cancelarla. Si hay un inconveniente, marca el envío "
                    "como PROBLEMA."
                )

            resultado = _crear_solicitud(
                cursor, id_pedido, venta, id_usuario, motivo
            )

        elif venta.Estado == "CANCELACION_SOLICITADA":
            raise CancellationConflict(
                "Ya existe una solicitud de cancelación pendiente para esta venta."
            )

        else:
            raise CancellationConflict(
                f"La venta está en estado {venta.Estado} y no se puede cancelar."
            )

        resultado["estado_pedido"] = _sincronizar_estado_pedido(
            cursor, id_pedido, pedido.Estado
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

        cursor.execute(
            """
            SELECT C.IdPedido, C.IdVenta, V.IdVendedor
            FROM Cancelaciones C
            INNER JOIN Ventas V ON V.IdVenta = C.IdVenta
            WHERE C.IdCancelacion = ?;
            """,
            (id_cancelacion,)
        )

        datos = cursor.fetchone()

        if datos is None:
            raise CancellationNotFound("Cancelación no encontrada.")

        if datos.IdVendedor != id_vendedor:
            raise CancellationForbidden(
                "Solo el vendedor de la venta puede responder esta solicitud."
            )

        # Orden de bloqueo: pedido -> ventas/envíos -> cancelación
        pedido = _bloquear_pedido(cursor, datos.IdPedido)

        venta = next(
            v for v in _bloquear_ventas(cursor, datos.IdPedido)
            if v.IdVenta == datos.IdVenta
        )

        cursor.execute(
            """
            SELECT Estado, Motivo
            FROM Cancelaciones WITH (UPDLOCK, ROWLOCK)
            WHERE IdCancelacion = ?;
            """,
            (id_cancelacion,)
        )

        cancelacion = cursor.fetchone()

        if cancelacion.Estado != "SOLICITADA":
            raise CancellationConflict(
                f"La solicitud ya fue respondida ({cancelacion.Estado})."
            )

        if venta.Estado != "CANCELACION_SOLICITADA":
            raise CancellationConflict(
                f"La venta está en estado {venta.Estado}; no se puede responder."
            )

        nuevo_estado = "APROBADA" if aprobar else "RECHAZADA"

        cursor.execute(
            """
            UPDATE Cancelaciones
            SET Estado = ?,
                FechaResolucion = SYSDATETIME(),
                IdResolutor = ?,
                ObservacionResolucion = ?
            WHERE IdCancelacion = ?;
            """,
            (nuevo_estado, id_vendedor, observacion, id_cancelacion)
        )

        if aprobar:
            cursor.execute(
                """
                SELECT DC.IdDetallePedido, DC.Cantidad, DP.IdProducto
                FROM DetallesCancelacion DC
                INNER JOIN DetallesPedido DP
                    ON DP.IdDetallePedido = DC.IdDetallePedido
                WHERE DC.IdCancelacion = ?;
                """,
                (id_cancelacion,)
            )

            lineas_cancelar = [
                ({"id_producto": f.IdProducto}, f.Cantidad)
                for f in cursor.fetchall()
            ]

            _devolver_inventario(cursor, lineas_cancelar)

            _cancelar_venta_y_envio(
                cursor, venta,
                f"Cancelación #{id_cancelacion} aprobada por el vendedor."
            )

            estado_venta = "CANCELADA"

        else:
            # Solo las ventas ENVIADA pueden tener solicitud: se restaura
            cursor.execute(
                "UPDATE Ventas SET Estado = 'ENVIADA' WHERE IdVenta = ?;",
                (venta.IdVenta,)
            )

            _registrar_historial(
                cursor, "VENTA", venta.IdVenta,
                "CANCELACION_SOLICITADA", "ENVIADA",
                recortar(
                    f"Cancelación #{id_cancelacion} rechazada: "
                    f"{observacion or 'sin observación'}"
                )
            )

            estado_venta = "ENVIADA"

        estado_pedido = _sincronizar_estado_pedido(
            cursor, datos.IdPedido, pedido.Estado
        )

        return {
            "mensaje": (
                "Cancelación aprobada: inventario devuelto y reembolso simulado."
                if aprobar else
                "Solicitud de cancelación rechazada."
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
        C.IdCancelacion,
        C.IdPedido,
        C.IdVenta,
        C.IdSolicitante,
        C.Tipo,
        C.Estado,
        C.Motivo,
        C.MontoReembolso,
        C.FechaSolicitud,
        C.FechaResolucion,
        C.ObservacionResolucion,
        V.IdVendedor,
        P.IdComprador
    FROM Cancelaciones C
    INNER JOIN Ventas V ON V.IdVenta = C.IdVenta
    INNER JOIN Pedidos P ON P.IdPedido = C.IdPedido
"""


def _cancelacion_a_diccionario(fila, id_usuario: int):
    return {
        "id_cancelacion": fila.IdCancelacion,
        "id_pedido": fila.IdPedido,
        "id_venta": fila.IdVenta,
        "rol": "COMPRADOR" if fila.IdComprador == id_usuario else "VENDEDOR",
        "solicitada_por": (
            "COMPRADOR" if fila.IdSolicitante == fila.IdComprador else "VENDEDOR"
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
            condicion = "(P.IdComprador = ? OR V.IdVendedor = ?)"
            parametros = [id_usuario, id_usuario]

        consulta = _SELECT_CANCELACIONES + f" WHERE {condicion}"

        if estado:
            consulta += " AND C.Estado = ?"
            parametros.append(estado)

        consulta += " ORDER BY C.IdCancelacion DESC;"

        cursor.execute(consulta, parametros)

        return [
            _cancelacion_a_diccionario(f, id_usuario)
            for f in cursor.fetchall()
        ]

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def obtener_cancelacion(id_usuario: int, id_cancelacion: int):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            _SELECT_CANCELACIONES + """
            WHERE C.IdCancelacion = ?
              AND (P.IdComprador = ? OR V.IdVendedor = ?);
            """,
            (id_cancelacion, id_usuario, id_usuario)
        )

        fila = cursor.fetchone()

        if fila is None:
            raise CancellationNotFound("Cancelación no encontrada.")

        resultado = _cancelacion_a_diccionario(fila, id_usuario)

        cursor.execute(
            """
            SELECT
                DC.IdDetallePedido,
                DP.IdProducto,
                PR.Nombre,
                DC.Cantidad,
                DC.Monto
            FROM DetallesCancelacion DC
            INNER JOIN DetallesPedido DP
                ON DP.IdDetallePedido = DC.IdDetallePedido
            INNER JOIN Productos PR ON PR.IdProducto = DP.IdProducto
            WHERE DC.IdCancelacion = ?
            ORDER BY DC.IdDetalleCancelacion;
            """,
            (id_cancelacion,)
        )

        resultado["productos"] = [
            {
                "id_detalle_pedido": f.IdDetallePedido,
                "id_producto": f.IdProducto,
                "nombre": f.Nombre,
                "cantidad": f.Cantidad,
                "monto": a_float(f.Monto)
            }
            for f in cursor.fetchall()
        ]

        return resultado

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()
