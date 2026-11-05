from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.security import obtener_usuario_token
from app.services.carrito import UserNotActive
from app.services.envios import (
    crear_envio,
    actualizar_estado_envio,
    obtener_seguimiento,
    obtener_envios_pedido,
    SaleNotFound,
    ShipmentNotFound,
    OrderNotFound,
    ShipmentConflict
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


def _error_interno(contexto: str, error: Exception):
    print(f"ERROR AL {contexto}:", repr(error))

    return HTTPException(
        status_code=500,
        detail=f"No fue posible {contexto.lower()}."
    )


@router.post("/ventas/{id_venta}", status_code=201)
def crear(
    id_venta: int,
    datos: CrearEnvioRequest | None = None,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return crear_envio(
            id_vendedor=id_usuario,
            id_venta=id_venta,
            transportadora=datos.transportadora if datos else None
        )

    except UserNotActive as error:
        raise HTTPException(status_code=403, detail=str(error))

    except SaleNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except ShipmentConflict as error:
        raise HTTPException(status_code=409, detail=str(error))

    except Exception as error:
        raise _error_interno("CREAR EL ENVÍO", error)


@router.patch("/{id_envio}/estado")
def actualizar_estado(
    id_envio: int,
    datos: ActualizarEnvioRequest,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return actualizar_estado_envio(
            id_vendedor=id_usuario,
            id_envio=id_envio,
            nuevo_estado=datos.estado,
            observacion=datos.observacion
        )

    except UserNotActive as error:
        raise HTTPException(status_code=403, detail=str(error))

    except ShipmentNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except ShipmentConflict as error:
        raise HTTPException(status_code=409, detail=str(error))

    except Exception as error:
        raise _error_interno("ACTUALIZAR EL ENVÍO", error)


@router.get("/pedido/{id_pedido}")
def envios_de_un_pedido(
    id_pedido: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return obtener_envios_pedido(id_usuario, id_pedido)

    except OrderNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except Exception as error:
        raise _error_interno("CONSULTAR LOS ENVÍOS DEL PEDIDO", error)


@router.get("/{id_envio}")
def seguimiento(
    id_envio: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return obtener_seguimiento(id_usuario, id_envio)

    except ShipmentNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except Exception as error:
        raise _error_interno("CONSULTAR EL SEGUIMIENTO", error)