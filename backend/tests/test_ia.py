"""Pruebas del servicio de IA: inspector de estado."""
import pytest

from app.ia import inspector
from app.services import inspeccion_ia
from app.services.verificacion import evaluar_verificacion

CHECK_OK = {"enciende": True, "pantalla_sin_danos": True, "bateria_ok": True}


@pytest.mark.parametrize("texto, esperada", [
    ("Celular nuevo en su caja original, sin uso, con factura y garantía.", "COMO_NUEVO"),
    ("Portátil con un año de uso, funciona bien, rayones leves en la tapa.", "BUENO"),
    ("Televisor con la pantalla rota y líneas en la imagen, se apaga solo.", "ACEPTABLE"),
])
def test_clasifica_la_condicion(texto, esperada):
    r = inspector.analizar(None, texto, None, None, None)
    assert r["condicion_sugerida"] == esperada
    assert 0 < r["confianza"] <= 1
    assert abs(sum(r["probabilidades"].values()) - 1) < 0.01


def test_detecta_contradiccion_con_el_checklist():
    r = inspector.analizar("Celular", "Funciona, pero la pantalla está rota en una esquina.", None, CHECK_OK, "BUENO")
    assert r["coherencia"] == "REVISAR"
    assert any("Pantalla o carcasa sin daños" in a for a in r["alertas"])


def test_cita_el_texto_original_con_tildes():
    r = inspector.analizar(None, "La batería dura poco.", None, CHECK_OK, None)
    assert any("«batería dura poco»" in a for a in r["alertas"])


def test_respeta_las_negaciones():
    r = inspector.analizar(None, "Televisor impecable, sin golpes ni fisuras, en su caja.", "Ninguno",
                           CHECK_OK, "COMO_NUEVO")
    assert r["coherencia"] == "COHERENTE"
    assert r["alertas"] == []


def test_alerta_si_la_condicion_declarada_es_mejor_que_la_real():
    r = inspector.analizar(None, "Pantalla quebrada, batería hinchada y se reinicia solo.", None, None, "COMO_NUEVO")
    assert r["condicion_sugerida"] == "ACEPTABLE"
    assert any("Declaraste «Como nuevo»" in a for a in r["alertas"])


def test_sin_checklist_no_hay_contradicciones():
    assert inspector.detectar_contradicciones("pantalla rota", None) == []


def test_explica_con_expresiones_del_texto():
    r = inspector.analizar(None, "Consola sellada de fábrica, sin uso.", None, None, None)
    assert r["terminos_clave"]
    assert all(t in inspector.normalizar("Consola sellada de fábrica, sin uso.") for t in r["terminos_clave"])


def test_reentrena_si_no_hay_modelo_guardado(tmp_path, monkeypatch):
    monkeypatch.setattr(inspector, "ARCHIVO_MODELO", tmp_path / "modelo.joblib")
    monkeypatch.setattr(inspector, "_modelo", None)

    modelo = inspector.obtener_modelo()

    assert (tmp_path / "modelo.joblib").exists()
    assert set(modelo.classes_) == set(inspector.CONDICIONES)


def test_la_ia_bloquea_la_insignia_verificado():
    revisar = {"coherencia": "REVISAR"}
    assert evaluar_verificacion(CHECK_OK, 3, "BUENO", "Ninguno")["nivel"] == "VERIFICADO"
    assert evaluar_verificacion(CHECK_OK, 3, "BUENO", "Ninguno", revisar)["nivel"] == "PARCIAL"


def test_si_la_ia_falla_la_publicacion_sigue(monkeypatch):
    def falla(*args):
        raise RuntimeError("modelo no disponible")

    monkeypatch.setattr(inspector, "analizar", falla)
    assert inspeccion_ia.inspeccionar_y_guardar(None, 1, "x", "y", None, None, "BUENO") is None


def test_endpoint_inspeccionar_requiere_sesion(client):
    assert client.post("/ia/inspeccionar", json={"descripcion": "Celular"}).status_code in (401, 403)


def test_endpoint_inspeccionar(client, auth):
    r = client.post("/ia/inspeccionar", headers=auth, json={
        "nombre": "iPhone 11", "descripcion": "Tiene una grieta en la pantalla.",
        "descripcion_defectos": "Grieta", "condicion": "COMO_NUEVO", "checklist": CHECK_OK
    })
    datos = r.json()

    assert r.status_code == 200
    assert datos["coherencia"] == "REVISAR"
    assert datos["version_modelo"] == inspector.VERSION_MODELO


def test_endpoint_modelo(client):
    datos = client.get("/ia/modelo").json()
    assert datos["version"] == inspector.VERSION_MODELO
    assert datos["clases"] == list(inspector.CONDICIONES)
