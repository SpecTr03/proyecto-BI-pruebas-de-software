"""Entrena y selecciona modelos para predecir el puntaje global de Saber Pro.

El script extrae una muestra aleatoria de ``Fact_Resultados`` y enriquece cada
hecho con variables de ``Dim_Estudiante``, ``Dim_Institucion`` y
``Dim_Programa`` mediante ``$lookup``. La variable objetivo ``punt_global`` se
calcula como el promedio de los cinco módulos evaluados.

Se usa ``$sample`` con 200.000 registros para reducir el tiempo de
entrenamiento, el consumo de memoria y el costo de la validación cruzada. El
dataset completo supera 1.2 millones de hechos; una muestra aleatoria de ese
tamaño conserva la variabilidad socioeconómica e institucional necesaria para
comparar los modelos sin convertir el entrenamiento en un proceso inviable en
un equipo local.

Modelos comparados:
    - RandomForestRegressor
    - GradientBoostingRegressor
    - XGBRegressor

El mejor modelo se selecciona por MAE en el conjunto de test y se guarda junto
con el preprocesador en ``backend/models/modelo_saber_pro.pkl``.

Ejecución:
    python scripts/train_model.py

Opcionalmente:
    python scripts/train_model.py --output /tmp/modelo.pkl
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import OperationFailure, PyMongoError
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

try:
    from xgboost import XGBRegressor
except ImportError as exc:  # pragma: no cover - depende del entorno
    raise SystemExit(
        "Falta la dependencia 'xgboost'. Instálala con: pip install xgboost"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MONGO_URI = "mongodb://localhost:27017/"
DEFAULT_DATABASE = "SaberProDB"
DEFAULT_COLLECTION = "Fact_Resultados"
DEFAULT_OUTPUT = PROJECT_ROOT / "backend" / "models" / "modelo_saber_pro.pkl"

SAMPLE_SIZE = 200_000
RANDOM_STATE = 42
TEST_SIZE = 0.2
CV_FOLDS = 5

FEATURE_COLUMNS = [
    "genero",
    "estrato",
    "educacion_padre",
    "educacion_madre",
    "tiene_internet",
    "tiene_computador",
    "caracter_academico",
    "metodo_programa",
    "depto_reside",
    "depto_institucion",
]
NUMERIC_FEATURES = ["estrato"]
CATEGORICAL_FEATURES = [
    feature for feature in FEATURE_COLUMNS if feature not in NUMERIC_FEATURES
]

METRIC_FIELDS = [
    "mod_razona_cuantitat_punt",
    "mod_comuni_escrita_punt",
    "mod_lectura_critica_punt",
    "mod_ingles_punt",
    "mod_competen_ciudada_punt",
]

logger = logging.getLogger(__name__)


def build_aggregation_pipeline(sample_size: int = SAMPLE_SIZE) -> list[dict[str, Any]]:
    """Construye el pipeline de extracción y enriquecimiento de datos.

    Args:
        sample_size: Cantidad de hechos a muestrear antes de los ``$lookup``.

    Returns:
        Pipeline de agregación listo para ejecutar sobre ``Fact_Resultados``.

    Raises:
        ValueError: Si ``sample_size`` no es positivo.
    """
    if sample_size < 1:
        raise ValueError("sample_size debe ser mayor que cero.")

    sum_expression = {"$add": [f"${field}" for field in METRIC_FIELDS]}

    return [
        # Se muestrea primero para hacer los lookups solo sobre 200.000 hechos.
        {"$sample": {"size": sample_size}},
        {
            "$lookup": {
                "from": "Dim_Estudiante",
                "localField": "id_estudiante",
                "foreignField": "_id",
                "as": "dim_estudiante",
            }
        },
        {
            "$lookup": {
                "from": "Dim_Institucion",
                "localField": "id_institucion",
                "foreignField": "_id",
                "as": "dim_institucion",
            }
        },
        {
            "$lookup": {
                "from": "Dim_Programa",
                "localField": "id_programa",
                "foreignField": "_id",
                "as": "dim_programa",
            }
        },
        {
            "$unwind": {
                "path": "$dim_estudiante",
                "preserveNullAndEmptyArrays": True,
            }
        },
        {
            "$unwind": {
                "path": "$dim_institucion",
                "preserveNullAndEmptyArrays": True,
            }
        },
        {
            "$unwind": {
                "path": "$dim_programa",
                "preserveNullAndEmptyArrays": True,
            }
        },
        {
            "$project": {
                "_id": 0,
                "genero": "$dim_estudiante.genero",
                "estrato": "$dim_estudiante.estrato",
                "educacion_padre": "$dim_estudiante.educacion_padre",
                "educacion_madre": "$dim_estudiante.educacion_madre",
                "tiene_internet": "$dim_estudiante.tiene_internet",
                "tiene_computador": "$dim_estudiante.tiene_computador",
                "caracter_academico": "$dim_institucion.caracter_academico",
                "metodo_programa": "$dim_programa.metodo_programa",
                "depto_reside": "$dim_estudiante.depto_reside",
                "depto_institucion": "$dim_institucion.depto_institucion",
                "punt_global": {"$divide": [sum_expression, len(METRIC_FIELDS)]},
            }
        },
        # Si falta algún puntaje, el objetivo queda nulo y no sirve para entrenar.
        {"$match": {"punt_global": {"$ne": None}}},
    ]


def _parse_estrato(series: pd.Series) -> pd.Series:
    """Convierte valores como ``Estrato 2`` en el número ``2``."""
    extracted = series.astype("string").str.extract(r"(\d+)", expand=False)
    return pd.to_numeric(extracted, errors="coerce")


def _build_fallback_pipeline(
    collection: Collection,
    pipeline: list[dict[str, Any]],
    sample_size: int,
) -> list[dict[str, Any]]:
    """Amplía ``$sample`` para evitar el cursor aleatorio de MongoDB.

    ``$sample`` usa un cursor aleatorio cuando el tamaño solicitado es menor al
    5 % de la colección. En esta colección ese cursor puede fallar con el error
    28799. El fallback muestrea algo más del 5 % y luego limita al tamaño pedido.
    """
    total = collection.estimated_document_count()
    fallback_size = min(
        max(sample_size, int(total * 0.06) + 1),
        max(total, sample_size),
    )

    fallback_pipeline = list(pipeline)
    fallback_pipeline[0] = {"$sample": {"size": fallback_size}}
    if fallback_size > sample_size:
        fallback_pipeline.insert(1, {"$limit": sample_size})

    logger.warning(
        "Usando fallback de muestreo: $sample de %s registros y $limit de %s.",
        f"{fallback_size:,}",
        f"{sample_size:,}",
    )
    return fallback_pipeline


def _extract_sample(
    collection: Collection,
    pipeline: list[dict[str, Any]],
    sample_size: int,
    attempts: int = 5,
) -> list[dict[str, Any]]:
    """Ejecuta la agregación reintentando si ``$sample`` falla temporalmente.

    En colecciones grandes, el cursor aleatorio de ``$sample`` puede agotar
    sus intentos internos y devolver el error 28799. Se reintenta la misma
    agregación y, si el fallo persiste, se usa un muestreo mayor con ``$limit``.
    """
    for attempt in range(1, attempts + 1):
        try:
            return list(collection.aggregate(pipeline, allowDiskUse=True))
        except OperationFailure as exc:
            if exc.code != 28799:
                raise
            if attempt < attempts:
                logger.warning(
                    "MongoDB no pudo completar $sample (intento %d/%d); "
                    "reintentando...",
                    attempt,
                    attempts,
                )
                continue

            fallback_pipeline = _build_fallback_pipeline(
                collection,
                pipeline,
                sample_size,
            )
            return list(collection.aggregate(fallback_pipeline, allowDiskUse=True))

    return []


def load_dataset(
    collection: Collection,
    sample_size: int = SAMPLE_SIZE,
) -> pd.DataFrame:
    """Extrae la muestra, ejecuta los ``$lookup`` y prepara el DataFrame.

    Args:
        collection: Colección ``Fact_Resultados``.
        sample_size: Cantidad de registros a muestrear.

    Returns:
        DataFrame con las features y la columna objetivo ``punt_global``.

    Raises:
        RuntimeError: Si la muestra no devuelve registros o faltan columnas.
    """
    pipeline = build_aggregation_pipeline(sample_size)
    logger.info(
        "Extrayendo %s registros aleatorios de %s...",
        f"{sample_size:,}",
        collection.full_name,
    )

    records = _extract_sample(collection, pipeline, sample_size)
    if not records:
        raise RuntimeError(
            "La muestra no devolvió registros. Verifica que Fact_Resultados "
            "y las dimensiones tengan datos."
        )

    dataframe = pd.DataFrame.from_records(records)
    missing_columns = (
        set(FEATURE_COLUMNS + ["punt_global"]) - set(dataframe.columns)
    )
    if missing_columns:
        raise RuntimeError(
            "Faltan columnas en la extracción: "
            + ", ".join(sorted(missing_columns))
        )

    dataframe["estrato"] = _parse_estrato(dataframe["estrato"])
    dataframe["punt_global"] = pd.to_numeric(
        dataframe["punt_global"],
        errors="coerce",
    )
    dataframe = dataframe.dropna(subset=["punt_global"]).reset_index(drop=True)

    if dataframe.empty:
        raise RuntimeError(
            "No quedaron registros con punt_global válido después de la limpieza."
        )

    logger.info("Registros utilizables para entrenamiento: %s", f"{len(dataframe):,}")
    return dataframe


def build_preprocessor() -> ColumnTransformer:
    """Crea el preprocesador para variables numéricas y categóricas.

    ``estrato`` se imputa con la mediana. Las demás variables se imputan con la
    moda y se codifican con One-Hot Encoding.
    """
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
            ),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, NUMERIC_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )


def build_models() -> dict[str, Any]:
    """Devuelve los tres modelos que se compararán."""
    return {
        "RandomForest": RandomForestRegressor(
            n_estimators=100,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "GradientBoosting": GradientBoostingRegressor(
            n_estimators=100,
            random_state=RANDOM_STATE,
        ),
        "XGBoost": XGBRegressor(
            n_estimators=100,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }


def evaluate_model(
    model_name: str,
    estimator: Any,
    preprocessor: ColumnTransformer,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
) -> dict[str, Any]:
    """Evalúa un modelo con validación cruzada y con el conjunto de test.

    La validación cruzada se ejecuta sobre un ``Pipeline`` que incluye el
    preprocesador para evitar fuga de información entre folds.

    Args:
        model_name: Nombre legible del modelo.
        estimator: Instancia del regresor sin entrenar.
        preprocessor: ``ColumnTransformer`` sin entrenar.
        X_train: Features de entrenamiento.
        X_test: Features de test.
        y_train: Objetivo de entrenamiento.
        y_test: Objetivo de test.

    Returns:
        Diccionario con el modelo entrenado, el preprocesador entrenado y las
        métricas de evaluación.
    """
    logger.info("Evaluando %s con %d folds...", model_name, CV_FOLDS)

    cv_pipeline = Pipeline(
        steps=[
            ("preprocessor", clone(preprocessor)),
            ("model", clone(estimator)),
        ]
    )
    cv_scores = cross_val_score(
        cv_pipeline,
        X_train,
        y_train,
        cv=CV_FOLDS,
        scoring="neg_mean_absolute_error",
        # Los modelos de árbol ya usan n_jobs=-1; se evita paralelismo anidado.
        n_jobs=1,
    )
    cv_mae = -float(np.mean(cv_scores))

    fitted_preprocessor = clone(preprocessor).fit(X_train)
    X_train_prepared = fitted_preprocessor.transform(X_train)
    X_test_prepared = fitted_preprocessor.transform(X_test)

    fitted_model = clone(estimator).fit(X_train_prepared, y_train)
    predictions = fitted_model.predict(X_test_prepared)

    test_mae = float(mean_absolute_error(y_test, predictions))
    test_rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))
    test_r2 = float(r2_score(y_test, predictions))

    logger.info(
        "%s -> CV MAE: %.4f | Test MAE: %.4f | RMSE: %.4f | R2: %.4f",
        model_name,
        cv_mae,
        test_mae,
        test_rmse,
        test_r2,
    )

    return {
        "name": model_name,
        "cv_mae": cv_mae,
        "test_mae": test_mae,
        "rmse": test_rmse,
        "r2": test_r2,
        "model": fitted_model,
        "preprocessor": fitted_preprocessor,
    }


def train_and_select(
    dataframe: pd.DataFrame,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Divide los datos, entrena los modelos y selecciona el mejor por MAE.

    Returns:
        Una tupla con el mejor resultado y la lista completa de resultados.
    """
    X = dataframe[FEATURE_COLUMNS].copy()
    y = dataframe["punt_global"].astype(float)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
    )

    preprocessor = build_preprocessor()
    results = [
        evaluate_model(
            model_name=model_name,
            estimator=estimator,
            preprocessor=preprocessor,
            X_train=X_train,
            X_test=X_test,
            y_train=y_train,
            y_test=y_test,
        )
        for model_name, estimator in build_models().items()
    ]

    best_result = min(results, key=lambda result: result["test_mae"])
    return best_result, results


def save_artifact(
    best_result: dict[str, Any],
    output_path: Path,
) -> list[str]:
    """Guarda el modelo, el preprocesador y los nombres de features.

    Args:
        best_result: Resultado del mejor modelo.
        output_path: Ruta del archivo ``.pkl``.

    Returns:
        Lista con los nombres de las features transformadas por el modelo.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    feature_names = list(best_result["preprocessor"].get_feature_names_out())
    artifact = {
        "model": best_result["model"],
        "preprocessor": best_result["preprocessor"],
        "feature_names": feature_names,
    }

    joblib.dump(artifact, output_path, compress=3)
    logger.info("Artefacto guardado en %s", output_path)
    return feature_names


def print_report(
    results: list[dict[str, Any]],
    best_result: dict[str, Any],
    feature_names: list[str],
    output_path: Path,
) -> None:
    """Imprime la tabla comparativa, la importancia y el resumen final."""
    report = pd.DataFrame(
        [
            {
                "Modelo": result["name"],
                "CV MAE": result["cv_mae"],
                "Test MAE": result["test_mae"],
                "RMSE": result["rmse"],
                "R2": result["r2"],
            }
            for result in results
        ]
    )

    print("\n" + "=" * 78)
    print("COMPARACIÓN DE MODELOS")
    print("=" * 78)
    print(report.to_string(index=False, float_format=lambda value: f"{value:.4f}"))

    print("\n" + "=" * 78)
    print("IMPORTANCIA DE VARIABLES DEL MEJOR MODELO")
    print("=" * 78)

    model = best_result["model"]
    importances = getattr(model, "feature_importances_", None)
    if importances is None:
        print("El modelo seleccionado no expone feature_importances_.")
    else:
        importances_array = np.asarray(importances)
        if len(importances_array) == len(feature_names):
            series = pd.Series(importances_array, index=feature_names)
        else:
            series = pd.Series(importances_array)

        top_features = series.sort_values(ascending=False).head(20)
        print(top_features.to_string())

    print("\n" + "=" * 78)
    print("MEJOR MODELO SELECCIONADO")
    print("=" * 78)
    print(f"Modelo:        {best_result['name']}")
    print(f"CV MAE:        {best_result['cv_mae']:.4f}")
    print(f"Test MAE:      {best_result['test_mae']:.4f}")
    print(f"RMSE:          {best_result['rmse']:.4f}")
    print(f"R2:            {best_result['r2']:.4f}")
    print(f"Artefacto:     {output_path}")
    print("=" * 78)


def parse_args() -> argparse.Namespace:
    """Lee los argumentos opcionales de línea de comandos."""
    parser = argparse.ArgumentParser(
        description=(
            "Entrena modelos de regresión para predecir el puntaje global "
            "de Saber Pro."
        )
    )
    parser.add_argument(
        "--mongo-uri",
        default=os.getenv("MONGO_URI", DEFAULT_MONGO_URI),
        help="URI de conexión a MongoDB.",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("MONGO_DATABASE", DEFAULT_DATABASE),
        help="Nombre de la base de datos.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=SAMPLE_SIZE,
        help="Cantidad de registros aleatorios a extraer.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Ruta del artefacto .pkl de salida.",
    )
    return parser.parse_args()


def main() -> int:
    """Punto de entrada del script de entrenamiento."""
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    client: MongoClient | None = None
    try:
        client = MongoClient(
            args.mongo_uri,
            serverSelectionTimeoutMS=10_000,
        )
        client.admin.command("ping")
        logger.info(
            "Conectado a MongoDB: base de datos '%s'",
            args.database,
        )

        collection = client[args.database][DEFAULT_COLLECTION]
        dataframe = load_dataset(collection, args.sample_size)

        best_result, results = train_and_select(dataframe)
        feature_names = save_artifact(best_result, args.output)
        print_report(results, best_result, feature_names, args.output)
        return 0

    except (PyMongoError, ConnectionError, RuntimeError, ValueError) as exc:
        logger.error("El entrenamiento no pudo completarse: %s", exc)
        return 1
    except Exception:
        logger.exception("Error inesperado durante el entrenamiento.")
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
