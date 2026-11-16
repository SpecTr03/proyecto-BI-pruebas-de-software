"""Lógica de negocio para la proyección de crecimiento del promedio global."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..constants import METRICAS_COMPETENCIAS
from .kpi_controller import _ejecutar_agregacion, _obtener_database

FACT_COLLECTION = "Fact_Resultados"
DIM_TIME_COLLECTION = "Dim_Tiempo"
MIN_REGISTROS_PERIODO = 100
VENTANA_PROMEDIO_MOVIL = 3
METODOS_VALIDOS = frozenset({"promedio_movil", "regresion_lineal"})


def _pipeline_historico() -> list[dict[str, Any]]:
    """Construye el pipeline que agrupa el promedio global por periodo.

    El ``$group`` se hace primero sobre la FK indexada ``id_tiempo`` y el
    ``$lookup`` se ejecuta después sobre los pocos periodos resultantes. Hacer
    el ``$lookup`` antes del ``$group`` obliga a resolver la dimensión para
    más de un millón de hechos y eleva el tiempo de respuesta por encima de
    los 30 segundos.
    """
    metricas = [f"${campo}" for campo in METRICAS_COMPETENCIAS.values()]
    return [
        {
            "$group": {
                "_id": "$id_tiempo",
                "promedio": {"$avg": {"$avg": metricas}},
                "count": {"$sum": 1},
            }
        },
        {"$match": {"count": {"$gte": MIN_REGISTROS_PERIODO}}},
        {
            "$lookup": {
                "from": DIM_TIME_COLLECTION,
                "localField": "_id",
                "foreignField": "_id",
                "as": "tiempo",
            }
        },
        {"$unwind": "$tiempo"},
        {
            "$project": {
                "_id": 0,
                "periodo": "$tiempo.periodo",
                "promedio": 1,
            }
        },
        {"$sort": {"periodo": 1}},
    ]


def obtener_historico() -> list[dict[str, Any]]:
    """Obtiene el promedio global por periodo con al menos 100 registros.

    Returns:
        Lista ordenada de ``{"periodo": str, "promedio": float}``.

    Raises:
        HTTPException: 503 si MongoDB no responde o falla la agregación.
    """
    database = _obtener_database()
    result = _ejecutar_agregacion(database, _pipeline_historico())

    historico: list[dict[str, Any]] = []
    for document in result:
        periodo = document.get("periodo", document.get("_id"))
        promedio = document.get("promedio")
        if periodo is None or promedio is None:
            continue
        historico.append(
            {
                "periodo": str(periodo),
                "promedio": round(float(promedio), 2),
            }
        )

    historico.sort(key=lambda item: item["periodo"])
    return historico


def proyectar_promedio_movil(
    historico: list[dict[str, Any]],
    ventana: int = VENTANA_PROMEDIO_MOVIL,
) -> float:
    """Proyecta el siguiente valor con el promedio de los últimos periodos."""
    if ventana < 1:
        raise ValueError("La ventana del promedio móvil debe ser al menos 1.")
    if len(historico) < ventana:
        raise ValueError(
            "Se requieren al menos "
            f"{ventana} periodos para calcular el promedio móvil; "
            f"se recibieron {len(historico)}."
        )

    promedios = [
        float(item["promedio"]) for item in historico[-ventana:]
    ]
    return round(sum(promedios) / ventana, 2)


def proyectar_regresion_lineal(
    historico: list[dict[str, Any]],
) -> float:
    """Proyecta el siguiente valor con una regresión lineal simple."""
    if len(historico) < 2:
        raise ValueError(
            "Se requieren al menos 2 periodos para calcular la regresión "
            f"lineal; se recibieron {len(historico)}."
        )

    x = np.arange(len(historico), dtype=float)
    y = np.array(
        [float(item["promedio"]) for item in historico],
        dtype=float,
    )
    pendiente, intercepto = np.polyfit(x, y, 1)
    proyeccion = float(pendiente * len(historico) + intercepto)
    return round(max(0.0, min(300.0, proyeccion)), 2)


def siguiente_periodo(periodo: str) -> str:
    """Calcula el siguiente periodo lógico en formato YYYY + semestre."""
    texto = str(periodo).strip()
    if len(texto) != 5 or not texto.isdigit():
        raise ValueError(
            "El periodo debe tener el formato YYYY + semestre (5 dígitos)."
        )

    anio = int(texto[:4])
    semestre = int(texto[4])
    if not 1 <= semestre <= 6:
        raise ValueError("El semestre del periodo debe estar entre 1 y 6.")

    if semestre < 6:
        return f"{anio}{semestre + 1}"
    return f"{anio + 1}1"


def calcular_proyeccion_crecimiento(
    metodo: str = "promedio_movil",
) -> dict[str, Any]:
    """Orquesta el cálculo de la proyección de crecimiento.

    Args:
        metodo: ``promedio_movil`` o ``regresion_lineal``.

    Returns:
        Diccionario compatible con ``ProyeccionCrecimientoResponse``.

    Raises:
        ValueError: Si el método no es válido o el histórico es insuficiente.
        HTTPException: 503 si MongoDB no responde o falla la agregación.
    """
    if metodo not in METODOS_VALIDOS:
        raise ValueError(
            f"Método no válido: {metodo!r}. Usa 'promedio_movil' o "
            "'regresion_lineal'."
        )

    historico = obtener_historico()
    if not historico:
        raise ValueError(
            "No hay periodos con suficientes registros para calcular la "
            "proyección."
        )

    periodo_actual = str(historico[-1]["periodo"])
    promedio_actual = round(float(historico[-1]["promedio"]), 2)

    if metodo == "promedio_movil":
        promedio_proyectado = proyectar_promedio_movil(historico)
    else:
        promedio_proyectado = proyectar_regresion_lineal(historico)

    periodo_proyectado = siguiente_periodo(periodo_actual)
    tasa_crecimiento = (
        round(
            (
                (promedio_proyectado - promedio_actual)
                / promedio_actual
            )
            * 100,
            2,
        )
        if promedio_actual != 0
        else 0.0
    )

    return {
        "periodo_actual": periodo_actual,
        "promedio_actual": promedio_actual,
        "periodo_proyectado": periodo_proyectado,
        "promedio_proyectado": promedio_proyectado,
        "tasa_crecimiento_porcentual": tasa_crecimiento,
        "metodo": metodo,
        "periodos_analizados": len(historico),
        "historico": historico,
    }
