"""Endpoint de proyección de crecimiento del promedio global."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth import require_permission
from ..controllers.proyeccion_controller import calcular_proyeccion_crecimiento
from ..models.proyeccion import ProyeccionCrecimientoResponse

router = APIRouter(
    prefix="/proyeccion",
    tags=["Proyección"],
    dependencies=[Depends(require_permission("dashboard:read"))],
)


@router.get(
    "/crecimiento",
    response_model=ProyeccionCrecimientoResponse,
    summary="Proyección de crecimiento del promedio global",
    responses={
        400: {"description": "Histórico insuficiente para la proyección"},
        422: {"description": "Método de proyección no válido"},
        503: {"description": "MongoDB no disponible o error de consulta"},
    },
)
def obtener_proyeccion_crecimiento(
    metodo: Literal["promedio_movil", "regresion_lineal"] = Query(
        default="promedio_movil",
        description=(
            "Método de proyección: 'promedio_movil' (últimos 3 periodos) "
            "o 'regresion_lineal' (tendencia histórica)."
        ),
    ),
) -> ProyeccionCrecimientoResponse:
    """Proyecta el promedio global del siguiente periodo.

    Raises:
        HTTPException: 400 si el histórico no alcanza para el método; 503 si
            MongoDB no responde o falla la agregación.
    """
    try:
        resultado = calcular_proyeccion_crecimiento(metodo)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ProyeccionCrecimientoResponse(**resultado)
