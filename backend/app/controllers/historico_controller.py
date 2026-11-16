"""Cálculo de la serie histórica del puntaje global."""

from typing import Any, Mapping

from ..builders.query_builder import QueryBuilder
from ..models.grafica import HistoricoResponse, PuntoHistorico
from .kpi_controller import (
    FACT_COLLECTION,
    METRICAS_COMPETENCIAS,
    _obtener_database,
    _ejecutar_agregacion,
    _redondear,
)


def calcular_historico(
    filtros: Mapping[str, Any],
    anio: str | None = None,
) -> HistoricoResponse:
    """Calcula el promedio global por año, aplicando los filtros del dashboard."""
    builder = (
        QueryBuilder()
        .filtrar_por_anio(anio)
        .filtrar_por_departamento(filtros.get("departamento"))
        .filtrar_por_municipio(filtros.get("municipio"))
        .filtrar_por_institucion(filtros.get("institucion"))
        .filtrar_por_caracter_institucion(filtros.get("caracter_institucion"))
        .filtrar_por_programa(filtros.get("programa"))
        .filtrar_por_metodo_programa(filtros.get("metodo_programa"))
        .filtrar_por_genero(filtros.get("genero"))
        .filtrar_por_estrato(filtros.get("estrato"))
        .filtrar_por_grupo_referencia(filtros.get("grupo_referencia"))
    )
    database = _obtener_database()
    result = _ejecutar_agregacion(
        database,
        builder.build_global_trend(METRICAS_COMPETENCIAS),
        FACT_COLLECTION,
    )

    return HistoricoResponse(
        puntos=[
            PuntoHistorico(
                anio=str(document["anio"]),
                promedio_global=_redondear(document.get("promedio_global")),
                total_registros=int(document.get("total_registros", 0)),
            )
            for document in result
            if document.get("anio") is not None
        ],
        filtros={**filtros, **({"anio": anio} if anio else {})},
    )
