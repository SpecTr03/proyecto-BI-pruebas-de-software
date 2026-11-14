"""Controlador de salud y rendimiento de la base de datos MongoDB."""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import HTTPException, status
from pymongo.database import Database
from pymongo.errors import PyMongoError

from ..database import mongo_connection
from ..models.salud import SaludBDResponse

logger = logging.getLogger(__name__)

COLECCIONES = (
    "Fact_Resultados",
    "Dim_Tiempo",
    "Dim_Estudiante",
    "Dim_Institucion",
    "Dim_Programa",
    "Dim_Ubicacion_Examen",
)

BYTES_PER_MB = 1024 * 1024
NUM_CONSULTAS_MEDIDAS = 5


def _contar_documentos(database: Database) -> dict[str, int]:
    """Cuenta los documentos de cada colección del Esquema de Estrella."""
    return {
        coleccion: database[coleccion].count_documents({})
        for coleccion in COLECCIONES
    }


def _calentar_consulta(collection: Any) -> None:
    """Ejecuta una consulta de calentamiento para evitar el cold start."""
    collection.count_documents({})


def _medir_consulta(collection: Any) -> float:
    """Mide en milisegundos una consulta de referencia."""
    inicio = time.perf_counter()
    collection.count_documents({})
    return (time.perf_counter() - inicio) * 1000


def _medir_consultas(collection: Any) -> dict[str, float | int]:
    """Mide la consulta cinco veces y resume sus tiempos en milisegundos."""
    mediciones = [
        _medir_consulta(collection)
        for _ in range(NUM_CONSULTAS_MEDIDAS)
    ]
    return {
        "tiempo_promedio_consulta_ms": round(
            sum(mediciones) / len(mediciones),
            3,
        ),
        "tiempo_min_consulta_ms": round(min(mediciones), 3),
        "tiempo_max_consulta_ms": round(max(mediciones), 3),
        "num_consultas_medidas": len(mediciones),
    }


def _obtener_espacio_mb(database: Database) -> float:
    """Obtiene el espacio total de la base de datos en MB desde ``dbStats``."""
    stats = database.command("dbStats")
    total_bytes = stats.get("totalSize") or (
        stats.get("storageSize", 0) + stats.get("indexSize", 0)
    ) or stats.get("dataSize", 0)
    return float(total_bytes) / BYTES_PER_MB


def obtener_salud_bd() -> SaludBDResponse:
    """Devuelve métricas de salud y rendimiento de la base de datos.

    Consulta el estado de la conexión, cuenta los documentos de las seis
    colecciones y obtiene el espacio total ocupado mediante ``dbStats``.

    El tiempo de consulta se mide con ``count_documents({})`` sobre
    ``Fact_Resultados``. Primero se ejecuta una consulta de calentamiento y
    luego se realizan 5 mediciones con ``time.perf_counter()``; la consulta
    de calentamiento se descarta por cold start y el promedio, mínimo y máximo
    se calculan sobre las 5 mediciones restantes. Un promedio superior a
    1000 ms se considera indicio de rendimiento degradado.

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
        fact_resultados = database["Fact_Resultados"]
        _calentar_consulta(fact_resultados)
        estadisticas = _medir_consultas(fact_resultados)
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

    if estadisticas["tiempo_promedio_consulta_ms"] > 1000:
        logger.warning(
            "Rendimiento degradado en MongoDB: %.3f ms promedio por consulta",
            estadisticas["tiempo_promedio_consulta_ms"],
        )

    return SaludBDResponse(
        estado_conexion="conectado",
        colecciones=colecciones,
        **estadisticas,
        espacio_total_mb=round(espacio_mb, 2),
        total_documentos=sum(colecciones.values()),
    )
