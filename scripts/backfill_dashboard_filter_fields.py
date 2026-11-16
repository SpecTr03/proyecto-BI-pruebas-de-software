"""Agrega filtros indexables a los hechos ya cargados, sin borrar datos."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import UpdateOne
from pymongo.database import Database

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / "backend" / ".env")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.constants import normalize_dashboard_filter_value
from backend.app.database import MongoConnection
from scripts.populate_nosql import create_dashboard_filter_indexes

FACT_COLLECTION = "Fact_Resultados"
BATCH_SIZE = 5_000
FILTER_DIMENSIONS = {
    "anio": ("id_tiempo", "Dim_Tiempo", "periodo"),
    "departamento": ("id_estudiante", "Dim_Estudiante", "depto_reside"),
    "municipio": ("id_estudiante", "Dim_Estudiante", "mcpio_reside"),
    "institucion": ("id_institucion", "Dim_Institucion", "nombre_institucion"),
    "caracter_institucion": (
        "id_institucion",
        "Dim_Institucion",
        "caracter_academico",
    ),
    "programa": ("id_programa", "Dim_Programa", "programa_academico"),
    "metodo_programa": ("id_programa", "Dim_Programa", "metodo_programa"),
    "genero": ("id_estudiante", "Dim_Estudiante", "genero"),
    "estrato": ("id_estudiante", "Dim_Estudiante", "estrato"),
    "grupo_referencia": ("id_programa", "Dim_Programa", "nucleo_pregrado"),
}


def _read_dimension_values(
    database: Database,
    facts: list[dict[str, Any]],
) -> dict[tuple[str, ObjectId], dict[str, Any]]:
    values_by_dimension: dict[tuple[str, ObjectId], dict[str, Any]] = {}
    fields_by_collection: dict[str, set[str]] = {}
    ids_by_collection: dict[str, set[ObjectId]] = {}
    for foreign_key, collection, field in FILTER_DIMENSIONS.values():
        ids = {
            fact[foreign_key]
            for fact in facts
            if isinstance(fact.get(foreign_key), ObjectId)
        }
        fields_by_collection.setdefault(collection, set()).add(field)
        ids_by_collection.setdefault(collection, set()).update(ids)

    for collection, ids in ids_by_collection.items():
        fields = fields_by_collection[collection]
        projection = {field: 1 for field in fields}
        for document in database[collection].find(
            {"_id": {"$in": list(ids)}},
            projection,
        ):
            values_by_dimension[(collection, document["_id"])] = {
                field: document.get(field) for field in fields
            }

    return values_by_dimension


def _build_filter_values(
    fact: dict[str, Any],
    dimension_values: dict[tuple[str, ObjectId], dict[str, Any]],
) -> dict[str, str | None]:
    filters: dict[str, str | None] = {}
    for filter_key, (foreign_key, collection, field) in FILTER_DIMENSIONS.items():
        dimension = dimension_values.get(
            (collection, fact.get(foreign_key)),
            {},
        )
        value = dimension.get(field)
        if filter_key == "anio" and value is not None:
            value = str(value).strip()[:4]
        filters[filter_key] = normalize_dashboard_filter_value(
            filter_key,
            value,
        )
    return filters


def backfill_dashboard_filter_fields(
    database: Database,
    collection_name: str = FACT_COLLECTION,
    batch_size: int = BATCH_SIZE,
) -> int:
    """Copia valores de dimensión a cada hecho por lotes sin reemplazar documentos."""
    collection = database[collection_name]
    processed = 0
    last_id: ObjectId | None = None

    while True:
        query: dict[str, Any] = {"dashboard_filters": {"$exists": False}}
        if last_id is not None:
            query["_id"] = {"$gt": last_id}

        facts = list(
            collection.find(
                query,
                {
                    "_id": 1,
                    "id_tiempo": 1,
                    "id_estudiante": 1,
                    "id_institucion": 1,
                    "id_programa": 1,
                },
            )
            .sort("_id", 1)
            .limit(batch_size)
        )
        if not facts:
            break

        dimension_values = _read_dimension_values(database, facts)
        updates = [
            UpdateOne(
                {"_id": fact["_id"]},
                {
                    "$set": {
                        "dashboard_filters": _build_filter_values(
                            fact,
                            dimension_values,
                        )
                    }
                },
            )
            for fact in facts
        ]
        collection.bulk_write(updates, ordered=False)
        processed += len(facts)
        last_id = facts[-1]["_id"]
        logging.info("Hechos actualizados con filtros: %s", processed)

    missing_count = collection.count_documents(
        {"dashboard_filters": {"$exists": False}}
    )
    if missing_count:
        raise RuntimeError(
            f"Quedaron {missing_count} hechos sin campos de filtro."
        )

    create_dashboard_filter_indexes(database, collection_name)
    return processed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill indexable dashboard filters without deleting data."
    )
    parser.add_argument(
        "--mongo-uri",
        default=os.getenv("MONGO_URI", "mongodb://localhost:27017/"),
    )
    parser.add_argument(
        "--database",
        default=os.getenv("MONGO_DATABASE", "SaberProDB"),
    )
    parser.add_argument("--collection", default=FACT_COLLECTION)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size debe ser mayor que cero.")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )
    connection = MongoConnection(args.mongo_uri, args.database)
    try:
        database = connection.connect()
        processed = backfill_dashboard_filter_fields(
            database,
            args.collection,
            args.batch_size,
        )
        logging.info(
            "Migración completada: %s hechos actualizados y filtros indexados.",
            processed,
        )
        return 0
    except Exception as exc:
        logging.error(
            "No fue posible completar la migración (%s).",
            type(exc).__name__,
        )
        return 1
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
