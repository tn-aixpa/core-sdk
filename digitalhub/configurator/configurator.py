from __future__ import annotations

import os

from digitalhub.configurator.credentials_store import CredentialsStore
from digitalhub.configurator.ini_module import load_from_config, write_config


class EnvConfigurator:
    """
    Configurator object used to configure clients and store credentials.
    """

    def __init__(self) -> None:
        # Store
        self._creds_store = CredentialsStore()

        # Current credentials set (__default by default)
        self._environment = "__default"

    ##############################
    # Public methods
    ##############################

    def set_current_env(self, creds_set: str) -> None:
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
        self._environment = creds_set

    def get_current_env(self) -> str:
        """
        Get the current credentials set.

        Returns
        -------
        str
            Credentials set name.
        """
        return self._environment

    ##############################
    # Private methods
    ##############################

    def load_var(self, var_name: str) -> str | None:
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
        var = self.get_credentials(var_name)
        if var is None:
            var = self.load_from_env(var_name)
        if var is None:
            var = self.load_from_config(var_name)
        return var

    def load_from_env(self, var: str) -> str | None:
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

    def load_from_config(self, var: str) -> str | None:
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
        return load_from_config(var)

    def write_env(self, key_to_include: list[str] | None = None) -> None:
        """
        Write the env variables to the .dhcore file.
        It will overwrite any existing env variables.

        Parameters
        ----------
        key_to_include : list[str]
            List of keys to include.

        Returns
        -------
        None
        """
        if key_to_include is None:
            key_to_include = []
        creds = self.get_cred_list(key_to_include)
        write_config(creds, self._environment)

    ##############################
    # Credentials store methods
    ##############################

    def set_credential(self, key: str, value: str) -> None:
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
        self._creds_store.set(self._environment, key, value)

    def get_credentials(self, key: str) -> dict:
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
        return self._creds_store.get(self._environment, key)

    def get_all_cred(self) -> dict:
        """
        Get all the credentials.

        Returns
        -------
        dict
            The credentials.
        """
        return self._creds_store.get_all(self._environment)

    def get_cred_list(self, keys: list[str]) -> list[str]:
        """
        Get the list of credentials.

        Parameters
        ----------
        keys : list[str]
            The list of keys.

        Returns
        -------
        list[str]
            The list of credentials.
        """
        return {k: v for k, v in self.get_all_cred().items() if k in keys}


configurator = EnvConfigurator()
