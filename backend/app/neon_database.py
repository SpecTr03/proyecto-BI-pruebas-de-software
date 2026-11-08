"""Conexión a la base de datos PostgreSQL administrada por Neon."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row


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

    def get_app_user(self, user_id: str) -> dict[str, str] | None:
        """Obtiene el usuario Neon y su rol activo de la aplicación."""
        try:
            with self.connection() as connection:
                with connection.cursor(row_factory=dict_row) as cursor:
                    row = cursor.execute(
                        """
                        SELECT u.id::text, u.name, u.email, a.role::text
                        FROM neon_auth."user" AS u
                        JOIN app.users AS a ON a.id = u.id
                        WHERE u.id = %s AND a.is_active
                        """,
                        (user_id,),
                    ).fetchone()
            return dict(row) if row else None
        except psycopg.Error as exc:
            raise ConnectionError("No fue posible consultar el usuario en Neon.") from exc


neon_database = NeonDatabase()
