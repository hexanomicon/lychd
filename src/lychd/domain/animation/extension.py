from __future__ import annotations

from lychd.config.runes.extension import RuneConfigStore
from lychd.domain.animation.services.adapters.contracts import (
    PortalDefinition,
    PortalRuntimeFactory,
    SoulstoneDefinition,
    SoulstoneRuntimeAdapter,
)
from lychd.extensions.base import ExtensionStore


class SoulstoneStore(ExtensionStore):
    """Store for local/model runtime Soulstone definitions."""

    def __init__(self, runes: RuneConfigStore) -> None:
        """Create an empty Soulstone store bound to the shared rune store."""
        self._runes = runes
        self._definitions: list[SoulstoneDefinition] = []

    @property
    def definitions(self) -> tuple[SoulstoneDefinition, ...]:
        """Registered Soulstone definitions."""
        return tuple(self._definitions)

    @property
    def runtime_adapters(self) -> tuple[SoulstoneRuntimeAdapter, ...]:
        """Runtime adapters contributed by registered Soulstone definitions."""
        return tuple(definition.runtime_adapter for definition in self._definitions)

    def add(self, definition: SoulstoneDefinition) -> None:
        """Register one Soulstone definition and its RuneConfig schema."""
        runtime = getattr(definition.runtime_adapter, "runtime", None)
        for existing in self._definitions:
            existing_runtime = getattr(existing.runtime_adapter, "runtime", None)
            if runtime is not None and existing_runtime == runtime:
                return
            if existing.rune_schema is definition.rune_schema and type(existing.runtime_adapter) is type(
                definition.runtime_adapter
            ):
                return
        self._definitions.append(definition)
        self._runes.add_schema(definition.rune_schema)


class PortalStore(ExtensionStore):
    """Store for remote/API model integrations (mirrors SoulstoneStore)."""

    def __init__(self, runes: RuneConfigStore) -> None:
        """Create an empty Portal store bound to the shared rune store."""
        self._runes = runes
        self._definitions: list[PortalDefinition] = []

    @property
    def definitions(self) -> tuple[PortalDefinition, ...]:
        """Registered Portal definitions."""
        return tuple(self._definitions)

    @property
    def factories(self) -> tuple[PortalRuntimeFactory, ...]:
        """Portal runtime factories contributed by registered Portal definitions."""
        return tuple(definition.factory for definition in self._definitions)

    def add(self, definition: PortalDefinition) -> None:
        """Register one Portal definition and its RuneConfig schema (first-wins dedup)."""
        for existing in self._definitions:
            if existing.rune_schema is definition.rune_schema and type(existing.factory) is type(definition.factory):
                return
        self._definitions.append(definition)
        self._runes.add_schema(definition.rune_schema)
