from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Minimum number of parts in a volume string (host:container)
MIN_VOLUME_PARTS = 2

# Indices for parsing volume parts from a colon-separated string
INDEX_HOST = 0
INDEX_CONTAINER = 1
INDEX_OPTIONS = 2


class QuadletBase(BaseModel):
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
            msg = (
                "MountData with mirror=True requires identical host_path and "
                f"container_path. Got '{self.host_path}' and '{self.container_path}'."
            )
            raise ValueError(msg)
        return self

    def __str__(self) -> str:
        """Manifest the mount as a colon-separated string."""
        opts = ",".join(self.options)
        return f"{self.host_path}:{self.container_path}:{opts}" if opts else f"{self.host_path}:{self.container_path}"

    @classmethod
    def from_str(cls, val: str) -> MountData:
        """Transmute a raw string into a structured MountData."""
        return cls.model_validate(val)


class QuadletContainer(QuadletBase):
    """Data model for 'container.jinja'. Represents a single [Container] Quadlet file.

    The Vessel that contains a portion of the Daemon's spirit.
    """

    # [Unit] section
    description: str
    wants: list[str] = Field(default_factory=lambda: ["network-online.target"])
    requires: list[str] = Field(default_factory=list)
    after: list[str] = Field(default_factory=lambda: ["network-online.target"])
    conflicts: list[str] = Field(default_factory=list, description="The Law of Exclusivity")

    # [Container] section
    image: str
    container_name: str
    pod: str | None = None  # If part of a pod (e.g. 'lychd.pod')
    pod_service: str | None = None
    start_with_pod: bool = False
    user: str | None = None

    # Coven Membership (Systemd Targets)
    targets: list[str] = Field(
        default_factory=list,
        description="The Covens (Systemd Targets) this Rune belongs to.",
    )

    run_init: bool = True
    # A container joined to a Pod inherits the Pod's user namespace; Podman
    # ignores per-container --userns in that topology.
    user_ns: str | None = None
    podman_args: list[str] = Field(default_factory=lambda: ["--replace"])
    devices: list[str] = Field(
        default_factory=list,
        description="Host devices passed through to the container (Quadlet AddDevice= lines).",
    )
    security_label_disable: bool = Field(
        default=False,
        description="When true, emit SecurityLabelDisable=true (SELinux label off, --security-opt label=disable).",
    )

    volumes: list[MountData] = Field(default_factory=list)
    env_vars: dict[str, str] = Field(default_factory=dict)
    secrets: list[str] = Field(
        default_factory=list, description="Podman secret specs rendered as Quadlet Secret= lines."
    )

    # The actual command (list of args joined by spaces in template)
    exec: str | None = None

    # [Service] section
    service_type: Literal["simple", "oneshot"] | None = None
    remain_after_exit: bool = False
    restart_policy: str = "always"

    # [Install] - Crucial for auto-start
    wanted_by: list[str] = Field(default_factory=lambda: ["default.target"])

    @model_validator(mode="after")
    def derive_pod_service(self) -> QuadletContainer:
        """Resolve a Quadlet source name to the systemd service it generates."""
        if self.pod is not None and self.pod_service is None:
            pod_name = self.pod.removesuffix(".pod")
            object.__setattr__(self, "pod_service", f"{pod_name}-pod.service")
        return self


class QuadletPod(QuadletBase):
    """Data model for 'pod.jinja'.

    The Sepulcher—the physical boundary of the Daemon's presence.
    """

    description: str = "The Sepulcher (LychD Pod)"
    pod_name: str = "lychd"
    publish_ports: list[str] = Field(default_factory=list)
    user_ns: str | None = "keep-id"

    # [Install] section
    wanted_by: list[str] = Field(default_factory=lambda: ["default.target"])


class QuadletTarget(QuadletBase):
    """Data model for 'target.jinja'.

    A Coven—a collection of Runes that define an Operational State.
    """

    name: str  # e.g. 'vision' -> lychd-coven-vision.target
    description: str
    # The generated pod service unit name. Quadlet turns `lychd.pod` (PodName=lychd)
    # into `lychd-pod.service`; `PartOf=` in a real systemd unit must reference that
    # service, NOT the Quadlet source name `lychd.pod`.
    part_of: str = "lychd-pod.service"

    # [Install] section
    wanted_by: list[str] = Field(default_factory=lambda: ["default.target"])


class SystemdService(BaseModel):
    """A plain systemd --user unit (uncaged daemonhood) — deliberately NOT a Quadlet.

    The uncaged vessel runs the LychD server directly on the host (no Podman pod,
    no Quadlet generator), so this is a hand-rendered ``.service`` unit written
    straight into the systemd user unit dir. It shares nothing with the Quadlet
    ``render``/template machinery on purpose.
    """

    name: str = "lychd-vessel"
    description: str = "LychD Vessel (uncaged)"
    exec_start: str  # "<sys.prefix>/bin/lychd run --host 127.0.0.1 --port <port>"
    environment: dict[str, str] = Field(default_factory=lambda: {"LYCHD_MODE": "uncaged"})
    restart: str = "on-failure"
    wanted_by: str = "default.target"

    @property
    def filename(self) -> str:
        """The on-disk unit filename (e.g. ``lychd-vessel.service``)."""
        return f"{self.name}.service"

    def render(self) -> str:
        """Render the [Unit]/[Service]/[Install] text with deterministic key order.

        Environment keys are emitted sorted so the output is diff-stable across
        rewrites (Scribe idempotency); the section order is fixed.
        """
        env_lines = [f'Environment="{key}={value}"' for key, value in sorted(self.environment.items())]
        lines = [
            "[Unit]",
            f"Description={self.description}",
            "",
            "[Service]",
            f"ExecStart={self.exec_start}",
            *env_lines,
            f"Restart={self.restart}",
            "",
            "[Install]",
            f"WantedBy={self.wanted_by}",
            "",
        ]
        return "\n".join(lines)
