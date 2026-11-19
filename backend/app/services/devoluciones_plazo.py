"""Plazo para devolver una compra entregada (sin dependencias, para evitar ciclos)."""

from datetime import datetime

DIAS_PLAZO = 15


def dias_restantes(fecha_entrega: datetime | None, ahora: datetime | None = None) -> int:
    """Días que quedan para pedir la devolución (0 si venció o no hay entrega)."""
    if fecha_entrega is None:
        return 0
    transcurridos = ((ahora or datetime.now()) - fecha_entrega).days
    return max(0, DIAS_PLAZO - transcurridos)
