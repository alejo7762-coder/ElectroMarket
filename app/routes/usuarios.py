from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.security import crear_token_acceso, obtener_usuario_token
from app.services.usuarios import (
    registrar_usuario,
    autenticar_usuario,
    obtener_perfil,
    actualizar_perfil,
    cambiar_contrasena,
    EmailAlreadyExists,
    InvalidCredentials,
    AccountInactive,
    UserNotFound
)


router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"]
)


EDAD_MINIMA = 18

Genero = Literal["MASCULINO", "FEMENINO", "OTRO", "PREFIERO_NO_DECIRLO"]


def _limpiar(valor):
    if isinstance(valor, str):
        valor = valor.strip()
        return valor or None

    return valor


def _validar_fecha_nacimiento(valor: date | None):
    if valor is None:
        return None

    hoy = date.today()

    if valor > hoy:
        raise ValueError("La fecha de nacimiento no puede estar en el futuro.")

    edad = hoy.year - valor.year - (
        (hoy.month, hoy.day) < (valor.month, valor.day)
    )

    if edad < EDAD_MINIMA:
        raise ValueError(
            f"Debes tener al menos {EDAD_MINIMA} años para registrarte."
        )

    if edad > 120:
        raise ValueError("La fecha de nacimiento no es válida.")

    return valor


class DatosPersonales(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    apellido: str = Field(min_length=2, max_length=100)
    telefono: Optional[str] = Field(
        default=None,
        max_length=20,
        pattern=r"^\+?[0-9 ]{7,20}$"
    )
    fecha_nacimiento: Optional[date] = None
    genero: Optional[Genero] = None

    @field_validator("nombre", "apellido", "telefono", mode="before")
    @classmethod
    def limpiar_textos(cls, valor):
        return _limpiar(valor)

    @field_validator("genero", mode="before")
    @classmethod
    def limpiar_genero(cls, valor):
        return _limpiar(valor)

    @field_validator("fecha_nacimiento")
    @classmethod
    def validar_fecha(cls, valor):
        return _validar_fecha_nacimiento(valor)


class RegistroUsuario(DatosPersonales):
    correo: EmailStr
    contrasena: str = Field(min_length=8, max_length=128)


class LoginUsuario(BaseModel):
    correo: EmailStr
    contrasena: str = Field(min_length=1, max_length=128)


class CambioContrasena(BaseModel):
    contrasena_actual: str = Field(min_length=1, max_length=128)
    contrasena_nueva: str = Field(min_length=8, max_length=128)


@router.post("/registro", status_code=201)
def crear_usuario(datos: RegistroUsuario):
    try:
        id_usuario = registrar_usuario(
            nombre=datos.nombre,
            apellido=datos.apellido,
            correo=str(datos.correo).strip().lower(),
            contrasena=datos.contrasena,
            telefono=datos.telefono,
            fecha_nacimiento=datos.fecha_nacimiento,
            genero=datos.genero
        )

        return {
            "mensaje": "Usuario registrado correctamente.",
            "id_usuario": id_usuario
        }

    except EmailAlreadyExists as error:
        raise HTTPException(status_code=409, detail=str(error))

    except Exception as error:
        print("ERROR AL REGISTRAR USUARIO:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible registrar el usuario."
        )


@router.post("/login")
def iniciar_sesion(datos: LoginUsuario):
    try:
        usuario = autenticar_usuario(
            correo=str(datos.correo).strip().lower(),
            contrasena=datos.contrasena
        )

        token = crear_token_acceso(usuario)

        return {
            "mensaje": "Inicio de sesión exitoso.",
            "access_token": token,
            "token_type": "bearer",
            "usuario": usuario
        }

    except InvalidCredentials:
        raise HTTPException(
            status_code=401,
            detail="Correo o contraseña incorrectos."
        )

    except AccountInactive:
        raise HTTPException(
            status_code=403,
            detail="La cuenta no está activa."
        )

    except Exception as error:
        print("ERROR AL INICIAR SESIÓN:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible iniciar sesión."
        )


@router.get("/me")
def consultar_perfil(id_usuario: int = Depends(obtener_usuario_token)):
    try:
        return obtener_perfil(id_usuario)

    except (UserNotFound, AccountInactive):
        raise HTTPException(status_code=401, detail="Usuario no disponible.")

    except Exception as error:
        print("ERROR AL CONSULTAR EL PERFIL:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar el perfil."
        )


@router.put("/me")
def editar_perfil(
    datos: DatosPersonales,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        perfil = actualizar_perfil(
            id_usuario=id_usuario,
            nombre=datos.nombre,
            apellido=datos.apellido,
            telefono=datos.telefono,
            fecha_nacimiento=datos.fecha_nacimiento,
            genero=datos.genero
        )

        return {
            "mensaje": "Perfil actualizado correctamente.",
            "usuario": perfil
        }

    except (UserNotFound, AccountInactive):
        raise HTTPException(status_code=401, detail="Usuario no disponible.")

    except Exception as error:
        print("ERROR AL ACTUALIZAR EL PERFIL:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible actualizar el perfil."
        )


@router.put("/me/contrasena")
def actualizar_contrasena(
    datos: CambioContrasena,
    id_usuario: int = Depends(obtener_usuario_token)
):
    if datos.contrasena_actual == datos.contrasena_nueva:
        raise HTTPException(
            status_code=422,
            detail="La nueva contraseña debe ser diferente a la actual."
        )

    try:
        return cambiar_contrasena(
            id_usuario, datos.contrasena_actual, datos.contrasena_nueva
        )

    except InvalidCredentials:
        # 400 y no 401: el token es válido, lo incorrecto es el dato enviado
        raise HTTPException(
            status_code=400,
            detail="La contraseña actual no es correcta."
        )

    except UserNotFound:
        raise HTTPException(status_code=401, detail="Usuario no disponible.")

    except Exception as error:
        print("ERROR AL CAMBIAR LA CONTRASEÑA:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible cambiar la contraseña."
        )
