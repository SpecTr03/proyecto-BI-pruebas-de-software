"""Pruebas de la métrica probabilística HU21."""

from __future__ import annotations

import math

from backend.app.controllers import prediccion_controller


def test_probabilidad_es_porcentual_y_limita_el_resultado() -> None:
    artifact = {"test_rmse": 20.0}

    igual_a_media = prediccion_controller._calcular_probabilidad_superar_media(
        150.0,
        150.0,
        artifact,
    )
    superior = prediccion_controller._calcular_probabilidad_superar_media(
        170.0,
        150.0,
        artifact,
    )
    inferior = prediccion_controller._calcular_probabilidad_superar_media(
        130.0,
        150.0,
        artifact,
    )

    assert 0 <= igual_a_media <= 100
    assert math.isclose(igual_a_media, 50.0, abs_tol=0.01)
    assert superior > 50
    assert inferior < 50


def test_probabilidad_supera_media_aumenta_con_el_puntaje() -> None:
    artifact = {"test_mae": 25.0}
    probabilidades = [
        prediccion_controller._calcular_probabilidad_superar_media(
            puntaje,
            150.0,
            artifact,
        )
        for puntaje in (120.0, 150.0, 180.0)
    ]

    assert probabilidades == sorted(probabilidades)
