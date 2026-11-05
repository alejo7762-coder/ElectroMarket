"""
Configuración común de las pruebas.

Las pruebas unitarias NO necesitan SQL Server: los servicios se
reemplazan con monkeypatch. Las pruebas de integración están en
tests/integracion y solo se ejecutan si se define la variable
ELECTROMARKET_DB_TESTS=1.
"""

import os

# Debe existir antes de importar app.security
os.environ.setdefault("JWT_SECRET_KEY", "clave-solo-para-pruebas-electromarket-123456")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security import crear_token_acceso


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def token():
    return crear_token_acceso({"id_usuario": 7, "correo": "prueba@correo.com"})


@pytest.fixture
def auth(token):
    return {"Authorization": f"Bearer {token}"}
