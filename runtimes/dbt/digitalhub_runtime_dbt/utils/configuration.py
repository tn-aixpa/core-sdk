from __future__ import annotations

from pathlib import Path

from digitalhub.utils.generic_utils import decode_base64_string, extract_archive, requests_chunk_download
from digitalhub.utils.git_utils import clone_repository
from digitalhub.utils.logger import LOGGER
from digitalhub.utils.s3_utils import get_bucket_and_key, get_s3_source
from digitalhub.utils.uri_utils import has_git_scheme, has_remote_scheme, has_s3_scheme

from digitalhub_runtime_dbt.utils.env import (
    POSTGRES_DATABASE,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_SCHEMA,
    POSTGRES_USER,
)

##############################
# Templates
##############################

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
            host: "{POSTGRES_HOST}"
            user: "{POSTGRES_USER}"
            pass: "{POSTGRES_PASSWORD}"
            port: {POSTGRES_PORT}
            dbname: "{POSTGRES_DATABASE}"
            schema: "{POSTGRES_SCHEMA}"
    target: dev
""".lstrip(
    "\n"
)


def generate_dbt_profile_yml(root: Path) -> None:
    """
    Create dbt profiles.yml

    Returns
    -------
    None
    """
    profiles_path = root / "profiles.yml"
    profiles_path.write_text(PROFILE_TEMPLATE)


def generate_dbt_project_yml(root: Path, model_dir: Path, project: str) -> None:
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
    project_path = root / "dbt_project.yml"
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
        return outputs["output_table"]
    except IndexError as e:
        msg = f"Outputs must be a list of one dataitem. Exception: {e.__class__}. Error: {e.args}"
        LOGGER.exception(msg)
        raise RuntimeError(msg) from e
    except KeyError as e:
        msg = f"Must pass reference to 'output_table'. Exception: {e.__class__}. Error: {e.args}"
        LOGGER.exception(msg)
        raise RuntimeError(msg) from e


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
    # Get relevant information
    code = source_spec.get("code")
    base64 = source_spec.get("base64")
    source = source_spec.get("source")
    handler: str = source_spec.get("handler")

    if code is not None:
        return code

    if base64 is not None:
        return decode_base64_string(base64)

    # Http(s) or s3 presigned urls
    if has_remote_scheme(source):
        filename = path / "archive.zip"
        requests_chunk_download(source, filename)
        extract_archive(path, filename)

    # Git repo
    if has_git_scheme(source):
        path = path / "repository"
        clone_repository(path, source)

    # S3 path
    if has_s3_scheme(source):
        filename = path / "archive.zip"
        bucket, key = get_bucket_and_key(source)
        get_s3_source(bucket, key, filename)
        extract_archive(path, filename)

    if handler is not None:
        return (path / handler).read_text()

    # Unsupported scheme
    raise RuntimeError("Unable to collect source.")
