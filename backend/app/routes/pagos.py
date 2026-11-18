from fastapi import APIRouter, Depends

from app.security import obtener_usuario_token
from app.services.pagos import listar_pagos, obtener_pago


router = APIRouter(
    prefix="/pagos",
    tags=["Pagos"]
)


@router.get("/")
def mis_pagos(id_usuario: int = Depends(obtener_usuario_token)):
    return listar_pagos(id_usuario)


@router.get("/{id_pago}")
def detalle_pago(
    id_pago: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    return obtener_pago(id_usuario, id_pago)
