"""Domain transmutation from animator runes into concrete Quadlet manifests.

This module is pure domain logic: it computes Quadlet data models but performs
no filesystem writes or host mutations.
"""

from __future__ import annotations

import os
import shlex
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final, Protocol

from lychd.config.settings.root import get_settings
from lychd.extensions.base import ExtensionStore
from lychd.system.constants import (
    CONTAINER_LYCHD_PORT,
    CONTAINER_POSTGRES_PORT,
    PATH_CODEX_ROOT,
    PATH_CORE_DIR,
    PATH_CRYPT_ROOT,
    PATH_EXTENSIONS_DIR,
    PATH_LAB_DIR,
    PATH_POSTGRES_ROOT_DIR,
    PATH_POSTGRESS_DATA_DIR,
    PATH_SYSTEMD_UNITS_DIR,
    PATH_SYSTEMD_USER_UNITS_DIR,
)
from lychd.system.path_policy import paths_overlap
from lychd.system.schemas import (
    MountData,
    QuadletBase,
    QuadletContainer,
    QuadletPod,
    QuadletTarget,
    SystemdService,
    podman_secret_source,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lychd.config.runes.registry import RuneRegistry
    from lychd.config.settings.root import Settings
    from lychd.domain.animation.schemas import PortalConfig, SoulstoneConfig
    from lychd.domain.animation.services.adapters.contracts import RuntimePlan, SoulstoneRuntimePlanner

MIN_COVEN_MEMBERS: Final[int] = 2
LYCHD_POD_QUADLET: Final[str] = "lychd.pod"
LYCHD_POD_SERVICE: Final[str] = "lychd-pod.service"


def _normalize_mount_path(path: Path, *, stone_name: str, side: str) -> Path:
    """Normalize an absolute mount endpoint, expanding ``~`` on the host side."""
    try:
        candidate = path.expanduser() if side == "host" else path
    except RuntimeError as exc:
        msg = f"Soulstone '{stone_name}' mount {side} path is not valid: {path}"
        raise ValueError(msg) from exc
    path_text = os.fspath(candidate)
    if "%" in path_text or "\\" in path_text or any(not char.isprintable() for char in path_text):
        msg = f"Soulstone '{stone_name}' mount {side} path contains unsafe systemd characters"
        raise ValueError(msg)
    if not candidate.is_absolute():
        msg = f"Soulstone '{stone_name}' mount {side} path must be absolute: {path}"
        raise ValueError(msg)
    normalized = os.path.normpath(candidate)
    if normalized.startswith("//"):
        normalized = f"/{normalized.lstrip('/')}"
    return Path(normalized)


def _resolve_host_path(path: Path, *, stone_name: str) -> Path:
    """Resolve existing host symlinks so an alias cannot evade control-root checks."""
    try:
        return path.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        msg = f"Soulstone '{stone_name}' mount host path cannot be resolved safely: {path}"
        raise ValueError(msg) from exc


def transmute_uncaged_vessel(settings: Settings) -> SystemdService:
    """Build the uncaged vessel unit from settings.

    Emits a :class:`SystemdService` model; writes nothing (pure domain). The
    exec line boots the server directly on the host via the native ``lychd serve``
    entrypoint, NOT a Quadlet.
    """
    exec_start = f"{Path(sys.prefix) / 'bin' / 'lychd'} serve --host 127.0.0.1 --port {settings.server.port}"
    return SystemdService(
        name="lychd-uncaged-vessel",
        description="LychD Vessel (uncaged)",
        exec_start=exec_start,
    )


@dataclass(frozen=True)
class QuadletContribution:
    """What one extension adds to the transmuted pod.

    By type this can add ONLY containers and pod ports -- it cannot mutate
    soulstone containers, core manifests, or targets (brief §8, property 4).
    """

    containers: list[QuadletContainer] = field(default_factory=list)
    pod_ports: list[str] = field(default_factory=list)  # "host:container"


@dataclass(frozen=True)
class TransmutationContext:
    """Everything a contributor may read. No mutation surface (frozen)."""

    settings: Settings
    soulstones: Sequence[SoulstoneConfig]
    portals: Sequence[PortalConfig]
    runes: RuneRegistry  # contributors find their own rune: runes.one_or_none(X)


class QuadletContributor(Protocol):
    """A contributor that appends containers/pod-ports to the transmuted pod."""

    def contribute(self, ctx: TransmutationContext) -> QuadletContribution:
        """Return this extension's additive contribution to the pod."""
        ...


class TransmutationStore(ExtensionStore):
    """Store for Quadlet contributions from extensions."""

    def __init__(self) -> None:
        """Create an empty contributor store."""
        self._contributors: list[QuadletContributor] = []

    def add_contributor(self, contributor: QuadletContributor) -> None:
        """Register one Quadlet contributor."""
        self._contributors.append(contributor)

    @property
    def contributors(self) -> tuple[QuadletContributor, ...]:
        """Registered Quadlet contributors, in registration order."""
        return tuple(self._contributors)


class Transmuter:
    """The Alchemist of Form.

    Responsible for:
    - Transmuting Soulstone Runes into Quadlet manifests.
    - Grouping Soulstones into operator-facing Coven targets.
    - Defining the core Quadlet manifests (Pod, Phylactery, Oculus).

    Physical exclusivity is deliberately NOT encoded as systemd ``Conflicts=``:
    only the Orchestrator may stop a runtime, after closing lease admission and
    draining it. Hidden systemd side effects would bypass that safety barrier.
    """

    def __init__(
        self,
        *,
        runtime_planner: SoulstoneRuntimePlanner,
        contributors: Sequence[QuadletContributor] = (),
    ) -> None:
        """Initialize transmuter with an injected runtime planner and contributors.

        INVARIANT (brief §8, property 4): ``QuadletContribution`` can add ONLY
        containers and pod ports; it can never mutate soulstone containers, core
        manifests, or targets. That is why ``AnimatorRegistry`` may build a
        Transmuter with NO contributors to extract soulstone containers -- a
        contribution cannot alter a soulstone container by type.
        """
        self._runtime_planner = runtime_planner
        self._contributors = tuple(contributors)

    def transmute_all(
        self,
        soulstones: Sequence[SoulstoneConfig],
        *,
        portals: Sequence[PortalConfig] | None = None,
        runes: RuneRegistry | None = None,
        runtime_plans: Sequence[RuntimePlan] | None = None,
    ) -> list[QuadletBase]:
        """Convert Soulstone Runes into a complete Quadlet manifest set."""
        from lychd.config.runes.registry import RuneRegistry

        settings = get_settings()
        resolved_portals = tuple(portals or ())
        resolved_runes = runes if runes is not None else RuneRegistry(())

        ctx = TransmutationContext(
            settings=settings,
            soulstones=soulstones,
            portals=resolved_portals,
            runes=resolved_runes,
        )
        contributions = [contributor.contribute(ctx) for contributor in self._contributors]
        resolved_runtime_plans = (
            list(runtime_plans)
            if runtime_plans is not None
            else [self._runtime_planner.plan(stone) for stone in soulstones]
        )
        if len(resolved_runtime_plans) != len(soulstones):
            msg = "Runtime plan count must match the Soulstone count"
            raise ValueError(msg)

        self._validate_secret_isolation(settings, resolved_portals, soulstones, resolved_runtime_plans)

        manifests: list[QuadletBase] = []

        # 1. The Sepulcher (Pod): core ports + contribution ports (contributor order).
        contribution_ports = [port for contribution in contributions for port in contribution.pod_ports]
        manifests.append(self._create_pod(settings, contribution_ports, resolved_runtime_plans))

        # 2. The Core Rituals (Vessel, Phylactery).
        manifests.extend(self._create_core_manifests(settings, resolved_portals, soulstones))

        # 3. Contribution containers (contributor order) -- e.g. the Oculus.
        for contribution in contributions:
            manifests.extend(contribution.containers)

        # 4. Calculate Covens.
        covens: dict[str, list[SoulstoneConfig]] = {}
        for stone in soulstones:
            for group in stone.groups:
                covens.setdefault(group, []).append(stone)

        # 5. Generate Coven Targets.
        for group, members in covens.items():
            if len(members) >= MIN_COVEN_MEMBERS:
                manifests.append(
                    QuadletTarget(
                        name=group,
                        description=f"LychD Coven: {group}",
                    )
                )

        # 6. Transmute Extension Soulstones. Covens group starts; they do not
        # encode hidden stop side effects. The Orchestrator owns exclusivity.
        manifests.extend(
            self._transmute_soulstone(stone, covens, settings, runtime_plan)
            for stone, runtime_plan in zip(soulstones, resolved_runtime_plans, strict=True)
        )

        return manifests

    def _create_pod(
        self,
        settings: Settings,
        extra_ports: list[str],
        runtime_plans: Sequence[RuntimePlan],
    ) -> QuadletPod:
        """Define the physical boundary of the Sepulcher.

        Core ports come first, then contribution ports append in contributor
        order -- a contributor can never reorder or shadow a core port.
        """
        ports = [
            f"127.0.0.1:{settings.server.port}:{CONTAINER_LYCHD_PORT}",
            f"127.0.0.1:{settings.server.database.port}:{CONTAINER_POSTGRES_PORT}",
            *(f"127.0.0.1:{mapping}" for mapping in extra_ports),
        ]
        shared_memory_requirements = [plan.pod_shared_memory_bytes for plan in runtime_plans]
        if any(requirement < 0 for requirement in shared_memory_requirements):
            msg = "Runtime plans cannot request a negative pod shared-memory capacity"
            raise ValueError(msg)
        shared_memory_bytes = sum(shared_memory_requirements)
        return QuadletPod(
            publish_ports=ports,
            shm_size=self._format_memory_size(shared_memory_bytes) if shared_memory_bytes else None,
        )

    def _format_memory_size(self, size_bytes: int) -> str:
        """Render an exact byte requirement in the largest integral Quadlet unit."""
        for suffix, scale in (("t", 1024**4), ("g", 1024**3), ("m", 1024**2), ("k", 1024)):
            if size_bytes % scale == 0:
                return f"{size_bytes // scale}{suffix}"
        return str(size_bytes)

    def _validate_secret_isolation(
        self,
        settings: Settings,
        portals: Sequence[PortalConfig],
        soulstones: Sequence[SoulstoneConfig],
        runtime_plans: Sequence[RuntimePlan],
    ) -> None:
        """Keep every data-plane credential distinct from privileged control secrets."""
        app_secret = settings.server.web.secret_key_secret
        db_secret = settings.server.database.password_secret
        if app_secret == db_secret:
            msg = "Core application-signing and database-password secrets must use distinct names"
            raise ValueError(msg)
        core_secrets = {app_secret, db_secret}
        portal_secrets = {portal.api_key_secret_name for portal in portals if portal.api_key_secret_name is not None}
        portal_core_aliases = sorted(portal_secrets.intersection(core_secrets))
        if portal_core_aliases:
            aliases = ", ".join(portal_core_aliases)
            msg = f"Portal API secret(s) {aliases} cannot alias core application or database secrets"
            raise ValueError(msg)
        privileged = core_secrets | portal_secrets
        control_plane_owners: dict[str, tuple[int, str]] = {}
        for stone_index, stone in enumerate(soulstones):
            for secret_name in stone.control_plane_secret_names:
                previous = control_plane_owners.get(secret_name)
                if previous is not None:
                    msg = (
                        f"Soulstones '{previous[1]}' and '{stone.name}' cannot share control-plane "
                        f"secret '{secret_name}'"
                    )
                    raise ValueError(msg)
                control_plane_owners[secret_name] = (stone_index, stone.name)

        for stone_index, (stone, plan) in enumerate(zip(soulstones, runtime_plans, strict=True)):
            runtime_secret_names = {podman_secret_source(secret) for secret in plan.secrets}
            data_plane_secrets = {
                *stone.secret_env_files.values(),
                *stone.control_plane_secret_names,
                *runtime_secret_names,
            }
            overlap = sorted(data_plane_secrets.intersection(privileged))
            if overlap:
                msg = (
                    f"Soulstone '{stone.name}' secret(s) {', '.join(overlap)} must be distinct "
                    "from core and Portal secrets"
                )
                raise ValueError(msg)

            # A runtime adapter may mount its own control document into the
            # runtime it controls (TabbyAPI requires this), but Rune-level data
            # secrets must never alias any control-plane document, and an
            # adapter must never mount a document owned by another Soulstone.
            rune_aliases = sorted(set(stone.secret_env_files.values()).intersection(control_plane_owners))
            foreign_runtime_aliases = sorted(
                secret_name
                for secret_name in runtime_secret_names
                if (owner := control_plane_owners.get(secret_name)) is not None and owner[0] != stone_index
            )
            forbidden_aliases = sorted({*rune_aliases, *foreign_runtime_aliases})
            if forbidden_aliases:
                aliases = ", ".join(forbidden_aliases)
                msg = (
                    f"Soulstone '{stone.name}' data-plane secret(s) {aliases} cannot alias "
                    "a Soulstone control-plane secret"
                )
                raise ValueError(msg)

    def _create_core_manifests(
        self,
        settings: Settings,
        portals: Sequence[PortalConfig],
        soulstones: Sequence[SoulstoneConfig],
    ) -> list[QuadletContainer]:
        """Define the persistent core services (Vessel, Phylactery).

        The Vessel mounts all internal and portal-referenced Podman secrets so
        runtime connectors can resolve credentials from ``/run/secrets``.
        """
        vessel_mounts = [MountData.from_str(mount) for mount in self._vessel_mount_strings(settings)]
        migrator_mounts = [MountData.from_str(mount) for mount in self._migrator_mount_strings()]
        app_secret_name = settings.server.web.secret_key_secret
        db_secret_name = settings.server.database.password_secret
        portal_secret_names = [portal.api_key_secret_name for portal in portals if portal.api_key_secret_name]
        control_plane_secret_names = [
            secret_name for stone in soulstones for secret_name in stone.control_plane_secret_names
        ]
        vessel_secrets = list(
            dict.fromkeys([app_secret_name, db_secret_name, *portal_secret_names, *control_plane_secret_names])
        )
        reactor_dependencies = (
            ["lychd-reactor.path"] if settings.orchestration.switching.actuator == "host-reactor" else []
        )

        # 1. The Vessel (LychD Web Server)
        vessel = QuadletContainer(
            description="The Vessel (LychD Application Kernel)",
            image=settings.server.web.image,
            container_name="lychd-vessel",
            pod=LYCHD_POD_QUADLET,
            user="%U",
            volumes=vessel_mounts,
            env_vars={
                **self._runtime_path_env(),
                "LYCHD_APP_SECRET_KEY_FILE": self._secret_file(app_secret_name),
                "SERVER__DATABASE__HOST": "localhost",
                "SERVER__DATABASE__PORT": str(CONTAINER_POSTGRES_PORT),
                "LYCHD_DB_PASSWORD_FILE": self._secret_file(db_secret_name),
            },
            secrets=vessel_secrets,
            wants=["lychd-migrate.service", *reactor_dependencies],
            requires=["lychd-migrate.service", *reactor_dependencies],
            after=["lychd-migrate.service", *reactor_dependencies],
        )

        # 2. The Phylactery (Postgres)
        # Postgres keeps its image UID; :U maps bind ownership for that rootless
        # container identity while :Z applies the SELinux private label.
        data_mount = f"{PATH_POSTGRESS_DATA_DIR}:/var/lib/postgresql/data:U,Z"
        init_mount = f"{PATH_POSTGRES_ROOT_DIR / 'init_db.sh'}:/docker-entrypoint-initdb.d/10-lychd-init.sh:ro,Z"
        phylactery = QuadletContainer(
            description="The Phylactery (Postgres & PgVector)",
            image=settings.server.database.image,
            container_name="lychd-phylactery",
            pod=LYCHD_POD_QUADLET,
            volumes=[MountData.from_str(data_mount), MountData.from_str(init_mount)],
            env_vars={
                "POSTGRES_USER": settings.server.database.user,
                "POSTGRES_DB": settings.server.database.database,
                "POSTGRES_PASSWORD_FILE": self._secret_file(db_secret_name),
            },
            secrets=[db_secret_name],
            wants=[LYCHD_POD_SERVICE],
            after=[LYCHD_POD_SERVICE],
        )

        # 3. Explicit migration gate. It runs inside the pod, where the DB secret is
        # already mounted, and waits boundedly for Postgres before invoking Alembic.
        # The unit remains inactive after success, so every explicit Vessel start
        # re-validates the schema idempotently.
        migrator = QuadletContainer(
            description="LychD Phylactery Migration Gate",
            image=settings.server.web.image,
            container_name="lychd-migrate",
            pod=LYCHD_POD_QUADLET,
            user="%U",
            volumes=migrator_mounts,
            env_vars={
                **self._runtime_path_env(),
                "LYCHD_APP_SECRET_KEY_FILE": self._secret_file(app_secret_name),
                "SERVER__DATABASE__HOST": "localhost",
                "SERVER__DATABASE__PORT": str(CONTAINER_POSTGRES_PORT),
                "LYCHD_DB_PASSWORD_FILE": self._secret_file(db_secret_name),
            },
            secrets=[app_secret_name, db_secret_name],
            exec="lychd database --wait-seconds 60 upgrade head --no-prompt",
            wants=["lychd-phylactery.service"],
            requires=["lychd-phylactery.service"],
            after=["lychd-phylactery.service"],
            service_type="oneshot",
            restart_policy="no",
            wanted_by=[],
        )

        return [vessel, phylactery, migrator]

    def _transmute_soulstone(
        self,
        stone: SoulstoneConfig,
        covens: dict[str, list[SoulstoneConfig]],
        settings: Settings,
        runtime_plan: RuntimePlan,
    ) -> QuadletContainer:
        """Convert a single Soulstone Rune into a Quadlet container manifest."""
        # Only list groups that actually Forge into Targets (The Law of the Coven)
        coven_targets = [g for g in stone.groups if len(covens.get(g, [])) >= MIN_COVEN_MEMBERS]

        merged_env = {k: str(v) for k, v in stone.env_vars.items()}
        merged_env.update(runtime_plan.env_overrides)
        merged_env.update(
            {env_name: self._secret_file(secret_name) for env_name, secret_name in stone.secret_env_files.items()}
        )
        merged_env.update(self._runtime_path_env())
        merged_podman_args = list(dict.fromkeys(["--replace", *runtime_plan.podman_args]))

        # Soulstones are data-plane model runtimes. They receive only explicitly
        # configured model/runtime volumes, never the Codex, Crypt, or Reactor inbox.
        mount_strings = [*stone.volumes]
        mount_strings.extend(runtime_plan.volumes)
        merged_mounts = self._validated_soulstone_mounts(
            mount_strings,
            stone_name=stone.name,
            settings=settings,
        )
        merged_secrets = list(dict.fromkeys([*stone.secret_env_files.values(), *runtime_plan.secrets]))

        # Boot survivor determinism (F4): auto-starting every dedicated runtime
        # would bypass the Orchestrator's single-owner plan/drain boundary and can
        # overcommit hardware. Only persistent residents are auto-wanted;
        # dedicated non-residents start on demand through the Orchestrator.
        wanted_by = ["default.target"] if stone.concurrency.persistent_resident else []

        return QuadletContainer(
            description=stone.description or f"LychD Soulstone: {stone.name}",
            image=stone.image,
            container_name=f"lychd-{stone.name}",
            pod=LYCHD_POD_QUADLET,
            user="%U",
            targets=coven_targets,
            env_vars=merged_env,
            devices=list(stone.devices),
            security_label_disable=stone.security_label_disable,
            # Merge Rune volumes and adapter volumes only after
            # proving that none crosses back into the trusted control plane.
            volumes=merged_mounts,
            exec=shlex.join(runtime_plan.exec_args) if runtime_plan.exec_args else None,
            podman_args=merged_podman_args,
            secrets=merged_secrets,
            # Never emit Conflicts= for managed runtimes. A systemd-triggered
            # implicit stop would bypass lease admission closure and drain.
            conflicts=[],
            binds_to=list(runtime_plan.unit_binds_to),
            wants=[LYCHD_POD_SERVICE],
            after=[LYCHD_POD_SERVICE, *runtime_plan.unit_after],
            wanted_by=wanted_by,
        )

    def _validated_soulstone_mounts(
        self,
        mount_strings: Sequence[str],
        *,
        stone_name: str,
        settings: Settings,
    ) -> list[MountData]:
        """Parse, normalize, and confine data-plane mounts outside control roots."""
        inbox_dir = settings.orchestration.switching.host_reactor_dir
        protected_roots = tuple(
            dict.fromkeys(
                (
                    PATH_CODEX_ROOT,
                    PATH_CRYPT_ROOT,
                    PATH_SYSTEMD_UNITS_DIR,
                    PATH_SYSTEMD_USER_UNITS_DIR,
                    inbox_dir,
                    settings.orchestration.switching.host_reactor_journal_dir,
                )
            )
        )
        protected_host_roots = tuple(
            (root, _resolve_host_path(root, stone_name=stone_name)) for root in protected_roots
        )
        protected_container_roots = tuple((root, Path(os.path.normpath(root))) for root in protected_roots)

        validated: list[MountData] = []
        seen: set[tuple[Path, Path, tuple[str, ...]]] = set()
        destinations: dict[Path, Path] = {}
        for raw_mount in mount_strings:
            parsed = MountData.from_str(raw_mount)
            host_path = _normalize_mount_path(parsed.host_path, stone_name=stone_name, side="host")
            container_path = _normalize_mount_path(
                parsed.container_path,
                stone_name=stone_name,
                side="container",
            )
            resolved_host = _resolve_host_path(host_path, stone_name=stone_name)

            previous_host = destinations.setdefault(container_path, resolved_host)
            if previous_host != resolved_host or any(
                existing.container_path == container_path for existing in validated
            ):
                msg = f"Soulstone '{stone_name}' declares more than one mount for container path {container_path}"
                raise ValueError(msg)

            for configured_root, protected_root in protected_host_roots:
                if paths_overlap(resolved_host, protected_root):
                    msg = (
                        f"Soulstone '{stone_name}' host mount path {host_path} overlaps "
                        f"protected control root {configured_root}"
                    )
                    raise ValueError(msg)
            for configured_root, protected_root in protected_container_roots:
                if paths_overlap(container_path, protected_root):
                    msg = (
                        f"Soulstone '{stone_name}' container mount path {container_path} overlaps "
                        f"protected control root {configured_root}"
                    )
                    raise ValueError(msg)

            # Emit the canonical host target we checked. Keeping a symlink alias
            # in the unit would reopen a retargeting race between bind and start.
            key = (resolved_host, container_path, tuple(parsed.options))
            if key in seen:
                continue
            seen.add(key)
            validated.append(
                MountData(
                    host_path=resolved_host,
                    container_path=container_path,
                    mirror=resolved_host == container_path,
                    options=list(parsed.options),
                )
            )
        return validated

    def _migrator_mount_strings(self) -> list[str]:
        """Return the read-only configuration mounts needed by the migration CLI."""
        return [
            f"{PATH_CODEX_ROOT}:{PATH_CODEX_ROOT}:ro,Z",
            f"{PATH_CORE_DIR}:{PATH_CORE_DIR}:ro,Z",
            f"{PATH_EXTENSIONS_DIR}:{PATH_EXTENSIONS_DIR}:ro,Z",
        ]

    def _vessel_mount_strings(self, settings: Settings) -> list[str]:
        """Return the trusted Vessel control-plane mounts."""
        mounts = [
            f"{PATH_CODEX_ROOT}:{PATH_CODEX_ROOT}:ro,Z",
            f"{PATH_LAB_DIR}:{PATH_LAB_DIR}:rw,Z",
            f"{PATH_CORE_DIR}:{PATH_CORE_DIR}:ro,Z",
            f"{PATH_EXTENSIONS_DIR}:{PATH_EXTENSIONS_DIR}:ro,Z",
        ]
        if settings.orchestration.switching.actuator == "host-reactor":
            inbox = settings.orchestration.switching.host_reactor_dir
            journal = settings.orchestration.switching.host_reactor_journal_dir
            mounts.append(f"{inbox}:{inbox}:rw,Z")
            mounts.append(f"{journal}:{journal}:ro,Z")
        return mounts

    def _runtime_path_env(self) -> dict[str, str]:
        """Keep XDG-derived host/container paths symmetric under ``User=%U``."""
        from lychd.system.constants import (
            PATH_XDG_CACHE_HOME,
            PATH_XDG_CONFIG_HOME,
            PATH_XDG_DATA_HOME,
        )

        return {
            "HOME": str(Path.home()),
            "XDG_CONFIG_HOME": str(PATH_XDG_CONFIG_HOME),
            "XDG_DATA_HOME": str(PATH_XDG_DATA_HOME),
            "XDG_CACHE_HOME": str(PATH_XDG_CACHE_HOME),
        }

    def _secret_file(self, secret_name: str) -> str:
        """Map a Podman secret name to its default mounted file path."""
        return f"/run/secrets/{secret_name}"
