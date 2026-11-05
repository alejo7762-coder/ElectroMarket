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
        "condicion": "BUENO"
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
