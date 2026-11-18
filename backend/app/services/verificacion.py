"""
Verificación del estado físico y funcional de los productos.

El vendedor declara un checklist y describe los defectos al publicar.
Con eso, el número de fotos y la condición se calcula un nivel de
verificación (VERIFICADO, PARCIAL o SIN_VERIFICAR) y un puntaje 0-100
que la tienda muestra como insignia y barra de estado.

Tabla: VerificacionProductos (database/scripts/05_verificacion_productos.sql)
"""

MIN_FOTOS_VERIFICADO = 3

# clave de la API -> (columna en la BD, texto para el comprador, esencial)
CRITERIOS = {
    "enciende": ("Enciende", "Enciende y funciona correctamente", True),
    "pantalla_sin_danos": ("PantallaSinDanos", "Pantalla o carcasa sin daños", True),
    "bateria_ok": ("BateriaOk", "Batería o alimentación en buen estado", True),
    "sin_reparaciones": ("SinReparaciones", "Sin reparaciones ni piezas cambiadas", False),
    "accesorios_completos": ("AccesoriosCompletos", "Incluye accesorios originales", False),
    "con_garantia": ("ConGarantia", "Conserva garantía o factura", False),
}

PUNTOS_CONDICION = {"COMO_NUEVO": 30, "BUENO": 20, "ACEPTABLE": 10}

SIN_DEFECTOS = ("ninguno", "ninguna", "sin defectos", "no tiene", "n/a", "na")


def evaluar_verificacion(checklist: dict | None, total_fotos: int, condicion: str, defectos: str | None):
    """
    Calcula nivel, puntaje y requisitos faltantes. Función pura.

    - VERIFICADO: todos los criterios esenciales, al menos
      MIN_FOTOS_VERIFICADO fotos y defectos descritos.
    - PARCIAL: hay checklist pero falta algún requisito.
    - SIN_VERIFICAR: el vendedor no completó el checklist.
    """
    if not checklist:
        return {
            "nivel": "SIN_VERIFICAR",
            "puntaje": 0,
            "faltantes": ["El vendedor no completó el checklist de estado."],
            "criterios": [],
            "total_fotos": total_fotos,
            "fotos_requeridas": MIN_FOTOS_VERIFICADO,
            "defectos": None,
        }

    criterios = [
        {"clave": clave, "texto": texto, "esencial": esencial, "cumple": bool(checklist.get(clave))}
        for clave, (_, texto, esencial) in CRITERIOS.items()
    ]

    faltantes = [
        f"No cumple: {c['texto'].lower()}." for c in criterios if c["esencial"] and not c["cumple"]
    ]

    if total_fotos < MIN_FOTOS_VERIFICADO:
        faltantes.append(f"Tiene {total_fotos} de {MIN_FOTOS_VERIFICADO} fotos mínimas.")

    defectos = (defectos or "").strip()
    if not defectos:
        faltantes.append("No se describieron los defectos o el desgaste.")

    # 50 puntos por criterios (esenciales pesan el doble), 30 por condición,
    # 20 por fotos (proporcional hasta el mínimo).
    pesos = [2 if c["esencial"] else 1 for c in criterios]
    logrados = sum(p for p, c in zip(pesos, criterios) if c["cumple"])
    puntaje = round(50 * logrados / sum(pesos))
    puntaje += PUNTOS_CONDICION.get(condicion, 0)
    puntaje += round(20 * min(total_fotos, MIN_FOTOS_VERIFICADO) / MIN_FOTOS_VERIFICADO)

    return {
        "nivel": "VERIFICADO" if not faltantes else "PARCIAL",
        "puntaje": min(puntaje, 100),
        "faltantes": faltantes,
        "criterios": criterios,
        "total_fotos": total_fotos,
        "fotos_requeridas": MIN_FOTOS_VERIFICADO,
        "defectos": defectos or None,
        "sin_defectos": defectos.lower().rstrip(".") in SIN_DEFECTOS,
    }


def guardar_verificacion(cursor, id_producto: int, checklist: dict, defectos: str):
    """Inserta o actualiza el checklist del producto (dentro de la transacción del llamador)."""
    columnas = [col for col, _, _ in CRITERIOS.values()]
    valores = [1 if checklist.get(clave) else 0 for clave in CRITERIOS]

    asignaciones = ", ".join(f"{c} = ?" for c in columnas)

    cursor.execute(
        f"""
        UPDATE VerificacionProductos
        SET {asignaciones}, DescripcionDefectos = ?, FechaActualizacion = SYSDATETIME()
        WHERE IdProducto = ?;
        """,
        (*valores, defectos, id_producto),
    )

    if cursor.rowcount == 0:
        cursor.execute(
            f"""
            INSERT INTO VerificacionProductos (IdProducto, {", ".join(columnas)}, DescripcionDefectos)
            VALUES (?, {", ".join("?" for _ in columnas)}, ?);
            """,
            (id_producto, *valores, defectos),
        )


def obtener_verificacion(cursor, id_producto: int, total_fotos: int, condicion: str):
    columnas = ", ".join(col for col, _, _ in CRITERIOS.values())

    cursor.execute(
        f"""
        SELECT {columnas}, DescripcionDefectos
        FROM VerificacionProductos
        WHERE IdProducto = ?;
        """,
        (id_producto,),
    )

    fila = cursor.fetchone()

    if fila is None:
        return evaluar_verificacion(None, total_fotos, condicion, None)

    checklist = {clave: bool(getattr(fila, col)) for clave, (col, _, _) in CRITERIOS.items()}

    return evaluar_verificacion(checklist, total_fotos, condicion, fila.DescripcionDefectos)


# Fragmento SQL para listados: nivel de verificación calculado en la BD
SQL_NIVEL_VERIFICACION = f"""
    CASE
        WHEN VP.IdProducto IS NULL THEN 'SIN_VERIFICAR'
        WHEN VP.Enciende = 1 AND VP.PantallaSinDanos = 1 AND VP.BateriaOk = 1
             AND LEN(LTRIM(RTRIM(VP.DescripcionDefectos))) > 0
             AND (SELECT COUNT(*) FROM ImagenesProducto IV
                  WHERE IV.IdProducto = P.IdProducto) >= {MIN_FOTOS_VERIFICADO}
            THEN 'VERIFICADO'
        ELSE 'PARCIAL'
    END
"""
