"""Pruebas del KPI de distribución de niveles de inglés."""

from backend.app.controllers import kpi_controller


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


def test_calcular_kpi_ingles_devuelve_distribucion_y_porcentajes(
    monkeypatch,
) -> None:
    _mock_agregacion(
        monkeypatch,
        [
            {"_id": "-A1", "total": 30},
            {"_id": "A1", "total": 20},
            {"_id": "A2", "total": 50},
            {"_id": "B1", "total": 100},
            {"_id": "B2", "total": 50},
        ],
    )

    resultado = kpi_controller.calcular_kpi_ingles({})

    assert resultado == {
        "total_registros": 250,
        "distribucion": {
            "-A1": 30,
            "A1": 20,
            "A2": 50,
            "B1": 100,
            "B2": 50,
        },
        "porcentajes": {
            "-A1": 12.0,
            "A1": 8.0,
            "A2": 20.0,
            "B1": 40.0,
            "B2": 20.0,
        },
        "porcentaje_b1_bplus": 60.0,
    }


def test_calcular_kpi_ingles_sin_datos_devuelve_ceros(monkeypatch) -> None:
    _mock_agregacion(monkeypatch, [])

    resultado = kpi_controller.calcular_kpi_ingles({})

    assert resultado == {
        "total_registros": 0,
        "distribucion": {},
        "porcentajes": {},
        "porcentaje_b1_bplus": 0.0,
    }


def test_calcular_kpi_ingles_normaliza_variantes_y_omite_nulos(
    monkeypatch,
) -> None:
    _mock_agregacion(
        monkeypatch,
        [
            {"_id": "b1", "total": 10},
            {"_id": "B2", "total": 5},
            {"_id": "a1", "total": 5},
            {"_id": "-a1", "total": 10},
            {"_id": "a2", "total": 10},
            {"_id": None, "total": 999},
        ],
    )

    resultado = kpi_controller.calcular_kpi_ingles({})

    assert resultado["total_registros"] == 40
    assert resultado["distribucion"] == {
        "-A1": 10,
        "A1": 5,
        "A2": 10,
        "B1": 10,
        "B2": 5,
    }
    assert resultado["porcentajes"] == {
        "-A1": 25.0,
        "A1": 12.5,
        "A2": 25.0,
        "B1": 25.0,
        "B2": 12.5,
    }
    assert resultado["porcentaje_b1_bplus"] == 37.5


def test_calcular_kpi_ingles_porcentaje_b1_bplus_incluye_b2(
    monkeypatch,
) -> None:
    _mock_agregacion(
        monkeypatch,
        [
            {"_id": "A1", "total": 75},
            {"_id": "B2", "total": 25},
        ],
    )

    resultado = kpi_controller.calcular_kpi_ingles({})

    assert resultado["total_registros"] == 100
    assert resultado["distribucion"]["B2"] == 25
    assert resultado["porcentaje_b1_bplus"] == 25.0


def test_pipeline_ingles_usa_lookups_solo_cuando_son_necesarios(
    monkeypatch,
) -> None:
    ejecuciones: list[tuple[str, list[dict]]] = []
    _mock_agregacion(monkeypatch, [], ejecuciones)

    kpi_controller.calcular_kpi_ingles({})
    collection, pipeline = _get_ejecucion(ejecuciones)

    assert collection == "Fact_Resultados"
    assert not any("$lookup" in paso for paso in pipeline)
    assert pipeline[-1] == {
        "$group": {"_id": "$mod_ingles_desem", "total": {"$sum": 1}}
    }

    ejecuciones.clear()
    kpi_controller.calcular_kpi_ingles({"genero": "F"})
    _, pipeline_estudiante = _get_ejecucion(ejecuciones)

    assert any(
        paso.get("$lookup", {}).get("from") == "Dim_Estudiante"
        for paso in pipeline_estudiante
    )

    ejecuciones.clear()
    kpi_controller.calcular_kpi_ingles({"periodo": "20225"})
    _, pipeline_periodo = _get_ejecucion(ejecuciones)

    assert any(
        paso.get("$lookup", {}).get("from") == "Dim_Tiempo"
        for paso in pipeline_periodo
    )
    assert not any(
        paso.get("$lookup", {}).get("from") == "Dim_Estudiante"
        for paso in pipeline_periodo
    )
