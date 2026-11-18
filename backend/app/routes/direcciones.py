from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from app.security import obtener_usuario_token
from app.services.direcciones import (
    listar_direcciones,
    obtener_direccion,
    crear_direccion,
    actualizar_direccion,
    eliminar_direccion
)


router = APIRouter(
    prefix="/direcciones",
    tags=["Direcciones"]
)


class DireccionRequest(BaseModel):
    # Límites iguales a las columnas de Direcciones
    direccion: str = Field(min_length=5, max_length=250)
    ciudad: str = Field(min_length=2, max_length=100)
    departamento: str = Field(min_length=2, max_length=100)
    codigo_postal: str | None = Field(default=None, max_length=15, pattern=r"^[0-9A-Za-z -]{3,15}$")

    @field_validator(
        "direccion", "ciudad", "departamento", "codigo_postal",
        mode="before"
    )
    @classmethod
    def limpiar(cls, valor):
        # Quita espacios antes de validar longitudes
        if isinstance(valor, str):
            valor = valor.strip()
            return valor or None

        return valor


@router.get("/")
def listar(id_usuario: int = Depends(obtener_usuario_token)):
    return listar_direcciones(id_usuario)


@router.post("/", status_code=201)
def crear(
    datos: DireccionRequest,
    id_usuario: int = Depends(obtener_usuario_token)
):
    return crear_direccion(
        id_usuario=id_usuario,
        direccion=datos.direccion,
        ciudad=datos.ciudad,
        departamento=datos.departamento,
        codigo_postal=datos.codigo_postal
    )


@router.get("/{id_direccion}")
def consultar(
    id_direccion: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    return obtener_direccion(id_usuario, id_direccion)


@router.put("/{id_direccion}")
def actualizar(
    id_direccion: int,
    datos: DireccionRequest,
    id_usuario: int = Depends(obtener_usuario_token)
):
    return actualizar_direccion(
        id_usuario=id_usuario,
        id_direccion=id_direccion,
        direccion=datos.direccion,
        ciudad=datos.ciudad,
        departamento=datos.departamento,
        codigo_postal=datos.codigo_postal
    )


@router.delete("/{id_direccion}")
def eliminar(
    id_direccion: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    return eliminar_direccion(id_usuario, id_direccion)
