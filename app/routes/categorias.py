from fastapi import APIRouter, HTTPException

from app.services.productos import listar_categorias


router = APIRouter(
    prefix="/categorias",
    tags=["Categorías"]
)


@router.get("/")
def consultar_categorias():
    try:
        return listar_categorias()

    except Exception as error:
        print("ERROR AL CONSULTAR CATEGORÍAS:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar las categorías."
        )
