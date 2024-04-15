"""
DHCore Client module.
"""
from __future__ import annotations

import os

import requests
from digitalhub_core.client.objects.base import Client
from digitalhub_core.utils.exceptions import BackendError
from pydantic import BaseModel


class AuthConfig(BaseModel):
    """Client configuration model."""

    user: str = None
    """Username."""


class OAuth2TokenAuth(AuthConfig):
    """OAuth2 token authentication model."""

    access_token: str
    """OAuth2 token."""


class BasicAuth(AuthConfig):
    """Basic authentication model."""

    password: str
    """Basic authentication password."""


class ClientDHCore(Client):
    """
    DHCore client.

    The DHCore client is used to communicate with the Digitalhub Core backendAPI via REST.
    At creation, the client trys to get the endpoint and authentication parameters
    from the environment variables. In case the endpoint is not set, it raises an exception.
    """

    def __init__(self, config: dict = None) -> None:
        """
        Constructor.
        """
        super().__init__()

        self._endpoint = None

        self._auth_type = None
        self._user = None
        self._password = None
        self._access_token = None

        self._configure(config)

    def create_object(self, api: str, obj: dict | None = None, **kwargs) -> dict:
        """
        Create an object.

        Parameters
        ----------
        obj : dict
            The object to create.
        api : str
            The api to create the object with.

        Returns
        -------
        dict
            The created object.
        """
        kwargs["json"] = obj
        return self._call("POST", api, **kwargs)

    def read_object(self, api: str, **kwargs) -> dict:
        """
        Get an object.

        Parameters
        ----------
        api : str
            The api to get the object with.

        Returns
        -------
        dict
            The object.
        """
        return self._call("GET", api, **kwargs)

    def update_object(self, api: str, obj: dict | None = None, **kwargs) -> dict:
        """
        Update an object.

        Parameters
        ----------
        obj : dict
            The object to update.
        api : str
            The api to update the object with.

        Returns
        -------
        dict
            The updated object.
        """
        kwargs["json"] = obj
        return self._call("PUT", api, **kwargs)

    def delete_object(self, api: str, **kwargs) -> dict:
        """
        Delete an object.

        Parameters
        ----------
        api : str
            The api to delete the object with.

        Returns
        -------
        dict
            A generic dictionary.
        """
        resp = self._call("DELETE", api, **kwargs)
        if isinstance(resp, bool):
            resp = {"deleted": resp}
        return resp

    def list_objects(self, api: str, **kwargs) -> list[dict]:
        """
        List objects.

        Parameters
        ----------
        api : str
            The api to list the objects with.
        **kwargs : dict


        Returns
        -------
        list[dict]
            The list of objects.
        """
        if kwargs is None:
            kwargs = {}

        if kwargs.get("params") is None:
            kwargs["params"] = {}

        start_page = 0
        if "page" not in kwargs["params"]:
            kwargs["params"]["page"] = start_page

        objects = []
        while True:
            resp = self._call("GET", api, **kwargs)
            contents = resp["content"]
            total_pages = resp["totalPages"]
            if not contents or kwargs["params"]["page"] >= total_pages:
                break
            objects.extend(contents)
            kwargs["params"]["page"] += 1

        return objects

    def _call(self, call_type: str, api: str, **kwargs) -> dict:
        """
        Make a call to the DHCore API.
        Keyword arguments are passed to the session.request function.

        Parameters
        ----------
        call_type : str
            The type of call to make.
        api : str
            The api to call.
        **kwargs
            Keyword arguments.

        Returns
        -------
        dict
            The response object.
        """
        url = self._endpoint + api

        # Choose auth type
        if self._auth_type == "basic":
            kwargs["auth"] = self._user, self._password
        elif self._auth_type == "oauth2":
            kwargs["headers"] = {"Authorization": f"Bearer {self._access_token}"}

        # Call
        response = None
        try:
            response = requests.request(call_type, url, timeout=60, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if isinstance(e, requests.exceptions.Timeout):
                msg = "Request to DHCore backend timed out."
            elif isinstance(e, requests.exceptions.ConnectionError):
                msg = "Unable to connect to DHCore backend."
            elif isinstance(e, requests.exceptions.JSONDecodeError):
                return {}
            else:
                msg = f"Backend error: {e}"
            raise BackendError(msg) from e

    ################################
    # Configuration methods
    ################################

    def _configure(self, config: dict | None = None) -> None:
        """
        Function to set environment variables for DHub Core config.

        Parameters
        ----------
        config : ClientConfig
            The client config.

        Returns
        -------
        None
        """

        # Get endpoint at the beginning
        self._get_endpoint_from_env()

        # Evaluate configuration authentication parameters
        if config is not None:
            # Validate configuration against pydantic model

            # Try to get user/access_token or user/password

            if config.get("access_token") is not None:
                config = OAuth2TokenAuth(**config)
                self._user = config.user
                self._access_token = config.access_token
                self._auth_type = "oauth2"

            elif config.get("user") is not None and config.get("password") is not None:
                config = BasicAuth(**config)
                self._user = config.user
                self._password = config.password
                self._auth_type = "basic"

            return

        # Otherwise, use environment variables
        self._get_auth_from_env()

    def _get_endpoint_from_env(self) -> None:
        """
        Get DHub Core endpoint environment variables.

        Returns
        -------
        None

        Raises
        ------
        Exception
            If the endpoint of DHCore is not set in the env variables.
        """
        endpoint = os.getenv("DIGITALHUB_CORE_ENDPOINT")
        if endpoint is None:
            raise BackendError("Endpoint not set as environment variables.")

        # Sanitize endpoint string
        sanitized_endpoint = endpoint.removesuffix("/")

        # Set endpoint
        self._endpoint = sanitized_endpoint

    def _get_auth_from_env(self) -> None:
        """
        Get authentication parameters from the env.

        Returns
        -------
        tuple[str, str], str, None
            The authentication parameters.
        """
        # User for future entity ownership
        self._user = os.getenv("DIGITALHUB_CORE_USER")

        # Prioritize token over user/password
        token = os.getenv("DIGITALHUB_CORE_TOKEN")
        if token is not None:
            self._auth_type = "oauth2"
            self._access_token = token
            return

        password = os.getenv("DIGITALHUB_CORE_PASSWORD")
        if self._user is not None and password is not None:
            self._auth_type = "basic"
            self._password = password
            return

    @staticmethod
    def is_local() -> bool:
        """
        Declare if Client is local.

        Returns
        -------
        bool
            False
        """
        return False
