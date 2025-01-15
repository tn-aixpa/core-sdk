from __future__ import annotations

from enum import Enum


class S3StoreEnv(Enum):
    """
    S3Store environment
    """

    ENDPOINT_URL = "S3_ENDPOINT_URL"
    ACCESS_KEY_ID = "AWS_ACCESS_KEY_ID"
    SECRET_ACCESS_KEY = "AWS_SECRET_ACCESS_KEY"
    BUCKET_NAME = "S3_BUCKET_NAME"
