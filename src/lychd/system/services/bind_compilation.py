"""Pure declaration-to-request compilation for one bind generation."""

from __future__ import annotations

import secrets
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from lychd.system.services.bind import BindRequest

if TYPE_CHECKING:
    from lychd.config.runes.registry import RuneRegistry
    from lychd.config.settings.root import Settings
    from lychd.domain.animation.schemas import PortalConfig, SoulstoneConfig
    from lychd.domain.animation.services.adapters.contracts import RuntimePlan
    from lychd.extensions.host import AssembledExtensions


def required_secret_names_from_soulstones(
    soulstones: Sequence[SoulstoneConfig],
    runtime_plans: Sequence[RuntimePlan] = (),
) -> list[str]:
    """Collect every Rune-, control-, and adapter-planned Soulstone secret."""
    from lychd.system.schemas import podman_secret_source

    if runtime_plans and len(runtime_plans) != len(soulstones):
        msg = "Runtime plan count must match the Soulstone count"
        raise ValueError(msg)
    names: set[str] = set()
    for stone in soulstones:
        names.update(name for name in stone.secret_env_files.values() if name)
        names.update(stone.control_plane_secret_names)
    for plan in runtime_plans:
        names.update(podman_secret_source(spec) for spec in plan.secrets)
    return sorted(names)


def uncaged_control_plane_secret_names(
    soulstones: Sequence[SoulstoneConfig],
) -> tuple[str, ...]:
    """Return secrets that only the caged Vessel can receive from Podman."""
    return tuple(sorted({name for stone in soulstones for name in stone.control_plane_secret_names}))


def compile_bind_request(
    *,
    settings: Settings,
    extensions: AssembledExtensions,
    runes: RuneRegistry,
    soulstones: Sequence[SoulstoneConfig],
    portals: Sequence[PortalConfig],
    uncaged: bool,
) -> BindRequest:
    """Compile loaded declarations into one immutable application request."""
    from lychd.domain.animation.services.adapters.registry import (
        RuntimeAdapterRegistry,
    )
    from lychd.domain.animation.transmute import Transmuter

    runtime_planner = RuntimeAdapterRegistry(
        adapters=extensions.runtime_adapters,
        settings=settings,
    )
    runtime_plans = tuple(runtime_planner.plan(stone) for stone in soulstones)
    required_soulstone_secrets = required_secret_names_from_soulstones(
        soulstones,
        runtime_plans,
    )
    portal_secrets = {portal.api_key_secret_name for portal in portals if portal.api_key_secret_name is not None}
    manifests = Transmuter(
        settings=settings,
        runtime_planner=runtime_planner,
        contributors=extensions.quadlet_contributors,
    ).transmute_all(
        tuple(soulstones),
        portals=tuple(portals),
        runes=runes,
        runtime_plans=runtime_plans,
    )
    return BindRequest.compile(
        manifests=manifests,
        plain_units=_desired_plain_units(
            settings=settings,
            uncaged=uncaged,
        ),
        core_secret_factories={
            settings.server.web.secret_key_secret: (lambda: secrets.token_hex(32)),
            settings.server.database.password_secret: (lambda: secrets.token_urlsafe(16)),
        },
        required_secret_names=sorted(
            {
                *required_soulstone_secrets,
                *portal_secrets,
            }
        ),
    )


def _host_reactor_units(*, settings: Settings) -> dict[str, str]:
    """Render the host-only trigger/consumer into the desired plain-unit set."""
    from lychd.system.constants import (
        PATH_XDG_CACHE_HOME,
        PATH_XDG_CONFIG_HOME,
        PATH_XDG_DATA_HOME,
    )
    from lychd.system.services.reactor import (
        render_reactor_path_unit,
        render_reactor_service_unit,
    )

    executable = Path(sys.prefix) / "bin" / "lychd"
    environment = {
        "HOME": str(Path.home()),
        "XDG_CACHE_HOME": str(PATH_XDG_CACHE_HOME),
        "XDG_CONFIG_HOME": str(PATH_XDG_CONFIG_HOME),
        "XDG_DATA_HOME": str(PATH_XDG_DATA_HOME),
    }
    return {
        "lychd-reactor.service": render_reactor_service_unit(
            executable=executable,
            environment=environment,
        ),
        "lychd-reactor.path": render_reactor_path_unit(
            inbox_dir=settings.orchestration.switching.host_reactor_dir,
            journal_dir=settings.orchestration.switching.host_reactor_journal_dir,
        ),
    }


def _desired_plain_units(
    *,
    settings: Settings,
    uncaged: bool,
) -> dict[str, str]:
    """Compile the complete non-Quadlet unit set for one binding plan."""
    from lychd.domain.animation.transmute import transmute_uncaged_vessel

    plain_units = (
        _host_reactor_units(settings=settings) if settings.orchestration.switching.actuator == "host-reactor" else {}
    )
    if uncaged:
        service = transmute_uncaged_vessel(settings)
        plain_units[service.filename] = service.render()
    return plain_units


__all__ = [
    "compile_bind_request",
    "required_secret_names_from_soulstones",
    "uncaged_control_plane_secret_names",
]
