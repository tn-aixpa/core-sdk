from __future__ import annotations

import os

import psycopg2
from digitalhub.utils.logger import LOGGER

POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE")
POSTGRES_SCHEMA = os.getenv("POSTGRES_SCHEMA", "public")


def get_connection() -> psycopg2.extensions.connection:
    """
    Create a connection to postgres and return a session with autocommit enabled.

    Returns
    -------
    psycopg2.extensions.connection
        The connection to postgres.

    Raises
    ------
    RuntimeError
        If something got wrong during connection to postgres.
    """
    try:
        LOGGER.info("Connecting to postgres.")
        return psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DATABASE,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
        )
    except Exception as e:
        msg = f"Something got wrong during connection to postgres. Exception: {e.__class__}. Error: {e.args}"
        LOGGER.exception(msg)
        raise RuntimeError(msg) from e
