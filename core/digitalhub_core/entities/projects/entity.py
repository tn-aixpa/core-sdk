"""
Project module.
"""
from __future__ import annotations

import typing
from pathlib import Path

from digitalhub_core.client.builder import get_client
from digitalhub_core.context.builder import set_context
from digitalhub_core.entities._base.entity import Entity
from digitalhub_core.entities._builders.metadata import build_metadata
from digitalhub_core.entities._builders.spec import build_spec
from digitalhub_core.entities._builders.status import build_status
from digitalhub_core.entities.artifacts.crud import (
    create_artifact_from_dict,
    delete_artifact,
    get_artifact,
    list_artifacts,
    new_artifact,
)
from digitalhub_core.entities.functions.crud import (
    create_function_from_dict,
    delete_function,
    get_function,
    list_functions,
    new_function,
)
from digitalhub_core.entities.secrets.crud import (
    create_secret_from_dict,
    delete_secret,
    get_secret,
    list_secrets,
    new_secret,
)
from digitalhub_core.entities.workflows.crud import (
    create_workflow_from_dict,
    delete_workflow,
    get_workflow,
    list_workflows,
    new_workflow,
)
from digitalhub_core.utils.api import api_base_create, api_base_read, api_base_update, api_ctx_read
from digitalhub_core.utils.exceptions import BackendError, EntityError
from digitalhub_core.utils.generic_utils import build_uuid, get_timestamp
from digitalhub_core.utils.io_utils import write_yaml

if typing.TYPE_CHECKING:
    from digitalhub_core.entities.artifacts.entity import Artifact
    from digitalhub_core.entities.functions.entity import Function
    from digitalhub_core.entities.projects.metadata import ProjectMetadata
    from digitalhub_core.entities.projects.spec import ProjectSpec
    from digitalhub_core.entities.projects.status import ProjectStatus
    from digitalhub_core.entities.secrets.entity import Secret
    from digitalhub_core.entities.workflows.entity import Workflow


CTX_ENTITIES = ["artifacts", "functions", "workflows", "secrets"]
FUNC_MAP = {
    "artifacts": create_artifact_from_dict,
    "functions": create_function_from_dict,
    "workflows": create_workflow_from_dict,
    "secrets": create_secret_from_dict,
}


