from __future__ import annotations

from pydantic import BaseModel


class Metric(BaseModel):
    value: float | int | list[float | int]
