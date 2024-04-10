"""
Entity metadata module.
"""
from __future__ import annotations

from digitalhub_core.entities._base.base import ModelObj


class Metadata(ModelObj):
    """
    A class representing the metadata of an entity.
    Metadata is a collection of information about an entity thought
    to be modifiable by the user. The information contained in the
    metadata can be discordant with the actual state of the entity,
    for example the name of the entity in the database.
    """

    def __init__(
        self,
        name: str | None = None,
        source: str | None = None,
        labels: list[str] | None = None,
        embedded: bool = True,
        created: str | None = None,
        created_by: str | None = None,
        updated: str | None = None,
        updated_by: str | None = None,
    ) -> None:
        """
        Constructor.

        Parameters
        ----------
        name : str
            Name the object.
        source : str
            (Remote GIT) Source of the entity.
        labels : list[str]
            A list of labels to associate with the entity.
        embedded : bool
            Whether the entity specifications are embedded into a project.
        created : str
            Created date.
        created_by : str
            Created by.
        updated : str
            Updated date.
        updated_by : str
            Updated by.
        """
        self.name = name
        self.source = source
        self.labels = labels
        self.embedded = embedded
        self.created = created
        self.updated = updated

    @classmethod
    def from_dict(cls, obj: dict) -> "Metadata":
        """
        Return entity metadata object from dictionary.

        Parameters
        ----------
        obj : dict
            A dictionary containing the attributes of the entity metadata.

        Returns
        -------
        Metadata
            An entity metadata object.
        """
        return cls(**obj)


class MetadataRegistry(dict):
    """
    A class representing the registry of entity metadata.
    """

    def register(self, kind: str, module: str, metadata_class: str) -> None:
        """
        Register an entity metadata.

        Parameters
        ----------
        kind : str
            The kind of the entity.
        module : str
            The module name of the entity metadata.
        metadata_class : str
            The class name of the entity metadata.

        Returns
        -------
        None
        """
        self[kind] = {"module": module, "metadata_class": metadata_class}