class Project(Entity):
    """
    A class representing a project.
    """

    def __init__(
        self,
        name: str,
        kind: str,
        metadata: ProjectMetadata,
        spec: ProjectSpec,
        status: ProjectStatus,
        local: bool = False,
    ) -> None:
        """
        Constructor.

        Parameters
        ----------
        name : str
            Name of the object.
        kind : str
            Kind of the object.
        metadata : ProjectMetadata
            Metadata of the object.
        spec : ProjectSpec
            Specification of the object.
        status : ProjectStatus
            Status of the object.
        local: bool
            If True, export locally.
        """
        super().__init__()
        self.name = name
        self.kind = kind
        self.key = f"store://{name}"
        self.metadata = metadata
        self.spec = spec
        self.status = status

        # Add attributes to be used in the to_dict method
        self._obj_attr.extend(["name", "key"])

        # Set client
        self._client = get_client(local)

        # Set context
        set_context(self)

    #############################
    #  Save / Export
    #############################

    def save(self, update: bool = False) -> Project:
        """
        Save entity into backend.

        Parameters
        ----------
        update : bool
            If True, the object will be updated.

        Returns
        -------
        Project
            Entity saved.
        """
        # Try to refresh project if local client
        if self._client.is_local():
            obj = self._refresh().to_dict()
        else:
            obj = self.to_dict()

        if not update:
            api = api_base_create("projects")
            new_obj = self._client.create_object(api, obj)
            self._update_attributes(new_obj)
            return self

        self.metadata.updated = obj["metadata"]["updated"] = get_timestamp()
        api = api_base_update("projects", self.id)
        new_obj = self._client.update_object(api, obj)
        self._update_attributes(new_obj)
        return self

    def export(self, filename: str | None = None) -> None:
        """
        Export object as a YAML file. If the objects are not embedded, the objects are
        exported as a YAML file.

        Parameters
        ----------
        filename : str
            Name of the export YAML file. If not specified, the default value is used.

        Returns
        -------
        None
        """
        # Try to refresh project if local client
        if self._client.is_local():
            obj = self._refresh().to_dict()
        else:
            obj = self.to_dict()

        if filename is None:
            filename = f"{self.kind}_{self.name}.yml"
        pth = Path(self.spec.context) / filename
        pth.parent.mkdir(parents=True, exist_ok=True)
        write_yaml(pth, obj)

        # Export objects related to project if not embedded
        for entity_type in CTX_ENTITIES:
            for entity in self._get_objects(entity_type):
                api = api_ctx_read(self.name, entity_type, entity["id"])
                obj = self._client.read_object(api)
                ctx_obj = FUNC_MAP[entity_type](obj)
                if not ctx_obj.metadata.embedded:
                    ctx_obj.export()

    def _refresh(self) -> "Project":
        """
        Refresh object from backend.

        Returns
        -------
        Project
            Project object.
        """
        try:
            api = api_base_read("projects", self.name)
            obj = self._client.read_object(api)
            return self.from_dict(obj, validate=False)
        except BackendError:
            return self

    #############################
    #  Generic operations for objects
    #############################

    def _add_object(self, obj: Entity, entity_type: str) -> None:
        """
        Add object to project as specification.

        Parameters
        ----------
        obj : Entity
            Object to be added to project.
        entity_type : str
            Type of object to be added to project.

        Returns
        -------
        None
        """
        self._check_entity_type(entity_type)

        # Pop spec if not embedded
        if obj.metadata.embedded:
            obj_representation = obj.to_dict()
        else:
            obj_representation = obj.to_dict()
            obj_representation.pop("spec")

        # Get list of objects related to project by entity type
        attr = getattr(self.spec, entity_type, [])

        # If empty, append directly
        if not attr:
            attr.append(obj_representation)

        # If not empty, check if object already exists and update if necessary.
        # Only latest version is stored in project spec.
        else:
            for idx, _ in enumerate(attr):
                if attr[idx]["name"] == obj.name:
                    attr[idx] = obj_representation

        # Set attribute
        setattr(self.spec, entity_type, attr)

    def _delete_object(self, entity_type: str, entity_name: str | None = None, entity_id: str | None = None) -> None:
        """
        Delete object from project.

        Parameters
        ----------
        entity_type : str
            Type of object to be deleted.
        entity_name : str
            Entity name.
        entity_id : str
            Entity ID.

        Returns
        -------
        None
        """
        if entity_id is None:
            attr_name = "name"
            var = entity_name
        else:
            attr_name = "id"
            var = entity_id
        self._check_entity_type(entity_type)
        spec_list = getattr(self.spec, entity_type, [])
        setattr(self.spec, entity_type, [i for i in spec_list if i.get(attr_name) != var])

    def _get_objects(self, entity_type: str) -> list[dict]:
        """
        Get entity type related to project.

        Parameters
        ----------
        entity_type : str
            Type of object to be retrieved.

        Returns
        -------
        list[dict]
            List of objects related to project.
        """
        self._check_entity_type(entity_type)
        return getattr(self.spec, entity_type, [])

    @staticmethod
    def _check_entity_type(entity_type: str) -> None:
        """
        Check if kind is valid.

        Parameters
        ----------
        entity_type : str
            Type of object to be checked.

        Returns
        -------
        None

        Raises
        ------
        EntityError
            If type is not valid.
        """
        if entity_type not in CTX_ENTITIES:
            raise EntityError(f"Entity type '{entity_type}' is not valid.")

    #############################
    #  Artifacts
    #############################

    def new_artifact(self, **kwargs) -> Artifact:
        """
        Create an instance of the Artifact class with the provided parameters.

        Parameters
        ----------
        **kwargs
            Keyword arguments.

        Returns
        -------
        Artifact
           Object instance.
        """
        kwargs["project"] = self.name
        kwargs["kind"] = "artifact"
        obj = new_artifact(**kwargs)
        self._add_object(obj, "artifacts")
        return obj

    def get_artifact(self, entity_name: str | None = None, entity_id: str | None = None, **kwargs) -> Artifact:
        """
        Get object from backend.

        Parameters
        ----------
        entity_name : str
            Entity name.
        entity_id : str
            Entity ID.
        **kwargs : dict
            Parameters to pass to the API call.

        Returns
        -------
        Artifact
            Instance of Artifact class.
        """
        obj = get_artifact(self.name, entity_name=entity_name, entity_id=entity_id, **kwargs)
        self._add_object(obj, "artifacts")
        return obj

    def delete_artifact(self, entity_name: str | None = None, entity_id: str | None = None, **kwargs) -> None:
        """
        Delete a Artifact from project.

        Parameters
        ----------
        entity_name : str
            Entity name.
        entity_id : str
            Entity ID.
        **kwargs : dict
            Parameters to pass to the API call.

        Returns
        -------
        None
        """
        delete_artifact(self.name, entity_name=entity_name, entity_id=entity_id, **kwargs)
        self._delete_object("artifacts", entity_name, entity_id)

    def set_artifact(self, artifact: Artifact) -> None:
        """
        Set a Artifact.

        Parameters
        ----------
        artifact : Artifact
            Artifact to set.

        Returns
        -------
        None
        """
        self._add_object(artifact, "artifacts")

    def list_artifacts(self, **kwargs) -> list[dict]:
        """
        List artifacts associated with the project.

        Parameters
        ----------
        **kwargs : dict
            Filters to apply to the list. Shold be params={"filter": "value"}.

        Returns
        -------
        list[dict]
            List of objects related to project.
        """
        return list_artifacts(self.name, **kwargs)

    #############################
    #  Functions
    #############################

    def new_function(self, **kwargs) -> Function:
        """
        Create a Function instance with the given parameters.

        Parameters
        ----------
        **kwargs
            Keyword arguments.

        Returns
        -------
        Function
           Object instance.
        """
        kwargs["project"] = self.name
        obj = new_function(**kwargs)
        self._add_object(obj, "functions")
        return obj

    def get_function(self, entity_name: str | None = None, entity_id: str | None = None, **kwargs) -> Function:
        """
        Get object from backend.

        Parameters
        ----------
        entity_name : str
            Entity name.
        entity_id : str
            Entity ID.
        **kwargs : dict
            Parameters to pass to the API call.

        Returns
        -------
        Function
            Instance of Function class.
        """
        obj = get_function(self.name, entity_name=entity_name, entity_id=entity_id, **kwargs)
        self._add_object(obj, "functions")
        return obj

    def delete_function(self, entity_name: str | None = None, entity_id: str | None = None, **kwargs) -> None:
        """
        Delete a Function from project.

        Parameters
        ----------
        entity_name : str
            Entity name.
        entity_id : str
            Entity ID.
        **kwargs : dict
            Parameters to pass to the API call.

        Returns
        -------
        None
        """
        delete_function(self.name, entity_name=entity_name, entity_id=entity_id, **kwargs)
        self._delete_object("functions", entity_name, entity_id)

    def set_function(self, function: Function) -> None:
        """
        Set a Function.

        Parameters
        ----------
        function : Function
            Function to set.

        Returns
        -------
        None
        """
        self._add_object(function, "functions")

    def list_functions(self, **kwargs) -> list[dict]:
        """
        List functions associated with the project.

        Parameters
        ----------
        **kwargs : dict
            Filters to apply to the list. Shold be params={"filter": "value"}.

        Returns
        -------
        list[dict]
            List of objects related to project.
        """
        return list_functions(self.name, **kwargs)

    #############################
    #  Workflows
    #############################

    def new_workflow(self, **kwargs) -> Workflow:
        """
        Create a new Workflow instance with the specified parameters.

        Parameters
        ----------
        **kwargs
            Keyword arguments.

        Returns
        -------
        Workflow
            An instance of the created workflow.
        """
        kwargs["project"] = self.name
        obj = new_workflow(**kwargs)
        self._add_object(obj, "workflows")
        return obj

    def get_workflow(self, entity_name: str | None = None, entity_id: str | None = None, **kwargs) -> Workflow:
        """
        Get object from backend.

        Parameters
        ----------
        entity_name : str
            Entity name.
        entity_id : str
            Entity ID.
        **kwargs : dict
            Parameters to pass to the API call.

        Returns
        -------
        Workflow
            Instance of Workflow class.
        """
        obj = get_workflow(self.name, entity_name=entity_name, entity_id=entity_id, **kwargs)
        self._add_object(obj, "workflows")
        return obj

    def delete_workflow(self, entity_name: str | None = None, entity_id: str | None = None, **kwargs) -> None:
        """
        Delete a Workflow from project.

        Parameters
        ----------
        entity_name : str
            Entity name.
        entity_id : str
            Entity ID.
        **kwargs : dict
            Parameters to pass to the API call.

        Returns
        -------
        None
        """
        delete_workflow(self.name, entity_name=entity_name, entity_id=entity_id, **kwargs)
        self._delete_object("workflows", entity_name, entity_id)

    def set_workflow(self, workflow: Workflow) -> None:
        """
        Set a Workflow.

        Parameters
        ----------
        workflow : Workflow
            Workflow to set.

        Returns
        -------
        None
        """
        self._add_object(workflow, "workflows")

    def list_workflows(self, **kwargs) -> list[dict]:
        """
        List workflows associated with the project.

        Parameters
        ----------
        **kwargs : dict
            Filters to apply to the list. Shold be params={"filter": "value"}.

        Returns
        -------
        list[dict]
            List of objects related to project.
        """
        return list_workflows(self.name, **kwargs)

    #############################
    #  Secrets
    #############################

    def new_secret(self, **kwargs) -> Secret:
        """
        Create a new Secret instance with the specified parameters.

        Parameters
        ----------
        **kwargs
            Keyword arguments.

        Returns
        -------
        Secret
            An instance of the created secret.
        """
        kwargs["project"] = self.name
        obj = new_secret(**kwargs)
        self._add_object(obj, "secrets")
        return obj

    def get_secret(self, entity_name: str | None = None, entity_id: str | None = None, **kwargs) -> Secret:
        """
        Get object from backend.

        Parameters
        ----------
        entity_name : str
            Entity name.
        entity_id : str
            Entity ID.
        **kwargs : dict
            Parameters to pass to the API call.

        Returns
        -------
        Secret
            Instance of Secret class.
        """
        obj = get_secret(self.name, entity_name=entity_name, entity_id=entity_id, **kwargs)
        self._add_object(obj, "secrets")
        return obj

    def delete_secret(self, entity_name: str | None = None, entity_id: str | None = None, **kwargs) -> None:
        """
        Delete a Secret from project.

        Parameters
        ----------
        entity_name : str
            Entity name.
        entity_id : str
            Entity ID.
        **kwargs : dict
            Parameters to pass to the API call.

        Returns
        -------
        None
        """
        delete_secret(self.name, entity_name=entity_name, entity_id=entity_id, **kwargs)
        self._delete_object("secrets", entity_name, entity_id)

    def set_secret(self, secret: Secret) -> None:
        """
        Set a Secret.

        Parameters
        ----------
        secret : Secret
            Secret to set.

        Returns
        -------
        None
        """
        self._add_object(secret, "secrets")

    def list_secrets(self, **kwargs) -> list[dict]:
        """
        List secrets associated with the project.

        Parameters
        ----------
        **kwargs : dict
            Filters to apply to the list. Shold be params={"filter": "value"}.

        Returns
        -------
        list[dict]
            List of objects related to project.
        """
        return list_secrets(self.name, **kwargs)

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
        name = build_uuid(obj.get("name"))
        kind = obj.get("kind")
        metadata = build_metadata(kind, layer_digitalhub="digitalhub_core", **obj.get("metadata", {}))
        spec = build_spec(
            kind,
            layer_digitalhub="digitalhub_core",
            validate=validate,
            **obj.get("spec", {}),
        )
        status = build_status(kind, layer_digitalhub="digitalhub_core", **obj.get("status", {}))
        local = obj.get("local", False)
        return {
            "name": name,
            "kind": kind,
            "metadata": metadata,
            "spec": spec,
            "status": status,
            "local": local,
        }


