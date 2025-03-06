from __future__ import annotations

import typing
from warnings import warn

from requests import request

from digitalhub.client.dhcore.enums import AuthType, DhcoreEnvVar
from digitalhub.client.dhcore.models import BasicAuth, OAuth2TokenAuth
from digitalhub.configurator.configurator import configurator
from digitalhub.utils.exceptions import ClientError
from digitalhub.utils.uri_utils import has_remote_scheme

if typing.TYPE_CHECKING:
    from requests import Response


# Default key used to store authentication information
AUTH_KEY = "_auth"

# API levels that are supported
MAX_API_LEVEL = 20
MIN_API_LEVEL = 10
LIB_VERSION = 10


class ClientDHCoreConfigurator:
    """
    Configurator object used to configure the client.
    """

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
            self._get_auth_vars()
            return

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
                configurator.set_credential(*pair)

        elif config.get("user") is not None and config.get("password") is not None:
            config = BasicAuth(**config)
            for pair in [
                (AUTH_KEY, AuthType.BASIC.value),
                (DhcoreEnvVar.ENDPOINT.value, config.endpoint),
                (DhcoreEnvVar.USER.value, config.user),
                (DhcoreEnvVar.PASSWORD.value, config.password),
            ]:
                configurator.set_credential(*pair)

        else:
            raise ClientError("Invalid credentials format.")

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
        api = api.removeprefix("/")
        return f"{configurator.get_credential(DhcoreEnvVar.ENDPOINT.value)}/{api}"

    ##############################
    # Private methods
    ##############################

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
        endpoint = configurator.load_var(DhcoreEnvVar.ENDPOINT.value)
        if endpoint is None:
            raise ClientError("Endpoint not set as environment variables.")
        endpoint = self._sanitize_endpoint(endpoint)
        configurator.set_credential(DhcoreEnvVar.ENDPOINT.value, endpoint)

    def _get_auth_vars(self) -> None:
        """
        Get authentication parameters from the env.

        Returns
        -------
        None
        """
        # Give priority to access token
        access_token = configurator.load_var(DhcoreEnvVar.ACCESS_TOKEN.value)
        if access_token is not None:
            configurator.set_credential(AUTH_KEY, AuthType.OAUTH2.value)
            configurator.set_credential(DhcoreEnvVar.ACCESS_TOKEN.value, access_token)

        # Fallback to basic
        else:
            user = configurator.load_var(DhcoreEnvVar.USER.value)
            password = configurator.load_var(DhcoreEnvVar.PASSWORD.value)
            if user is not None and password is not None:
                configurator.set_credential(AUTH_KEY, AuthType.BASIC.value)
                configurator.set_credential(DhcoreEnvVar.USER.value, user)
                configurator.set_credential(DhcoreEnvVar.PASSWORD.value, password)

    ##############################
    # Auth methods
    ##############################

    def basic_auth(self) -> bool:
        """
        Get basic auth.

        Returns
        -------
        bool
        """
        auth_type = configurator.get_credential(AUTH_KEY)
        return auth_type == AuthType.BASIC.value

    def oauth2_auth(self) -> bool:
        """
        Get oauth2 auth.

        Returns
        -------
        bool
        """
        auth_type = configurator.get_credential(AUTH_KEY)
        return auth_type == AuthType.OAUTH2.value

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
        creds = configurator.get_all_credentials()
        if AUTH_KEY not in creds:
            return kwargs
        if self.basic_auth():
            user = creds[DhcoreEnvVar.USER.value]
            password = creds[DhcoreEnvVar.PASSWORD.value]
            kwargs["auth"] = (user, password)
        elif self.oauth2_auth():
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
        refresh_token = configurator.load_from_env(DhcoreEnvVar.REFRESH_TOKEN.value)
        response = self._call_refresh_token_endpoint(url, refresh_token)

        # Otherwise try token from file
        if response.status_code in (400, 401, 403):
            refresh_token = configurator.load_from_config(DhcoreEnvVar.REFRESH_TOKEN.value)
            response = self._call_refresh_token_endpoint(url, refresh_token)

        response.raise_for_status()
        dict_response = response.json()

        # Read new access token and refresh token
        configurator.set_credential(DhcoreEnvVar.ACCESS_TOKEN.value, dict_response["access_token"])
        configurator.set_credential(DhcoreEnvVar.REFRESH_TOKEN.value, dict_response["refresh_token"])

        # Propagate new access token to config file
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
                DhcoreEnvVar.ACCESS_TOKEN.value,
                DhcoreEnvVar.REFRESH_TOKEN.value,
            ]
        )

    def _get_refresh_endpoint(self) -> str:
        """
        Get the refresh endpoint.

        Returns
        -------
        str
            Refresh endpoint.
        """
        # Get issuer endpoint
        endpoint_issuer = configurator.load_var(DhcoreEnvVar.ISSUER.value)
        if endpoint_issuer is not None:
            endpoint_issuer = self._sanitize_endpoint(endpoint_issuer)
            configurator.set_credential(DhcoreEnvVar.ISSUER.value, endpoint_issuer)
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
        client_id = configurator.load_var(DhcoreEnvVar.CLIENT_ID.value)
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
