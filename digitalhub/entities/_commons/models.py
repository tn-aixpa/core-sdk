from __future__ import annotations

from pydantic import BaseModel

from digitalhub.utils.types import MetricType


class Metric(BaseModel):
    """
    Metric.
    """

    value: MetricType
