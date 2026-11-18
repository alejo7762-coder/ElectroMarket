"""
Reseñas y calificaciones de productos y vendedores.

Reglas:
- Solo el comprador de una venta ENTREGADA puede reseñar sus productos.
- Una reseña por producto en cada venta (UQ_Resenas_Venta_Producto).
- No se reseña un producto cuyas unidades se cancelaron por completo.
- El comprador puede editar su reseña; el comentario es opcional.

Tabla: Resenas (database/scripts/06_resenas.sql)
"""

from contextlib import contextmanager

from app.db.connection import get_connection
from app.errores import ReviewConflict, ReviewForbidden, ReviewNotFound
from app.services.utilidades import iso, verificar_usuario_activo


@contextmanager
def _cursor(transaccion: bool = False):
    conexion = get_connection()
    cursor = conexion.cursor()
    try:
        yield cursor
        if transaccion:
            conexion.commit()
    except Exception:
        if transaccion:
            conexion.rollback()
        raise
    finally:
        cursor.close()
        conexion.close()


def nombre_publico(nombre: str, apellido: str | None) -> str:
    """«Luis C.»: el comprador se muestra con la inicial del apellido."""
    inicial = f" {apellido.strip()[0].upper()}." if apellido and apellido.strip() else ""
    return f"{nombre.strip()}{inicial}"


def resumen_calificaciones(calificaciones: list[int]) -> dict:
    """Promedio, total y distribución de 1 a 5 estrellas. Función pura."""
    total = len(calificaciones)
    distribucion = {estrellas: calificaciones.count(estrellas) for estrellas in range(5, 0, -1)}
    return {
        "promedio": round(sum(calificaciones) / total, 2) if total else None,
        "total": total,
        "distribucion": distribucion,
    }


def _limpiar(comentario: str | None) -> str | None:
    comentario = (comentario or "").strip()
    return comentario or None


_SELECT_RESENAS = """
    SELECT
        R.IdResena, R.IdVenta, R.IdProducto, R.IdVendedor, R.IdComprador,
        R.CalificacionProducto, R.CalificacionVendedor, R.Comentario,
        R.FechaResena, R.FechaEdicion,
        U.Nombre AS NombreComprador, U.Apellido AS ApellidoComprador,
        P.Nombre AS Producto
    FROM Resenas R
    INNER JOIN Usuarios U ON U.IdUsuario = R.IdComprador
    INNER JOIN Productos P ON P.IdProducto = R.IdProducto
"""


def _a_diccionario(fila) -> dict:
    return {
        "id_resena": fila.IdResena,
        "id_venta": fila.IdVenta,
        "id_producto": fila.IdProducto,
        "producto": fila.Producto,
        "id_vendedor": fila.IdVendedor,
        "comprador": nombre_publico(fila.NombreComprador, fila.ApellidoComprador),
        "calificacion_producto": fila.CalificacionProducto,
        "calificacion_vendedor": fila.CalificacionVendedor,
        "comentario": fila.Comentario,
        "fecha": iso(fila.FechaResena),
        "editada": fila.FechaEdicion is not None,
        "compra_verificada": True,
    }


# ----------------------------------------------------------------------
# Crear y editar
# ----------------------------------------------------------------------

def _validar_compra(cursor, id_usuario: int, id_venta: int, id_producto: int):
    cursor.execute(
        """
        SELECT V.IdVendedor, V.Estado, PE.IdComprador,
               DP.Cantidad - COALESCE((
                   SELECT SUM(DSC.CantidadSolicitada)
                   FROM DetalleSolicitudCancelacion DSC
                   INNER JOIN SolicitudesCancelacion SC ON SC.IdSolicitud = DSC.IdSolicitud
                   WHERE DSC.IdDetallePedido = DP.IdDetallePedido AND SC.Estado = 'APROBADA'
               ), 0) AS Vigente
        FROM Ventas V
        INNER JOIN Pedidos PE ON PE.IdPedido = V.IdPedido
        INNER JOIN DetalleVenta DV ON DV.IdVenta = V.IdVenta
        INNER JOIN DetallesPedido DP ON DP.IdDetallePedido = DV.IdDetallePedido
        WHERE V.IdVenta = ? AND DP.IdProducto = ?;
        """,
        (id_venta, id_producto),
    )
    compra = cursor.fetchone()

    if compra is None:
        raise ReviewNotFound("El producto no pertenece a esa compra.")
    if compra.IdComprador != id_usuario:
        raise ReviewForbidden("Solo el comprador puede reseñar esta compra.")
    if compra.Estado != "ENTREGADA":
        raise ReviewConflict("Solo puedes reseñar compras entregadas.")
    if compra.Vigente <= 0:
        raise ReviewConflict("No puedes reseñar un producto que cancelaste.")

    return compra


