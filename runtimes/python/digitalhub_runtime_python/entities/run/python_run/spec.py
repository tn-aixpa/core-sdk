from __future__ import annotations

from digitalhub.entities.run._base.spec import RunSpec, RunValidator


class RunSpecPythonRun(RunSpec):
    """RunSpecPythonRun specifications."""

    def __init__(
        self,
        task: str,
        local_execution: bool = False,
        function: str | None = None,
        workflow: str | None = None,
        node_selector: list[dict] | None = None,
        volumes: list[dict] | None = None,
        resources: dict | None = None,
        affinity: dict | None = None,
        tolerations: list[dict] | None = None,
        envs: list[dict] | None = None,
        secrets: list[str] | None = None,
        profile: str | None = None,
        source: dict | None = None,
        image: str | None = None,
        base_image: str | None = None,
        python_version: str | None = None,
        requirements: list | None = None,
        backoff_limit: int | None = None,
        schedule: str | None = None,
        service_type: str | None = None,
        replicas: int | None = None,
        instructions: dict | None = None,
        inputs: dict | None = None,
        outputs: dict | None = None,
        parameters: dict | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            task,
            local_execution,
            function,
            workflow,
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
        self.source = source
        self.image = image
        self.base_image = base_image
        self.python_version = python_version
        self.requirements = requirements
        self.backoff_limit = backoff_limit
        self.schedule = schedule
        self.service_type = service_type
        self.replicas = replicas
        self.instructions = instructions
        self.inputs = inputs
        self.outputs = outputs
        self.parameters = parameters


class RunValidatorPythonRun(RunValidator):
    """RunValidatorPythonRun validator."""

    # Function parameters
    source: dict = None
    image: str = None
    base_image: str = None
    python_version: str = None
    requirements: list = None

    # Task job
    backoff_limit: int = None
    schedule: str = None

    # Task serve
    service_type: str = None
    replicas: int = None

    # Task build
    instructions: list[str] = None

    # Run parameters
    inputs: dict = None
    """Run inputs."""

    outputs: dict = None
    """Run outputs."""

    parameters: dict = None
    """Run parameters."""
