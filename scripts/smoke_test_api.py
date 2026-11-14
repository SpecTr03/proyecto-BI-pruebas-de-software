"""Smoke test de los endpoints principales de la API SaberPro.

Qué hace:
    Ejecuta peticiones HTTP contra la API FastAPI y valida el estado y la
    estructura mínima de las respuestas. Mide el tiempo de cada petición,
    muestra un resumen con colores ANSI y devuelve un código de salida distinto
    de cero si alguna prueba falla.

Cómo ejecutarlo:
    python scripts/smoke_test_api.py
    python scripts/smoke_test_api.py --base-url http://localhost:8000
    python scripts/smoke_test_api.py --email usuario@universidad.edu.co --password "..."

    También se pueden usar las variables de entorno SMOKE_TEST_EMAIL y
    SMOKE_TEST_PASSWORD.

    Sin credenciales solo se ejecuta la prueba pública GET /api/health.
    Para ejecutar las pruebas autenticadas y negativas se deben proporcionar
    las credenciales de un usuario activo.

Requisito:
    El servidor FastAPI debe estar corriendo previamente. Por ejemplo:
        uvicorn app.main:app --env-file .env

Dependencia:
    requests
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
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
YELLOW = "\033[93m"
RESET = "\033[0m"

NIVELES_DESEMPENO = ["Bajo", "Medio", "Alto", "Muy Alto"]
ROLES_VALIDOS = {"Administrador", "Analista", "Investigador"}
INDICADORES_VALIDOS = {"Deficiente", "Aceptable", "Sobresaliente"}
INVALID_PASSWORD = "smoke-test-password-invalida"

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


@dataclass(frozen=True)
class TestContext:
    """Datos compartidos por las pruebas."""

    base_url: str
    email: str = ""
    password: str = ""


TestFunc = Callable[[requests.Session, TestContext], None]


@dataclass
class GroupResult:
    """Resultado acumulado de un grupo de pruebas."""

    passed: int = 0
    failed: int = 0
    executed: bool = True


@dataclass
class SuiteSummary:
    """Resumen completo de la ejecución."""

    public: GroupResult
    authenticated: GroupResult
    negative: GroupResult
    total_elapsed: float

    @property
    def passed(self) -> int:
        return self.public.passed + self.authenticated.passed + self.negative.passed

    @property
    def failed(self) -> int:
        return self.public.failed + self.authenticated.failed + self.negative.failed


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


def _assert_indicadores(data: dict[str, Any]) -> None:
    """Valida el mapa de indicadores cualitativos de competencias."""
    indicadores = data.get("indicadores")
    if not isinstance(indicadores, dict):
        raise AssertionError(
            "'indicadores' debe ser un objeto JSON; se recibió: "
            f"{type(indicadores).__name__}."
        )

    competencias = {"razonamiento", "lectura", "ciudadanas", "escrita", "ingles"}
    if set(indicadores) != competencias:
        raise AssertionError(
            "'indicadores' debe contener exactamente las claves "
            f"{sorted(competencias)}; se recibió: {sorted(indicadores)}."
        )

    for competencia, indicador in indicadores.items():
        if indicador not in INDICADORES_VALIDOS:
            raise AssertionError(
                f"El indicador de '{competencia}' debe estar en "
                f"{sorted(INDICADORES_VALIDOS)}; se recibió: {indicador!r}."
            )


def _assert_indicadores(data: dict[str, Any]) -> None:
    """Valida el mapa de indicadores cualitativos de competencias."""
    indicadores = data.get("indicadores")
    if not isinstance(indicadores, dict):
        raise AssertionError(
            "'indicadores' debe ser un objeto JSON; se recibió: "
            f"{type(indicadores).__name__}."
        )

    competencias = {"razonamiento", "lectura", "ciudadanas", "escrita", "ingles"}
    if set(indicadores) != competencias:
        raise AssertionError(
            "'indicadores' debe contener exactamente las claves "
            f"{sorted(competencias)}; se recibió: {sorted(indicadores)}."
        )

    for competencia, indicador in indicadores.items():
        if indicador not in INDICADORES_VALIDOS:
            raise AssertionError(
                f"El indicador de '{competencia}' debe estar en "
                f"{sorted(INDICADORES_VALIDOS)}; se recibió: {indicador!r}."
            )


def _assert_indicadores(data: dict[str, Any]) -> None:
    """Valida el mapa de indicadores cualitativos de competencias."""
    indicadores = data.get("indicadores")
    if not isinstance(indicadores, dict):
        raise AssertionError(
            "'indicadores' debe ser un objeto JSON; se recibió: "
            f"{type(indicadores).__name__}."
        )

    competencias = {"razonamiento", "lectura", "ciudadanas", "escrita", "ingles"}
    if set(indicadores) != competencias:
        raise AssertionError(
            "'indicadores' debe contener exactamente las claves "
            f"{sorted(competencias)}; se recibió: {sorted(indicadores)}."
        )

    for competencia, indicador in indicadores.items():
        if indicador not in INDICADORES_VALIDOS:
            raise AssertionError(
                f"El indicador de '{competencia}' debe estar en "
                f"{sorted(INDICADORES_VALIDOS)}; se recibió: {indicador!r}."
            )


def test_health(session: requests.Session, context: TestContext) -> None:
    """Valida GET /api/health sin autenticación."""
    response = session.get(f"{context.base_url}/api/health", timeout=TIMEOUT_SECONDS)
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


def test_login(session: requests.Session, context: TestContext) -> None:
    """Valida POST /api/auth/login y configura el token en la sesión."""
    response = session.post(
        f"{context.base_url}/api/auth/login",
        json={"email": context.email, "password": context.password},
        timeout=TIMEOUT_SECONDS,
    )
    _assert_status(response)
    data = _response_json(response)

    token = data.get("access_token")
    token_type = data.get("token_type")
    if not isinstance(token, str) or not token.strip():
        raise AssertionError("La respuesta de login no contiene 'access_token'.")
    if token_type != "Bearer":
        raise AssertionError(
            f"'token_type' debe ser 'Bearer'; se recibió: {token_type!r}."
        )

    session.headers["Authorization"] = f"Bearer {token}"


def test_auth_me(session: requests.Session, context: TestContext) -> None:
    """Valida GET /api/auth/me con el token configurado en la sesión."""
    response = session.get(
        f"{context.base_url}/api/auth/me",
        timeout=TIMEOUT_SECONDS,
    )
    _assert_status(response)
    data = _response_json(response)

    if not data.get("id"):
        raise AssertionError("La respuesta de /api/auth/me no contiene 'id'.")
    if not data.get("email"):
        raise AssertionError("La respuesta de /api/auth/me no contiene 'email'.")
    role = data.get("role")
    if role not in ROLES_VALIDOS:
        raise AssertionError(
            "'role' debe ser uno de "
            f"{sorted(ROLES_VALIDOS)}; se recibió: {role!r}."
        )
    if not isinstance(data.get("permissions"), list):
        raise AssertionError(
            "La respuesta de /api/auth/me no contiene una lista de permisos."
        )


def test_filtros_periodos(session: requests.Session, context: TestContext) -> None:
    """Valida GET /api/filtros/periodos."""
    response = session.get(
        f"{context.base_url}/api/filtros/periodos",
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


def test_kpis_global(session: requests.Session, context: TestContext) -> None:
    """Valida GET /api/kpis/global."""
    response = session.get(
        f"{context.base_url}/api/kpis/global",
        timeout=TIMEOUT_SECONDS,
    )
    _assert_status(response)
    data = _response_json(response)
    _assert_positive_number(data, "promedio_global")


def test_kpis_competencias(session: requests.Session, context: TestContext) -> None:
    """Valida GET /api/kpis/competencias."""
    response = session.get(
        f"{context.base_url}/api/kpis/competencias",
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

    indicadores = data.get("indicadores")
    if not isinstance(indicadores, dict):
        raise AssertionError(
            "'indicadores' debe ser un objeto JSON; se recibió: "
            f"{type(indicadores).__name__}."
        )

    competencias = {"razonamiento", "lectura", "ciudadanas", "escrita", "ingles"}
    if set(indicadores) != competencias:
        raise AssertionError(
            "'indicadores' debe contener exactamente las claves "
            f"{sorted(competencias)}; se recibió: {sorted(indicadores)}."
        )

    for competencia, indicador in indicadores.items():
        if indicador not in INDICADORES_VALIDOS:
            raise AssertionError(
                f"El indicador de '{competencia}' debe estar en "
                f"{sorted(INDICADORES_VALIDOS)}; se recibió: {indicador!r}."
            )


def test_salud_bd(session: requests.Session, context: TestContext) -> None:
    """Valida GET /api/salud-bd."""
    response = session.get(
        f"{context.base_url}/api/salud-bd",
        timeout=TIMEOUT_SECONDS,
    )
    _assert_status(response)
    data = _response_json(response)

    if data.get("estado_conexion") != "conectado":
        raise AssertionError(
            "'estado_conexion' debe ser 'conectado'; se recibió: "
            f"{data.get('estado_conexion')!r}."
        )

    tiempo_promedio = data.get("tiempo_promedio_consulta_ms")
    if (
        not isinstance(tiempo_promedio, (int, float))
        or isinstance(tiempo_promedio, bool)
        or not 0 < tiempo_promedio < 5000
    ):
        raise AssertionError(
            "'tiempo_promedio_consulta_ms' debe ser mayor que 0 y menor "
            f"que 5000; se recibió: {tiempo_promedio!r}."
        )

    if data.get("num_consultas_medidas") != 5:
        raise AssertionError(
            "'num_consultas_medidas' debe ser 5; se recibió: "
            f"{data.get('num_consultas_medidas')!r}."
        )

    tiempo_min = data.get("tiempo_min_consulta_ms")
    tiempo_max = data.get("tiempo_max_consulta_ms")
    for nombre, valor in (
        ("tiempo_min_consulta_ms", tiempo_min),
        ("tiempo_max_consulta_ms", tiempo_max),
    ):
        if (
            not isinstance(valor, (int, float))
            or isinstance(valor, bool)
            or valor < 0
        ):
            raise AssertionError(
                f"'{nombre}' debe ser un número no negativo; "
                f"se recibió: {valor!r}."
            )

    if not tiempo_min <= tiempo_promedio <= tiempo_max:
        raise AssertionError(
            "Se esperaba tiempo_min_consulta_ms <= "
            "tiempo_promedio_consulta_ms <= tiempo_max_consulta_ms; "
            f"se recibió: {tiempo_min!r}, {tiempo_promedio!r}, {tiempo_max!r}."
        )


def test_predecir(session: requests.Session, context: TestContext) -> None:
    """Valida POST /api/predecir con un estudiante de ejemplo."""
    response = session.post(
        f"{context.base_url}/api/predecir",
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


def test_kpis_global_sin_token(
    session: requests.Session,
    context: TestContext,
) -> None:
    """Valida que GET /api/kpis/global rechace una petición sin token."""
    response = session.get(
        f"{context.base_url}/api/kpis/global",
        timeout=TIMEOUT_SECONDS,
    )
    _assert_status(response, 401)


def test_login_password_incorrecta(
    session: requests.Session,
    context: TestContext,
) -> None:
    """Valida que POST /api/auth/login rechace una contraseña incorrecta."""
    if not context.email:
        raise AssertionError(
            "Se requiere '--email' para la prueba negativa de login."
        )

    response = session.post(
        f"{context.base_url}/api/auth/login",
        json={"email": context.email, "password": INVALID_PASSWORD},
        timeout=TIMEOUT_SECONDS,
    )
    _assert_status(response, 401)


PUBLIC_TESTS: list[tuple[str, TestFunc]] = [
    ("GET /api/health", test_health),
]

AUTHENTICATED_TESTS: list[tuple[str, TestFunc]] = [
    ("GET /api/auth/me", test_auth_me),
    ("GET /api/filtros/periodos", test_filtros_periodos),
    ("GET /api/kpis/global", test_kpis_global),
    ("GET /api/kpis/competencias", test_kpis_competencias),
    ("GET /api/salud-bd", test_salud_bd),
    ("POST /api/predecir", test_predecir),
]

NEGATIVE_TESTS: list[tuple[str, TestFunc]] = [
    ("GET /api/kpis/global sin token", test_kpis_global_sin_token),
    (
        "POST /api/auth/login con contraseña incorrecta",
        test_login_password_incorrecta,
    ),
]


def _print_ok(name: str, elapsed_ms: float) -> None:
    """Imprime una prueba exitosa en verde."""
    print(f"{GREEN}[OK]{RESET} {name} - {elapsed_ms:.0f}ms")


def _print_fail(name: str, elapsed_ms: float, reason: str) -> None:
    """Imprime una prueba fallida en rojo junto con el motivo."""
    print(f"{RED}[FAIL]{RESET} {name} - {elapsed_ms:.0f}ms")
    print(f"       {RED}{reason}{RESET}")


def _run_group(
    title: str,
    tests: list[tuple[str, TestFunc]],
    session: requests.Session,
    context: TestContext,
) -> GroupResult:
    """Ejecuta un grupo de pruebas y devuelve su resultado."""
    print(f"\n{title}")
    print("-" * 60)

    result = GroupResult()
    for name, test_func in tests:
        start = time.perf_counter()
        try:
            test_func(session, context)
        except requests.ConnectionError as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            message = (
                f"No se pudo conectar a {context.base_url}. "
                "¿Está el servidor corriendo?"
            )
            _print_fail(name, elapsed_ms, message)
            raise ServidorNoDisponibleError(message) from exc
        except requests.RequestException as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            _print_fail(name, elapsed_ms, f"Error de red/HTTP: {exc}")
            result.failed += 1
        except AssertionError as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            _print_fail(name, elapsed_ms, str(exc))
            result.failed += 1
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            _print_fail(name, elapsed_ms, f"Error inesperado: {exc}")
            result.failed += 1
        else:
            elapsed_ms = (time.perf_counter() - start) * 1000
            _print_ok(name, elapsed_ms)
            result.passed += 1

    return result


def run_suite(context: TestContext, credentials_provided: bool) -> SuiteSummary:
    """Ejecuta las pruebas públicas y, si hay credenciales, las demás."""
    total_start = time.perf_counter()

    with requests.Session() as public_session:
        public_result = _run_group(
            "PRUEBAS PÚBLICAS",
            PUBLIC_TESTS,
            public_session,
            context,
        )

    authenticated_result = GroupResult(executed=credentials_provided)
    negative_result = GroupResult(executed=credentials_provided)

    if credentials_provided:
        with requests.Session() as authenticated_session:
            login_result = _run_group(
                "AUTENTICACIÓN",
                [("POST /api/auth/login", test_login)],
                authenticated_session,
                context,
            )
            authenticated_result.passed += login_result.passed
            authenticated_result.failed += login_result.failed

            if login_result.failed == 0:
                authenticated_tests = _run_group(
                    "PRUEBAS AUTENTICADAS",
                    AUTHENTICATED_TESTS,
                    authenticated_session,
                    context,
                )
                authenticated_result.passed += authenticated_tests.passed
                authenticated_result.failed += authenticated_tests.failed
            else:
                print(
                    f"{YELLOW}[WARN]{RESET} Se omiten las pruebas autenticadas "
                    "porque el login falló."
                )

        with requests.Session() as anonymous_session:
            negative_result = _run_group(
                "PRUEBAS NEGATIVAS",
                NEGATIVE_TESTS,
                anonymous_session,
                context,
            )

    total_elapsed = time.perf_counter() - total_start
    return SuiteSummary(
        public=public_result,
        authenticated=authenticated_result,
        negative=negative_result,
        total_elapsed=total_elapsed,
    )


def _print_group_summary(label: str, result: GroupResult) -> None:
    """Imprime el resumen de un grupo de pruebas."""
    if not result.executed:
        print(f"{label}: no ejecutadas (sin credenciales)")
        return
    print(
        f"{label}: {result.passed} pasadas, "
        f"{result.failed} fallidas"
    )


def print_summary(summary: SuiteSummary) -> None:
    """Imprime el resumen final de la ejecución."""
    total = summary.passed + summary.failed

    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    _print_group_summary("Pruebas públicas", summary.public)
    _print_group_summary("Pruebas autenticadas", summary.authenticated)
    _print_group_summary("Pruebas negativas", summary.negative)
    print("-" * 60)
    print(f"Total de pruebas ejecutadas: {total}")
    print(f"Total de pruebas pasadas: {summary.passed}")
    print(f"Total de pruebas fallidas: {summary.failed}")
    print(f"Tiempo total: {summary.total_elapsed:.2f}s")

    if summary.failed == 0:
        print(f"{GREEN}Todas las pruebas ejecutadas pasaron{RESET}")
    else:
        print(f"{RED}{summary.failed} pruebas fallaron{RESET}")


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
    parser.add_argument(
        "--email",
        default=os.getenv("SMOKE_TEST_EMAIL"),
        help=(
            "Correo del usuario de prueba. También se puede definir "
            "SMOKE_TEST_EMAIL."
        ),
    )
    parser.add_argument(
        "--password",
        default=os.getenv("SMOKE_TEST_PASSWORD"),
        help=(
            "Contraseña del usuario de prueba. También se puede definir "
            "SMOKE_TEST_PASSWORD."
        ),
    )
    return parser.parse_args()


def main() -> int:
    """Punto de entrada del smoke test."""
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    email = (args.email or "").strip()
    password = args.password or ""
    credentials_provided = bool(email and password)

    print(f"Smoke test API SaberPro - {base_url}")
    print("-" * 60)

    if not credentials_provided:
        print(
            f"{YELLOW}[WARN]{RESET} No se proporcionaron credenciales. "
            "Solo se ejecutará la prueba pública /api/health."
        )
        print(
            "       Usa --email y --password o define "
            "SMOKE_TEST_EMAIL y SMOKE_TEST_PASSWORD."
        )

    context = TestContext(
        base_url=base_url,
        email=email,
        password=password,
    )

    try:
        summary = run_suite(context, credentials_provided)
    except ServidorNoDisponibleError:
        return 1

    print_summary(summary)
    return 0 if summary.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
