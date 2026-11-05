from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from fastapi import UploadFile, File
import os

from app.services.productos import modificar_producto

from app.services.productos import (
    publicar_producto,
    CategoryNotFound,
    CategoryInactive,
    listar_productos,
    obtener_producto,
    ProductNotFound,
    ProductForbidden,
    ProductDeleted,
    gestionar_estado_producto,
    ProductInvalidState,
    ProductOutOfStock
)

from app.services.imagenes import (
    guardar_imagen,
    listar_imagenes_producto,
    cambiar_imagen_principal,
    eliminar_imagen,
    ProductNotFound as ImageProductNotFound,
    ProductForbidden as ImageProductForbidden,
    ImageLimitExceeded,
    InvalidImage
)

from app.security import obtener_usuario_token


router = APIRouter(
    prefix="/productos",
    tags=["Productos"]
)


class ProductoNuevo(BaseModel):
    id_categoria: int = Field(gt=0)
    nombre: str = Field(min_length=2, max_length=150)
    descripcion: str = Field(min_length=1, max_length=1000)
    precio: Decimal = Field(gt=0)
    stock: int = Field(ge=0)
    condicion: Literal[
        "COMO_NUEVO",
        "BUENO",
        "ACEPTABLE"
    ]


@router.post("/publicar", status_code=201)
def crear_producto(
    datos: ProductoNuevo,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        id_producto = publicar_producto(
            id_vendedor=id_usuario,
            id_categoria=datos.id_categoria,
            nombre=datos.nombre.strip(),
            descripcion=datos.descripcion.strip(),
            precio=datos.precio,
            stock=datos.stock,
            condicion=datos.condicion
        )

        return {
            "mensaje": "Producto publicado correctamente.",
            "id_producto": id_producto
        }

    except CategoryNotFound as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )

    except CategoryInactive as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        print("ERROR AL PUBLICAR PRODUCTO:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible publicar el producto."
        )
@router.get("/")
def consultar_productos(
    id_categoria: int | None = None
):
    try:
        if id_categoria is not None and id_categoria <= 0:
            raise HTTPException(
                status_code=400,
                detail="El identificador de categoría debe ser mayor que cero."
            )

        productos = listar_productos(id_categoria)

        return {
            "total": len(productos),
            "productos": productos
        }

    except HTTPException:
        raise

    except Exception as error:
        print("ERROR AL CONSULTAR PRODUCTOS:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar los productos."
        )


@router.get("/{id_producto}")
def consultar_producto(id_producto: int):
    try:
        if id_producto <= 0:
            raise HTTPException(
                status_code=400,
                detail="El identificador debe ser mayor que cero."
            )

        producto = obtener_producto(id_producto)

        if producto is None:
            raise HTTPException(
                status_code=404,
                detail="El producto no existe."
            )

        return producto

    except HTTPException:
        raise

    except Exception as error:
        print("ERROR AL CONSULTAR PRODUCTO:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar el producto."
        )

class ProductoActualizar(BaseModel):
    id_categoria: int = Field(gt=0)
    nombre: str = Field(min_length=2, max_length=150)
    descripcion: str = Field(min_length=1, max_length=1000)
    precio: Decimal = Field(gt=0)
    stock: int = Field(ge=0)
    condicion: Literal[
        "COMO_NUEVO",
        "BUENO",
        "ACEPTABLE"
    ]


@router.put("/{id_producto}")
def actualizar_producto(
    id_producto: int,
    datos: ProductoActualizar,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        if id_producto <= 0:
            raise HTTPException(
                status_code=400,
                detail="El identificador debe ser mayor que cero."
            )

        resultado = modificar_producto(
            id_producto=id_producto,
            id_vendedor=id_usuario,
            id_categoria=datos.id_categoria,
            nombre=datos.nombre.strip(),
            descripcion=datos.descripcion.strip(),
            precio=datos.precio,
            stock=datos.stock,
            condicion=datos.condicion
        )

        return {
            "mensaje": "Producto actualizado correctamente.",
            "id_producto": resultado
        }

    except ProductNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except ProductForbidden as error:
        raise HTTPException(status_code=403, detail=str(error))

    except ProductDeleted as error:
        raise HTTPException(status_code=400, detail=str(error))

    except CategoryNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except CategoryInactive as error:
        raise HTTPException(status_code=400, detail=str(error))

    except HTTPException:
        raise

    except Exception as error:
        print("ERROR AL MODIFICAR PRODUCTO:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="No fue posible modificar el producto."
        )
@router.patch("/{id_producto}/estado")
def cambiar_estado_producto(
    id_producto: int,
    accion: Literal["PAUSAR", "REACTIVAR", "ELIMINAR"],
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        resultado = gestionar_estado_producto(
            id_producto=id_producto,
            id_vendedor=id_usuario,
            accion=accion
        )

        return {
            "mensaje": "Estado del producto actualizado correctamente.",
            "producto": resultado
        }

    except ProductNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except ProductForbidden as error:
        raise HTTPException(status_code=403, detail=str(error))

    except ProductDeleted as error:
        raise HTTPException(status_code=400, detail=str(error))

    except ProductInvalidState as error:
        raise HTTPException(status_code=400, detail=str(error))

    except ProductOutOfStock as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Error interno al gestionar el estado del producto."
        )


@router.post("/{id_producto}/imagenes", status_code=201)
async def subir_imagen_producto(
    id_producto: int,
    archivo: UploadFile = File(...),
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        # Obtener extensión del archivo
        extension = os.path.splitext(
            archivo.filename or ""
        )[1].lower()

        # Leer como máximo 5 MB + 1 byte
        contenido = await archivo.read(5 * 1024 * 1024 + 1)

        resultado = guardar_imagen(
            id_producto=id_producto,
            id_vendedor=id_usuario,
            contenido=contenido,
            extension=extension
        )

        return {
            "mensaje": "Imagen cargada correctamente.",
            "imagen": resultado
        }

    except ImageProductNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except ImageProductForbidden as error:
        raise HTTPException(status_code=403, detail=str(error))

    except ImageLimitExceeded as error:
        raise HTTPException(status_code=400, detail=str(error))

    except InvalidImage as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Error interno al cargar la imagen."
        )

    finally:
        await archivo.close()
@router.get("/{id_producto}/imagenes")
def consultar_imagenes_producto(
    id_producto: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        imagenes = listar_imagenes_producto(id_producto)

        return {
            "id_producto": id_producto,
            "total_imagenes": len(imagenes),
            "imagenes": imagenes
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Error interno al consultar las imágenes."
        )
@router.patch("/{id_producto}/imagenes/{id_imagen}/principal")
def actualizar_imagen_principal(
    id_producto: int,
    id_imagen: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return cambiar_imagen_principal(
            id_producto=id_producto,
            id_imagen=id_imagen,
            id_vendedor=id_usuario
        )

    except ImageProductNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except ImageProductForbidden as error:
        raise HTTPException(status_code=403, detail=str(error))

    except InvalidImage as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Error interno al actualizar la imagen principal."
        )
@router.delete("/{id_producto}/imagenes/{id_imagen}")
def eliminar_imagen_producto(
    id_producto: int,
    id_imagen: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return eliminar_imagen(
            id_producto=id_producto,
            id_imagen=id_imagen,
            id_vendedor=id_usuario
        )

    except ImageProductNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except ImageProductForbidden as error:
        raise HTTPException(status_code=403, detail=str(error))

    except InvalidImage as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Error interno al eliminar la imagen."
        )