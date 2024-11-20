from __future__ import annotations

from enum import Enum


class HuggingfaceTaskName(Enum):
    """
    Huggingface task name enum.
    """

    SEQUENCE_CLASSIFICATION = "SEQUENCE_CLASSIFICATION"
    TOKEN_CLASSIFICATION = "TOKEN_CLASSIFICATION"
    FILL_MASK = "FILL_MASK"
    TEXT_GENERATION = "TEXT_GENERATION"
    TEXT2TEXT_GENERATION = "TEXT2TEXT_GENERATION"


class Backend(Enum):
    """
    Backend enum.
    """

    AUTO = "AUTO"
    VLLM = "VLLM"
    HUGGINGFACE = "HUGGINGFACE"


class Dtype(Enum):
    """
    Dtype enum.
    """

    AUTO = "AUTO"
    FLOAT32 = "FLOAT32"
    FLOAT16 = "FLOAT16"
    BFLOAT16 = "BFLOAT16"
    FLOAT = "FLOAT"
    HALF = "HALF"
