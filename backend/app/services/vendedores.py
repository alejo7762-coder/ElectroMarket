"""
Perfil público del vendedor e índice de fiabilidad.

El índice (0 a 100) combina cinco factores calculados con datos reales del
sistema, para que el comprador sepa qué tan confiable es el vendedor:

    Calificación   40  promedio de estrellas al vendedor (bayesiano: con
                       pocas reseñas se acerca a 3,5 para no premiar ni
                       castigar en exceso una sola opinión)
    Experiencia    25  ventas entregadas (máximo con 20)
    Cumplimiento   20  ventas que el vendedor NO canceló por su cuenta
    Verificación   10  productos publicados con «Estado verificado»
    Antigüedad      5  meses desde el registro (máximo con 12)

Niveles: ALTA (80 o más), MEDIA (55 a 79), BAJA (menos de 55) y NUEVO si
todavía no tiene ventas entregadas ni reseñas.
"""

from datetime import datetime

from app.errores import SellerNotFound
from app.services.resenas import _cursor, resumen_calificaciones
from app.services.utilidades import iso
from app.services.verificacion import SQL_NIVEL_VERIFICACION

PRIOR_ESTRELLAS = 3.5
PESO_PRIOR = 3
TOPE_VENTAS = 20
TOPE_MESES = 12

NIVELES = {"ALTA": "Fiabilidad alta", "MEDIA": "Fiabilidad media", "BAJA": "Fiabilidad baja", "NUEVO": "Vendedor nuevo"}


def calcular_fiabilidad(calificaciones: list[int], ventas_totales: int, entregadas: int,
                        canceladas_por_vendedor: int, publicados: int, verificados: int, meses: int) -> dict:
    """Índice de fiabilidad y sus factores. Función pura."""
    n = len(calificaciones)
    bayesiano = (PRIOR_ESTRELLAS * PESO_PRIOR + sum(calificaciones)) / (PESO_PRIOR + n)

    factores = [
        ("Calificación", 40 * (bayesiano - 1) / 4,
         f"{sum(calificaciones) / n:.1f}".replace(".", ",") + f" de 5 en {n} reseña{'s' if n != 1 else ''}" if n else "Sin reseñas todavía"),
        ("Experiencia", 25 * min(entregadas, TOPE_VENTAS) / TOPE_VENTAS,
         f"{entregadas} venta{'s' if entregadas != 1 else ''} entregada{'s' if entregadas != 1 else ''}"),
        ("Cumplimiento", 20 * (1 - canceladas_por_vendedor / ventas_totales) if ventas_totales else 10,
         f"{canceladas_por_vendedor} de {ventas_totales} ventas canceladas por el vendedor" if ventas_totales else "Sin ventas todavía"),
        ("Verificación", 10 * verificados / publicados if publicados else 0,
         f"{verificados} de {publicados} productos con estado verificado" if publicados else "Sin productos publicados"),
        ("Antigüedad", 5 * min(meses, TOPE_MESES) / TOPE_MESES, f"{meses} mes{'es' if meses != 1 else ''} en ElectroMarket"),
    ]
    maximos = {"Calificación": 40, "Experiencia": 25, "Cumplimiento": 20, "Verificación": 10, "Antigüedad": 5}
    indice = round(sum(puntos for _, puntos, _ in factores))

    if entregadas == 0 and n == 0:
        nivel = "NUEVO"
    elif indice >= 80:
        nivel = "ALTA"
    elif indice >= 55:
        nivel = "MEDIA"
    else:
        nivel = "BAJA"

    return {
        "indice": indice,
        "nivel": nivel,
        "texto": NIVELES[nivel],
        "factores": [
            {"factor": nombre, "puntos": round(puntos, 1), "maximo": maximos[nombre], "detalle": detalle}
            for nombre, puntos, detalle in factores
        ],
    }


def _meses_desde(fecha: datetime) -> int:
    hoy = datetime.now()
    return max(0, (hoy.year - fecha.year) * 12 + hoy.month - fecha.month - (hoy.day < fecha.day))


def perfil_vendedor(id_vendedor: int) -> dict:
    with _cursor() as cursor:
        cursor.execute(
            "SELECT Nombre, Apellido, FechaRegistro, Estado FROM Usuarios WHERE IdUsuario = ?;",
            (id_vendedor,),
        )
        usuario = cursor.fetchone()
        if usuario is None or usuario.Estado != "ACTIVO":
            raise SellerNotFound("El vendedor no existe o no está activo.")

        cursor.execute(
            """
            SELECT
                COUNT(*) AS Totales,
                SUM(CASE WHEN V.Estado = 'ENTREGADA' THEN 1 ELSE 0 END) AS Entregadas,
                SUM(CASE WHEN V.Estado = 'CANCELADA' AND CV.IdVenta IS NOT NULL THEN 1 ELSE 0 END) AS CanceladasVendedor
            FROM Ventas V
            LEFT JOIN (
                -- ventas cuya cancelación pidió el propio vendedor
                SELECT DISTINCT SC.IdVenta
                FROM SolicitudesCancelacion SC
                INNER JOIN Ventas V2 ON V2.IdVenta = SC.IdVenta
                WHERE SC.IdUsuario = V2.IdVendedor AND SC.Estado = 'APROBADA'
            ) CV ON CV.IdVenta = V.IdVenta
            WHERE V.IdVendedor = ?;
            """,
            (id_vendedor,),
        )
        ventas = cursor.fetchone()

        cursor.execute(
            """
            SELECT COUNT(*) AS Publicados,
                   SUM(CASE WHEN T.Nivel = 'VERIFICADO' THEN 1 ELSE 0 END) AS Verificados
            FROM (
                SELECT """ + SQL_NIVEL_VERIFICACION + """ AS Nivel
                FROM Productos P
                LEFT JOIN VerificacionProductos VP ON VP.IdProducto = P.IdProducto
                WHERE P.IdVendedor = ? AND P.Estado = 'PUBLICADO'
            ) T;
            """,
            (id_vendedor,),
        )
        productos = cursor.fetchone()

        cursor.execute(
            "SELECT CalificacionVendedor, CalificacionProducto FROM Resenas WHERE IdVendedor = ?;",
            (id_vendedor,),
        )
        filas = cursor.fetchall()

    calificaciones = [f.CalificacionVendedor for f in filas]
    meses = _meses_desde(usuario.FechaRegistro)

    return {
        "id_vendedor": id_vendedor,
        "nombre": f"{usuario.Nombre} {usuario.Apellido}".strip(),
        "miembro_desde": iso(usuario.FechaRegistro),
        "ventas_entregadas": int(ventas.Entregadas or 0),
        "productos_publicados": int(productos.Publicados or 0),
        "calificacion_vendedor": resumen_calificaciones(calificaciones),
        "calificacion_productos": resumen_calificaciones([f.CalificacionProducto for f in filas]),
        "fiabilidad": calcular_fiabilidad(
            calificaciones, int(ventas.Totales or 0), int(ventas.Entregadas or 0),
            int(ventas.CanceladasVendedor or 0), int(productos.Publicados or 0),
            int(productos.Verificados or 0), meses,
        ),
    }
