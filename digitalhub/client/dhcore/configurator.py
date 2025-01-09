from __future__ import annotations

import os
import typing
from warnings import warn

from dotenv import set_key
from dotenv.main import DotEnv
from requests import request

from digitalhub.client.dhcore.credentials_store import CredentialsStore
from digitalhub.client.dhcore.enums import AuthType, DhcoreEnvVar
from digitalhub.client.dhcore.env import ENV_FILE, LIB_VERSION, MAX_API_LEVEL, MIN_API_LEVEL
from digitalhub.client.dhcore.error_parser import ErrorParser
from digitalhub.client.dhcore.models import BasicAuth, OAuth2TokenAuth
from digitalhub.utils.exceptions import BackendError
from digitalhub.utils.uri_utils import has_remote_scheme

if typing.TYPE_CHECKING:
    from requests import Response


class ClientDHCoreConfigurator:
    """
    Configurator object used to configure the client.
    """

    def __init__(self) -> None:
        # Store
        self._store = CredentialsStore()

        # Error parser
        self._error_parser = ErrorParser()

        # Auth type
        self._auth_type: str | None = None

    ##############################
    # Configuration methods
    ##############################

    def configure(self, config: dict | None = None) -> None:
        """
        Configure the client attributes with config (given or from
        environment).
        Regarding authentication parameters, the config parameter
        takes precedence over the env variables, and the token
        over the basic auth. Furthermore, the config parameter is
        validated against the proper pydantic model.

        Parameters
        ----------
        config : dict
            Configuration dictionary.

        Returns
        -------
        None
        """
        if config is None:
            self._get_endpoint_from_env()
            return self._get_auth_from_env()

        # Read passed config
        if config.get("access_token") is not None:
            config = OAuth2TokenAuth(**config)
            self._auth_type = AuthType.OAUTH2.value
            self._store.set_credentials(DhcoreEnvVar.ENDPOINT.value, config.endpoint)
            self._store.set_credentials(DhcoreEnvVar.ISSUER.value, config.issuer)
            self._store.set_credentials(DhcoreEnvVar.ACCESS_TOKEN.value, config.access_token)
            self._store.set_credentials(DhcoreEnvVar.REFRESH_TOKEN.value, config.refresh_token)
            self._store.set_credentials(DhcoreEnvVar.CLIENT_ID.value, config.client_id)

        elif config.get("user") is not None and config.get("password") is not None:
            config = BasicAuth(**config)
            self._auth_type = AuthType.BASIC.value
            self._store.set_credentials(DhcoreEnvVar.ENDPOINT.value, config.endpoint)
            self._store.set_credentials(DhcoreEnvVar.USER.value, config.user)
            self._store.set_credentials(DhcoreEnvVar.PASSWORD.value, config.password)

        else:
            raise BackendError("No authentication method provided.")

    ##############################
    # Loader methods
    ##############################

    def _load_var(self, var_name: str) -> str | None:
        """
        Get env variable from credentials store, env or file (in order).

        Parameters
        ----------
        var_name : str
            Environment variable name.

        Returns
        -------
        str | None
            Environment variable value.
        """
        var = self._store.get_credentials(var_name)
        if var is None:
            var = self._load_from_env(var_name)
        if var is None:
            var = self._load_from_config(var_name)
        return var

    @staticmethod
    def _load_from_env(var: str) -> str | None:
        """
        Load variable from env.

        Parameters
        ----------
        var : str
            Environment variable name.

        Returns
        -------
        str | None
            Environment variable value.
        """
        env_var = os.getenv(var)
        if env_var != "":
            return env_var

    @staticmethod
    def _load_from_config(var: str) -> str | None:
        """
        Load variable from config file.

        Parameters
        ----------
        var : str
            Environment variable name.

        Returns
        -------
        str | None
            Environment variable value.
        """
        return DotEnv(ENV_FILE).get(var)

    def _get_endpoint_from_env(self) -> None:
        """
        Get the DHCore endpoint from env.

        Returns
        -------
        None

        Raises
        ------
        Exception
            If the endpoint of DHCore is not set in the env variables.
        """
        endpoint = self._load_var(DhcoreEnvVar.ENDPOINT.value)
        if endpoint is None:
            raise BackendError("Endpoint not set as environment variables.")
        endpoint = self._sanitize_endpoint(endpoint)
        self._store.set_credentials(DhcoreEnvVar.ENDPOINT.value, endpoint)

    def _get_auth_from_env(self) -> None:
        """
        Get authentication parameters from the env.

        Returns
        -------
        None
        """
        # Give priority to access token
        access_token = self._load_var(DhcoreEnvVar.ACCESS_TOKEN.value)
        if access_token is not None:
            self._auth_type = AuthType.OAUTH2.value
            self._store.set_credentials(DhcoreEnvVar.ACCESS_TOKEN.value, access_token)

        # Fallback to basic
        else:
            user = self._load_var(DhcoreEnvVar.USER.value)
            password = self._load_var(DhcoreEnvVar.PASSWORD.value)
            if user is not None and password is not None:
                self._auth_type = AuthType.BASIC.value
                self._store.set_credentials(DhcoreEnvVar.USER.value, user)
                self._store.set_credentials(DhcoreEnvVar.PASSWORD.value, password)

    def _write_env(self) -> None:
        """
        Write the env variables to the .dhcore file.
        It will overwrite any existing env variables.

        Returns
        -------
        None
        """
        try:
            for k, v in self._store.get_all_credentials().items():
                set_key(dotenv_path=ENV_FILE, key_to_set=k, value_to_set=v)
        except Exception as e:
            warn(f"Failed to write env file: {e}")

    ##############################
    # Helper methods
    ##############################

    def check_core_version(self, response: Response) -> None:
        """
        Raise an exception if DHCore API version is not supported.

        Parameters
        ----------
        response : Response
            The response object.

        Returns
        -------
        None
        """
        if "X-Api-Level" in response.headers:
            core_api_level = int(response.headers["X-Api-Level"])
            if not (MIN_API_LEVEL <= core_api_level <= MAX_API_LEVEL):
                raise BackendError("Backend API level not supported.")
            if LIB_VERSION < core_api_level:
                warn("Backend API level is higher than library version. You should consider updating the library.")

    def build_url(self, api: str) -> str:
        """
        Build the url.

        Parameters
        ----------
        api : str
            The api to call.

        Returns
        -------
        str
            The url.
        """
        return f"{self._store.get_credentials(DhcoreEnvVar.ENDPOINT.value)}/{api}"

    @staticmethod
    def _sanitize_endpoint(endpoint: str) -> str:
        """
        Sanitize the endpoint.

        Returns
        -------
        None
        """
        if not has_remote_scheme(endpoint):
            raise BackendError("Invalid endpoint scheme. Must start with http:// or https://.")

        endpoint = endpoint.strip()
        return endpoint.removesuffix("/")

    ##############################
    # Auth methods
    ##############################

    def set_request_auth(self, kwargs: dict) -> dict:
        """
        Get the authentication header.

        Parameters
        ----------
        kwargs : dict
            Keyword arguments to pass to the request.

        Returns
        -------
        dict
            Authentication header.
        """
        if self._auth_type == AuthType.BASIC.value:
            user = self._store.get_credentials(DhcoreEnvVar.USER.value)
            password = self._store.get_credentials(DhcoreEnvVar.PASSWORD.value)
            kwargs["auth"] = (user, password)
        elif self._auth_type == AuthType.OAUTH2.value:
            if "headers" not in kwargs:
                kwargs["headers"] = {}
            access_token = self._store.get_credentials(DhcoreEnvVar.ACCESS_TOKEN.value)
            kwargs["headers"]["Authorization"] = f"Bearer {access_token}"
        return kwargs

    def get_new_access_token(self) -> None:
        """
        Get a new access token.

        Returns
        -------
        None
        """
        # Call issuer and get endpoint for
        # refreshing access token
        url = self._get_refresh_endpoint()

        # Call refresh token endpoint
        # Try token from env
        refresh_token = self._load_from_env(DhcoreEnvVar.REFRESH_TOKEN.value)
        response = self._call_refresh_token_endpoint(url, refresh_token)

        # Otherwise try token from file
        if response.status_code in (400, 401, 403):
            refresh_token = self._load_from_config(DhcoreEnvVar.REFRESH_TOKEN.value)
            response = self._call_refresh_token_endpoint(url, refresh_token)

        response.raise_for_status()
        dict_response = response.json()

        # Read new access token and refresh token
        self._store.set_credentials(DhcoreEnvVar.ACCESS_TOKEN.value, dict_response["access_token"])
        self._store.set_credentials(DhcoreEnvVar.REFRESH_TOKEN.value, dict_response["refresh_token"])

        # Propagate new access token to env
        self._write_env()

    def _get_refresh_endpoint(self) -> str:
        """
        Get the refresh endpoint.

        Returns
        -------
        str
            Refresh endpoint.
        """
        # Get issuer endpoint
        endpoint_issuer = self._load_var(DhcoreEnvVar.ISSUER.value)
        if endpoint_issuer is not None:
            endpoint_issuer = self._sanitize_endpoint(endpoint_issuer)
            self._store.set_credentials(DhcoreEnvVar.ISSUER.value, endpoint_issuer)
        else:
            raise BackendError("Issuer endpoint not set.")

        # Standard issuer endpoint path
        url = endpoint_issuer + "/.well-known/openid-configuration"

        # Call issuer to get refresh endpoint
        r = request("GET", url, timeout=60)
        r.raise_for_status()
        return r.json().get("token_endpoint")

    def _call_refresh_token_endpoint(self, url: str, refresh_token: str) -> Response:
        """
        Call the refresh token endpoint.

        Parameters
        ----------
        url : str
            Refresh token endpoint.
        refresh_token : str
            Refresh token.

        Returns
        -------
        Response
            Response object.
        """
        # Get client id
        client_id = self._load_var(DhcoreEnvVar.CLIENT_ID.value)
        if client_id is None:
            raise BackendError("Client id not set.")

        # Send request to get new access token
        payload = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": refresh_token,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        return request("POST", url, data=payload, headers=headers, timeout=60)
