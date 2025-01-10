from __future__ import annotations

import os
import typing
from configparser import ConfigParser
from warnings import warn

from requests import request

from digitalhub.client.dhcore.credentials_store import CredentialsStore
from digitalhub.client.dhcore.enums import AuthType, DhcoreEnvVar
from digitalhub.client.dhcore.env import ENV_FILE, LIB_VERSION, MAX_API_LEVEL, MIN_API_LEVEL
from digitalhub.client.dhcore.models import BasicAuth, OAuth2TokenAuth
from digitalhub.utils.exceptions import ClientError
from digitalhub.utils.uri_utils import has_remote_scheme

if typing.TYPE_CHECKING:
    from requests import Response


AUTH_KEY = "_auth"
DEFAULT_SET = "DEFAULT"


class ClientDHCoreConfigurator:
    """
    Configurator object used to configure the client.
    """

    def __init__(self) -> None:
        # Store
        self._store = CredentialsStore()

        # Current credentials set (DEFAULT by default)
        self._profile_creds = DEFAULT_SET

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
            self._get_core_endpoint()
            return self._get_auth_vars()

        # Read passed config
        # Validate and save credentials
        if config.get("access_token") is not None:
            config = OAuth2TokenAuth(**config)
            for pair in [
                (AUTH_KEY, AuthType.OAUTH2.value),
                (DhcoreEnvVar.ENDPOINT.value, config.endpoint),
                (DhcoreEnvVar.ISSUER.value, config.issuer),
                (DhcoreEnvVar.ACCESS_TOKEN.value, config.access_token),
                (DhcoreEnvVar.REFRESH_TOKEN.value, config.refresh_token),
                (DhcoreEnvVar.CLIENT_ID.value, config.client_id),
            ]:
                self._set_credential(*pair)

        elif config.get("user") is not None and config.get("password") is not None:
            config = BasicAuth(**config)
            for pair in [
                (AUTH_KEY, AuthType.BASIC.value),
                (DhcoreEnvVar.ENDPOINT.value, config.endpoint),
                (DhcoreEnvVar.USER.value, config.user),
                (DhcoreEnvVar.PASSWORD.value, config.password),
            ]:
                self._set_credential(*pair)

        else:
            raise ClientError("Invalid credentials format.")

    def set_current_credentials_set(self, creds_set: str) -> None:
        """
        Set the current credentials set.

        Parameters
        ----------
        creds_set : str
            Credentials set name.

        Returns
        -------
        None
        """
        self._profile_creds = creds_set

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
                raise ClientError("Backend API level not supported.")
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
        return f"{self._get_credentials(DhcoreEnvVar.ENDPOINT.value)}/{api}"

    ##############################
    # Private methods
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
        var = self._get_credentials(var_name)
        if var is None:
            var = self._load_from_env(var_name)
        if var is None:
            var = self._load_from_config(var_name)
        return var

    def _load_from_env(self, var: str) -> str | None:
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
        if self._profile_creds != DEFAULT_SET:
            var += f"__{self._profile_creds}"
        env_var = os.getenv(var)
        if env_var != "":
            return env_var

    def _load_from_config(self, var: str) -> str | None:
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
        cfg = ConfigParser()
        cfg.read(ENV_FILE)
        try:
            return cfg[self._profile_creds].get(var)
        except KeyError:
            raise ClientError(f"No section {self._profile_creds} in config file.")

    @staticmethod
    def _sanitize_endpoint(endpoint: str) -> str:
        """
        Sanitize the endpoint.

        Returns
        -------
        None
        """
        if not has_remote_scheme(endpoint):
            raise ClientError("Invalid endpoint scheme. Must start with http:// or https://.")

        endpoint = endpoint.strip()
        return endpoint.removesuffix("/")

    def _get_core_endpoint(self) -> None:
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
            raise ClientError("Endpoint not set as environment variables.")
        endpoint = self._sanitize_endpoint(endpoint)
        self._set_credential(DhcoreEnvVar.ENDPOINT.value, endpoint)

    def _get_auth_vars(self) -> None:
        """
        Get authentication parameters from the env.

        Returns
        -------
        None
        """
        # Give priority to access token
        access_token = self._load_var(DhcoreEnvVar.ACCESS_TOKEN.value)
        if access_token is not None:
            self._set_credential(AUTH_KEY, AuthType.OAUTH2.value)
            self._set_credential(DhcoreEnvVar.ACCESS_TOKEN.value, access_token)

        # Fallback to basic
        else:
            user = self._load_var(DhcoreEnvVar.USER.value)
            password = self._load_var(DhcoreEnvVar.PASSWORD.value)
            if user is not None and password is not None:
                self._set_credential(AUTH_KEY, AuthType.BASIC.value)
                self._set_credential(DhcoreEnvVar.USER.value, user)
                self._set_credential(DhcoreEnvVar.PASSWORD.value, password)

    def _write_env(self) -> None:
        """
        Write the env variables to the .dhcore file.
        It will overwrite any existing env variables.

        Returns
        -------
        None
        """
        try:
            cfg = ConfigParser()
            cfg.read(ENV_FILE)

            creds = self._get_all_cred()
            creds.pop(AUTH_KEY, None)

            default = cfg.defaults()
            if not default:
                cfg[DEFAULT_SET] = creds
                if self._profile_creds != DEFAULT_SET:
                    cfg.add_section(self._profile_creds)
                    cfg[self._profile_creds] = creds
            else:
                sections = cfg.sections()
                if self._profile_creds not in sections and self._profile_creds != DEFAULT_SET:
                    cfg.add_section(self._profile_creds)
                cfg[self._profile_creds] = creds

            ENV_FILE.touch(exist_ok=True)
            with open(ENV_FILE, "w") as inifile:
                cfg.write(inifile)

        except Exception as e:
            raise ClientError(f"Failed to write env file: {e}")

    ##############################
    # Credentials store methods
    ##############################

    def _set_credential(self, key: str, value: str) -> None:
        """
        Register a credential value.

        Parameters
        ----------
        key : str
            The key.
        value : str
            The value.

        Returns
        -------
        None
        """
        self._store.set(self._profile_creds, key, value)

    def _get_credentials(self, key: str) -> dict:
        """
        Get the credentials.

        Parameters
        ----------
        key : str
            The key.

        Returns
        -------
        dict
            The credentials.
        """
        return self._store.get(self._profile_creds, key)

    def _get_all_cred(self) -> dict:
        """
        Get all the credentials.

        Returns
        -------
        dict
            The credentials.
        """
        return self._store.get_all(self._profile_creds)

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
        creds = self._get_all_cred()
        if AUTH_KEY not in creds:
            return kwargs
        if creds[AUTH_KEY] == AuthType.BASIC.value:
            user = creds[DhcoreEnvVar.USER.value]
            password = creds[DhcoreEnvVar.PASSWORD.value]
            kwargs["auth"] = (user, password)
        elif creds[AUTH_KEY] == AuthType.OAUTH2.value:
            if "headers" not in kwargs:
                kwargs["headers"] = {}
            access_token = creds[DhcoreEnvVar.ACCESS_TOKEN.value]
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
        self._set_credential(DhcoreEnvVar.ACCESS_TOKEN.value, dict_response["access_token"])
        self._set_credential(DhcoreEnvVar.REFRESH_TOKEN.value, dict_response["refresh_token"])

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
            self._set_credential(DhcoreEnvVar.ISSUER.value, endpoint_issuer)
        else:
            raise ClientError("Issuer endpoint not set.")

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
            raise ClientError("Client id not set.")

        # Send request to get new access token
        payload = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": refresh_token,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        return request("POST", url, data=payload, headers=headers, timeout=60)
