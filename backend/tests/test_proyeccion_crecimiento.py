"""Pruebas de la proyección de crecimiento del promedio global."""

from __future__ import annotations

import pytest
from backend.app.controllers import proyeccion_controller
from backend.app.routes import proyeccion as proyeccion_routes
from fastapi import FastAPI
from fastapi.testclient import TestClient

PERIODOS = (
    "20183",
    "20184",
    "20194",
    "20195",
    "20196",
    "20202",
    "20203",
    "20212",
    "20213",
    "20222",
    "20223",
    "20225",
    "20226",
)


def _historico(promedios: list[float]) -> list[dict]:
    return [
        {"periodo": periodo, "promedio": promedio}
        for periodo, promedio in zip(PERIODOS, promedios)
    ]


def test_promedio_movil_proyecta_promedio_de_los_ultimos_tres(
    monkeypatch,
) -> None:
    historico = _historico([float(100 + indice) for indice in range(13)])
    monkeypatch.setattr(
        proyeccion_controller,
        "obtener_historico",
        lambda: historico,
    )

    resultado = proyeccion_controller.calcular_proyeccion_crecimiento()

    assert resultado["periodo_actual"] == "20226"
    assert resultado["promedio_actual"] == 112.0
    assert resultado["periodo_proyectado"] == "20231"
    assert resultado["promedio_proyectado"] == 111.0
    assert resultado["tasa_crecimiento_porcentual"] == -0.89
    assert resultado["metodo"] == "promedio_movil"
    assert resultado["periodos_analizados"] == 13
    assert resultado["historico"] == historico


def test_regresion_lineal_proyecta_el_siguiente_valor(monkeypatch) -> None:
    historico = _historico([100.0 + 5 * indice for indice in range(13)])

    proyectado = proyeccion_controller.proyectar_regresion_lineal(historico)

    assert proyectado == pytest.approx(165.0, abs=0.01)

    monkeypatch.setattr(
        proyeccion_controller,
        "obtener_historico",
        lambda: historico,
    )
    resultado = proyeccion_controller.calcular_proyeccion_crecimiento(
        "regresion_lineal"
    )

    assert resultado["metodo"] == "regresion_lineal"
    assert resultado["promedio_proyectado"] == pytest.approx(165.0, abs=0.01)


def test_siguiente_periodo_de_20226_es_20231() -> None:
    assert proyeccion_controller.siguiente_periodo("20226") == "20231"
    assert proyeccion_controller.siguiente_periodo("20225") == "20226"


def test_promedio_movil_requiere_al_menos_tres_periodos() -> None:
    historico = _historico([100.0, 101.0])

    with pytest.raises(ValueError, match="al menos 3"):
        proyeccion_controller.proyectar_promedio_movil(historico)


def test_endpoint_proyeccion_requiere_autenticacion() -> None:
    app = FastAPI()
    app.include_router(proyeccion_routes.router, prefix="/api")

    response = TestClient(app).get("/api/proyeccion/crecimiento")

    assert response.status_code == 401
