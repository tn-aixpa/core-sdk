"""
Task module.
"""
from __future__ import annotations

import typing
from pathlib import Path

from digitalhub_core.context.builder import get_context
from digitalhub_core.entities._base.entity import Entity
from digitalhub_core.entities._builders.metadata import build_metadata
from digitalhub_core.entities._builders.spec import build_spec
from digitalhub_core.entities._builders.status import build_status
from digitalhub_core.entities.runs.crud import delete_run, get_run, new_run, run_from_parameters
from digitalhub_core.utils.api import api_ctx_create, api_ctx_update
from digitalhub_core.utils.generic_utils import build_uuid, get_timestamp
from digitalhub_core.utils.io_utils import write_yaml

if typing.TYPE_CHECKING:
    from digitalhub_core.context.context import Context
    from digitalhub_core.entities.runs.entity import Run
    from digitalhub_core.entities.tasks.metadata import TaskMetadata
    from digitalhub_core.entities.tasks.spec import TaskSpec
    from digitalhub_core.entities.tasks.status import TaskStatus


class Task(Entity):
    """
    A class representing a task.
    """

    def __init__(
        self,
        project: str,
        uuid: str,
        kind: str,
        metadata: TaskMetadata,
        spec: TaskSpec,
        status: TaskStatus,
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
        metadata : TaskMetadata
            Metadata of the object.
        spec : TaskSpec
            Specification of the object.
        status : TaskStatus
            Status of the object.
        """
        super().__init__()
        self.project = project
        self.id = uuid
        self.kind = kind
        self.key = f"store://{project}/tasks/{kind}/{uuid}"
        self.metadata = metadata
        self.spec = spec
        self.status = status

        # Add attributes to be used in the to_dict method
        self._obj_attr.extend(["project", "id", "key"])

    #############################
    #  Save / Export
    #############################

    def save(self, update: bool = False) -> Task:
        """
        Save entity into backend.

        Parameters
        ----------
        update : bool
            Flag to indicate update.

        Returns
        -------
        Task
            Entity saved.
        """
        obj = self.to_dict()

        if not update:
            api = api_ctx_create(self.project, "tasks")
            new_obj = self._context().create_object(api, obj)
            self._update_attributes(new_obj)
            return self

        self.metadata.updated = obj["metadata"]["updated"] = get_timestamp()
        api = api_ctx_update(self.project, "tasks", self.id)
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
    #  Task methods
    #############################

    def run(
        self,
        inputs: list | None,
        outputs: list | None = None,
        parameters: dict | None = None,
        values: list | None = None,
        local_execution: bool = False,
    ) -> Run:
        """
        Run task.

        Parameters
        ----------
        inputs : list
            The inputs of the run.
        outputs : list
            The outputs of the run.
        parameters : dict
            The parameters of the run.
        values : list
            The values of the run.
        local_execution : bool
            Flag to indicate if the run will be executed locally.

        Returns
        -------
        Run
            Run object.
        """
        return self.new_run(
            project=self.project,
            task=self._get_task_string(),
            kind=f"{self.kind.split('+')[0]}+run",
            inputs=inputs,
            outputs=outputs,
            parameters=parameters,
            values=values,
            local_execution=local_execution,
        )

    def _get_task_string(self) -> str:
        """
        Get task string.

        Returns
        -------
        str
            Task string.
        """
        splitted = self.spec.function.split("://")
        return f"{self.kind}://{splitted[1]}"

    #############################
    # CRUD Methods for Run
    #############################

    def new_run(self, **kwargs) -> Run:
        """
        Create a new run.

        Parameters
        ----------
        **kwargs
            Keyword arguments.

        Returns
        -------
        Run
            Run object.
        """
        if kwargs["local_execution"]:
            return run_from_parameters(**kwargs)
        return new_run(**kwargs)

    def get_run(self, entity_id: str) -> Run:
        """
        Get run.

        Parameters
        ----------
        entity_id : str
            Entity ID.

        Returns
        -------
        Run
            Run object.
        """
        return get_run(self.project, entity_id)

    def delete_run(self, entity_id: str) -> None:
        """
        Delete run.

        Parameters
        ----------
        entity_id : str
            Entity ID.

        Returns
        -------
        None
        """
        delete_run(self.project, entity_id)

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
            validate=validate,
            framework_runtime=kind.split("+")[0],
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


def task_from_parameters(
    project: str,
    kind: str,
    uuid: str | None = None,
    source: str | None = None,
    labels: list[str] | None = None,
    function: str | None = "",
    node_selector: list[dict] | None = None,
    volumes: list[dict] | None = None,
    resources: list[dict] | None = None,
    affinity: dict | None = None,
    tolerations: list[dict] | None = None,
    k8s_labels: list[dict] | None = None,
    env: list[dict] | None = None,
    secrets: list[str] | None = None,
    backoff_limit: int | None = None,
    schedule: str | None = None,
    replicas: int | None = None,
    **kwargs,
) -> Task:
    """
    Create a new object instance.

    Parameters
    ----------
    project : str
        Project name.
    kind : str
        Kind of the object.
    uuid : str
        ID of the object in form of UUID.
    source : str
        Remote git source for object.
    labels : list[str]
        List of labels.
    node_selector : list[NodeSelector]
        The node selector of the task.
    volumes : list[Volume]
        The volumes of the task.
    resources : list[Resource]
        Kubernetes resources for the task.
    affinity : Affinity
        The affinity of the task.
    tolerations : list[Toleration]
        The tolerations of the task.
    k8s_labels : list[Label]
        The labels of the task.
    env : list[Env]
        The env variables of the task.
    secrets : list[str]
        The secrets of the task.
    backoff_limit : int
        The backoff limit of the task.
    schedule : str
        The schedule of the task.
    replicas : int
        The replicas of the task.
    **kwargs
        Spec keyword arguments.

    Returns
    -------
    Task
       Object instance.
    """
    uuid = build_uuid(uuid)
    metadata = build_metadata(
        kind=kind,
        framework_runtime=kind.split("+")[0],
        project=project,
        name=uuid,
        source=source,
        labels=labels,
    )

    k8s = {
        "node_selector": node_selector,
        "volumes": volumes,
        "resources": resources,
        "affinity": affinity,
        "tolerations": tolerations,
        "labels": k8s_labels,
        "env": env,
        "secrets": secrets,
        "backoff_limit": backoff_limit,
        "schedule": schedule,
        "replicas": replicas,
    }
    kwargs["k8s"] = k8s
    spec = build_spec(
        kind,
        framework_runtime=function.split("://")[0],
        function=function,
        **kwargs,
    )
    status = build_status(
        kind,
        framework_runtime=function.split("://")[0],
    )
    return Task(
        project=project,
        uuid=uuid,
        kind=kind,
        metadata=metadata,
        spec=spec,
        status=status,
    )


def task_from_dict(obj: dict) -> Task:
    """
    Create Task object from dictionary.

    Parameters
    ----------
    obj : dict
        Dictionary representation of Task.

    Returns
    -------
    Task
        Task object.
    """
    return Task.from_dict(obj, validate=False)
