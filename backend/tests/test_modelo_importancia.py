"""Pruebas del endpoint de importancia de variables del modelo."""

from __future__ import annotations

from pathlib import Path

from backend.app.auth import AuthenticatedUser, get_current_user
from backend.app.controllers import modelo_controller
from backend.app.routes import modelo as modelo_routes
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _ModeloFake:
    def __init__(self, importances: list[float]) -> None:
        self.feature_importances_ = importances


def _mock_modelo(
    monkeypatch,
    importances: list[float],
    feature_names: list[str],
) -> None:
    artifact = {
        "model": _ModeloFake(importances),
        "feature_names": feature_names,
    }
    monkeypatch.setattr(
        modelo_controller,
        "cargar_modelo",
        lambda: artifact,
    )


def _cliente_autenticado() -> TestClient:
    app = FastAPI()
    app.include_router(modelo_routes.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id="test-user",
        email="test@example.com",
        role="Analista",
        permissions=frozenset({"dashboard:read"}),
    )
    return TestClient(app)


def test_calcular_importancia_ordena_ranking_descendente(monkeypatch) -> None:
    _mock_modelo(
        monkeypatch,
        [0.1, 0.5, 0.2, 0.7],
        [
            "num__estrato",
            "cat__genero_F",
            "cat__depto_reside_VALLE",
            "cat__caracter_academico_UNIVERSIDAD",
        ],
    )

    resultado = modelo_controller.calcular_importancia()

    assert resultado["ranking"] == [
        {
            "variable": "caracter academico UNIVERSIDAD",
            "importancia": 0.7,
        },
        {"variable": "genero F", "importancia": 0.5},
        {"variable": "depto reside VALLE", "importancia": 0.2},
        {"variable": "estrato", "importancia": 0.1},
    ]
    assert resultado["total_features"] == 4


def test_limpiar_nombre_feature_quita_prefijos_y_reemplaza_guiones_bajos() -> None:
    assert (
        modelo_controller.limpiar_nombre_feature(
            "cat__caracter_academico_UNIVERSIDAD"
        )
        == "caracter academico UNIVERSIDAD"
    )
    assert modelo_controller.limpiar_nombre_feature("num__estrato") == "estrato"
    assert (
        modelo_controller.limpiar_nombre_feature("sin_prefijo")
        == "sin prefijo"
    )


def test_importancia_maneja_errores_del_modelo(
    monkeypatch,
    tmp_path: Path,
) -> None:
    cliente = _cliente_autenticado()

    ruta_inexistente = tmp_path / "no-existe.pkl"
    monkeypatch.setattr(modelo_controller, "MODEL_PATH", ruta_inexistente)
    modelo_controller.cargar_modelo.cache_clear()

    response = cliente.get("/api/modelo/importancia")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "El modelo no está entrenado. Ejecuta scripts/train_model.py primero."
    )

    ruta_corrupta = tmp_path / "corrupto.pkl"
    ruta_corrupta.write_text("no es un joblib", encoding="utf-8")
    monkeypatch.setattr(modelo_controller, "MODEL_PATH", ruta_corrupta)
    modelo_controller.cargar_modelo.cache_clear()

    response = cliente.get("/api/modelo/importancia")

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "No fue posible cargar el modelo entrenado."
    )

    monkeypatch.setattr(
        modelo_controller,
        "cargar_modelo",
        lambda: {"model": object(), "feature_names": ["num__estrato"]},
    )

    response = cliente.get("/api/modelo/importancia")

    assert response.status_code == 501
    assert response.json()["detail"] == (
        "El modelo actual no expone feature_importances_. "
        "Se requiere un modelo basado en árboles."
    )


def test_endpoint_modelo_importancia_requiere_autenticacion() -> None:
    app = FastAPI()
    app.include_router(modelo_routes.router, prefix="/api")

    response = TestClient(app).get("/api/modelo/importancia")

    assert response.status_code == 401


def test_top_variable_coincide_con_el_primer_ranking(monkeypatch) -> None:
    _mock_modelo(
        monkeypatch,
        [0.2, 0.6, 0.15],
        ["num__estrato", "cat__genero_F", "num__edad"],
    )

    resultado = modelo_controller.calcular_importancia()

    assert resultado["top_variable"] == resultado["ranking"][0]["variable"]
    assert (
        resultado["top_importancia"]
        == resultado["ranking"][0]["importancia"]
    )
