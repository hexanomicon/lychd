"""Shaped extension store for delivered delegated-agent runtimes."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from lychd.domain.delegation.ports import DelegatedAgentRuntime
from lychd.extensions.base import ExtensionStore

_RUNTIME_ID: Final = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


@dataclass(frozen=True, slots=True)
class DelegatedRuntimeDefinition:
    """One executable delegated runtime exposed by an extension."""

    runtime_id: str
    display_name: str
    limitations: tuple[str, ...]
    runtime_adapter: DelegatedAgentRuntime

    def __post_init__(self) -> None:
        """Reject ambiguous identity or adapter mismatches."""
        if _RUNTIME_ID.fullmatch(self.runtime_id) is None:
            msg = f"Invalid delegated runtime id {self.runtime_id!r}; use lower-kebab-case."
            raise ValueError(msg)
        if not self.display_name.strip():
            msg = f"Delegated runtime {self.runtime_id!r} requires a display name."
            raise ValueError(msg)
        if any(not limitation.strip() for limitation in self.limitations):
            msg = f"Delegated runtime {self.runtime_id!r} contains an empty limitation."
            raise ValueError(msg)
        if self.runtime_adapter.name != self.runtime_id:
            msg = f"Delegated runtime adapter name does not match definition {self.runtime_id!r}."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class RegisteredDelegatedRuntime:
    """One delivered runtime with host-assigned extension provenance."""

    provider_id: str
    definition: DelegatedRuntimeDefinition


class DelegatedRuntimeStore(ExtensionStore):
    """Strict catalogue of executable delegated runtimes."""

    def __init__(self, *, current_provider: Callable[[], str]) -> None:
        """Create an empty store bound to the active extension provenance."""
        super().__init__()
        self._current_provider = current_provider
        self._registrations: dict[str, RegisteredDelegatedRuntime] = {}

    @property
    def registrations(self) -> tuple[RegisteredDelegatedRuntime, ...]:
        return tuple(self._registrations.values())

    @property
    def runtime_adapters(self) -> Mapping[str, DelegatedAgentRuntime]:
        return MappingProxyType(
            {
                registration.definition.runtime_id: registration.definition.runtime_adapter
                for registration in self._registrations.values()
            }
        )

    def add(self, definition: DelegatedRuntimeDefinition) -> None:
        self._require_mutable()
        provider_id = self._current_provider()
        existing = self._registrations.get(definition.runtime_id)
        if existing is not None:
            msg = (
                f"Delegated runtime {definition.runtime_id!r} from {provider_id!r} conflicts with "
                f"the runtime already registered by {existing.provider_id!r}."
            )
            raise ValueError(msg)
        self._registrations[definition.runtime_id] = RegisteredDelegatedRuntime(
            provider_id=provider_id,
            definition=definition,
        )


__all__ = (
    "DelegatedRuntimeDefinition",
    "DelegatedRuntimeStore",
    "RegisteredDelegatedRuntime",
)
