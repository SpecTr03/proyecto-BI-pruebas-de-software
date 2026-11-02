"""Lógica de negocio para el cálculo de KPIs."""

from __future__ import annotations

import logging
from typing import Any, Mapping

from fastapi import HTTPException, status
from pymongo.errors import PyMongoError

from ..builders.query_builder import QueryBuilder
from ..database import mongo_connection

logger = logging.getLogger(__name__)

FACT_COLLECTION = "Fact_Resultados"
DEFAULT_METRIC = "mod_razona_cuantitat_punt"


def calcular_kpi(
    filtros: Mapping[str, Any],
    metrica: str = DEFAULT_METRIC,
) -> dict[str, Any]:
    """Calcula el promedio de una métrica aplicando los filtros recibidos.

    Args:
        filtros: Diccionario con los filtros opcionales del dashboard.
        metrica: Métrica numérica de ``Fact_Resultados``.

    Returns:
        Diccionario compatible con ``KpiResponse``.

    Raises:
        HTTPException: 400 si la métrica no es válida o 503 si MongoDB falla.
    """
    builder = (
        QueryBuilder()
        .filtrar_por_periodo(filtros.get("periodo"))
        .filtrar_por_departamento(filtros.get("departamento"))
        .filtrar_por_municipio(filtros.get("municipio"))
        .filtrar_por_institucion(filtros.get("institucion"))
        .filtrar_por_caracter_institucion(filtros.get("caracter_institucion"))
        .filtrar_por_programa(filtros.get("programa"))
        .filtrar_por_metodo_programa(filtros.get("metodo_programa"))
        .filtrar_por_genero(filtros.get("genero"))
        .filtrar_por_estrato(filtros.get("estrato"))
        .filtrar_por_grupo_referencia(filtros.get("grupo_referencia"))
        .filtrar_por_internet(filtros.get("internet"))
        .filtrar_por_computador(filtros.get("computador"))
        .filtrar_por_departamento_examen(filtros.get("departamento_examen"))
        .filtrar_por_municipio_examen(filtros.get("municipio_examen"))
    )

    try:
        pipeline = builder.build_kpi(metrica)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    try:
        database = mongo_connection.get_database()
        cursor = database[FACT_COLLECTION].aggregate(
            pipeline,
            allowDiskUse=True,
        )
        result = list(cursor)
    except (PyMongoError, ConnectionError) as exc:
        logger.exception("Error consultando MongoDB")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible consultar MongoDB.",
        ) from exc

    if not result:
        return {
            "metric": metrica,
            "value": None,
            "total_records": 0,
            "filters": dict(filtros),
        }

    document = result[0]
    value = document.get("value")
    total_records = int(document.get("total_records", 0))

    return {
        "metric": metrica,
        "value": round(float(value), 2) if value is not None else None,
        "total_records": total_records,
        "filters": dict(filtros),
    }
