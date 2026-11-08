"""Comprobación de la integración con Neon Postgres."""

from fastapi import APIRouter, HTTPException, status

from ..neon_database import neon_database

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "/neon",
    summary="Comprueba la conexión con Neon Postgres",
    responses={503: {"description": "Neon Postgres no disponible"}},
)
def neon_health() -> dict[str, str]:
    """Ejecuta una consulta real contra la base de datos de Neon."""
    if not neon_database.ping():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "neon_postgres": "disconnected"},
        )
    return {"status": "ok", "neon_postgres": "connected"}
