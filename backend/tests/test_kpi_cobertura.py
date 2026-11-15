"""Pruebas del KPI de cobertura socioeconómica."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.controllers import kpi_controller
from backend.app.routes import kpis as kpis_routes


def _mock_agregacion(
    monkeypatch,
    documentos: list[dict],
    pipelines: list[list[dict]] | None = None,
) -> None:
    monkeypatch.setattr(kpi_controller, "_obtener_database", lambda: object())

    def fake_ejecutar(database, pipeline):
        if pipelines is not None:
            pipelines.append(pipeline)
        return documentos

    monkeypatch.setattr(
        kpi_controller,
        "_ejecutar_agregacion",
        fake_ejecutar,
    )


def test_calcular_kpi_cobertura_calcula_total_y_porcentaje(
    monkeypatch,
) -> None:
    _mock_agregacion(
        monkeypatch,
        [
            {"_id": "Estrato 1", "total": 30},
            {"_id": "Estrato 2", "total": 20},
            {"_id": "Estrato 3", "total": 50},
        ],
    )

    resultado = kpi_controller.calcular_kpi_cobertura({})

    assert resultado["total_registros"] == 100
    assert resultado["porcentaje_estratos_1_2"] == 50.0
    assert resultado["distribucion_estratos"] == {
        "Estrato 1": 30,
        "Estrato 2": 20,
        "Estrato 3": 50,
    }


def test_calcular_kpi_cobertura_incluye_lookup_y_group_por_estrato(
    monkeypatch,
) -> None:
    pipelines: list[list[dict]] = []
    _mock_agregacion(monkeypatch, [], pipelines)

    kpi_controller.calcular_kpi_cobertura({})

    pipeline = pipelines[0]
    assert any(
        paso.get("$lookup", {}).get("from") == "Dim_Estudiante"
        for paso in pipeline
    )
    assert any(
        paso.get("$unwind", {}).get("path") == "$dim_estudiante"
        for paso in pipeline
    )

    group = next(paso["$group"] for paso in pipeline if "$group" in paso)
    assert group["_id"] == "$dim_estudiante.estrato"
    assert group["total"] == {"$sum": 1}


def test_calcular_kpi_cobertura_sin_datos_devuelve_ceros(
    monkeypatch,
) -> None:
    _mock_agregacion(monkeypatch, [])

    resultado = kpi_controller.calcular_kpi_cobertura({})

    assert resultado == {
        "total_registros": 0,
        "porcentaje_estratos_1_2": 0.0,
        "distribucion_estratos": {},
    }


def test_route_kpi_cobertura_delega_en_controller(monkeypatch) -> None:
    filtros = {"periodo": "20225"}
    esperado = {
        "total_registros": 100,
        "porcentaje_estratos_1_2": 50.0,
        "distribucion_estratos": {"Estrato 1": 50, "Estrato 2": 50},
    }
    capturado: dict[str, object] = {}

    def fake_calcular(filtros_recibidos):
        capturado.update(filtros_recibidos)
        return esperado

    monkeypatch.setattr(
        kpis_routes,
        "calcular_kpi_cobertura",
        fake_calcular,
    )

    resultado = kpis_routes.get_kpi_cobertura(filtros)

    assert capturado == filtros
    assert resultado == esperado


def test_endpoint_kpi_cobertura_requiere_autenticacion() -> None:
    app = FastAPI()
    app.include_router(kpis_routes.router, prefix="/api")

    response = TestClient(app).get("/api/kpis/cobertura")

    assert response.status_code == 401

