"""Modelos Pydantic para las respuestas de KPIs."""

from typing import Any

from pydantic import BaseModel, Field


class KpiResponse(BaseModel):
    """Resultado de un KPI calculado sobre ``Fact_Resultados``."""

    metric: str = Field(
        ...,
        examples=["mod_razona_cuantitat_punt"],
        description="Métrica numérica consultada.",
    )
    value: float | None = Field(
        default=None,
        examples=[152.34],
        description="Promedio de la métrica; ``None`` si no hay datos.",
    )
    total_records: int = Field(
        default=0,
        ge=0,
        examples=[1209063],
        description="Cantidad de registros que coincidieron con los filtros.",
    )
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Filtros aplicados en la consulta.",
    )
