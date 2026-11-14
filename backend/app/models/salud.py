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
        examples=[238.47],
        description=(
            "Promedio en milisegundos de 5 mediciones de "
            "``count_documents({})`` sobre ``Fact_Resultados``, "
            "descartando la primera por cold start."
        ),
    )
    tiempo_min_consulta_ms: float = Field(
        ...,
        ge=0,
        examples=[120.15],
        description="Tiempo mínimo en milisegundos de las 5 mediciones.",
    )
    tiempo_max_consulta_ms: float = Field(
        ...,
        ge=0,
        examples=[450.82],
        description="Tiempo máximo en milisegundos de las 5 mediciones.",
    )
    num_consultas_medidas: int = Field(
        ...,
        ge=1,
        examples=[5],
        description="Cantidad de mediciones usadas para calcular el promedio.",
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
