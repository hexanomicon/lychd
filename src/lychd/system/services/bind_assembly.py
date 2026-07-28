"""Concrete host-adapter assembly for the bind application use case."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lychd.system.services.bind import BindUseCase

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lychd.config.settings import SettingsSnapshot
    from lychd.system.readiness import BindingFoundation
    from lychd.system.services.binding_preflight import BindingPreflightService


def assemble_bind_use_case(
    *,
    foundation: BindingFoundation,
    preflight_service: BindingPreflightService,
    settings_snapshot: SettingsSnapshot,
    uncaged_control_plane_secrets: Sequence[str],
    uncaged: bool,
) -> BindUseCase:
    """Wire concrete host adapters behind the reusable bind use case."""
    from lychd.system.services.lifecycle.lock import LifecycleLock
    from lychd.system.services.scribe.facade import ScribeService
    from lychd.system.services.secrets import PodmanSecretStore
    from lychd.system.services.systemd import SystemdUserManager

    secret_store = PodmanSecretStore(foundation.podman_bin)
    scribe = ScribeService(
        expected_sites=foundation.sites,
    )

    def revalidate_foundation() -> BindingFoundation:
        settings = settings_snapshot.materialize()
        current = preflight_service.inspect(
            settings,
            uncaged=uncaged,
            uncaged_control_plane_secrets=(tuple(uncaged_control_plane_secrets) if uncaged else ()),
        )
        return current.require_ready()

    return BindUseCase(
        scribe=scribe,
        secrets=secret_store,
        systemd_factory=(
            lambda: SystemdUserManager(
                systemctl_bin=foundation.systemctl_bin,
            )
        ),
        foundation=foundation,
        foundation_probe=revalidate_foundation,
        lock_factory=LifecycleLock,
    )


__all__ = ["assemble_bind_use_case"]
