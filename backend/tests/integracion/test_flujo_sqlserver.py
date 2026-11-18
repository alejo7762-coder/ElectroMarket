"""
Prueba de integración del flujo completo contra SQL Server real:
registro -> producto -> dirección -> carrito -> compra -> pago
-> cancelación parcial -> envío -> solicitud de cancelación -> aprobación.

IMPORTANTE: escribe datos reales en la base configurada en .env.
Úsala preferiblemente sobre una copia de la base de datos.

Ejecutar (PowerShell):
    $env:ELECTROMARKET_DB_TESTS = "1"
    $env:ELECTROMARKET_ID_CATEGORIA = "1"   # una categoría activa
    pytest tests/integracion -v
"""

import os
import uuid

import pytest
from dotenv import load_dotenv

load_dotenv()

pytestmark = pytest.mark.skipif(
    os.getenv("ELECTROMARKET_DB_TESTS") != "1",
    reason="Define ELECTROMARKET_DB_TESTS=1 para probar contra SQL Server."
)

ID_CATEGORIA = int(os.getenv("ELECTROMARKET_ID_CATEGORIA", "1"))


def _ok(respuesta, codigo=200):
    assert respuesta.status_code == codigo, (
        f"{respuesta.request.method} {respuesta.request.url} -> "
        f"{respuesta.status_code}: {respuesta.text}"
    )
    return respuesta.json()


def _crear_usuario(client, nombre):
    correo = f"{nombre}.{uuid.uuid4().hex[:8]}@pruebas.electromarket.com"

    _ok(client.post("/usuarios/registro", json={
        "nombre": nombre,
        "apellido": "Prueba",
        "correo": correo,
        "contrasena": "Prueba12345"
    }), 201)

    token = _ok(client.post("/usuarios/login", json={
        "correo": correo,
        "contrasena": "Prueba12345"
    }))["access_token"]

    return {"Authorization": f"Bearer {token}"}


def _publicar(client, vendedor, nombre, precio, stock):
    return _ok(client.post("/productos/publicar", headers=vendedor, json={
        "id_categoria": ID_CATEGORIA,
        "nombre": nombre,
        "descripcion": "Producto creado por la prueba de integración.",
        "precio": precio,
        "stock": stock,
        "condicion": "BUENO",
        "checklist": {"enciende": True, "pantalla_sin_danos": True, "bateria_ok": True},
        "descripcion_defectos": "Ninguno"
    }), 201)["id_producto"]


def _stock(client, id_producto):
    return _ok(client.get(f"/productos/{id_producto}"))["stock"]


