"""Comparación de competencias entre una IES y su grupo de referencia nacional."""

from fastapi import HTTPException, status

from ..models.grafica import ComparativoCompetenciasResponse
from .kpi_controller import calcular_kpi_competencias


def calcular_comparativo_competencias(
    institucion: str,
    grupo_referencia: str,
) -> ComparativoCompetenciasResponse:
    """Calcula los promedios de competencias para la IES y el grupo nacional."""
    institution_name = institucion.strip()
    reference_group = grupo_referencia.strip()
    if not institution_name or not reference_group:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La institución y el grupo de referencia son obligatorios.",
        )

    institution_result = calcular_kpi_competencias({
        "institucion": institution_name,
        "grupo_referencia": reference_group,
    })
    national_result = calcular_kpi_competencias({
        "grupo_referencia": reference_group,
    })
    competency_names = ("razonamiento", "lectura", "ciudadanas", "escrita", "ingles")

    return ComparativoCompetenciasResponse(
        institucion=institution_name,
        grupo_referencia=reference_group,
        promedios_institucion={
            name: institution_result[name] for name in competency_names
        },
        promedios_nacionales={
            name: national_result[name] for name in competency_names
        },
        total_institucion=institution_result["total_registros"],
        total_nacional=national_result["total_registros"],
    )
