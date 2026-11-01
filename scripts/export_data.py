import argparse
import csv
import io
import json
import os
from collections.abc import Iterator, Mapping
from datetime import date, datetime
from pathlib import Path
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.cursor import Cursor


DEFAULT_MONGO_URI = "mongodb://localhost:27017/"
DEFAULT_DATABASE = "SaberProDB"
DEFAULT_COLLECTION = "Fact_Resultados"
DEFAULT_LIMIT = 10_000
MAX_LIMIT = 100_000
DEFAULT_BATCH_SIZE = 10_000

FILTER_FIELDS: dict[str, str] = {
    "year": "year",
    "period": "period",
    "department": "geography.department",
    "municipality": "geography.municipality",
    "presentation_department": "geography.presentation_department",
    "presentation_municipality": "geography.presentation_municipality",
    "institution_department": "geography.institution_department",
    "institution": "institution.inst_nombre_institucion",
    "institution_code": "institution.inst_cod_institucion",
    "reference_group": "reference_group",
    "program": "program.estu_prgm_academico",
    "method": "program.estu_metodo_prgm",
    "gender": "student.estu_genero",
    "stratum": "socioeconomic.fami_estratovivienda",
    "has_internet": "socioeconomic.fami_tieneinternet",
    "has_computer": "socioeconomic.fami_tienecomputador",
}


def build_filter(filters: Mapping[str, Any]) -> dict[str, Any]:
    """Converts dashboard filter names into MongoDB query fields."""
    query: dict[str, Any] = {}
    for name, value in filters.items():
        if name not in FILTER_FIELDS:
            continue
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        query[FILTER_FIELDS[name]] = value
    return query


def flatten_document(
    document: Mapping[str, Any],
    prefix: str = "",
    separator: str = ".",
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in document.items():
        field_name = f"{prefix}{separator}{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            result.update(flatten_document(value, field_name, separator))
        else:
            result[field_name] = make_json_safe(value)
    return result


def make_json_safe(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): make_json_safe(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [make_json_safe(child) for child in value]
    return value


def get_collection(
    mongo_uri: str | None = None,
    database: str | None = None,
    collection_name: str | None = None,
) -> Collection:
    uri = mongo_uri or os.getenv("MONGO_URI", DEFAULT_MONGO_URI)
    database_name = database or os.getenv("MONGO_DATABASE", DEFAULT_DATABASE)
    collection = collection_name or os.getenv("MONGO_COLLECTION", DEFAULT_COLLECTION)
    client = MongoClient(uri, serverSelectionTimeoutMS=5_000)
    client.admin.command("ping")
    return client[database_name][collection]


def iter_filtered_records(
    collection: Collection,
    filters: Mapping[str, Any] | None = None,
    *,
    offset: int = 0,
    limit: int | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> Iterator[list[dict[str, Any]]]:
    if offset < 0:
        raise ValueError("offset must be greater than or equal to zero")
    if limit is not None and limit < 1:
        raise ValueError("limit must be greater than zero")
    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero")

    query = build_filter(filters or {})
    cursor: Cursor = collection.find(query)
    cursor = cursor.sort("_id", ASCENDING).skip(offset)
    if limit is not None:
        cursor = cursor.limit(limit)

    batch: list[dict[str, Any]] = []
    for document in cursor:
        batch.append(make_json_safe(document))
        if len(batch) == batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def count_filtered_records(
    collection: Collection,
    filters: Mapping[str, Any] | None = None,
) -> int:
    return collection.count_documents(build_filter(filters or {}))


def iter_json(
    collection: Collection,
    filters: Mapping[str, Any] | None = None,
    *,
    offset: int = 0,
    limit: int | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> Iterator[str]:
    yield "["
    first_document = True
    for batch in iter_filtered_records(
        collection,
        filters,
        offset=offset,
        limit=limit,
        batch_size=batch_size,
    ):
        for document in batch:
            if not first_document:
                yield ","
            yield json.dumps(document, ensure_ascii=False, separators=(",", ":"))
            first_document = False
    yield "]"


def iter_csv(
    collection: Collection,
    filters: Mapping[str, Any] | None = None,
    *,
    offset: int = 0,
    limit: int | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> Iterator[str]:
    batches = iter_filtered_records(
        collection,
        filters,
        offset=offset,
        limit=limit,
        batch_size=batch_size,
    )
    flattened_rows: list[dict[str, Any]] = []
    fieldnames: set[str] = set()

    for batch in batches:
        for document in batch:
            row = flatten_document(document)
            flattened_rows.append(row)
            fieldnames.update(row)

    if not flattened_rows:
        yield "No records found\n"
        return

    output = io.StringIO(newline="")
    ordered_fields = sorted(fieldnames)
    writer = csv.DictWriter(output, fieldnames=ordered_fields, extrasaction="ignore")
    writer.writeheader()
    yield output.getvalue()
    output.seek(0)
    output.truncate(0)

    for row in flattened_rows:
        writer.writerow(row)
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)


def export_filtered_data(
    collection: Collection,
    output_path: str | Path,
    *,
    format: str = "csv",
    filters: Mapping[str, Any] | None = None,
    offset: int = 0,
    limit: int | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> int:
    if format not in {"csv", "json"}:
        raise ValueError("format must be 'csv' or 'json'")
    if limit is not None and limit < 1:
        raise ValueError("limit must be greater than zero")
    if limit is not None and limit > MAX_LIMIT:
        raise ValueError(f"limit cannot exceed {MAX_LIMIT}")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    chunks = (
        iter_csv(collection, filters, offset=offset, limit=limit, batch_size=batch_size)
        if format == "csv"
        else iter_json(collection, filters, offset=offset, limit=limit, batch_size=batch_size)
    )

    matched = count_filtered_records(collection, filters)
    if limit is None:
        count = max(0, matched - offset)
    else:
        count = max(0, min(limit, matched - offset))

    with output.open("w", encoding="utf-8-sig" if format == "csv" else "utf-8", newline="") as file:
        for chunk in chunks:
            file.write(chunk)
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export filtered Saber Pro data from MongoDB to CSV or JSON."
    )
    parser.add_argument("--format", choices=["csv", "json"], default="csv")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mongo-uri", default=os.getenv("MONGO_URI", DEFAULT_MONGO_URI))
    parser.add_argument("--database", default=os.getenv("MONGO_DATABASE", DEFAULT_DATABASE))
    parser.add_argument("--collection", default=os.getenv("MONGO_COLLECTION", DEFAULT_COLLECTION))
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)

    for name in FILTER_FIELDS:
        parser.add_argument(
            f"--{name.replace('_', '-')}",
            dest=name,
            default=None,
            type=int if name == "year" else str,
        )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.offset < 0:
        raise ValueError("offset must be greater than or equal to zero")
    if args.limit < 1 or args.limit > MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
    if args.batch_size < 1:
        raise ValueError("batch-size must be greater than zero")

    collection = get_collection(args.mongo_uri, args.database, args.collection)
    filters = {name: getattr(args, name) for name in FILTER_FIELDS if getattr(args, name) is not None}
    total = count_filtered_records(collection, filters)
    exported = export_filtered_data(
        collection,
        args.output,
        format=args.format,
        filters=filters,
        offset=args.offset,
        limit=args.limit,
        batch_size=args.batch_size,
    )
    print(f"Matched records: {total}")
    print(f"Exported records: {exported}")
    print(f"Output: {args.output.resolve()}")


if __name__ == "__main__":
    main()
