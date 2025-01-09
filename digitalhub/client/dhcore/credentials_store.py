from __future__ import annotations


class CredentialsStore:
    """
    Credentials store to store and retrieve credentials.
    """

    def __init__(self) -> None:
        self._credentials: dict[str, str] = {}

    def set_credentials(self, key: str, value: str) -> None:
        """
        Set credentials.

        Parameters
        ----------
        key : str
            The key of the credentials.
        value : str
            The value of the credentials.
        """
        self._credentials[key] = value

    def get_credentials(self, key: str) -> str | None:
        """
        Get credentials.

        Parameters
        ----------
        key : str
            The key of the credentials.

        Returns
        -------
        str | None
            The value of the credentials.
        """
        return self._credentials.get(key)

    def get_all_credentials(self) -> dict[str, str]:
        """
        Get all credentials.

        Returns
        -------
        dict[str, str]
            The credentials.
        """
        return self._credentials
