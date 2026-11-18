"""Pruebas del servicio de IA de precio sugerido (red neuronal 9-6-1)."""
import pytest

from app.ia import precio


def _sugerir(**cambios):
    datos = {"categoria": "Celulares", "meses": 24, "condicion": "BUENO", "caja": True,
             "garantia": False, "precio_nuevo": 2_400_000, **cambios}
    return precio.sugerir(datos["categoria"], datos["meses"], datos["condicion"],
                          datos["caja"], datos["garantia"], datos["precio_nuevo"])


def test_arquitectura_9_6_1_con_67_parametros():
    red = precio.obtener_modelo()
    assert [w.shape for w in red.red.coefs_] == [(9, 6), (6, 1)]
    assert red.red.activation == "relu"
    assert red.parametros == 67


@pytest.mark.parametrize("categoria, grupo", [
    ("Celulares", "CELULAR"), ("Televisores", "TELEVISOR"), ("Neveras", "NEVERA"),
    ("Videojuegos", "OTRO"), ("Pequeños electrodomésticos", "OTRO"),
])
def test_agrupa_las_categorias(categoria, grupo):
    assert precio.grupo_categoria(categoria) == grupo


def test_vector_de_entrada_escalado():
    x = precio.vector_entrada("NEVERA", 240, "COMO_NUEVO", True, False, 2_000_000)
    assert len(x) == 9
    assert x[:4] == [0, 0, 1, 0]
    assert x[4] == 1.0          # antigüedad con tope de 120 meses
    assert x[5] == 1.0          # COMO_NUEVO
    assert 0 <= x[8] <= 1       # precio en escala logarítmica


def test_sugerencia_y_rango_de_10_por_ciento():
    r = _sugerir()
    assert 0 < r["proporcion"] < 1
    assert r["rango_minimo"] < r["precio_sugerido"] < r["rango_maximo"] < r["precio_nuevo"]
    assert r["rango_maximo"] == pytest.approx(r["precio_sugerido"] * 1.1, rel=0.01)
    assert {f["factor"] for f in r["factores"]} == {"Antigüedad", "Condición", "Caja y accesorios", "Garantía vigente"}


def test_comportamiento_esperado_del_mercado():
    base = _sugerir()["precio_sugerido"]
    assert _sugerir(meses=60)["precio_sugerido"] < base             # más antiguo, menos valor
    assert _sugerir(condicion="COMO_NUEVO")["precio_sugerido"] > base
    assert _sugerir(condicion="ACEPTABLE")["precio_sugerido"] < base
    assert _sugerir(caja=False)["precio_sugerido"] < base


def test_endpoint_requiere_sesion(client):
    assert client.post("/productos/precio-sugerido", json={}).status_code in (401, 403)


def test_endpoint_precio_sugerido(client, auth):
    r = client.post("/productos/precio-sugerido", headers=auth, json={
        "categoria": "Celulares", "antiguedad_meses": 24, "condicion": "BUENO",
        "incluye_caja": True, "garantia_vigente": False, "precio_nuevo": 2400000
    })
    assert r.status_code == 200
    assert r.json()["grupo_categoria"] == "CELULAR"
    assert r.json()["version_modelo"] == precio.VERSION_MODELO


def test_endpoint_valida_las_entradas(client, auth):
    r = client.post("/productos/precio-sugerido", headers=auth, json={
        "categoria": "Celulares", "antiguedad_meses": -1, "condicion": "BUENO", "precio_nuevo": 10
    })
    assert r.status_code == 422
