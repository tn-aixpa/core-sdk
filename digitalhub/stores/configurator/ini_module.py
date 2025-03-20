from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path

from digitalhub.utils.exceptions import ClientError

# File where to write DHCORE_ACCESS_TOKEN and DHCORE_REFRESH_TOKEN
# It's used because we inject the variables in jupyter env,
# but refresh token is only available once. Is it's used, we cannot
# overwrite it with coder, so we need to store the new one in a file,
# preserved for jupyter restart
ENV_FILE = Path.home() / ".dhcore.ini"


def load_from_config(var: str) -> str | None:
    """
    Load variable from config file.

    Parameters
    ----------
    profile : str
        Credentials set name.
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
        profile = cfg["DEFAULT"]["current_environment"]
        return cfg[profile].get(var)
    except KeyError:
        return


def write_config(creds: dict, environment: str) -> None:
    """
    Write the env variables to the .dhcore.ini file.
    It will overwrite any existing env variables.

    Parameters
    ----------
    creds : dict
        Credentials.
    environment : str
        Credentials set name.

    Returns
    -------
    None
    """
    try:
        cfg = ConfigParser()
        cfg.read(ENV_FILE)

        sections = cfg.sections()
        if environment not in sections:
            cfg.add_section(environment)

        cfg["DEFAULT"]["current_environment"] = environment
        for k, v in creds.items():
            cfg[environment][k] = v

        ENV_FILE.touch(exist_ok=True)
        with open(ENV_FILE, "w") as inifile:
            cfg.write(inifile)

    except Exception as e:
        raise ClientError(f"Failed to write env file: {e}")
