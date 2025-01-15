from __future__ import annotations

from enum import Enum


class SqlStoreEnv(Enum):
    """
    SqlStore environment
    """

    HOST = "POSTGRES_HOST"
    PORT = "POSTGRES_PORT"
    USER = "POSTGRES_USER"
    PASSWORD = "POSTGRES_PASSWORD"
    DATABASE = "POSTGRES_DATABASE"
    PG_SCHEMA = "POSTGRES_SCHEMA"
