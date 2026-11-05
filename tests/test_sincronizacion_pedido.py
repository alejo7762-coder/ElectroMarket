"""
Prueba el cálculo del estado del pedido a partir de sus ventas
(app/services/envios.py -> _sincronizar_estado_pedido) con un cursor falso.
"""

from types import SimpleNamespace

import pytest

from app.services.envios import _sincronizar_estado_pedido


class CursorFalso:
    def __init__(self, estados_ventas):
        self.estados = estados_ventas
        self.actualizaciones = []
        self._resultado = []

    def execute(self, sql, *parametros):
        sql_normalizado = " ".join(sql.split())

        if sql_normalizado.startswith("SELECT Estado FROM Ventas"):
            self._resultado = [
                SimpleNamespace(Estado=e)
                for e in self.estados if e != "CANCELADA"
            ]
        elif sql_normalizado.startswith("SELECT COUNT(*) FROM Ventas"):
            self._resultado = [(len(self.estados),)]
        elif sql_normalizado.startswith("UPDATE Pedidos"):
            self.actualizaciones.append(parametros[0][0])
            self._resultado = []
        else:
            self._resultado = []

    def fetchall(self):
        return self._resultado

    def fetchone(self):
        return self._resultado[0] if self._resultado else None


@pytest.mark.parametrize("ventas, esperado", [
    (["PENDIENTE"], "PAGADO"),
    (["PREPARANDO"], "EN_PROCESO"),
    (["ENVIADA", "PENDIENTE"], "PARCIALMENTE_ENVIADO"),
    (["ENVIADA", "ENTREGADA"], "EN_PROCESO"),
    (["ENTREGADA", "ENTREGADA"], "COMPLETADO"),
    (["ENTREGADA", "CANCELADA"], "COMPLETADO"),
    (["CANCELADA", "CANCELADA"], "CANCELADO"),
    (["CANCELACION_SOLICITADA", "CANCELADA"], "EN_PROCESO"),
    (["CANCELACION_SOLICITADA", "PENDIENTE"], "PARCIALMENTE_ENVIADO"),
])
def test_estado_del_pedido(ventas, esperado):
    cursor = CursorFalso(ventas)

    assert _sincronizar_estado_pedido(cursor, 1, "PAGADO") == esperado


def test_no_actualiza_si_el_estado_no_cambia():
    cursor = CursorFalso(["PENDIENTE"])

    _sincronizar_estado_pedido(cursor, 1, "PAGADO")

    assert cursor.actualizaciones == []
