from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query
)

from app.security import obtener_usuario_token
from app.services.ventas import (
    listar_ventas,
    obtener_venta,
    resumen_ventas,
    ESTADOS_VENTA
)


router = APIRouter(
    prefix="/ventas",
    tags=["Ventas"]
)


@router.get("/")
def mis_ventas(
    estado: str | None = Query(
        default=None,
        description="Filtra por estado: " + ", ".join(ESTADOS_VENTA)
    ),
    id_usuario: int = Depends(obtener_usuario_token)
):
    if estado:
        estado = estado.upper()

        if estado not in ESTADOS_VENTA:
            raise HTTPException(
                status_code=422,
                detail="Estado no válido. Usa: " + ", ".join(ESTADOS_VENTA)
            )

    return listar_ventas(id_usuario, estado)


# Debe declararse antes de /{id_venta}
@router.get("/resumen")
def resumen(id_usuario: int = Depends(obtener_usuario_token)):
    return resumen_ventas(id_usuario)


@router.get("/{id_venta}")
def detalle_venta(
    id_venta: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    return obtener_venta(id_usuario, id_venta)
