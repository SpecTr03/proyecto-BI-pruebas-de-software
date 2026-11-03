"""Punto de entrada de la API REST con FastAPI.

Ejecución local:
    uvicorn app.main:app --reload --app-dir backend

Documentación interactiva:
    http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from .database import mongo_connection
from .routes.filtros import router as filtros_router
from .routes.health import router as health_router
from .routes.kpis import router as kpis_router
from .routes.prediccion import router as prediccion_router
from .routes.salud_bd import router as salud_bd_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Conecta a MongoDB al iniciar y cierra el cliente al apagar.

    Si MongoDB no está disponible, la API igualmente arranca para que
    ``/api/health`` pueda reportar el estado ``disconnected``.
    """
    try:
        # ``connect`` es bloqueante; se ejecuta en un hilo para no bloquear
        # el event loop durante el arranque.
        await asyncio.to_thread(mongo_connection.connect)
        logger.info("MongoDB disponible al iniciar la API")
    except Exception:
        logger.warning(
            "No se pudo conectar a MongoDB al iniciar; "
            "revisa MONGO_URI y MONGO_DATABASE",
            exc_info=True,
        )

    yield

    mongo_connection.close()
    logger.info("Aplicación finalizada")


app = FastAPI(
    title="SaberPro BI API",
    description=(
        "API REST para consultar la base de datos MongoDB SaberProDB, "
        "organizada con un Esquema de Estrella."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Rutas de la API.
app.include_router(health_router, prefix="/api")
app.include_router(kpis_router, prefix="/api")
app.include_router(filtros_router, prefix="/api")
app.include_router(prediccion_router, prefix="/api")
app.include_router(salud_bd_router, prefix="/api")


@app.get("/", tags=["Root"], summary="Información básica de la API")
def root() -> dict[str, str]:
    """Devuelve un mensaje de bienvenida y el enlace a la documentación."""
    return {
        "message": "SaberPro BI API",
        "docs": "/docs",
    }