def project_from_parameters(
    name: str,
    kind: str,
    description: str | None = None,
    source: str | None = None,
    labels: list[str] | None = None,
    local: bool = False,
    context: str | None = None,
    **kwargs,
) -> Project:
    """
    Create project.

    Parameters
    ----------
    name : str
        Name that identifies the object.
    kind : str
        Kind of the object.
    description : str
        Description of the object.
    source : str
        Remote git source for object.
    labels : list[str]
        List of labels.
    local : bool
        Flag to determine if object will be exported to backend.
    context : str
        The context of the project.
    **kwargs
        Spec keyword arguments.

    Returns
    -------
    Project
        Project object.
    """
    name = build_uuid(name)
    spec = build_spec(
        kind,
        layer_digitalhub="digitalhub_core",
        context=context,
        **kwargs,
    )
    metadata = build_metadata(
        kind,
        layer_digitalhub="digitalhub_core",
        name=name,
        description=description,
        labels=labels,
        source=source,
    )
    status = build_status(kind, layer_digitalhub="digitalhub_core")
    return Project(
        name=name,
        kind=kind,
        metadata=metadata,
        spec=spec,
        status=status,
        local=local,
    )


def project_from_dict(obj: dict) -> Project:
    """
    Create project from dictionary.

    Parameters
    ----------
    obj : dict
        Dictionary to create object from.

    Returns
    -------
    Project
        Project object.
    """
    return Project.from_dict(obj, validate=False)
