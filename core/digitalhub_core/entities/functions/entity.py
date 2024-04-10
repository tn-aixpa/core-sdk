"""
Function module.
"""
from __future__ import annotations

import typing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from digitalhub_core.context.builder import get_context
from digitalhub_core.entities._base.entity import Entity
from digitalhub_core.entities._builders.metadata import build_metadata
from digitalhub_core.entities._builders.spec import build_spec
from digitalhub_core.entities._builders.status import build_status
from digitalhub_core.entities.tasks.crud import create_task, create_task_from_dict, delete_task, new_task
from digitalhub_core.utils.api import api_ctx_create, api_ctx_list, api_ctx_update
from digitalhub_core.utils.exceptions import BackendError, EntityError
from digitalhub_core.utils.generic_utils import build_uuid, get_timestamp
from digitalhub_core.utils.io_utils import write_yaml

if typing.TYPE_CHECKING:
    from digitalhub_core.context.context import Context
    from digitalhub_core.entities.functions.metadata import FunctionMetadata
    from digitalhub_core.entities.functions.spec import FunctionSpec
    from digitalhub_core.entities.functions.status import FunctionStatus
    from digitalhub_core.entities.runs.entity import Run
    from digitalhub_core.entities.tasks.entity import Task


class Function(Entity):
    """
    A class representing a function.
    """

    def __init__(
        self,
        project: str,
        name: str,
        uuid: str,
        kind: str,
        metadata: FunctionMetadata,
        spec: FunctionSpec,
        status: FunctionStatus,
    ) -> None:
        """
        Constructor.

        Parameters
        ----------
        project : str
            Project name.
        name : str
            Name of the object.
        uuid : str
            Version of the object.
        kind : str
            Kind of the object.
        metadata : FunctionMetadata
            Metadata of the object.
        spec : FunctionSpec
            Specification of the object.
        status : FunctionStatus
            Status of the object.
        """
        super().__init__()
        self.project = project
        self.name = name
        self.id = uuid
        self.kind = kind
        self.key = f"store://{project}/functions/{kind}/{name}:{uuid}"
        self.metadata = metadata
        self.spec = spec
        self.status = status

        # Add attributes to be used in the to_dict method
        self._obj_attr.extend(["project", "name", "id", "key"])

        # Initialize tasks
        self._tasks: dict[str, Task] = {}

    #############################
    #  Save / Export
    #############################

    def save(self, update: bool = False) -> Function:
        """
        Save entity into backend.

        Parameters
        ----------
        uuid : str
            Specify uuid for the function update

        Returns
        -------
        Function
            Entity saved.
        """
        obj = self.to_dict(include_all_non_private=True)

        if not update:
            api = api_ctx_create(self.project, "functions")
            new_obj = self._context().create_object(api, obj)
            self._update_attributes(new_obj)
            return self

        self.metadata.updated = obj["metadata"]["updated"] = get_timestamp()
        api = api_ctx_update(self.project, "functions", self.id)
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
            filename = f"function_{self.kind}_{self.name}_{self.id}.yml"
        pth = Path(self._context().project_dir) / filename
        pth.parent.mkdir(parents=True, exist_ok=True)

        # Embed tasks in file
        if self._tasks:
            obj = [obj] + [v.to_dict() for _, v in self._tasks.items()]

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
    #  Function Methods
    #############################

    def run(
        self,
        action: str,
        node_selector: list[dict] | None = None,
        volumes: list[dict] | None = None,
        resources: list[dict] | None = None,
        affinity: dict | None = None,
        tolerations: list[dict] | None = None,
        labels: list[dict] | None = None,
        env: list[dict] | None = None,
        secrets: list[str] | None = None,
        backoff_limit: int | None = None,
        schedule: str | None = None,
        replicas: int | None = None,
        inputs: dict | None = None,
        outputs: dict | None = None,
        parameters: dict | None = None,
        values: list | None = None,
        local_execution: bool = False,
        **kwargs,
    ) -> Run:
        """
        Run function.

        Parameters
        ----------
        action : str
            Action to execute. Task parameter.
        node_selector : list[dict]
            The node selector of the task. Task parameter.
        volumes : list[dict]
            The volumes of the task. Task parameter.
        resources : list[dict]
            Kubernetes resources for the task. Task parameter.
        affinity : Affinity
            Kubernetes affinity parameters. Task parameter.
        tolerations : list[dict]
            Kubernetes tolerations parameters. Task parameter.
        labels : list[dict]
            The labels of the task.
        env : list[dict]
            The env variables of the task. Task parameter.
        secrets : list[str]
            The secrets of the task. Task parameter.
        backoff_limit : int
            The backoff limit of the task. Task parameter.
        schedule : str
            The schedule of the task. Task parameter.
        replicas : int
            The replicas of the task. Task parameter.
        inputs : dict
            Function inputs. Run parameter.
        outputs : dict
            Function outputs. Run parameter.
        parameters : dict
            Function parameters. Run parameter.
        values : list
            Function values. Run parameter.
        local_execution : bool
            Flag to determine if object has local execution. Run parameter.
        **kwargs
            Keyword arguments passed to Task builder.

        Returns
        -------
        Run
            Run instance.
        """

        # Create task if does not exists
        task = self._tasks.get(action)

        # Check in backend
        if task is None and not self._context().local:
            task = self._check_task_in_backend(action)

        # Create new task
        if task is None:
            task = self.new_task(
                kind=f"{self.kind}+{action}",
                node_selector=node_selector,
                volumes=volumes,
                resources=resources,
                affinity=affinity,
                tolerations=tolerations,
                labels=labels,
                env=env,
                secrets=secrets,
                backoff_limit=backoff_limit,
                schedule=schedule,
                replicas=replicas,
                **kwargs,
            )

        # Run function from task
        run = task.run(inputs, outputs, parameters, values, local_execution)

        # If execution is done by DHCore backend, return the object
        if not local_execution:
            if self._context().local:
                raise BackendError("Cannot run remote function with local backend.")
            return run

        # If local execution, build and launch run
        run.build()
        with ThreadPoolExecutor(max_workers=1) as executor:
            result = executor.submit(run.run)
        return result.result()

    def _check_task_in_backend(self, action: str) -> None | Task:
        """
        Check if task exists in backend.

        Parameters
        ----------
        action : str
            Action to check.

        Returns
        -------
        None | Task
            Task if exists, None otherwise.
        """
        api = api_ctx_list(self.project, "tasks")
        params = {"function": self._get_function_string(), "kind": f"{self.kind}+{action}"}
        objs = self._context().list_objects(api, params=params)
        for i in objs:
            self._tasks[action] = create_task_from_dict(i)
            return self._tasks[action]

    def _get_function_string(self) -> str:
        """
        Get function string.

        Returns
        -------
        str
            Function string.
        """
        return f"{self.kind}://{self.project}/{self.name}:{self.id}"

    #############################
    #  CRUD Methods for Tasks
    #############################

    def import_tasks(self, tasks: list[dict]) -> None:
        """
        Import tasks from yaml.

        Parameters
        ----------
        tasks : list[dict]
            List of tasks to import.

        Returns
        -------
        None
        """
        # Loop over tasks list, in the case where the function
        # is imported from local file.
        for task in tasks:
            # If task is not a dictionary, skip it
            if not isinstance(task, dict):
                continue

            # Create the object instance from dictionary,
            # the form in which tasks are stored in function
            # status
            task_obj = create_task_from_dict(task)

            # Try to save it in backend to been able to use
            # it for launching runs. In fact, tasks must be
            # persisted in backend to be able to launch runs.
            # Ignore if task already exists
            try:
                task_obj.save()
            except BackendError:
                pass

            # Set task if function is the same. Overwrite
            # status task dict with the new task object
            if task_obj.spec.function == self._get_function_string():
                self._tasks[task_obj.kind] = task_obj

    def new_task(self, **kwargs) -> Task:
        """
        Create new task.

        Parameters
        ----------
        **kwargs
            Keyword arguments.

        Returns
        -------
        Task
            New task.
        """
        kwargs["project"] = self.project
        kwargs["function"] = self._get_function_string()
        kwargs["kind"] = kwargs["kind"]
        task = new_task(**kwargs)
        self._tasks[kwargs["kind"]] = task
        return task

    def update_task(self, kind: str, **kwargs) -> None:
        """
        Update task.

        Parameters
        ----------
        kind : str
            Kind of the task.
        **kwargs
            Keyword arguments.

        Returns
        -------
        None

        Raises
        ------
        EntityError
            If task does not exist.
        """
        self._raise_if_not_exists(kind)

        # Update kwargs
        kwargs["project"] = self.project
        kwargs["kind"] = kind
        kwargs["function"] = self._get_function_string()
        kwargs["uuid"] = self._tasks[kind].id

        # Update task
        task = create_task(**kwargs)
        task.save(update=True)
        self._tasks[kind] = task

    def get_task(self, kind: str) -> Task:
        """
        Get task.

        Parameters
        ----------
        kind : str
            Kind of the task.

        Returns
        -------
        Task
            Task.

        Raises
        ------
        EntityError
            If task is not created.
        """
        self._raise_if_not_exists(kind)
        return self._tasks[kind]

    def delete_task(self, kind: str, cascade: bool = True) -> None:
        """
        Delete task.

        Parameters
        ----------
        kind : str
            Kind of the task.
        cascade : bool
            Flag to determine if cascade deletion must be performed.

        Returns
        -------
        None

        Raises
        ------
        EntityError
            If task is not created.
        """
        self._raise_if_not_exists(kind)
        delete_task(self.project, self._tasks[kind].name, cascade=cascade)
        self._tasks.pop(kind, None)

    def _raise_if_not_exists(self, kind: str) -> None:
        """
        Raise error if task is not created.

        Parameters
        ----------
        kind : str
            Kind of the task.

        Returns
        -------
        None

        Raises
        ------
        EntityError
            If task does not exist.
        """
        if self._tasks.get(kind) is None:
            raise EntityError("Task does not exist.")

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
        obj : dict
            Dictionary to parse.
        validate : bool
            Flag to determine if validation must be performed.

        Returns
        -------
        dict
            A dictionary containing the attributes of the entity instance.
        """
        project = obj.get("project")
        name = obj.get("name")
        kind = obj.get("kind")
        uuid = build_uuid(obj.get("id"))
        metadata = build_metadata(kind, framework_runtime=kind, **obj.get("metadata", {}))
        spec = build_spec(kind, framework_runtime=kind, validate=validate, **obj.get("spec", {}))
        status = build_status(kind, framework_runtime=kind, **obj.get("status", {}))
        return {
            "project": project,
            "name": name,
            "uuid": uuid,
            "kind": kind,
            "metadata": metadata,
            "spec": spec,
            "status": status,
        }


def function_from_parameters(
    project: str,
    name: str,
    kind: str,
    uuid: str | None = None,
    description: str | None = None,
    git_source: str | None = None,
    labels: list[str] | None = None,
    embedded: bool = True,
    **kwargs,
) -> Function:
    """
    Create a new Function instance and persist it to the backend.

    Parameters
    ----------
    project : str
        Project name.
    name : str
        Name that identifies the object.
    kind : str
        Kind of the object.
    uuid : str
        ID of the object in form of UUID.
    description : str
        Description of the object.
    git_source : str
        Remote git source for object.
    labels : list[str]
        List of labels.
    embedded : bool
        Flag to determine if object must be embedded in project.
    **kwargs
        Spec keyword arguments.

    Returns
    -------
    Function
       Object instance.
    """
    uuid = build_uuid(uuid)
    spec = build_spec(
        kind,
        framework_runtime=kind,
        **kwargs,
    )
    metadata = build_metadata(
        kind,
        framework_runtime=kind,
        project=project,
        name=name,
        version=uuid,
        description=description,
        source=git_source,
        labels=labels,
        embedded=embedded,
    )
    status = build_status(
        kind,
        framework_runtime=kind,
    )
    return Function(
        project=project,
        name=name,
        uuid=uuid,
        kind=kind,
        metadata=metadata,
        spec=spec,
        status=status,
    )


def function_from_dict(obj: dict) -> Function:
    """
    Create function from dictionary.

    Parameters
    ----------
    obj : dict
        Dictionary to create object from.

    Returns
    -------
    Function
        Function object.
    """
    return Function.from_dict(obj, validate=False)
