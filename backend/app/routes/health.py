"""Endpoint de salud de la API."""

from fastapi import APIRouter, HTTPException, status

from ..database import mongo_connection
from ..models.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Estado de la API y de MongoDB",
    responses={503: {"description": "MongoDB no disponible"}},
)
def health() -> HealthResponse:
    """Comprueba que la API esté activa y que MongoDB responda.

    Returns:
        ``{"status": "ok", "mongo": "connected"}`` si la conexión es exitosa.

    Raises:
        HTTPException: 503 si MongoDB no responde.
    """
    if not mongo_connection.ping():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "mongo": "disconnected"},
        )

    return HealthResponse(status="ok", mongo="connected")