def crear_resena(id_usuario: int, id_venta: int, id_producto: int, calificacion_producto: int,
                 calificacion_vendedor: int, comentario: str | None) -> dict:
    with _cursor(transaccion=True) as cursor:
        verificar_usuario_activo(cursor, id_usuario)
        compra = _validar_compra(cursor, id_usuario, id_venta, id_producto)

        cursor.execute(
            "SELECT IdResena FROM Resenas WITH (UPDLOCK, HOLDLOCK) WHERE IdVenta = ? AND IdProducto = ?;",
            (id_venta, id_producto),
        )
        if cursor.fetchone():
            raise ReviewConflict("Ya reseñaste este producto; puedes editar tu reseña.")

        cursor.execute(
            """
            INSERT INTO Resenas (IdVenta, IdProducto, IdComprador, IdVendedor,
                                 CalificacionProducto, CalificacionVendedor, Comentario)
            OUTPUT INSERTED.IdResena
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (id_venta, id_producto, id_usuario, compra.IdVendedor,
             calificacion_producto, calificacion_vendedor, _limpiar(comentario)),
        )
        id_resena = cursor.fetchone()[0]

        cursor.execute(_SELECT_RESENAS + " WHERE R.IdResena = ?;", (id_resena,))
        return _a_diccionario(cursor.fetchone())


def editar_resena(id_usuario: int, id_resena: int, calificacion_producto: int,
                  calificacion_vendedor: int, comentario: str | None) -> dict:
    with _cursor(transaccion=True) as cursor:
        verificar_usuario_activo(cursor, id_usuario)
        cursor.execute("SELECT IdComprador FROM Resenas WITH (UPDLOCK) WHERE IdResena = ?;", (id_resena,))
        fila = cursor.fetchone()

        if fila is None:
            raise ReviewNotFound("Reseña no encontrada.")
        if fila.IdComprador != id_usuario:
            raise ReviewForbidden("Solo puedes editar tus propias reseñas.")

        cursor.execute(
            """
            UPDATE Resenas
            SET CalificacionProducto = ?, CalificacionVendedor = ?, Comentario = ?, FechaEdicion = SYSDATETIME()
            WHERE IdResena = ?;
            """,
            (calificacion_producto, calificacion_vendedor, _limpiar(comentario), id_resena),
        )
        cursor.execute(_SELECT_RESENAS + " WHERE R.IdResena = ?;", (id_resena,))
        return _a_diccionario(cursor.fetchone())


# ----------------------------------------------------------------------
# Consultas
# ----------------------------------------------------------------------

def resenas_producto(id_producto: int) -> dict:
    with _cursor() as cursor:
        cursor.execute(_SELECT_RESENAS + " WHERE R.IdProducto = ? ORDER BY R.FechaResena DESC;", (id_producto,))
        resenas = [_a_diccionario(f) for f in cursor.fetchall()]

    return {**resumen_calificaciones([r["calificacion_producto"] for r in resenas]), "resenas": resenas}


def resenas_vendedor(id_vendedor: int) -> dict:
    with _cursor() as cursor:
        cursor.execute(_SELECT_RESENAS + " WHERE R.IdVendedor = ? ORDER BY R.FechaResena DESC;", (id_vendedor,))
        resenas = [_a_diccionario(f) for f in cursor.fetchall()]

    return {**resumen_calificaciones([r["calificacion_vendedor"] for r in resenas]), "resenas": resenas}


def mis_resenas(id_usuario: int, id_pedido: int | None = None) -> list[dict]:
    consulta = _SELECT_RESENAS + " INNER JOIN Ventas V ON V.IdVenta = R.IdVenta WHERE R.IdComprador = ?"
    parametros = [id_usuario]
    if id_pedido is not None:
        consulta += " AND V.IdPedido = ?"
        parametros.append(id_pedido)

    with _cursor() as cursor:
        verificar_usuario_activo(cursor, id_usuario)
        cursor.execute(consulta + " ORDER BY R.FechaResena DESC;", parametros)
        return [_a_diccionario(f) for f in cursor.fetchall()]