def test_flujo_completo(client):
    vendedor = _crear_usuario(client, "Vendedor")
    comprador = _crear_usuario(client, "Comprador")

    celular = _publicar(client, vendedor, "Celular de prueba", 100000, 5)
    televisor = _publicar(client, vendedor, "Televisor de prueba", 900000, 1)

    id_direccion = _ok(client.post("/direcciones/", headers=comprador, json={
        "direccion": "Calle 10 # 20-30",
        "ciudad": "Bogotá",
        "departamento": "Cundinamarca",
        "codigo_postal": "110111"
    }), 201)["id_direccion"]

    for producto, cantidad in [(celular, 3), (televisor, 1)]:
        _ok(client.post("/carrito/agregar", headers=comprador, json={
            "id_producto": producto, "cantidad": cantidad
        }), 201)

    # Pago rechazado: el carrito se conserva y no se toca el inventario
    rechazo = _ok(client.post("/pedidos/comprar", headers=comprador, json={
        "id_direccion": id_direccion,
        "metodo_pago": "TARJETA_SIMULADA",
        "numero_tarjeta": "4111111111110000"
    }), 402)
    assert rechazo["estado_pedido"] == "CANCELADO"
    assert _stock(client, celular) == 5

    # Pago aprobado
    compra = _ok(client.post("/pedidos/comprar", headers=comprador, json={
        "id_direccion": id_direccion
    }), 201)
    id_pedido = compra["id_pedido"]
    id_venta = compra["ventas"][0]["id_venta"]
    assert compra["estado_pedido"] == "PAGADO"
    assert _stock(client, celular) == 2
    assert _stock(client, televisor) == 0

    # Cancelación parcial antes del despacho
    parcial = _ok(client.post(
        f"/cancelaciones/pedidos/{id_pedido}/parcial",
        headers=comprador,
        json={
            "motivo": "Compré unidades de más",
            "productos": [{"id_producto": celular, "cantidad": 2}]
        }
    ), 201)
    assert parcial["monto_reembolsado"] == 200000
    assert _stock(client, celular) == 4

    # Despacho
    id_envio = _ok(client.post(
        f"/envios/ventas/{id_venta}", headers=vendedor, json={}
    ), 201)["id_envio"]
    _ok(client.patch(
        f"/envios/{id_envio}/estado", headers=vendedor, json={"estado": "ENVIADO"}
    ))

    # Ya despachado: solo se puede solicitar la cancelación de la venta
    _ok(client.post(
        f"/cancelaciones/pedidos/{id_pedido}/parcial",
        headers=comprador,
        json={"motivo": "Ya no lo quiero", "productos": [{"id_producto": celular}]}
    ), 409)

    solicitud = _ok(client.post(
        f"/cancelaciones/ventas/{id_venta}",
        headers=comprador,
        json={"motivo": "Ya no necesito el pedido"}
    ), 201)
    assert solicitud["estado"] == "SOLICITADA"

    aprobada = _ok(client.post(
        f"/cancelaciones/{solicitud['id_cancelacion']}/aprobar",
        headers=vendedor,
        json={"observacion": "Se recibe la devolución del transportador."}
    ))
    assert aprobada["estado_venta"] == "CANCELADA"
    assert aprobada["estado_pedido"] == "CANCELADO"
    assert _stock(client, celular) == 5
    assert _stock(client, televisor) == 1

    detalle = _ok(client.get(f"/pedidos/{id_pedido}", headers=comprador))
    assert detalle["total_neto"] == 0
    assert len(detalle["cancelaciones"]) == 2

    seguimiento = _ok(client.get(f"/envios/{id_envio}", headers=comprador))
    assert seguimiento["estado_envio"] == "CANCELADO"

    resumen = _ok(client.get("/ventas/resumen", headers=vendedor))
    assert resumen["ingresos_netos"] == 0


def _png():
    """Imagen PNG mínima válida (1x1)."""
    import base64
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )


def _adelantar_reembolsos(id_pedido):
    """Simula que pasó el tiempo de la pasarela para los reembolsos del pedido."""
    from app.db.connection import get_connection

    conexion = get_connection()
    try:
        conexion.cursor().execute(
            """
            UPDATE R SET FechaSolicitud = DATEADD(MINUTE, -5, SYSDATETIME())
            FROM Reembolsos R INNER JOIN Pagos PG ON PG.IdPago = R.IdPago
            WHERE PG.IdPedido = ?;
            """,
            (id_pedido,)
        )
        conexion.commit()
    finally:
        conexion.close()


