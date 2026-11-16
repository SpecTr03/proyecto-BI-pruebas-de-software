"""Endpoints de series y gráficas descriptivas."""

from typing import Any

from fastapi import APIRouter, Depends, Query

from ..auth import require_permission
from ..controllers.estrato_controller import calcular_desempeno_por_estrato
from ..controllers.historico_controller import calcular_historico
from ..models.grafica import EstratosResponse, HistoricoResponse

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
