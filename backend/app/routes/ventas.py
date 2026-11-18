from fastapi import APIRouter, Depends, HTTPException, Query

from app.security import obtener_usuario_token
from app.services.carrito import UserNotActive
from app.services.ventas import (
    listar_ventas,
    obtener_venta,
    resumen_ventas,
    SaleNotFound,
    ESTADOS_VENTA
)


router = APIRouter(
    prefix="/ventas",
    tags=["Ventas"]
)


def _error_interno(contexto: str, error: Exception):
    print(f"ERROR AL {contexto}:", repr(error))

    return HTTPException(
        status_code=500,
        detail=f"No fue posible {contexto.lower()}."
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

    try:
        return listar_ventas(id_usuario, estado)

    except UserNotActive as error:
        raise HTTPException(status_code=403, detail=str(error))

    except Exception as error:
        raise _error_interno("CONSULTAR LAS VENTAS", error)


# Debe declararse antes de /{id_venta}
@router.get("/resumen")
def resumen(id_usuario: int = Depends(obtener_usuario_token)):
    try:
        return resumen_ventas(id_usuario)

    except UserNotActive as error:
        raise HTTPException(status_code=403, detail=str(error))

    except Exception as error:
        raise _error_interno("CONSULTAR EL RESUMEN DE VENTAS", error)


@router.get("/{id_venta}")
def detalle_venta(
    id_venta: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return obtener_venta(id_usuario, id_venta)

    except SaleNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except Exception as error:
        raise _error_interno("CONSULTAR LA VENTA", error)
