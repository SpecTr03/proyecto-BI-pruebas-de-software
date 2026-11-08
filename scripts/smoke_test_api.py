"""Smoke test de los endpoints principales de la API SaberPro.

Qué hace:
    Ejecuta peticiones HTTP contra la API FastAPI y valida el estado y la
    estructura mínima de las respuestas de los endpoints principales. Mide el
    tiempo de cada petición, muestra un resumen con colores ANSI y devuelve un
    código de salida distinto de cero si alguna prueba falla.

Cómo ejecutarlo:
    python scripts/smoke_test_api.py
    python scripts/smoke_test_api.py --base-url http://localhost:8000

Requisito:
    El servidor FastAPI debe estar corriendo previamente. Por ejemplo:
        uvicorn app.main:app --env-file .env

Dependencia:
    requests
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any, Callable

try:
    import requests
except ImportError as exc:  # pragma: no cover - depende del entorno
    raise SystemExit(
        "Falta la dependencia 'requests'. Instálala con: pip install requests"
    ) from exc


DEFAULT_BASE_URL = "http://localhost:8000"
TIMEOUT_SECONDS = 10.0

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

NIVELES_DESEMPENO = ["Bajo", "Medio", "Alto", "Muy Alto"]

PREDICTION_PAYLOAD = {
    "genero": "F",
    "estrato": "Estrato 2",
    "educacion_padre": "Educación profesional completa",
    "educacion_madre": "Educación profesional completa",
    "tiene_internet": "Si",
    "tiene_computador": "Si",
    "caracter_academico": "UNIVERSIDAD",
    "metodo_programa": "PRESENCIAL",
    "depto_reside": "VALLE",
    "depto_institucion": "VALLE",
}

TestFunc = Callable[[requests.Session, str], None]


class ServidorNoDisponibleError(RuntimeError):
    """Se lanza cuando el servidor no acepta conexiones."""


def _short_response_text(response: requests.Response, limit: int = 200) -> str:
    """Compacta y recorta el cuerpo de una respuesta para mostrarlo en errores."""
    text = " ".join(response.text.split())
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def _assert_status(response: requests.Response, expected: int = 200) -> None:
    """Valida el código HTTP de una respuesta."""
    if response.status_code != expected:
        raise AssertionError(
            f"Se esperaba HTTP {expected}; se recibió {response.status_code}. "
            f"Cuerpo: {_short_response_text(response)}"
        )


def _response_json(response: requests.Response) -> dict[str, Any]:
    """Convierte la respuesta a JSON y valida que sea un objeto."""
    try:
        data = response.json()
    except ValueError as exc:
        raise AssertionError("La respuesta no contiene JSON válido.") from exc

    if not isinstance(data, dict):
        raise AssertionError(
            "Se esperaba un objeto JSON; se recibió "
            f"{type(data).__name__}."
        )
    return data


def _assert_positive_number(data: dict[str, Any], field: str) -> None:
    """Valida que un campo exista y sea un número mayor que cero."""
    value = data.get(field)
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or value <= 0
    ):
        raise AssertionError(
            f"'{field}' debe ser un número mayor que 0; se recibió: {value!r}."
        )


def test_health(session: requests.Session, base_url: str) -> None:
    """Valida GET /api/health."""
    response = session.get(f"{base_url}/api/health", timeout=TIMEOUT_SECONDS)
    _assert_status(response)
    data = _response_json(response)

    if data.get("status") != "ok":
        raise AssertionError(
            f"'status' debe ser 'ok'; se recibió: {data.get('status')!r}."
        )
    if data.get("mongo") != "connected":
        raise AssertionError(
            "'mongo' debe ser 'connected'; se recibió: "
            f"{data.get('mongo')!r}."
        )


def test_filtros_periodos(session: requests.Session, base_url: str) -> None:
    """Valida GET /api/filtros/periodos."""
    response = session.get(
        f"{base_url}/api/filtros/periodos",
        timeout=TIMEOUT_SECONDS,
    )
    _assert_status(response)
    data = _response_json(response)

    valores = data.get("valores")
    if not isinstance(valores, list):
        raise AssertionError(
            f"'valores' debe ser una lista; se recibió: {type(valores).__name__}."
        )
    if len(valores) < 1:
        raise AssertionError("'valores' debe contener al menos un elemento.")


def test_kpis_global(session: requests.Session, base_url: str) -> None:
    """Valida GET /api/kpis/global."""
    response = session.get(
        f"{base_url}/api/kpis/global",
        timeout=TIMEOUT_SECONDS,
    )
    _assert_status(response)
    data = _response_json(response)
    _assert_positive_number(data, "promedio_global")


def test_kpis_competencias(session: requests.Session, base_url: str) -> None:
    """Valida GET /api/kpis/competencias."""
    response = session.get(
        f"{base_url}/api/kpis/competencias",
        timeout=TIMEOUT_SECONDS,
    )
    _assert_status(response)
    data = _response_json(response)

    for field in (
        "razonamiento",
        "lectura",
        "ciudadanas",
        "escrita",
        "ingles",
    ):
        _assert_positive_number(data, field)


def test_salud_bd(session: requests.Session, base_url: str) -> None:
    """Valida GET /api/salud-bd."""
    response = session.get(
        f"{base_url}/api/salud-bd",
        timeout=TIMEOUT_SECONDS,
    )
    _assert_status(response)
    data = _response_json(response)

    if data.get("estado_conexion") != "conectado":
        raise AssertionError(
            "'estado_conexion' debe ser 'conectado'; se recibió: "
            f"{data.get('estado_conexion')!r}."
        )


def test_predecir(session: requests.Session, base_url: str) -> None:
    """Valida POST /api/predecir con un estudiante de ejemplo."""
    response = session.post(
        f"{base_url}/api/predecir",
        json=PREDICTION_PAYLOAD,
        timeout=TIMEOUT_SECONDS,
    )
    _assert_status(response)
    data = _response_json(response)

    _assert_positive_number(data, "puntaje_predicho")
    nivel = data.get("nivel_desempeno")
    if nivel not in NIVELES_DESEMPENO:
        raise AssertionError(
            "'nivel_desempeno' debe ser uno de "
            f"{NIVELES_DESEMPENO}; se recibió: {nivel!r}."
        )


TESTS: list[tuple[str, TestFunc]] = [
    ("GET /api/health", test_health),
    ("GET /api/filtros/periodos", test_filtros_periodos),
    ("GET /api/kpis/global", test_kpis_global),
    ("GET /api/kpis/competencias", test_kpis_competencias),
    ("GET /api/salud-bd", test_salud_bd),
    ("POST /api/predecir", test_predecir),
]


def _print_ok(name: str, elapsed_ms: float) -> None:
    """Imprime una prueba exitosa en verde."""
    print(f"{GREEN}[OK]{RESET} {name} - {elapsed_ms:.0f}ms")


def _print_fail(name: str, elapsed_ms: float, reason: str) -> None:
    """Imprime una prueba fallida en rojo junto con el motivo."""
    print(f"{RED}[FAIL]{RESET} {name} - {elapsed_ms:.0f}ms")
    print(f"       {RED}{reason}{RESET}")


def run_suite(base_url: str) -> tuple[int, int, float]:
    """Ejecuta todas las pruebas y devuelve pasadas, fallidas y tiempo total."""
    passed = 0
    failed = 0
    total_start = time.perf_counter()

    with requests.Session() as session:
        for name, test_func in TESTS:
            start = time.perf_counter()
            try:
                test_func(session, base_url)
            except requests.ConnectionError as exc:
                elapsed_ms = (time.perf_counter() - start) * 1000
                message = (
                    f"No se pudo conectar a {base_url}. "
                    "¿Está el servidor corriendo?"
                )
                _print_fail(name, elapsed_ms, message)
                raise ServidorNoDisponibleError(message) from exc
            except requests.RequestException as exc:
                elapsed_ms = (time.perf_counter() - start) * 1000
                _print_fail(name, elapsed_ms, f"Error de red/HTTP: {exc}")
                failed += 1
            except AssertionError as exc:
                elapsed_ms = (time.perf_counter() - start) * 1000
                _print_fail(name, elapsed_ms, str(exc))
                failed += 1
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - start) * 1000
                _print_fail(name, elapsed_ms, f"Error inesperado: {exc}")
                failed += 1
            else:
                elapsed_ms = (time.perf_counter() - start) * 1000
                _print_ok(name, elapsed_ms)
                passed += 1

    total_elapsed = time.perf_counter() - total_start
    return passed, failed, total_elapsed


def print_summary(passed: int, failed: int, total_elapsed: float) -> None:
    """Imprime el resumen final de la ejecución."""
    total = passed + failed

    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Total de pruebas ejecutadas: {total}")
    print(f"Total de pruebas pasadas: {passed}")
    print(f"Total de pruebas fallidas: {failed}")
    print(f"Tiempo total: {total_elapsed:.2f}s")

    if failed == 0:
        print(f"{GREEN}✅ Todas las pruebas pasaron{RESET}")
    else:
        print(f"{RED}❌ {failed} pruebas fallaron{RESET}")


def parse_args() -> argparse.Namespace:
    """Lee los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description=(
            "Smoke test de los endpoints principales de la API SaberPro."
        )
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"URL base de la API (default: {DEFAULT_BASE_URL}).",
    )
    return parser.parse_args()


def main() -> int:
    """Punto de entrada del smoke test."""
    args = parse_args()
    base_url = args.base_url.rstrip("/")

    print(f"Smoke test API SaberPro - {base_url}")
    print("-" * 60)

    try:
        passed, failed, total_elapsed = run_suite(base_url)
    except ServidorNoDisponibleError:
        return 1

    print_summary(passed, failed, total_elapsed)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
