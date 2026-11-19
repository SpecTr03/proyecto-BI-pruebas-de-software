from bson import ObjectId

from backend.app.builders.query_builder import QueryBuilder
from backend.app.constants import DASHBOARD_FILTER_FIELDS
from backend.app.controllers import comparativo_controller
from backend.app.controllers import distribucion_controller
from backend.app.controllers import estrato_controller
from backend.app.controllers import historico_controller
from backend.app.controllers import ranking_controller
from backend.app.controllers.kpi_controller import METRICAS_COMPETENCIAS
from scripts.populate_nosql import DocumentBuilder, create_dashboard_filter_indexes


def test_query_builder_creates_yearly_global_trend_pipeline() -> None:
    pipeline = (
        QueryBuilder()
        .filtrar_por_anio("2018")
        .filtrar_por_departamento("ANTIOQUIA")
        .build_global_trend(METRICAS_COMPETENCIAS)
    )

    assert pipeline[0] == {
        "$match": {
            "$and": [
                {"dashboard_filters.anio": {"$in": ["2018"]}},
                {"dashboard_filters.departamento": {"$in": ["antioquia"]}},
            ]
        }
    }
    assert not any("$lookup" in stage for stage in pipeline)
    assert any("$set" in stage and "_puntaje_global_registro" in stage["$set"] for stage in pipeline)
    assert pipeline[-1] == {"$sort": {"anio": 1}}
    group = next(stage["$group"] for stage in pipeline if "$group" in stage)
    assert group["_id"] == "$dashboard_filters.anio"
    assert "$avg" in group["promedio_global"]


def test_historical_filter_values_are_normalized_for_indexed_fields() -> None:
    pipeline = (
        QueryBuilder()
        .filtrar_por_estrato("2")
        .filtrar_por_genero(["F", "M"])
        .build_global_trend(METRICAS_COMPETENCIAS)
    )

    assert pipeline[0]["$match"]["$and"] == [
        {"dashboard_filters.estrato": {"$in": ["estrato 2"]}},
        {"dashboard_filters.genero": {"$in": ["f", "m"]}},
    ]


def test_document_builder_copies_normalized_dashboard_filter_values() -> None:
    builder = DocumentBuilder()
    dimension_ids = {
        name: ObjectId()
        for name in (
            "Dim_Tiempo",
            "Dim_Estudiante",
            "Dim_Institucion",
            "Dim_Programa",
            "Dim_Ubicacion_Examen",
        )
    }
    fact = builder.build_fact(
        {
            "ESTU_CONSECUTIVO": "test",
            "PERIODO": 20225,
            "ESTU_DEPTO_RESIDE": " ANTIOQUIA ",
            "ESTU_MCPIO_RESIDE": "MEDELLÍN",
            "INST_NOMBRE_INSTITUCION": "Universidad ABC",
            "INST_CARACTER_ACADEMICO": "Universidad",
            "ESTU_PRGM_ACADEMICO": "Ingeniería",
            "ESTU_METODO_PRGM": "Presencial",
            "ESTU_GENERO": "F",
            "FAMI_ESTRATOVIVIENDA": "2",
            "ESTU_NUCLEO_PREGRADO": "Ingeniería",
        },
        dimension_ids,
    )

    assert fact["dashboard_filters"] == {
        "anio": "2022",
        "departamento": "antioquia",
        "municipio": "medellín",
        "institucion": "universidad abc",
        "caracter_institucion": "universidad",
        "programa": "ingeniería",
        "metodo_programa": "presencial",
        "genero": "f",
        "estrato": "estrato 2",
        "grupo_referencia": "ingeniería",
    }


def test_etl_indexes_every_denormalized_dashboard_filter() -> None:
    class FakeCollection:
        def __init__(self) -> None:
            self.indexes: list[tuple[list[tuple[str, int]], dict[str, str]]] = []

        def create_index(self, keys, **options) -> None:
            self.indexes.append((keys, options))

    class FakeDatabase:
        def __init__(self) -> None:
            self.collection = FakeCollection()

        def __getitem__(self, collection_name: str) -> FakeCollection:
            assert collection_name == "Fact_Resultados"
            return self.collection

    database = FakeDatabase()
    create_dashboard_filter_indexes(database, "Fact_Resultados")

    assert {
        options["name"] for _, options in database.collection.indexes
    } == {
        f"ix_fact_dashboard_filter_{key}"
        for key in DASHBOARD_FILTER_FIELDS
    }


