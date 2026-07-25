"""Typed evidence shared by host-readiness probes and CLI presentation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ReadinessSection(StrEnum):
    """Stable presentation groups for one host-foundation report."""

    FOUNDATION = "HOST FOUNDATION"
    BINDING_SITES = "BINDING SITES"


class ReadinessState(StrEnum):
    """Evidence strength without conflating presence with readiness."""

    VERIFIED = "verified"
    PLANNED = "planned"
    OPTIONAL = "optional"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class HostReadinessItem:
    """One immutable host capability or binding-site observation."""

    key: str
    label: str
    section: ReadinessSection
    state: ReadinessState
    detail: str
    required_for_bind: bool = False
    target: Path | None = None

    @classmethod
    def failed(
        cls,
        *,
        key: str,
        label: str,
        detail: str,
        required: bool = False,
        section: ReadinessSection = ReadinessSection.FOUNDATION,
        target: Path | None = None,
    ) -> HostReadinessItem:
        """Create a blocked required item or unknown optional observation."""
        return cls(
            key=key,
            label=label,
            section=section,
            state=ReadinessState.BLOCKED if required else ReadinessState.UNKNOWN,
            detail=detail,
            required_for_bind=required,
            target=target,
        )


@dataclass(frozen=True, slots=True)
class HostReadinessReport:
    """Stable host evidence rendered by initialization."""

    items: tuple[HostReadinessItem, ...]

    @property
    def ready_for_bind(self) -> bool:
        """Return whether every required capability is verified now.

        This proves only local host foundation and prepared Binding sites. It
        does not prove configuration, secrets, generated units, containers,
        migrations, database health, or model readiness.
        """
        required = tuple(item for item in self.items if item.required_for_bind)
        return bool(required) and all(item.state is ReadinessState.VERIFIED for item in required)

    @property
    def ready_after_init(self) -> bool:
        """Return whether init can prepare the only unverified required sites."""
        required = tuple(item for item in self.items if item.required_for_bind)
        return bool(required) and all(
            item.state in {ReadinessState.VERIFIED, ReadinessState.PLANNED}
            for item in required
        )

    def item(self, key: str) -> HostReadinessItem:
        """Return one exact report item or fail on a programming error."""
        matches = tuple(item for item in self.items if item.key == key)
        if len(matches) != 1:
            message = f"Host readiness report contains {len(matches)} items named {key!r}."
            raise LookupError(message)
        return matches[0]


__all__ = (
    "HostReadinessItem",
    "HostReadinessReport",
    "ReadinessSection",
    "ReadinessState",
)
