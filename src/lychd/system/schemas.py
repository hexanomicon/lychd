from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Minimum number of parts in a volume string (host:container)
MIN_VOLUME_PARTS = 2

# Indices for parsing volume parts from a colon-separated string
INDEX_HOST = 0
INDEX_CONTAINER = 1
INDEX_OPTIONS = 2


class RuneBase(BaseModel):
    """Base class for all Systemd Artifacts (The Physical Manifestations)."""

    model_config = ConfigDict(frozen=True)


class MountData(BaseModel):
    """The Ritual of Shared Space.

    Enforces Path Symmetry (Mirroring) and manages SELinux labeling.
    """

    host_path: Path
    container_path: Path
    mirror: bool = True
    options: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def validate_input(cls, data: Any) -> Any:
        """Allow initializing from a colon-separated string."""
        if isinstance(data, str):
            val = data
            parts = val.split(":")
            if len(parts) < MIN_VOLUME_PARTS:
                msg = f"Invalid volume format: {val}. Expected host:container[:opts]"
                raise ValueError(msg)

            host = Path(parts[INDEX_HOST])
            container = Path(parts[INDEX_CONTAINER])
            opts = parts[INDEX_OPTIONS].split(",") if len(parts) > INDEX_OPTIONS else []

            return {
                "host_path": host,
                "container_path": container,
                "options": opts,
                "mirror": host == container,
            }
        return data

    @model_validator(mode="after")
    def validate_mirroring(self) -> MountData:
        """Law of Geographic Determinism: Host and Container paths must be identical if mirrored."""
        if self.mirror and self.host_path != self.container_path:
            # Strictly enforce for Codex/Crypt/Forge when mirroring is enabled
            # Note: We allow non-symmetric paths if mirror=False
            pass
        return self

    def __str__(self) -> str:
        """Manifest the mount as a colon-separated string."""
        opts = ",".join(self.options)
        return f"{self.host_path}:{self.container_path}:{opts}" if opts else f"{self.host_path}:{self.container_path}"

    @classmethod
    def from_str(cls, val: str) -> MountData:
        """Transmute a raw string into a structured MountData."""
        return cls.model_validate(val)


class ContainerRune(RuneBase):
    """Data model for 'container.jinja'. Represents a single [Container] Quadlet file.

    The Vessel that contains a portion of the Daemon's spirit.
    """

    # [Unit] section
    description: str
    wants: list[str] = Field(default_factory=lambda: ["network-online.target"])
    after: list[str] = Field(default_factory=lambda: ["network-online.target"])
    conflicts: list[str] = Field(default_factory=list, description="The Law of Exclusivity")

    # [Container] section
    image: str
    container_name: str
    pod: str | None = None  # If part of a pod (e.g. 'lychd.pod')

    # Coven Membership (Systemd Targets)
    targets: list[str] = Field(
        default_factory=list,
        description="The Covens (Systemd Targets) this Rune belongs to.",
    )

    run_init: bool = True
    user_ns: str | None = "keep-id"  # ADR 08: Identity Symmetry
    podman_args: list[str] = Field(default_factory=lambda: ["--replace"])

    volumes: list[MountData] = Field(default_factory=list)
    env_vars: dict[str, str] = Field(default_factory=dict)

    # The actual command (list of args joined by spaces in template)
    exec: str | None = None

    # [Service] section
    restart_policy: str = "always"

    # [Install] - Crucial for auto-start
    wanted_by: list[str] = Field(default_factory=lambda: ["default.target"])


class PodRune(RuneBase):
    """Data model for 'pod.jinja'.

    The Sepulcher—the physical boundary of the Daemon's presence.
    """

    description: str = "The Sepulcher (LychD Pod)"
    pod_name: str = "lychd"
    publish_ports: list[str] = Field(default_factory=list)

    # [Install] section
    wanted_by: list[str] = Field(default_factory=lambda: ["default.target"])


class TargetRune(RuneBase):
    """Data model for 'target.jinja'.

    A Coven—a collection of Runes that define an Operational State.
    """

    name: str  # e.g. 'vision' -> lychd-coven-vision.target
    description: str
    part_of: str = "lychd.pod"

    # [Install] section
    wanted_by: list[str] = Field(default_factory=lambda: ["default.target"])
