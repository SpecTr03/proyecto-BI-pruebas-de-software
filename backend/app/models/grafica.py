"""Modelos para las series temporales del dashboard."""

from typing import Any

from pydantic import BaseModel, Field


class PuntoHistorico(BaseModel):
    anio: str = Field(..., examples=["2018"])
    promedio_global: float = Field(..., examples=[148.72])
    total_registros: int = Field(..., ge=0, examples=[250000])


class HistoricoResponse(BaseModel):
    puntos: list[PuntoHistorico] = Field(default_factory=list)
    filtros: dict[str, Any] = Field(default_factory=dict)


class DesempenoEstrato(BaseModel):
    estrato: str = Field(..., examples=["Estrato 2"])
    promedio_global: float = Field(..., examples=[148.72])
    total_registros: int = Field(..., ge=0, examples=[250000])


class EstratosResponse(BaseModel):
    datos: list[DesempenoEstrato] = Field(default_factory=list)
