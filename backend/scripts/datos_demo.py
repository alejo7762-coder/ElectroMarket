"""
Carga datos de demostración usando la propia API (con todas sus validaciones).

Crea una vendedora con productos publicados (checklist y 3 fotos cada uno)
y un comprador con una dirección. Escribe en la base configurada en .env.

Uso, desde backend/:
    python -m scripts.datos_demo
"""

import base64
import uuid

from fastapi.testclient import TestClient

from app.main import app

CONTRASENA = "Demo12345"
FOTO = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

PRODUCTOS = [
    ("iPhone 12 128 GB", 1850000, 3, "BUENO", True, "Rayón leve en la esquina superior. Batería al 86 %."),
    ("Televisor Samsung 50 pulgadas", 1400000, 1, "COMO_NUEVO", True, "Ninguno"),
    ("Nevera LG 300 L", 950000, 2, "ACEPTABLE", False, "Golpe en la puerta; enfría correctamente."),
]


def _ok(respuesta, codigo=200):
    if respuesta.status_code != codigo:
        raise SystemExit(f"{respuesta.request.method} {respuesta.request.url} -> {respuesta.status_code}: {respuesta.text}")
    return respuesta.json()


def _usuario(cliente, nombre, apellido, sufijo):
    correo = f"{nombre.lower()}.{sufijo}@demo.electromarket.com"
    _ok(cliente.post("/usuarios/registro", json={
        "nombre": nombre, "apellido": apellido, "correo": correo, "contrasena": CONTRASENA
    }), 201)
    token = _ok(cliente.post("/usuarios/login", json={"correo": correo, "contrasena": CONTRASENA}))["access_token"]
    return correo, {"Authorization": f"Bearer {token}"}


def main():
    cliente = TestClient(app)
    sufijo = uuid.uuid4().hex[:6]

    id_categoria = _ok(cliente.get("/categorias/"))[0]["id_categoria"]
    correo_vendedora, vendedora = _usuario(cliente, "Ana", "Vendedora", sufijo)
    correo_comprador, comprador = _usuario(cliente, "Luis", "Comprador", sufijo)

    for nombre, precio, stock, condicion, con_fotos, defectos in PRODUCTOS:
        id_producto = _ok(cliente.post("/productos/publicar", headers=vendedora, json={
            "id_categoria": id_categoria, "nombre": nombre,
            "descripcion": f"{nombre} usado en buen funcionamiento.",
            "precio": precio, "stock": stock, "condicion": condicion,
            "checklist": {"enciende": True, "pantalla_sin_danos": condicion != "ACEPTABLE",
                          "bateria_ok": True, "accesorios_completos": condicion == "COMO_NUEVO"},
            "descripcion_defectos": defectos
        }), 201)["id_producto"]

        for i in range(3 if con_fotos else 1):
            _ok(cliente.post(f"/productos/{id_producto}/imagenes", headers=vendedora,
                             files={"archivo": (f"foto{i}.png", FOTO, "image/png")}), 201)

    _ok(cliente.post("/direcciones/", headers=comprador, json={
        "direccion": "Calle 10 # 5-20", "ciudad": "Bogotá",
        "departamento": "Cundinamarca", "codigo_postal": "110111"
    }), 201)

    print("Datos de demostración creados.")
    print(f"  Vendedora: {correo_vendedora} / {CONTRASENA}")
    print(f"  Comprador: {correo_comprador} / {CONTRASENA}")


if __name__ == "__main__":
    main()
