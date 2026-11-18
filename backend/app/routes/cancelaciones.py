from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from app.security import obtener_usuario_token
from app.services.carrito import UserNotActive
from app.services.cancelaciones import (
    cancelar_pedido_total,
    cancelar_pedido_parcial,
    cancelar_venta,
    responder_solicitud,
    listar_cancelaciones,
    obtener_cancelacion,
    CancellationNotFound,
    CancellationConflict,
    CancellationForbidden,
    OrderNotFound,
    SaleNotFound
)


router = APIRouter(
    prefix="/cancelaciones",
    tags=["Cancelaciones"]
)


def _limpiar_texto(valor):
    if isinstance(valor, str):
        valor = valor.strip()
        return valor or None

    return valor


class MotivoRequest(BaseModel):
    motivo: str = Field(min_length=5, max_length=500)

    @field_validator("motivo", mode="before")
    @classmethod
    def limpiar_motivo(cls, valor):
        return _limpiar_texto(valor)


class ProductoCancelar(BaseModel):
    id_producto: int = Field(gt=0)
    cantidad: int | None = Field(
        default=None,
        gt=0,
        description="Unidades a cancelar. Si se omite, se cancelan todas."
    )


class CancelacionParcialRequest(MotivoRequest):
    productos: list[ProductoCancelar] = Field(min_length=1)

    @field_validator("productos")
    @classmethod
    def sin_repetidos(cls, productos):
        ids = [p.id_producto for p in productos]

        if len(ids) != len(set(ids)):
            raise ValueError("No repitas el mismo producto en la solicitud.")

        return productos


class RespuestaRequest(BaseModel):
    observacion: str | None = Field(default=None, max_length=500)


def _manejar_errores(error: Exception, contexto: str):
    if isinstance(error, HTTPException):
        return error

    if isinstance(error, UserNotActive):
        return HTTPException(status_code=403, detail=str(error))

    if isinstance(error, CancellationForbidden):
        return HTTPException(status_code=403, detail=str(error))

    if isinstance(error, (CancellationNotFound, OrderNotFound, SaleNotFound)):
        return HTTPException(status_code=404, detail=str(error))

    if isinstance(error, CancellationConflict):
        return HTTPException(status_code=409, detail=str(error))

    print(f"ERROR AL {contexto}:", repr(error))

    return HTTPException(
        status_code=500,
        detail=f"No fue posible {contexto.lower()}."
    )


@router.post("/pedidos/{id_pedido}/total", status_code=201)
def cancelar_total(
    id_pedido: int,
    datos: MotivoRequest,
    id_usuario: int = Depends(obtener_usuario_token)
):
    """
    Cancela todo el pedido. Las ventas no despachadas se cancelan de
    inmediato; las ya despachadas quedan como solicitud para el vendedor.
    """
    try:
        return cancelar_pedido_total(id_usuario, id_pedido, datos.motivo)

    except Exception as error:
        raise _manejar_errores(error, "CANCELAR EL PEDIDO")


@router.post("/pedidos/{id_pedido}/parcial", status_code=201)
def cancelar_parcial(
    id_pedido: int,
    datos: CancelacionParcialRequest,
    id_usuario: int = Depends(obtener_usuario_token)
):
    """
    Cancela algunos productos o algunas unidades del pedido.
    Solo aplica a productos que aún no han sido despachados.
    """
    try:
        productos = {p.id_producto: p.cantidad for p in datos.productos}

        return cancelar_pedido_parcial(
            id_usuario, id_pedido, datos.motivo, productos
        )

    except Exception as error:
        raise _manejar_errores(error, "CANCELAR LOS PRODUCTOS")


@router.post("/ventas/{id_venta}", status_code=201)
def cancelar_una_venta(
    id_venta: int,
    datos: MotivoRequest,
    id_usuario: int = Depends(obtener_usuario_token)
):
    """
    Cancela la parte de un vendedor. La puede usar el comprador
    (inmediata o como solicitud si ya se despachó) o el vendedor
    (solo antes de despachar).
    """
    try:
        return cancelar_venta(id_usuario, id_venta, datos.motivo)

    except Exception as error:
        raise _manejar_errores(error, "CANCELAR LA VENTA")


@router.post("/{id_cancelacion}/aprobar")
def aprobar(
    id_cancelacion: int,
    datos: RespuestaRequest | None = None,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return responder_solicitud(
            id_usuario, id_cancelacion, True,
            datos.observacion if datos else None
        )

    except Exception as error:
        raise _manejar_errores(error, "APROBAR LA CANCELACIÓN")


@router.post("/{id_cancelacion}/rechazar")
def rechazar(
    id_cancelacion: int,
    datos: RespuestaRequest | None = None,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return responder_solicitud(
            id_usuario, id_cancelacion, False,
            datos.observacion if datos else None
        )

    except Exception as error:
        raise _manejar_errores(error, "RECHAZAR LA CANCELACIÓN")


@router.get("/")
def mis_cancelaciones(
    rol: Literal["COMPRADOR", "VENDEDOR"] | None = Query(default=None),
    estado: Literal["SOLICITADA", "APROBADA", "RECHAZADA"] | None = Query(
        default=None
    ),
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return listar_cancelaciones(id_usuario, rol, estado)

    except Exception as error:
        raise _manejar_errores(error, "CONSULTAR LAS CANCELACIONES")


@router.get("/{id_cancelacion}")
def detalle_cancelacion(
    id_cancelacion: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return obtener_cancelacion(id_usuario, id_cancelacion)

    except Exception as error:
        raise _manejar_errores(error, "CONSULTAR LA CANCELACIÓN")