def test_verificacion_y_reembolsos(client):
    vendedor = _crear_usuario(client, "Vendedora")
    comprador = _crear_usuario(client, "Comprador")

    # Verificación: sin fotos queda PARCIAL; con 3 fotos, VERIFICADO
    id_producto = _publicar(client, vendedor, "Portátil de prueba", 500000, 3)
    assert _ok(client.get(f"/productos/{id_producto}"))["verificacion"]["nivel"] == "PARCIAL"

    for i in range(3):
        _ok(client.post(
            f"/productos/{id_producto}/imagenes", headers=vendedor,
            files={"archivo": (f"foto{i}.png", _png(), "image/png")}
        ), 201)

    verificacion = _ok(client.get(f"/productos/{id_producto}"))["verificacion"]
    assert verificacion["nivel"] == "VERIFICADO"
    assert verificacion["total_fotos"] == 3

    catalogo = _ok(client.get("/productos/"))["productos"]
    assert any(p["id_producto"] == id_producto and p["nivel_verificacion"] == "VERIFICADO" for p in catalogo)

    # El vendedor no puede comprar su propio producto
    _ok(client.post("/carrito/agregar", headers=vendedor, json={"id_producto": id_producto, "cantidad": 1}), 403)

    id_direccion = _ok(client.post("/direcciones/", headers=comprador, json={
        "direccion": "Carrera 7 # 45-10", "ciudad": "Medellín", "departamento": "Antioquia"
    }), 201)["id_direccion"]
    _ok(client.post("/carrito/agregar", headers=comprador, json={"id_producto": id_producto, "cantidad": 2}), 201)
    compra = _ok(client.post("/pedidos/comprar", headers=comprador, json={"id_direccion": id_direccion}), 201)
    id_pedido = compra["id_pedido"]

    # Cancelación parcial: reembolso PENDIENTE y pago todavía APROBADO
    _ok(client.post(f"/cancelaciones/pedidos/{id_pedido}/parcial", headers=comprador, json={
        "motivo": "Solo necesito una unidad", "productos": [{"id_producto": id_producto, "cantidad": 1}]
    }), 201)
    reembolsos = _ok(client.get(f"/reembolsos/?id_pedido={id_pedido}", headers=comprador))
    assert reembolsos["total_pendiente"] == 500000
    assert reembolsos["reembolsos"][0]["estado"] == "PENDIENTE"

    # La pasarela procesa el reembolso: pago REEMBOLSO_PARCIAL
    _adelantar_reembolsos(id_pedido)
    reembolsos = _ok(client.get(f"/reembolsos/?id_pedido={id_pedido}", headers=comprador))
    assert reembolsos["total_reembolsado"] == 500000
    assert reembolsos["reembolsos"][0]["referencia"].startswith("RMB-")
    pago = _ok(client.get("/pagos/", headers=comprador))[0]
    assert pago["estado"] == "REEMBOLSO_PARCIAL"

    # Cancelación del resto: la API la informa como TOTAL y el pago queda REEMBOLSADO
    total = _ok(client.post(f"/cancelaciones/pedidos/{id_pedido}/total", headers=comprador, json={
        "motivo": "Ya no necesito el portátil"
    }), 201)
    assert total["monto_reembolsado"] == 500000

    _adelantar_reembolsos(id_pedido)
    pago = _ok(client.get(f"/pagos/{pago['id_pago']}", headers=comprador))
    assert pago["estado"] == "REEMBOLSADO"
    assert pago["estado_reembolso"] == "REEMBOLSADO"
    assert pago["reembolsado"] == 1000000

    tipos = {c["tipo"] for c in _ok(client.get(f"/pedidos/{id_pedido}", headers=comprador))["cancelaciones"]}
    assert tipos == {"PARCIAL", "TOTAL"}
    assert _stock(client, id_producto) == 3


def test_inspector_ia_en_la_publicacion(client):
    vendedor = _crear_usuario(client, "VendedorIA")

    # El vendedor marca "pantalla sin daños" pero describe una pantalla rota
    id_producto = _ok(client.post("/productos/publicar", headers=vendedor, json={
        "id_categoria": ID_CATEGORIA, "nombre": "Celular con detalle",
        "descripcion": "Funciona, pero la pantalla está rota en una esquina.",
        "precio": 300000, "stock": 1, "condicion": "BUENO",
        "checklist": {"enciende": True, "pantalla_sin_danos": True, "bateria_ok": True},
        "descripcion_defectos": "Pantalla rota"
    }), 201)["id_producto"]

    for i in range(3):
        _ok(client.post(f"/productos/{id_producto}/imagenes", headers=vendedor,
                        files={"archivo": (f"f{i}.png", _png(), "image/png")}), 201)

    producto = _ok(client.get(f"/productos/{id_producto}"))
    assert producto["inspeccion_ia"]["coherencia"] == "REVISAR"
    assert producto["verificacion"]["nivel"] == "PARCIAL"  # la IA impide VERIFICADO
    mis = _ok(client.get("/mis-productos/", headers=vendedor))["productos"]
    assert mis[0]["coherencia_ia"] == "REVISAR" and mis[0]["nivel_verificacion"] == "PARCIAL"

    # Corrige la publicación de forma coherente: queda VERIFICADO
    _ok(client.put(f"/productos/{id_producto}", headers=vendedor, json={
        "id_categoria": ID_CATEGORIA, "nombre": "Celular con detalle",
        "descripcion": "Funciona, pero la pantalla está rota en una esquina.",
        "precio": 250000, "stock": 1, "condicion": "ACEPTABLE",
        "checklist": {"enciende": True, "pantalla_sin_danos": False, "bateria_ok": True},
        "descripcion_defectos": "Pantalla rota"
    }))
    producto = _ok(client.get(f"/productos/{id_producto}"))
    assert producto["inspeccion_ia"]["coherencia"] == "COHERENTE"
    assert producto["inspeccion_ia"]["condicion_sugerida"] == "ACEPTABLE"


