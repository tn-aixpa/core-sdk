from __future__ import annotations

import os

from digitalhub.configurator.credentials_store import CredentialsStore
from digitalhub.configurator.ini_module import load_from_config, write_config

DEFAULT_SET = "DEFAULT"


class Configurator:
    """
    Configurator object used to configure clients and store credentials.
    """

    def __init__(self) -> None:
        # Store
        self._creds_store = CredentialsStore()

        # Current credentials set (DEFAULT by default)
        self._profile_creds = DEFAULT_SET

    ##############################
    # Public methods
    ##############################

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
        return load_from_config(self._profile_creds, var)

    def _write_env(self, key_to_exclude: list[str] | None = None) -> None:
        """
        Write the env variables to the .dhcore file.
        It will overwrite any existing env variables.

        Returns
        -------
        None
        """
        if key_to_exclude is None:
            key_to_exclude = []
        creds = self._get_all_cred()
        creds = {k: v for k, v in creds.items() if k not in key_to_exclude}
        write_config(creds, DEFAULT_SET, self._profile_creds)

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
        self._creds_store.set(self._profile_creds, key, value)

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
        return self._creds_store.get(self._profile_creds, key)

    def _get_all_cred(self) -> dict:
        """
        Get all the credentials.

        Returns
        -------
        dict
            The credentials.
        """
        return self._creds_store.get_all(self._profile_creds)
