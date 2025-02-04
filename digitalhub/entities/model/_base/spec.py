from __future__ import annotations

from digitalhub.entities._base.material.spec import MaterialSpec, MaterialValidator


class ModelSpec(MaterialSpec):
    """
    ModelSpec specifications.
    """

    def __init__(
        self,
        path: str,
        framework: str | None = None,
        algorithm: str | None = None,
        parameters: dict | None = None,
    ) -> None:
        self.path = path
        self.framework = framework
        self.algorithm = algorithm
        self.parameters = parameters


class ModelValidator(MaterialValidator):
    """
    ModelValidator validator.
    """

    path: str
    """Path to the model."""

    framework: str = None
    """Model framework (e.g. 'pytorch')."""

    algorithm: str = None
    """Model algorithm (e.g. 'resnet')."""

    parameters: dict = None
    """Model validator."""
