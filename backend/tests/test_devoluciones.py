"""Devoluciones después de la entrega."""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

import app.routes.devoluciones as rutas
from app.errores import ReturnConflict, ReturnForbidden
from app.services.devoluciones import calcular_lineas_devolucion
from app.services.devoluciones_plazo import DIAS_PLAZO, dias_restantes

LINEAS = [
    {"id_detalle_pedido": 1, "id_producto": 10, "nombre": "Celular", "disponible": 2, "precio": Decimal("500000")},
    {"id_detalle_pedido": 2, "id_producto": 11, "nombre": "Cargador", "disponible": 0, "precio": Decimal("40000")},
]
SOLICITUD = {"id_venta": 3, "motivo": "DEFECTUOSO", "descripcion": "La pantalla parpadea al encenderla."}


def test_plazo_de_devolucion():
    ahora = datetime(2026, 11, 19, 12)
    assert dias_restantes(ahora - timedelta(days=1), ahora) == DIAS_PLAZO - 1
    assert dias_restantes(ahora - timedelta(days=DIAS_PLAZO + 2), ahora) == 0
    assert dias_restantes(None, ahora) == 0


def test_devolver_toda_la_compra():
    elegidas, monto = calcular_lineas_devolucion(LINEAS, None)
    assert [(l["id_producto"], c) for l, c in elegidas] == [(10, 2)]
    assert monto == Decimal("1000000.00")


def test_devolucion_parcial():
    elegidas, monto = calcular_lineas_devolucion(LINEAS, {10: 1})
    assert elegidas[0][1] == 1 and monto == Decimal("500000.00")


@pytest.mark.parametrize("solicitados", [{10: 3}, {11: 1}, {99: 1}])
def test_no_se_devuelve_mas_de_lo_disponible(solicitados):
    with pytest.raises(ReturnConflict):
        calcular_lineas_devolucion(LINEAS, solicitados)


def test_sin_unidades_disponibles():
    with pytest.raises(ReturnConflict):
        calcular_lineas_devolucion([{**LINEAS[0], "disponible": 0}], None)


def test_solicitar_requiere_sesion(client):
    assert client.post("/devoluciones/", json=SOLICITUD).status_code in (401, 403)


@pytest.mark.parametrize("cambio", [
    {"motivo": "PORQUE_SI"},
    {"descripcion": "corta"},
    {"productos": [{"id_producto": 1}, {"id_producto": 1, "cantidad": 1}]},
    {"productos": [{"id_producto": 1, "cantidad": 0}]},
])
def test_validaciones_de_la_solicitud(client, auth, cambio):
    assert client.post("/devoluciones/", headers=auth, json={**SOLICITUD, **cambio}).status_code == 422


def test_solicitar_envia_los_productos(client, auth, monkeypatch):
    recibido = {}
    monkeypatch.setattr(rutas, "solicitar_devolucion", lambda *a: recibido.setdefault("a", a) and {"id_devolucion": 1})
    r = client.post("/devoluciones/", headers=auth, json={**SOLICITUD, "descripcion": "  La pantalla parpadea mucho.  ",
                                                          "productos": [{"id_producto": 10, "cantidad": 1}]})
    assert r.status_code == 201
    assert recibido["a"] == (7, 3, "DEFECTUOSO", "La pantalla parpadea mucho.", {10: 1})


def test_rechazo_exige_motivo(client, auth):
    assert client.post("/devoluciones/4/rechazar", headers=auth, json={"observacion": ""}).status_code == 422


def test_recibir_exige_decidir_el_inventario(client, auth):
    assert client.post("/devoluciones/4/recibir", headers=auth, json={}).status_code == 422


def test_errores_de_negocio(client, auth, monkeypatch):
    for error, codigo in [(ReturnForbidden("x"), 403), (ReturnConflict("x"), 409)]:
        def falso(*a, e=error):
            raise e
        monkeypatch.setattr(rutas, "responder_devolucion", falso)
        assert client.post("/devoluciones/4/aprobar", headers=auth, json={}).status_code == codigo
