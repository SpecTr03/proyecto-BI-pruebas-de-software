"""Pruebas de la medición de rendimiento de MongoDB."""

import pytest

from backend.app.routes import salud_bd


class FakeCollection:
    """Colección mínima que registra las consultas de referencia."""

    def __init__(self) -> None:
        self.calls = 0

    def count_documents(self, filtro: dict) -> None:
        assert filtro == {}
        self.calls += 1


def test_medir_consultas_ejecuta_cinco_consultas_y_promedia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collection = FakeCollection()
    tiempos = iter(
        [
            0.100,
            0.102,
            0.200,
            0.204,
            0.300,
            0.306,
            0.400,
            0.408,
            0.500,
            0.510,
        ]
    )
    monkeypatch.setattr(salud_bd.time, "perf_counter", lambda: next(tiempos))

    resultado = salud_bd._medir_consultas(collection)

    assert collection.calls == 5
    assert resultado["num_consultas_medidas"] == 5
    assert resultado["tiempo_promedio_consulta_ms"] == pytest.approx(6.0)
    assert resultado["tiempo_min_consulta_ms"] == pytest.approx(2.0)
    assert resultado["tiempo_max_consulta_ms"] == pytest.approx(10.0)
    assert (
        resultado["tiempo_min_consulta_ms"]
        <= resultado["tiempo_promedio_consulta_ms"]
        <= resultado["tiempo_max_consulta_ms"]
    )
