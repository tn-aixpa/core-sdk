from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from mimetypes import guess_type
from pathlib import Path

from pydantic import BaseModel

from digitalhub.utils.uri_utils import has_local_scheme


class FileInfo(BaseModel):
    """
    File info class.
    """

    path: str = None
    name: str = None
    content_type: str = None
    size: int = None
    hash: str = None
    last_modified: str = None

    def to_dict(self):
        return self.model_dump()


def calculate_blob_hash(data_path: str) -> str:
    """
    Calculate the hash of a file.

    Parameters
    ----------
    data_path : str
        Path to the file.

    Returns
    -------
    str
        The hash of the file.
    """
    with open(data_path, "rb") as f:
        data = f.read()
        return f"sha256:{sha256(data).hexdigest()}"


def get_file_size(data_path: str) -> int:
    """
    Get the size of a file.

    Parameters
    ----------
    data_path : str
        Path to the file.

    Returns
    -------
    int
        The size of the file.
    """
    return Path(data_path).stat().st_size


def get_file_mime_type(data_path: str) -> str:
    """
    Get the mime type of a file.

    Parameters
    ----------
    data_path : str
        Path to the file.

    Returns
    -------
    str
        The mime type of the file.
    """
    return guess_type(data_path)[0]


def get_path_name(data_path: str) -> str:
    """
    Get the name of a file.

    Parameters
    ----------
    data_path : str
        Path to the file.

    Returns
    -------
    str
        The name of the file.
    """
    return Path(data_path).name


def get_last_modified(data_path: str) -> str:
    """
    Get the last modified date of a file.

    Parameters
    ----------
    data_path : str
        Path to the file.

    Returns
    -------
    str
        The last modified date of the file.
    """
    path = Path(data_path)
    timestamp = path.stat().st_mtime
    return datetime.fromtimestamp(timestamp).astimezone().isoformat()


def get_s3_path(src_path: str) -> str:
    """
    Get the S3 path of a file.

    Parameters
    ----------
    src_path : str
        Path to the file.

    Returns
    -------
    str
        The S3 path of the file.
    """
    return Path(src_path).as_uri()


def get_file_info_from_local(path: str, src_path: str) -> None | dict:
    """
    Get file info from path.

    Parameters
    ----------
    path : str
        Target path of the object.
    src_path : str
        Local path of some source.

    Returns
    -------
    dict
        File info.
    """
    try:
        name = get_path_name(path)
        content_type = get_file_mime_type(path)
        size = get_file_size(path)
        hash = calculate_blob_hash(path)
        last_modified = get_last_modified(path)

        return FileInfo(
            path=src_path,
            name=name,
            content_type=content_type,
            size=size,
            hash=hash,
            last_modified=last_modified,
        ).to_dict()
    except Exception:
        return None


def get_file_info_from_s3(path: str, metadata: dict) -> None | dict:
    """
    Get file info from path.

    Parameters
    ----------
    path : str
        Object source path.
    metadata : dict
        Metadata of the object from S3.

    Returns
    -------
    dict
        File info.
    """
    try:
        size = metadata["ContentLength"]
        file_hash = metadata["ETag"][1:-1]

        file_size_limit_multipart = 20 * 1024 * 1024
        if size < file_size_limit_multipart:
            file_hash = "md5:" + file_hash
        else:
            file_hash = "LiteralETag:" + file_hash

        name = get_path_name(path)
        content_type = metadata["ContentType"]
        last_modified = metadata["LastModified"].isoformat()

        return FileInfo(
            path=path,
            name=name,
            content_type=content_type,
            size=size,
            hash=file_hash,
            last_modified=last_modified,
        ).to_dict()
    except Exception:
        return None


def eval_zip_type(source: str) -> bool:
    """
    Evaluate zip type.

    Parameters
    ----------
    source : str
        Source.

    Returns
    -------
    bool
        True if path is zip.
    """
    extension = source.endswith(".zip")
    mime_zip = get_file_mime_type(source) == "application/zip"
    return extension or mime_zip


def eval_text_type(source: str) -> bool:
    """
    Evaluate text type.

    Parameters
    ----------
    source : str
        Source.

    Returns
    -------
    bool
        True if path is text.
    """
    return get_file_mime_type(source) == "text/plain"


def eval_py_type(source: str) -> bool:
    """
    Evaluate python type.

    Parameters
    ----------
    source : str
        Source.

    Returns
    -------
    bool
        True if path is python.
    """
    extension = source.endswith(".py")
    mime_py = get_file_mime_type(source) == "text/x-python"
    return extension or mime_py


def eval_zip_sources(source: str | list[str]) -> bool:
    """
    Evaluate zip sources.

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

    return eval_zip_type(path)


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
        source_is_local = all(has_local_scheme(s) for s in source)
        for s in source:
            if Path(s).is_dir():
                raise ValueError(f"Invalid source path: {s}. List of paths must be list of files, not directories.")
    else:
        source_is_local = has_local_scheme(source)

    if not source_is_local:
        raise ValueError("Invalid source path. Source must be a local path.")
