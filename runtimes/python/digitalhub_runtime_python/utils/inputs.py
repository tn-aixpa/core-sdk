from __future__ import annotations

import inspect
import typing
from typing import Any, Callable

from digitalhub.context.api import get_context
from digitalhub.entities.project.crud import get_project
from digitalhub.factory.api import build_entity_from_dict
from digitalhub.utils.logger import LOGGER

if typing.TYPE_CHECKING:
    from digitalhub.entities._base.entity.entity import Entity
    from digitalhub.entities.project._base.entity import Project


def get_project_(project_name: str) -> Project:
    """
    Get project.

    Parameters
    ----------
    project_name : str
        Project name.

    Returns
    -------
    Project
        Project.
    """
    try:
        ctx = get_context(project_name)
        return get_project(project_name, local=ctx.local)
    except Exception as e:
        msg = f"Error during project collection. Exception: {e.__class__}. Error: {e.args}"
        LOGGER.exception(msg)
        raise RuntimeError(msg)


def get_entity_inputs(inputs: dict) -> dict[str, Entity]:
    """
    Set inputs.

    Parameters
    ----------
    inputs : dict
        Run inputs.
    parameters : dict
        Run parameters.
    tmp_dir : Path
        Temporary directory for storing dataitms and artifacts.

    Returns
    -------
    dict
        Dictionary of inputs.
    """
    try:
        return {k: build_entity_from_dict(v) for k, v in inputs.items()}
    except Exception as e:
        msg = f"Error during inputs collection. Exception: {e.__class__}. Error: {e.args}"
        LOGGER.exception(msg)
        raise RuntimeError(msg) from e


def compose_inputs(
    inputs: dict,
    parameters: dict,
    local_execution: bool,
    func: Callable,
    project: str | Project,
    context: Any | None = None,
    event: Any | None = None,
) -> dict:
    """
    Compose inputs.

    Parameters
    ----------
    inputs : dict
        Run inputs.
    parameters : dict
        Run parameters.
    local_execution : bool
        Local execution.
    func : Callable
        Function to execute.
    project : str
        Project name.
    context : nuclio_sdk.Context
        Nuclio context.
    event : nuclio_sdk.Event
        Nuclio event.

    Returns
    -------
    dict
        Function inputs.
    """
    try:
        entity_inputs = get_entity_inputs(inputs)
        fnc_args = {**parameters, **entity_inputs}

        fnc_parameters = inspect.signature(func).parameters

        _has_project = "project" in fnc_parameters
        _has_context = "context" in fnc_parameters
        _has_event = "event" in fnc_parameters

        # Project is reserved keyword argument
        # both in local and remote executions
        if _has_project:
            if _has_context and not local_execution:
                fnc_args["project"] = context.project
            elif isinstance(project, str):
                fnc_args["project"] = get_project_(project)
            else:
                fnc_args["project"] = project

        # Context and event are reserved keyword arguments
        # only in remote executions
        if not local_execution:
            if _has_context:
                fnc_args["context"] = context
            if _has_event:
                fnc_args["event"] = event

        return fnc_args

    except Exception as e:
        msg = f"Error during function arguments compostion. Exception: {e.__class__}. Error: {e.args}"
        LOGGER.exception(msg)
        raise RuntimeError(msg) from e
