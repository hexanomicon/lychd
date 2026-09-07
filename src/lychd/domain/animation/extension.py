from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from lychd.config.runes.extension import RuneConfigStore
from lychd.domain.animation.services.adapters.contracts import (
    PortalDefinition,
    SoulstoneDefinition,
    SoulstoneRuntimeAdapter,
)
from lychd.extensions.base import ExtensionStore


@dataclass(frozen=True, slots=True)
class _RegisteredSoulstoneDefinition:
    """One Soulstone definition with host-assigned extension provenance."""

    registrant_id: str
    definition: SoulstoneDefinition


@dataclass(frozen=True, slots=True)
class _RegisteredPortalDefinition:
    """One Portal definition with host-assigned extension provenance."""

    registrant_id: str
    definition: PortalDefinition


class SoulstoneStore(ExtensionStore):
    """Store for local/model runtime Soulstone definitions."""

    def __init__(self, runes: RuneConfigStore, *, current_registrant: Callable[[], str] | None = None) -> None:
        """Create an empty Soulstone store bound to the shared rune store."""
        super().__init__()
        self._runes = runes
        self._current_registrant = current_registrant or (lambda: "core")
        self._registrations: list[_RegisteredSoulstoneDefinition] = []

    @property
    def definitions(self) -> tuple[SoulstoneDefinition, ...]:
        """Registered Soulstone definitions."""
        return tuple(registration.definition for registration in self._registrations)

    @property
    def runtime_adapters(self) -> tuple[SoulstoneRuntimeAdapter, ...]:
        """Runtime adapters contributed by registered Soulstone definitions."""
        return tuple(registration.definition.runtime_adapter for registration in self._registrations)

    def add(self, definition: SoulstoneDefinition) -> None:
        """Register one Soulstone definition and its RuneConfig schema."""
        self._require_mutable()
        registrant_id = self._current_registrant()
        runtime = getattr(definition.runtime_adapter, "runtime", None)
        for registration in self._registrations:
            existing = registration.definition
            existing_runtime = getattr(existing.runtime_adapter, "runtime", None)
            if existing == definition:
                if registration.registrant_id == registrant_id:
                    return
                msg = (
                    f"Soulstone definition for runtime {runtime!r} from {registrant_id!r} "
                    f"duplicates the definition registered by {registration.registrant_id!r}."
                )
                raise ValueError(msg)
            if (
                runtime is not None
                and existing_runtime == runtime
                and existing.rune_schema is definition.rune_schema
                and type(existing.runtime_adapter) is type(definition.runtime_adapter)
            ):
                if registration.registrant_id == registrant_id:
                    return
                msg = (
                    f"Soulstone runtime {runtime!r} from {registrant_id!r} duplicates "
                    f"the definition registered by {registration.registrant_id!r}."
                )
                raise ValueError(msg)
            if runtime is not None and existing_runtime == runtime:
                msg = (
                    f"Soulstone runtime {runtime!r} from {registrant_id!r} conflicts with the runtime "
                    f"registered by {registration.registrant_id!r}: existing adapter "
                    f"{type(existing.runtime_adapter).__name__} with schema {existing.rune_schema.__name__}; "
                    f"refusing {type(definition.runtime_adapter).__name__} with schema "
                    f"{definition.rune_schema.__name__}."
                )
                raise ValueError(msg)
            if existing.rune_schema is definition.rune_schema:
                msg = (
                    f"Soulstone schema {definition.rune_schema.__name__} from {registrant_id!r} conflicts with "
                    f"the schema registered by {registration.registrant_id!r}: existing adapter "
                    f"{type(existing.runtime_adapter).__name__}; refusing "
                    f"{type(definition.runtime_adapter).__name__}."
                )
                raise ValueError(msg)
        self._runes.add_schema(definition.rune_schema)
        self._registrations.append(_RegisteredSoulstoneDefinition(registrant_id=registrant_id, definition=definition))


class PortalStore(ExtensionStore):
    """Store for remote/API model integrations (mirrors SoulstoneStore)."""

    def __init__(self, runes: RuneConfigStore, *, current_registrant: Callable[[], str] | None = None) -> None:
        """Create an empty Portal store bound to the shared rune store."""
        super().__init__()
        self._runes = runes
        self._current_registrant = current_registrant or (lambda: "core")
        self._registrations: list[_RegisteredPortalDefinition] = []

    @property
    def definitions(self) -> tuple[PortalDefinition, ...]:
        """Registered Portal definitions."""
        return tuple(registration.definition for registration in self._registrations)

    def add(self, definition: PortalDefinition) -> None:
        """Register one exact Portal definition per RuneConfig schema."""
        self._require_mutable()
        registrant_id = self._current_registrant()
        for registration in self._registrations:
            existing = registration.definition
            if existing == definition:
                if registration.registrant_id == registrant_id:
                    return
                msg = (
                    f"Portal schema {definition.rune_schema.__name__} from {registrant_id!r} "
                    f"duplicates the definition registered by {registration.registrant_id!r}."
                )
                raise ValueError(msg)
            if existing.rune_schema is definition.rune_schema:
                existing_name = getattr(existing.factory, "__name__", type(existing.factory).__name__)
                incoming_name = getattr(definition.factory, "__name__", type(definition.factory).__name__)
                msg = (
                    f"Portal schema {definition.rune_schema.__name__} from {registrant_id!r} conflicts with "
                    f"the schema registered by {registration.registrant_id!r}: existing factory "
                    f"{existing_name}; refusing {incoming_name}."
                )
                raise ValueError(msg)
        self._runes.add_schema(definition.rune_schema)
        self._registrations.append(_RegisteredPortalDefinition(registrant_id=registrant_id, definition=definition))
