import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.errores import ErrorAplicacion

from app.routes import usuarios
from app.routes import productos
from app.routes import mis_productos
from app.routes import categorias
from app.routes import carrito
from app.routes import pedidos
from app.routes import envios
from app.routes import direcciones
from app.routes import pagos
from app.routes import ventas
from app.routes import cancelaciones
from app.routes import reembolsos
from app.routes import ia
from app.routes import resenas


# backend/ (contiene app/ y storage/) y raíz del repositorio (contiene frontend/)
BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR.parent / "frontend"
STORAGE_DIR = BASE_DIR / "storage"

# La carpeta de fotos debe existir antes de montarla
(STORAGE_DIR / "productos").mkdir(parents=True, exist_ok=True)


app = FastAPI(
    title="ElectroMarket API",
    description="API para la plataforma de compraventa de productos electrónicos.",
    version="1.0.0"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("electromarket")


@app.exception_handler(ErrorAplicacion)
def manejar_error_aplicacion(request: Request, error: ErrorAplicacion):
    """Errores de negocio: cada clase define su código HTTP."""
    return JSONResponse(status_code=error.status_code, content={"detail": error.detalle})


@app.exception_handler(Exception)
def manejar_error_inesperado(request: Request, error: Exception):
    """Errores no previstos: se registran y el cliente recibe un 500 genérico."""
    logger.exception("Error en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Ocurrió un error interno. Intenta de nuevo más tarde."}
    )


app.include_router(usuarios.router)
app.include_router(productos.router)
app.include_router(mis_productos.router)
app.include_router(categorias.router)
app.include_router(carrito.router)
app.include_router(pedidos.router)
app.include_router(envios.router)
app.include_router(direcciones.router)
app.include_router(pagos.router)
app.include_router(ventas.router)
app.include_router(cancelaciones.router)
app.include_router(reembolsos.router)
app.include_router(ia.router)
app.include_router(ia.router_precio)
app.include_router(resenas.router)


@app.get("/", include_in_schema=False)
def inicio():
    # La raíz abre la tienda; la API sigue documentada en /docs
    return RedirectResponse(url="/web/")


@app.get("/estado")
def estado():
    return {
        "proyecto": "ElectroMarket",
        "estado": "Activo"
    }


# Fotos de los productos (las rutas guardadas en la BD empiezan por storage/)
app.mount(
    "/storage",
    StaticFiles(directory=STORAGE_DIR),
    name="storage"
)

# Interfaz gráfica
app.mount(
    "/web",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="web"
)
