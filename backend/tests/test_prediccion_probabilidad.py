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


def test_riesgo_quintil_inferior_disminuye_al_subir_el_puntaje() -> None:
    artifact = {"test_rmse": 20.0}
    riesgos = [
        prediccion_controller._calcular_probabilidad_riesgo(
            puntaje,
            125.6,
            artifact,
        )
        for puntaje in (100.0, 125.6, 160.0)
    ]

    assert riesgos == sorted(riesgos, reverse=True)
    assert math.isclose(riesgos[1], 50.0, abs_tol=0.01)


def test_clasificar_riesgo_devuelve_niveles_cuantitativos() -> None:
    assert prediccion_controller._clasificar_riesgo(70) == "Alto"
    assert prediccion_controller._clasificar_riesgo(40) == "Medio"
    assert prediccion_controller._clasificar_riesgo(20) == "Bajo"
