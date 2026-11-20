"""Pruebas del KPI de cobertura socioeconómica."""

from backend.app.controllers import kpi_controller
from backend.app.routes import kpis as kpis_routes
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _mock_agregacion(
    monkeypatch,
    documentos: list[dict],
    ejecuciones: list[tuple[str, list[dict]]] | None = None,
) -> None:
    monkeypatch.setattr(kpi_controller, "_obtener_database", lambda: object())

    def fake_ejecutar(database, pipeline, collection="Fact_Resultados"):
        if ejecuciones is not None:
            ejecuciones.append((collection, pipeline))
        return documentos

    monkeypatch.setattr(
        kpi_controller,
        "_ejecutar_agregacion",
        fake_ejecutar,
    )


def _get_ejecucion(
    ejecuciones: list[tuple[str, list[dict]]],
) -> tuple[str, list[dict]]:
    assert len(ejecuciones) == 1
    return ejecuciones[0]


def test_calcular_kpi_cobertura_calcula_total_y_porcentaje(
    monkeypatch,
) -> None:
    ejecuciones: list[tuple[str, list[dict]]] = []
    _mock_agregacion(
        monkeypatch,
        [
            {"_id": "Estrato 1", "total": 30},
            {"_id": "Estrato 2", "total": 20},
            {"_id": "Estrato 3", "total": 50},
        ],
        ejecuciones,
    )

    resultado = kpi_controller.calcular_kpi_cobertura({})

    assert resultado["total_registros"] == 100
    assert resultado["porcentaje_estratos_1_2"] == 50.0
    assert resultado["distribucion_estratos"] == {
        "Estrato 1": 30,
        "Estrato 2": 20,
        "Estrato 3": 50,
    }

    collection, pipeline = _get_ejecucion(ejecuciones)
    assert collection == "Dim_Estudiante"
    assert not any("$lookup" in paso for paso in pipeline)
    assert pipeline[-1] == {
        "$group": {"_id": "$estrato", "total": {"$sum": 1}}
    }


def test_calcular_kpi_cobertura_con_filtro_estudiante_usa_dim_estudiante(
    monkeypatch,
) -> None:
    ejecuciones: list[tuple[str, list[dict]]] = []
    _mock_agregacion(monkeypatch, [], ejecuciones)

    kpi_controller.calcular_kpi_cobertura({"genero": "F"})

    collection, pipeline = _get_ejecucion(ejecuciones)
    assert collection == "Dim_Estudiante"
    assert not any("$lookup" in paso for paso in pipeline)

    match = next(paso for paso in pipeline if "$match" in paso)
    assert any(
        "genero" in condicion
        for condicion in match["$match"].get("$and", [])
    )
    assert pipeline[-1] == {
        "$group": {"_id": "$estrato", "total": {"$sum": 1}}
    }


def test_calcular_kpi_cobertura_con_estrato_usa_dim_estudiante(
    monkeypatch,
) -> None:
    ejecuciones: list[tuple[str, list[dict]]] = []
    _mock_agregacion(monkeypatch, [], ejecuciones)

    kpi_controller.calcular_kpi_cobertura({"estrato": "2"})

    collection, pipeline = _get_ejecucion(ejecuciones)
    assert collection == "Dim_Estudiante"
    assert not any("$lookup" in paso for paso in pipeline)

    match = next(paso for paso in pipeline if "$match" in paso)
    assert any(
        condicion.get("estrato", {}).get("$options") == "i"
        and condicion.get("estrato", {})
        .get("$regex", "")
        .replace("\\", "")
        == "^Estrato 2$"
        for condicion in match["$match"].get("$and", [])
    )


def test_calcular_kpi_cobertura_con_filtro_de_hecho_agrupa_ids_antes_del_lookup(
    monkeypatch,
) -> None:
    ejecuciones: list[tuple[str, list[dict]]] = []
    _mock_agregacion(monkeypatch, [], ejecuciones)

    kpi_controller.calcular_kpi_cobertura({"periodo": "20225"})

    collection, pipeline = _get_ejecucion(ejecuciones)
    assert collection == "Fact_Resultados"

    time_lookup_index = next(
        index
        for index, paso in enumerate(pipeline)
        if paso.get("$lookup", {}).get("from") == "Dim_Tiempo"
    )
    time_match_index = next(
        index
        for index, paso in enumerate(pipeline)
        if "$match" in paso
        and any(
            "dim_tiempo.periodo" in condicion
            for condicion in paso["$match"].get("$and", [])
        )
    )
    id_group_index = next(
        index
        for index, paso in enumerate(pipeline)
        if paso.get("$group", {}).get("_id") == "$id_estudiante"
    )
    assert time_lookup_index < time_match_index < id_group_index

    student_index = next(
        index
        for index, paso in enumerate(pipeline)
        if paso.get("$lookup", {}).get("from") == "Dim_Estudiante"
    )
    assert id_group_index < student_index

    student_lookup = pipeline[student_index]["$lookup"]
    assert student_lookup["localField"] == "_id"
    assert student_lookup["pipeline"] == [
        {"$project": {"_id": 1, "estrato": 1}}
    ]

    final_group_index = next(
        index
        for index, paso in enumerate(pipeline)
        if paso.get("$group", {}).get("_id") == "$dim_estudiante.estrato"
    )
    assert student_index < final_group_index
    assert pipeline[final_group_index]["$group"]["total"] == {
        "$sum": "$total"
    }


def test_calcular_kpi_cobertura_con_filtro_mixto_proyecta_campos_estudiante(
    monkeypatch,
) -> None:
    ejecuciones: list[tuple[str, list[dict]]] = []
    _mock_agregacion(monkeypatch, [], ejecuciones)

    kpi_controller.calcular_kpi_cobertura(
        {"periodo": "20225", "genero": "F"}
    )

    collection, pipeline = _get_ejecucion(ejecuciones)
    assert collection == "Fact_Resultados"

    id_group_index = next(
        index
        for index, paso in enumerate(pipeline)
        if paso.get("$group", {}).get("_id") == "$id_estudiante"
    )
    student_index = next(
        index
        for index, paso in enumerate(pipeline)
        if paso.get("$lookup", {}).get("from") == "Dim_Estudiante"
    )
    assert id_group_index < student_index

    student_lookup = pipeline[student_index]["$lookup"]
    assert student_lookup["pipeline"] == [
        {"$project": {"_id": 1, "estrato": 1, "genero": 1}}
    ]

    student_match_index = next(
        index
        for index, paso in enumerate(pipeline)
        if "$match" in paso
        and any(
            "dim_estudiante.genero" in condicion
            for condicion in paso["$match"].get("$and", [])
        )
    )
    assert student_index < student_match_index


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


def test_calcular_kpi_cobertura_unifica_variantes_de_sin_estrato(
    monkeypatch,
) -> None:
    _mock_agregacion(
        monkeypatch,
        [
            {"_id": "Sin Estrato", "total": 5654},
            {"_id": "Sin estrato", "total": 52163},
        ],
    )

    resultado = kpi_controller.calcular_kpi_cobertura({})

    assert resultado["total_registros"] == 57817
    assert resultado["porcentaje_estratos_1_2"] == 0.0
    assert resultado["distribucion_estratos"] == {"Sin estrato": 57817}


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
