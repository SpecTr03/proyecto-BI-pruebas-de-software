from backend.app.builders.query_builder import QueryBuilder
from backend.app.controllers import historico_controller
from backend.app.controllers.kpi_controller import METRICAS_COMPETENCIAS


def test_query_builder_creates_yearly_global_trend_pipeline() -> None:
    pipeline = (
        QueryBuilder()
        .filtrar_por_anio("2018")
        .filtrar_por_departamento("ANTIOQUIA")
        .build_global_trend(METRICAS_COMPETENCIAS)
    )

    assert pipeline[0]["$lookup"]["from"] == "Dim_Tiempo"
    assert any("$match" in stage for stage in pipeline)
    assert any("$set" in stage and "_puntaje_global_registro" in stage["$set"] for stage in pipeline)
    assert pipeline[-1] == {"$sort": {"anio": 1}}
    group = next(stage["$group"] for stage in pipeline if "$group" in stage)
    assert group["_id"]["$substrBytes"][1:] == [0, 4]
    assert "promedio_global" in group


def test_calcular_historico_aplica_filtros_y_formatea_puntos(monkeypatch) -> None:
    captured: dict[str, object] = {}
    rows = [
        {"anio": "2018", "promedio_global": 149.827, "total_registros": 20},
        {"anio": "2019", "promedio_global": 151.2, "total_registros": 25},
    ]

    monkeypatch.setattr(historico_controller, "_obtener_database", lambda: object())

    def fake_aggregate(database, pipeline, collection):
        captured["pipeline"] = pipeline
        captured["collection"] = collection
        return rows

    monkeypatch.setattr(historico_controller, "_ejecutar_agregacion", fake_aggregate)

    response = historico_controller.calcular_historico(
        {
            "departamento": "ANTIOQUIA",
            "municipio": "MEDELLIN",
            "institucion": "UNIVERSIDAD",
            "caracter_institucion": "UNIVERSIDAD",
            "programa": "MEDICINA",
            "metodo_programa": "PRESENCIAL",
            "genero": "F",
            "estrato": "2",
            "grupo_referencia": "SALUD",
        },
        anio="2018",
    )

    assert [point.model_dump() for point in response.puntos] == [
        {"anio": "2018", "promedio_global": 149.83, "total_registros": 20},
        {"anio": "2019", "promedio_global": 151.2, "total_registros": 25},
    ]
    assert response.filtros["anio"] == "2018"
    assert captured["collection"] == "Fact_Resultados"
    pipeline = captured["pipeline"]
    match = next(stage["$match"] for stage in pipeline if "$match" in stage)
    assert len(match["$and"]) == 10


def test_filter_year_endpoint_returns_distinct_years(monkeypatch) -> None:
    from backend.app.models.filtro import FiltroResponse
    from backend.app.routes import filtros

    monkeypatch.setattr(
        filtros,
        "obtener_valores_distintos",
        lambda collection, field: FiltroResponse(
            valores=["20183", "20184", "20191", "20225"],
            total=4,
        ),
    )

    assert filtros.listar_anios() == FiltroResponse(
        valores=["2018", "2019", "2022"],
        total=3,
    )
