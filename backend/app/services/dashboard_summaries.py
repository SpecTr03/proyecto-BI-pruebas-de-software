"""Generación y lectura de agregados estáticos del dashboard."""

import logging
from datetime import datetime, timezone
from typing import Any

from pymongo.database import Database

from ..builders.query_builder import QueryBuilder
from ..constants import METRICAS_COMPETENCIAS

SUMMARY_COLLECTION = "Dashboard_Summaries"
FACT_COLLECTION = "Fact_Resultados"
logger = logging.getLogger(__name__)
SUMMARY_PIPELINES = {
    "historical": QueryBuilder().build_global_trend(METRICAS_COMPETENCIAS),
    "strata": QueryBuilder().build_global_by_stratum(METRICAS_COMPETENCIAS),
    "ranking:OFICIAL": (
        QueryBuilder()
        .filtrar_por_tipo_institucion("OFICIAL")
        .build_institution_ranking(METRICAS_COMPETENCIAS)
    ),
    "ranking:NO OFICIAL": (
        QueryBuilder()
        .filtrar_por_tipo_institucion("NO OFICIAL")
        .build_institution_ranking(METRICAS_COMPETENCIAS)
    ),
}


def get_dashboard_summary(database: Database, key: str) -> Any | None:
    """Devuelve el resultado precalculado o ``None`` si aún no existe."""
    document = database[SUMMARY_COLLECTION].find_one(
        {"_id": key},
        {"data": 1},
    )
    return document.get("data") if document else None


def refresh_dashboard_summaries(
    database: Database,
    fact_collection: str = FACT_COLLECTION,
) -> dict[str, int]:
    """Recalcula y reemplaza los resúmenes luego de una carga de datos."""
    summaries = database[SUMMARY_COLLECTION]
    generated_at = datetime.now(timezone.utc)
    source_count = database[fact_collection].estimated_document_count()
    result_counts: dict[str, int] = {}

    for key, pipeline in SUMMARY_PIPELINES.items():
        logger.info("Calculating dashboard summary '%s'.", key)
        rows = list(
            database[fact_collection].aggregate(
                pipeline,
                allowDiskUse=True,
            )
        )
        data: Any = rows
        if key.startswith("ranking:"):
            data = rows[0] if rows else {"top": [], "bottom": []}

        summaries.replace_one(
            {"_id": key},
            {
                "_id": key,
                "data": data,
                "generated_at": generated_at,
                "source_count": source_count,
            },
            upsert=True,
        )
        result_counts[key] = (
            len(data) if isinstance(data, list) else len(data.get("top", []))
        )
        logger.info("Dashboard summary '%s' refreshed.", key)

    return result_counts
