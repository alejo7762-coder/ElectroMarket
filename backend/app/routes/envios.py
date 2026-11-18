from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.security import obtener_usuario_token
from app.services.envios import (
    crear_envio,
    actualizar_estado_envio,
    obtener_seguimiento,
    obtener_envios_pedido
)


router = APIRouter(
    prefix="/envios",
    tags=["Envíos"]
)


class CrearEnvioRequest(BaseModel):
    transportadora: str | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )


class ActualizarEnvioRequest(BaseModel):
    estado: Literal[
        "PREPARANDO",
        "ENVIADO",
        "EN_TRANSITO",
        "ENTREGADO",
        "PROBLEMA"
    ]
    observacion: str | None = Field(default=None, max_length=500)


@router.post("/ventas/{id_venta}", status_code=201)
def crear(
    id_venta: int,
    datos: CrearEnvioRequest | None = None,
    id_usuario: int = Depends(obtener_usuario_token)
):
    return crear_envio(
        id_vendedor=id_usuario,
        id_venta=id_venta,
        transportadora=datos.transportadora if datos else None
    )


@router.patch("/{id_envio}/estado")
def actualizar_estado(
    id_envio: int,
    datos: ActualizarEnvioRequest,
    id_usuario: int = Depends(obtener_usuario_token)
):
    return actualizar_estado_envio(
        id_vendedor=id_usuario,
        id_envio=id_envio,
        nuevo_estado=datos.estado,
        observacion=datos.observacion
    )


@router.get("/pedido/{id_pedido}")
def envios_de_un_pedido(
    id_pedido: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    return obtener_envios_pedido(id_usuario, id_pedido)


@router.get("/{id_envio}")
def seguimiento(
    id_envio: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    return obtener_seguimiento(id_usuario, id_envio)
