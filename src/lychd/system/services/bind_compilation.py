"""Pure declaration-to-request compilation for one bind generation."""

from __future__ import annotations

import secrets
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from lychd.system.schemas import QuadletContainer, podman_secret_source
from lychd.system.services.bind import BindRequest

if TYPE_CHECKING:
    from lychd.config.runes.registry import RuneRegistry
    from lychd.config.settings.root import Settings
    from lychd.domain.animation.schemas import PortalConfig, SoulstoneConfig
    from lychd.domain.animation.services.adapters.contracts import RuntimePlan
    from lychd.domain.tether.compiler import TetherDeployment
    from lychd.domain.tether.models import TetherSnapshot
    from lychd.extensions.host import AssembledExtensions


def required_secret_names_from_soulstones(
    soulstones: Sequence[SoulstoneConfig],
    runtime_plans: Sequence[RuntimePlan] = (),
) -> list[str]:
    """Collect every Rune-, control-, and adapter-planned Soulstone secret."""
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


def compile_bind_request(
    *,
    settings: Settings,
    extensions: AssembledExtensions,
    runes: RuneRegistry,
    soulstones: Sequence[SoulstoneConfig],
    portals: Sequence[PortalConfig],
    tether_snapshot: TetherSnapshot | None = None,
    tether_runtime_root: Path | None = None,
    tether_config_root: Path | None = None,
    tether_consumer_uid: int | None = None,
    tether_forbidden_backend_addresses: tuple[str, ...] | None = None,
) -> BindRequest:
    """Compile the complete container binding generation from declared intent."""
    from lychd.domain.animation.capabilities import CapabilitySpec
    from lychd.domain.animation.conflicts import require_soulstone_capability_coverage
    from lychd.domain.animation.services.adapters.registry import (
        RuntimeAdapterRegistry,
    )
    from lychd.domain.animation.transmute import Transmuter

    runtime_planner = RuntimeAdapterRegistry(
        soulstone_registrations=extensions.soulstone_registrations,
    )
    runtime_plans = tuple(runtime_planner.plan(stone) for stone in soulstones)
    capability_specs: list[CapabilitySpec] = []
    for stone in soulstones:
        runtime = runtime_planner.build_runtime(stone)
        if runtime is not None:
            capability_specs.extend(runtime_planner.build_capability_specs(runtime))
    require_soulstone_capability_coverage(
        soulstones,
        capability_animator_names=(spec.animator_name for spec in capability_specs),
    )
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
    tether = _compile_tether_contribution(
        settings=settings,
        extensions=extensions,
        runes=runes,
        snapshot=tether_snapshot,
        runtime_root=tether_runtime_root,
        config_root=tether_config_root,
        consumer_uid=tether_consumer_uid,
        forbidden_backend_addresses=tether_forbidden_backend_addresses,
    )
    if tether is not None:
        existing_secrets = {
            podman_secret_source(spec)
            for manifest in manifests
            if isinstance(manifest, QuadletContainer)
            for spec in manifest.secrets
        }
        if existing_secrets.intersection(tether.required_secrets):
            msg = "Tether credentials cannot alias Core or other application credentials"
            raise ValueError(msg)
        manifests.extend(tether.manifests)
        if tether.consumer_mount is not None:
            manifests = [
                manifest.model_copy(update={"volumes": [*manifest.volumes, tether.consumer_mount]})
                if isinstance(manifest, QuadletContainer) and manifest.container_name == "lychd-vessel"
                else manifest
                for manifest in manifests
            ]
    core_secret_factories = {
        settings.server.web.secret_key_secret: (lambda: secrets.token_hex(32)),
        settings.server.database.password_secret: (lambda: secrets.token_urlsafe(16)),
        settings.server.database.runtime_password_secret: (lambda: secrets.token_urlsafe(32)),
        settings.server.database.phoenix_password_secret: (lambda: secrets.token_urlsafe(32)),
        settings.server.web.access_password_secret: (lambda: secrets.token_urlsafe(32)),
    }
    if tether is not None and set(core_secret_factories).intersection(tether.required_secrets):
        msg = "Tether credentials cannot use a Core-generated secret name"
        raise ValueError(msg)
    manifest_secrets = {
        podman_secret_source(spec)
        for manifest in manifests
        if isinstance(manifest, QuadletContainer)
        for spec in manifest.secrets
    }
    # Only emitted references inherit generation authority; explicit operator
    # requirements must retain BindRequest's core/operator overlap refusal.
    manifest_requirements = manifest_secrets.difference(core_secret_factories)
    return BindRequest.compile(
        manifests=manifests,
        plain_units=_desired_plain_units(settings=settings),
        core_secret_factories=core_secret_factories,
        tether=tether,
        required_secret_names=sorted(
            {
                *required_soulstone_secrets,
                *portal_secrets,
                *manifest_requirements,
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
) -> dict[str, str]:
    """Compile the complete non-Quadlet unit set for one binding plan."""
    return _host_reactor_units(settings=settings) if settings.orchestration.switching.actuator == "host-reactor" else {}


__all__ = [
    "compile_bind_request",
    "required_secret_names_from_soulstones",
]


def _compile_tether_contribution(
    *,
    settings: Settings,
    extensions: AssembledExtensions,
    runes: RuneRegistry,
    snapshot: TetherSnapshot | None,
    runtime_root: Path | None,
    config_root: Path | None,
    consumer_uid: int | None,
    forbidden_backend_addresses: tuple[str, ...] | None,
) -> TetherDeployment | None:
    """Require explicit current host authority for the one trusted Tether compiler."""
    from lychd.domain.tether.compiler import compile_tether
    from lychd.domain.tether.models import TetherRune

    rune = runes.one_or_none(TetherRune)
    if rune is None:
        if snapshot is not None:
            msg = "Tether admission requires its selected Rune"
            raise ValueError(msg)
        return None
    if "tether" not in settings.extensions.builtins or TetherRune not in extensions.rune_schemas:
        msg = "Tether Rune was not registered by its selected native extension"
        raise ValueError(msg)
    if snapshot is None or runtime_root is None or config_root is None or consumer_uid is None:
        msg = "Tether bind requires explicit current admission and owned projection roots"
        raise ValueError(msg)
    return compile_tether(
        rune=rune,
        snapshot=snapshot,
        runtime_root=runtime_root,
        config_root=config_root,
        core_web_port=settings.server.port,
        consumer_uid=consumer_uid,
        forbidden_backend_addresses=forbidden_backend_addresses,
    )
