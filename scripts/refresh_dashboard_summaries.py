"""Recalcula agregados persistentes para acelerar el dashboard."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / "backend" / ".env")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import MongoConnection
from backend.app.services.dashboard_summaries import refresh_dashboard_summaries


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh cached dashboard aggregates in MongoDB."
    )
    parser.add_argument(
        "--mongo-uri",
        default=os.getenv("MONGO_URI", "mongodb://localhost:27017/"),
    )
    parser.add_argument(
        "--database",
        default=os.getenv("MONGO_DATABASE", "SaberProDB"),
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )
    connection = MongoConnection(args.mongo_uri, args.database)
    try:
        database = connection.connect()
        counts = refresh_dashboard_summaries(database)
        for key, count in counts.items():
            logging.info("Resumen %s actualizado (%d elementos).", key, count)
        return 0
    except Exception:
        logging.exception("No fue posible actualizar los resúmenes del dashboard.")
        return 1
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
