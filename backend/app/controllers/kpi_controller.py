"""Lógica de negocio para el cálculo de KPIs."""

from __future__ import annotations

import bisect
import logging
from typing import Any, Mapping

from fastapi import HTTPException, status
from pymongo.database import Database
from pymongo.errors import PyMongoError

from ..builders.query_builder import QueryBuilder
from ..database import mongo_connection

logger = logging.getLogger(__name__)

FACT_COLLECTION = "Fact_Resultados"
DIM_TIME_COLLECTION = "Dim_Tiempo"
DEFAULT_METRIC = "mod_razona_cuantitat_punt"

# Alias de respuesta -> campo numérico en Fact_Resultados.
METRICAS_COMPETENCIAS: dict[str, str] = {
    "razonamiento": "mod_razona_cuantitat_punt",
    "lectura": "mod_lectura_critica_punt",
    "ciudadanas": "mod_competen_ciudada_punt",
    "escrita": "mod_comuni_escrita_punt",
    "ingles": "mod_ingles_punt",
}


def _construir_builder(filtros: Mapping[str, Any]) -> QueryBuilder:
    """Crea un ``QueryBuilder`` con todos los filtros opcionales del dashboard."""
    return (
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


def _obtener_database() -> Database:
    """Obtiene la base de datos o lanza un 503 si MongoDB no responde."""
    try:
        return mongo_connection.get_database()
    except (PyMongoError, ConnectionError) as exc:
        logger.exception("Error conectando con MongoDB")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible conectar con MongoDB.",
        ) from exc


def _ejecutar_agregacion(
    database: Database,
    pipeline: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Ejecuta un pipeline sobre ``Fact_Resultados`` con manejo de errores."""
    try:
        cursor = database[FACT_COLLECTION].aggregate(
            pipeline,
            allowDiskUse=True,
        )
        return list(cursor)
    except (PyMongoError, ConnectionError) as exc:
        logger.exception("Error consultando MongoDB")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible consultar MongoDB.",
        ) from exc


def _redondear(value: Any) -> float:
    """Convierte un valor numérico a ``float`` con dos decimales."""
    return round(float(value), 2) if value is not None else 0.0


def _obtener_periodo_anterior(
    database: Database,
    periodo_actual: str,
) -> str | None:
    """Obtiene el periodo inmediatamente anterior en ``Dim_Tiempo``."""
    try:
        raw_periodos = database[DIM_TIME_COLLECTION].distinct(
            "periodo",
            {"periodo": {"$ne": None}},
        )
    except (PyMongoError, ConnectionError) as exc:
        logger.exception("Error consultando periodos en Dim_Tiempo")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible consultar los periodos en MongoDB.",
        ) from exc

    periodos = sorted(
        {
            str(periodo).strip()
            for periodo in raw_periodos
            if periodo is not None and str(periodo).strip()
        }
    )
    indice = bisect.bisect_left(periodos, periodo_actual)
    if indice <= 0:
        return None
    return periodos[indice - 1]


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
    builder = _construir_builder(filtros)

    try:
        pipeline = builder.build_kpi(metrica)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    database = _obtener_database()
    result = _ejecutar_agregacion(database, pipeline)

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


def calcular_kpi_global(filtros: Mapping[str, Any]) -> dict[str, Any]:
    """Calcula el promedio global y su comparativo con el periodo anterior.

    El pipeline agrupa una sola vez y calcula los cinco promedios por
    competencia más el promedio global. Si se recibe ``periodo``, se ejecuta
    la misma agregación para el periodo inmediatamente anterior de
    ``Dim_Tiempo`` y se calcula la variación porcentual.

    Args:
        filtros: Diccionario con los filtros opcionales del dashboard.

    Returns:
        Diccionario compatible con ``KpiGlobalResponse``.

    Raises:
        HTTPException: 503 si MongoDB no responde o falla una consulta.
    """
    periodo_filtro = filtros.get("periodo")
    periodo_actual = (
        str(periodo_filtro).strip() if periodo_filtro is not None else None
    )
    if not periodo_actual:
        periodo_actual = None

    builder = _construir_builder(filtros)
    pipeline = builder.build_kpi_multi(METRICAS_COMPETENCIAS)

    database = _obtener_database()
    result = _ejecutar_agregacion(database, pipeline)

    if not result:
        return {
            "promedio_global": 0.0,
            "total_registros": 0,
            "periodo_actual": periodo_actual,
            "comparativo_porcentual": None,
        }

    document = result[0]
    promedio_actual = _redondear(document.get("promedio_global"))
    total_registros = int(document.get("total_registros", 0))
    comparativo: float | None = None

    if periodo_actual:
        periodo_anterior = _obtener_periodo_anterior(database, periodo_actual)
        if periodo_anterior:
            filtros_anteriores = dict(filtros)
            filtros_anteriores["periodo"] = periodo_anterior
            pipeline_anterior = _construir_builder(
                filtros_anteriores
            ).build_kpi_multi(METRICAS_COMPETENCIAS)
            result_anterior = _ejecutar_agregacion(database, pipeline_anterior)

            if result_anterior:
                promedio_anterior = _redondear(
                    result_anterior[0].get("promedio_global")
                )
                if promedio_anterior != 0:
                    comparativo = round(
                        (
                            (promedio_actual - promedio_anterior)
                            / promedio_anterior
                        )
                        * 100,
                        2,
                    )

    return {
        "promedio_global": promedio_actual,
        "total_registros": total_registros,
        "periodo_actual": periodo_actual,
        "comparativo_porcentual": comparativo,
    }


def calcular_kpi_competencias(
    filtros: Mapping[str, Any],
) -> dict[str, Any]:
    """Calcula los cinco promedios por competencia en una sola pasada.

    Args:
        filtros: Diccionario con los filtros opcionales del dashboard.

    Returns:
        Diccionario compatible con ``KpiCompetenciasResponse``.

    Raises:
        HTTPException: 503 si MongoDB no responde o falla la consulta.
    """
    builder = _construir_builder(filtros)
    pipeline = builder.build_kpi_multi(METRICAS_COMPETENCIAS)

    database = _obtener_database()
    result = _ejecutar_agregacion(database, pipeline)

    if not result:
        return {
            "razonamiento": 0.0,
            "lectura": 0.0,
            "ciudadanas": 0.0,
            "escrita": 0.0,
            "ingles": 0.0,
            "promedio_global": 0.0,
            "total_registros": 0,
        }

    document = result[0]
    return {
        "razonamiento": _redondear(document.get("razonamiento")),
        "lectura": _redondear(document.get("lectura")),
        "ciudadanas": _redondear(document.get("ciudadanas")),
        "escrita": _redondear(document.get("escrita")),
        "ingles": _redondear(document.get("ingles")),
        "promedio_global": _redondear(document.get("promedio_global")),
        "total_registros": int(document.get("total_registros", 0)),
    }
