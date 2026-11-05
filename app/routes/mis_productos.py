from fastapi import APIRouter, Depends, HTTPException

from app.security import obtener_usuario_token
from app.services.productos import listar_productos_vendedor


router = APIRouter(
    prefix="/mis-productos",
    tags=["Productos"]
)


@router.get("/")
def consultar_mis_productos(id_usuario: int = Depends(obtener_usuario_token)):
    """Productos del vendedor autenticado (publicados, pausados y agotados)."""
    try:
        productos = listar_productos_vendedor(id_usuario)

        return {"total": len(productos), "productos": productos}

    except Exception as error:
        print("ERROR AL CONSULTAR MIS PRODUCTOS:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar tus productos."
        )
