"""Controlador para los valores únicos de los filtros del dashboard."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from pymongo.errors import PyMongoError

from ..database import mongo_connection
from ..models.filtro import FiltroResponse

logger = logging.getLogger(__name__)


def obtener_valores_distintos(
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
