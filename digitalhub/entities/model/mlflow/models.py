from __future__ import annotations

from pydantic import BaseModel, Field


class Signature(BaseModel):
    """
    MLFlow model signature.
    """

    inputs: str = None
    outputs: str = None
    params: str = None

    def to_dict(self):
        return self.model_dump()


class Dataset(BaseModel):
    """
    MLFlow model dataset.
    """

    name: str = None
    digest: str = None
    profile: str = None
    schema_: str = Field(default=None, alias="schema")
    source: str = None
    source_type: str = None

    def to_dict(self):
        return self.model_dump()
