"""Builder de pipelines de agregación para el Esquema de Estrella.

``QueryBuilder`` acumula filtros sobre las dimensiones y construye un pipeline
de MongoDB con los ``$lookup`` necesarios. Los filtros son opcionales y
fluidos; cada método devuelve la misma instancia para permitir encadenamiento.

Los nombres de campos coinciden con los documentos generados por
``scripts/populate_nosql.py``.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any

# Relación entre cada dimensión y su colección/llave foránea en MongoDB.
DIMENSION_LOOKUPS: dict[str, dict[str, Any]] = {
    "tiempo": {
        "from": "Dim_Tiempo",
        "localField": "id_tiempo",
        "foreignField": "_id",
        "as": "dim_tiempo",
    },
    "estudiante": {
        "from": "Dim_Estudiante",
        "localField": "id_estudiante",
        "foreignField": "_id",
        "as": "dim_estudiante",
    },
    "institucion": {
        "from": "Dim_Institucion",
        "localField": "id_institucion",
        "foreignField": "_id",
        "as": "dim_institucion",
    },
    "programa": {
        "from": "Dim_Programa",
        "localField": "id_programa",
        "foreignField": "_id",
        "as": "dim_programa",
    },
    "ubicacion": {
        "from": "Dim_Ubicacion_Examen",
        "localField": "id_ubicacion_examen",
        "foreignField": "_id",
        "as": "dim_ubicacion",
    },
}

# Orden determinista de los lookups para que el pipeline sea reproducible.
DIMENSION_ORDER = ("tiempo", "estudiante", "institucion", "programa", "ubicacion")

# Métricas numéricas permitidas para KPIs de promedio.
NUMERIC_METRICS = frozenset(
    {
        "mod_razona_cuantitat_punt",
        "mod_comuni_escrita_punt",
        "mod_lectura_critica_punt",
        "mod_ingles_punt",
        "mod_competen_ciudada_punt",
    }
)

# Campos de la tabla de hechos que se devuelven en ``build()``.
FACT_FIELDS = (
    "estu_consecutivo",
    "id_tiempo",
    "id_estudiante",
    "id_institucion",
    "id_programa",
    "id_ubicacion_examen",
    "mod_razona_cuantitat_punt",
    "mod_comuni_escrita_punt",
    "mod_lectura_critica_punt",
    "mod_ingles_punt",
    "mod_competen_ciudada_punt",
    "mod_comuni_escrita_desem",
    "mod_ingles_desem",
)


class QueryBuilder:
    """Construye consultas dinámicas para ``Fact_Resultados``.

    Ejemplo:
        >>> pipeline = (
        ...     QueryBuilder()
        ...     .filtrar_por_periodo("20225")
        ...     .filtrar_por_genero("F")
        ...     .build_kpi("mod_razona_cuantitat_punt")
        ... )
    """

    def __init__(self) -> None:
        """Inicializa un builder sin filtros."""
        self._conditions: list[dict[str, Any]] = []
        self._required_dimensions: set[str] = set()

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_values(value: Any) -> list[str]:
        """Normaliza un valor escalar o una colección a una lista de textos.

        Los valores vacíos, ``None`` y cadenas en blanco se ignoran.
        """
        raw_values = (
            value
            if isinstance(value, (list, tuple, set, frozenset))
            else [value]
        )
        cleaned: list[str] = []
        for item in raw_values:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                cleaned.append(text)
        return cleaned

    @staticmethod
    def _normalize_yes_no(value: str) -> str:
        """Convierte variantes de verdadero/falso a ``Si`` o ``No``."""
        normalized = value.strip().lower()
        if normalized in {"true", "1", "si", "sí", "yes", "y"}:
            return "Si"
        if normalized in {"false", "0", "no", "n"}:
            return "No"
        return value.strip()

    @staticmethod
    def _normalize_estrato(value: str) -> str:
        """Convierte ``2`` en ``Estrato 2`` y deja el texto original si ya viene."""
        text = value.strip()
        return f"Estrato {text}" if text.isdigit() else text

    def _build_condition(
        self,
        field: str,
        value: Any,
        normalizer: Callable[[str], str] | None = None,
    ) -> dict[str, Any] | None:
        """Crea una condición ``$match`` insensible a mayúsculas.

        Soporta un valor escalar o una lista de valores. En el segundo caso
        genera un ``$or`` con una expresión regular por cada valor.
        """
        values = self._clean_values(value)
        if not values:
            return None

        if normalizer is not None:
            values = [normalizer(item) for item in values]

        if len(values) == 1:
            return {
                field: {
                    "$regex": f"^{re.escape(values[0])}$",
                    "$options": "i",
                }
            }

        return {
            "$or": [
                {
                    field: {
                        "$regex": f"^{re.escape(item)}$",
                        "$options": "i",
                    }
                }
                for item in values
            ]
        }

    def _add_filter(
        self,
        dimension: str,
        field: str,
        value: Any,
        normalizer: Callable[[str], str] | None = None,
    ) -> "QueryBuilder":
        """Agrega un filtro y registra la dimensión que necesita ``$lookup``."""
        lookup = DIMENSION_LOOKUPS[dimension]
        condition = self._build_condition(
            f"{lookup['as']}.{field}", value, normalizer
        )
        if condition is not None:
            self._required_dimensions.add(dimension)
            self._conditions.append(condition)
        return self

    # ------------------------------------------------------------------
    # Filtros públicos (10 filtros del dashboard + filtros adicionales)
    # ------------------------------------------------------------------

    def filtrar_por_periodo(self, periodo: Any) -> "QueryBuilder":
        """Filtra por periodo académico, por ejemplo ``20225``."""
        return self._add_filter("tiempo", "periodo", periodo)

    def filtrar_por_departamento(self, depto: Any) -> "QueryBuilder":
        """Filtra por departamento de residencia del estudiante."""
        return self._add_filter("estudiante", "depto_reside", depto)

    def filtrar_por_municipio(self, municipio: Any) -> "QueryBuilder":
        """Filtra por municipio de residencia del estudiante."""
        return self._add_filter("estudiante", "mcpio_reside", municipio)

    def filtrar_por_institucion(self, nombre: Any) -> "QueryBuilder":
        """Filtra por nombre de la institución de educación superior."""
        return self._add_filter("institucion", "nombre_institucion", nombre)

    def filtrar_por_caracter_institucion(self, caracter: Any) -> "QueryBuilder":
        """Filtra por carácter académico de la institución."""
        return self._add_filter("institucion", "caracter_academico", caracter)

    def filtrar_por_programa(self, programa: Any) -> "QueryBuilder":
        """Filtra por nombre del programa académico."""
        return self._add_filter("programa", "programa_academico", programa)

    def filtrar_por_metodo_programa(self, metodo: Any) -> "QueryBuilder":
        """Filtra por metodología del programa (presencial, virtual, etc.)."""
        return self._add_filter("programa", "metodo_programa", metodo)

    def filtrar_por_genero(self, genero: Any) -> "QueryBuilder":
        """Filtra por género del estudiante (``F``/``M``)."""
        return self._add_filter("estudiante", "genero", genero)

    def filtrar_por_estrato(self, estrato: Any) -> "QueryBuilder":
        """Filtra por estrato socioeconómico.

        Acepta ``2`` o ``"Estrato 2"``; ambos se normalizan al valor guardado.
        """
        return self._add_filter(
            "estudiante", "estrato", estrato, self._normalize_estrato
        )

    def filtrar_por_grupo_referencia(self, nucleo: Any) -> "QueryBuilder":
        """Filtra por núcleo de conocimiento/grupo de referencia."""
        return self._add_filter("programa", "nucleo_pregrado", nucleo)

    def filtrar_por_internet(self, tiene: Any) -> "QueryBuilder":
        """Filtra por tenencia de internet (``True``/``False`` o ``Si``/``No``)."""
        return self._add_filter(
            "estudiante", "tiene_internet", tiene, self._normalize_yes_no
        )

    def filtrar_por_computador(self, tiene: Any) -> "QueryBuilder":
        """Filtra por tenencia de computador (``True``/``False`` o ``Si``/``No``)."""
        return self._add_filter(
            "estudiante", "tiene_computador", tiene, self._normalize_yes_no
        )

    def filtrar_por_departamento_examen(self, depto: Any) -> "QueryBuilder":
        """Filtra por departamento donde se presentó el examen."""
        return self._add_filter("ubicacion", "depto_presentacion", depto)

    def filtrar_por_municipio_examen(self, municipio: Any) -> "QueryBuilder":
        """Filtra por municipio donde se presentó el examen."""
        return self._add_filter("ubicacion", "mcpio_presentacion", municipio)

    # ------------------------------------------------------------------
    # Construcción del pipeline
    # ------------------------------------------------------------------

    def reset(self) -> "QueryBuilder":
        """Limpia filtros y dimensiones acumuladas."""
        self._conditions.clear()
        self._required_dimensions.clear()
        return self

    def _base_pipeline(self) -> list[dict[str, Any]]:
        """Devuelve los ``$lookup`` y el ``$match`` comunes a todos los KPIs."""
        pipeline: list[dict[str, Any]] = [
            {"$lookup": DIMENSION_LOOKUPS[name]}
            for name in DIMENSION_ORDER
            if name in self._required_dimensions
        ]

        if self._conditions:
            pipeline.append({"$match": {"$and": self._conditions}})

        return pipeline

    def build(self) -> list[dict[str, Any]]:
        """Construye un pipeline que devuelve documentos de hechos filtrados.

        Returns:
            Pipeline de agregación listo para ``collection.aggregate()``.
        """
        pipeline = self._base_pipeline()
        projection = {"_id": 0}
        projection.update({field: 1 for field in FACT_FIELDS})
        pipeline.append({"$project": projection})
        return pipeline

    def build_kpi(
        self,
        metric: str = "mod_razona_cuantitat_punt",
    ) -> list[dict[str, Any]]:
        """Construye un pipeline que calcula el promedio de una métrica.

        Args:
            metric: Nombre de una métrica numérica de ``Fact_Resultados``.

        Returns:
            Pipeline con ``$group`` y ``$project`` listo para ejecutar.

        Raises:
            ValueError: Si la métrica no está permitida.
        """
        if metric not in NUMERIC_METRICS:
            allowed = ", ".join(sorted(NUMERIC_METRICS))
            raise ValueError(
                f"Métrica no permitida: '{metric}'. Métricas válidas: {allowed}"
            )

        pipeline = self._base_pipeline()
        pipeline.extend(
            [
                {
                    "$group": {
                        "_id": None,
                        "value": {"$avg": f"${metric}"},
                        "total_records": {"$sum": 1},
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "value": 1,
                        "total_records": 1,
                    }
                },
            ]
        )
        return pipeline

    def build_kpi_multi(
        self,
        metrics: Mapping[str, str],
    ) -> list[dict[str, Any]]:
        """Construye un pipeline que calcula varias métricas en una sola pasada.

        El resultado incluye un campo por cada alias de ``metrics``, el total de
        registros y ``promedio_global`` calculado como la suma de los promedios
        dividida entre la cantidad de métricas.

        Args:
            metrics: Mapa ``{alias_respuesta: campo_metrica}``. Los campos deben
                pertenecer a ``NUMERIC_METRICS``.

        Returns:
            Pipeline con ``$group`` y ``$project`` listo para ejecutar.

        Raises:
            ValueError: Si no se indican métricas, se repite un alias reservado
                o alguna métrica no está permitida.
        """
        if not metrics:
            raise ValueError("Debe indicar al menos una métrica.")

        reserved = {"total_registros", "promedio_global"}
        repeated = reserved.intersection(metrics)
        if repeated:
            aliases = ", ".join(sorted(repeated))
            raise ValueError(f"Alias reservado(s): {aliases}")

        invalid = [
            metric for metric in metrics.values() if metric not in NUMERIC_METRICS
        ]
        if invalid:
            allowed = ", ".join(sorted(NUMERIC_METRICS))
            raise ValueError(
                "Métrica(s) no permitida(s): "
                f"{', '.join(sorted(set(invalid)))}. "
                f"Métricas válidas: {allowed}"
            )

        aliases = list(metrics)
        group: dict[str, Any] = {
            "_id": None,
            "total_registros": {"$sum": 1},
        }
        projection: dict[str, Any] = {
            "_id": 0,
            "total_registros": 1,
        }

        for alias, metric in metrics.items():
            group[alias] = {"$avg": f"${metric}"}
            projection[alias] = 1

        projection["promedio_global"] = {
            "$divide": [
                {"$sum": [f"${alias}" for alias in aliases]},
                len(aliases),
            ]
        }

        pipeline = self._base_pipeline()
        pipeline.extend(
            [
                {"$group": group},
                {"$project": projection},
            ]
        )
        return pipeline

    def __repr__(self) -> str:
        """Representación útil para depuración."""
        return (
            f"QueryBuilder(conditions={len(self._conditions)}, "
            f"dimensions={sorted(self._required_dimensions)})"
        )
