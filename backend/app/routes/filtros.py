"""Endpoints para poblar los filtros multidimensionales del dashboard.

Cada endpoint delega en ``filtros_controller`` la consulta de valores únicos
sobre una dimensión del Esquema de Estrella.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import require_permission
from ..controllers.filtros_controller import obtener_valores_distintos
from ..models.filtro import FiltroResponse

router = APIRouter(
    prefix="/filtros",
    tags=["Filtros"],
    dependencies=[Depends(require_permission("dashboard:read"))],
)


@router.get(
    "/periodos",
    response_model=FiltroResponse,
    summary="Listar periodos académicos",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_periodos() -> FiltroResponse:
    """Devuelve los periodos únicos de ``Dim_Tiempo`` delegando al controller."""
    return obtener_valores_distintos("Dim_Tiempo", "periodo")


@router.get(
    "/anios",
    response_model=FiltroResponse,
    summary="Listar años académicos",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_anios() -> FiltroResponse:
    """Deriva los años disponibles a partir de los periodos académicos."""
    periodos = obtener_valores_distintos("Dim_Tiempo", "periodo")
    anios = sorted({periodo[:4] for periodo in periodos.valores if len(periodo) >= 4})
    return FiltroResponse(valores=anios, total=len(anios))


@router.get(
    "/departamentos",
    response_model=FiltroResponse,
    summary="Listar departamentos de residencia",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_departamentos() -> FiltroResponse:
    """Devuelve los departamentos únicos delegando al controller."""
    return obtener_valores_distintos("Dim_Estudiante", "depto_reside")


@router.get(
    "/departamentos-institucion",
    response_model=FiltroResponse,
    summary="Listar departamentos de instituciones",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_departamentos_institucion() -> FiltroResponse:
    """Devuelve los departamentos únicos de las instituciones."""
    return obtener_valores_distintos(
        "Dim_Institucion",
        "depto_institucion",
    )


@router.get(
    "/educacion-padre",
    response_model=FiltroResponse,
    summary="Listar niveles educativos del padre",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_educacion_padre() -> FiltroResponse:
    """Devuelve los niveles educativos registrados para el padre."""
    return obtener_valores_distintos(
        "Dim_Estudiante",
        "educacion_padre",
    )


@router.get(
    "/educacion-madre",
    response_model=FiltroResponse,
    summary="Listar niveles educativos de la madre",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_educacion_madre() -> FiltroResponse:
    """Devuelve los niveles educativos registrados para la madre."""
    return obtener_valores_distintos(
        "Dim_Estudiante",
        "educacion_madre",
    )


@router.get(
    "/municipios",
    response_model=FiltroResponse,
    summary="Listar municipios de residencia",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_municipios() -> FiltroResponse:
    """Devuelve los municipios únicos delegando al controller."""
    return obtener_valores_distintos("Dim_Estudiante", "mcpio_reside")


@router.get(
    "/instituciones",
    response_model=FiltroResponse,
    summary="Listar instituciones de educación superior",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_instituciones() -> FiltroResponse:
    """Devuelve las instituciones únicas delegando al controller."""
    return obtener_valores_distintos(
        "Dim_Institucion",
        "nombre_institucion",
    )


@router.get(
    "/caracteres",
    response_model=FiltroResponse,
    summary="Listar caracteres académicos de instituciones",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_caracteres() -> FiltroResponse:
    """Devuelve los caracteres académicos únicos delegando al controller."""
    return obtener_valores_distintos(
        "Dim_Institucion",
        "caracter_academico",
    )


@router.get(
    "/programas",
    response_model=FiltroResponse,
    summary="Listar programas académicos",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_programas() -> FiltroResponse:
    """Devuelve los programas académicos únicos delegando al controller."""
    return obtener_valores_distintos(
        "Dim_Programa",
        "programa_academico",
    )


@router.get(
    "/metodos",
    response_model=FiltroResponse,
    summary="Listar metodologías de programa",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_metodos() -> FiltroResponse:
    """Devuelve las metodologías únicas delegando al controller."""
    return obtener_valores_distintos("Dim_Programa", "metodo_programa")


@router.get(
    "/generos",
    response_model=FiltroResponse,
    summary="Listar géneros",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_generos() -> FiltroResponse:
    """Devuelve los géneros únicos delegando al controller."""
    return obtener_valores_distintos("Dim_Estudiante", "genero")


@router.get(
    "/estratos",
    response_model=FiltroResponse,
    summary="Listar estratos socioeconómicos",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_estratos() -> FiltroResponse:
    """Devuelve los estratos únicos delegando al controller."""
    return obtener_valores_distintos("Dim_Estudiante", "estrato")


@router.get(
    "/nucleos",
    response_model=FiltroResponse,
    summary="Listar núcleos de conocimiento",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_nucleos() -> FiltroResponse:
    """Devuelve los núcleos de conocimiento únicos delegando al controller."""
    return obtener_valores_distintos("Dim_Programa", "nucleo_pregrado")
