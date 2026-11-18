from decimal import Decimal
from pathlib import Path as RutaArchivo
from typing import Literal

from fastapi import APIRouter, Depends, File, Path, Query, UploadFile
from pydantic import BaseModel, Field, field_validator

from app.errores import ProductNotFound
from app.security import obtener_usuario_token
from app.services.imagenes import (
    MAX_SIZE,
    cambiar_imagen_principal,
    eliminar_imagen,
    guardar_imagen,
    listar_imagenes_producto
)
from app.services.productos import (
    gestionar_estado_producto,
    listar_productos,
    modificar_producto,
    obtener_producto,
    publicar_producto
)


router = APIRouter(
    prefix="/productos",
    tags=["Productos"]
)

IdProducto = Path(gt=0, description="Identificador del producto")
IdImagen = Path(gt=0, description="Identificador de la imagen")


class ChecklistEstado(BaseModel):
    """Declaración del vendedor sobre el estado del producto."""
    enciende: bool
    pantalla_sin_danos: bool
    bateria_ok: bool
    sin_reparaciones: bool = False
    accesorios_completos: bool = False
    con_garantia: bool = False


class ProductoDatos(BaseModel):
    """Datos para publicar o modificar un producto (límites = columnas de la BD)."""
    id_categoria: int = Field(gt=0)
    nombre: str = Field(min_length=2, max_length=150)
    descripcion: str = Field(min_length=1, max_length=1000)
    precio: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    stock: int = Field(ge=0, le=100_000)
    condicion: Literal["COMO_NUEVO", "BUENO", "ACEPTABLE"]
    checklist: ChecklistEstado
    # Obligatorio: defectos, rayones o desgaste ("Ninguno" si no tiene)
    descripcion_defectos: str = Field(min_length=3, max_length=1000)

    @field_validator("nombre", "descripcion", "descripcion_defectos", mode="before")
    @classmethod
    def quitar_espacios(cls, valor):
        return valor.strip() if isinstance(valor, str) else valor

    def a_servicio(self) -> dict:
        return {
            "id_categoria": self.id_categoria,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "precio": self.precio,
            "stock": self.stock,
            "condicion": self.condicion,
            "checklist": self.checklist.model_dump(),
            "defectos": self.descripcion_defectos
        }


# ----------------------------------------------------------------------
# Catálogo (público)
# ----------------------------------------------------------------------

@router.get("/")
def consultar_productos(
    id_categoria: int | None = Query(default=None, gt=0),
    id_vendedor: int | None = Query(default=None, gt=0)
):
    productos = listar_productos(id_categoria, id_vendedor)
    return {"total": len(productos), "productos": productos}


@router.get("/{id_producto}")
def consultar_producto(id_producto: int = IdProducto):
    producto = obtener_producto(id_producto)

    if producto is None:
        raise ProductNotFound("El producto no existe.")

    return producto


# ----------------------------------------------------------------------
# Gestión del vendedor
# ----------------------------------------------------------------------

@router.post("/publicar", status_code=201)
def crear_producto(
    datos: ProductoDatos,
    id_usuario: int = Depends(obtener_usuario_token)
):
    id_producto = publicar_producto(id_vendedor=id_usuario, **datos.a_servicio())
    return {"mensaje": "Producto publicado correctamente.", "id_producto": id_producto}


@router.put("/{id_producto}")
def actualizar_producto(
    datos: ProductoDatos,
    id_producto: int = IdProducto,
    id_usuario: int = Depends(obtener_usuario_token)
):
    modificar_producto(id_producto=id_producto, id_vendedor=id_usuario, **datos.a_servicio())
    return {"mensaje": "Producto actualizado correctamente.", "id_producto": id_producto}


@router.patch("/{id_producto}/estado")
def cambiar_estado_producto(
    accion: Literal["PAUSAR", "REACTIVAR", "ELIMINAR"],
    id_producto: int = IdProducto,
    id_usuario: int = Depends(obtener_usuario_token)
):
    resultado = gestionar_estado_producto(
        id_producto=id_producto,
        id_vendedor=id_usuario,
        accion=accion
    )
    return {"mensaje": "Estado del producto actualizado correctamente.", "producto": resultado}


# ----------------------------------------------------------------------
# Imágenes
# ----------------------------------------------------------------------

@router.post("/{id_producto}/imagenes", status_code=201)
async def subir_imagen_producto(
    id_producto: int = IdProducto,
    archivo: UploadFile = File(...),
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        extension = RutaArchivo(archivo.filename or "").suffix.lower()
        # Se lee un byte más del máximo para detectar archivos demasiado grandes
        contenido = await archivo.read(MAX_SIZE + 1)

        resultado = guardar_imagen(
            id_producto=id_producto,
            id_vendedor=id_usuario,
            contenido=contenido,
            extension=extension
        )
        return {"mensaje": "Imagen cargada correctamente.", "imagen": resultado}

    finally:
        await archivo.close()


@router.get("/{id_producto}/imagenes")
def consultar_imagenes_producto(id_producto: int = IdProducto):
    imagenes = listar_imagenes_producto(id_producto)
    return {"id_producto": id_producto, "total_imagenes": len(imagenes), "imagenes": imagenes}


@router.patch("/{id_producto}/imagenes/{id_imagen}/principal")
def actualizar_imagen_principal(
    id_producto: int = IdProducto,
    id_imagen: int = IdImagen,
    id_usuario: int = Depends(obtener_usuario_token)
):
    return cambiar_imagen_principal(
        id_producto=id_producto,
        id_imagen=id_imagen,
        id_vendedor=id_usuario
    )


@router.delete("/{id_producto}/imagenes/{id_imagen}")
def eliminar_imagen_producto(
    id_producto: int = IdProducto,
    id_imagen: int = IdImagen,
    id_usuario: int = Depends(obtener_usuario_token)
):
    return eliminar_imagen(
        id_producto=id_producto,
        id_imagen=id_imagen,
        id_vendedor=id_usuario
    )
