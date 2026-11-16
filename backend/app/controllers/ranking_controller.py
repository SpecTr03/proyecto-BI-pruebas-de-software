"""Cálculo de rankings Top/Bottom de instituciones por tipo."""

from typing import Literal

from fastapi import HTTPException, status

from ..builders.query_builder import QueryBuilder
from ..models.grafica import RankingInstitucionesResponse, InstitucionRanking
from .kpi_controller import (
    FACT_COLLECTION,
    METRICAS_COMPETENCIAS,
    _ejecutar_agregacion,
    _obtener_database,
    _redondear,
)


TipoInstitucion = Literal["OFICIAL", "NO OFICIAL"]


def calcular_ranking_instituciones(
    tipo: TipoInstitucion,
) -> RankingInstitucionesResponse:
    """Calcula los diez puntajes globales más altos y más bajos por tipo de IES."""
    normalized_type = tipo.strip().upper()
    if normalized_type not in {"OFICIAL", "NO OFICIAL"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El tipo debe ser OFICIAL o NO OFICIAL.",
        )

    builder = QueryBuilder().filtrar_por_tipo_institucion(normalized_type)
    rows = _ejecutar_agregacion(
        _obtener_database(),
        builder.build_institution_ranking(METRICAS_COMPETENCIAS),
        FACT_COLLECTION,
    )
    result = rows[0] if rows else {}

    def ranking(items: list[dict]) -> list[InstitucionRanking]:
        return [
            InstitucionRanking(
                institucion=str(item["institucion"]),
                promedio_global=_redondear(item.get("promedio_global")),
                total_registros=int(item.get("total_registros", 0)),
            )
            for item in items
            if item.get("institucion") is not None
        ]

    return RankingInstitucionesResponse(
        tipo=normalized_type,
        top=ranking(result.get("top", [])),
        bottom=ranking(result.get("bottom", [])),
    )
