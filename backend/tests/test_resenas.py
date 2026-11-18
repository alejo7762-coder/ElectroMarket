"""Reseñas, calificaciones y fiabilidad del vendedor."""
import app.routes.resenas as rutas
from app.errores import ReviewConflict, ReviewForbidden
from app.services.resenas import nombre_publico, resumen_calificaciones
from app.services.vendedores import calcular_fiabilidad

RESENA = {"id_venta": 3, "id_producto": 5, "calificacion_producto": 5, "calificacion_vendedor": 4,
          "comentario": "  Llegó bien  "}


def test_resumen_de_calificaciones():
    r = resumen_calificaciones([5, 4, 5, 3])
    assert r["promedio"] == 4.25 and r["total"] == 4
    assert r["distribucion"] == {5: 2, 4: 1, 3: 1, 2: 0, 1: 0}
    assert resumen_calificaciones([])["promedio"] is None


def test_nombre_publico_del_comprador():
    assert nombre_publico("Luis", "Comprador") == "Luis C."
    assert nombre_publico("Ana", "") == "Ana"


def test_vendedor_nuevo_sin_historial():
    f = calcular_fiabilidad([], 0, 0, 0, 0, 0, 0)
    assert f["nivel"] == "NUEVO"
    assert {x["factor"] for x in f["factores"]} == {"Calificación", "Experiencia", "Cumplimiento", "Verificación", "Antigüedad"}


def test_vendedor_confiable():
    f = calcular_fiabilidad([5] * 20, 25, 22, 0, 4, 4, 14)
    assert f["nivel"] == "ALTA" and f["indice"] >= 80
    assert all(x["puntos"] <= x["maximo"] for x in f["factores"])


def test_una_sola_resena_no_define_la_fiabilidad():
    una_mala = calcular_fiabilidad([1], 1, 1, 0, 1, 1, 6)
    una_buena = calcular_fiabilidad([5], 1, 1, 0, 1, 1, 6)
    calificacion = lambda f: next(x["puntos"] for x in f["factores"] if x["factor"] == "Calificación")
    assert 10 < calificacion(una_mala) < calificacion(una_buena) < 35   # promedio bayesiano


def test_cancelar_ventas_baja_la_fiabilidad():
    cumple = calcular_fiabilidad([4, 5], 10, 8, 0, 2, 1, 6)["indice"]
    cancela = calcular_fiabilidad([4, 5], 10, 5, 5, 2, 1, 6)["indice"]
    assert cancela < cumple


def test_publicar_resena_requiere_sesion(client):
    assert client.post("/resenas/", json=RESENA).status_code in (401, 403)


def test_estrellas_entre_1_y_5(client, auth):
    assert client.post("/resenas/", headers=auth, json={**RESENA, "calificacion_producto": 6}).status_code == 422
    assert client.post("/resenas/", headers=auth, json={**RESENA, "calificacion_vendedor": 0}).status_code == 422


def test_publicar_resena(client, auth, monkeypatch):
    recibido = {}

    def falso(*args):
        recibido["args"] = args
        return {"id_resena": 1}

    monkeypatch.setattr(rutas, "crear_resena", falso)
    r = client.post("/resenas/", headers=auth, json=RESENA)

    assert r.status_code == 201
    assert recibido["args"] == (7, 3, 5, 5, 4, "Llegó bien")


def test_errores_de_negocio(client, auth, monkeypatch):
    for error, codigo in [(ReviewForbidden("x"), 403), (ReviewConflict("x"), 409)]:
        def falso(*args, e=error):
            raise e
        monkeypatch.setattr(rutas, "crear_resena", falso)
        assert client.post("/resenas/", headers=auth, json=RESENA).status_code == codigo


def test_perfil_vendedor_publico(client, monkeypatch):
    monkeypatch.setattr(rutas, "perfil_vendedor", lambda id_vendedor: {"id_vendedor": id_vendedor})
    assert client.get("/vendedores/9").json() == {"id_vendedor": 9}
