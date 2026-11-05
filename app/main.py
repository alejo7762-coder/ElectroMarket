from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

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


BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"
STORAGE_DIR = BASE_DIR / "storage"

# La carpeta de fotos debe existir antes de montarla
(STORAGE_DIR / "productos").mkdir(parents=True, exist_ok=True)


app = FastAPI(
    title="ElectroMarket API",
    description="API para la plataforma de compraventa de productos electrónicos.",
    version="1.0.0"
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
