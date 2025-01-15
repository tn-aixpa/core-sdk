from __future__ import annotations

import typing

from digitalhub.stores.builder import store_builder

if typing.TYPE_CHECKING:
    from digitalhub.stores._base.store import Store


def get_store(project: str, uri: str, config: dict | None = None) -> Store:
    """
    Get store instance by URI.

    Parameters
    ---------
    project : str
        Project name.
    uri : str
        URI to parse.
    config : dict
        Store configuration.

    Returns
    -------
    Store
        Store instance.
    """
    return store_builder.get(uri, config)
