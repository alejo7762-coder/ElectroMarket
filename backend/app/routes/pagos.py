from fastapi import APIRouter, Depends, HTTPException

from app.security import obtener_usuario_token
from app.services.carrito import UserNotActive
from app.services.pagos import listar_pagos, obtener_pago, PaymentNotFound


router = APIRouter(
    prefix="/pagos",
    tags=["Pagos"]
)


@router.get("/")
def mis_pagos(id_usuario: int = Depends(obtener_usuario_token)):
    try:
        return listar_pagos(id_usuario)

    except UserNotActive as error:
        raise HTTPException(status_code=403, detail=str(error))

    except Exception as error:
        print("ERROR AL CONSULTAR LOS PAGOS:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar los pagos."
        )


@router.get("/{id_pago}")
def detalle_pago(
    id_pago: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return obtener_pago(id_usuario, id_pago)

    except PaymentNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except Exception as error:
        print("ERROR AL CONSULTAR EL PAGO:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar el pago."
        )
