import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import usuario, producto, proveedor, inventario
from app.models import movimiento_inventario, venta, detalle_venta, reporte

from app.routes import auth, dashboard, inventario, productos, proveedores, reportes, usuarios, ventas

load_dotenv()

app = FastAPI(title="STOCK MX API")

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,"
        "http://127.0.0.1:3000,http://127.0.0.1:5173,"
        "http://localhost:5500,http://127.0.0.1:5500",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(productos.router)
app.include_router(proveedores.router)
app.include_router(inventario.router)
app.include_router(ventas.router)
app.include_router(usuarios.router)
app.include_router(reportes.router)


@app.get("/")
def inicio():
    return {"mensaje": "STOCK MX API funcionando correctamente"}
