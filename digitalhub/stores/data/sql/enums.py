# SPDX-FileCopyrightText: © 2025 DSLab - Fondazione Bruno Kessler
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from enum import Enum


class SqlStoreEnv(Enum):
    """
    SqlStore environment
    """

    HOST = "DB_HOST"
    PORT = "DB_PORT"
    USERNAME = "DB_USERNAME"
    PASSWORD = "DB_PASSWORD"
    DATABASE = "DB_DATABASE"
    PG_SCHEMA = "DB_SCHEMA"
