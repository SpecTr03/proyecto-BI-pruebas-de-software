"""Modelos Pydantic para la proyección de crecimiento."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProyeccionCrecimientoResponse(BaseModel):
    """Proyección del promedio global para el siguiente periodo."""

    periodo_actual: str = Field(
        ...,
        description="Periodo más reciente con datos (ej. '20226').",
    )
    promedio_actual: float = Field(
        ...,
        ge=0,
        le=300,
        description="Promedio global del periodo actual.",
    )
    periodo_proyectado: str = Field(
        ...,
        description="Periodo estimado (ej. '20231').",
    )
    promedio_proyectado: float = Field(
        ...,
        ge=0,
        le=300,
        description="Promedio global proyectado para el próximo periodo.",
    )
    tasa_crecimiento_porcentual: float = Field(
        ...,
        description=(
            "Variación esperada en porcentaje "
            "(positivo = crecimiento, negativo = declive)."
        ),
    )
    metodo: str = Field(
        ...,
        description="Método usado: 'promedio_movil' o 'regresion_lineal'.",
    )
    periodos_analizados: int = Field(
        ...,
        ge=1,
        description="Cantidad de periodos usados para la proyección.",
    )
    historico: list[dict] = Field(
        ...,
        description="Lista de {periodo, promedio} del histórico usado.",
    )
