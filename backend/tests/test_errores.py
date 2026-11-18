"""Manejo global de errores y validaciones alineadas con la base de datos."""
from fastapi.testclient import TestClient

import app.routes.pagos as rutas_pagos
import app.routes.productos as rutas_productos
from app.errores import Conflicto, NoEncontrado, PaymentNotFound, ProductDeleted
from app.main import app


def test_error_de_negocio_usa_su_codigo(client, auth, monkeypatch):
    def falso(id_usuario, id_pago):
        raise PaymentNotFound("Pago no encontrado.")

    monkeypatch.setattr(rutas_pagos, "obtener_pago", falso)
    r = client.get("/pagos/3", headers=auth)

    assert r.status_code == 404
    assert r.json() == {"detail": "Pago no encontrado."}


def test_categorias_de_error():
    assert issubclass(PaymentNotFound, NoEncontrado)
    assert issubclass(ProductDeleted, Conflicto)


def test_error_inesperado_no_expone_detalles(auth, monkeypatch):
    def falso(id_usuario):
        raise RuntimeError("cadena de conexión secreta")

    monkeypatch.setattr(rutas_pagos, "listar_pagos", falso)
    r = TestClient(app, raise_server_exceptions=False).get("/pagos/", headers=auth)

    assert r.status_code == 500
    assert "secreta" not in r.text


def test_producto_inexistente_404(client, monkeypatch):
    monkeypatch.setattr(rutas_productos, "obtener_producto", lambda id_producto: None)
    assert client.get("/productos/99").status_code == 404


def test_ids_deben_ser_positivos(client):
    assert client.get("/productos/0").status_code == 422
    assert client.get("/productos/?id_categoria=-1").status_code == 422


def test_direccion_respeta_tamano_de_columnas(client, auth):
    base = {"direccion": "Calle 10 # 5-20", "ciudad": "Bogotá", "departamento": "Cundinamarca"}

    largo = client.post("/direcciones/", headers=auth, json={**base, "codigo_postal": "1" * 16})
    assert largo.status_code == 422


def test_cantidad_del_carrito_tiene_tope(client, auth):
    r = client.post("/carrito/agregar", headers=auth, json={"id_producto": 1, "cantidad": 1000})
    assert r.status_code == 422


def test_precio_maximo_dos_decimales(client, auth):
    r = client.post("/productos/publicar", headers=auth, json={
        "id_categoria": 1, "nombre": "Celular", "descripcion": "Usado",
        "precio": "10.999", "stock": 1, "condicion": "BUENO",
        "checklist": {"enciende": True, "pantalla_sin_danos": True, "bateria_ok": True},
        "descripcion_defectos": "Ninguno"
    })
    assert r.status_code == 422
