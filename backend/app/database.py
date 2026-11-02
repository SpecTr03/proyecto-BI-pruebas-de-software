"""Conexión Singleton a MongoDB.

La aplicación comparte un único ``MongoClient`` durante todo su ciclo de vida.
El cliente se crea de forma perezosa (lazy) y se reutiliza en cada request.

Variables de entorno:
    MONGO_URI: URI de conexión a MongoDB.
    MONGO_DATABASE: Nombre de la base de datos (por defecto ``SaberProDB``).
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Optional

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)

DEFAULT_MONGO_URI = "mongodb://localhost:27017/"
DEFAULT_MONGO_DATABASE = "SaberProDB"
DEFAULT_SERVER_SELECTION_TIMEOUT_MS = 5_000


class MongoConnection:
    """Singleton que administra la conexión a MongoDB.

    El patrón se implementa con ``__new__`` y un lock para que dos hilos no
    puedan crear dos clientes distintos al mismo tiempo.
    """

    _instance: Optional["MongoConnection"] = None
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs) -> "MongoConnection":
        """Devuelve siempre la misma instancia de la clase."""
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instance = instance
            return cls._instance

    def __init__(
        self,
        uri: str | None = None,
        database_name: str | None = None,
    ) -> None:
        """Inicializa la configuración una sola vez.

        Args:
            uri: URI de MongoDB. Si es ``None`` se lee ``MONGO_URI``.
            database_name: Nombre de la base de datos. Si es ``None`` se lee
                ``MONGO_DATABASE``.
        """
        if getattr(self, "_initialized", False):
            return

        with self._lock:
            if getattr(self, "_initialized", False):
                return

            self._uri = uri or os.getenv("MONGO_URI", DEFAULT_MONGO_URI)
            self._database_name = database_name or os.getenv(
                "MONGO_DATABASE", DEFAULT_MONGO_DATABASE
            )
            self._client: MongoClient | None = None
            self._database: Database | None = None
            self._initialized = True

    @property
    def database_name(self) -> str:
        """Nombre de la base de datos configurada."""
        return self._database_name

    def connect(self) -> Database:
        """Crea el cliente y valida la conexión.

        Returns:
            La instancia de la base de datos configurada.

        Raises:
            ConnectionError: Si MongoDB no está disponible o la URI es inválida.
        """
        with self._lock:
            if self._database is not None:
                return self._database

            client: MongoClient | None = None
            try:
                client = MongoClient(
                    self._uri,
                    serverSelectionTimeoutMS=DEFAULT_SERVER_SELECTION_TIMEOUT_MS,
                    appname="saberpro-bi-api",
                )
                # ``admin.command("ping")`` obliga a validar la conexión real.
                client.admin.command("ping")
                database = client[self._database_name]
            except (PyMongoError, ValueError) as exc:
                if client is not None:
                    client.close()
                raise ConnectionError(
                    f"No se pudo conectar a MongoDB en '{self._uri}' "
                    f"(base de datos: '{self._database_name}')"
                ) from exc

            self._client = client
            self._database = database
            logger.info(
                "Conexión MongoDB establecida: base de datos '%s'",
                self._database_name,
            )
            return self._database

    def get_database(self) -> Database:
        """Devuelve la base de datos, conectándose si es necesario."""
        return self.connect()

    def ping(self) -> bool:
        """Comprueba si MongoDB responde.

        Returns:
            ``True`` si el servidor responde al comando ``ping``; ``False`` en
            caso contrario.
        """
        try:
            self.connect().command("ping")
            return True
        except (ConnectionError, PyMongoError):
            logger.warning("MongoDB no responde al ping", exc_info=True)
            return False

    def close(self) -> None:
        """Cierra el cliente y libera la referencia a la base de datos.

        La instancia Singleton se conserva para permitir reconectar más tarde.
        """
        with self._lock:
            if self._client is not None:
                self._client.close()
                logger.info("Conexión MongoDB cerrada")
            self._client = None
            self._database = None

    @classmethod
    def reset_instance(cls) -> None:
        """Elimina la instancia Singleton.

        Está pensado para pruebas unitarias. En producción no es necesario.
        """
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
            cls._instance = None


# Instancia global usada por toda la aplicación.
mongo_connection = MongoConnection()
