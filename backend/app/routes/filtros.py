"""Endpoints para poblar los filtros multidimensionales del dashboard.

Cada endpoint consulta valores únicos con ``distinct()`` sobre una dimensión
del Esquema de Estrella y los devuelve ordenados alfabéticamente.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import PyMongoError

from ..database import mongo_connection
from ..auth import require_permission
from ..models.filtro import FiltroResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/filtros",
    tags=["Filtros"],
    dependencies=[Depends(require_permission("dashboard:read"))],
)


def _obtener_valores_distintos(
    coleccion: str,
    campo: str,
) -> FiltroResponse:
    """Obtiene los valores únicos no nulos y no vacíos de un campo.

    Args:
        coleccion: Nombre de la colección de dimensión.
        campo: Campo sobre el cual se ejecuta ``distinct``.

    Returns:
        ``FiltroResponse`` con los valores ordenados y su total.

    Raises:
        HTTPException: 503 si MongoDB no está disponible o la consulta falla.
    """
    try:
        database = mongo_connection.get_database()
        raw_values = database[coleccion].distinct(
            campo,
            {campo: {"$ne": None}},
        )
    except (PyMongoError, ConnectionError) as exc:
        logger.exception(
            "Error consultando valores distintos de %s.%s",
            coleccion,
            campo,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible consultar MongoDB.",
        ) from exc

    # ``$ne: None`` excluye nulos; el filtro en Python elimina cadenas vacías.
    valores: set[str] = set()
    for value in raw_values:
        if value is None:
            continue
        texto = str(value).strip()
        if texto:
            valores.add(texto)

    valores_ordenados = sorted(valores, key=str.casefold)

    return FiltroResponse(
        valores=valores_ordenados,
        total=len(valores_ordenados),
    )


@router.get(
    "/periodos",
    response_model=FiltroResponse,
    summary="Listar periodos académicos",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_periodos() -> FiltroResponse:
    """Devuelve los periodos únicos de ``Dim_Tiempo``."""
    return _obtener_valores_distintos("Dim_Tiempo", "periodo")


@router.get(
    "/departamentos",
    response_model=FiltroResponse,
    summary="Listar departamentos de residencia",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_departamentos() -> FiltroResponse:
    """Devuelve los departamentos únicos de ``Dim_Estudiante``."""
    return _obtener_valores_distintos("Dim_Estudiante", "depto_reside")


@router.get(
    "/municipios",
    response_model=FiltroResponse,
    summary="Listar municipios de residencia",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_municipios() -> FiltroResponse:
    """Devuelve los municipios únicos de ``Dim_Estudiante``."""
    return _obtener_valores_distintos("Dim_Estudiante", "mcpio_reside")


@router.get(
    "/instituciones",
    response_model=FiltroResponse,
    summary="Listar instituciones de educación superior",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_instituciones() -> FiltroResponse:
    """Devuelve los nombres únicos de instituciones de ``Dim_Institucion``."""
    return _obtener_valores_distintos(
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
    """Devuelve los caracteres académicos únicos de ``Dim_Institucion``."""
    return _obtener_valores_distintos(
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
    """Devuelve los programas académicos únicos de ``Dim_Programa``."""
    return _obtener_valores_distintos(
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
    """Devuelve las metodologías únicas de ``Dim_Programa``."""
    return _obtener_valores_distintos("Dim_Programa", "metodo_programa")


@router.get(
    "/generos",
    response_model=FiltroResponse,
    summary="Listar géneros",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_generos() -> FiltroResponse:
    """Devuelve los géneros únicos de ``Dim_Estudiante``."""
    return _obtener_valores_distintos("Dim_Estudiante", "genero")


@router.get(
    "/estratos",
    response_model=FiltroResponse,
    summary="Listar estratos socioeconómicos",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_estratos() -> FiltroResponse:
    """Devuelve los estratos únicos de ``Dim_Estudiante``."""
    return _obtener_valores_distintos("Dim_Estudiante", "estrato")


@router.get(
    "/nucleos",
    response_model=FiltroResponse,
    summary="Listar núcleos de conocimiento",
    responses={503: {"description": "MongoDB no disponible"}},
)
def listar_nucleos() -> FiltroResponse:
    """Devuelve los núcleos de conocimiento únicos de ``Dim_Programa``."""
    return _obtener_valores_distintos("Dim_Programa", "nucleo_pregrado")
