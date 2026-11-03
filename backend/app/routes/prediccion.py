"""Endpoint para predecir el puntaje global de Saber Pro."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from ..controllers.prediccion_controller import (
    ModeloNoDisponibleError,
    predecir,
)
from ..models.prediccion import PrediccionInput, PrediccionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predecir", tags=["Predicción"])


@router.post(
    "",
    response_model=PrediccionResponse,
    summary="Predice el puntaje global de un estudiante",
    responses={
        500: {"description": "Error interno al generar la predicción"},
        503: {"description": "Modelo de predicción no disponible"},
    },
)
def predecir_puntaje(input_data: PrediccionInput) -> PrediccionResponse:
    """Predice el puntaje global a partir de los datos del estudiante.

    Args:
        input_data: Datos socioeconómicos y académicos del estudiante.

    Returns:
        ``PrediccionResponse`` con el puntaje estimado y su nivel de desempeño.

    Raises:
        HTTPException: 503 si el artefacto del modelo no existe o no se puede
            cargar; 500 si ocurre un error durante la predicción.
    """
    try:
        resultado = predecir(input_data.model_dump())
    except ModeloNoDisponibleError as exc:
        logger.error("Modelo de predicción no disponible: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Error inesperado generando la predicción")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible generar la predicción con el modelo.",
        ) from exc

    return PrediccionResponse(**resultado)
