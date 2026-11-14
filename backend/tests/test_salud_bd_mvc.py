"""Pruebas MVC para el endpoint de salud de MongoDB."""

from backend.app.controllers import salud_bd_controller
from backend.app.models.salud import SaludBDResponse
from backend.app.routes import salud_bd


def test_route_salud_bd_delega_en_controller(monkeypatch) -> None:
    esperado = SaludBDResponse(
        estado_conexion="conectado",
        colecciones={"Fact_Resultados": 1},
        tiempo_promedio_consulta_ms=10.0,
        tiempo_min_consulta_ms=5.0,
        tiempo_max_consulta_ms=15.0,
        num_consultas_medidas=5,
        espacio_total_mb=1.0,
        total_documentos=1,
    )
    llamadas: list[bool] = []

    def fake_obtener_salud_bd() -> SaludBDResponse:
        llamadas.append(True)
        return esperado

    monkeypatch.setattr(
        salud_bd_controller,
        "obtener_salud_bd",
        fake_obtener_salud_bd,
    )
    monkeypatch.setattr(salud_bd, "mongo_connection", None, raising=False)

    resultado = salud_bd.obtener_salud_bd()

    assert resultado is esperado
    assert llamadas == [True]
