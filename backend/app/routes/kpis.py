"""Endpoints de KPIs."""

from typing import Any

from fastapi import APIRouter, Depends, Query

from ..controllers.kpi_controller import (
    DEFAULT_METRIC,
    calcular_kpi,
    calcular_kpi_competencias,
    calcular_kpi_global,
)
from ..models.kpi import (
    KpiCompetenciasResponse,
    KpiGlobalResponse,
    KpiResponse,
)

router = APIRouter(prefix="/kpis", tags=["KPIs"])


def _obtener_filtros_dashboard(
    periodo: str | None = Query(
        default=None,
        description="Periodo académico, por ejemplo 20225.",
    ),
    departamento: str | None = Query(
        default=None,
        description="Departamento de residencia del estudiante.",
    ),
    municipio: str | None = Query(
        default=None,
        description="Municipio de residencia del estudiante.",
    ),
    institucion: str | None = Query(
        default=None,
        description="Nombre de la institución de educación superior.",
    ),
    caracter_institucion: str | None = Query(
        default=None,
        description="Carácter académico de la institución.",
    ),
    programa: str | None = Query(
        default=None,
        description="Nombre del programa académico.",
    ),
    metodo_programa: str | None = Query(
        default=None,
        description="Metodología del programa.",
    ),
    genero: str | None = Query(
        default=None,
        description="Género del estudiante (F/M).",
    ),
    estrato: str | None = Query(
        default=None,
        description="Estrato socioeconómico; acepta '2' o 'Estrato 2'.",
    ),
    grupo_referencia: str | None = Query(
        default=None,
        description="Núcleo de conocimiento/grupo de referencia.",
    ),
    internet: bool | None = Query(
        default=None,
        description="Tenencia de internet en el hogar.",
    ),
    computador: bool | None = Query(
        default=None,
        description="Tenencia de computador en el hogar.",
    ),
    departamento_examen: str | None = Query(
        default=None,
        description="Departamento donde se presentó el examen.",
    ),
    municipio_examen: str | None = Query(
        default=None,
        description="Municipio donde se presentó el examen.",
    ),
) -> dict[str, Any]:
    """Recoge los filtros opcionales compartidos por los endpoints de KPIs."""
    filtros = {
        "periodo": periodo,
        "departamento": departamento,
        "municipio": municipio,
        "institucion": institucion,
        "caracter_institucion": caracter_institucion,
        "programa": programa,
        "metodo_programa": metodo_programa,
        "genero": genero,
        "estrato": estrato,
        "grupo_referencia": grupo_referencia,
        "internet": internet,
        "computador": computador,
        "departamento_examen": departamento_examen,
        "municipio_examen": municipio_examen,
    }

    # ``False`` es un filtro válido, por eso solo se descartan los ``None``.
    return {key: value for key, value in filtros.items() if value is not None}


@router.get(
    "",
    response_model=KpiResponse,
    summary="Promedio de una métrica con filtros opcionales",
    responses={
        400: {"description": "Métrica no válida"},
        503: {"description": "MongoDB no disponible"},
    },
)
def get_kpi(
    filtros: dict[str, Any] = Depends(_obtener_filtros_dashboard),
    metrica: str = Query(
        default=DEFAULT_METRIC,
        description="Métrica numérica a promediar.",
    ),
) -> dict[str, Any]:
    """Calcula el promedio de una métrica usando ``QueryBuilder``.

    Todos los filtros son opcionales. Si no se envían, el promedio se calcula
    sobre toda la colección ``Fact_Resultados``.
    """
    return calcular_kpi(filtros, metrica)


@router.get(
    "/global",
    response_model=KpiGlobalResponse,
    summary="KPI promedio global y comparativo con el periodo anterior",
    responses={503: {"description": "MongoDB no disponible"}},
)
def get_kpi_global(
    filtros: dict[str, Any] = Depends(_obtener_filtros_dashboard),
) -> dict[str, Any]:
    """Calcula el promedio global de las cinco competencias.

    Acepta los mismos filtros opcionales que ``/api/kpis``. Si se envía
    ``periodo``, devuelve además la variación porcentual frente al periodo
    inmediatamente anterior registrado en ``Dim_Tiempo``.
    """
    return calcular_kpi_global(filtros)


@router.get(
    "/competencias",
    response_model=KpiCompetenciasResponse,
    summary="KPIs promedio por competencia",
    responses={503: {"description": "MongoDB no disponible"}},
)
def get_kpi_competencias(
    filtros: dict[str, Any] = Depends(_obtener_filtros_dashboard),
) -> dict[str, Any]:
    """Calcula en una sola consulta los promedios de las cinco competencias.

    Acepta los mismos filtros opcionales que ``/api/kpis`` y añade el promedio
    global y el total de registros que coincidieron.
    """
    return calcular_kpi_competencias(filtros)
