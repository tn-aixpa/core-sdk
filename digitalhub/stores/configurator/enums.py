from __future__ import annotations

from enum import Enum


class CredsOrigin(Enum):
    """
    List credential origins.
    """

    ENV = "env"
    FILE = "file"
