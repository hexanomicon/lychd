"""Trusted executable discovery for host-readiness probes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from lychd.system.host_tools import trusted_host_tool


@dataclass(frozen=True, slots=True)
class HostReadinessTools:
    """Trusted executables used by the read-only probes."""

    systemctl: str | None
    podman: str | None
    quadlet_user_generator: str | None
    findmnt: str | None
    btrfs: str | None
    chattr: str | None
    lsattr: str | None
    getenforce: str | None

    @classmethod
    def discover(
        cls,
        *,
        lookup: Callable[[str], str | None] = trusted_host_tool,
    ) -> HostReadinessTools:
        """Resolve the complete toolchain through trusted host paths."""
        return cls(
            systemctl=lookup("systemctl"),
            podman=lookup("podman"),
            quadlet_user_generator=lookup("podman-user-generator"),
            findmnt=lookup("findmnt"),
            btrfs=lookup("btrfs"),
            chattr=lookup("chattr"),
            lsattr=lookup("lsattr"),
            getenforce=lookup("getenforce"),
        )


__all__ = ("HostReadinessTools",)
