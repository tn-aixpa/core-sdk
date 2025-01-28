from __future__ import annotations

import typing

from digitalhub.entities._base.material.entity import MaterialEntity
from digitalhub.entities._commons.enums import EntityTypes
from digitalhub.entities._commons.utils import validate_metric_value
from digitalhub.entities._operations.processor import processor

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

        # Initialize metrics
        self._init_metrics()

    def save(self, update: bool = False) -> Model:
        """
        Save entity into backend.

        Parameters
        ----------
        update : bool
            Flag to indicate update.

        Returns
        -------
        Model
            Entity saved.
        """
        obj: Model = super().save(update)
        obj._get_metrics()
        return obj

    def log_metric(
        self,
        key: str,
        value: list | float | int,
        overwrite: bool = False,
        single_value: bool = False,
    ) -> None:
        """
        Log metric.

        Parameters
        ----------
        key : str
            Key of the metric.
        value : float
            Value of the metric.
        overwrite : bool
            If True, overwrite existing metric.
        single_value : bool
            If True, value is a single value.

        Returns
        -------
        None
        """
        validate_metric_value(value)

        if isinstance(value, list):
            self._handle_metric_list(key, value, overwrite)
        elif single_value:
            self._handle_metric_single(key, value, overwrite)
        else:
            self._handle_metric_list_append(key, value, overwrite)

        processor.update_metric(self.project, self.ENTITY_TYPE, self.id, key, self.status.metrics[key])

    ##############################
    # Helper methods
    ##############################

    def _init_metrics(self) -> None:
        """
        Initialize metrics.

        Returns
        -------
        None
        """
        if self.status.metrics is None:
            self.status.metrics = {}

    def _get_metrics(self) -> None:
        """
        Get model metrics from backend.

        Returns
        -------
        None
        """
        self.status.metrics = processor.read_metrics(
            project=self.project,
            entity_type=self.ENTITY_TYPE,
            entity_id=self.id,
        )

    def _handle_metric_single(self, key: str, value: float | int, overwrite: bool = False) -> None:
        """
        Handle metric single value.

        Parameters
        ----------
        key : str
            Key of the metric.
        value : float
            Value of the metric.
        overwrite : bool
            If True, overwrite existing metric.

        Returns
        -------
        None
        """
        if key not in self.status.metrics or overwrite:
            self.status.metrics[key] = value

    def _handle_metric_list_append(self, key: str, value: float | int, overwrite: bool = False) -> None:
        """
        Handle metric list append.

        Parameters
        ----------
        key : str
            Key of the metric.
        value : float
            Value of the metric.
        overwrite : bool
            If True, overwrite existing metric.

        Returns
        -------
        None
        """
        if key not in self.status.metrics or overwrite:
            self.status.metrics[key] = [value]
        else:
            self.status.metrics[key].append(value)

    def _handle_metric_list(self, key: str, value: list[int | float], overwrite: bool = False) -> None:
        """
        Handle metric list.

        Parameters
        ----------
        key : str
            Key of the metric.
        value : list[int | float]
            Value of the metric.
        overwrite : bool
            If True, overwrite existing metric.

        Returns
        -------
        None
        """
        if key not in self.status.metrics or overwrite:
            self.status.metrics[key] = value
        else:
            self.status.metrics[key].extend(value)
