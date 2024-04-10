"""
Run module.
"""
from __future__ import annotations

import typing
from collections import namedtuple
from pathlib import Path

from digitalhub_core.context.builder import get_context
from digitalhub_core.entities._base.entity import Entity
from digitalhub_core.entities._base.status import State
from digitalhub_core.entities._builders.metadata import build_metadata
from digitalhub_core.entities._builders.spec import build_spec
from digitalhub_core.entities._builders.status import build_status
from digitalhub_core.runtimes.builder import build_runtime
from digitalhub_core.utils.api import api_base_list, api_ctx_create, api_ctx_list, api_ctx_read, api_ctx_update
from digitalhub_core.utils.exceptions import EntityError
from digitalhub_core.utils.generic_utils import build_uuid, get_timestamp
from digitalhub_core.utils.io_utils import write_yaml

if typing.TYPE_CHECKING:
    from digitalhub_core.context.context import Context
    from digitalhub_core.entities.runs.metadata import RunMetadata
    from digitalhub_core.entities.runs.spec import RunSpec
    from digitalhub_core.entities.runs.status import RunStatus
    from digitalhub_core.runtimes.base import Runtime


TaskString = namedtuple(
    "TaskString",
    ["function_kind", "task_kind", "function_name", "function_id"],
)


class Run(Entity):
    """
    A class representing a run.
    """

    def __init__(
        self,
        project: str,
        uuid: str,
        kind: str,
        metadata: RunMetadata,
        spec: RunSpec,
        status: RunStatus,
    ) -> None:
        """
        Constructor.

        Parameters
        ----------
        project : str
            Project name.
        uuid : str
            UUID.
        kind : str
            Kind of the object.
        metadata : RunMetadata
            Metadata of the object.
        spec : RunSpec
            Specification of the object.
        status : RunStatus
            Status of the object.
        """
        super().__init__()
        self.project = project
        self.id = uuid
        self.kind = kind
        self.key = f"store://{project}/runs/{kind}/{uuid}"
        self.metadata = metadata
        self.spec = spec
        self.status = status

        # Add attributes to be used in the to_dict method
        self._obj_attr.extend(["project", "id", "key"])

    #############################
    #  Save / Export
    #############################

    def save(self, update: bool = False) -> Run:
        """
        Save entity into backend.

        Parameters
        ----------
        update : bool
            If True, the object will be updated.

        Returns
        -------
        Run
            Entity saved.
        """
        obj = self.to_dict(include_all_non_private=True)

        if not update:
            api = api_ctx_create(self.project, "runs")
            new_obj = self._context().create_object(api, obj)
            self._update_attributes(new_obj)
            return self

        self.metadata.updated = obj["metadata"]["updated"] = get_timestamp()
        api = api_ctx_update(self.project, "runs", self.id)
        new_obj = self._context().update_object(api, obj)
        self._update_attributes(new_obj)
        return self

    def export(self, filename: str | None = None) -> None:
        """
        Export object as a YAML file.

        Parameters
        ----------
        filename : str
            Name of the export YAML file. If not specified, the default value is used.

        Returns
        -------
        None
        """
        obj = self.to_dict()
        if filename is None:
            filename = f"{self.kind}_{self.name}_{self.id}.yml"
        pth = Path(self._context().project_dir) / filename
        pth.parent.mkdir(parents=True, exist_ok=True)
        write_yaml(pth, obj)

    #############################
    #  Context
    #############################

    def _context(self) -> Context:
        """
        Get context.

        Returns
        -------
        Context
            Context.
        """
        return get_context(self.project)

    #############################
    #  Run Methods
    #############################

    def build(self) -> None:
        """
        Build run.

        Returns
        -------
        None
        """
        function = self._get_function()
        task = self._get_task()
        runtime = self._get_runtime()
        new_spec = runtime.build(function, task, self.to_dict())
        self.spec = build_spec(
            self.kind,
            framework_runtime=self.kind.split("+")[0],
            **new_spec,
        )
        self._set_status({"state": State.BUILT.value})
        self.save()

    def run(self) -> Run:
        """
        Run run.

        Returns
        -------
        Run
            Run object.
        """
        if self.spec.local_execution:
            if not self.status.state == State.BUILT.value:
                raise EntityError("Run is not in built state. Build it again.")

        runtime = self._get_runtime()
        try:
            self._set_status({"state": State.RUNNING.value})
            self.spec.inputs = self.inputs(as_dict=True)
            self.save(update=True)
            status = runtime.run(self.to_dict(include_all_non_private=True))
        except Exception as err:
            status = {"state": State.ERROR.value, "message": str(err)}

        # need to consider eventual run execution side effects, and update status only
        self.refresh()
        self._set_status(status)
        self.save(update=True)
        return self

    def inputs(self, as_dict: bool = False) -> list[dict[str, Entity]]:
        """
        Get inputs passed in spec as objects or as dictionaries.

        Parameters
        ----------
        as_dict : bool
            If True, return inputs as dictionaries.

        Returns
        -------
        list
            List of input objects.
        """
        return self.spec.get_inputs(as_dict=as_dict)

    def results(self) -> dict:
        """
        Get results from runtime execution.

        Returns
        -------
        dict
            Results from backend.
        """
        return self.status.get_results()

    def outputs(self, as_key: bool = False, as_dict: bool = False) -> list:
        """
        Get run objects results.

        Parameters
        ----------
        as_key : bool
            If True, return results as keys.
        as_dict : bool
            If True, return results as dictionaries.

        Returns
        -------
        list
            List of output objects.
        """
        return self.status.get_outputs(as_key=as_key, as_dict=as_dict)

    def values(self) -> list:
        """
        Get values from runtime execution.

        Returns
        -------
        list
            Values from backend.
        """
        value_list = getattr(self.spec, "values", [])
        value_list = value_list if value_list is not None else []
        return self.status.get_values(value_list)

    def refresh(self) -> Run:
        """
        Get object from backend.

        Returns
        -------
        Run
            Run object.
        """
        api = api_ctx_read(self.project, "runs", self.id)
        obj = self._context().read_object(api)
        self._update_attributes(obj)
        return self

    def logs(self) -> dict:
        """
        Get object from backend.
        Returns empty dictionary if context is local.

        Returns
        -------
        dict
            Logs from backend.
        """
        if self._context().local:
            return {}
        api = api_ctx_read(self.project, "runs", self.id) + "/log"
        return self._context().read_object(api)

    def stop(self) -> None:
        """
        Stop run.

        Returns
        -------
        None
        """
        # Do nothing if context is local
        if self._context().local:
            return
        api = api_ctx_create(self.project, "runs") + f"/{self.id}/stop"
        self._context().create_object(api)
        self.status.state = State.STOPPED.value

    def _set_status(self, status: dict) -> None:
        """
        Set run status.

        Parameters
        ----------
        status : dict
            Status to set.

        Returns
        -------
        None

        Raises
        ------
        EntityError
            If status is not a dictionary or a Status object.
        """
        if not isinstance(status, dict):
            raise EntityError("Status must be a dictionary.")
        self.status: RunStatus = build_status(self.kind, framework_runtime=self.kind.split("+")[0], **status)

    #############################
    #  Functions and Tasks
    #############################

    def _parse_task_string(self) -> TaskString:
        """
        Parse task string.

        Returns
        -------
        None
        """
        kinds, func = self.spec.task.split("://")
        fnc_kind, tsk_kind = kinds.split("+")
        fnc_name, fnc_id = func.split("/")[1].split(":")
        return TaskString(fnc_kind, tsk_kind, fnc_name, fnc_id)

    def _get_function(self) -> dict:
        """
        Get object from backend. Reimplemented to avoid circular imports.

        Returns
        -------
        dict
            Function from backend.
        """
        parsed = self._parse_task_string()
        api = api_ctx_read(self.project, "functions", parsed.function_id)
        return self._context().read_object(api)

    def _get_task(self) -> dict:
        """
        Get object from backend. Reimplemented to avoid circular imports.

        Returns
        -------
        dict
            Task from backend.
        """
        parsed = self._parse_task_string()
        function_string = f"{parsed.function_kind}://{self.project}/{parsed.function_name}:{parsed.function_id}"

        # Local backend
        if self._context().local:
            api = api_base_list("tasks")
            tasks = self._context().list_objects(api)
            for i in tasks:
                if i.get("spec").get("function") == function_string:
                    return i
            raise EntityError("Task not found.")

        # Remote backend
        api = api_ctx_list(self.project, "tasks")
        params = {"function": function_string, "kind": f"{parsed.function_kind}+{parsed.task_kind}"}
        obj = self._context().list_objects(api, params=params)
        return obj[0]

    #############################
    # Runtimes
    #############################

    def _get_runtime(self) -> Runtime:
        """
        Build runtime to build run or execute it.

        Returns
        -------
        Runtime
            Runtime object.
        """
        fnc_kind = self._parse_task_string().function_kind
        return build_runtime(fnc_kind)

    #############################
    #  Static interface methods
    #############################

    @staticmethod
    def _parse_dict(
        obj: dict,
        validate: bool = True,
    ) -> dict:
        """
        Get dictionary and parse it to a valid entity dictionary.

        Parameters
        ----------
        entity : str
            Entity type.
        obj : dict
            Dictionary to parse.

        Returns
        -------
        dict
            A dictionary containing the attributes of the entity instance.
        """
        project = obj.get("project")
        kind = obj.get("kind")
        uuid = build_uuid(obj.get("id"))
        metadata = build_metadata(kind, framework_runtime=kind.split("+")[0], **obj.get("metadata", {}))
        spec = build_spec(
            kind,
            framework_runtime=kind.split("+")[0],
            validate=validate,
            **obj.get("spec", {}),
        )
        status = build_status(kind, framework_runtime=kind.split("+")[0], **obj.get("status", {}))
        return {
            "project": project,
            "uuid": uuid,
            "kind": kind,
            "metadata": metadata,
            "spec": spec,
            "status": status,
        }


