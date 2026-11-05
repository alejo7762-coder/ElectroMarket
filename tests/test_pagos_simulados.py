from app.services.pedidos import _simular_pago


def test_pago_simulado_se_aprueba():
    aprobado, _ = _simular_pago("SIMULADO", None)
    assert aprobado is True


def test_transferencia_simulada_se_aprueba():
    aprobado, _ = _simular_pago("TRANSFERENCIA_SIMULADA", None)
    assert aprobado is True


def test_tarjeta_valida_se_aprueba():
    aprobado, _ = _simular_pago("TARJETA_SIMULADA", "4111111111111111")
    assert aprobado is True


def test_tarjeta_terminada_en_0000_se_rechaza():
    aprobado, mensaje = _simular_pago("TARJETA_SIMULADA", "4111111111110000")
    assert aprobado is False
    assert "rechazada" in mensaje.lower()
