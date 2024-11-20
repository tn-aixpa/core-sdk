from __future__ import annotations

import argparse
import json
import os
import time

import digitalhub as dh
from digitalhub.entities._base.entity.entity import Entity
from digitalhub.entities._commons.enums import State
from digitalhub.utils.logger import LOGGER

# default KFP artifacts and output (ui metadata, metrics etc.)
# directories to /tmp to allow running with security context
KFPMETA_DIR = "/tmp"
KFP_ARTIFACTS_DIR = "/tmp"


def _is_finished(state: str) -> bool:
    """
    Check if state is finished.

    Parameters
    ----------
    state : str
        The state to check.

    Returns
    -------
    bool
        True if the state is finished, False otherwise.
    """
    return state in (State.COMPLETED.value, State.ERROR.value, State.STOPPED.value)


def _is_complete(state: str) -> bool:
    """
    Check if state is complete.

    Parameters
    ----------
    state : str
        The state to check.

    Returns
    -------
    bool
        True if the state is complete, False otherwise.
    """
    return state == State.COMPLETED.value


def execute_step(
    project: str,
    function: str | None = None,
    function_id: str | None = None,
    workflow: str | None = None,
    workflow_id: str | None = None,
    action: str | None = None,
    jsonprops: str | None = None,
    inputs: dict | None = None,
    outputs: dict | None = None,
    parameters: dict | None = None,
    values: list | None = None,
    args: dict | None = None,
) -> None:
    """
    Execute a step.

    Parameters
    ----------
    project : str
        The project name.
    function : str
        The function name.
    function_id : str
        The function id.
    workflow : str
        The workflow name.
    workflow_id : str
        The workflow id.
    action : str
        The action name.
    jsonprops : str
        The json properties.
    inputs : dict
        The inputs.
    outputs : dict
        The outputs.
    parameters : dict
        The parameters.
    values : list
        The values.
    args : dict
        The args.

    Returns
    -------
    None
    """

    LOGGER.info("Loading project " + project)
    project = dh.get_project(project)

    if jsonprops is not None:
        props = json.loads(jsonprops)
        props = {k: v for k, v in props.items() if v}
    else:
        props = {}

    if args is None:
        args = {}

    if function is not None:
        LOGGER.info("Executing function " + function + " task " + action)
        function = (
            project.get_function(function, entity_id=function_id)
            if function_id is not None
            else project.get_function(function)
        )

        run = function.run(
            action,
            node_selector=props.get("node_selector", []),
            volumes=props.get("volumes", []),
            resources=props.get("resources", {}),
            envs=props.get("envs", []),
            secrets=props.get("secrets", []),
            inputs=inputs,
            outputs=outputs,
            parameters=parameters,
            values=values,
            **args,
        )
    elif workflow is not None:
        if action is None:
            action = "pipeline"

        LOGGER.info("Executing workflow " + workflow + " task " + action)
        function = (
            project.get_workflow(workflow, entity_id=workflow_id)
            if workflow_id is not None
            else project.get_workflow(workflow)
        )

        run = workflow.run(
            action,
            node_selector=props.get("node_selector", []),
            volumes=props.get("volumes", []),
            resources=props.get("resources", {}),
            envs=props.get("envs", []),
            secrets=props.get("secrets", []),
            inputs=inputs,
            outputs=outputs,
            parameters=parameters,
            values=values,
            **args,
        )
    else:
        LOGGER.info("Step failed: no workflow of function defined ")
        exit(1)

    # Wait for the run to complete
    while not _is_finished(run.status.state):
        time.sleep(5)
        run = run.refresh()
        LOGGER.info("Step state: " + run.status.state)

    # write run_id
    try:
        _write_output("run_id", run.id)
    except Exception as e:
        LOGGER.warning(f"Failed writing run_id to temp file. Ignoring ({repr(e)})")
        pass

    # If the run is complete process outputs
    if _is_complete(run.status.state):
        LOGGER.info("Step completed: " + run.status.state)

        results = {}

        # process entities
        for prop, val in run.outputs().items():
            # write to file val
            target_output = f"entity_{prop}"
            results[target_output] = val if isinstance(val, str) else val.key if isinstance(val, Entity) else val["key"]
        # process values
        if values is not None:
            if hasattr(run, "values"):
                for prop, val in run.values(values_list=values).items():
                    # write to file val
                    target_output = f"value_{prop}"
                    results[target_output] = str(val)
            else:
                LOGGER.warning("Run does not have values method, cannot process values")

        for key, value in results.items():
            try:
                _write_output(key, value)
            except Exception as e:
                LOGGER.warning(f"Failed writing to temp file. Ignoring ({repr(e)})")
                pass

        LOGGER.info("Done.")
    else:
        LOGGER.info("Step failed: " + run.status.state)
        exit(1)


