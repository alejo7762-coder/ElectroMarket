from typing import Literal

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, Field, field_validator, model_validator

from app.security import obtener_usuario_token
from app.services.devoluciones import (
    confirmar_recepcion,
    listar_devoluciones,
    obtener_devolucion,
    registrar_envio,
    responder_devolucion,
    solicitar_devolucion
)


router = APIRouter(prefix="/devoluciones", tags=["Devoluciones"])

IdDevolucion = Path(gt=0, description="Identificador de la devolución")
Motivo = Literal["DEFECTUOSO", "NO_COINCIDE", "LLEGO_DANADO", "EQUIVOCADO", "ARREPENTIMIENTO"]
Estado = Literal["SOLICITADA", "APROBADA", "RECHAZADA", "ENVIADA", "RECIBIDA"]


class SinEspacios(BaseModel):
    """Quita los espacios de los extremos de todos los textos."""

    @field_validator("*", mode="before")
    @classmethod
    def quitar_espacios(cls, valor):
        return valor.strip() if isinstance(valor, str) else valor


class ProductoDevolver(BaseModel):
    id_producto: int = Field(gt=0)
    cantidad: int | None = Field(default=None, gt=0, description="Vacío = todas las unidades disponibles")


class SolicitudDevolucion(SinEspacios):
    id_venta: int = Field(gt=0)
    motivo: Motivo
    descripcion: str = Field(min_length=10, max_length=1000)
    productos: list[ProductoDevolver] | None = Field(default=None, description="Vacío = toda la compra")


    @model_validator(mode="after")
    def sin_repetidos(self):
        if self.productos:
            ids = [p.id_producto for p in self.productos]
            if len(ids) != len(set(ids)):
                raise ValueError("Cada producto debe aparecer una sola vez.")
        return self


class Respuesta(SinEspacios):
    observacion: str | None = Field(default=None, max_length=500)



class Rechazo(SinEspacios):
    observacion: str = Field(min_length=5, max_length=500, description="Motivo del rechazo")



class EnvioDevolucion(SinEspacios):
    transportadora: str = Field(min_length=2, max_length=100)
    numero_guia: str = Field(min_length=3, max_length=100)



class Recepcion(BaseModel):
    reintegrar_inventario: bool = Field(description="Devolver las unidades al inventario para venderlas de nuevo")


@router.post("/", status_code=201)
def solicitar(datos: SolicitudDevolucion, id_usuario: int = Depends(obtener_usuario_token)):
    """El comprador pide devolver una compra entregada (dentro del plazo)."""
    productos = None if not datos.productos else {p.id_producto: p.cantidad for p in datos.productos}
    return solicitar_devolucion(id_usuario, datos.id_venta, datos.motivo, datos.descripcion, productos)


@router.get("/")
def mis_devoluciones(
    rol: Literal["COMPRADOR", "VENDEDOR"] | None = None,
    id_pedido: int | None = Query(default=None, gt=0),
    estado: Estado | None = None,
    id_usuario: int = Depends(obtener_usuario_token)
):
    return listar_devoluciones(id_usuario, rol, id_pedido, estado)


@router.get("/{id_devolucion}")
def detalle(id_devolucion: int = IdDevolucion, id_usuario: int = Depends(obtener_usuario_token)):
    return obtener_devolucion(id_usuario, id_devolucion)


@router.post("/{id_devolucion}/aprobar")
def aprobar(datos: Respuesta, id_devolucion: int = IdDevolucion, id_usuario: int = Depends(obtener_usuario_token)):
    """El vendedor acepta la devolución; el comprador debe enviar el producto."""
    return responder_devolucion(id_usuario, id_devolucion, True, datos.observacion or None)


@router.post("/{id_devolucion}/rechazar")
def rechazar(datos: Rechazo, id_devolucion: int = IdDevolucion, id_usuario: int = Depends(obtener_usuario_token)):
    return responder_devolucion(id_usuario, id_devolucion, False, datos.observacion)


@router.post("/{id_devolucion}/enviar")
def enviar(datos: EnvioDevolucion, id_devolucion: int = IdDevolucion, id_usuario: int = Depends(obtener_usuario_token)):
    """El comprador registra la transportadora y la guía con que devolvió el producto."""
    return registrar_envio(id_usuario, id_devolucion, datos.transportadora, datos.numero_guia)


@router.post("/{id_devolucion}/recibir")
def recibir(datos: Recepcion, id_devolucion: int = IdDevolucion, id_usuario: int = Depends(obtener_usuario_token)):
    """El vendedor confirma que recibió el producto: se registra el reembolso."""
    return confirmar_recepcion(id_usuario, id_devolucion, datos.reintegrar_inventario)
