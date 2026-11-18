from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.security import obtener_usuario_token
from app.services.carrito import UserNotActive
from app.services.direcciones import (
    listar_direcciones,
    obtener_direccion,
    crear_direccion,
    actualizar_direccion,
    eliminar_direccion,
    AddressNotFound,
    AddressInUse
)


router = APIRouter(
    prefix="/direcciones",
    tags=["Direcciones"]
)


class DireccionRequest(BaseModel):
    direccion: str = Field(min_length=5, max_length=200)
    ciudad: str = Field(min_length=2, max_length=100)
    departamento: str = Field(min_length=2, max_length=100)
    codigo_postal: str | None = Field(default=None, max_length=20)

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


def _error_interno(contexto: str, error: Exception):
    print(f"ERROR AL {contexto}:", repr(error))

    return HTTPException(
        status_code=500,
        detail=f"No fue posible {contexto.lower()}."
    )


@router.get("/")
def listar(id_usuario: int = Depends(obtener_usuario_token)):
    try:
        return listar_direcciones(id_usuario)

    except UserNotActive as error:
        raise HTTPException(status_code=403, detail=str(error))

    except Exception as error:
        raise _error_interno("CONSULTAR LAS DIRECCIONES", error)


@router.post("/", status_code=201)
def crear(
    datos: DireccionRequest,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return crear_direccion(
            id_usuario=id_usuario,
            direccion=datos.direccion,
            ciudad=datos.ciudad,
            departamento=datos.departamento,
            codigo_postal=datos.codigo_postal
        )

    except UserNotActive as error:
        raise HTTPException(status_code=403, detail=str(error))

    except Exception as error:
        raise _error_interno("REGISTRAR LA DIRECCIÓN", error)


@router.get("/{id_direccion}")
def consultar(
    id_direccion: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return obtener_direccion(id_usuario, id_direccion)

    except AddressNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except Exception as error:
        raise _error_interno("CONSULTAR LA DIRECCIÓN", error)


@router.put("/{id_direccion}")
def actualizar(
    id_direccion: int,
    datos: DireccionRequest,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return actualizar_direccion(
            id_usuario=id_usuario,
            id_direccion=id_direccion,
            direccion=datos.direccion,
            ciudad=datos.ciudad,
            departamento=datos.departamento,
            codigo_postal=datos.codigo_postal
        )

    except UserNotActive as error:
        raise HTTPException(status_code=403, detail=str(error))

    except AddressNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except Exception as error:
        raise _error_interno("ACTUALIZAR LA DIRECCIÓN", error)


@router.delete("/{id_direccion}")
def eliminar(
    id_direccion: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return eliminar_direccion(id_usuario, id_direccion)

    except UserNotActive as error:
        raise HTTPException(status_code=403, detail=str(error))

    except AddressNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except AddressInUse as error:
        raise HTTPException(status_code=409, detail=str(error))

    except Exception as error:
        raise _error_interno("ELIMINAR LA DIRECCIÓN", error)
