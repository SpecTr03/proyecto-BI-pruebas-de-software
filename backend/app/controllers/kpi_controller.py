"""Lógica de negocio para el cálculo de KPIs."""

from __future__ import annotations

import bisect
import logging
from typing import Any, Mapping

from fastapi import HTTPException, status
from pymongo.database import Database
from pymongo.errors import PyMongoError

from ..builders.query_builder import (
    DIMENSION_LOOKUPS,
    DIMENSION_ORDER,
    QueryBuilder,
)
from ..constants import METRICAS_COMPETENCIAS
from ..database import mongo_connection

logger = logging.getLogger(__name__)

FACT_COLLECTION = "Fact_Resultados"
DIM_TIME_COLLECTION = "Dim_Tiempo"
DIM_ESTUDIANTE_COLLECTION = "Dim_Estudiante"
DEFAULT_METRIC = "mod_razona_cuantitat_punt"

ESTRATOS_VULNERABLES = frozenset({"Estrato 1", "Estrato 2"})
NIVELES_INGLES = ("-A1", "A1", "A2", "B1", "B2")
NORMALIZACION_NIVEL_INGLES = {
    "-a1": "-A1",
    "a1": "A1",
    "a2": "A2",
    "b1": "B1",
    "b2": "B2",
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


def _iter_condition_fields(condition: Mapping[str, Any]) -> list[str]:
    """Devuelve los campos referenciados por una condición del builder."""
    if "$or" in condition:
        fields: list[str] = []
        for branch in condition["$or"]:
            fields.extend(_iter_condition_fields(branch))
        return fields
    return [field for field in condition if not field.startswith("$")]


def _condition_dimension(condition: Mapping[str, Any]) -> str | None:
    """Identifica la dimensión referenciada por una condición del builder."""
    fields = _iter_condition_fields(condition)
    if not fields:
        return None

    field = fields[0]
    for dimension in DIMENSION_ORDER:
        prefix = f"{DIMENSION_LOOKUPS[dimension]['as']}."
        if field.startswith(prefix):
            return dimension
    return None


def _proyeccion_estudiante(
    conditions: list[dict[str, Any]],
) -> dict[str, int]:
    """Proyecta ``estrato`` y los campos usados por filtros de estudiante."""
    projection = {"_id": 1, "estrato": 1}
    prefix = f"{DIMENSION_LOOKUPS['estudiante']['as']}."

    for condition in conditions:
        for field in _iter_condition_fields(condition):
            if field.startswith(prefix):
                projection[field[len(prefix) :]] = 1

    return projection


def _lookup_estudiante(
    conditions: list[dict[str, Any]],
    local_field: str = "id_estudiante",
) -> dict[str, Any]:
    """Construye el ``$lookup`` de estudiante con proyección mínima."""
    return {
        "$lookup": {
            **DIMENSION_LOOKUPS["estudiante"],
            "localField": local_field,
            "pipeline": [
                {"$project": _proyeccion_estudiante(conditions)},
            ],
        }
    }


def _adaptar_condicion_dimension(
    condition: Mapping[str, Any],
    prefix: str,
) -> dict[str, Any]:
    """Quita el alias de una dimensión a una condición del builder."""
    if "$or" in condition:
        return {
            "$or": [
                _adaptar_condicion_dimension(branch, prefix)
                for branch in condition["$or"]
            ]
        }

    adaptada: dict[str, Any] = {}
    for field, value in condition.items():
        if field.startswith(prefix):
            field = field[len(prefix) :]
        adaptada[field] = value
    return adaptada


def _construir_pipeline_dim_estudiante(
    conditions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Agrega directo sobre ``Dim_Estudiante`` sin consultar hechos."""
    pipeline: list[dict[str, Any]] = []
    if conditions:
        prefix = f"{DIMENSION_LOOKUPS['estudiante']['as']}."
        pipeline.append(
            {
                "$match": {
                    "$and": [
                        _adaptar_condicion_dimension(condition, prefix)
                        for condition in conditions
                    ]
                }
            }
        )

    pipeline.append(
        {
            "$group": {
                "_id": "$estrato",
                "total": {"$sum": 1},
            }
        }
    )
    return pipeline


def _construir_pipeline_hechos(
    builder: QueryBuilder,
    fact_conditions: list[dict[str, Any]],
    dimension_conditions: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Filtra hechos, reduce IDs únicos y consulta estudiantes una sola vez."""
    pipeline: list[dict[str, Any]] = []
    if fact_conditions:
        pipeline.append({"$match": {"$and": fact_conditions}})

    for dimension in DIMENSION_ORDER:
        if dimension == "estudiante":
            continue
        if dimension not in builder._required_dimensions:
            continue

        pipeline.append({"$lookup": DIMENSION_LOOKUPS[dimension]})
        if dimension_conditions[dimension]:
            pipeline.append(
                {"$match": {"$and": dimension_conditions[dimension]}}
            )

    pipeline.append({"$project": {"id_estudiante": 1}})
    pipeline.append(
        {
            "$group": {
                "_id": "$id_estudiante",
                "total": {"$sum": 1},
            }
        }
    )
    pipeline.append(
        _lookup_estudiante(
            dimension_conditions["estudiante"],
            local_field="_id",
        )
    )
    if dimension_conditions["estudiante"]:
        pipeline.append(
            {"$match": {"$and": dimension_conditions["estudiante"]}}
        )

    pipeline.extend(
        [
            {
                "$unwind": {
                    "path": "$dim_estudiante",
                    "preserveNullAndEmptyArrays": True,
                }
            },
            {
                "$group": {
                    "_id": "$dim_estudiante.estrato",
                    "total": {"$sum": "$total"},
                }
            },
        ]
    )
    return pipeline


def _construir_pipeline_cobertura(
    builder: QueryBuilder,
) -> tuple[str, list[dict[str, Any]]]:
    """Elige la colección y el pipeline híbrido para el KPI de cobertura."""
    fact_conditions: list[dict[str, Any]] = []
    dimension_conditions: dict[str, list[dict[str, Any]]] = {
        dimension: [] for dimension in DIMENSION_ORDER
    }

    for condition in builder._conditions:
        dimension = _condition_dimension(condition)
        if dimension is None:
            fact_conditions.append(condition)
        else:
            dimension_conditions[dimension].append(condition)

    requiere_hechos = bool(fact_conditions) or any(
        dimension != "estudiante"
        and dimension in builder._required_dimensions
        for dimension in DIMENSION_ORDER
    )
    if requiere_hechos:
        return (
            FACT_COLLECTION,
            _construir_pipeline_hechos(
                builder,
                fact_conditions,
                dimension_conditions,
            ),
        )

    return (
        DIM_ESTUDIANTE_COLLECTION,
        _construir_pipeline_dim_estudiante(
            dimension_conditions["estudiante"],
        ),
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
    collection: str = FACT_COLLECTION,
) -> list[dict[str, Any]]:
    """Ejecuta un pipeline sobre la colección indicada con manejo de errores."""
    try:
        cursor = database[collection].aggregate(
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


def _normalizar_estrato(value: Any) -> str:
    """Normaliza el estrato agrupado por MongoDB."""
    if value is None:
        return "Sin estrato"
    texto = " ".join(str(value).split())
    if not texto or texto.casefold() == "sin estrato":
        return "Sin estrato"
    return texto


def _normalizar_nivel_ingles(value: Any) -> str | None:
    """Normaliza el nivel de inglés agrupado por MongoDB."""
    if value is None:
        return None
    texto = " ".join(str(value).split())
    if not texto:
        return None
    return NORMALIZACION_NIVEL_INGLES.get(texto.casefold(), texto)


def clasificar_desempeno(promedio: float) -> str:
    """Clasifica un promedio de competencia según la escala ICFES aproximada.

    Args:
        promedio: Puntaje promedio de una competencia.

    Returns:
        ``"Deficiente"`` si el promedio es menor que 120, ``"Aceptable"``
        si está entre 120 y 180 inclusive, o ``"Sobresaliente"`` si supera 180.
    """
    if promedio <= 120:
        return "Deficiente"
    if promedio <= 180:
        return "Aceptable"
    return "Sobresaliente"


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


def _calcular_kpi_por_periodo(
    database: Database,
    periodo: str,
) -> list[dict[str, Any]]:
    """Calcula el KPI filtrando hechos por la FK indexada de tiempo."""
    try:
        time_document = database[DIM_TIME_COLLECTION].find_one(
            {"periodo": periodo},
            {"_id": 1},
        )
    except (PyMongoError, ConnectionError) as exc:
        logger.exception("Error consultando el periodo %s", periodo)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible consultar los periodos en MongoDB.",
        ) from exc

    if not time_document:
        return []

    pipeline = (
        QueryBuilder()
        .filtrar_por_tiempo_id(time_document["_id"])
        .build_kpi_multi(METRICAS_COMPETENCIAS)
    )
    return _ejecutar_agregacion(database, pipeline)


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

    database = _obtener_database()
    only_period_filter = all(
        key == "periodo" or value in (None, "")
        for key, value in filtros.items()
    )
    if periodo_actual and only_period_filter:
        result = _calcular_kpi_por_periodo(database, periodo_actual)
    else:
        builder = _construir_builder(filtros)
        pipeline = builder.build_kpi_multi(METRICAS_COMPETENCIAS)
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
            if only_period_filter:
                result_anterior = _calcular_kpi_por_periodo(
                    database,
                    periodo_anterior,
                )
            else:
                pipeline_anterior = _construir_builder(
                    filtros_anteriores
                ).build_kpi_multi(METRICAS_COMPETENCIAS)
                result_anterior = _ejecutar_agregacion(
                    database,
                    pipeline_anterior,
                )

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

    Además de los promedios numéricos, devuelve un indicador cualitativo por
    competencia usando la escala ICFES aproximada de ``clasificar_desempeno``.

    Args:
        filtros: Diccionario con los filtros opcionales del dashboard.

    Returns:
        Diccionario compatible con ``KpiCompetenciasResponse``, incluyendo
        ``indicadores`` para razonamiento, lectura, ciudadanas, escrita e
        inglés.

    Raises:
        HTTPException: 503 si MongoDB no responde o falla la consulta.
    """
    builder = _construir_builder(filtros)
    pipeline = builder.build_kpi_multi(METRICAS_COMPETENCIAS)

    database = _obtener_database()
    result = _ejecutar_agregacion(database, pipeline)

    if not result:
        competencias = {nombre: 0.0 for nombre in METRICAS_COMPETENCIAS}
    else:
        document = result[0]
        competencias = {
            nombre: _redondear(document.get(nombre))
            for nombre in METRICAS_COMPETENCIAS
        }

    indicadores = {
        nombre: clasificar_desempeno(promedio)
        for nombre, promedio in competencias.items()
    }

    return {
        **competencias,
        "promedio_global": (
            _redondear(result[0].get("promedio_global")) if result else 0.0
        ),
        "total_registros": int(result[0].get("total_registros", 0)) if result else 0,
        "indicadores": indicadores,
    }


def calcular_kpi_cobertura(
    filtros: Mapping[str, Any],
) -> dict[str, Any]:
    """Calcula el total de evaluados y la cobertura de estratos 1 y 2.

    Usa ``Dim_Estudiante`` cuando no hay filtros de hechos y consulta
    ``Fact_Resultados`` solo cuando es necesario aplicar esos filtros.

    Args:
        filtros: Diccionario con los filtros opcionales del dashboard.

    Returns:
        Diccionario compatible con ``KpiCoberturaResponse``.

    Raises:
        HTTPException: 503 si MongoDB no responde o falla la consulta.
    """
    builder = _construir_builder(filtros)
    collection, pipeline = _construir_pipeline_cobertura(builder)

    database = _obtener_database()
    result = _ejecutar_agregacion(database, pipeline, collection)

    distribucion: dict[str, int] = {}
    for document in result:
        estrato = _normalizar_estrato(document.get("_id"))
        total = int(document.get("total", 0) or 0)
        distribucion[estrato] = distribucion.get(estrato, 0) + total

    total_registros = sum(distribucion.values())
    if total_registros == 0:
        return {
            "total_registros": 0,
            "porcentaje_estratos_1_2": 0.0,
            "distribucion_estratos": {},
        }

    registros_vulnerables = sum(
        total
        for estrato, total in distribucion.items()
        if estrato in ESTRATOS_VULNERABLES
    )
    porcentaje = round(
        (registros_vulnerables / total_registros) * 100,
        2,
    )

    return {
        "total_registros": total_registros,
        "porcentaje_estratos_1_2": porcentaje,
        "distribucion_estratos": dict(sorted(distribucion.items())),
    }


def calcular_kpi_ingles(
    filtros: Mapping[str, Any],
) -> dict[str, Any]:
    """Calcula la distribución de niveles de desempeño en inglés.

    Args:
        filtros: Diccionario con los filtros opcionales del dashboard.

    Returns:
        Diccionario compatible con ``KpiInglesResponse``. Los niveles
        desconocidos se conservan al final de la distribución para no fallar
        si aparecen valores nuevos en el dataset.

    Raises:
        HTTPException: 503 si MongoDB no responde o falla la consulta.
    """
    builder = _construir_builder(filtros)
    pipeline = builder._base_pipeline()
    pipeline.extend(
        [
            {"$match": {"mod_ingles_desem": {"$ne": None}}},
            {
                "$group": {
                    "_id": "$mod_ingles_desem",
                    "total": {"$sum": 1},
                }
            },
        ]
    )

    database = _obtener_database()
    result = _ejecutar_agregacion(database, pipeline)

    conteos: dict[str, int] = {}
    for document in result:
        nivel = _normalizar_nivel_ingles(document.get("_id"))
        if nivel is None:
            continue
        total = int(document.get("total", 0) or 0)
        conteos[nivel] = conteos.get(nivel, 0) + total

    total_registros = sum(conteos.values())
    if total_registros == 0:
        return {
            "total_registros": 0,
            "distribucion": {},
            "porcentajes": {},
            "porcentaje_b1_bplus": 0.0,
        }

    distribucion = {
        nivel: conteos[nivel]
        for nivel in NIVELES_INGLES
        if nivel in conteos
    }
    for nivel in sorted(set(conteos) - set(NIVELES_INGLES)):
        distribucion[nivel] = conteos[nivel]

    porcentajes = {
        nivel: round((total / total_registros) * 100, 2)
        for nivel, total in distribucion.items()
    }
    total_b1_b2 = distribucion.get("B1", 0) + distribucion.get("B2", 0)
    porcentaje_b1_bplus = round(
        (total_b1_b2 / total_registros) * 100,
        2,
    )

    return {
        "total_registros": total_registros,
        "distribucion": distribucion,
        "porcentajes": porcentajes,
        "porcentaje_b1_bplus": porcentaje_b1_bplus,
    }