def test_global_trend_groups_by_denormalized_year_without_lookups() -> None:
    pipeline = QueryBuilder().build_global_trend(METRICAS_COMPETENCIAS)

    group = next(stage["$group"] for stage in pipeline if "$group" in stage)
    assert group["_id"] == "$dashboard_filters.anio"
    assert not any("$lookup" in stage for stage in pipeline)
    assert pipeline[-1] == {"$sort": {"anio": 1}}


def test_period_foreign_key_filter_runs_before_dimension_lookups() -> None:
    pipeline = (
        QueryBuilder()
        .filtrar_por_tiempo_id("period-object-id")
        .build_kpi_multi(METRICAS_COMPETENCIAS)
    )

    assert pipeline[0] == {"$match": {"$and": [{"id_tiempo": "period-object-id"}]}}
    assert not any("$lookup" in stage for stage in pipeline)


def test_calcular_historico_aplica_filtros_y_formatea_puntos(monkeypatch) -> None:
    captured: dict[str, object] = {}
    rows = [
        {"anio": "2018", "promedio_global": 149.827, "total_registros": 20},
        {"anio": "2019", "promedio_global": 151.2, "total_registros": 25},
    ]

    monkeypatch.setattr(historico_controller, "_obtener_database", lambda: object())
    monkeypatch.setattr(historico_controller, "get_dashboard_summary", lambda database, key: None)

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


def test_query_builder_groups_global_score_by_department() -> None:
    pipeline = QueryBuilder().build_global_by_department(METRICAS_COMPETENCIAS)

    assert not any("$lookup" in stage for stage in pipeline)
    group = next(stage["$group"] for stage in pipeline if "$group" in stage)
    assert group["_id"] == "$dashboard_filters.departamento"
    assert group["promedio_global"] == {"$avg": "$_puntaje_global_registro"}
    assert pipeline[-1] == {"$sort": {"departamento": 1}}


def test_department_distribution_normalizes_names_and_ignores_foreign_places(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        distribucion_controller,
        "_obtener_database",
        lambda: object(),
    )
    monkeypatch.setattr(
        distribucion_controller,
        "_ejecutar_agregacion",
        lambda database, pipeline, collection: [
            {"departamento": "Bogotá", "promedio_global": 155.126, "total_registros": 20},
            {"departamento": "NORTE SANTANDER", "promedio_global": 144.5, "total_registros": 10},
            {"departamento": "Miami", "promedio_global": 180, "total_registros": 2},
        ],
    )

    response = distribucion_controller.calcular_distribucion_departamental({})

    assert [item.model_dump() for item in response.datos] == [
        {"departamento": "bogota d.c.", "promedio_global": 155.13, "total_registros": 20},
        {"departamento": "norte de santander", "promedio_global": 144.5, "total_registros": 10},
    ]


def test_query_builder_groups_global_score_by_student_stratum() -> None:
    pipeline = QueryBuilder().build_global_by_stratum(METRICAS_COMPETENCIAS)

    assert pipeline[0]["$lookup"]["from"] == "Dim_Estudiante"
    group = next(stage["$group"] for stage in pipeline if "$group" in stage)
    assert group["_id"] == "$_estrato"
    assert group["promedio_global"] == {"$avg": "$_puntaje_global_registro"}


def test_calcular_desempeno_por_estrato_normaliza_y_ignora_fuera_de_rango(
    monkeypatch,
) -> None:
    rows = [
        {"estrato": "3", "promedio_global": 157.128, "total_registros": 30},
        {"estrato": "Estrato 1", "promedio_global": 141.5, "total_registros": 10},
        {"estrato": "1", "promedio_global": 142.5, "total_registros": 10},
        {"estrato": "Estrato 7", "promedio_global": 180, "total_registros": 2},
        {"estrato": "Sin estrato", "promedio_global": 120, "total_registros": 4},
    ]
    monkeypatch.setattr(estrato_controller, "_obtener_database", lambda: object())
    monkeypatch.setattr(
        estrato_controller,
        "get_dashboard_summary",
        lambda database, key: None,
    )
    monkeypatch.setattr(
        estrato_controller,
        "_ejecutar_agregacion",
        lambda database, pipeline, collection: rows,
    )

    response = estrato_controller.calcular_desempeno_por_estrato()

    assert [point.model_dump() for point in response.datos] == [
        {"estrato": "Estrato 1", "promedio_global": 142.0, "total_registros": 20},
        {"estrato": "Estrato 3", "promedio_global": 157.13, "total_registros": 30},
    ]


