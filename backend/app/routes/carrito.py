from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.security import obtener_usuario_token

from app.services.carrito import (
    obtener_carrito,
    agregar_producto,
    actualizar_cantidad,
    eliminar_producto_carrito,
    vaciar_carrito
)


router = APIRouter(
    prefix="/carrito",
    tags=["Carrito de compras"]
)


class AgregarProductoRequest(BaseModel):
    id_producto: int = Field(gt=0)
    cantidad: int = Field(gt=0, le=100)


@router.get("/")
def consultar_carrito(
    id_usuario: int = Depends(obtener_usuario_token)
):
    return obtener_carrito(id_usuario)


@router.post("/agregar", status_code=201)
def agregar_producto_carrito(
    datos: AgregarProductoRequest,
    id_usuario: int = Depends(obtener_usuario_token)
):
    return agregar_producto(
        id_usuario=id_usuario,
        id_producto=datos.id_producto,
        cantidad=datos.cantidad
    )


@router.put("/actualizar/{id_producto}")
def actualizar_producto_carrito(
    id_producto: int,
    cantidad: int = Query(gt=0, le=100),
    id_usuario: int = Depends(obtener_usuario_token)
):
    return actualizar_cantidad(
        id_usuario=id_usuario,
        id_producto=id_producto,
        cantidad=cantidad
    )


@router.delete("/eliminar/{id_producto}")
def eliminar_producto(
    id_producto: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    return eliminar_producto_carrito(id_usuario, id_producto)


@router.delete("/vaciar")
def vaciar_carrito_usuario(
    id_usuario: int = Depends(obtener_usuario_token)
):
    return vaciar_carrito(id_usuario)
