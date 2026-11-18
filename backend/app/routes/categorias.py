from fastapi import APIRouter

from app.services.productos import listar_categorias


router = APIRouter(
    prefix="/categorias",
    tags=["Categorías"]
)


@router.get("/")
def consultar_categorias():
    return listar_categorias()
