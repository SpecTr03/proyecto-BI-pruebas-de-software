"""Modelos Pydantic de entrada y salida."""

from .filtro import FiltroResponse
from .grafica import (
    DesempenoEstrato,
    EstratosResponse,
    HistoricoResponse,
    PuntoHistorico,
)
from .health import HealthResponse
from .kpi import (
    KpiCoberturaResponse,
    KpiCompetenciasResponse,
    KpiGlobalResponse,
    KpiResponse,
)
from .prediccion import PrediccionInput, PrediccionResponse
from .salud import SaludBDResponse

__all__ = [
    "FiltroResponse",
    "DesempenoEstrato",
    "EstratosResponse",
    "HealthResponse",
    "HistoricoResponse",
    "KpiCoberturaResponse",
    "KpiCompetenciasResponse",
    "KpiGlobalResponse",
    "KpiResponse",
    "PrediccionInput",
    "PrediccionResponse",
    "PuntoHistorico",
    "SaludBDResponse",
]
