from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from lychd.config.runes.base import RuneConfig
from lychd.extensions.base import ExtensionStore


class RuneConfigStore(ExtensionStore):
    """Store for active extension-owned TOML schemas."""

    def __init__(self, *, current_provider: Callable[[], str] | None = None) -> None:
        """Create an empty rune schema store."""
        super().__init__()
        self._current_provider = current_provider or (lambda: "direct")
        self._schemas: list[type[RuneConfig]] = []
        self._owners: dict[type[RuneConfig], str] = {}
        self._anchors: dict[Path, tuple[type[RuneConfig], str]] = {}

    @property
    def rune_schemas(self) -> tuple[type[RuneConfig], ...]:
        """Registered rune schemas."""
        return tuple(self._schemas)

    def add_schema(self, schema: type[RuneConfig]) -> None:
        """Register one schema and reserve its exact filesystem anchor."""
        self._require_mutable()
        provider_id = self._current_provider()
        existing_owner = self._owners.get(schema)
        if existing_owner is not None:
            if existing_owner == provider_id:
                return
            msg = (
                f"Rune schema {schema.__name__} from {provider_id!r} conflicts with "
                f"the schema already registered by {existing_owner!r}."
            )
            raise ValueError(msg)

        anchor = schema.relative_path
        existing_anchor = self._anchors.get(anchor)
        if existing_anchor is not None:
            existing_schema, anchor_owner = existing_anchor
            msg = (
                f"Rune anchor '{anchor}' for {schema.__name__} from {provider_id!r} conflicts with "
                f"{existing_schema.__name__} registered by {anchor_owner!r}."
            )
            raise ValueError(msg)

        self._schemas.append(schema)
        self._owners[schema] = provider_id
        self._anchors[anchor] = (schema, provider_id)
