"""
Dataitem module.
"""
from __future__ import annotations

import typing
from pathlib import Path

from digitalhub_core.context.builder import get_context
from digitalhub_core.entities._base.entity import Entity
from digitalhub_core.entities._builders.metadata import build_metadata
from digitalhub_core.entities._builders.spec import build_spec
from digitalhub_core.entities._builders.status import build_status
from digitalhub_core.utils.api import api_ctx_create, api_ctx_update
from digitalhub_core.utils.exceptions import EntityError
from digitalhub_core.utils.generic_utils import build_uuid, get_timestamp
from digitalhub_core.utils.io_utils import write_yaml
from digitalhub_core.utils.uri_utils import map_uri_scheme

if typing.TYPE_CHECKING:
    from digitalhub_core.context.context import Context
    from digitalhub_data.entities.dataitems.metadata import DataitemMetadata
    from digitalhub_data.entities.dataitems.spec import DataitemSpec
    from digitalhub_data.entities.dataitems.status import DataitemStatus


class Dataitem(Entity):
    """
    A class representing a dataitem.
    """

    def __init__(
        self,
        project: str,
        name: str,
        uuid: str,
        kind: str,
        metadata: DataitemMetadata,
        spec: DataitemSpec,
        status: DataitemStatus,
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
        metadata : DataitemMetadata
            Metadata of the object.
        spec : DataitemSpec
            Specification of the object.
        status : DataitemStatus
            Status of the object.
        """
        super().__init__()
        self.project = project
        self.name = name
        self.id = uuid
        self.kind = kind
        self.key = f"store://{project}/dataitems/{kind}/{name}:{uuid}"
        self.metadata = metadata
        self.spec = spec
        self.status = status

        # Add attributes to be used in the to_dict method
        self._obj_attr.extend(["project", "name", "id", "key"])

    #############################
    #  Save / Export
    #############################

    def save(self, update: bool = False) -> Dataitem:
        """
        Save entity into backend.

        Parameters
        ----------
        uuid : str
            Specify uuid for the dataitem to update

        Returns
        -------
        Dataitem
            Entity saved.
        """
        obj = self.to_dict()

        if not update:
            api = api_ctx_create(self.project, "dataitems")
            new_obj = self._context().create_object(api, obj)
            self._update_attributes(new_obj)
            return self

        self.metadata.updated = obj["metadata"]["updated"] = get_timestamp()
        api = api_ctx_update(self.project, "dataitems", self.id)
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
    #  Helper Methods
    #############################

    @staticmethod
    def _check_local(path: str) -> bool:
        """
        Check if path is local.

        Parameters
        ----------
        path : str
            Path to check.

        Returns
        -------
        bool
            True if local, False otherwise.
        """
        return map_uri_scheme(path) == "local"

    @staticmethod
    def _get_extension(path: str, file_format: str | None = None) -> str:
        """
        Get extension of path.

        Parameters
        ----------
        path : str
            Path to get extension from.
        file_format : str
            File format.

        Returns
        -------
        str
            File extension.

        Raises
        ------
        EntityError
            If file format is not supported.
        """
        if file_format is not None:
            return file_format

        scheme = map_uri_scheme(path)
        if scheme == "sql":
            return "parquet"

        ext = Path(path).suffix[1:]
        if ext is not None:
            return ext
        raise EntityError("Unknown file format. Only csv and parquet are supported.")

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
        name = obj.get("name")
        kind = obj.get("kind")
        uuid = build_uuid(obj.get("id"))
        metadata = build_metadata(kind, layer_digitalhub="digitalhub_data", **obj.get("metadata", {}))
        spec = build_spec(
            kind,
            layer_digitalhub="digitalhub_data",
            validate=validate,
            **obj.get("spec", {}),
        )
        status = build_status(kind, layer_digitalhub="digitalhub_data", **obj.get("status", {}))
        return {
            "project": project,
            "name": name,
            "uuid": uuid,
            "kind": kind,
            "metadata": metadata,
            "spec": spec,
            "status": status,
        }
