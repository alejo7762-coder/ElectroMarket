from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, Field, field_validator

from app.security import obtener_usuario_token
from app.services.resenas import (
    crear_resena,
    editar_resena,
    mis_resenas,
    resenas_producto,
    resenas_vendedor
)
from app.services.vendedores import perfil_vendedor


router = APIRouter(tags=["Reseñas y vendedores"])


class Calificacion(BaseModel):
    calificacion_producto: int = Field(ge=1, le=5, description="Estrellas para el producto (1 a 5)")
    calificacion_vendedor: int = Field(ge=1, le=5, description="Estrellas para el vendedor (1 a 5)")
    comentario: str | None = Field(default=None, max_length=1000)

    @field_validator("comentario", mode="before")
    @classmethod
    def quitar_espacios(cls, valor):
        return valor.strip() if isinstance(valor, str) else valor


class ResenaNueva(Calificacion):
    id_venta: int = Field(gt=0)
    id_producto: int = Field(gt=0)


# ---------------------------------------------------------------- públicas

@router.get("/productos/{id_producto}/resenas")
def consultar_resenas_producto(id_producto: int = Path(gt=0)):
    """Promedio, distribución de estrellas y reseñas del producto."""
    return resenas_producto(id_producto)


@router.get("/vendedores/{id_vendedor}")
def consultar_vendedor(id_vendedor: int = Path(gt=0)):
    """Perfil público del vendedor con su índice de fiabilidad."""
    return perfil_vendedor(id_vendedor)


@router.get("/vendedores/{id_vendedor}/resenas")
def consultar_resenas_vendedor(id_vendedor: int = Path(gt=0)):
    return resenas_vendedor(id_vendedor)


# ---------------------------------------------------------------- comprador

@router.post("/resenas/", status_code=201)
def publicar_resena(datos: ResenaNueva, id_usuario: int = Depends(obtener_usuario_token)):
    """Reseña de un producto comprado (la venta debe estar entregada)."""
    return crear_resena(id_usuario, datos.id_venta, datos.id_producto,
                        datos.calificacion_producto, datos.calificacion_vendedor, datos.comentario)


@router.put("/resenas/{id_resena}")
def actualizar_resena(datos: Calificacion, id_resena: int = Path(gt=0),
                      id_usuario: int = Depends(obtener_usuario_token)):
    return editar_resena(id_usuario, id_resena, datos.calificacion_producto,
                         datos.calificacion_vendedor, datos.comentario)


@router.get("/resenas/mias")
def consultar_mis_resenas(id_pedido: int | None = Query(default=None, gt=0),
                          id_usuario: int = Depends(obtener_usuario_token)):
    return mis_resenas(id_usuario, id_pedido)
