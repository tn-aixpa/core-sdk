from __future__ import annotations

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
                (S3StoreEnv.BUCKET_NAME.value, config.bucket_name),
            ]:
                configurator.set_credential(*pair)

    def get_s3_creds(self) -> dict:
        """
        Get endpoint, access key and secret key.

        Returns
        -------
        dict
            The credentials.
        """
        creds = configurator.get_all_cred()
        try:
            return {
                "endpoint_url": creds[S3StoreEnv.ENDPOINT_URL.value],
                "aws_access_key_id": creds[S3StoreEnv.ACCESS_KEY_ID.value],
                "aws_secret_access_key": creds[S3StoreEnv.SECRET_ACCESS_KEY.value],
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
        endpoint = configurator.load_var(S3StoreEnv.ENDPOINT_URL.value)
        access_key = configurator.load_var(S3StoreEnv.ACCESS_KEY_ID.value)
        secret_key = configurator.load_var(S3StoreEnv.SECRET_ACCESS_KEY.value)
        bucket_name = configurator.load_var(S3StoreEnv.BUCKET_NAME.value)
        if endpoint is None or access_key is None or secret_key is None or bucket_name is None:
            raise StoreError("Missing credentials for S3 store.")
        configurator.set_credential(S3StoreEnv.ENDPOINT_URL.value, endpoint)
        configurator.set_credential(S3StoreEnv.ACCESS_KEY_ID.value, access_key)
        configurator.set_credential(S3StoreEnv.SECRET_ACCESS_KEY.value, secret_key)
        configurator.set_credential(S3StoreEnv.BUCKET_NAME.value, bucket_name)
        self._write_env()

    def _write_env(self) -> None:
        """
        Write the env variables to the .dhcore.ini file.
        It will overwrite any existing env variables.

        Returns
        -------
        None
        """
        configurator.write_env(
            [
                S3StoreEnv.ENDPOINT_URL.value,
                S3StoreEnv.ACCESS_KEY_ID.value,
                S3StoreEnv.SECRET_ACCESS_KEY.value,
                S3StoreEnv.BUCKET_NAME.value,
            ]
        )
