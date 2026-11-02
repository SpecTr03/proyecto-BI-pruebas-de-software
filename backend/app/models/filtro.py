"""Modelos Pydantic para los filtros del dashboard."""

from pydantic import BaseModel, Field


class FiltroResponse(BaseModel):
    """Valores únicos disponibles para poblar un dropdown de filtros."""

    valores: list[str] = Field(
        default_factory=list,
        description="Valores únicos ordenados alfabéticamente.",
        examples=[["20183", "20184", "20194"]],
    )
    total: int = Field(
        default=0,
        ge=0,
        description="Cantidad de valores únicos encontrados.",
        examples=[3],
    )
