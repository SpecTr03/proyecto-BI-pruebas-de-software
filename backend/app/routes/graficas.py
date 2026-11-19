"""Endpoints de series y gráficas descriptivas."""

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query

from ..auth import require_permission
from ..controllers.comparativo_controller import calcular_comparativo_competencias
from ..controllers.distribucion_controller import calcular_distribucion_departamental
from ..controllers.estrato_controller import calcular_desempeno_por_estrato
from ..controllers.historico_controller import calcular_historico
from ..controllers.ranking_controller import calcular_ranking_instituciones
from ..models.grafica import (
    ComparativoCompetenciasResponse,
    DistribucionDepartamentalResponse,
    EstratosResponse,
    HistoricoResponse,
    RankingInstitucionesResponse,
)

router = APIRouter(
    prefix="/graficas",
    tags=["Gráficas"],
    dependencies=[Depends(require_permission("dashboard:read"))],
)


@router.get(
    "/historico",
    response_model=HistoricoResponse,
    summary="Promedio global histórico por año",
    responses={503: {"description": "MongoDB no disponible"}},
)
def get_historico(
    anio: int | None = Query(default=None, ge=2018, le=2022),
    departamento: str | None = None,
    municipio: str | None = None,
    institucion: str | None = None,
    caracter_institucion: str | None = None,
    programa: str | None = None,
    metodo_programa: str | None = None,
    genero: str | None = None,
    estrato: str | None = None,
    grupo_referencia: str | None = None,
) -> HistoricoResponse:
    filtros: dict[str, Any] = {
        "departamento": departamento,
        "municipio": municipio,
        "institucion": institucion,
        "caracter_institucion": caracter_institucion,
        "programa": programa,
        "metodo_programa": metodo_programa,
        "genero": genero,
        "estrato": estrato,
        "grupo_referencia": grupo_referencia,
    }
    return calcular_historico(
        {key: value for key, value in filtros.items() if value is not None},
        anio=str(anio) if anio is not None else None,
    )


@router.get(
    "/desempeno-estratos",
    response_model=EstratosResponse,
    summary="Puntaje global medio por estrato socioeconómico",
    responses={503: {"description": "MongoDB no disponible"}},
)
def get_desempeno_estratos() -> EstratosResponse:
    return calcular_desempeno_por_estrato()


@router.get(
    "/comparativo-competencias",
    response_model=ComparativoCompetenciasResponse,
    summary="Comparar una IES con el promedio nacional de su grupo",
    responses={
        422: {"description": "Institución y grupo de referencia requeridos"},
        503: {"description": "MongoDB no disponible"},
    },
)
def get_comparativo_competencias(
    institucion: str = Query(..., min_length=1),
    grupo_referencia: str = Query(..., min_length=1),
) -> ComparativoCompetenciasResponse:
    return calcular_comparativo_competencias(institucion, grupo_referencia)


@router.get(
    "/ranking-instituciones",
    response_model=RankingInstitucionesResponse,
    summary="Rankings Top/Bottom de IES oficiales o no oficiales",
    responses={503: {"description": "MongoDB no disponible"}},
)
def get_ranking_instituciones(
    tipo: Literal["OFICIAL", "NO OFICIAL"] = Query(...),
) -> RankingInstitucionesResponse:
    return calcular_ranking_instituciones(tipo)


@router.get(
    "/distribucion-departamental",
    response_model=DistribucionDepartamentalResponse,
    summary="Promedio global por departamento",
    responses={503: {"description": "MongoDB no disponible"}},
)
def get_distribucion_departamental(
    anio: int | None = Query(default=None, ge=2018, le=2022),
) -> DistribucionDepartamentalResponse:
    filtros: dict[str, Any] = {"anio": str(anio)} if anio is not None else {}
    return calcular_distribucion_departamental(
        {key: value for key, value in filtros.items() if value is not None}
    )
