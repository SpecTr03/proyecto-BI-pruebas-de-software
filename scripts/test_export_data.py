from scripts.export_data import build_filter, flatten_document, make_json_safe


def test_build_filter_maps_dashboard_names() -> None:
    result = build_filter({
        "year": 2018,
        "department": "BOGOTA",
        "institution": "UNIVERSIDAD",
        "unsupported": "ignored",
    })
    assert result == {
        "year": 2018,
        "geography.department": "BOGOTA",
        "institution.inst_nombre_institucion": "UNIVERSIDAD",
    }


def test_build_filter_ignores_empty_values() -> None:
    assert build_filter({"year": None, "department": "", "period": "20225"}) == {
        "period": "20225",
    }


def test_flatten_document_uses_dot_notation() -> None:
    result = flatten_document({
        "year": 2018,
        "geography": {"department": "BOGOTA"},
        "scores": {"mod_ingles_punt": 220},
    })
    assert result == {
        "year": 2018,
        "geography.department": "BOGOTA",
        "scores.mod_ingles_punt": 220,
    }


def test_make_json_safe_handles_object_id() -> None:
    from bson import ObjectId

    identifier = ObjectId()
    assert make_json_safe(identifier) == str(identifier)
