"""Constantes compartidas por los cálculos analíticos."""

DASHBOARD_FILTER_FIELDS: dict[str, str] = {
    "anio": "dashboard_filters.anio",
    "departamento": "dashboard_filters.departamento",
    "municipio": "dashboard_filters.municipio",
    "institucion": "dashboard_filters.institucion",
    "caracter_institucion": "dashboard_filters.caracter_institucion",
    "programa": "dashboard_filters.programa",
    "metodo_programa": "dashboard_filters.metodo_programa",
    "genero": "dashboard_filters.genero",
    "estrato": "dashboard_filters.estrato",
    "grupo_referencia": "dashboard_filters.grupo_referencia",
}

METRICAS_COMPETENCIAS: dict[str, str] = {
    "razonamiento": "mod_razona_cuantitat_punt",
    "lectura": "mod_lectura_critica_punt",
    "ciudadanas": "mod_competen_ciudada_punt",
    "escrita": "mod_comuni_escrita_punt",
    "ingles": "mod_ingles_punt",
}


def normalize_dashboard_filter_value(
    filter_key: str,
    value: object,
) -> str | None:
    """Normaliza filtros de lectura rápida para coincidir con valores del ETL."""
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None
    if filter_key == "estrato" and text.isdigit():
        text = f"Estrato {text}"
    return text.casefold()
