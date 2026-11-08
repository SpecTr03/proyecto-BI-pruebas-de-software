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

    def list_app_users(self) -> list[dict[str, object]]:
        """Lista las cuentas autenticadas y su estado administrativo."""
        try:
            with self.connection() as connection:
                with connection.cursor(row_factory=dict_row) as cursor:
                    rows = cursor.execute(
                        """
                        SELECT u.id::text, u.name, u.email, a.role::text,
                               a.is_active
                        FROM neon_auth."user" AS u
                        JOIN app.users AS a ON a.id = u.id
                        ORDER BY u.name, u.email
                        """
                    ).fetchall()
            return [dict(row) for row in rows]
        except psycopg.Error as exc:
            raise ConnectionError("No fue posible listar los usuarios.") from exc

    def get_user_by_email(self, email: str) -> dict[str, str] | None:
        """Busca una cuenta creada en Neon Auth por correo."""
        try:
            with self.connection() as connection:
                with connection.cursor(row_factory=dict_row) as cursor:
                    row = cursor.execute(
                        """
                        SELECT id::text, name, email
                        FROM neon_auth."user"
                        WHERE LOWER(email) = LOWER(%s)
                        """,
                        (email,),
                    ).fetchone()
            return dict(row) if row else None
        except psycopg.Error as exc:
            raise ConnectionError("No fue posible consultar el correo en Neon Auth.") from exc

    def upsert_app_user(
        self,
        user_id: str,
        email: str,
        role: str,
        is_active: bool = True,
    ) -> dict[str, object] | None:
        """Crea o actualiza el rol y el estado de una cuenta de aplicación."""
        try:
            with self.connection() as connection:
                with connection.cursor(row_factory=dict_row) as cursor:
                    row = cursor.execute(
                        """
                        INSERT INTO app.users (id, email, role, is_active)
                        VALUES (%s::uuid, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            email = EXCLUDED.email,
                            role = EXCLUDED.role,
                            is_active = EXCLUDED.is_active,
                            updated_at = NOW()
                        RETURNING id::text, role::text, is_active
                        """,
                        (user_id, email, role, is_active),
                    ).fetchone()
                    connection.commit()
            return dict(row) if row else None
        except psycopg.Error as exc:
            raise ConnectionError("No fue posible guardar el usuario.") from exc


neon_database = NeonDatabase()
