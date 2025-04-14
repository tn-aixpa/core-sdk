from __future__ import annotations

from digitalhub.entities._base.entity.spec import Spec, SpecValidator


class TriggerSpec(Spec):
    """
    TriggerSpec specifications.
    """

    def __init__(self, **kwargs) -> None:
        ...


class TriggerValidator(SpecValidator):
    """
    TriggerValidator validator.
    """
