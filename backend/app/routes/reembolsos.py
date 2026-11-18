from fastapi import APIRouter, Depends, HTTPException

from app.security import obtener_usuario_token
from app.services.carrito import UserNotActive
from app.services.reembolsos import listar_reembolsos, obtener_reembolso, RefundNotFound


router = APIRouter(
    prefix="/reembolsos",
    tags=["Reembolsos"]
)


@router.get("/")
def mis_reembolsos(
    id_pedido: int | None = None,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        reembolsos = listar_reembolsos(id_usuario, id_pedido)

        return {
            "total": len(reembolsos),
            "total_reembolsado": round(sum(r["valor"] for r in reembolsos if r["estado"] == "PROCESADO"), 2),
            "total_pendiente": round(sum(r["valor"] for r in reembolsos if r["estado"] == "PENDIENTE"), 2),
            "reembolsos": reembolsos
        }

    except UserNotActive as error:
        raise HTTPException(status_code=403, detail=str(error))

    except Exception as error:
        print("ERROR AL CONSULTAR LOS REEMBOLSOS:", repr(error))
        raise HTTPException(status_code=500, detail="No fue posible consultar los reembolsos.")


@router.get("/{id_reembolso}")
def detalle_reembolso(
    id_reembolso: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    try:
        return obtener_reembolso(id_usuario, id_reembolso)

    except RefundNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))

    except UserNotActive as error:
        raise HTTPException(status_code=403, detail=str(error))

    except Exception as error:
        print("ERROR AL CONSULTAR EL REEMBOLSO:", repr(error))
        raise HTTPException(status_code=500, detail="No fue posible consultar el reembolso.")
