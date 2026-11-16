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


def test_kpi_por_periodo_filtra_hechos_por_fk_indexada(monkeypatch) -> None:
    class TimeCollection:
        def find_one(self, query, projection):
            return {"_id": f"id-{query['periodo']}"}

    class FakeDatabase:
        def __getitem__(self, collection):
            assert collection == "Dim_Tiempo"
            return TimeCollection()

    database = FakeDatabase()
    captured = []
    results = {
        "id-20225": [
            {"promedio_global": 150.0, "total_registros": 20}
        ],
        "id-20224": [
            {"promedio_global": 140.0, "total_registros": 15}
        ],
    }

    monkeypatch.setattr(kpi_controller, "_obtener_database", lambda: database)
    monkeypatch.setattr(
        kpi_controller,
        "_obtener_periodo_anterior",
        lambda database, periodo: "20224",
    )

    def fake_aggregate(database, pipeline, collection="Fact_Resultados"):
        captured.append(pipeline)
        time_id = pipeline[0]["$match"]["$and"][0]["id_tiempo"]
        return results[time_id]

    monkeypatch.setattr(kpi_controller, "_ejecutar_agregacion", fake_aggregate)

    result = kpi_controller.calcular_kpi_global({"periodo": "20225"})

    assert len(captured) == 2
    assert all(not any("$lookup" in stage for stage in pipeline) for pipeline in captured)
    assert result["promedio_global"] == 150
    assert result["total_registros"] == 20
    assert result["comparativo_porcentual"] == 7.14
