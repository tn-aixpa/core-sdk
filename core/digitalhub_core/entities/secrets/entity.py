"""
Secret module.
"""
from __future__ import annotations

import typing
from pathlib import Path

from digitalhub_core.context.builder import get_context
from digitalhub_core.entities._base.entity import Entity
from digitalhub_core.entities._builders.metadata import build_metadata
from digitalhub_core.entities._builders.spec import build_spec
from digitalhub_core.entities._builders.status import build_status
from digitalhub_core.utils.api import api_ctx_create, api_ctx_list, api_ctx_update
from digitalhub_core.utils.generic_utils import build_uuid, get_timestamp
from digitalhub_core.utils.io_utils import write_yaml

if typing.TYPE_CHECKING:
    from digitalhub_core.context.context import Context
    from digitalhub_core.entities.secrets.metadata import SecretMetadata
    from digitalhub_core.entities.secrets.spec import SecretSpec
    from digitalhub_core.entities.secrets.status import SecretStatus


class Secret(Entity):
    """
    A class representing a secret.
    """

    def __init__(
        self,
        project: str,
        name: str,
        uuid: str,
        kind: str,
        metadata: SecretMetadata,
        spec: SecretSpec,
        status: SecretStatus,
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
        metadata : SecretMetadata
            Metadata of the object.
        spec : SecretSpec
            Specification of the object.
        status : SecretStatus
            Status of the object.
        """
        super().__init__()
        self.project = project
        self.name = name
        self.id = uuid
        self.kind = kind
        self.key = f"store://{project}/secrets/{kind}/{name}:{uuid}"
        self.metadata = metadata
        self.spec = spec
        self.status = status

        # Add attributes to be used in the to_dict method
        self._obj_attr.extend(["project", "name", "id", "key"])

    #############################
    #  Save / Export
    #############################

    def save(self, update: bool = False) -> Secret:
        """
        Save entity into backend.

        Parameters
        ----------
        update : bool
            Flag to indicate update.

        Returns
        -------
        Secret
            Entity saved.
        """
        obj = self.to_dict()

        if not update:
            api = api_ctx_create(self.project, "secrets")
            new_obj = self._context().create_object(api, obj)
            self._update_attributes(new_obj)
            return self

        self.metadata.updated = obj["metadata"]["updated"] = get_timestamp()
        api = api_ctx_update(self.project, "secrets", self.id)
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
    #  Secret methods
    #############################

    def set_secret_value(self, value: str) -> None:
        """
        Set a secret.

        Parameters
        ----------
        key : str
            Key of the secret.
        value : str
            Value of the secret.

        Returns
        -------
        None
        """
        if self._context().local:
            raise NotImplementedError("set_secret() is not implemented for local projects.")

        obj = {self.name: value}
        api = api_ctx_list(self.project, "secrets") + "/data"
        self._context().update_object(api, obj)

    def read_secret_value(self) -> dict:
        """
        Read a secret from backend.

        Parameters
        ----------
        key : str
            Key or list of keys from the secret.

        Returns
        -------
        str
            Value of the secret.
        """
        if self._context().local:
            raise NotImplementedError("read_secret() is not implemented for local projects.")

        params = {"keys": self.name}
        api = api_ctx_list(self.project, "secrets") + "/data"
        return self._context().read_object(api, params=params)

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

        Returns
        -------
        dict
            A dictionary containing the attributes of the entity instance.
        """
        project = obj.get("project")
        name = obj.get("name")
        kind = obj.get("kind")
        uuid = build_uuid(obj.get("id"))
        metadata = build_metadata(kind, layer_digitalhub="digitalhub_core", **obj.get("metadata", {}))
        spec = build_spec(
            kind,
            layer_digitalhub="digitalhub_core",
            validate=validate,
            **obj.get("spec", {}),
        )
        status = build_status(kind, layer_digitalhub="digitalhub_core", **obj.get("status", {}))
        return {
            "project": project,
            "name": name,
            "uuid": uuid,
            "kind": kind,
            "metadata": metadata,
            "spec": spec,
            "status": status,
        }


def secret_from_parameters(
    project: str,
    name: str,
    kind: str,
    uuid: str | None = None,
    description: str | None = None,
    source: str | None = None,
    labels: list[str] | None = None,
    embedded: bool = True,
    **kwargs,
) -> Secret:
    """
    Create a new Secret instance with the specified parameters.

    Parameters
    ----------
    project : str
        A string representing the project associated with this secret.
    name : str
        The name of the secret.
    kind : str
        Kind of the object.
    uuid : str
        ID of the object in form of UUID.
    source : str
        Remote git source for object.
    labels : list[str]
        List of labels.
    description : str
        A description of the secret.
    embedded : bool
        Flag to determine if object must be embedded in project.
    **kwargs
        Spec keyword arguments.

    Returns
    -------
    Secret
        An instance of the created secret.
    """
    uuid = build_uuid(uuid)
    metadata = build_metadata(
        kind,
        layer_digitalhub="digitalhub_core",
        project=project,
        name=name,
        version=uuid,
        description=description,
        source=source,
        labels=labels,
        embedded=embedded,
    )
    path = f"kubernetes://dhcore-proj-secrets-{project}/{name}"
    provider = "kubernetes"
    spec = build_spec(
        kind,
        path=path,
        provider=provider,
        layer_digitalhub="digitalhub_core",
        **kwargs,
    )
    status = build_status(kind, layer_digitalhub="digitalhub_core")
    return Secret(
        project=project,
        name=name,
        uuid=uuid,
        kind=kind,
        metadata=metadata,
        spec=spec,
        status=status,
    )


def secret_from_dict(obj: dict) -> Secret:
    """
    Create Secret instance from a dictionary.

    Parameters
    ----------
    obj : dict
        Dictionary to create object from.

    Returns
    -------
    Secret
        Secret instance.
    """
    return Secret.from_dict(obj, validate=False)
