from __future__ import annotations

import typing

from digitalhub.context.api import get_context
from digitalhub.stores.data.builder import store_builder

if typing.TYPE_CHECKING:
    from digitalhub.stores.data._base.store import Store


def get_store(project: str, uri: str) -> Store:
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
    config = get_context(project).config
    return store_builder.get(project, uri, config)
