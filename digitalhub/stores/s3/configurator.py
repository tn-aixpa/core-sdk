from __future__ import annotations

from botocore.config import Config

from digitalhub.configurator.configurator import configurator
from digitalhub.stores.s3.enums import S3StoreEnv
from digitalhub.stores.s3.models import S3StoreConfig
from digitalhub.utils.exceptions import StoreError


class S3StoreConfigurator:
    """
    Configure the store by getting the credentials from user
    provided config or from environment.
    """

    def __init__(self, config: dict | None = None) -> None:
        self.configure(config)

    ##############################
    # Configuration methods
    ##############################

    def configure(self, config: dict | None = None) -> None:
        """
        Configure the store by getting the credentials from user
        provided config or from environment.

        Parameters
        ----------
        config : dict
            Configuration dictionary.

        Returns
        -------
        None
        """
        # Validate config
        if config is None:
            self._get_config()
        else:
            config = S3StoreConfig(**config)
            for pair in [
                (S3StoreEnv.ENDPOINT_URL.value, config.endpoint),
                (S3StoreEnv.ACCESS_KEY_ID.value, config.access_key),
                (S3StoreEnv.SECRET_ACCESS_KEY.value, config.secret_key),
                (S3StoreEnv.SESSION_TOKEN.value, config.session_token),
                (S3StoreEnv.BUCKET_NAME.value, config.bucket_name),
                (S3StoreEnv.REGION.value, config.region),
                (S3StoreEnv.SIGNATURE_VERSION.value, config.signature_version),
            ]:
                configurator.set_credential(*pair)

    def get_boto3_client_config(self) -> dict:
        """
        Get S3 credentials (access key, secret key,
        session token and other config).

        Returns
        -------
        dict
            The credentials.
        """
        creds = configurator.get_all_credentials()
        try:
            return {
                "endpoint_url": creds[S3StoreEnv.ENDPOINT_URL.value],
                "aws_access_key_id": creds[S3StoreEnv.ACCESS_KEY_ID.value],
                "aws_secret_access_key": creds[S3StoreEnv.SECRET_ACCESS_KEY.value],
                "aws_session_token": creds[S3StoreEnv.SESSION_TOKEN.value],
                "config": Config(
                    region_name=creds[S3StoreEnv.REGION.value],
                    signature_version=creds[S3StoreEnv.SIGNATURE_VERSION.value],
                ),
            }
        except KeyError as e:
            raise StoreError(f"Missing credentials for S3 store. {str(e)}")

    def _get_config(self) -> None:
        """
        Get the store configuration.

        Returns
        -------
        None
        """
        required_vars = [
            S3StoreEnv.ENDPOINT_URL,
            S3StoreEnv.ACCESS_KEY_ID,
            S3StoreEnv.SECRET_ACCESS_KEY,
            S3StoreEnv.BUCKET_NAME,
        ]
        optional_vars = [S3StoreEnv.REGION, S3StoreEnv.SIGNATURE_VERSION, S3StoreEnv.SESSION_TOKEN]

        # Load required environment variables
        credentials = {var.value: configurator.load_var(var.value) for var in required_vars}

        # Check for missing required credentials
        missing_vars = [key for key, value in credentials.items() if value is None]
        if missing_vars:
            raise StoreError(f"Missing credentials for S3 store: {', '.join(missing_vars)}")

        # Load optional environment variables
        credentials.update({var.value: configurator.load_var(var.value) for var in optional_vars})

        # Set credentials
        for key, value in credentials.items():
            configurator.set_credential(key, value)
