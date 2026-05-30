from __future__ import annotations

from lychd.config.runes.base import RuneConfig
from lychd.extensions.base import ExtensionStore


class RuneConfigStore(ExtensionStore):
    """Store for active extension-owned TOML schemas."""

    def __init__(self) -> None:
        """Create an empty rune schema store."""
        self._schemas: list[type[RuneConfig]] = []

    @property
    def rune_schemas(self) -> tuple[type[RuneConfig], ...]:
        """Registered rune schemas."""
        return tuple(self._schemas)

    def add_schema(self, schema: type[RuneConfig]) -> None:
        """Register a RuneConfig subclass exposed by this extension."""
        if schema not in self._schemas:
            self._schemas.append(schema)
