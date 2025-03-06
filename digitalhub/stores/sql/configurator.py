from __future__ import annotations

from digitalhub.configurator.configurator import configurator
from digitalhub.stores.sql.enums import SqlStoreEnv
from digitalhub.stores.sql.models import SqlStoreConfig
from digitalhub.utils.exceptions import StoreError


class SqlStoreConfigurator:
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
        if config is None:
            self._get_config()
        else:
            config: SqlStoreConfig = SqlStoreConfig(**config)
            for pair in [
                (SqlStoreEnv.USERNAME.value, config.user),
                (SqlStoreEnv.PASSWORD.value, config.password),
                (SqlStoreEnv.HOST.value, config.host),
                (SqlStoreEnv.PORT.value, config.port),
                (SqlStoreEnv.DATABASE.value, config.database),
            ]:
                configurator.set_credential(*pair)

    def get_sql_conn_string(self) -> str:
        """
        Get the connection string from environment variables.

        Returns
        -------
        str
            The connection string.
        """
        creds = configurator.get_all_credentials()
        try:
            user = creds[SqlStoreEnv.USERNAME.value]
            password = creds[SqlStoreEnv.PASSWORD.value]
            host = creds[SqlStoreEnv.HOST.value]
            port = creds[SqlStoreEnv.PORT.value]
            database = creds[SqlStoreEnv.DATABASE.value]
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"
        except KeyError as e:
            raise StoreError(f"Missing credentials for SQL store. {str(e)}")

    def _get_config(self) -> None:
        """
        Get the credentials from environment variables.

        Returns
        -------
        None
        """
        user = configurator.load_var(SqlStoreEnv.USERNAME.value)
        password = configurator.load_var(SqlStoreEnv.PASSWORD.value)
        host = configurator.load_var(SqlStoreEnv.HOST.value)
        port = configurator.load_var(SqlStoreEnv.PORT.value)
        database = configurator.load_var(SqlStoreEnv.DATABASE.value)
        if user is None or password is None or host is None or port is None or database is None:
            raise StoreError("Missing credentials for SQL store.")
        configurator.set_credential(SqlStoreEnv.USERNAME.value, user)
        configurator.set_credential(SqlStoreEnv.PASSWORD.value, password)
        configurator.set_credential(SqlStoreEnv.HOST.value, host)
        configurator.set_credential(SqlStoreEnv.PORT.value, port)
        configurator.set_credential(SqlStoreEnv.DATABASE.value, database)
