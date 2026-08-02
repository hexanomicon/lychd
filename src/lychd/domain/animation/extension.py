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
class RegisteredSoulstoneDefinition:
    """One Soulstone definition with host-assigned extension provenance."""

    provider_id: str
    definition: SoulstoneDefinition


@dataclass(frozen=True, slots=True)
class RegisteredPortalDefinition:
    """One Portal definition with host-assigned extension provenance."""

    provider_id: str
    definition: PortalDefinition


class SoulstoneStore(ExtensionStore):
    """Store for local/model runtime Soulstone definitions."""

    def __init__(self, runes: RuneConfigStore, *, current_provider: Callable[[], str] | None = None) -> None:
        """Create an empty Soulstone store bound to the shared rune store."""
        super().__init__()
        self._runes = runes
        self._current_provider = current_provider or (lambda: "direct")
        self._registrations: list[RegisteredSoulstoneDefinition] = []

    @property
    def registrations(self) -> tuple[RegisteredSoulstoneDefinition, ...]:
        """Registered definitions with exact provider ownership."""
        return tuple(self._registrations)

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
        provider_id = self._current_provider()
        runtime = getattr(definition.runtime_adapter, "runtime", None)
        for registration in self._registrations:
            existing = registration.definition
            existing_runtime = getattr(existing.runtime_adapter, "runtime", None)
            if existing == definition:
                if registration.provider_id == provider_id:
                    return
                msg = (
                    f"Soulstone definition for runtime {runtime!r} from {provider_id!r} "
                    f"duplicates the definition owned by {registration.provider_id!r}."
                )
                raise ValueError(msg)
            if (
                runtime is not None
                and existing_runtime == runtime
                and existing.rune_schema is definition.rune_schema
                and type(existing.runtime_adapter) is type(definition.runtime_adapter)
            ):
                if registration.provider_id == provider_id:
                    return
                msg = (
                    f"Soulstone runtime {runtime!r} from {provider_id!r} duplicates "
                    f"the definition owned by {registration.provider_id!r}."
                )
                raise ValueError(msg)
            if runtime is not None and existing_runtime == runtime:
                msg = (
                    f"Soulstone runtime {runtime!r} is already registered by "
                    f"{type(existing.runtime_adapter).__name__} with schema {existing.rune_schema.__name__}; "
                    f"refusing {type(definition.runtime_adapter).__name__} with schema "
                    f"{definition.rune_schema.__name__}."
                )
                raise ValueError(msg)
            if existing.rune_schema is definition.rune_schema:
                msg = (
                    f"Soulstone schema {definition.rune_schema.__name__} is already registered by "
                    f"{type(existing.runtime_adapter).__name__}; refusing "
                    f"{type(definition.runtime_adapter).__name__}."
                )
                raise ValueError(msg)
        self._runes.add_schema(definition.rune_schema)
        self._registrations.append(RegisteredSoulstoneDefinition(provider_id=provider_id, definition=definition))


class PortalStore(ExtensionStore):
    """Store for remote/API model integrations (mirrors SoulstoneStore)."""

    def __init__(self, runes: RuneConfigStore, *, current_provider: Callable[[], str] | None = None) -> None:
        """Create an empty Portal store bound to the shared rune store."""
        super().__init__()
        self._runes = runes
        self._current_provider = current_provider or (lambda: "direct")
        self._registrations: list[RegisteredPortalDefinition] = []

    @property
    def registrations(self) -> tuple[RegisteredPortalDefinition, ...]:
        """Registered definitions with exact provider ownership."""
        return tuple(self._registrations)

    @property
    def definitions(self) -> tuple[PortalDefinition, ...]:
        """Registered Portal definitions."""
        return tuple(registration.definition for registration in self._registrations)

    def add(self, definition: PortalDefinition) -> None:
        """Register one exact Portal definition per RuneConfig schema."""
        self._require_mutable()
        provider_id = self._current_provider()
        for registration in self._registrations:
            existing = registration.definition
            if existing == definition:
                if registration.provider_id == provider_id:
                    return
                msg = (
                    f"Portal schema {definition.rune_schema.__name__} from {provider_id!r} "
                    f"duplicates the definition owned by {registration.provider_id!r}."
                )
                raise ValueError(msg)
            if existing.rune_schema is definition.rune_schema:
                existing_name = getattr(existing.factory, "__name__", type(existing.factory).__name__)
                incoming_name = getattr(definition.factory, "__name__", type(definition.factory).__name__)
                msg = (
                    f"Portal schema {definition.rune_schema.__name__} is already registered by "
                    f"{existing_name}; refusing {incoming_name}."
                )
                raise ValueError(msg)
        self._runes.add_schema(definition.rune_schema)
        self._registrations.append(RegisteredPortalDefinition(provider_id=provider_id, definition=definition))
