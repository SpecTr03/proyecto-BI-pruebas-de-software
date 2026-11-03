"""Lógica de negocio para la predicción del puntaje global de Saber Pro."""

from __future__ import annotations

import logging
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

MODEL_PATH = (
    Path(__file__).resolve().parents[2] / "models" / "modelo_saber_pro.pkl"
)

FEATURE_COLUMNS = [
    "genero",
    "estrato",
    "educacion_padre",
    "educacion_madre",
    "tiene_internet",
    "tiene_computador",
    "caracter_academico",
    "metodo_programa",
    "depto_reside",
    "depto_institucion",
]

REQUIRED_ARTIFACT_KEYS = {"model", "preprocessor"}


class ModeloNoDisponibleError(RuntimeError):
    """Se lanza cuando el artefacto del modelo no existe o no se puede cargar."""


def _validar_artefacto(artifact: Any) -> dict[str, Any]:
    """Valida que el artefacto cargado tenga las claves necesarias."""
    if not isinstance(artifact, dict):
        raise ModeloNoDisponibleError(
            "El artefacto del modelo no tiene el formato esperado: "
            "se esperaba un diccionario."
        )

    missing_keys = REQUIRED_ARTIFACT_KEYS - set(artifact)
    if missing_keys:
        raise ModeloNoDisponibleError(
            "El artefacto del modelo está incompleto; faltan las claves: "
            + ", ".join(sorted(missing_keys))
            + "."
        )

    return artifact


@lru_cache(maxsize=1)
def cargar_modelo() -> dict[str, Any]:
    """Carga y cachea el artefacto ``modelo_saber_pro.pkl``.

    Returns:
        Diccionario con ``model``, ``preprocessor`` y ``feature_names``.

    Raises:
        ModeloNoDisponibleError: Si el archivo no existe, está corrupto o no
            contiene las claves requeridas.
    """
    if not MODEL_PATH.exists():
        raise ModeloNoDisponibleError(
            f"El modelo de predicción no existe en '{MODEL_PATH}'. "
            "Ejecuta 'python scripts/train_model.py' para generarlo."
        )

    try:
        artifact = joblib.load(MODEL_PATH)
    except Exception as exc:
        logger.exception("No fue posible cargar el modelo de predicción")
        raise ModeloNoDisponibleError(
            "No fue posible cargar el modelo de predicción. Verifica que "
            "joblib, pandas, scikit-learn y xgboost estén instalados y que "
            "el archivo no esté corrupto."
        ) from exc

    return _validar_artefacto(artifact)


def _parse_estrato(value: Any) -> float:
    """Convierte ``Estrato 2`` o ``2`` en el número ``2.0``.

    Si no hay un número en el valor, devuelve ``NaN`` para que el
    ``SimpleImputer`` del preprocesador lo complete con la mediana.
    """
    match = re.search(r"\d+", str(value))
    if match is None:
        return math.nan
    return float(match.group())


def _columnas_entrada(preprocessor: Any) -> list[str]:
    """Obtiene las columnas originales usadas al entrenar el preprocesador."""
    columnas = getattr(preprocessor, "feature_names_in_", None)
    if columnas is None:
        return list(FEATURE_COLUMNS)
    return [str(columna) for columna in columnas]


def _clasificar_nivel(puntaje: float) -> str:
    """Clasifica el puntaje global en un nivel de desempeño.

    Los límites se interpretan como ``[125, 150)``, ``[150, 175]`` y
    ``(175, 300]``; por debajo de 125 el nivel es ``Bajo``.
    """
    if puntaje < 125:
        return "Bajo"
    if puntaje < 150:
        return "Medio"
    if puntaje <= 175:
        return "Alto"
    return "Muy Alto"


def predecir(input_data: dict[str, Any]) -> dict[str, Any]:
    """Genera la predicción del puntaje global para un estudiante.

    Args:
        input_data: Diccionario con las variables de ``PrediccionInput``.

    Returns:
        Diccionario con ``puntaje_predicho``, ``nivel_desempeno`` y
        ``confianza``.

    Raises:
        ModeloNoDisponibleError: Si el modelo no está disponible.
        ValueError: Si el modelo no puede generar una predicción válida.
    """
    artifact = cargar_modelo()
    model = artifact["model"]
    preprocessor = artifact["preprocessor"]

    columnas = _columnas_entrada(preprocessor)
    fila = {columna: input_data.get(columna) for columna in columnas}
    fila["estrato"] = _parse_estrato(fila.get("estrato"))
    dataframe = pd.DataFrame([fila], columns=columnas)

    try:
        transformed = preprocessor.transform(dataframe)
        predicciones = np.asarray(model.predict(transformed)).reshape(-1)
    except Exception as exc:
        logger.exception("Error aplicando el modelo de predicción")
        raise ValueError(
            "No fue posible generar la predicción con el modelo."
        ) from exc

    if predicciones.size != 1:
        raise ValueError(
            "El modelo devolvió una cantidad inesperada de predicciones."
        )

    puntaje = float(predicciones[0])
    if not math.isfinite(puntaje):
        raise ValueError("El modelo devolvió un puntaje no finito.")

    puntaje = max(0.0, min(300.0, puntaje))

    return {
        "puntaje_predicho": round(puntaje, 2),
        "nivel_desempeno": _clasificar_nivel(puntaje),
        "confianza": None,
    }
