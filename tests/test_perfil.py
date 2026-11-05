"""Pruebas de registro con fecha de nacimiento y género, y edición del perfil."""

from datetime import date

import app.routes.mis_productos as rutas_mis_productos
import app.routes.usuarios as rutas_usuarios
from app.services.usuarios import InvalidCredentials


def _registro(**cambios):
    datos = {
        "nombre": "Sergio",
        "apellido": "Martínez",
        "correo": "sergio@correo.com",
        "contrasena": "Clave12345",
        "fecha_nacimiento": "1992-03-15",
        "genero": "MASCULINO"
    }
    datos.update(cambios)
    return datos


def test_registro_envia_fecha_y_genero(client, monkeypatch):
    recibido = {}
    monkeypatch.setattr(
        rutas_usuarios, "registrar_usuario",
        lambda **kw: recibido.update(kw) or 10
    )

    respuesta = client.post("/usuarios/registro", json=_registro())

    assert respuesta.status_code == 201
    assert recibido["fecha_nacimiento"] == date(1992, 3, 15)
    assert recibido["genero"] == "MASCULINO"


def test_registro_menor_de_edad(client):
    hace_diez_anios = date.today().replace(year=date.today().year - 10)
    respuesta = client.post(
        "/usuarios/registro", json=_registro(fecha_nacimiento=hace_diez_anios.isoformat())
    )
    assert respuesta.status_code == 422


def test_registro_fecha_futura(client):
    respuesta = client.post("/usuarios/registro", json=_registro(fecha_nacimiento="2999-01-01"))
    assert respuesta.status_code == 422


def test_registro_genero_invalido(client):
    respuesta = client.post("/usuarios/registro", json=_registro(genero="X"))
    assert respuesta.status_code == 422


def test_registro_celular_invalido(client):
    respuesta = client.post("/usuarios/registro", json=_registro(telefono="abc"))
    assert respuesta.status_code == 422


def test_editar_perfil(client, auth, monkeypatch):
    recibido = {}

    def falso(**kw):
        recibido.update(kw)
        return {"nombre": kw["nombre"], "apellido": kw["apellido"]}

    monkeypatch.setattr(rutas_usuarios, "actualizar_perfil", falso)

    respuesta = client.put(
        "/usuarios/me",
        json={"nombre": "  Sergio Andrés ", "apellido": "Martínez", "telefono": "", "genero": ""},
        headers=auth
    )

    assert respuesta.status_code == 200
    assert recibido["id_usuario"] == 7
    assert recibido["nombre"] == "Sergio Andrés"
    assert recibido["telefono"] is None
    assert recibido["genero"] is None


def test_cambiar_contrasena_igual(client, auth):
    respuesta = client.put(
        "/usuarios/me/contrasena",
        json={"contrasena_actual": "Clave12345", "contrasena_nueva": "Clave12345"},
        headers=auth
    )
    assert respuesta.status_code == 422


def test_cambiar_contrasena_actual_incorrecta(client, auth, monkeypatch):
    def falso(*_):
        raise InvalidCredentials()

    monkeypatch.setattr(rutas_usuarios, "cambiar_contrasena", falso)

    respuesta = client.put(
        "/usuarios/me/contrasena",
        json={"contrasena_actual": "otra", "contrasena_nueva": "Nueva12345"},
        headers=auth
    )

    # 400 y no 401, para que la interfaz no cierre la sesión
    assert respuesta.status_code == 400


def test_mis_productos_requiere_sesion(client):
    assert client.get("/mis-productos/").status_code in (401, 403)


def test_mis_productos_del_usuario_del_token(client, auth, monkeypatch):
    monkeypatch.setattr(
        rutas_mis_productos, "listar_productos_vendedor",
        lambda id_vendedor: [{"id_producto": 1, "id_vendedor": id_vendedor}]
    )

    respuesta = client.get("/mis-productos/", headers=auth)

    assert respuesta.status_code == 200
    assert respuesta.json()["productos"][0]["id_vendedor"] == 7


def test_raiz_abre_la_tienda(client):
    respuesta = client.get("/", follow_redirects=False)
    assert respuesta.status_code in (302, 307)
    assert respuesta.headers["location"] == "/web/"


def test_interfaz_se_sirve(client):
    respuesta = client.get("/web/")
    assert respuesta.status_code == 200
    assert "Productos destacados" in respuesta.text
