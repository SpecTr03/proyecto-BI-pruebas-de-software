"""Modelos Pydantic para la predicción del puntaje global de Saber Pro."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PrediccionInput(BaseModel):
    """Datos socioeconómicos y académicos usados por el modelo."""

    genero: str = Field(
        ...,
        examples=["F"],
        description="Género del estudiante (F/M).",
    )
    estrato: str = Field(
        ...,
        examples=["Estrato 2", "2"],
        description="Estrato socioeconómico; acepta 'Estrato 2' o '2'.",
    )
    educacion_padre: str = Field(
        ...,
        examples=["Educación profesional completa"],
        description="Máximo nivel educativo del padre.",
    )
    educacion_madre: str = Field(
        ...,
        examples=["Educación profesional completa"],
        description="Máximo nivel educativo de la madre.",
    )
    tiene_internet: str = Field(
        ...,
        examples=["Si", "No"],
        description="Tenencia de internet en el hogar.",
    )
    tiene_computador: str = Field(
        ...,
        examples=["Si", "No"],
        description="Tenencia de computador en el hogar.",
    )
    caracter_academico: str = Field(
        ...,
        examples=["UNIVERSIDAD"],
        description="Carácter académico de la institución.",
    )
    metodo_programa: str = Field(
        ...,
        examples=["PRESENCIAL"],
        description="Metodología del programa académico.",
    )
    depto_reside: str = Field(
        ...,
        examples=["VALLE"],
        description="Departamento de residencia del estudiante.",
    )
    depto_institucion: str = Field(
        ...,
        examples=["VALLE"],
        description="Departamento de la institución de educación superior.",
    )


class PrediccionResponse(BaseModel):
    """Resultado de la predicción del puntaje global."""

    puntaje_predicho: float = Field(
        ...,
        ge=0,
        le=300,
        examples=[148.72],
        description="Puntaje global estimado en el rango de 0 a 300.",
    )
    nivel_desempeno: str = Field(
        ...,
        examples=["Medio"],
        description="Nivel de desempeño: Bajo, Medio, Alto o Muy Alto.",
    )
    confianza: float | None = Field(
        default=None,
        ge=0,
        le=1,
        examples=[None],
        description=(
            "Confianza de la predicción cuando el modelo la expone; "
            "``None`` si no está disponible."
        ),
    )
    probabilidad_superar_media_nacional: float = Field(
        ...,
        ge=0,
        le=100,
        examples=[62.45],
        description=(
            "Probabilidad estimada, en porcentaje, de superar la media "
            "nacional de Saber Pro."
        ),
    )
    media_nacional: float = Field(
        ...,
        ge=0,
        le=300,
        examples=[148.72],
        description="Media nacional usada como referencia.",
    )
    probabilidad_riesgo_quintil_inferior: float = Field(
        ...,
        ge=0,
        le=100,
        examples=[38.2],
        description="Porcentaje estimado de riesgo de quedar en el quintil inferior.",
    )
    nivel_riesgo: str = Field(
        ...,
        examples=["Medio"],
        description="Nivel de riesgo académico: Bajo, Medio o Alto.",
    )
    umbral_quintil_inferior: float = Field(
        ...,
        ge=0,
        le=300,
        examples=[125.6],
        description="Puntaje límite del 20% inferior de la distribución.",
    )
