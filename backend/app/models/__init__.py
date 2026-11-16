"""Modelos Pydantic de entrada y salida."""

from .filtro import FiltroResponse
from .grafica import (
    ComparativoCompetenciasResponse,
    DesempenoEstrato,
    EstratosResponse,
    HistoricoResponse,
    InstitucionRanking,
    PuntoHistorico,
    RankingInstitucionesResponse,
)
from .health import HealthResponse
from .kpi import (
    KpiCoberturaResponse,
    KpiCompetenciasResponse,
    KpiGlobalResponse,
    KpiResponse,
)
from .modelo import ImportanciaVariable, ModeloImportanciaResponse
from .prediccion import PrediccionInput, PrediccionResponse
from .salud import SaludBDResponse

__all__ = [
    "FiltroResponse",
    "ComparativoCompetenciasResponse",
    "DesempenoEstrato",
    "EstratosResponse",
    "HealthResponse",
    "HistoricoResponse",
    "ImportanciaVariable",
    "InstitucionRanking",
    "KpiCoberturaResponse",
    "KpiCompetenciasResponse",
    "KpiGlobalResponse",
    "KpiResponse",
    "ModeloImportanciaResponse",
    "PrediccionInput",
    "PrediccionResponse",
    "PuntoHistorico",
    "RankingInstitucionesResponse",
    "SaludBDResponse",
]
