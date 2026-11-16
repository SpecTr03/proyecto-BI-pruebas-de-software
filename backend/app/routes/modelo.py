"""Endpoint de importancia de variables del modelo entrenado."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import require_permission
from ..controllers.modelo_controller import (
    ModeloCorruptoError,
    ModeloNoEntrenadoError,
    ModeloSinImportanciasError,
    calcular_importancia,
)
from ..models.modelo import ModeloImportanciaResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/modelo",
    tags=["Modelo"],
    dependencies=[Depends(require_permission("dashboard:read"))],
)


@router.get(
    "/importancia",
    response_model=ModeloImportanciaResponse,
    summary="Importancia de variables del modelo XGBoost",
    responses={
        500: {"description": "Modelo corrupto o error interno"},
        501: {"description": "El modelo no expone feature_importances_"},
        503: {"description": "Modelo no entrenado"},
    },
)
def obtener_importancia() -> ModeloImportanciaResponse:
    """Devuelve el top 20 de variables más importantes del modelo.

    Raises:
        HTTPException: 503 si el modelo no está entrenado; 501 si el modelo
            no expone ``feature_importances_``; 500 si el artefacto está
            corrupto o falla el cálculo.
    """
    try:
        resultado = calcular_importancia()
    except ModeloNoEntrenadoError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ModeloSinImportanciasError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc
    except ModeloCorruptoError as exc:
        logger.exception("Modelo entrenado corrupto")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible cargar el modelo entrenado.",
        ) from exc
    except Exception as exc:
        logger.exception("Error inesperado calculando la importancia")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible calcular la importancia de las variables.",
        ) from exc

    return ModeloImportanciaResponse(**resultado)
