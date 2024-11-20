from __future__ import annotations

from digitalhub.entities.task._base.models import CoreServiceType
from digitalhub.entities.task._base.spec import TaskSpecFunction, TaskValidatorFunction
from pydantic import Field


class TaskSpecPythonServe(TaskSpecFunction):
    """TaskSpecPythonServe specifications."""

    def __init__(
        self,
        function: str,
        node_selector: list[dict] | None = None,
        volumes: list[dict] | None = None,
        resources: dict | None = None,
        affinity: dict | None = None,
        tolerations: list[dict] | None = None,
        envs: list[dict] | None = None,
        secrets: list[str] | None = None,
        profile: str | None = None,
        replicas: int | None = None,
        service_type: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            function,
            node_selector,
            volumes,
            resources,
            affinity,
            tolerations,
            envs,
            secrets,
            profile,
            **kwargs,
        )
        self.replicas = replicas
        self.service_type = service_type


class TaskValidatorPythonServe(TaskValidatorFunction):
    """
    TaskValidatorPythonServe validator.
    """

    replicas: int = Field(default=None, ge=1)
    """Number of replicas."""

    service_type: CoreServiceType = Field(default=CoreServiceType.NODE_PORT.value)
    """Service type."""