def _write_output(key: str, value: str) -> None:
    # NOTE: if key has "../x", it would fail on path traversal
    path = os.path.join(KFP_ARTIFACTS_DIR, key)
    if not _is_safe_path(KFP_ARTIFACTS_DIR, path):
        LOGGER.warning(f"Path traversal is not allowed ignoring, {path} / {key}")
        return
    path = os.path.abspath(path)
    LOGGER.info(f"Writing artifact output, {path}, {value}")
    with open(path, "w") as fp:
        fp.write(value)
    # check file
    file_stats = os.stat(path)
    LOGGER.debug(f"Checking file {path}: {file_stats.st_size}")


def _is_safe_path(base, filepath, is_symlink=False) -> bool:
    # Avoid path traversal attacks by ensuring that the path is safe
    resolved_filepath = os.path.abspath(filepath) if not is_symlink else os.path.realpath(filepath)
    return base == os.path.commonpath((base, resolved_filepath))


def parser():
    parser = argparse.ArgumentParser(description="Step executor")

    parser.add_argument("--project", type=str, help="Project reference", required=True)
    parser.add_argument("--function", type=str, help="Function name", required=False, default=None)
    parser.add_argument("--function_id", type=str, help="Function ID", required=False, default=None)
    parser.add_argument("--workflow", type=str, help="Workflow name", required=False, default=None)
    parser.add_argument("--workflow_id", type=str, help="Workflow ID", required=False, default=None)
    parser.add_argument("--action", type=str, help="Action type", required=False, default=None)
    parser.add_argument(
        "--jsonprops",
        type=str,
        help="Function execution properties in JSON format",
        required=False,
    )
    parser.add_argument("--parameters", type=str, help="Function parameters", required=False)
    parser.add_argument("-a", type=str, action="append", help="Function args", required=False)
    parser.add_argument("-ie", action="append", type=str, help="Input entity property", required=False)
    parser.add_argument("-iv", action="append", type=str, help="Input value property", required=False)
    parser.add_argument("-oe", action="append", type=str, help="Output entity property", required=False)
    parser.add_argument("-ov", action="append", type=str, help="Output value property", required=False)
    return parser


def main(args):
    """
    Main function. Get run from backend and execute function.
    """

    inputs = {}
    if args.ie is not None:
        for ie in args.ie:
            ie_param = ie[0 : ie.find("=")]
            ie_value = ie[ie.find("=") + 1 :]
            inputs[ie_param] = ie_value

    parameters = {}
    if args.iv is not None:
        for iv in args.iv:
            iv_param = iv[0 : iv.find("=")]
            iv_value = iv[iv.find("=") + 1 :]
            parameters[iv_param] = iv_value

    outputs = {}
    if args.oe is not None:
        for oe in args.oe:
            oe_param = oe[0 : oe.find("=")]
            oe_value = oe[oe.find("=") + 1 :]
            outputs[oe_param] = oe_value

    values = []
    if args.ov is not None:
        for ov in args.ov:
            values.append(ov)

    step_args = {}
    if args.a is not None:
        for a in args.a:
            p = a.split("=")
            step_args[p[0]] = p[1]

    execute_step(
        args.project,
        args.function,
        args.function_id,
        args.workflow,
        args.workflow_id,
        args.action,
        args.jsonprops,
        inputs,
        outputs,
        parameters,
        values,
        step_args,
    )


if __name__ == "__main__":
    # Defining and parsing the command-line arguments
    args = parser().parse_args()

    main(args)