def test_comparativo_calcula_ies_y_grupo_nacional_con_filtros_correctos(
    monkeypatch,
) -> None:
    calls = []

    def fake_calcular(filtros):
        calls.append(filtros)
        total = 25 if "institucion" in filtros else 1000
        return {
            "razonamiento": 150.0,
            "lectura": 151.0,
            "ciudadanas": 149.0,
            "escrita": 152.0,
            "ingles": 153.0,
            "total_registros": total,
        }

    monkeypatch.setattr(
        comparativo_controller,
        "calcular_kpi_competencias",
        fake_calcular,
    )

    response = comparativo_controller.calcular_comparativo_competencias(
        "  Universidad ABC  ",
        "  INGENIERÍA  ",
    )

    assert calls == [
        {"institucion": "Universidad ABC", "grupo_referencia": "INGENIERÍA"},
        {"grupo_referencia": "INGENIERÍA"},
    ]
    assert response.institucion == "Universidad ABC"
    assert response.grupo_referencia == "INGENIERÍA"
    assert response.total_institucion == 25
    assert response.total_nacional == 1000
    assert response.promedios_institucion["ingles"] == 153


def test_query_builder_creates_official_institution_top_and_bottom_pipeline() -> None:
    pipeline = (
        QueryBuilder()
        .filtrar_por_tipo_institucion("OFICIAL")
        .build_institution_ranking(METRICAS_COMPETENCIAS)
    )

    match = next(stage["$match"] for stage in pipeline if "$match" in stage)
    assert match["$and"][0]["dim_institucion.origen"] == {
        "$regex": "^OFICIAL",
        "$options": "i",
    }
    groups = [stage["$group"] for stage in pipeline if "$group" in stage]
    assert groups[0]["_id"] == "$id_institucion"
    assert groups[1]["_id"] == "$_nombre_institucion"
    institution_lookup = next(
        index
        for index, stage in enumerate(pipeline)
        if stage.get("$lookup", {}).get("from") == "Dim_Institucion"
    )
    assert next(index for index, stage in enumerate(pipeline) if "$group" in stage) < institution_lookup
    facet = pipeline[-1]["$facet"]
    assert facet["top"][0]["$sort"]["promedio_global"] == -1
    assert facet["top"][1] == {"$limit": 10}
    assert facet["bottom"][0]["$sort"]["promedio_global"] == 1
    assert facet["bottom"][1] == {"$limit": 10}
    assert facet["bottom"][2]["$sort"]["promedio_global"] == -1


def test_query_builder_rejects_unknown_institution_type() -> None:
    import pytest

    with pytest.raises(ValueError, match="OFICIAL"):
        QueryBuilder().filtrar_por_tipo_institucion("MIXTA")


def test_calcular_ranking_instituciones_formats_both_rankings(monkeypatch) -> None:
    rows = [
        {
            "top": [
                {
                    "institucion": "Universidad A",
                    "promedio_global": 180.126,
                    "total_registros": 20,
                }
            ],
            "bottom": [
                {
                    "institucion": "Universidad B",
                    "promedio_global": 120,
                    "total_registros": 8,
                }
            ],
        }
    ]
    monkeypatch.setattr(ranking_controller, "_obtener_database", lambda: object())
    monkeypatch.setattr(
        ranking_controller,
        "get_dashboard_summary",
        lambda database, key: None,
    )
    monkeypatch.setattr(
        ranking_controller,
        "_ejecutar_agregacion",
        lambda database, pipeline, collection: rows,
    )

    response = ranking_controller.calcular_ranking_instituciones("OFICIAL")

    assert response.tipo == "OFICIAL"
    assert response.top[0].model_dump() == {
        "institucion": "Universidad A",
        "promedio_global": 180.13,
        "total_registros": 20,
    }
    assert response.bottom[0].institucion == "Universidad B"
