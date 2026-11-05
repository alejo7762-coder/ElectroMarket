from fastapi import FastAPI
from app.routes import usuarios
from app.routes import productos
from app.routes import carrito

app = FastAPI(
    title="ElectroMarket API",
    description="API para la plataforma de compraventa de productos electrónicos.",
    version="1.0.0"
)

app.include_router(usuarios.router)
app.include_router(productos.router)
app.include_router(carrito.router)

@app.get("/")
def inicio():
    return {
        "mensaje": "Bienvenido a la API de ElectroMarket",
        "estado": "Funcionando"
    }


@app.get("/estado")
def estado():
    return {
        "proyecto": "ElectroMarket",
        "estado": "Activo"
    }