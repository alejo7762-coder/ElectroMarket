from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.security import obtener_usuario_token

from app.services.carrito import (
    obtener_carrito,
    agregar_producto,
    actualizar_cantidad,
    eliminar_producto_carrito,
    vaciar_carrito,
    UserNotActive,
    OwnProduct,
    CartProcessed
)

from app.services.productos import (
    ProductNotFound,
    ProductInvalidState,
    ProductOutOfStock
)


router = APIRouter(
    prefix="/carrito",
    tags=["Carrito de compras"]
)


class AgregarProductoRequest(BaseModel):
    id_producto: int = Field(gt=0)
    cantidad: int = Field(gt=0)


@router.get("/")
def consultar_carrito(
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return obtener_carrito(id_usuario)

    except UserNotActive as error:
        raise HTTPException(
            status_code=403,
            detail=str(error)
        )


@router.post("/agregar", status_code=201)
def agregar_producto_carrito(
    datos: AgregarProductoRequest,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return agregar_producto(
            id_usuario=id_usuario,
            id_producto=datos.id_producto,
            cantidad=datos.cantidad
        )

    except UserNotActive as error:
        raise HTTPException(status_code=403, detail=str(error))

    except OwnProduct as error:
        raise HTTPException(status_code=403, detail=str(error))

    except CartProcessed as error:
        raise HTTPException(status_code=409, detail=str(error))

    except ProductNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except ProductInvalidState as error:
        raise HTTPException(status_code=409, detail=str(error))

    except ProductOutOfStock as error:
        raise HTTPException(status_code=409, detail=str(error))

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

@router.put("/actualizar/{id_producto}")
def actualizar_producto_carrito(
    id_producto: int,
    cantidad: int = Query(gt=0),
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return actualizar_cantidad(
            id_usuario=id_usuario,
            id_producto=id_producto,
            cantidad=cantidad
        )

    except UserNotActive as error:
        raise HTTPException(status_code=403, detail=str(error))

    except OwnProduct as error:
        raise HTTPException(status_code=403, detail=str(error))

    except CartProcessed as error:
        raise HTTPException(status_code=409, detail=str(error))

    except ProductNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except ProductInvalidState as error:
        raise HTTPException(status_code=409, detail=str(error))

    except ProductOutOfStock as error:
        raise HTTPException(status_code=409, detail=str(error))

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    
@router.delete("/eliminar/{id_producto}")
def eliminar_producto(
    id_producto: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return eliminar_producto_carrito(id_usuario, id_producto)

    except UserNotActive:
        raise HTTPException(
            status_code=403,
            detail="El usuario no está activo."
        )

    except CartProcessed:
        raise HTTPException(
            status_code=409,
            detail="No se pueden modificar productos de un carrito procesado."
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@router.delete("/vaciar")
def vaciar_carrito_usuario(
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return vaciar_carrito(id_usuario)

    except UserNotActive:
        raise HTTPException(
            status_code=403,
            detail="El usuario no está activo."
        )

    except CartProcessed:
        raise HTTPException(
            status_code=409,
            detail="No se puede vaciar un carrito procesado."
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