def run_from_parameters(
    project: str,
    task: str,
    kind: str,
    uuid: str | None = None,
    source: str | None = None,
    labels: list[str] | None = None,
    inputs: dict | None = None,
    outputs: list | None = None,
    parameters: dict | None = None,
    values: list | None = None,
    local_execution: bool = False,
    **kwargs,
) -> Run:
    """
    Create run.

    Parameters
    ----------
    project : str
        Project name.
    task : str
        Name of the task associated with the run.
    kind : str
        Kind of the object.
    uuid : str
        ID of the object in form of UUID.
    source : str
        Remote git source for object.
    labels : list[str]
        List of labels.
    inputs : dict
        Inputs of the run.
    outputs : list
        Outputs of the run.
    parameters : dict
        Parameters of the run.
    values : list
        Values of the run.
    local_execution : bool
        Flag to determine if object has local execution.
    embedded : bool
        Flag to determine if object must be embedded in project.
    **kwargs
        Spec keyword arguments.

    Returns
    -------
    Run
        Run object.
    """
    uuid = build_uuid(uuid)
    metadata = build_metadata(
        kind=kind,
        framework_runtime=task.split("+")[0],
        project=project,
        name=uuid,
        source=source,
        labels=labels,
    )
    spec = build_spec(
        kind,
        framework_runtime=task.split("+")[0],
        task=task,
        inputs=inputs,
        outputs=outputs,
        parameters=parameters,
        values=values,
        local_execution=local_execution,
        **kwargs,
    )
    status = build_status(kind, framework_runtime=task.split("+")[0])
    return Run(
        project=project,
        uuid=uuid,
        kind=kind,
        metadata=metadata,
        spec=spec,
        status=status,
    )


def run_from_dict(obj: dict) -> Run:
    """
    Create run from dictionary.

    Parameters
    ----------
    obj : dict
        Dictionary to create object from.

    Returns
    -------
    Run
        Run object.
    """
    return Run.from_dict(obj, validate=False)
