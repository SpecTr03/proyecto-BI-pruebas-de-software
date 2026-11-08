"""Conexión a la base de datos PostgreSQL administrada por Neon."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg


class NeonDatabase:
    """Abre conexiones PostgreSQL usando la URL agrupada para la aplicación."""

    def __init__(self) -> None:
        self._database_url = os.getenv("DATABASE_URL")

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        if not self._database_url:
            raise ConnectionError("DATABASE_URL no está configurada.")

        connection = psycopg.connect(self._database_url, connect_timeout=5)
        try:
            yield connection
        finally:
            connection.close()

    def ping(self) -> bool:
        try:
            with self.connection() as connection:
                connection.execute("SELECT 1").fetchone()
            return True
        except (ConnectionError, psycopg.Error):
            return False


neon_database = NeonDatabase()
