from __future__ import annotations

import typing
from pathlib import Path

from digitalhub_core.entities.functions.crud import get_function
from digitalhub_core.utils.generic_utils import (
    build_uuid,
    clone_repository,
    decode_string,
    extract_archive,
    get_bucket_and_key,
    get_s3_source,
    requests_chunk_download,
)
from digitalhub_core.utils.logger import LOGGER
from mlrun import get_or_create_project

if typing.TYPE_CHECKING:
    from digitalhub_core.entities.functions.entity import Function
    from mlrun.projects import MlrunProject
    from mlrun.runtimes import BaseRuntime


def get_dhcore_function(function_string: str) -> Function:
    """
    Get DHCore function.

    Parameters
    ----------
    function_string : str
        Function string.

    Returns
    -------
    Function
        DHCore function.
    """
    splitted = function_string.split("://")[1].split("/")
    function_name, function_version = splitted[1].split(":")
    LOGGER.info(f"Getting function {function_name}:{function_version}.")
    try:
        return get_function(splitted[0], function_name, function_version)
    except Exception:
        msg = f"Error getting function {function_name}:{function_version}."
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
        Path to the function source.
    """
    # Prepare path
    path.mkdir(parents=True, exist_ok=True)

    # Get relevant information
    base64 = source_spec.get("base64")
    source = source_spec.get("source")
    handler = source_spec.get("handler")

    # First check if source is base64
    if base64 is not None:
        filename = build_uuid().replace("-", "_") + ".py"
        path = path / filename
        decode_base64(path, base64)
        return str(path)

    # Second check if source is path
    if not (source is not None and handler is not None):
        raise RuntimeError("Function source and handler must be defined.")

    scheme = source.split("://")[0]

    # Http(s) or s3 presigned urls
    if scheme in ["http", "https"]:
        filename = path / "archive.zip"
        get_remote_source(source, filename)
        unzip(path, filename)
        return str(path / handler)

    # Git repo
    if scheme == "git+https":
        source = source.replace("git+", "")
        path = path / "repository"
        get_repository(path, source)
        return str(path / handler)

    # S3 path
    if scheme == "zip+s3":
        filename = path / "archive.zip"
        bucket, key = get_bucket_and_key(source)
        get_s3_source(bucket, key, filename)
        unzip(path, filename)
        return str(path / handler)

    # Unsupported scheme
    raise RuntimeError(f"Unsupported scheme: {scheme}")


def get_remote_source(source: str, filename: Path) -> None:
    """
    Get remote source.

    Parameters
    ----------
    source : str
        HTTP(S) or S3 presigned URL.
    filename : Path
        Path where to save the function source.

    Returns
    -------
    str
        Function code.
    """
    try:
        requests_chunk_download(source, filename)
    except Exception:
        msg = "Some error occurred while downloading function source."
        LOGGER.exception(msg)
        raise RuntimeError(msg)


def unzip(path: Path, filename: Path) -> None:
    """
    Extract an archive.

    Parameters
    ----------
    path : Path
        Path where to extract the archive.
    filename : Path
        Path to the archive.

    Returns
    -------
    None
    """

    try:
        extract_archive(path, filename)
    except Exception:
        msg = "Source must be a valid zipfile."
        LOGGER.exception(msg)
        raise RuntimeError(msg)


def get_repository(path: Path, source: str) -> str:
    """
    Get repository.

    Parameters
    ----------
    path : Path
        Path where to save the function source.
    source : str
        Git repository URL in format git://<url>.

    Returns
    -------
    None
    """
    try:
        clone_repository(path, source)
    except Exception:
        msg = "Some error occurred while downloading function repo source."
        LOGGER.exception(msg)
        raise RuntimeError(msg)


def decode_base64(path: Path, base64: str) -> str:
    """
    Save function source.

    Parameters
    ----------
    path : str
        Path where to save the function source.
    base64 : str
        Function source base64.

    Returns
    -------
    path
        Path to the function source.
    """
    try:
        path.write_text(decode_string(base64))
    except Exception:
        msg = "Some error occurred while decoding function source."
        LOGGER.exception(msg)
        raise RuntimeError(msg)


def get_mlrun_project(project_name: str) -> MlrunProject:
    """
    Get Mlrun project.

    Parameters
    ----------
    project_name : str
        Project name.

    Returns
    -------
    MlrunProject
        Mlrun project.
    """
    try:
        return get_or_create_project(project_name, "./")
    except Exception:
        msg = f"Error getting Mlrun project '{project_name}'."
        LOGGER.exception(msg)
        raise RuntimeError(msg)


def get_mlrun_function(
    project: MlrunProject,
    function_name: str,
    function_source: str,
    function_specs: dict,
) -> BaseRuntime:
    """
    Get Mlrun function.

    Parameters
    ----------
    project : MlrunProject
        Mlrun project.
    function_name : str
        Name of the function.
    function_source : str
        Path to the function source.
    function_specs : dict
        Function specs.

    Returns
    -------
    BaseRuntime
        Mlrun function.
    """
    try:
        project.set_function(function_source, name=function_name, **function_specs)
        project.save()
        return project.get_function(function_name)
    except Exception:
        msg = f"Error getting Mlrun function '{function_name}'."
        LOGGER.exception(msg)
        raise RuntimeError(msg)


def parse_function_specs(spec: dict) -> dict:
    """
    Parse function specs.

    Parameters
    ----------
    function : dict
        DHCore function spec.

    Returns
    -------
    dict
        Function specs.
    """
    try:
        return {
            "image": spec.get("image"),
            "tag": spec.get("tag"),
            # "command": spec.get("command"),
            "handler": spec.get("handler"),
        }
    except AttributeError:
        msg = "Error parsing function specs."
        LOGGER.error(msg)
        raise RuntimeError(msg)
