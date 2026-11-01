import argparse
from pathlib import Path
from typing import Any

import pandas as pd
from pymongo import ASCENDING, MongoClient


DEFAULT_CSV = Path(__file__).resolve().parents[1] / "data" / "Resultados_Saber_Pro_20260927.csv"
BATCH_SIZE = 10_000

TEXT_FIELDS = {
    "student": [
        "ESTU_CONSECUTIVO",
        "ESTU_PAIS_RESIDE",
        "ESTU_GENERO",
        "ESTU_NACIONALIDAD",
        "ESTU_PRIVADO_LIBERTAD",
        "ESTU_ESTUDIANTE",
        "ESTU_HORASSEMANATRABAJA",
        "ESTU_VALORMATRICULAUNIVERSIDAD",
        "ESTU_PAGOMATRICULABECA",
        "ESTU_PAGOMATRICULACREDITO",
        "ESTU_PAGOMATRICULAPADRES",
        "ESTU_PAGOMATRICULAPROPIO",
    ],
    "institution": [
        "INST_COD_INSTITUCION",
        "INST_NOMBRE_INSTITUCION",
        "INST_CARACTER_ACADEMICO",
        "INST_ORIGEN",
        "ESTU_INST_DEPARTAMENTO",
        "ESTU_INST_MUNICIPIO",
        "ESTU_INST_CODMUNICIPIO",
    ],
    "program": [
        "ESTU_NUCLEO_PREGRADO",
        "ESTU_PRGM_ACADEMICO",
        "ESTU_METODO_PRGM",
        "ESTU_NIVEL_PRGM_ACADEMICO",
        "ESTU_SNIES_PRGMACADEMICO",
    ],
    "socioeconomic": [
        "FAMI_EDUCACIONPADRE",
        "FAMI_EDUCACIONMADRE",
        "FAMI_ESTRATOVIVIENDA",
        "FAMI_TIENECOMPUTADOR",
        "FAMI_TIENEINTERNET",
    ],
}


def clean_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def build_document(row: pd.Series) -> dict[str, Any]:
    period = clean_value(row.get("PERIODO"))
    period_text = str(period) if period is not None else None
    year = int(period_text[:-1]) if period_text and period_text[:-1].isdigit() else period

    def nested(group: str) -> dict[str, Any]:
        return {
            field.lower(): clean_value(row.get(field))
            for field in TEXT_FIELDS[group]
            if field in row and pd.notna(row.get(field))
        }

    scores = {
        field.lower(): clean_value(row.get(field))
        for field in (
            "MOD_RAZONA_CUANTITAT_PUNT",
            "MOD_COMUNI_ESCRITA_PUNT",
            "MOD_COMUNI_ESCRITA_DESEM",
            "MOD_INGLES_DESEM",
            "MOD_LECTURA_CRITICA_PUNT",
            "MOD_INGLES_PUNT",
            "MOD_COMPETEN_CIUDADA_PUNT",
        )
        if field in row and pd.notna(row.get(field))
    }

    return {
        "period": period_text,
        "year": year,
        "geography": {
            "department": clean_value(row.get("ESTU_DEPTO_RESIDE")),
            "department_code": clean_value(row.get("ESTU_COD_RESIDE_DEPTO")),
            "municipality": clean_value(row.get("ESTU_MCPIO_RESIDE")),
            "municipality_code": clean_value(row.get("ESTU_COD_RESIDE_MCPIO")),
            "presentation_department": clean_value(row.get("ESTU_DEPTO_PRESENTACION")),
            "presentation_department_code": clean_value(row.get("ESTU_COD_DEPTO_PRESENTACION")),
            "presentation_municipality": clean_value(row.get("ESTU_MCPIO_PRESENTACION")),
            "presentation_municipality_code": clean_value(row.get("ESTU_COD_MCPIO_PRESENTACION")),
            "institution_department": clean_value(row.get("ESTU_INST_DEPARTAMENTO")),
            "institution_municipality": clean_value(row.get("ESTU_INST_MUNICIPIO")),
        },
        "student": nested("student"),
        "institution": nested("institution"),
        "program": nested("program"),
        "socioeconomic": nested("socioeconomic"),
        "reference_group": clean_value(row.get("ESTU_NUCLEO_PREGRADO")),
        "scores": scores,
    }


def create_indexes(collection: Any) -> None:
    indexes = [
        ("period", [("period", ASCENDING)]),
        ("year", [("year", ASCENDING)]),
        ("institution_name", [("institution.inst_nombre_institucion", ASCENDING)]),
        ("institution_code", [("institution.inst_cod_institucion", ASCENDING)]),
        ("department", [("geography.department", ASCENDING)]),
        ("presentation_department", [("geography.presentation_department", ASCENDING)]),
        ("institution_department", [("geography.institution_department", ASCENDING)]),
        ("reference_group", [("reference_group", ASCENDING)]),
        ("socioeconomic", [
            ("socioeconomic.fami_estratovivienda", ASCENDING),
            ("socioeconomic.fami_tieneinternet", ASCENDING),
            ("socioeconomic.fami_tienecomputador", ASCENDING),
        ]),
        (
            "dynamic_filters",
            [
                ("year", ASCENDING),
                ("geography.department", ASCENDING),
                ("institution.inst_nombre_institucion", ASCENDING),
                ("reference_group", ASCENDING),
            ],
        ),
    ]
    for name, keys in indexes:
        collection.create_index(keys, name=name)


def load_csv(
    csv_path: Path,
    mongo_uri: str,
    database_name: str,
    collection_name: str,
    batch_size: int,
    reset: bool,
    encoding: str,
) -> int:
    selected_encoding = encoding
    if selected_encoding == "auto":
        try:
            pd.read_csv(csv_path, nrows=5, encoding="utf-8-sig")
            selected_encoding = "utf-8-sig"
        except UnicodeDecodeError:
            selected_encoding = "latin-1"

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5_000)
    client.admin.command("ping")
    collection = client[database_name][collection_name]
    if reset:
        collection.delete_many({})
    create_indexes(collection)

    total = 0
    documents: list[dict[str, Any]] = []
    print(f"Reading CSV with encoding: {selected_encoding}")
    chunks = pd.read_csv(
        csv_path,
        chunksize=batch_size,
        low_memory=False,
        encoding=selected_encoding,
    )
    for chunk in chunks:
        documents.extend(build_document(row) for _, row in chunk.iterrows())
        collection.insert_many(documents, ordered=False)
        total += len(documents)
        print(f"Inserted {total} documents")
        documents = []

    return total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load Saber Pro results into MongoDB with optimized indexes")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017/")
    parser.add_argument("--database", default="SaberProDB")
    parser.add_argument("--collection", default="Fact_Resultados")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--encoding", default="auto", choices=["auto", "utf-8", "utf-8-sig", "latin-1"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.csv.is_file():
        raise FileNotFoundError(f"CSV not found: {args.csv}")
    if args.batch_size < 1:
        raise ValueError("batch-size must be greater than zero")

    total = load_csv(
        csv_path=args.csv,
        mongo_uri=args.mongo_uri,
        database_name=args.database,
        collection_name=args.collection,
        batch_size=args.batch_size,
        reset=args.reset,
        encoding=args.encoding,
    )
    print(f"Load completed: {total} documents")


if __name__ == "__main__":
    main()
