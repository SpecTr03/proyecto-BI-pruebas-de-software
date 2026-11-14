"""Endpoint de salud y rendimiento de la base de datos MongoDB."""

from fastapi import APIRouter, Depends

from ..auth import require_permission
from ..controllers import salud_bd_controller
from ..models.salud import SaludBDResponse

router = APIRouter(
    prefix="/salud-bd",
    tags=["Salud BD"],
    dependencies=[Depends(require_permission("dashboard:read"))],
)


@router.get(
    "",
    response_model=SaludBDResponse,
    summary="Salud y rendimiento de la base de datos MongoDB",
    responses={
        503: {
            "description": "MongoDB no disponible o error al consultar métricas",
        }
    },
)
def obtener_salud_bd() -> SaludBDResponse:
    """Devuelve las métricas de salud delegando en ``salud_bd_controller``.

    El controller mide ``count_documents({})`` sobre ``Fact_Resultados``,
    descarta una consulta de calentamiento y calcula promedio, mínimo y máximo
    sobre 5 mediciones.
    """
    return salud_bd_controller.obtener_salud_bd()
