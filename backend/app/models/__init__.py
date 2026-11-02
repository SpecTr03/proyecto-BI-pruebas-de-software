"""Modelos Pydantic de entrada y salida."""

from .health import HealthResponse
from .kpi import KpiResponse

__all__ = ["HealthResponse", "KpiResponse"]
