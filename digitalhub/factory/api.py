from __future__ import annotations

import typing

from digitalhub.factory.factory import factory
from digitalhub.utils.exceptions import BuilderError

if typing.TYPE_CHECKING:
    from digitalhub.entities._base.entity.entity import Entity
    from digitalhub.entities._base.entity.metadata import Metadata
    from digitalhub.entities._base.entity.spec import Spec
    from digitalhub.entities._base.entity.status import Status
    from digitalhub.runtimes._base import Runtime


def build_entity_from_params(**kwargs) -> Entity:
    """
    Build an entity from keyword parameters.

    Parameters
    ----------
    **kwargs : dict
        Entity parameters. Must include 'kind' parameter specifying entity type.

    Returns
    -------
    Entity
        The constructed entity instance.

    Raises
    ------
    BuilderError
        If 'kind' parameter is missing or builder not found.
    """
    try:
        kind = kwargs["kind"]
    except KeyError:
        raise BuilderError("Missing 'kind' parameter.")
    _raise_if_entity_builder_not_found(kind)
    return factory.build_entity_from_params(kind, **kwargs)


def build_entity_from_dict(obj: dict) -> Entity:
    """
    Build an entity from a dictionary representation.

    Parameters
    ----------
    obj : dict
        Dictionary containing entity data. Must include 'kind' key.

    Returns
    -------
    Entity
        The constructed entity instance.

    Raises
    ------
    BuilderError
        If 'kind' key is missing or builder not found.
    """
    try:
        kind = obj["kind"]
    except KeyError:
        raise BuilderError("Missing 'kind' parameter.")
    _raise_if_entity_builder_not_found(kind)
    return factory.build_entity_from_dict(kind, obj)


def build_spec(kind_to_build_from: str, **kwargs) -> Spec:
    """
    Build an entity spec.

    Parameters
    ----------
    kind_to_build_from : str
        Entity type.

    Returns
    -------
    Spec
        Spec object.
    """
    _raise_if_entity_builder_not_found(kind_to_build_from)
    return factory.build_spec(kind_to_build_from, **kwargs)


def build_metadata(kind_to_build_from: str, **kwargs) -> Metadata:
    """
    Build an entity metadata.

    Parameters
    ----------
    kind_to_build_from : str
        Entity type.

    Returns
    -------
    Metadata
        Metadata object.
    """
    _raise_if_entity_builder_not_found(kind_to_build_from)
    return factory.build_metadata(kind_to_build_from, **kwargs)


def build_status(kind_to_build_from: str, **kwargs) -> Status:
    """
    Build an entity status.

    Parameters
    ----------
    kind_to_build_from : str
        Entity type.

    Returns
    -------
    Status
        Status object.
    """
    _raise_if_entity_builder_not_found(kind_to_build_from)
    return factory.build_status(kind_to_build_from, **kwargs)


def build_runtime(kind_to_build_from: str, project: str) -> Runtime:
    """
    Build a runtime.

    Parameters
    ----------
    kind_to_build_from : str
        Runtime type.
    project : str
        Project name.

    Returns
    -------
    Runtime
        Runtime object.
    """
    _raise_if_runtime_builder_not_found(kind_to_build_from)
    return factory.build_runtime(kind_to_build_from, project)


def get_entity_type_from_kind(kind: str) -> str:
    """
    Get entity type from builder.

    Parameters
    ----------
    kind : str
        Entity type.

    Returns
    -------
    str
        Entity type.
    """
    _raise_if_entity_builder_not_found(kind)
    return factory.get_entity_type_from_kind(kind)


def get_all_kinds(kind: str) -> list[str]:
    """
    Get all kinds.

    Parameters
    ----------
    kind : str
        Kind.

    Returns
    -------
    list[str]
        All entities runtime kinds.
    """
    _raise_if_entity_builder_not_found(kind)
    return factory.get_all_kinds(kind)


def get_executable_kind(kind: str) -> str:
    """
    Get executable kind.

    Parameters
    ----------
    kind : str
        Kind.

    Returns
    -------
    str
        Executable kind.
    """
    _raise_if_entity_builder_not_found(kind)
    return factory.get_executable_kind(kind)


def get_task_kind_from_action(kind: str, action: str) -> str:
    """
    Get task kinds from action.

    Parameters
    ----------
    kind : str
        Kind.
    action : str
        Action.

    Returns
    -------
    str
        Task kind.
    """
    _raise_if_entity_builder_not_found(kind)
    return factory.get_task_kind_from_action(kind, action)


def get_action_from_task_kind(kind: str, task_kind: str) -> str:
    """
    Get action from task.

    Parameters
    ----------
    kind : str
        Kind.
    task_kind : str
        Task kind.

    Returns
    -------
    str
        Action.
    """
    _raise_if_entity_builder_not_found(kind)
    return factory.get_action_from_task_kind(kind, task_kind)


def get_run_kind(kind: str) -> str:
    """
    Get run kind.

    Parameters
    ----------
    kind : str
        Kind.

    Returns
    -------
    str
        Run kind.
    """
    _raise_if_entity_builder_not_found(kind)
    return factory.get_run_kind(kind)


def _raise_if_entity_builder_not_found(kind: str) -> None:
    """
    Verify entity builder existence.

    Parameters
    ----------
    kind : str
        The entity kind to verify.

    Raises
    ------
    BuilderError
        If no builder exists for the specified kind.
    """
    if kind not in factory._entity_builders:
        raise BuilderError(f"Builder for kind '{kind}' not found.")


def _raise_if_runtime_builder_not_found(kind: str) -> None:
    """
    Verify runtime builder existence.

    Parameters
    ----------
    kind : str
        The runtime kind to verify.

    Raises
    ------
    BuilderError
        If no builder exists for the specified kind.
    """
    if kind not in factory._runtime_builders:
        raise BuilderError(f"Builder for kind '{kind}' not found.")
