"""
Funciones de apoyo compartidas por los módulos de pedidos, pagos,
ventas y cancelaciones.
"""

from decimal import Decimal

from app.services.carrito import UserNotActive


# Posibles nombres de la columna de fecha de creación en cada tabla.
# Se consulta con SELECT * para no depender del nombre exacto.
# Un pago con reembolso parcial o total sigue contando como cobrado
ESTADOS_PAGO_COBRADO = ("APROBADO", "REEMBOLSO_PARCIAL", "REEMBOLSADO")

# Tipo de una solicitud de cancelación para la API. En la BD toda solicitud
# con venta es PARCIAL (CK_Solicitudes_Tipo); es TOTAL si cubrió todas las
# unidades que seguían vigentes en la venta cuando se hizo.
SQL_TIPO_CANCELACION = """
    CASE
        WHEN SC.IdVenta IS NULL THEN SC.TipoSolicitud
        WHEN (SELECT SUM(DSCT.CantidadSolicitada)
              FROM DetalleSolicitudCancelacion DSCT
              WHERE DSCT.IdSolicitud = SC.IdSolicitud)
          >= (SELECT SUM(DPT.Cantidad)
              FROM DetalleVenta DVT
              INNER JOIN DetallesPedido DPT ON DPT.IdDetallePedido = DVT.IdDetallePedido
              WHERE DVT.IdVenta = SC.IdVenta)
           - (SELECT COALESCE(SUM(DAT.CantidadSolicitada), 0)
              FROM DetalleSolicitudCancelacion DAT
              INNER JOIN SolicitudesCancelacion SAT ON SAT.IdSolicitud = DAT.IdSolicitud
              WHERE SAT.IdVenta = SC.IdVenta
                AND SAT.Estado = 'APROBADA'
                AND SAT.IdSolicitud < SC.IdSolicitud)
            THEN 'TOTAL'
        ELSE 'PARCIAL'
    END
"""

COLUMNAS_FECHA = (
    "FechaPedido",
    "FechaVenta",
    "FechaCreacion",
    "FechaRegistro",
    "Fecha"
)


def iso(valor):
    return valor.isoformat() if valor else None


def a_float(valor):
    if valor is None:
        return 0.0

    return float(Decimal(str(valor)))


def fecha_creacion(fila):
    for columna in COLUMNAS_FECHA:
        try:
            valor = getattr(fila, columna)
        except AttributeError:
            continue

        return iso(valor)

    return None


def verificar_usuario_activo(cursor, id_usuario: int):
    cursor.execute(
        "SELECT Estado FROM Usuarios WHERE IdUsuario = ?;",
        (id_usuario,)
    )

    usuario = cursor.fetchone()

    if usuario is None or usuario.Estado != "ACTIVO":
        raise UserNotActive("El usuario no existe o no está activo.")
