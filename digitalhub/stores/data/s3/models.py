from __future__ import annotations

from pydantic import BaseModel


class S3StoreConfig(BaseModel):
    """
    S3 store configuration class.
    """

    endpoint_url: str
    """S3 endpoint URL."""

    aws_access_key_id: str
    """AWS access key ID."""

    aws_secret_access_key: str
    """AWS secret access key."""

    bucket_name: str
    """S3 bucket name."""
