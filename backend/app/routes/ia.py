import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from app.ia import inspector, precio
from app.routes.productos import ChecklistEstado
from app.security import obtener_usuario_token


router = APIRouter(
    prefix="/ia",
    tags=["Inteligencia artificial"]
)

EVIDENCIAS = Path(__file__).resolve().parents[3] / "docs" / "evidencias" / "ia"
METRICAS = EVIDENCIAS / "metricas_modelo.json"
METRICAS_PRECIO = EVIDENCIAS / "metricas_precio.json"

# El precio sugerido se expone en /productos, como se definió en el Documento Maestro
router_precio = APIRouter(prefix="/productos", tags=["Inteligencia artificial"])


class SolicitudPrecio(BaseModel):
    """Características del artículo para estimar su precio de mercado."""
    categoria: str = Field(min_length=2, max_length=80, description="Nombre de la categoría")
    antiguedad_meses: int = Field(ge=0, le=240)
    condicion: Literal["COMO_NUEVO", "BUENO", "ACEPTABLE"]
    incluye_caja: bool = False
    garantia_vigente: bool = False
    precio_nuevo: float = Field(ge=50_000, le=50_000_000, description="Precio del artículo nuevo, en COP")


@router_precio.post("/precio-sugerido")
def precio_sugerido(
    datos: SolicitudPrecio,
    id_usuario: int = Depends(obtener_usuario_token)
):
    """Red neuronal 9-6-1: precio sugerido y rango ±10 %. Es consultivo; no se guarda."""
    return precio.sugerir(
        datos.categoria, datos.antiguedad_meses, datos.condicion,
        datos.incluye_caja, datos.garantia_vigente, datos.precio_nuevo
    )


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
    """Descripción de los servicios de IA y sus métricas (evidencia)."""
    metricas = json.loads(METRICAS.read_text(encoding="utf-8")) if METRICAS.exists() else None
    metricas_precio = json.loads(METRICAS_PRECIO.read_text(encoding="utf-8")) if METRICAS_PRECIO.exists() else None

    return {
        "servicios": [
            {
                "nombre": "Precio sugerido",
                "version": precio.VERSION_MODELO,
                "endpoint": "POST /productos/precio-sugerido",
                "tipo": "Red neuronal perceptrón multicapa 9-6-1 (ReLU, salida sigmoide), scikit-learn, local",
                "entrada": "Categoría, antigüedad, condición, caja y accesorios, garantía y precio nuevo",
                "salida": "Proporción r, precio sugerido y rango ±10 %, efecto de cada característica",
                "metricas": metricas_precio and {
                    "fecha": metricas_precio["fecha"],
                    "parametros_red": metricas_precio["parametros_red"],
                    "comparacion": metricas_precio["comparacion"],
                    "red_supera_lineas_base": metricas_precio["red_supera_lineas_base"],
                },
            },
            {
                "nombre": "Inspector de estado",
                "version": inspector.VERSION_MODELO,
                "endpoint": "POST /ia/inspeccionar",
                "tipo": "Clasificación de texto: regresión logística sobre TF-IDF (scikit-learn), local",
                "entrada": "Título, descripción, defectos, checklist y condición declarada",
                "salida": "Condición sugerida, confianza, coherencia (COHERENTE/REVISAR), alertas y expresiones clave",
                "clases": list(inspector.CONDICIONES),
                "metricas": metricas and {
                    "fecha": metricas["fecha"],
                    "ejemplos_entrenamiento": metricas["ejemplos_entrenamiento"],
                    "exactitud_validacion_interna": metricas["validacion_interna"]["exactitud"],
                    "exactitud_evaluacion_manual": metricas["evaluacion_manual"]["exactitud"],
                    "coherencia": metricas["coherencia"],
                },
            },
        ]
    }
