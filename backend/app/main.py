"""Punto de entrada de la API FastAPI de Ho smartvision."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import (
    app_users,
    auth,
    cameras,
    clients,
    events,
    gateways,
    onvif,
    properties,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Valida que la configuración crítica esté presente al arrancar.
    get_settings()
    yield


app = FastAPI(
    title="Ho smartvision API",
    description="Backend de gestión de cámaras CCTV (ONVIF, eventos, multi-cliente).",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Healthcheck simple para Railway/Render."""
    return {"status": "ok", "environment": settings.environment}


# Registro de routers
app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(properties.router)
app.include_router(gateways.router)
app.include_router(cameras.router)
app.include_router(events.router)
app.include_router(onvif.router)
app.include_router(app_users.router)
