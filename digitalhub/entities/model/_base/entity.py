from __future__ import annotations

import typing

from digitalhub.entities._base.material.entity import MaterialEntity
from digitalhub.entities._commons.enums import EntityTypes

if typing.TYPE_CHECKING:
    from digitalhub.entities._base.entity.metadata import Metadata
    from digitalhub.entities.model._base.spec import ModelSpec
    from digitalhub.entities.model._base.status import ModelStatus


class Model(MaterialEntity):
    """
    A class representing a model.
    """

    ENTITY_TYPE = EntityTypes.MODEL.value

    def __init__(
        self,
        project: str,
        name: str,
        uuid: str,
        kind: str,
        metadata: Metadata,
        spec: ModelSpec,
        status: ModelStatus,
        user: str | None = None,
    ) -> None:
        super().__init__(project, name, uuid, kind, metadata, spec, status, user)
        self.spec: ModelSpec
        self.status: ModelStatus

    def log_metrics(self, metrics: dict[str, float]) -> None:
        """
        Log metrics to the model status.

        Parameters
        ----------
        metrics : dict[str, float]
            The metrics to log.

        Returns
        -------
        None
        """
        if not isinstance(metrics, dict):
            raise TypeError("Metrics must be a dictionary")
        self.status.metrics = metrics
        self.save(update=True)
