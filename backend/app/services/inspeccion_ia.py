"""
Integración del inspector de estado (app/ia/inspector.py) con la base de datos.

- inspeccionar_y_guardar: analiza la publicación y guarda el resultado en
  InspeccionesIA. Si la IA falla, se registra en el log y la publicación
  sigue adelante (la IA ayuda, no bloquea la venta).
- obtener_inspeccion: lee el último análisis de un producto.
"""

import json
import logging

from app.ia import inspector

logger = logging.getLogger("electromarket.ia")


def inspeccionar_y_guardar(cursor, id_producto: int, nombre: str, descripcion: str,
                           defectos: str | None, checklist: dict | None, condicion: str):
    try:
        resultado = inspector.analizar(nombre, descripcion, defectos, checklist, condicion)
    except Exception:
        logger.exception("No fue posible analizar con IA el producto %s", id_producto)
        return None

    valores = (
        resultado["condicion_sugerida"],
        resultado["confianza"],
        resultado["coherencia"],
        json.dumps(resultado["alertas"], ensure_ascii=False),
        json.dumps(resultado["terminos_clave"], ensure_ascii=False)[:500],
        resultado["version_modelo"],
    )

    cursor.execute(
        """
        UPDATE InspeccionesIA
        SET CondicionSugerida = ?, Confianza = ?, Coherencia = ?, Alertas = ?,
            TerminosClave = ?, VersionModelo = ?, FechaAnalisis = SYSDATETIME()
        WHERE IdProducto = ?;
        """,
        (*valores, id_producto),
    )

    if cursor.rowcount == 0:
        cursor.execute(
            """
            INSERT INTO InspeccionesIA
                (IdProducto, CondicionSugerida, Confianza, Coherencia, Alertas, TerminosClave, VersionModelo)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (id_producto, *valores),
        )

    return resultado


def obtener_inspeccion(cursor, id_producto: int):
    cursor.execute(
        """
        SELECT CondicionSugerida, Confianza, Coherencia, Alertas, TerminosClave, VersionModelo, FechaAnalisis
        FROM InspeccionesIA
        WHERE IdProducto = ?;
        """,
        (id_producto,),
    )
    fila = cursor.fetchone()

    if fila is None:
        return None

    return {
        "condicion_sugerida": fila.CondicionSugerida,
        "confianza": float(fila.Confianza),
        "coherencia": fila.Coherencia,
        "alertas": json.loads(fila.Alertas or "[]"),
        "terminos_clave": json.loads(fila.TerminosClave or "[]"),
        "version_modelo": fila.VersionModelo,
        "fecha_analisis": fila.FechaAnalisis.isoformat(),
    }
