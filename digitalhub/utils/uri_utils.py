from __future__ import annotations

from enum import Enum
from urllib.parse import urlparse


class Scheme(Enum):
    """
    Scheme types.
    """

    S3 = "s3"
    LOCAL = "local"
    REMOTE = "remote"
    SQL = "sql"
    GIT = "git"


def map_uri_scheme(uri: str) -> str:
    """
    Map an URI scheme to a common scheme.

    Parameters
    ----------
    uri : str
        URI.

    Returns
    -------
    str
        Mapped scheme type.

    Raises
    ------
    ValueError
        If the scheme is unknown.
    """
    scheme = urlparse(uri).scheme
    if scheme in [""]:
        return Scheme.LOCAL.value
    if scheme in ["file", "local"]:
        raise ValueError("For local path, do not use any scheme")
    if scheme in ["http", "https"]:
        return Scheme.REMOTE.value
    if scheme in ["s3", "s3a", "s3n", "zip+s3"]:
        return Scheme.S3.value
    if scheme in ["sql", "postgresql"]:
        return Scheme.SQL.value
    if scheme in ["git", "git+http", "git+https"]:
        return Scheme.GIT.value
    raise ValueError(f"Unknown scheme '{scheme}'!")


def has_local_scheme(path: str) -> bool:
    """
    Check if path is local.

    Parameters
    ----------
    path : str
        Path of some source.

    Returns
    -------
    bool
        True if path is local.
    """
    return map_uri_scheme(path) == Scheme.LOCAL.value


def has_remote_scheme(path: str) -> bool:
    """
    Check if path is remote.

    Parameters
    ----------
    path : str
        Path of some source.

    Returns
    -------
    bool
        True if path is remote.
    """
    return map_uri_scheme(path) == Scheme.REMOTE.value


def has_s3_scheme(path: str) -> bool:
    """
    Check if path is s3.

    Parameters
    ----------
    path : str
        Path of some source.

    Returns
    -------
    bool
        True if path is s3.
    """
    return map_uri_scheme(path) == Scheme.S3.value


def has_sql_scheme(path: str) -> bool:
    """
    Check if path is sql.

    Parameters
    ----------
    path : str
        Path of some source.

    Returns
    -------
    bool
        True if path is sql.
    """
    return map_uri_scheme(path) == Scheme.SQL.value


def has_git_scheme(path: str) -> bool:
    """
    Check if path is git.

    Parameters
    ----------
    path : str
        Path of some source.

    Returns
    -------
    bool
        True if path is git.
    """
    return map_uri_scheme(path) == Scheme.GIT.value
