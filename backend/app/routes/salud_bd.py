"""Endpoint de salud y rendimiento de la base de datos MongoDB."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException, status
from pymongo.database import Database
from pymongo.errors import PyMongoError

from ..database import mongo_connection
from ..models.salud import SaludBDResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/salud-bd", tags=["Salud BD"])

COLECCIONES = (
    "Fact_Resultados",
    "Dim_Tiempo",
    "Dim_Estudiante",
    "Dim_Institucion",
    "Dim_Programa",
    "Dim_Ubicacion_Examen",
)

BYTES_PER_MB = 1024 * 1024


def _contar_documentos(database: Database) -> dict[str, int]:
    """Cuenta los documentos de cada colección del Esquema de Estrella."""
    return {
        coleccion: database[coleccion].count_documents({})
        for coleccion in COLECCIONES
    }


def _medir_agregacion(database: Database) -> float:
    """Mide en milisegundos una agregación simple sobre ``Fact_Resultados``."""
    inicio = time.perf_counter()
    list(
        database["Fact_Resultados"].aggregate(
            [{"$count": "total"}],
        )
    )
    return (time.perf_counter() - inicio) * 1000


def _obtener_espacio_mb(database: Database) -> float:
    """Obtiene el espacio total de la base de datos en MB desde ``dbStats``."""
    stats = database.command("dbStats")
    total_bytes = stats.get("totalSize") or (
        stats.get("storageSize", 0) + stats.get("indexSize", 0)
    ) or stats.get("dataSize", 0)
    return float(total_bytes) / BYTES_PER_MB


@router.get(
    "",
    response_model=SaludBDResponse,
    summary="Salud y rendimiento de la base de datos MongoDB",
    responses={
        503: {
            "description": "MongoDB no disponible o error al consultar métricas",
        }
    },
)
def obtener_salud_bd() -> SaludBDResponse:
    """Devuelve métricas de salud y rendimiento de la base de datos.

    Consulta el estado de la conexión, cuenta los documentos de las seis
    colecciones, mide el tiempo de una agregación simple y obtiene el espacio
    total ocupado mediante ``dbStats``.

    Returns:
        ``SaludBDResponse`` con las métricas de la base de datos.

    Raises:
        HTTPException: 503 si MongoDB no responde o falla una consulta.
    """
    if not mongo_connection.ping():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "estado_conexion": "desconectado",
                "mensaje": (
                    "MongoDB no responde. Verifica MONGO_URI, MONGO_DATABASE "
                    "y que el servidor esté en ejecución."
                ),
            },
        )

    try:
        database = mongo_connection.get_database()
        colecciones = _contar_documentos(database)
        tiempo_ms = _medir_agregacion(database)
        espacio_mb = _obtener_espacio_mb(database)
    except (PyMongoError, ConnectionError) as exc:
        logger.exception("Error obteniendo métricas de salud de MongoDB")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "estado_conexion": "desconectado",
                "mensaje": (
                    "No fue posible obtener las métricas de MongoDB. "
                    "Revisa la conexión y los permisos del usuario."
                ),
            },
        ) from exc

    return SaludBDResponse(
        estado_conexion="conectado",
        colecciones=colecciones,
        tiempo_promedio_consulta_ms=round(tiempo_ms, 3),
        espacio_total_mb=round(espacio_mb, 2),
        total_documentos=sum(colecciones.values()),
    )
