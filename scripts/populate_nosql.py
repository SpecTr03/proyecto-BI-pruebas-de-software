"""Carga un CSV depurado de Saber Pro en MongoDB con un Esquema de Estrella.

Colecciones:
    Fact_Resultados, Dim_Tiempo, Dim_Estudiante, Dim_Institucion,
    Dim_Programa y Dim_Ubicacion_Examen.

La limpieza y el reporte post-ETL se realizan en el notebook
``notebooks/resultados-saber-pro-analisis.ipynb``. Este script recibe el CSV
limpio y se ocupa únicamente de transformarlo al esquema estrella y cargarlo.

Patrones y requisitos implementados:
    - Singleton para la conexión a MongoDB.
    - Builder para construir documentos de hechos y dimensiones.
    - Inserción de hechos por lotes de 10.000 con insert_many(ordered=False).
    - Upsert idempotente de dimensiones.
    - Índices para los filtros del dashboard.
    - Manejo de errores por lote y resumen final de la carga.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import threading
import time

from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
from bson import ObjectId
from pymongo import ASCENDING, MongoClient, ReplaceOne
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import (
    BulkWriteError,
    ConnectionFailure,
    OperationFailure,
    PyMongoError,
)
from pymongo.results import BulkWriteResult

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

DEFAULT_CSV = Path(__file__).resolve().parents[1] / "data" / "Resultados_Saber_Pro_limpio.csv"
DEFAULT_MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DEFAULT_DATABASE = os.getenv("MONGO_DATABASE", "SaberProDB")
DEFAULT_FACT_COLLECTION = "Fact_Resultados"
DEFAULT_BATCH_SIZE = 10_000
LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"

DIM_COLLECTIONS = (
    "Dim_Tiempo",
    "Dim_Estudiante",
    "Dim_Institucion",
    "Dim_Programa",
    "Dim_Ubicacion_Examen",
)

# Campo MongoDB -> columna CSV. Solo se leen las columnas necesarias.
TIME_FIELDS = {"periodo": "PERIODO"}

STUDENT_FIELDS = {
    "genero": "ESTU_GENERO",
    "fecha_nacimiento": "ESTU_FECHANACIMIENTO",
    "nacionalidad": "ESTU_NACIONALIDAD",
    "pais_reside": "ESTU_PAIS_RESIDE",
    "depto_reside": "ESTU_DEPTO_RESIDE",
    "mcpio_reside": "ESTU_MCPIO_RESIDE",
    "privado_libertad": "ESTU_PRIVADO_LIBERTAD",
    "estudiante": "ESTU_ESTUDIANTE",
    "horas_trabaja": "ESTU_HORASSEMANATRABAJA",
    "educacion_padre": "FAMI_EDUCACIONPADRE",
    "educacion_madre": "FAMI_EDUCACIONMADRE",
    "estrato": "FAMI_ESTRATOVIVIENDA",
    "tiene_computador": "FAMI_TIENECOMPUTADOR",
    "tiene_internet": "FAMI_TIENEINTERNET",
    "valor_matricula": "ESTU_VALORMATRICULAUNIVERSIDAD",
    "pago_beca": "ESTU_PAGOMATRICULABECA",
    "pago_credito": "ESTU_PAGOMATRICULACREDITO",
    "pago_padres": "ESTU_PAGOMATRICULAPADRES",
    "pago_propio": "ESTU_PAGOMATRICULAPROPIO",
}

INSTITUTION_FIELDS = {
    "nombre_institucion": "INST_NOMBRE_INSTITUCION",
    "caracter_academico": "INST_CARACTER_ACADEMICO",
    "origen": "INST_ORIGEN",
    "cole_termino": "ESTU_COLE_TERMINO",
    "depto_institucion": "ESTU_INST_DEPARTAMENTO",
    "mcpio_institucion": "ESTU_INST_MUNICIPIO",
}

PROGRAM_FIELDS = {
    "nucleo_pregrado": "ESTU_NUCLEO_PREGRADO",
    "programa_academico": "ESTU_PRGM_ACADEMICO",
    "metodo_programa": "ESTU_METODO_PRGM",
}

EXAM_LOCATION_FIELDS = {
    "depto_presentacion": "ESTU_DEPTO_PRESENTACION",
    "mcpio_presentacion": "ESTU_MCPIO_PRESENTACION",
}

METRIC_FIELDS = {
    "mod_razona_cuantitat_punt": "MOD_RAZONA_CUANTITAT_PUNT",
    "mod_comuni_escrita_punt": "MOD_COMUNI_ESCRITA_PUNT",
    "mod_lectura_critica_punt": "MOD_LECTURA_CRITICA_PUNT",
    "mod_ingles_punt": "MOD_INGLES_PUNT",
    "mod_competen_ciudada_punt": "MOD_COMPETEN_CIUDADA_PUNT",
}

TEXT_METRIC_FIELDS = {
    "mod_comuni_escrita_desem": "MOD_COMUNI_ESCRITA_DESEM",
    "mod_ingles_desem": "MOD_INGLES_DESEM",
}

REQUIRED_COLUMNS = {"PERIODO", "ESTU_CONSECUTIVO"}
ALL_COLUMNS = sorted(
    set(TIME_FIELDS.values())
    | set(STUDENT_FIELDS.values())
    | set(INSTITUTION_FIELDS.values())
    | set(PROGRAM_FIELDS.values())
    | set(EXAM_LOCATION_FIELDS.values())
    | set(METRIC_FIELDS.values())
    | set(TEXT_METRIC_FIELDS.values())
    | REQUIRED_COLUMNS
)

FACT_INDEXES = (
    ([("estu_consecutivo", ASCENDING)], {"unique": True, "name": "ux_fact_consecutivo"}),
    ([("id_tiempo", ASCENDING)], {"name": "ix_fact_id_tiempo"}),
    ([("id_estudiante", ASCENDING)], {"name": "ix_fact_id_estudiante"}),
    ([("id_institucion", ASCENDING)], {"name": "ix_fact_id_institucion"}),
    ([("id_programa", ASCENDING)], {"name": "ix_fact_id_programa"}),
    ([("id_ubicacion_examen", ASCENDING)], {"name": "ix_fact_id_ubicacion"}),
    (
        [("id_tiempo", ASCENDING), ("id_institucion", ASCENDING)],
        {"name": "ix_fact_tiempo_institucion"},
    ),
)

DIM_INDEXES = {
    "Dim_Tiempo": (
        ([("periodo", ASCENDING)], {"unique": True, "name": "ux_dim_tiempo_periodo"}),
    ),
    "Dim_Estudiante": (
        ([("genero", ASCENDING)], {"name": "ix_dim_estudiante_genero"}),
        ([("depto_reside", ASCENDING)], {"name": "ix_dim_estudiante_depto"}),
        ([("mcpio_reside", ASCENDING)], {"name": "ix_dim_estudiante_mcpio"}),
        ([("estrato", ASCENDING)], {"name": "ix_dim_estudiante_estrato"}),
        ([("tiene_internet", ASCENDING)], {"name": "ix_dim_estudiante_internet"}),
        ([("tiene_computador", ASCENDING)], {"name": "ix_dim_estudiante_computador"}),
        (
            [("depto_reside", ASCENDING), ("mcpio_reside", ASCENDING)],
            {"name": "ix_dim_estudiante_geo"},
        ),
    ),
    "Dim_Institucion": (
        ([("nombre_institucion", ASCENDING)], {"name": "ix_dim_institucion_nombre"}),
        ([("caracter_academico", ASCENDING)], {"name": "ix_dim_institucion_caracter"}),
        ([("depto_institucion", ASCENDING)], {"name": "ix_dim_institucion_depto"}),
        ([("mcpio_institucion", ASCENDING)], {"name": "ix_dim_institucion_mcpio"}),
    ),
    "Dim_Programa": (
        ([("nucleo_pregrado", ASCENDING)], {"name": "ix_dim_programa_nucleo"}),
        ([("programa_academico", ASCENDING)], {"name": "ix_dim_programa_nombre"}),
        ([("metodo_programa", ASCENDING)], {"name": "ix_dim_programa_metodo"}),
    ),
    "Dim_Ubicacion_Examen": (
        ([("depto_presentacion", ASCENDING)], {"name": "ix_dim_ubicacion_depto"}),
        ([("mcpio_presentacion", ASCENDING)], {"name": "ix_dim_ubicacion_mcpio"}),
        (
            [("depto_presentacion", ASCENDING), ("mcpio_presentacion", ASCENDING)],
            {"name": "ix_dim_ubicacion_geo"},
        ),
    ),
}


# ---------------------------------------------------------------------------
# Normalización de tipos
# ---------------------------------------------------------------------------

def to_native(value: Any) -> Any:
    """Convierte escalares pandas/NumPy a tipos nativos compatibles con BSON."""
    if value is None:
        return None

    # pd.NA, NaN, NaT, etc. Se evalúa antes de las fechas para no guardar "NaT".
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, np.datetime64):
        return pd.Timestamp(value).isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        number = float(value)
        return None if not np.isfinite(number) else number
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.str_):
        return str(value)
    if isinstance(value, float):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, int):
        return int(value)

    # Fallback para escalares de pandas 3.x/PyArrow que no son tipos NumPy.
    for converter in ("item", "as_py"):
        method = getattr(value, converter, None)
        if callable(method):
            try:
                native = method()
            except (TypeError, ValueError, AttributeError):
                continue
            if native is not value:
                return native

    return value


def as_text(value: Any) -> str | None:
    value = to_native(value)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def as_int(value: Any) -> int | None:
    value = to_native(value)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def as_code(value: Any) -> str | None:
    """Normaliza códigos numéricos (3.0 -> "3") sin perder códigos textuales."""
    value = to_native(value)
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return as_text(value)


# ---------------------------------------------------------------------------
# HU-30: Singleton de conexión
# ---------------------------------------------------------------------------

class MongoConnection:
    """Garantiza una única instancia de MongoClient en el proceso."""

    _instance: "MongoConnection | None" = None
    _lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> "MongoConnection":
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instance = instance
            return cls._instance

    def __init__(self, uri: str | None = None, database: str | None = None) -> None:
        if getattr(self, "_initialized", False):
            return
        self.uri = uri or os.getenv("MONGO_URI", DEFAULT_MONGO_URI)
        self.database_name = database or os.getenv("MONGO_DATABASE", DEFAULT_DATABASE)
        self._client: MongoClient | None = None
        self._database: Database | None = None
        self._initialized = True

    def connect(self) -> Database:
        with self._lock:
            if self._database is not None:
                return self._database
            try:
                self._client = MongoClient(
                    self.uri,
                    serverSelectionTimeoutMS=5_000,
                    connectTimeoutMS=10_000,
                )
                self._client.admin.command("ping")
                self._database = self._client[self.database_name]
                logging.info("Conectado a MongoDB: %s / %s", self.uri, self.database_name)
            except Exception as exc:
                if self._client is not None:
                    self._client.close()
                self._client = None
                self._database = None
                raise ConnectionError(
                    f"No se pudo conectar a MongoDB en {self.uri!r}. "
                    "Verifique el servidor y la variable MONGO_URI."
                ) from exc
            return self._database

    def close(self) -> None:
        with self._lock:
            if self._client is not None:
                self._client.close()
            self._client = None
            self._database = None
            self._initialized = False
            type(self)._instance = None


# ---------------------------------------------------------------------------
# HU-30: Builder de documentos del esquema estrella
# ---------------------------------------------------------------------------

class DocumentBuilder:
    """Construye documentos BSON para hechos y dimensiones.

    Los _id son deterministas para que una re-ejecución no duplique datos.
    """

    @staticmethod
    def _stable_object_id(*parts: Any) -> ObjectId:
        payload = "|".join("__NONE__" if part is None else str(part) for part in parts)
        digest = hashlib.blake2b(payload.encode("utf-8"), digest_size=12).digest()
        return ObjectId(digest)

    def build_dim_tiempo(self, row: Mapping[str, Any]) -> dict[str, Any]:
        raw_period = to_native(row.get(TIME_FIELDS["periodo"]))
        if isinstance(raw_period, float) and raw_period.is_integer():
            raw_period = int(raw_period)
        periodo = as_text(raw_period)
        return {
            "_id": self._stable_object_id("Dim_Tiempo", periodo),
            "periodo": periodo,
        }

    def build_dim_estudiante(self, row: Mapping[str, Any]) -> dict[str, Any]:
        fields = {
            name: as_text(row.get(column))
            for name, column in STUDENT_FIELDS.items()
        }
        consecutivo = as_text(row.get("ESTU_CONSECUTIVO"))
        natural_key: Any = consecutivo if consecutivo is not None else tuple(fields.values())
        return {
            "_id": self._stable_object_id("Dim_Estudiante", natural_key),
            **fields,
        }

    def build_dim_institucion(self, row: Mapping[str, Any]) -> dict[str, Any]:
        fields = {
            name: as_text(row.get(column))
            for name, column in INSTITUTION_FIELDS.items()
        }
        return {
            "_id": self._stable_object_id("Dim_Institucion", *fields.values()),
            **fields,
        }

    def build_dim_programa(self, row: Mapping[str, Any]) -> dict[str, Any]:
        fields = {
            name: as_text(row.get(column))
            for name, column in PROGRAM_FIELDS.items()
        }
        return {
            "_id": self._stable_object_id("Dim_Programa", *fields.values()),
            **fields,
        }

    def build_dim_ubicacion_examen(self, row: Mapping[str, Any]) -> dict[str, Any]:
        fields = {
            name: as_text(row.get(column))
            for name, column in EXAM_LOCATION_FIELDS.items()
        }
        return {
            "_id": self._stable_object_id("Dim_Ubicacion_Examen", *fields.values()),
            **fields,
        }

    def build_dimensions(self, row: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        return {
            "Dim_Tiempo": self.build_dim_tiempo(row),
            "Dim_Estudiante": self.build_dim_estudiante(row),
            "Dim_Institucion": self.build_dim_institucion(row),
            "Dim_Programa": self.build_dim_programa(row),
            "Dim_Ubicacion_Examen": self.build_dim_ubicacion_examen(row),
        }

    def build_fact(
        self,
        row: Mapping[str, Any],
        dimension_ids: Mapping[str, ObjectId],
    ) -> dict[str, Any]:
        consecutivo = as_text(row.get("ESTU_CONSECUTIVO"))
        return {
            "_id": self._stable_object_id("Fact_Resultados", consecutivo),
            "estu_consecutivo": consecutivo,
            "id_tiempo": dimension_ids["Dim_Tiempo"],
            "id_estudiante": dimension_ids["Dim_Estudiante"],
            "id_institucion": dimension_ids["Dim_Institucion"],
            "id_programa": dimension_ids["Dim_Programa"],
            "id_ubicacion_examen": dimension_ids["Dim_Ubicacion_Examen"],
            **{
                name: as_int(row.get(column))
                for name, column in METRIC_FIELDS.items()
            },
            **{
                name: as_code(row.get(column))
                for name, column in TEXT_METRIC_FIELDS.items()
            },
        }


# ---------------------------------------------------------------------------
# Lectura y limpieza del CSV
# ---------------------------------------------------------------------------

def ensure_not_lfs_pointer(csv_path: Path) -> None:
    if not csv_path.is_file():
        raise FileNotFoundError(f"No existe el archivo CSV: {csv_path}")
    with csv_path.open("rb") as file:
        if file.readline().startswith(LFS_POINTER_PREFIX):
            raise RuntimeError(
                f"{csv_path} es un puntero de Git LFS, no el CSV real. "
                "Ejecute 'git lfs install' y 'git lfs pull'."
            )


def resolve_encoding(csv_path: Path, requested: str) -> str:
    candidates = ["utf-8-sig", "utf-8", "latin-1"] if requested == "auto" else [requested]
    for encoding in candidates:
        try:
            pd.read_csv(csv_path, nrows=5, encoding=encoding, low_memory=False)
            return encoding
        except UnicodeDecodeError:
            continue
        except pd.errors.ParserError as exc:
            raise RuntimeError(f"No se pudo parsear el CSV con encoding {encoding}") from exc
    raise RuntimeError(f"No se pudo determinar el encoding de {csv_path}")


def read_available_columns(csv_path: Path, encoding: str) -> list[str]:
    header = pd.read_csv(csv_path, nrows=0, encoding=encoding, low_memory=False)
    available = [column for column in ALL_COLUMNS if column in header.columns]
    missing = REQUIRED_COLUMNS - set(available)
    if missing:
        raise RuntimeError("Faltan columnas obligatorias: " + ", ".join(sorted(missing)))
    return available


# ---------------------------------------------------------------------------
# Índices y escritura
# ---------------------------------------------------------------------------

def collection_names(fact_collection: str) -> tuple[str, ...]:
    return (fact_collection, *DIM_COLLECTIONS)


def drop_collections(database: Database, fact_collection: str) -> None:
    logging.warning("--reset: eliminando las colecciones del esquema estrella.")
    for name in collection_names(fact_collection):
        database[name].drop()


def create_indexes(database: Database, fact_collection: str) -> None:
    specs: list[tuple[Collection, list[tuple[str, int]], dict[str, Any]]] = [
        (database[fact_collection], keys, options) for keys, options in FACT_INDEXES
    ]
    for name, indexes in DIM_INDEXES.items():
        specs.extend((database[name], keys, options) for keys, options in indexes)

    for collection, keys, options in specs:
        try:
            collection.create_index(keys, **options)
        except OperationFailure as exc:
            logging.warning(
                "No se pudo crear el índice %s en %s: %s",
                options.get("name", keys),
                collection.name,
                exc,
            )


def upsert_dimensions(
    database: Database,
    dimensions: Mapping[str, Mapping[ObjectId, dict[str, Any]]],
    stop_on_error: bool,
    stats: dict[str, int],
) -> None:
    """Upsert idempotente de dimensiones con ReplaceOne."""
    for name, documents in dimensions.items():
        if not documents:
            continue
        operations = [
            ReplaceOne({"_id": document["_id"]}, document, upsert=True)
            for document in documents.values()
        ]
        try:
            result: BulkWriteResult = database[name].bulk_write(operations, ordered=False)
            stats["dim_upserted"] += result.upserted_count
            stats["dim_matched"] += result.matched_count
        except BulkWriteError as exc:
            details = exc.details or {}
            stats["dim_upserted"] += int(details.get("nUpserted") or 0)
            stats["dim_matched"] += int(details.get("nMatched") or 0)
            stats["failed_batches"] += 1
            logging.error(
                "Error en upsert de %s: %s errores de escritura. Se continúa.",
                name,
                len(details.get("writeErrors") or []),
            )
            if stop_on_error:
                raise
        except ConnectionFailure as exc:
            stats["failed_batches"] += 1
            logging.error("Conexión perdida al escribir en %s: %s", name, exc)
            raise
        except PyMongoError as exc:
            stats["failed_batches"] += 1
            logging.error("Error de MongoDB al escribir en %s: %s", name, exc)
            if stop_on_error:
                raise


def insert_facts(
    collection: Collection,
    facts: list[dict[str, Any]],
    batch_size: int,
    stop_on_error: bool,
    stats: dict[str, int],
) -> None:
    """Inserta hechos por lotes con insert_many(ordered=False)."""
    for start in range(0, len(facts), batch_size):
        batch = facts[start : start + batch_size]
        if not batch:
            continue
        try:
            result = collection.insert_many(batch, ordered=False)
            stats["facts_inserted"] += len(result.inserted_ids)
        except BulkWriteError as exc:
            details = exc.details or {}
            inserted = int(details.get("nInserted") or 0)
            stats["facts_inserted"] += inserted
            stats["failed_batches"] += 1
            logging.error(
                "Lote de hechos con errores: %s insertados, %s errores de escritura. "
                "Se continúa con el siguiente lote.",
                inserted,
                len(details.get("writeErrors") or []),
            )
            if stop_on_error:
                raise
        except ConnectionFailure as exc:
            stats["failed_batches"] += 1
            logging.error("Conexión perdida al insertar hechos: %s", exc)
            raise
        except PyMongoError as exc:
            stats["failed_batches"] += 1
            logging.error("Error de MongoDB al insertar hechos: %s", exc)
            if stop_on_error:
                raise


# ---------------------------------------------------------------------------
# Resumen y CLI
# ---------------------------------------------------------------------------

def print_summary(
    database: Database,
    fact_collection: str,
    stats: Mapping[str, int],
    elapsed: float,
) -> None:
    print("\n" + "=" * 64)
    print("RESUMEN DE CARGA")
    print("=" * 64)
    for name in collection_names(fact_collection):
        try:
            count = database[name].count_documents({})
        except PyMongoError as exc:
            logging.error("No se pudo contar %s: %s", name, exc)
            count = -1
        print(f"{name:<24} {count:>14,} documentos")
    print("-" * 64)
    print(f"Filas del CSV limpio:      {stats['rows_read']:>14,}")
    print(f"Hechos insertados:         {stats['facts_inserted']:>14,}")
    print(f"Dimensiones upsertadas:    {stats['dim_upserted']:>14,}")
    print(f"Dimensiones ya existentes: {stats['dim_matched']:>14,}")
    print(f"Lotes con error:           {stats['failed_batches']:>14,}")
    print(f"Tiempo total:              {elapsed:>14.2f} s")
    print("=" * 64)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Carga el CSV depurado de Saber Pro en MongoDB (Esquema de Estrella)."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument(
        "--mongo-uri",
        default=None,
        help="URI de MongoDB. Por defecto MONGO_URI o mongodb://localhost:27017/.",
    )
    parser.add_argument(
        "--database",
        default=None,
        help="Base de datos. Por defecto MONGO_DATABASE o SaberProDB.",
    )
    parser.add_argument(
        "--collection",
        default=DEFAULT_FACT_COLLECTION,
        help="Colección de hechos (por defecto Fact_Resultados).",
    )
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Elimina las seis colecciones antes de cargar. Operación destructiva.",
    )
    parser.add_argument(
        "--encoding",
        default="auto",
        choices=["auto", "utf-8", "utf-8-sig", "latin-1"],
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Detiene la carga ante el primer error de escritura.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )

    if args.batch_size < 1:
        logging.error("--batch-size debe ser mayor que cero.")
        return 2
    if args.collection in DIM_COLLECTIONS:
        logging.error("--collection no puede tener el nombre de una dimensión.")
        return 2

    started = time.perf_counter()
    stats = {
        "rows_read": 0,
        "facts_inserted": 0,
        "dim_upserted": 0,
        "dim_matched": 0,
        "failed_batches": 0,
    }

    connection: MongoConnection | None = None
    database: Database | None = None

    try:
        ensure_not_lfs_pointer(args.csv)
        encoding = resolve_encoding(args.csv, args.encoding)
        available_columns = read_available_columns(args.csv, encoding)
        logging.info("Encoding: %s", encoding)
        logging.info("Columnas leídas: %s", len(available_columns))

        connection = MongoConnection(args.mongo_uri, args.database)
        database = connection.connect()

        if args.reset:
            drop_collections(database, args.collection)
        create_indexes(database, args.collection)

        builder = DocumentBuilder()
        chunks = pd.read_csv(
            args.csv,
            chunksize=args.batch_size,
            usecols=available_columns,
            low_memory=False,
            encoding=encoding,
        )

        for chunk_number, chunk in enumerate(chunks, start=1):
            clean = chunk
            stats["rows_read"] += len(clean)

            if clean.empty:
                logging.info("Lote %d vacío; se omite.", chunk_number)
                continue

            dimensions: dict[str, dict[ObjectId, dict[str, Any]]] = {
                name: {} for name in DIM_COLLECTIONS
            }
            facts: list[dict[str, Any]] = []

            for row in clean.to_dict(orient="records"):
                dimension_docs = builder.build_dimensions(row)
                for name, document in dimension_docs.items():
                    dimensions[name].setdefault(document["_id"], document)

                dimension_ids = {
                    name: document["_id"]
                    for name, document in dimension_docs.items()
                }
                facts.append(builder.build_fact(row, dimension_ids))

            # Primero dimensiones: las FKs de los hechos ya existen.
            upsert_dimensions(database, dimensions, args.stop_on_error, stats)
            insert_facts(
                database[args.collection],
                facts,
                args.batch_size,
                args.stop_on_error,
                stats,
            )

            logging.info(
                "Lote %d: %d leídas, %d hechos acumulados.",
                chunk_number,
                len(clean),
                stats["facts_inserted"],
            )

        elapsed = time.perf_counter() - started
        print_summary(database, args.collection, stats, elapsed)
        return 0

    except (FileNotFoundError, RuntimeError, ConnectionError, PyMongoError) as exc:
        logging.error("La carga no pudo completarse: %s", exc)
        return 1
    except Exception:
        logging.exception("Error inesperado durante la carga.")
        return 1
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
