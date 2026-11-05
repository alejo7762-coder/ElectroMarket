from decimal import Decimal

import pytest

from app.services.cancelaciones import (
    calcular_lineas_a_cancelar,
    monto_linea,
    recortar,
    CancellationConflict
)


def _lineas():
    return [
        {"id_detalle_pedido": 1, "id_producto": 10, "nombre": "Celular",
         "vigente": 3, "precio": Decimal("500000.00")},
        {"id_detalle_pedido": 2, "id_producto": 20, "nombre": "Televisor",
         "vigente": 1, "precio": Decimal("1200000.00")},
        {"id_detalle_pedido": 3, "id_producto": 30, "nombre": "Nevera",
         "vigente": 0, "precio": Decimal("2000000.00")},
    ]


def test_total_toma_todas_las_unidades_vigentes():
    resultado = calcular_lineas_a_cancelar(_lineas(), None)

    assert [(l["id_producto"], c) for l, c in resultado] == [(10, 3), (20, 1)]


def test_parcial_por_unidades():
    resultado = calcular_lineas_a_cancelar(_lineas(), {10: 2})

    assert [(l["id_producto"], c) for l, c in resultado] == [(10, 2)]


def test_parcial_sin_cantidad_cancela_todo_el_producto():
    resultado = calcular_lineas_a_cancelar(_lineas(), {10: None})

    assert resultado[0][1] == 3


def test_no_permite_cancelar_mas_de_lo_vigente():
    with pytest.raises(CancellationConflict):
        calcular_lineas_a_cancelar(_lineas(), {10: 4})


def test_no_permite_producto_ya_cancelado():
    with pytest.raises(CancellationConflict):
        calcular_lineas_a_cancelar(_lineas(), {30: 1})


def test_no_permite_producto_ajeno_al_pedido():
    with pytest.raises(CancellationConflict):
        calcular_lineas_a_cancelar(_lineas(), {99: 1})


def test_total_sin_unidades_vigentes():
    lineas = [dict(l, vigente=0) for l in _lineas()]

    with pytest.raises(CancellationConflict):
        calcular_lineas_a_cancelar(lineas, None)


def test_monto_linea_redondea_a_centavos():
    assert monto_linea(Decimal("10.005"), 1) == Decimal("10.01")
    assert monto_linea(Decimal("500000.00"), 2) == Decimal("1000000.00")


def test_recortar_textos_largos():
    assert len(recortar("x" * 600)) == 250
    assert recortar("corto") == "corto"
