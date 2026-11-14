"""Pruebas MVC para los endpoints de filtros."""

import pytest

from backend.app.models.filtro import FiltroResponse
from backend.app.routes import filtros


@pytest.mark.parametrize(
    ("endpoint", "coleccion", "campo"),
    [
        ("listar_periodos", "Dim_Tiempo", "periodo"),
        ("listar_departamentos", "Dim_Estudiante", "depto_reside"),
        ("listar_municipios", "Dim_Estudiante", "mcpio_reside"),
        ("listar_instituciones", "Dim_Institucion", "nombre_institucion"),
        ("listar_caracteres", "Dim_Institucion", "caracter_academico"),
        ("listar_programas", "Dim_Programa", "programa_academico"),
        ("listar_metodos", "Dim_Programa", "metodo_programa"),
        ("listar_generos", "Dim_Estudiante", "genero"),
        ("listar_estratos", "Dim_Estudiante", "estrato"),
        ("listar_nucleos", "Dim_Programa", "nucleo_pregrado"),
    ],
)
def test_endpoints_filtros_delegan_en_controller(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
    coleccion: str,
    campo: str,
) -> None:
    llamadas: list[tuple[str, str]] = []
    esperado = FiltroResponse(valores=["2025"], total=1)

    def fake_obtener_valores_distintos(
        coleccion_arg: str,
        campo_arg: str,
    ) -> FiltroResponse:
        llamadas.append((coleccion_arg, campo_arg))
        return esperado

    monkeypatch.setattr(
        filtros,
        "obtener_valores_distintos",
        fake_obtener_valores_distintos,
    )
    monkeypatch.setattr(filtros, "mongo_connection", None, raising=False)

    resultado = getattr(filtros, endpoint)()

    assert resultado == esperado
    assert llamadas == [(coleccion, campo)]
