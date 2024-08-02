from __future__ import annotations

import importlib.util as imputil
from pathlib import Path
from typing import Callable

from digitalhub_core.utils.generic_utils import (
    decode_string,
    extract_archive,
    get_bucket_and_key,
    get_s3_source,
    requests_chunk_download,
)
from digitalhub_core.utils.git_utils import clone_repository
from digitalhub_core.utils.logger import LOGGER
from digitalhub_core.utils.uri_utils import map_uri_scheme


def get_function_from_source(path: Path, source_spec: dict) -> Callable:
    """
    Get function from source.

    Parameters
    ----------
    path : Path
        Path where to save the function source.
    source_spec : dict
        Funcrion source spec.

    Returns
    -------
    Callable
        Function.
    """
    try:
        source_path = save_function_source(path, source_spec)
        handler_path, function_name = parse_handler(source_spec["handler"])
        function_path = (source_path / handler_path).with_suffix(".py")
        return import_function(function_path, function_name)
    except Exception as e:
        msg = f"Some error occurred while getting function. Exception: {e.__class__}. Error: {e.args}"
        LOGGER.exception(msg)
        raise RuntimeError(msg) from e


def parse_handler(handler: str) -> tuple:
    """
    Parse handler.

    Parameters
    ----------
    handler : str
        Function handler

    Returns
    -------
    str
        Function handler.
    """
    parsed = handler.split(":")
    if len(parsed) == 1:
        return Path(""), parsed[0]
    return Path(*parsed[0].split(".")), parsed[1]


def save_function_source(path: Path, source_spec: dict) -> Path:
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
    Path
        Path to the function source.
    """
    # Prepare path
    path.mkdir(parents=True, exist_ok=True)

    # Get relevant information
    base64 = source_spec.get("base64")
    source = source_spec.get("source")

    scheme = None
    if source is not None:
        scheme = map_uri_scheme(source)

    # Base64
    if base64 is not None:
        filename = "main.py"
        if scheme == "local":
            filename = Path(source).name

        base64_path = path / filename
        base64_path.write_text(decode_base64(base64))

        if scheme is None or scheme == "local":
            return base64_path

    # Git repo
    if scheme == "git":
        get_repository(path, source)

    # Http(s) or s3 presigned urls
    elif scheme == "remote":
        filename = path / "archive.zip"
        get_remote_source(source, filename)
        unzip(path, filename)

    # S3 path
    elif scheme == "s3":
        filename = path / "archive.zip"
        bucket, key = get_bucket_and_key(source)
        get_s3_source(bucket, key, filename)
        unzip(path, filename)

    # Unsupported scheme
    else:
        raise RuntimeError(f"Unsupported scheme: {scheme}")

    return path


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
    except Exception as e:
        msg = f"Some error occurred while downloading function source. Exception: {e.__class__}. Error: {e.args}"
        LOGGER.exception(msg)
        raise RuntimeError(msg) from e


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
    except Exception as e:
        msg = f"Source must be a valid zipfile. Exception: {e.__class__}. Error: {e.args}"
        LOGGER.exception(msg)
        raise RuntimeError(msg) from e


def get_repository(path: Path, source: str) -> None:
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
        clone_repository(source, path)
    except Exception as e:
        msg = f"Some error occurred while downloading function repo source. Exception: {e.__class__}. Error: {e.args}"
        LOGGER.exception(msg)
        raise RuntimeError(msg) from e


def decode_base64(base64: str) -> str:
    """
    Decode base64 encoded code.

    Parameters
    ----------
    base64 : str
        The encoded code.

    Returns
    -------
    str
        The decoded code.

    Raises
    ------
    RuntimeError
        Error while decoding code.
    """
    try:
        return decode_string(base64)
    except Exception as e:
        msg = f"Some error occurred while decoding function source. Exception: {e.__class__}. Error: {e.args}"
        LOGGER.exception(msg)
        raise RuntimeError(msg) from e


def import_function(path: Path, handler: str) -> Callable:
    """
    Import a function from a module.

    Parameters
    ----------
    path : Path
        Path where the function source is located.
    handler : str
        Function name.

    Returns
    -------
    Callable
        Function.
    """
    try:
        spec = imputil.spec_from_file_location(path.stem, path)
        mod = imputil.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return getattr(mod, handler)
    except Exception as e:
        msg = f"Some error occurred while importing function. Exception: {e.__class__}. Error: {e.args}"
        LOGGER.exception(msg)
        raise RuntimeError(msg) from e
