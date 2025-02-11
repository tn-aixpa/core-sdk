from __future__ import annotations

import time
import typing

from digitalhub.entities._base.unversioned.entity import UnversionedEntity
from digitalhub.entities._commons.enums import EntityTypes, State
from digitalhub.entities._commons.utils import validate_metric_value
from digitalhub.entities._operations.processor import processor
from digitalhub.factory.api import (
    build_runtime,
    build_spec,
    build_status,
    get_entity_type_from_kind,
    get_executable_kind,
)
from digitalhub.utils.exceptions import EntityError
from digitalhub.utils.logger import LOGGER

if typing.TYPE_CHECKING:
    from digitalhub.entities._base.entity.metadata import Metadata
    from digitalhub.entities.run._base.spec import RunSpec
    from digitalhub.entities.run._base.status import RunStatus
    from digitalhub.runtimes._base import Runtime


class Run(UnversionedEntity):
    """
    A class representing a run.
    """

    ENTITY_TYPE = EntityTypes.RUN.value

    def __init__(
        self,
        project: str,
        uuid: str,
        kind: str,
        metadata: Metadata,
        spec: RunSpec,
        status: RunStatus,
        user: str | None = None,
    ) -> None:
        super().__init__(project, uuid, kind, metadata, spec, status, user)

        self.spec: RunSpec
        self.status: RunStatus

        # Initialize metrics
        self._init_metrics()

    ##############################
    #  Run Methods
    ##############################

    def build(self) -> None:
        """
        Build run.

        Returns
        -------
        None
        """
        executable = self._get_executable()
        task = self._get_task()
        new_spec = self._get_runtime().build(executable, task, self.to_dict())
        self.spec = build_spec(self.kind, **new_spec)
        self._set_state(State.BUILT.value)
        self.save(update=True)

    def run(self) -> Run:
        """
        Run run.

        Returns
        -------
        Run
            Run object.
        """
        self.refresh()

        self._start_execution()
        self._setup_execution()

        try:
            status = self._get_runtime().run(self.to_dict())
        except Exception as e:
            self.refresh()
            if self.spec.local_execution:
                self._set_state(State.ERROR.value)
            self._set_message(str(e))
            self.save(update=True)
            raise e
        finally:
            self._finish_execution()

        self.refresh()
        if not self.spec.local_execution:
            status.pop("state", None)
        new_status = {**self.status.to_dict(), **status}
        self._set_status(new_status)
        self.save(update=True)
        return self

    def wait(self, log_info: bool = True) -> Run:
        """
        Wait for run to finish.

        Parameters
        ----------
        log_info : bool
            If True, log information.

        Returns
        -------
        Run
            Run object.
        """
        start = time.time()
        while True:
            if log_info:
                LOGGER.info(f"Waiting for run {self.id} to finish...")
            self.refresh()
            time.sleep(5)
            if self.status.state in [
                State.STOPPED.value,
                State.ERROR.value,
                State.COMPLETED.value,
            ]:
                if log_info:
                    current = time.time() - start
                    LOGGER.info(f"Run {self.id} finished in {current:.2f} seconds.")
                return self

    def logs(self) -> dict:
        """
        Get run logs.

        Returns
        -------
        dict
            Run logs.
        """
        return processor.read_run_logs(self.project, self.ENTITY_TYPE, self.id)

    def stop(self) -> None:
        """
        Stop run.

        Returns
        -------
        None
        """
        if not self.spec.local_execution:
            return processor.stop_run(self.project, self.ENTITY_TYPE, self.id)

    def resume(self) -> None:
        """
        Resume run.

        Returns
        -------
        None
        """
        if not self.spec.local_execution:
            return processor.resume_run(self.project, self.ENTITY_TYPE, self.id)

    def log_metric(
        self,
        key: str,
        value: list[float | int] | float | int,
        overwrite: bool = False,
        single_value: bool = False,
    ) -> None:
        """
        Log metric into entity status.
        A metric is named by a key and value (single number or list of numbers).
        The metric by default is put in a list or appended to an existing list.
        If single_value is True, the value will be a single number.

        Parameters
        ----------
        key : str
            Key of the metric.
        value : list[float | int] | float | int
            Value of the metric.
        overwrite : bool
            If True, overwrite existing metric.
        single_value : bool
            If True, value is a single value.

        Returns
        -------
        None

        Examples
        --------
        Log a new value in a list
        >>> entity.log_metric("loss", 0.002)

        Append a new value in a list
        >>> entity.log_metric("loss", 0.0019)

        Log a list of values and append them to existing metric:
        >>> entity.log_metric("loss", [0.0018, 0.0015])

        Log a single value (not represented as list):
        >>> entity.log_metric("accuracy", 0.9, single_value=True)

        Log a list of values and overwrite existing metric:
        >>> entity.log_metric("accuracy", [0.8, 0.9], overwrite=True)
        """
        value = validate_metric_value(value)

        if isinstance(value, list):
            self._handle_metric_list(key, value, overwrite)
        elif single_value:
            self._handle_metric_single(key, value, overwrite)
        else:
            self._handle_metric_list_append(key, value, overwrite)

        processor.update_metric(self.project, self.ENTITY_TYPE, self.id, key, self.status.metrics[key])

    ##############################
    #  Helpers
    ##############################

    def _setup_execution(self) -> None:
        """
        Setup run execution.

        Returns
        -------
        None
        """

    def _start_execution(self) -> None:
        """
        Start run execution.

        Returns
        -------
        None
        """
        self._context().set_run(f"{self.key}:{self.id}")
        if self.spec.local_execution:
            if not self._is_ready_to_run():
                raise EntityError("Run is not in a state to run.")
            self._set_state(State.RUNNING.value)
            self.save(update=True)

    def _finish_execution(self) -> None:
        """
        Finish run execution.

        Returns
        -------
        None
        """
        self._context().unset_run()

    def _is_ready_to_run(self) -> bool:
        """
        Check if run is in a state ready for running (BUILT or STOPPED).

        Returns
        -------
        bool
            True if run is in runnable state, False otherwise.
        """
        return (self.status.state == State.BUILT.value) or (self.status.state == State.STOPPED.value)

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
        """
        self.status: RunStatus = build_status(self.kind, **status)

    def _set_state(self, state: str) -> None:
        """
        Update run state.

        Parameters
        ----------
        state : str
            State to set.

        Returns
        -------
        None
        """
        self.status.state = state

    def _set_message(self, message: str) -> None:
        """
        Update run message.

        Parameters
        ----------
        message : str
            Message to set.

        Returns
        -------
        None
        """
        self.status.message = message

    def _get_runtime(self) -> Runtime:
        """
        Build runtime to build run or execute it.

        Returns
        -------
        Runtime
            Runtime object.
        """
        return build_runtime(self.kind, self.project)

    def _get_executable(self) -> dict:
        """
        Get executable object from backend. Reimplemented to avoid
        circular imports.

        Returns
        -------
        dict
            Executable (function or workflow) from backend.
        """
        exec_kind = get_executable_kind(self.kind)
        exec_type = get_entity_type_from_kind(exec_kind)
        string_to_split = getattr(self.spec, exec_type)
        exec_name, exec_id = string_to_split.split("://")[-1].split("/")[-1].split(":")
        return processor.read_context_entity(
            exec_name,
            entity_type=exec_type,
            project=self.project,
            entity_id=exec_id,
        ).to_dict()

    def _get_task(self) -> dict:
        """
        Get object from backend. Reimplemented to avoid
        circular imports.

        Returns
        -------
        dict
            Task from backend.
        """
        task_id = self.spec.task.split("://")[-1].split("/")[-1]
        return processor.read_unversioned_entity(
            task_id,
            entity_type=EntityTypes.TASK.value,
            project=self.project,
        ).to_dict()

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
        Get run metrics from backend.

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
