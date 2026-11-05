from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from fastapi import Depends
from app.services.usuarios import (
    autenticar_usuario,
    InvalidCredentials,
    AccountInactive
)
from app.security import crear_token_acceso, obtener_usuario_token
from app.db.connection import get_connection
from app.services.usuarios import (
    registrar_usuario,
    EmailAlreadyExists
)

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"]
)


class RegistroUsuario(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    apellido: str = Field(min_length=2, max_length=100)
    correo: EmailStr
    contrasena: str = Field(min_length=8, max_length=128)
    telefono: Optional[str] = Field(default=None, max_length=20)


@router.post("/registro", status_code=201)
def crear_usuario(datos: RegistroUsuario):

    try:
        id_usuario = registrar_usuario(
            nombre=datos.nombre.strip(),
            apellido=datos.apellido.strip(),
            correo=str(datos.correo).strip().lower(),
            contrasena=datos.contrasena,
            telefono=datos.telefono
        )

        return {
            "mensaje": "Usuario registrado correctamente.",
            "id_usuario": id_usuario
        }

    except EmailAlreadyExists as error:
        raise HTTPException(
            status_code=409,
            detail=str(error)
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="No fue posible registrar el usuario."
        )
class LoginUsuario(BaseModel):
    correo: EmailStr
    contrasena: str = Field(min_length=1, max_length=128)

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

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="No fue posible iniciar sesión."
        )


@router.get("/me")
def consultar_perfil(
    id_usuario: int = Depends(obtener_usuario_token)
):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT IdUsuario, Nombre, Apellido, Correo, Telefono,
                   FechaRegistro, Estado
            FROM Usuarios
            WHERE IdUsuario = ?;
        """, id_usuario)

        usuario = cursor.fetchone()

        if usuario is None or usuario.Estado != "ACTIVO":
            raise HTTPException(
                status_code=401,
                detail="Usuario no disponible."
            )

        return {
            "id_usuario": usuario.IdUsuario,
            "nombre": usuario.Nombre,
            "apellido": usuario.Apellido,
            "correo": usuario.Correo,
            "telefono": usuario.Telefono,
            "fecha_registro": usuario.FechaRegistro,
            "estado": usuario.Estado
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar el perfil."
        )

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()