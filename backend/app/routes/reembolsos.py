from fastapi import APIRouter, Depends

from app.security import obtener_usuario_token
from app.services.reembolsos import listar_reembolsos, obtener_reembolso


router = APIRouter(
    prefix="/reembolsos",
    tags=["Reembolsos"]
)


@router.get("/")
def mis_reembolsos(
    id_pedido: int | None = None,
    id_usuario: int = Depends(obtener_usuario_token)
):
    reembolsos = listar_reembolsos(id_usuario, id_pedido)

    return {
        "total": len(reembolsos),
        "total_reembolsado": round(sum(r["valor"] for r in reembolsos if r["estado"] == "PROCESADO"), 2),
        "total_pendiente": round(sum(r["valor"] for r in reembolsos if r["estado"] == "PENDIENTE"), 2),
        "reembolsos": reembolsos
    }


@router.get("/{id_reembolso}")
def detalle_reembolso(
    id_reembolso: int,
    id_usuario: int = Depends(obtener_usuario_token)
):
    return obtener_reembolso(id_usuario, id_reembolso)
