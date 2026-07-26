"""Typed evidence shared by host-readiness probes and CLI presentation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from lychd.system.binding_sites import (
    AttestedBindingSite,
    AttestedBindingSites,
)
from lychd.system.host_foundation import (
    BINDING_FOUNDATION_READINESS_KEYS,
    QUADLET_SOURCES_READINESS_KEY,
    SYSTEMD_USER_UNITS_READINESS_KEY,
)
from lychd.system.host_tools import TrustedExecutable
from lychd.system.readiness.tools import HostReadinessTools


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


class HostFoundationError(RuntimeError):
    """The current host evidence cannot authorize binding effects."""


@dataclass(frozen=True, slots=True)
class HostReadinessItem:
    """One immutable host capability or binding-site observation."""

    key: str
    label: str
    section: ReadinessSection
    state: ReadinessState
    detail: str
    required_for_bind: bool = False
    repairable_by_init: bool = False
    target: Path | None = None
    site_identity: AttestedBindingSite | None = None

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
class BindingFoundation:
    """Exact host capabilities proved usable by the complete bind foundation."""

    systemctl: TrustedExecutable
    podman: TrustedExecutable
    quadlet_user_generator: TrustedExecutable
    sites: AttestedBindingSites

    @property
    def systemctl_bin(self) -> str:
        """Return the already-attested systemctl command path."""
        return self.systemctl.path

    @property
    def podman_bin(self) -> str:
        """Return the already-attested Podman command path."""
        return self.podman.path

    @property
    def quadlet_user_generator_bin(self) -> str:
        """Return the already-attested Quadlet generator command path."""
        return self.quadlet_user_generator.path


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
        return bool(required) and all(self._initializable(item) for item in required)

    @staticmethod
    def _initializable(item: HostReadinessItem) -> bool:
        """Return whether one bind gate is ready or an init-repairable site."""
        return item.state is ReadinessState.VERIFIED or (
            item.state is ReadinessState.PLANNED and item.repairable_by_init
        )

    def item(self, key: str) -> HostReadinessItem:
        """Return one exact report item or fail on a programming error."""
        matches = tuple(item for item in self.items if item.key == key)
        if len(matches) != 1:
            message = f"Host readiness report contains {len(matches)} items named {key!r}."
            raise LookupError(message)
        return matches[0]


@dataclass(frozen=True, slots=True)
class HostFoundationInspection:
    """Readiness presentation plus the trusted discoveries behind it."""

    report: HostReadinessReport
    tools: HostReadinessTools

    def require_ready_for_bind(self) -> BindingFoundation:
        """Refine read-only evidence into the exact authority bind may use."""
        unverified = tuple(
            item.label
            for item in self.report.items
            if item.required_for_bind and item.state is not ReadinessState.VERIFIED
        )
        if unverified:
            message = "Host foundation is not ready for binding: " + ", ".join(
                unverified,
            )
            raise HostFoundationError(message)
        try:
            gates = {key: self.report.item(key) for key in BINDING_FOUNDATION_READINESS_KEYS}
        except LookupError as exc:
            message = "Host readiness omitted a required binding gate."
            raise HostFoundationError(message) from exc
        blocked = tuple(
            item.label
            for item in gates.values()
            if (not item.required_for_bind or item.state is not ReadinessState.VERIFIED)
        )
        if blocked:
            message = "Host foundation is not ready for binding: " + ", ".join(blocked)
            raise HostFoundationError(message)
        tools = self.tools
        if tools.systemctl is None or tools.podman is None or tools.quadlet_user_generator is None:
            message = "Verified host readiness omitted required trusted tool evidence."
            raise HostFoundationError(message)
        quadlet_site = gates[QUADLET_SOURCES_READINESS_KEY].site_identity
        systemd_user_site = gates[SYSTEMD_USER_UNITS_READINESS_KEY].site_identity
        if quadlet_site is None or systemd_user_site is None:
            message = "Verified binding-site evidence omitted its exact kernel identity."
            raise HostFoundationError(message)
        if (
            gates[QUADLET_SOURCES_READINESS_KEY].target != quadlet_site.path
            or gates[SYSTEMD_USER_UNITS_READINESS_KEY].target != systemd_user_site.path
        ):
            message = "Verified binding-site target disagrees with its exact kernel identity."
            raise HostFoundationError(message)
        return BindingFoundation(
            systemctl=tools.systemctl,
            podman=tools.podman,
            quadlet_user_generator=tools.quadlet_user_generator,
            sites=AttestedBindingSites(
                quadlet=quadlet_site,
                systemd_user=systemd_user_site,
            ),
        )


__all__ = (
    "BindingFoundation",
    "HostFoundationError",
    "HostFoundationInspection",
    "HostReadinessItem",
    "HostReadinessReport",
    "ReadinessSection",
    "ReadinessState",
)
