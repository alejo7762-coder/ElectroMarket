import app.routes.reembolsos as rutas_reembolsos
import app.routes.productos as rutas_productos
from app.services.reembolsos import estado_reembolso_pago, referencia_reembolso
from app.services.verificacion import evaluar_verificacion, MIN_FOTOS_VERIFICADO


CHECK_OK = {"enciende": True, "pantalla_sin_danos": True, "bateria_ok": True}


# ---------------- Reembolsos ----------------

def test_estado_reembolso_pago():
    assert estado_reembolso_pago(100.0, 0) == "SIN_REEMBOLSO"
    assert estado_reembolso_pago(100.0, 40.0) == "REEMBOLSO_PARCIAL"
    assert estado_reembolso_pago(100.0, 100.0) == "REEMBOLSADO"


def test_referencia_reembolso():
    assert referencia_reembolso(42) == "RMB-00000042"


def test_reembolsos_requiere_sesion(client):
    assert client.get("/reembolsos/").status_code in (401, 403)


def test_reembolsos_totales(client, auth, monkeypatch):
    def falso(id_usuario, id_pedido):
        assert id_usuario == 7 and id_pedido == 3
        return [
            {"valor": 50.0, "estado": "PROCESADO"},
            {"valor": 20.0, "estado": "PENDIENTE"},
        ]

    monkeypatch.setattr(rutas_reembolsos, "listar_reembolsos", falso)
    datos = client.get("/reembolsos/?id_pedido=3", headers=auth).json()

    assert datos["total"] == 2
    assert datos["total_reembolsado"] == 50.0
    assert datos["total_pendiente"] == 20.0


def test_reembolso_inexistente_404(client, auth, monkeypatch):
    def falso(id_usuario, id_reembolso):
        raise rutas_reembolsos.RefundNotFound("Reembolso no encontrado.")

    monkeypatch.setattr(rutas_reembolsos, "obtener_reembolso", falso)
    assert client.get("/reembolsos/9", headers=auth).status_code == 404


# ---------------- Verificación ----------------

def test_sin_checklist_sin_verificar():
    r = evaluar_verificacion(None, 5, "COMO_NUEVO", None)
    assert r["nivel"] == "SIN_VERIFICAR" and r["puntaje"] == 0


def test_verificado_completo():
    r = evaluar_verificacion(CHECK_OK, MIN_FOTOS_VERIFICADO, "BUENO", "Ninguno")
    assert r["nivel"] == "VERIFICADO"
    assert r["faltantes"] == []
    assert r["sin_defectos"] is True


def test_parcial_por_fotos_insuficientes():
    r = evaluar_verificacion(CHECK_OK, 1, "BUENO", "Rayón leve")
    assert r["nivel"] == "PARCIAL"
    assert any("fotos" in f for f in r["faltantes"])


def test_parcial_por_criterio_esencial():
    r = evaluar_verificacion({**CHECK_OK, "bateria_ok": False}, 5, "BUENO", "Batería al 70 %")
    assert r["nivel"] == "PARCIAL"


def test_puntaje_maximo():
    todo = {**CHECK_OK, "sin_reparaciones": True, "accesorios_completos": True, "con_garantia": True}
    assert evaluar_verificacion(todo, 5, "COMO_NUEVO", "Ninguno")["puntaje"] == 100


PRODUCTO = {
    "id_categoria": 1, "nombre": "Celular", "descripcion": "Usado",
    "precio": 100, "stock": 1, "condicion": "BUENO",
}


def test_publicar_exige_checklist_y_defectos(client, auth):
    assert client.post("/productos/publicar", headers=auth, json=PRODUCTO).status_code == 422


def test_publicar_envia_checklist(client, auth, monkeypatch):
    recibido = {}

    def falso(**kwargs):
        recibido.update(kwargs)
        return 11

    monkeypatch.setattr(rutas_productos, "publicar_producto", falso)
    r = client.post("/productos/publicar", headers=auth, json={
        **PRODUCTO, "checklist": CHECK_OK, "descripcion_defectos": "  Ninguno "
    })

    assert r.status_code == 201
    assert recibido["checklist"]["enciende"] is True
    assert recibido["checklist"]["con_garantia"] is False
    assert recibido["defectos"] == "Ninguno"


# ---------------- Tipo de solicitud (CK_Solicitudes_Tipo) ----------------

def test_tipo_bd_respeta_restriccion_del_esquema():
    from app.services.cancelaciones import _tipo_bd

    # Con IdVenta la BD solo acepta PARCIAL; sin IdVenta, TOTAL
    assert _tipo_bd("TOTAL", 5) == "PARCIAL"
    assert _tipo_bd("PARCIAL", 5) == "PARCIAL"
    assert _tipo_bd("TOTAL", None) == "TOTAL"
