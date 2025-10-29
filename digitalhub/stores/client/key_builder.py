# SPDX-FileCopyrightText: © 2025 DSLab - Fondazione Bruno Kessler
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from digitalhub.stores.client.enums import ApiCategories


class ClientKeyBuilder:
    """
    Class that build the key of entities.
    """

    def build_key(self, category: str, *args, **kwargs) -> str:
        """
        Build key.

        Parameters
        ----------
        category : str
            Key category.
        *args : tuple
            Positional arguments.
        **kwargs : dict
            Keyword arguments.

        Returns
        -------
        str
            Key.
        """
        if category == ApiCategories.BASE.value:
            return self.base_entity_key(*args, **kwargs)
        return self.context_entity_key(*args, **kwargs)

    def base_entity_key(self, entity_id: str) -> str:
        """
        Build for base entity key.

        Parameters
        ----------
        entity_id : str
            Entity id.

        Returns
        -------
        str
            Key.
        """
        return f"store://{entity_id}"

    def context_entity_key(
        self,
        project: str,
        entity_type: str,
        entity_kind: str,
        entity_name: str,
        entity_id: str | None = None,
    ) -> str:
        """
        Build for context entity key.

        Parameters
        ----------
        project : str
            Project name.
        entity_type : str
            Entity type.
        entity_kind : str
            Entity kind.
        entity_name : str
            Entity name.
        entity_id : str
            Entity ID.

        Returns
        -------
        str
            Key.
        """
        if entity_id is None:
            return f"store://{project}/{entity_type}/{entity_kind}/{entity_name}"
        return f"store://{project}/{entity_type}/{entity_kind}/{entity_name}:{entity_id}"
