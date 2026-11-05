"""
Pruebas de las rutas: autenticación, validación de datos y
traducción de errores a códigos HTTP. Los servicios se simulan.
"""

import app.routes.cancelaciones as rutas_cancelaciones
import app.routes.direcciones as rutas_direcciones
import app.routes.pedidos as rutas_pedidos
import app.routes.ventas as rutas_ventas
from app.services.cancelaciones import CancellationConflict, OrderNotFound
from app.services.direcciones import AddressInUse
from app.services.pedidos import EmptyCart, PurchaseValidationError


# ---------------------------------------------------------------- seguridad

def test_rutas_protegidas_sin_token(client):
    for metodo, ruta in [
        ("get", "/pedidos/"),
        ("get", "/ventas/"),
        ("get", "/pagos/"),
        ("get", "/direcciones/"),
        ("get", "/cancelaciones/"),
        ("post", "/pedidos/comprar"),
    ]:
        respuesta = getattr(client, metodo)(ruta)
        assert respuesta.status_code in (401, 403), ruta


def test_token_invalido(client):
    respuesta = client.get(
        "/pedidos/", headers={"Authorization": "Bearer token-falso"}
    )
    assert respuesta.status_code == 401


# ---------------------------------------------------------------- compras

def test_compra_con_tarjeta_requiere_numero(client, auth):
    respuesta = client.post(
        "/pedidos/comprar",
        json={"id_direccion": 1, "metodo_pago": "TARJETA_SIMULADA"},
        headers=auth
    )
    assert respuesta.status_code == 422


def test_compra_metodo_invalido(client, auth):
    respuesta = client.post(
        "/pedidos/comprar",
        json={"id_direccion": 1, "metodo_pago": "EFECTIVO"},
        headers=auth
    )
    assert respuesta.status_code == 422


def test_compra_carrito_vacio(client, auth, monkeypatch):
    def falso(**_):
        raise EmptyCart("El carrito está vacío.")

    monkeypatch.setattr(rutas_pedidos, "procesar_compra", falso)

    respuesta = client.post(
        "/pedidos/comprar", json={"id_direccion": 1}, headers=auth
    )
    assert respuesta.status_code == 400


def test_compra_stock_insuficiente(client, auth, monkeypatch):
    def falso(**_):
        raise PurchaseValidationError([{"id_producto": 1, "motivo": "Stock"}])

    monkeypatch.setattr(rutas_pedidos, "procesar_compra", falso)

    respuesta = client.post(
        "/pedidos/comprar", json={"id_direccion": 1}, headers=auth
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["productos"][0]["id_producto"] == 1


def test_pago_rechazado_responde_402(client, auth, monkeypatch):
    monkeypatch.setattr(
        rutas_pedidos, "procesar_compra",
        lambda **_: {"pago": {"estado": "RECHAZADO"}, "estado_pedido": "CANCELADO"}
    )

    respuesta = client.post(
        "/pedidos/comprar",
        json={
            "id_direccion": 1,
            "metodo_pago": "TARJETA_SIMULADA",
            "numero_tarjeta": "4111111111110000"
        },
        headers=auth
    )
    assert respuesta.status_code == 402


def test_mis_pedidos_usa_el_usuario_del_token(client, auth, monkeypatch):
    llamadas = {}

    def falso(id_usuario, estado):
        llamadas["id_usuario"] = id_usuario
        llamadas["estado"] = estado
        return []

    monkeypatch.setattr(rutas_pedidos, "listar_pedidos", falso)

    respuesta = client.get("/pedidos/?estado=pagado", headers=auth)

    assert respuesta.status_code == 200
    assert llamadas == {"id_usuario": 7, "estado": "PAGADO"}


def test_mis_pedidos_estado_invalido(client, auth):
    respuesta = client.get("/pedidos/?estado=PERDIDO", headers=auth)
    assert respuesta.status_code == 422


# ---------------------------------------------------------------- ventas

def test_resumen_no_se_confunde_con_id(client, auth, monkeypatch):
    monkeypatch.setattr(rutas_ventas, "resumen_ventas", lambda _id: {"ok": True})

    respuesta = client.get("/ventas/resumen", headers=auth)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True}


# ---------------------------------------------------------------- direcciones

def test_direccion_con_espacios_es_invalida(client, auth):
    respuesta = client.post(
        "/direcciones/",
        json={"direccion": "     ", "ciudad": "Bogotá", "departamento": "Cundinamarca"},
        headers=auth
    )
    assert respuesta.status_code == 422


def test_direccion_en_uso_responde_409(client, auth, monkeypatch):
    def falso(*_):
        raise AddressInUse("En uso")

    monkeypatch.setattr(rutas_direcciones, "eliminar_direccion", falso)

    respuesta = client.delete("/direcciones/3", headers=auth)
    assert respuesta.status_code == 409


# ---------------------------------------------------------------- cancelaciones

def test_cancelacion_parcial_valida_productos(client, auth):
    respuesta = client.post(
        "/cancelaciones/pedidos/1/parcial",
        json={"motivo": "Ya no lo necesito", "productos": []},
        headers=auth
    )
    assert respuesta.status_code == 422


def test_cancelacion_parcial_no_admite_repetidos(client, auth):
    respuesta = client.post(
        "/cancelaciones/pedidos/1/parcial",
        json={
            "motivo": "Ya no lo necesito",
            "productos": [{"id_producto": 1}, {"id_producto": 1, "cantidad": 1}]
        },
        headers=auth
    )
    assert respuesta.status_code == 422


def test_cancelacion_parcial_envia_cantidades(client, auth, monkeypatch):
    recibido = {}

    def falso(id_usuario, id_pedido, motivo, productos):
        recibido.update(
            id_usuario=id_usuario, id_pedido=id_pedido, productos=productos
        )
        return {"ok": True}

    monkeypatch.setattr(rutas_cancelaciones, "cancelar_pedido_parcial", falso)

    respuesta = client.post(
        "/cancelaciones/pedidos/5/parcial",
        json={
            "motivo": "Compré de más",
            "productos": [{"id_producto": 1, "cantidad": 2}, {"id_producto": 3}]
        },
        headers=auth
    )

    assert respuesta.status_code == 201
    assert recibido == {
        "id_usuario": 7, "id_pedido": 5, "productos": {1: 2, 3: None}
    }


def test_cancelacion_motivo_obligatorio(client, auth):
    respuesta = client.post(
        "/cancelaciones/pedidos/1/total", json={"motivo": "   "}, headers=auth
    )
    assert respuesta.status_code == 422


def test_cancelacion_conflicto_responde_409(client, auth, monkeypatch):
    def falso(*_):
        raise CancellationConflict("Ya entregado")

    monkeypatch.setattr(rutas_cancelaciones, "cancelar_pedido_total", falso)

    respuesta = client.post(
        "/cancelaciones/pedidos/1/total",
        json={"motivo": "Cambié de opinión"},
        headers=auth
    )
    assert respuesta.status_code == 409


def test_cancelacion_pedido_ajeno_responde_404(client, auth, monkeypatch):
    def falso(*_):
        raise OrderNotFound("Pedido no encontrado.")

    monkeypatch.setattr(rutas_cancelaciones, "cancelar_pedido_total", falso)

    respuesta = client.post(
        "/cancelaciones/pedidos/99/total",
        json={"motivo": "Cambié de opinión"},
        headers=auth
    )
    assert respuesta.status_code == 404
