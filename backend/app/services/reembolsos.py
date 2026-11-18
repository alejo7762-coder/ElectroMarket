"""
Ciclo de vida de los reembolsos simulados.

1. Al aprobarse una cancelación se registra el reembolso en PENDIENTE
   (app/services/cancelaciones.py -> _registrar_reembolso).
2. La pasarela simulada lo procesa pasados MINUTOS_PROCESAMIENTO
   minutos: queda PROCESADO, con referencia y fecha de procesamiento.
   El procesamiento se aplica cada vez que el comprador consulta sus
   reembolsos o pagos, así no se necesita un proceso en segundo plano.
3. El pago muestra su estado de reembolso: SIN_REEMBOLSO,
   REEMBOLSO_PARCIAL o REEMBOLSADO.

Columnas añadidas por database/scripts/04_reembolsos.sql.
"""

from app.db.connection import get_connection
from app.services.utilidades import a_float, iso, verificar_usuario_activo


MINUTOS_PROCESAMIENTO = 1


class RefundNotFound(Exception):
    pass


def referencia_reembolso(id_reembolso: int) -> str:
    return f"RMB-{id_reembolso:08d}"


def estado_reembolso_pago(valor_pago: float, reembolsado: float) -> str:
    """Estado de reembolso de un pago a partir de lo devuelto. Función pura."""
    if reembolsado <= 0:
        return "SIN_REEMBOLSO"
    if reembolsado + 0.005 >= valor_pago:
        return "REEMBOLSADO"
    return "REEMBOLSO_PARCIAL"


def procesar_reembolsos_pendientes(cursor, id_comprador: int):
    """Simula la pasarela: procesa los reembolsos pendientes que ya cumplieron el tiempo."""
    cursor.execute(
        """
        UPDATE R
        SET R.Estado = 'PROCESADO',
            R.FechaProcesado = SYSDATETIME(),
            R.Referencia = 'RMB-' + RIGHT('00000000' + CAST(R.IdReembolso AS VARCHAR(10)), 8)
        FROM Reembolsos R
        INNER JOIN Pagos PG ON PG.IdPago = R.IdPago
        INNER JOIN Pedidos P ON P.IdPedido = PG.IdPedido
        WHERE P.IdComprador = ?
          AND R.Estado = 'PENDIENTE'
          AND R.FechaSolicitud <= DATEADD(MINUTE, -?, SYSDATETIME());
        """,
        (id_comprador, MINUTOS_PROCESAMIENTO),
    )


_SELECT_REEMBOLSOS = """
    SELECT
        R.IdReembolso,
        R.IdPago,
        R.IdSolicitud,
        R.Valor,
        R.Estado,
        R.Referencia,
        R.FechaSolicitud,
        R.FechaProcesado,
        PG.IdPedido,
        PG.Metodo,
        SC.TipoSolicitud,
        SC.Motivo
    FROM Reembolsos R
    INNER JOIN Pagos PG ON PG.IdPago = R.IdPago
    INNER JOIN Pedidos P ON P.IdPedido = PG.IdPedido
    LEFT JOIN SolicitudesCancelacion SC ON SC.IdSolicitud = R.IdSolicitud
"""


def _a_diccionario(fila):
    return {
        "id_reembolso": fila.IdReembolso,
        "id_pago": fila.IdPago,
        "id_pedido": fila.IdPedido,
        "id_cancelacion": fila.IdSolicitud,
        "tipo_cancelacion": fila.TipoSolicitud,
        "motivo": fila.Motivo,
        "valor": a_float(fila.Valor),
        "estado": fila.Estado,
        "metodo_destino": fila.Metodo,
        "referencia": fila.Referencia,
        "fecha_solicitud": iso(fila.FechaSolicitud),
        "fecha_procesado": iso(fila.FechaProcesado),
    }


def _ejecutar(id_usuario: int, consulta: str, parametros: tuple):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        verificar_usuario_activo(cursor, id_usuario)
        procesar_reembolsos_pendientes(cursor, id_usuario)
        connection.commit()

        cursor.execute(_SELECT_REEMBOLSOS + consulta, parametros)
        return [_a_diccionario(f) for f in cursor.fetchall()]

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def listar_reembolsos(id_usuario: int, id_pedido: int | None = None):
    consulta = " WHERE P.IdComprador = ?"
    parametros = [id_usuario]

    if id_pedido is not None:
        consulta += " AND P.IdPedido = ?"
        parametros.append(id_pedido)

    return _ejecutar(id_usuario, consulta + " ORDER BY R.IdReembolso DESC;", tuple(parametros))


def obtener_reembolso(id_usuario: int, id_reembolso: int):
    filas = _ejecutar(
        id_usuario,
        " WHERE R.IdReembolso = ? AND P.IdComprador = ?;",
        (id_reembolso, id_usuario),
    )

    if not filas:
        raise RefundNotFound("Reembolso no encontrado.")

    return filas[0]
