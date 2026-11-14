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


class KpiGlobalResponse(BaseModel):
    """KPI global y comparativo contra el periodo inmediatamente anterior."""

    promedio_global: float = Field(
        ...,
        examples=[148.72],
        description=(
            "Promedio global calculado como la suma de los cinco promedios "
            "de competencias dividida entre cinco."
        ),
    )
    total_registros: int = Field(
        ...,
        ge=0,
        examples=[1209063],
        description="Cantidad de registros que coincidieron con los filtros.",
    )
    periodo_actual: str | None = Field(
        default=None,
        examples=["20225"],
        description="Periodo consultado; ``None`` si no se aplicó ese filtro.",
    )
    comparativo_porcentual: float | None = Field(
        default=None,
        examples=[2.45],
        description=(
            "Variación porcentual del promedio global frente al periodo "
            "anterior; ``None`` si no hay periodo o datos comparables."
        ),
    )


class KpiCompetenciasResponse(BaseModel):
    """Promedios por competencia y promedio global en una sola consulta."""

    razonamiento: float = Field(
        ...,
        examples=[150.2],
        description="Promedio de razonamiento cuantitativo.",
    )
    lectura: float = Field(
        ...,
        examples=[151.4],
        description="Promedio de lectura crítica.",
    )
    ciudadanas: float = Field(
        ...,
        examples=[145.8],
        description="Promedio de competencias ciudadanas.",
    )
    escrita: float = Field(
        ...,
        examples=[146.3],
        description="Promedio de comunicación escrita.",
    )
    ingles: float = Field(
        ...,
        examples=[149.9],
        description="Promedio de inglés.",
    )
    promedio_global: float = Field(
        ...,
        examples=[148.72],
        description="Promedio de los cinco promedios por competencia.",
    )
    total_registros: int = Field(
        ...,
        ge=0,
        examples=[1209063],
        description="Cantidad de registros que coincidieron con los filtros.",
    )
    indicadores: dict[str, str] = Field(
        ...,
        examples=[
            {
                "razonamiento": "Aceptable",
                "lectura": "Aceptable",
                "ciudadanas": "Aceptable",
                "escrita": "Aceptable",
                "ingles": "Aceptable",
            }
        ],
        description=(
            "Indicador cualitativo por competencia según la escala ICFES "
            "aproximada: Deficiente (menor que 120), Aceptable (120-180) "
            "o Sobresaliente (mayor que 180)."
        ),
    )
    indicadores: dict[str, str] = Field(
        ...,
        examples=[
            {
                "razonamiento": "Aceptable",
                "lectura": "Aceptable",
                "ciudadanas": "Aceptable",
                "escrita": "Aceptable",
                "ingles": "Aceptable",
            }
        ],
        description=(
            "Indicador cualitativo por competencia según la escala ICFES "
            "aproximada: Deficiente (menor que 120), Aceptable (120-180) "
            "o Sobresaliente (mayor que 180)."
        ),
    )
