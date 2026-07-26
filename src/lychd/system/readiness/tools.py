"""Trusted executable discovery for host-readiness probes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from lychd.system.host_tools import (
    TrustedExecutable,
    trusted_executable,
    trusted_podman_user_generator_executable,
)


@dataclass(frozen=True, slots=True)
class HostReadinessTools:
    """Trusted executables used by the read-only probes."""

    systemctl: TrustedExecutable | None
    podman: TrustedExecutable | None
    quadlet_user_generator: TrustedExecutable | None
    findmnt: TrustedExecutable | None
    btrfs: TrustedExecutable | None
    chattr: TrustedExecutable | None
    lsattr: TrustedExecutable | None
    getenforce: TrustedExecutable | None

    @classmethod
    def discover(
        cls,
        *,
        lookup: Callable[[str], TrustedExecutable | None] = trusted_executable,
        generator_lookup: Callable[[], TrustedExecutable | None] | None = None,
    ) -> HostReadinessTools:
        """Resolve the complete toolchain through trusted host paths."""
        selected_generator_lookup = (
            trusted_podman_user_generator_executable
            if generator_lookup is None and lookup is trusted_executable
            else generator_lookup
        )
        return cls(
            systemctl=lookup("systemctl"),
            podman=lookup("podman"),
            quadlet_user_generator=(
                selected_generator_lookup()
                if selected_generator_lookup is not None
                else lookup("podman-user-generator")
            ),
            findmnt=lookup("findmnt"),
            btrfs=lookup("btrfs"),
            chattr=lookup("chattr"),
            lsattr=lookup("lsattr"),
            getenforce=lookup("getenforce"),
        )


__all__ = ("HostReadinessTools",)
