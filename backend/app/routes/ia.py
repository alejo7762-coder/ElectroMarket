import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from app.ia import inspector
from app.routes.productos import ChecklistEstado
from app.security import obtener_usuario_token


router = APIRouter(
    prefix="/ia",
    tags=["Inteligencia artificial"]
)

METRICAS = Path(__file__).resolve().parents[3] / "docs" / "evidencias" / "ia" / "metricas_modelo.json"


class SolicitudInspeccion(BaseModel):
    """Borrador de publicación que el vendedor quiere revisar antes de publicar."""
    nombre: str = Field(default="", max_length=150)
    descripcion: str = Field(min_length=3, max_length=1000)
    descripcion_defectos: str | None = Field(default=None, max_length=1000)
    condicion: Literal["COMO_NUEVO", "BUENO", "ACEPTABLE"] | None = None
    checklist: ChecklistEstado | None = None

    @field_validator("nombre", "descripcion", "descripcion_defectos", mode="before")
    @classmethod
    def quitar_espacios(cls, valor):
        return valor.strip() if isinstance(valor, str) else valor


@router.post("/inspeccionar")
def inspeccionar_publicacion(
    datos: SolicitudInspeccion,
    id_usuario: int = Depends(obtener_usuario_token)
):
    """Analiza el borrador sin guardarlo. Al publicar, el análisis se guarda con el producto."""
    return inspector.analizar(
        datos.nombre,
        datos.descripcion,
        datos.descripcion_defectos,
        datos.checklist.model_dump() if datos.checklist else None,
        datos.condicion
    )


@router.get("/modelo")
def informacion_modelo():
    """Descripción del modelo y sus métricas (evidencia del servicio de IA)."""
    metricas = json.loads(METRICAS.read_text(encoding="utf-8")) if METRICAS.exists() else None

    return {
        "nombre": "Inspector de estado",
        "version": inspector.VERSION_MODELO,
        "tipo": "Clasificación de texto: regresión logística sobre TF-IDF (scikit-learn), ejecutada localmente",
        "entrada": "Título, descripción, defectos, checklist y condición declarada de la publicación",
        "salida": "Condición sugerida, confianza, coherencia (COHERENTE/REVISAR), alertas y expresiones clave",
        "clases": list(inspector.CONDICIONES),
        "metricas": metricas and {
            "fecha": metricas["fecha"],
            "ejemplos_entrenamiento": metricas["ejemplos_entrenamiento"],
            "exactitud_validacion_interna": metricas["validacion_interna"]["exactitud"],
            "exactitud_evaluacion_manual": metricas["evaluacion_manual"]["exactitud"],
            "coherencia": metricas["coherencia"],
        },
    }
