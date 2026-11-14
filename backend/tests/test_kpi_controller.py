"""Pruebas de los indicadores cualitativos de competencias."""

from backend.app.controllers import kpi_controller


def test_clasificar_desempeno_respeta_los_limites_icfes() -> None:
    assert kpi_controller.clasificar_desempeno(119.99) == "Deficiente"
    assert kpi_controller.clasificar_desempeno(120) == "Aceptable"
    assert kpi_controller.clasificar_desempeno(180) == "Aceptable"
    assert kpi_controller.clasificar_desempeno(180.01) == "Sobresaliente"


def test_calcular_kpi_competencias_agrega_indicadores(monkeypatch) -> None:
    document = {
        "razonamiento": 119,
        "lectura": 120,
        "ciudadanas": 180,
        "escrita": 180.01,
        "ingles": 150,
        "promedio_global": 149.8,
        "total_registros": 100,
    }

    monkeypatch.setattr(kpi_controller, "_obtener_database", lambda: object())
    monkeypatch.setattr(
        kpi_controller,
        "_ejecutar_agregacion",
        lambda database, pipeline: [document],
    )

    result = kpi_controller.calcular_kpi_competencias({})

    assert result["indicadores"] == {
        "razonamiento": "Deficiente",
        "lectura": "Aceptable",
        "ciudadanas": "Aceptable",
        "escrita": "Sobresaliente",
        "ingles": "Aceptable",
    }
