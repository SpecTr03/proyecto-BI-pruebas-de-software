"""Cálculo geográfico del puntaje global por departamento."""

from collections.abc import Mapping
from typing import Any

from ..builders.query_builder import QueryBuilder
from ..models.grafica import DepartamentoResultado, DistribucionDepartamentalResponse
from .kpi_controller import (
    FACT_COLLECTION,
    METRICAS_COMPETENCIAS,
    _ejecutar_agregacion,
    _obtener_database,
    _redondear,
)

DEPARTMENT_ALIASES = {
    "bogota": "bogota d.c.",
    "bogotá": "bogota d.c.",
    "norte santander": "norte de santander",
    "san andres": "san andres y providencia",
    "valle": "valle del cauca",
}

COLOMBIA_DEPARTMENT_NAMES = frozenset(
    {
        "amazonas",
        "antioquia",
        "arauca",
        "atlantico",
        "bogota d.c.",
        "bolivar",
        "boyaca",
        "caldas",
        "caqueta",
        "casanare",
        "cauca",
        "cesar",
        "choco",
        "cordoba",
        "cundinamarca",
        "guainia",
        "guaviare",
        "huila",
        "la guajira",
        "magdalena",
        "meta",
        "narino",
        "norte de santander",
        "putumayo",
        "quindio",
        "risaralda",
        "san andres y providencia",
        "santander",
        "sucre",
        "tolima",
        "valle del cauca",
        "vaupes",
        "vichada",
    }
)


def _normalizar_departamento_colombia(value: Any) -> str | None:
    text = str(value).strip().lower()
    if not text:
        return None
    normalized = (
        text.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )
    normalized = DEPARTMENT_ALIASES.get(normalized, normalized)
    return normalized if normalized in COLOMBIA_DEPARTMENT_NAMES else None


def calcular_distribucion_departamental(
    filtros: Mapping[str, Any],
) -> DistribucionDepartamentalResponse:
    builder = (
        QueryBuilder()
        .filtrar_por_anio(filtros.get("anio"))
        .filtrar_por_municipio(filtros.get("municipio"))
        .filtrar_por_institucion(filtros.get("institucion"))
        .filtrar_por_caracter_institucion(filtros.get("caracter_institucion"))
        .filtrar_por_programa(filtros.get("programa"))
        .filtrar_por_metodo_programa(filtros.get("metodo_programa"))
        .filtrar_por_genero(filtros.get("genero"))
        .filtrar_por_estrato(filtros.get("estrato"))
        .filtrar_por_grupo_referencia(filtros.get("grupo_referencia"))
    )
    database = _obtener_database()
    result = _ejecutar_agregacion(
        database,
        builder.build_global_by_department(METRICAS_COMPETENCIAS),
        FACT_COLLECTION,
    )
    datos = []
    for document in result:
        department = _normalizar_departamento_colombia(document.get("departamento"))
        total_records = int(document.get("total_registros", 0))
        if department is None or total_records <= 0:
            continue
        datos.append(
            DepartamentoResultado(
                departamento=department,
                promedio_global=_redondear(document.get("promedio_global")),
                total_registros=total_records,
            )
        )
    return DistribucionDepartamentalResponse(datos=datos)
