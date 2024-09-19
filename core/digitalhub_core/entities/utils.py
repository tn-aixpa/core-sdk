from __future__ import annotations

from pathlib import Path

from digitalhub_core.entities.entity_types import EntityTypes
from digitalhub_core.utils.env_utils import get_s3_bucket
from digitalhub_core.utils.file_utils import get_file_mime_type
from digitalhub_core.utils.uri_utils import check_local_path


def parse_entity_key(key: str) -> tuple[str]:
    """
    Parse the entity key. Returns project, entity type, kind, name and uuid.

    Parameters
    ----------
    key : str
        The entity key.

    Returns
    -------
    tuple[str]
        Project, entity type, kind, name and uuid.
    """
    try:
        # Remove "store://" from the key
        key = key.replace("store://", "")

        # Split the key into parts
        parts = key.split("/")

        # The project is the first part
        project = parts[0]

        # The entity type is the second part
        entity_type = parts[1]

        # The kind is the third part
        kind = parts[2]

        # Tasks and runs have no name and uuid
        if entity_type in (EntityTypes.TASK.value, EntityTypes.RUN.value):
            name = None
            uuid = parts[3]

        # The name and uuid are separated by a colon in the last part
        else:
            name, uuid = parts[3].split(":")

        return project, entity_type, kind, name, uuid
    except Exception as e:
        raise ValueError("Invalid key format.") from e


def eval_local_source(source: str | list[str]) -> None:
    """
    Evaluate if source is local.

    Parameters
    ----------
    source : str | list[str]
        Source(s).

    Returns
    -------
    None
    """
    if isinstance(source, list):
        if not source:
            raise ValueError("Empty list of sources.")
        source_is_local = all(check_local_path(s) for s in source)
        for s in source:
            if Path(s).is_dir():
                raise ValueError(f"Invalid source path: {s}. List of paths must be list of files, not directories.")
    else:
        source_is_local = check_local_path(source)

    if not source_is_local:
        raise ValueError("Invalid source path. Source must be a local path.")


def eval_zip_type(source: str | list[str]) -> bool:
    """
    Evaluate zip type.

    Parameters
    ----------
    source : str | list[str]
        Source(s).

    Returns
    -------
    bool
        True if path is zip.
    """
    if isinstance(source, list):
        if len(source) > 1:
            return False
        else:
            path = source[0]
    else:
        if Path(source).is_dir():
            return False
        path = source

    extension = path.endswith(".zip")
    mime_zip = get_file_mime_type(path) == "application/zip"
    return extension or mime_zip


def build_log_path_from_filename(
    project: str,
    entity_type: str,
    name: str,
    uuid: str,
    filename: str,
) -> str:
    """
    Build log path.

    Parameters
    ----------
    project : str
        Project name.
    entity_type : str
        Entity type.
    name : str
        Object name.
    uuid : str
        Object UUID.
    filename : str
        Filename.

    Returns
    -------
    str
        Log path.
    """
    return f"s3://{get_s3_bucket()}/{project}/{entity_type}/{name}/{uuid}/{filename}"


def build_log_path_from_source(
    project: str,
    entity_type: str,
    name: str,
    uuid: str,
    source: str | list[str],
) -> str:
    """
    Build log path.

    Parameters
    ----------
    project : str
        Project name.
    entity_type : str
        Entity type.
    name : str
        Object name.
    uuid : str
        Object UUID.
    source : str | list[str]
        Source(s).

    Returns
    -------
    str
        Log path.
    """
    is_zip = eval_zip_type(source)
    scheme = "zip+s3" if is_zip else "s3"
    path = f"{scheme}://{get_s3_bucket()}/{project}/{entity_type}/{name}/{uuid}"

    if isinstance(source, list) and len(source) >= 1:
        if len(source) > 1:
            path += "/"
        else:
            path += f"/{Path(source[0]).name}"
    elif Path(source).is_dir():
        path += "/"
    elif Path(source).is_file():
        path += f"/{Path(source).name}"

    return path
