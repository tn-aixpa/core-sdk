from __future__ import annotations

from typing import Union

from pydantic import BaseModel


class Metric(BaseModel):
    value: Union[float, int, list[Union[float, int]]]
