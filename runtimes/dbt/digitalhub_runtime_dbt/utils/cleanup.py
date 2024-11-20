from __future__ import annotations

import shutil
from pathlib import Path

from digitalhub.utils.logger import LOGGER
from psycopg2 import sql

from digitalhub_runtime_dbt.utils.env import get_connection


def cleanup(tables: list[str], tmp_dir: Path) -> None:
    """
    Cleanup environment.

    Parameters
    ----------
    tables : list[str]
        List of tables to delete.

    Returns
    -------
    None
    """
    try:
        connection = get_connection()
        with connection:
            with connection.cursor() as cursor:
                for table in tables:
                    LOGGER.info(f"Dropping table '{table}'.")
                    query = sql.SQL("DROP TABLE {table}").format(table=sql.Identifier(table))
                    cursor.execute(query)
    except Exception as e:
        msg = f"Something got wrong during environment cleanup. Exception: {e.__class__}. Error: {e.args}"
        LOGGER.exception(msg)
        raise RuntimeError(msg) from e
    finally:
        LOGGER.info("Closing connection to postgres.")
        connection.close()

    LOGGER.info("Removing temporary directory.")
    shutil.rmtree(tmp_dir, ignore_errors=True)
