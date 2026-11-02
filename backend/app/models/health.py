"""Modelos Pydantic para el endpoint de salud."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Respuesta del chequeo de salud de la API."""

    status: str = Field(..., examples=["ok"], description="Estado de la API.")
    mongo: str = Field(
        ...,
        examples=["connected"],
        description="Estado de la conexión con MongoDB.",
    )
