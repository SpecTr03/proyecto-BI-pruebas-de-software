"""Modelos Pydantic de entrada y salida."""

from .filtro import FiltroResponse
from .health import HealthResponse
from .kpi import (
    KpiCompetenciasResponse,
    KpiGlobalResponse,
    KpiResponse,
)
from .prediccion import PrediccionInput, PrediccionResponse
from .salud import SaludBDResponse

__all__ = [
    "FiltroResponse",
    "HealthResponse",
    "KpiCompetenciasResponse",
    "KpiGlobalResponse",
    "KpiResponse",
    "PrediccionInput",
    "PrediccionResponse",
    "SaludBDResponse",
]
