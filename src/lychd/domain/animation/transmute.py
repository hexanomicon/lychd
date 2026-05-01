"""Domain transmutation from animator runes into concrete Quadlet manifests.

This module is pure domain logic: it computes Quadlet data models but performs
no filesystem writes or host mutations.
"""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING, Final

from lychd.config.settings import get_settings
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.system.constants import (
    CONTAINER_LYCHD_PORT,
    CONTAINER_PHOENIX_OTLP_PORT,
    CONTAINER_PHOENIX_UI_PORT,
    CONTAINER_POSTGRES_PORT,
    PATH_CODEX_ROOT,
    PATH_CORE_DIR,
    PATH_CRYPT_ROOT,
    PATH_EXTENSIONS_DIR,
    PATH_POSTGRES_ROOT_DIR,
)
from lychd.system.schemas import MountData, QuadletBase, QuadletContainer, QuadletPod, QuadletTarget

if TYPE_CHECKING:
    from lychd.config.settings import Settings
    from lychd.domain.animation.schemas import PortalConfig, SoulstoneConfig
    from lychd.domain.animation.services.adapters.contracts import SoulstoneRuntimePlanner

MIN_COVEN_MEMBERS: Final[int] = 2


class Transmuter:
    """The Alchemist of Form.

    Responsible for:
    - Transmuting Soulstones into ContainerRunes.
    - Calculating the Law of Exclusivity (Conflicts/Alliances).
    - Defining the Core Runes (Pod, Phylactery, Oculus).
    """

    def __init__(self, runtime_planner: SoulstoneRuntimePlanner | None = None) -> None:
        """Initialize transmuter with a runtime planner dependency."""
        self._runtime_planner = runtime_planner or RuntimeAdapterRegistry()

    def transmute_all(
        self,
        soulstones: list[SoulstoneConfig],
        *,
        portals: list[PortalConfig] | None = None,
    ) -> list[QuadletBase]:
        """Convert a set of Soulstones into a complete manifest of Runes."""
        settings = get_settings()
        runes: list[QuadletBase] = []
        resolved_portals = portals or []

        # 1. The Sepulcher (Pod)
        runes.append(self._create_pod(settings))

        # 2. The Core Rituals (Core Runes)
        runes.extend(self._create_core_runes(settings, resolved_portals))

        # 3. Calculate Covens
        covens: dict[str, list[SoulstoneConfig]] = {}
        for stone in soulstones:
            for group in stone.groups:
                covens.setdefault(group, []).append(stone)

        # 4. Generate Coven Targets
        for group, members in covens.items():
            if len(members) >= MIN_COVEN_MEMBERS:
                runes.append(
                    QuadletTarget(
                        name=group,
                        description=f"LychD Coven: {group}",
                    )
                )

        # 5. Transmute Extension Soulstones
        alliances = getattr(settings.lychd, "alliances", [])
        runes.extend(self._transmute_soulstone(stone, soulstones, covens, alliances, settings) for stone in soulstones)

        return runes

    def _create_pod(self, settings: Settings) -> QuadletPod:
        """Define the physical boundary of the Sepulcher."""
        ports = [
            f"{settings.server.port}:{CONTAINER_LYCHD_PORT}",
            f"{settings.db.port}:{CONTAINER_POSTGRES_PORT}",
            f"{settings.phoenix.ui_port}:{CONTAINER_PHOENIX_UI_PORT}",
            f"{settings.phoenix.otlp_port}:{CONTAINER_PHOENIX_OTLP_PORT}",
        ]
        return QuadletPod(publish_ports=ports)

    def _create_core_runes(self, settings: Settings, portals: list[PortalConfig]) -> list[QuadletContainer]:
        """Define the persistent services (Vessel, Phylactery, Oculus).

        The Vessel mounts all internal and portal-referenced Podman secrets so
        runtime connectors can resolve credentials from ``/run/secrets``.
        """
        system_mounts = [MountData.from_str(mount) for mount in self._system_mount_strings()]
        app_secret_name = settings.app.secret_key_secret
        db_secret_name = settings.db.password_secret
        portal_secret_names = [portal.api_key_secret for portal in portals if portal.api_key_secret]
        vessel_secrets = list(dict.fromkeys([app_secret_name, db_secret_name, *portal_secret_names]))

        # 1. The Vessel (LychD Web Server)
        vessel = QuadletContainer(
            description="The Vessel (LychD Application Kernel)",
            image=settings.app.image,
            container_name="lychd-vessel",
            pod="lychd.pod",
            volumes=system_mounts,
            env_vars={
                "APP__SECRET_KEY_FILE": self._secret_file(app_secret_name),
                "DB__HOST": "localhost",
                "DB__PORT": str(CONTAINER_POSTGRES_PORT),
                "DB__PASSWORD_FILE": self._secret_file(db_secret_name),
            },
            secrets=vessel_secrets,
            wants=["lychd-phylactery.service"],
            after=["lychd-phylactery.service"],
        )

        # 2. The Phylactery (Postgres)
        data_mount = f"{PATH_POSTGRES_ROOT_DIR}:/var/lib/postgresql/data:Z"
        phylactery = QuadletContainer(
            description="The Phylactery (Postgres & PgVector)",
            image=settings.db.image,
            container_name="lychd-phylactery",
            pod="lychd.pod",
            volumes=[MountData.from_str(data_mount)],
            env_vars={
                "POSTGRES_USER": settings.db.user,
                "POSTGRES_DB": settings.db.database,
            },
            wants=["lychd.pod"],
            after=["lychd.pod"],
        )

        # 3. The Oculus (Phoenix)
        db_url = f"postgresql://{settings.db.user}@localhost:{CONTAINER_POSTGRES_PORT}/phoenix"
        oculus = QuadletContainer(
            description="The Oculus (Arize Phoenix)",
            image=settings.phoenix.image,
            container_name="lychd-oculus",
            pod="lychd.pod",
            env_vars={"PHOENIX_PORT": str(CONTAINER_PHOENIX_UI_PORT), "PHOENIX_SQL_DATABASE_URL": db_url},
            wants=["lychd-phylactery.service"],
            after=["lychd-phylactery.service"],
        )

        return [vessel, phylactery, oculus]

    def _transmute_soulstone(
        self,
        stone: SoulstoneConfig,
        all_stones: list[SoulstoneConfig],
        covens: dict[str, list[SoulstoneConfig]],
        alliances: list[list[str]],
        settings: Settings,
    ) -> QuadletContainer:
        """Convert a single Soulstone into a ContainerRune."""
        conflicts = self._calculate_conflicts(stone, all_stones, covens, alliances)

        # Only list groups that actually Forge into Targets (The Law of the Coven)
        coven_targets = [g for g in stone.groups if len(covens.get(g, [])) >= MIN_COVEN_MEMBERS]

        runtime_plan = self._runtime_planner.plan(stone)
        merged_env = {k: str(v) for k, v in stone.env_vars.items()}
        merged_env.update(runtime_plan.env_overrides)
        merged_env.update(
            {env_name: self._secret_file(secret_name) for env_name, secret_name in stone.secret_env_files.items()}
        )
        merged_podman_args = list(dict.fromkeys(["--replace", *runtime_plan.podman_args]))

        mount_strings = [*self._system_mount_strings()]
        mount_strings.extend(settings.lychd.default_soulstone_mounts)
        mount_strings.extend(stone.volumes)
        mount_strings.extend(runtime_plan.volumes)
        # Preserve order and drop duplicates.
        merged_mounts = list(dict.fromkeys(mount_strings))
        merged_secrets = list(dict.fromkeys(stone.secret_env_files.values()))

        return QuadletContainer(
            description=stone.description or f"LychD Soulstone: {stone.name}",
            image=stone.image,
            container_name=f"lychd-{stone.name}",
            pod="lychd.pod",
            targets=coven_targets,
            env_vars=merged_env,
            # Merge system mounts, global defaults, user volumes, and adapter volumes.
            volumes=[MountData.from_str(v) for v in merged_mounts],
            exec=shlex.join(runtime_plan.exec_args) if runtime_plan.exec_args else None,
            podman_args=merged_podman_args,
            secrets=merged_secrets,
            conflicts=conflicts,
            wants=["lychd.pod"],
            after=["lychd.pod"],
        )

    def _system_mount_strings(self) -> list[str]:
        """Return baseline mounts shared by core units and all Soulstones."""
        return [
            f"{PATH_CODEX_ROOT}:{PATH_CODEX_ROOT}:ro,Z",
            f"{PATH_CRYPT_ROOT}:{PATH_CRYPT_ROOT}:rw,Z",
            f"{PATH_CORE_DIR}:{PATH_CORE_DIR}:ro,Z",
            f"{PATH_EXTENSIONS_DIR}:{PATH_EXTENSIONS_DIR}:ro,Z",
        ]

    def _secret_file(self, secret_name: str) -> str:
        """Map a Podman secret name to its default mounted file path."""
        return f"/run/secrets/{secret_name}"

    def _calculate_conflicts(
        self,
        current: SoulstoneConfig,
        all_stones: list[SoulstoneConfig],
        covens: dict[str, list[SoulstoneConfig]],
        alliances: list[list[str]],
    ) -> list[str]:
        """Implement the Law of Exclusivity (Implicit Hostility, Explicit Alliances)."""
        enemies: set[str] = set()

        # Determine current coven identities
        current_covens = set(current.groups)

        # Calculate allied covens
        allied_covens: set[str] = set()
        allied_stones: set[str] = {current.name}  # Self is always allied
        for alliance in alliances:
            if current_covens.intersection(alliance):
                allied_covens.update(alliance)

        # 1. Conflict with other Covens (Targets)
        for other_coven_name, members in covens.items():
            if (
                other_coven_name not in allied_covens
                and other_coven_name not in current_covens
                and len(members) >= MIN_COVEN_MEMBERS
            ):
                enemies.add(f"lychd-coven-{other_coven_name}.target")

        # 2. Conflict with other Soulstones (Services)
        # A stone conflicts with another stone if:
        # - They share no allied groups.
        # - One or both are not in a 'real' coven (>= MIN_COVEN_MEMBERS).
        for other in all_stones:
            if other.name in allied_stones:
                continue

            other_covens = set(other.groups)
            is_allied = bool(other_covens.intersection(allied_covens))

            if not is_allied:
                # If the other stone is in a 'real' coven, we already conflict with the target.
                # If not, we must conflict with the service directly.
                in_real_coven = any(len(covens.get(g, [])) >= MIN_COVEN_MEMBERS for g in other.groups)
                if not in_real_coven:
                    enemies.add(f"{other.service_name}.service")

        return sorted(enemies)
