"""Modelos para las series temporales del dashboard."""

from typing import Any, Literal

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


class ComparativoCompetenciasResponse(BaseModel):
    institucion: str
    grupo_referencia: str
    promedios_institucion: dict[str, float] = Field(default_factory=dict)
    promedios_nacionales: dict[str, float] = Field(default_factory=dict)
    total_institucion: int = Field(default=0, ge=0)
    total_nacional: int = Field(default=0, ge=0)


class InstitucionRanking(BaseModel):
    institucion: str
    promedio_global: float
    total_registros: int = Field(..., ge=0)


class RankingInstitucionesResponse(BaseModel):
    tipo: Literal["OFICIAL", "NO OFICIAL"]
    top: list[InstitucionRanking] = Field(default_factory=list)
    bottom: list[InstitucionRanking] = Field(default_factory=list)
