"""Modelos Pydantic para la salud de la base de datos MongoDB."""

from pydantic import BaseModel, Field


class SaludBDResponse(BaseModel):
    """Métricas de salud y rendimiento de la base de datos."""

    estado_conexion: str = Field(
        ...,
        examples=["conectado"],
        description="Estado de la conexión con MongoDB.",
    )
    colecciones: dict[str, int] = Field(
        default_factory=dict,
        description="Total de documentos por colección.",
        examples=[
            {
                "Fact_Resultados": 1209063,
                "Dim_Tiempo": 14,
                "Dim_Estudiante": 500000,
                "Dim_Institucion": 300,
                "Dim_Programa": 1500,
                "Dim_Ubicacion_Examen": 1100,
            }
        ],
    )
    tiempo_promedio_consulta_ms: float = Field(
        ...,
        ge=0,
        examples=[12.345],
        description="Tiempo de una agregación simple en milisegundos.",
    )
    espacio_total_mb: float = Field(
        ...,
        ge=0,
        examples=[850.75],
        description="Espacio total ocupado por la base de datos en MB.",
    )
    total_documentos: int = Field(
        ...,
        ge=0,
        examples=[1711977],
        description="Suma de documentos de todas las colecciones.",
    )
