"""
Base Function specification module.
"""
from __future__ import annotations

from digitalhub_core.entities._base.spec import Spec, SpecParams


class FunctionSpec(Spec):
    """
    Specification for a Function.
    """


class FunctionParams(SpecParams):
    """
    Function parameters model.
    """


class SourceCodeStruct:
    """
    Source code struct.
    """

    def __init__(
        self,
        source: str | None = None,
        code: str | None = None,
        base64: str | None = None,
        lang: str | None = None,
    ) -> None:
        """
        Constructor.

        Parameters
        ----------
        source : str
            Source reference.
        code : str
            Source code (plain).
        base64 : str
            Source code (base64 encoded).
        lang : str
            Source code language (hint).
        """
        self.source = source
        self.code = code
        self.base64 = base64
        self.lang = lang

    def to_dict(self) -> dict:
        """
        Convert to dictionary.

        Returns
        -------
        dict
            Dictionary representation of the object.
        """
        dict_ = {}
        if self.source is not None:
            dict_["source"] = self.source
        if self.base64 is not None:
            dict_["base64"] = self.base64
        if self.lang is not None:
            dict_["lang"] = self.lang

        return dict_

    def __repr__(self) -> str:
        return str(self.to_dict())
