from __future__ import annotations

from pathlib import Path

from digitalhub_core.utils.generic_utils import decode_string
from digitalhub_core.utils.logger import LOGGER
from digitalhub_data_dbt.utils.env import (
    POSTGRES_DATABASE,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_SCHEMA,
    POSTGRES_USER,
)

####################
# Templates
####################

PROJECT_TEMPLATE = """
name: "{}"
version: "1.0.0"
config-version: 2
profile: "postgres"
model-paths: ["{}"]
models:
""".lstrip(
    "\n"
)

MODEL_TEMPLATE_VERSION = """
models:
  - name: {}
    latest_version: {}
    versions:
        - v: {}
          config:
            materialized: table
""".lstrip(
    "\n"
)

PROFILE_TEMPLATE = f"""
postgres:
    outputs:
        dev:
            type: postgres
            host: {POSTGRES_HOST}
            user: {POSTGRES_USER}
            pass: {POSTGRES_PASSWORD}
            port: {POSTGRES_PORT}
            dbname: {POSTGRES_DATABASE}
            schema: {POSTGRES_SCHEMA}
    target: dev
""".lstrip(
    "\n"
)


def generate_dbt_profile_yml(root_dir: Path) -> None:
    """
    Create dbt profiles.yml

    Returns
    -------
    None
    """
    profiles_path = root_dir / "profiles.yml"
    profiles_path.write_text(PROFILE_TEMPLATE)


def generate_dbt_project_yml(root_dir: Path, model_dir: Path, project: str) -> None:
    """
    Create dbt_project.yml from 'dbt'

    Parameters
    ----------
    project : str
        The project name.

    Returns
    -------
    None
    """
    project_path = root_dir / "dbt_project.yml"
    project_path.write_text(PROJECT_TEMPLATE.format(project, model_dir.name))


def generate_outputs_conf(model_dir: Path, sql: str, output: str, uuid: str) -> None:
    """
    Write sql code for the model and write schema
    and version detail for outputs versioning

    Parameters
    ----------
    sql : str
        The sql code.
    output : str
        The output table name.
    uuid : str
        The uuid of the model for outputs versioning.

    Returns
    -------
    None
    """
    sql_path = model_dir / f"{output}.sql"
    sql_path.write_text(sql)

    output_path = model_dir / f"{output}.yml"
    output_path.write_text(MODEL_TEMPLATE_VERSION.format(output, uuid, uuid))


def generate_inputs_conf(model_dir: Path, name: str, uuid: str) -> None:
    """
    Generate inputs confs dependencies for dbt project.

    Parameters
    ----------
    project : str
        The project name.
    inputs : list
        The list of inputs dataitems names.

    Returns
    -------
    None
    """
    # write schema and version detail for inputs versioning
    input_path = model_dir / f"{name}.yml"
    input_path.write_text(MODEL_TEMPLATE_VERSION.format(name, uuid, uuid))

    # write also sql select for the schema
    sql_path = model_dir / f"{name}_v{uuid}.sql"
    sql_path.write_text(f'SELECT * FROM "{name}_v{uuid}"')


def get_output_table_name(outputs: list[dict]) -> str:
    """
    Get output table name from run spec.

    Parameters
    ----------
    outputs : list
        The outputs.

    Returns
    -------
    str
        The output dataitem/table name.

    Raises
    ------
    RuntimeError
        If outputs are not a list of one dataitem.
    """
    try:
        return outputs[0]["output_table"]
    except IndexError:
        msg = "Outputs must be a list of one dataitem."
        LOGGER.exception(msg)
        raise RuntimeError(msg)
    except KeyError:
        msg = "Must pass reference to 'output_table'."
        LOGGER.exception(msg)
        raise RuntimeError(msg)


def save_function_source(path: Path, source_spec: dict) -> str:
    """
    Save function source.

    Parameters
    ----------
    path : Path
        Path where to save the function source.
    source_spec : dict
        Function source spec.

    Returns
    -------
    path
        Function code.
    """
    path.mkdir(parents=True, exist_ok=True)
    base64 = source_spec.get("base64")
    if base64 is not None:
        return decode_base64(base64)
    raise NotImplementedError


def decode_base64(base64: str) -> str:
    """
    Decode sql code.

    Parameters
    ----------
    sql : str
        The sql code.

    Returns
    -------
    str
        The decoded sql code.

    Raises
    ------
    RuntimeError
        If sql code is not a valid string.
    """
    try:
        return decode_string(base64)
    except Exception:
        msg = "Sql code must be a valid string."
        LOGGER.exception(msg)
        raise RuntimeError(msg)
