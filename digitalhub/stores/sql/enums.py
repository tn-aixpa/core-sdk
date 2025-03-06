from __future__ import annotations

from enum import Enum


class SqlStoreEnv(Enum):
    """
    SqlStore environment
    """

    HOST = "DHCORE_DB_HOST"
    PORT = "DHCORE_DB_PORT"
    USERNAME = "DHCORE_DB_USERNAME"
    PASSWORD = "DHCORE_DB_PASSWORD"
    DATABASE = "DHCORE_DB_DATABASE"
    PG_SCHEMA = "DHCORE_DB_SCHEMA"
