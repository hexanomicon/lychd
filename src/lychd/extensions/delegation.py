"""Shaped extension store for delegated-agent runtime definitions.

The catalogue separates discovery from execution. A definition may describe a
future adapter without making it runnable; only definitions carrying an admitted
runtime adapter appear in ``runtime_adapters``.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from lychd.domain.delegation.ports import DelegatedAgentRuntime
from lychd.extensions.base import ExtensionStore

_RUNTIME_ID: Final = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_EXECUTABLE_NAME: Final = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._+-]*$")


class DelegatedRuntimeTransport(StrEnum):
    """How a delegated runtime would cross the execution boundary."""

    REFERENCE = "reference"
    CLI = "cli"
    PROVIDER_API = "provider-api"


class DelegatedRuntimeDelivery(StrEnum):
    """Whether this source tree currently carries an executable adapter."""

    AVAILABLE = "available"
    DECLARED_ONLY = "declared-only"


@dataclass(frozen=True, slots=True)
class DelegatedRuntimeSecurity:
    """Security prerequisites for an effectful delegated runtime."""

    isolated_process: bool
    requires_nono: bool
    requires_provider_gate: bool
    permits_direct_provider_credentials: bool = False

    def __post_init__(self) -> None:
        """Keep direct provider credentials outside every guest definition."""
        if self.permits_direct_provider_credentials:
            msg = "Delegated runtimes may not expose direct provider credentials to a guest."
            raise ValueError(msg)
        if self.isolated_process != self.requires_nono:
            msg = "Every isolated delegated process requires nono, and nono is not claimed without one."
            raise ValueError(msg)
        if self.requires_provider_gate and not self.isolated_process:
            msg = "A delegated Provider Gate grant requires an isolated guest process."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class DelegatedRuntimeCommand:
    """Inert, locally verified CLI shape; this object launches nothing."""

    executable: str
    fixed_arguments: tuple[str, ...]
    prompt_via_stdin: bool
    evidence: str

    def __post_init__(self) -> None:
        """Reject shell-bearing or unverifiable command metadata."""
        if _EXECUTABLE_NAME.fullmatch(self.executable) is None:
            msg = "Delegated runtime executable must be a bare executable name."
            raise ValueError(msg)
        if not self.evidence.strip():
            msg = "Delegated runtime command metadata requires an evidence note."
            raise ValueError(msg)
        if any(
            not argument or "\x00" in argument or "\n" in argument or "\r" in argument
            for argument in self.fixed_arguments
        ):
            msg = "Delegated runtime command metadata contains an empty or control-bearing argument."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class DelegatedRuntimeDefinition:
    """One discoverable delegated runtime and its honest delivery boundary."""

    runtime_id: str
    display_name: str
    transport: DelegatedRuntimeTransport
    delivery: DelegatedRuntimeDelivery
    security: DelegatedRuntimeSecurity
    limitations: tuple[str, ...]
    command: DelegatedRuntimeCommand | None = None
    runtime_adapter: DelegatedAgentRuntime | None = None

    def __post_init__(self) -> None:
        """Reject definitions that could project an inert adapter as runnable."""
        self._validate_identity()
        self._validate_transport()
        self._validate_delivery()

    def _validate_identity(self) -> None:
        if _RUNTIME_ID.fullmatch(self.runtime_id) is None:
            msg = f"Invalid delegated runtime id {self.runtime_id!r}; use lower-kebab-case."
            raise ValueError(msg)
        if not self.display_name.strip():
            msg = f"Delegated runtime {self.runtime_id!r} requires a display name."
            raise ValueError(msg)
        if any(not limitation.strip() for limitation in self.limitations):
            msg = f"Delegated runtime {self.runtime_id!r} contains an empty limitation."
            raise ValueError(msg)
        if self.delivery is DelegatedRuntimeDelivery.DECLARED_ONLY and not self.limitations:
            msg = f"Declared-only delegated runtime {self.runtime_id!r} must state why it is unavailable."
            raise ValueError(msg)

    def _validate_transport(self) -> None:
        if self.transport is DelegatedRuntimeTransport.CLI and self.command is None:
            msg = f"CLI delegated runtime {self.runtime_id!r} requires inert command metadata."
            raise ValueError(msg)
        if self.transport is not DelegatedRuntimeTransport.CLI and self.command is not None:
            msg = f"Non-CLI delegated runtime {self.runtime_id!r} cannot carry command metadata."
            raise ValueError(msg)

    def _validate_delivery(self) -> None:
        runnable = self.runtime_adapter is not None
        if runnable != (self.delivery is DelegatedRuntimeDelivery.AVAILABLE):
            msg = f"Delegated runtime {self.runtime_id!r} delivery status does not match its adapter."
            raise ValueError(msg)
        if runnable and self.transport is not DelegatedRuntimeTransport.REFERENCE:
            msg = (
                f"Effectful delegated runtime {self.runtime_id!r} cannot become runnable through "
                "declarative registration alone; an attested supervisor binding is required."
            )
            raise ValueError(msg)
        if runnable and (
            self.security.isolated_process or self.security.requires_nono or self.security.requires_provider_gate
        ):
            msg = f"Reference delegated runtime {self.runtime_id!r} cannot claim effectful security boundaries."
            raise ValueError(msg)
        if self.runtime_adapter is not None and self.runtime_adapter.name != self.runtime_id:
            msg = f"Delegated runtime adapter name does not match definition {self.runtime_id!r}."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class RegisteredDelegatedRuntime:
    """One runtime definition with host-assigned extension provenance."""

    provider_id: str
    definition: DelegatedRuntimeDefinition


class DelegatedRuntimeStore(ExtensionStore):
    """Strict runtime catalogue assembled through ``ExtensionContext``."""

    def __init__(self, *, current_provider: Callable[[], str]) -> None:
        """Create an empty store bound to the manager provenance bracket."""
        self._current_provider = current_provider
        self._registrations: dict[str, RegisteredDelegatedRuntime] = {}

    @property
    def registrations(self) -> tuple[RegisteredDelegatedRuntime, ...]:
        """Definitions in deterministic registration order."""
        return tuple(self._registrations.values())

    @property
    def runtime_adapters(self) -> Mapping[str, DelegatedAgentRuntime]:
        """Immutable projection containing only honestly executable adapters."""
        return MappingProxyType(
            {
                registration.definition.runtime_id: registration.definition.runtime_adapter
                for registration in self._registrations.values()
                if registration.definition.runtime_adapter is not None
            }
        )

    def get(self, runtime_id: str) -> RegisteredDelegatedRuntime | None:
        """Return one definition by canonical runtime id."""
        return self._registrations.get(runtime_id)

    def add(self, definition: DelegatedRuntimeDefinition) -> None:
        """Register one definition under the active extension provenance bracket."""
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
    "DelegatedRuntimeCommand",
    "DelegatedRuntimeDefinition",
    "DelegatedRuntimeDelivery",
    "DelegatedRuntimeSecurity",
    "DelegatedRuntimeStore",
    "DelegatedRuntimeTransport",
    "RegisteredDelegatedRuntime",
)