def test_resenas_y_fiabilidad(client):
    vendedor = _crear_usuario(client, "VendedorResenas")
    comprador = _crear_usuario(client, "CompradorResenas")
    otro = _crear_usuario(client, "Curioso")

    id_producto = _publicar(client, vendedor, "Parlante para reseñar", 150000, 3)
    id_vendedor = _ok(client.get(f"/productos/{id_producto}"))["id_vendedor"]
    assert _ok(client.get(f"/vendedores/{id_vendedor}"))["fiabilidad"]["nivel"] == "NUEVO"

    id_direccion = _ok(client.post("/direcciones/", headers=comprador, json={
        "direccion": "Calle 50 # 10-20", "ciudad": "Cali", "departamento": "Valle del Cauca"
    }), 201)["id_direccion"]
    _ok(client.post("/carrito/agregar", headers=comprador, json={"id_producto": id_producto, "cantidad": 1}), 201)
    compra = _ok(client.post("/pedidos/comprar", headers=comprador, json={"id_direccion": id_direccion}), 201)
    id_venta = compra["ventas"][0]["id_venta"]
    resena = {"id_venta": id_venta, "id_producto": id_producto, "calificacion_producto": 5,
              "calificacion_vendedor": 4, "comentario": "Suena muy bien"}

    # Antes de la entrega no se puede reseñar
    _ok(client.post("/resenas/", headers=comprador, json=resena), 409)

    id_envio = _ok(client.post(f"/envios/ventas/{id_venta}", headers=vendedor, json={}), 201)["id_envio"]
    for estado in ("ENVIADO", "EN_TRANSITO", "ENTREGADO"):
        _ok(client.patch(f"/envios/{id_envio}/estado", headers=vendedor, json={"estado": estado}))

    _ok(client.post("/resenas/", headers=otro, json=resena), 403)          # no es el comprador
    creada = _ok(client.post("/resenas/", headers=comprador, json=resena), 201)
    assert creada["comprador"].endswith("P.")                             # nombre abreviado
    _ok(client.post("/resenas/", headers=comprador, json=resena), 409)     # una por producto

    _ok(client.put(f"/resenas/{creada['id_resena']}", headers=comprador, json={
        "calificacion_producto": 4, "calificacion_vendedor": 5, "comentario": "Actualizo: excelente vendedor"
    }))
    _ok(client.put(f"/resenas/{creada['id_resena']}", headers=otro, json={
        "calificacion_producto": 1, "calificacion_vendedor": 1
    }), 403)

    del_producto = _ok(client.get(f"/productos/{id_producto}/resenas"))
    assert del_producto["promedio"] == 4 and del_producto["total"] == 1
    assert del_producto["resenas"][0]["editada"] is True
    assert _ok(client.get(f"/productos/{id_producto}"))["calificacion"]["total"] == 1

    perfil = _ok(client.get(f"/vendedores/{id_vendedor}"))
    assert perfil["ventas_entregadas"] == 1
    assert perfil["calificacion_vendedor"]["promedio"] == 5
    assert perfil["fiabilidad"]["nivel"] != "NUEVO"
    assert len(_ok(client.get("/resenas/mias", headers=comprador))) == 1
