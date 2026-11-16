"""Modelos Pydantic para la importancia de variables del modelo."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ImportanciaVariable(BaseModel):
    """Importancia relativa de una variable del modelo."""

    variable: str = Field(
        ...,
        description=(
            "Nombre limpio de la variable (sin prefijos cat__/num__)."
        ),
    )
    importancia: float = Field(
        ...,
        ge=0,
        le=1,
        description="Importancia relativa de la variable (0-1).",
    )


class ModeloImportanciaResponse(BaseModel):
    """Importancia de las variables del modelo entrenado."""

    top_variable: str = Field(
        ...,
        description="Nombre limpio de la variable más importante.",
    )
    top_importancia: float = Field(
        ...,
        ge=0,
        le=1,
        description="Importancia de la variable más importante.",
    )
    ranking: list[ImportanciaVariable] = Field(
        ...,
        description=(
            "Top 20 de variables ordenadas por importancia descendente."
        ),
    )
    total_features: int = Field(
        ...,
        ge=1,
        description="Total de features del modelo.",
    )
