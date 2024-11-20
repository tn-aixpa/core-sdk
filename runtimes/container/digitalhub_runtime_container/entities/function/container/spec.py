from __future__ import annotations

from digitalhub.entities.function._base.spec import FunctionSpec, FunctionValidator

from digitalhub_runtime_container.entities.function.container.models import SourceValidator


class FunctionSpecContainer(FunctionSpec):
    """
    FunctionSpecContainer specifications.
    """

    def __init__(
        self,
        image: str | None = None,
        base_image: str | None = None,
        command: str | None = None,
        args: list[str] | None = None,
        source: dict | None = None,
    ) -> None:
        super().__init__()

        self.image = image
        self.base_image = base_image
        self.command = command
        self.args = args
        self.source = source


class FunctionValidatorContainer(FunctionValidator):
    """
    FunctionValidatorContainer validator.
    """

    image: str = None
    """Name of the Function's container image."""

    base_image: str = None
    """Function's base container image."""

    command: str = None
    """Command to run inside the container."""

    args: list[str] = None
    """Arguments to pass to the entrypoint."""

    source: SourceValidator = None
    """Source code params."""
