"""Cálculo del puntaje global medio por estrato socioeconómico."""

import re
from typing import Any

from ..builders.query_builder import QueryBuilder
from ..models.grafica import DesempenoEstrato, EstratosResponse
from ..services.dashboard_summaries import get_dashboard_summary
from .kpi_controller import (
    FACT_COLLECTION,
    METRICAS_COMPETENCIAS,
    _ejecutar_agregacion,
    _obtener_database,
    _redondear,
)


def _normalizar_estrato(value: Any) -> str | None:
    match = re.search(r"\d+", str(value))
    if match is None:
        return None
    number = int(match.group())
    return f"Estrato {number}" if 1 <= number <= 6 else None


def calcular_desempeno_por_estrato() -> EstratosResponse:
    """Obtiene el promedio global de cada estrato entre 1 y 6."""
    pipeline = QueryBuilder().build_global_by_stratum(METRICAS_COMPETENCIAS)
    database = _obtener_database()
    result = get_dashboard_summary(database, "strata")
    if result is None:
        result = _ejecutar_agregacion(
            database,
            pipeline,
            FACT_COLLECTION,
        )

    totals: dict[str, tuple[float, int]] = {}
    for document in result:
        stratum = _normalizar_estrato(document.get("estrato"))
        average = document.get("promedio_global")
        count = int(document.get("total_registros", 0))
        if stratum is None or average is None or count <= 0:
            continue
        current_score_total, current_count = totals.get(stratum, (0.0, 0))
        totals[stratum] = (
            current_score_total + float(average) * count,
            current_count + count,
        )

    data = [
        DesempenoEstrato(
            estrato=f"Estrato {number}",
            promedio_global=_redondear(
                totals[f"Estrato {number}"][0] / totals[f"Estrato {number}"][1]
            ),
            total_registros=totals[f"Estrato {number}"][1],
        )
        for number in range(1, 7)
        if f"Estrato {number}" in totals
    ]
    return EstratosResponse(datos=data)
