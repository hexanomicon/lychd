from __future__ import annotations

import shlex
from typing import TYPE_CHECKING, Final

from lychd.config.settings import get_settings
from lychd.system.constants import (
    CONTAINER_LYCHD_PORT,
    CONTAINER_PHOENIX_OTLP_PORT,
    CONTAINER_PHOENIX_UI_PORT,
    CONTAINER_POSTGRES_PORT,
    PATH_CODEX_ROOT,
    PATH_CORE_DIR,
    PATH_CRYPT_ROOT,
    PATH_EXTENSIONS_DIR,
    PATH_POSTGRES_DIR,
)
from lychd.system.schemas import ContainerRune, MountData, PodRune, RuneBase, TargetRune

if TYPE_CHECKING:
    from lychd.domain.animation.schemas import Soulstone

MIN_COVEN_MEMBERS: Final[int] = 2


class Transmuter:
    """The Alchemist of Form.

    Responsible for:
    - Transmuting Soulstones into ContainerRunes.
    - Calculating the Law of Exclusivity (Conflicts/Alliances).
    - Defining the Core Runes (Pod, Phylactery, Oculus).
    """

    def transmute_all(self, soulstones: list[Soulstone]) -> list[RuneBase]:
        """Convert a set of Soulstones into a complete manifest of Runes."""
        runes: list[RuneBase] = []

        # 1. The Sepulcher (Pod)
        runes.append(self._create_pod())

        # 2. The Core Rituals (Core Runes)
        runes.extend(self._create_core_runes())

        # 3. Calculate Covens
        covens: dict[str, list[Soulstone]] = {}
        for stone in soulstones:
            for group in stone.groups:
                covens.setdefault(group, []).append(stone)

        # 4. Generate Coven Targets
        for group, members in covens.items():
            if len(members) >= MIN_COVEN_MEMBERS:
                runes.append(
                    TargetRune(
                        name=group,
                        description=f"LychD Coven: {group}",
                    )
                )

        # 5. Transmute Extension Soulstones
        alliances = getattr(get_settings().lychd, "alliances", [])
        runes.extend(self._transmute_soulstone(stone, soulstones, covens, alliances) for stone in soulstones)

        return runes

    def _create_pod(self) -> PodRune:
        """Define the physical boundary of the Sepulcher."""
        settings = get_settings()
        ports = [
            f"{settings.server.port}:{CONTAINER_LYCHD_PORT}",
            f"{settings.db.port}:{CONTAINER_POSTGRES_PORT}",
            f"{settings.phoenix.ui_port}:{CONTAINER_PHOENIX_UI_PORT}",
            f"{settings.phoenix.otlp_port}:{CONTAINER_PHOENIX_OTLP_PORT}",
        ]
        return PodRune(publish_ports=ports)

    def _create_core_runes(self) -> list[ContainerRune]:
        """Define the persistent services (Vessel, Phylactery, Oculus)."""
        settings = get_settings()

        # Shared System Mounts (The Trinity)
        system_mounts = [
            MountData.from_str(f"{PATH_CODEX_ROOT}:{PATH_CODEX_ROOT}:ro,Z"),
            MountData.from_str(f"{PATH_CRYPT_ROOT}:{PATH_CRYPT_ROOT}:rw,Z"),
            MountData.from_str(f"{PATH_CORE_DIR}:{PATH_CORE_DIR}:ro,Z"),
            # Note: Extensions are also RO by default
            MountData.from_str(f"{PATH_EXTENSIONS_DIR}:{PATH_EXTENSIONS_DIR}:ro,Z"),
        ]

        # 1. The Vessel (LychD Web Server)
        vessel = ContainerRune(
            description="The Vessel (LychD Application Kernel)",
            image=settings.app.image,
            container_name="lychd-vessel",
            pod="lychd.pod",
            volumes=system_mounts,
            env_vars={
                "APP__SECRET_KEY": settings.app.secret_key.get_secret_value(),
                "DB__HOST": "localhost",
                "DB__PORT": str(CONTAINER_POSTGRES_PORT),
            },
            wants=["lychd-phylactery.service"],
            after=["lychd-phylactery.service"],
        )

        # 2. The Phylactery (Postgres)
        data_mount = f"{PATH_POSTGRES_DIR}:/var/lib/postgresql/data:Z"
        phylactery = ContainerRune(
            description="The Phylactery (Postgres & PgVector)",
            image=settings.db.image,
            container_name="lychd-phylactery",
            pod="lychd.pod",
            volumes=[MountData.from_str(data_mount)],
            env_vars={"POSTGRES_USER": settings.db.user, "POSTGRES_DB": settings.db.database},
            wants=["lychd.pod"],
            after=["lychd.pod"],
        )

        # 3. The Oculus (Phoenix)
        db_url = (
            f"postgresql://{settings.db.user}:{settings.db.password.get_secret_value()}"
            f"@localhost:{CONTAINER_POSTGRES_PORT}/phoenix"
        )
        oculus = ContainerRune(
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
        stone: Soulstone,
        all_stones: list[Soulstone],
        covens: dict[str, list[Soulstone]],
        alliances: list[list[str]],
    ) -> ContainerRune:
        """Convert a single Soulstone into a ContainerRune."""
        conflicts = self._calculate_conflicts(stone, all_stones, covens, alliances)

        # Only list groups that actually Forge into Targets (The Law of the Coven)
        coven_targets = [g for g in stone.groups if len(covens.get(g, [])) >= MIN_COVEN_MEMBERS]

        # Shared System Mounts (The Trinity)
        system_mounts = [
            MountData.from_str(f"{PATH_CODEX_ROOT}:{PATH_CODEX_ROOT}:ro,Z"),
            MountData.from_str(f"{PATH_CRYPT_ROOT}:{PATH_CRYPT_ROOT}:rw,Z"),
            MountData.from_str(f"{PATH_CORE_DIR}:{PATH_CORE_DIR}:ro,Z"),
            MountData.from_str(f"{PATH_EXTENSIONS_DIR}:{PATH_EXTENSIONS_DIR}:ro,Z"),
        ]

        return ContainerRune(
            description=stone.description or f"LychD Soulstone: {stone.name}",
            image=stone.image,
            container_name=f"lychd-{stone.name}",
            pod="lychd.pod",
            targets=coven_targets,
            env_vars={k: str(v) for k, v in stone.env_vars.items()},
            # Merge user volumes with system mounts
            volumes=system_mounts + [MountData.from_str(v) for v in stone.volumes],
            exec=shlex.join(stone.exec) if stone.exec else None,
            conflicts=conflicts,
            wants=["lychd.pod"],
            after=["lychd.pod"],
        )

    def _calculate_conflicts(
        self,
        current: Soulstone,
        all_stones: list[Soulstone],
        covens: dict[str, list[Soulstone]],
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
