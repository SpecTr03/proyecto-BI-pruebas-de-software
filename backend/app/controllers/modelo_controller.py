"""Lógica de negocio para la importancia de variables del modelo."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

logger = logging.getLogger(__name__)

MODEL_PATH = (
    Path(__file__).resolve().parents[2] / "models" / "modelo_saber_pro.pkl"
)

TOP_RANKING = 20
REQUIRED_ARTIFACT_KEYS = {"model", "feature_names"}


class ModeloNoEntrenadoError(RuntimeError):
    """Se lanza cuando el archivo del modelo no existe."""


class ModeloCorruptoError(RuntimeError):
    """Se lanza cuando el artefacto del modelo no se puede interpretar."""


class ModeloSinImportanciasError(RuntimeError):
    """Se lanza cuando el modelo no expone ``feature_importances_``."""


@lru_cache(maxsize=1)
def cargar_modelo() -> dict[str, Any]:
    """Carga y cachea el artefacto ``modelo_saber_pro.pkl``.

    Returns:
        Diccionario con ``model`` y ``feature_names``.

    Raises:
        ModeloNoEntrenadoError: Si el archivo no existe.
        ModeloCorruptoError: Si el archivo está corrupto o incompleto.
    """
    if not MODEL_PATH.exists():
        raise ModeloNoEntrenadoError(
            "El modelo no está entrenado. "
            "Ejecuta scripts/train_model.py primero."
        )

    try:
        artifact = joblib.load(MODEL_PATH)
    except Exception as exc:
        logger.exception("No fue posible cargar el modelo entrenado")
        raise ModeloCorruptoError(
            "No fue posible cargar el modelo entrenado."
        ) from exc

    if not isinstance(artifact, dict):
        raise ModeloCorruptoError(
            "No fue posible cargar el modelo entrenado."
        )

    missing_keys = REQUIRED_ARTIFACT_KEYS - set(artifact)
    if missing_keys:
        raise ModeloCorruptoError(
            "No fue posible cargar el modelo entrenado."
        )

    return artifact


def limpiar_nombre_feature(nombre: str) -> str:
    """Limpia el nombre de una feature generada por ``ColumnTransformer``."""
    limpio = str(nombre)
    for prefijo in ("cat__", "num__"):
        if limpio.startswith(prefijo):
            limpio = limpio[len(prefijo) :]
            break
    return " ".join(limpio.replace("_", " ").split())


def calcular_importancia() -> dict[str, Any]:
    """Calcula el ranking de importancia de las variables del modelo.

    Returns:
        Diccionario compatible con ``ModeloImportanciaResponse``.

    Raises:
        ModeloNoEntrenadoError: Si el modelo no está entrenado.
        ModeloCorruptoError: Si el artefacto es inválido o inconsistente.
        ModeloSinImportanciasError: Si el modelo no es basado en árboles.
    """
    artifact = cargar_modelo()
    model = artifact.get("model")
    feature_names = artifact.get("feature_names")
    importances = getattr(model, "feature_importances_", None)

    if importances is None:
        raise ModeloSinImportanciasError(
            "El modelo actual no expone feature_importances_. "
            "Se requiere un modelo basado en árboles."
        )

    if not isinstance(feature_names, (list, tuple)) or not feature_names:
        raise ModeloCorruptoError(
            "No fue posible cargar el modelo entrenado."
        )

    try:
        importancias = [float(valor) for valor in importances]
    except (TypeError, ValueError) as exc:
        raise ModeloCorruptoError(
            "No fue posible cargar el modelo entrenado."
        ) from exc

    if len(importancias) != len(feature_names) or not importancias:
        raise ModeloCorruptoError(
            "No fue posible cargar el modelo entrenado."
        )

    ranking = [
        {
            "variable": limpiar_nombre_feature(str(nombre)),
            "importancia": importancia,
        }
        for nombre, importancia in zip(feature_names, importancias)
    ]
    ranking.sort(key=lambda item: item["importancia"], reverse=True)

    top = ranking[0]
    return {
        "top_variable": top["variable"],
        "top_importancia": top["importancia"],
        "ranking": ranking[:TOP_RANKING],
        "total_features": len(feature_names),
    }
