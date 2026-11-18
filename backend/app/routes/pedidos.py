from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

from app.security import obtener_usuario_token
from app.services.carrito import UserNotActive, CartProcessed
from app.services.pedidos import (
    procesar_compra,
    listar_pedidos,
    obtener_pedido,
    obtener_historial_pedido,
    EmptyCart,
    OrderNotFound,
    ESTADOS_PEDIDO,
    AddressNotFound,
    PurchaseValidationError
)


router = APIRouter(
    prefix="/pedidos",
    tags=["Pedidos"]
)


class CompraRequest(BaseModel):
    id_direccion: int = Field(gt=0)
    metodo_pago: Literal[
        "SIMULADO",
        "TARJETA_SIMULADA",
        "TRANSFERENCIA_SIMULADA"
    ] = "SIMULADO"
    numero_tarjeta: str | None = Field(
        default=None,
        pattern=r"^\d{16}$"
    )

    @model_validator(mode="after")
    def validar_tarjeta(self):
        if self.metodo_pago == "TARJETA_SIMULADA" and not self.numero_tarjeta:
            raise ValueError(
                "Debes enviar numero_tarjeta con el método TARJETA_SIMULADA."
            )
        return self


@router.post("/comprar", status_code=201)
def comprar(
    datos: CompraRequest,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        resultado = procesar_compra(
            id_usuario=id_usuario,
            id_direccion=datos.id_direccion,
            metodo_pago=datos.metodo_pago,
            numero_tarjeta=datos.numero_tarjeta
        )

        # Pago rechazado: 402 Payment Required
        if resultado["pago"]["estado"] == "RECHAZADO":
            return JSONResponse(status_code=402, content=resultado)

        return resultado

    except UserNotActive as error:
        raise HTTPException(status_code=403, detail=str(error))

    except CartProcessed as error:
        raise HTTPException(status_code=409, detail=str(error))

    except EmptyCart as error:
        raise HTTPException(status_code=400, detail=str(error))

    except AddressNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except PurchaseValidationError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "mensaje": str(error),
                "productos": error.problemas
            }
        )

    except Exception as error:
        print("ERROR AL PROCESAR LA COMPRA:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible procesar la compra."
        )


@router.get("/")
def mis_pedidos(
    estado: str | None = Query(
        default=None,
        description="Filtra por estado: " + ", ".join(ESTADOS_PEDIDO)
    ),
    id_usuario: int = Depends(obtener_usuario_token)
):
    if estado:
        estado = estado.upper()

        if estado not in ESTADOS_PEDIDO:
            raise HTTPException(
                status_code=422,
                detail="Estado no válido. Usa: " + ", ".join(ESTADOS_PEDIDO)
            )

    try:
        return listar_pedidos(id_usuario, estado)

    except UserNotActive as error:
        raise HTTPException(status_code=403, detail=str(error))

    except Exception as error:
        print("ERROR AL LISTAR LOS PEDIDOS:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar los pedidos."
        )


@router.get("/{id_pedido}")
def detalle_pedido(
    id_pedido: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return obtener_pedido(id_usuario, id_pedido)

    except OrderNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except Exception as error:
        print("ERROR AL CONSULTAR EL PEDIDO:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar el pedido."
        )


@router.get("/{id_pedido}/historial")
def historial_pedido(
    id_pedido: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return obtener_historial_pedido(id_usuario, id_pedido)

    except OrderNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except Exception as error:
        print("ERROR AL CONSULTAR EL HISTORIAL:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar el historial del pedido."
        )
