from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from lychd.system.secret_names import validate_podman_secret_name

# Minimum number of parts in a volume string (host:container)
MIN_VOLUME_PARTS = 2

# Indices for parsing volume parts from a colon-separated string
INDEX_HOST = 0
INDEX_CONTAINER = 1
INDEX_OPTIONS = 2

_MOUNT_OPTIONS: Final[frozenset[str]] = frozenset(
    {"O", "U", "Z", "copy", "nocopy", "nodev", "noexec", "nosuid", "ro", "rw", "z"}
)
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SECRET_MODE = re.compile(r"^0[0-7]{3}$")
_PUBLISH_PORT = re.compile(r"^127\.0\.0\.1:(\d{1,5}):(\d{1,5})$")
_UNIT_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@-]*$")
_MEMORY_SIZE = re.compile(r"^[1-9][0-9]*[kmgt]?$")
_MAX_PORT = 65535


def _validate_unit_text(
    value: str,
    *,
    field_name: str,
    allow_specifier: bool = False,
    allow_dollar: bool = False,
) -> str:
    """Reject text that can escape one systemd directive or inject a specifier."""
    if value and not value.isprintable():
        msg = f"{field_name} must contain printable single-line text"
        raise ValueError(msg)
    if "\\" in value:
        msg = f"{field_name} cannot contain backslashes or systemd continuation escapes"
        raise ValueError(msg)
    if not allow_dollar and "$" in value:
        msg = f"{field_name} cannot contain systemd environment expansion"
        raise ValueError(msg)
    if any(token.strip("'\"") == ";" for token in value.split()):
        msg = f"{field_name} cannot contain a standalone systemd command separator"
        raise ValueError(msg)
    if not allow_specifier and "%" in value.replace("%%", ""):
        msg = f"{field_name} contains an unescaped systemd specifier; use %% for a literal percent"
        raise ValueError(msg)
    return value


def systemd_environment_assignment(key: str, value: str) -> str:
    """Validate and quote one complete ``Environment=`` assignment."""
    if _ENV_NAME.fullmatch(key) is None:
        msg = f"Invalid environment variable name: {key!r}"
        raise ValueError(msg)
    _validate_unit_text(value, field_name=f"environment[{key!r}]", allow_dollar=True)
    escaped = f"{key}={value}".replace('"', '\\"')
    return f'"{escaped}"'


def quadlet_environment_assignment(key: str, value: str) -> str:
    """Quote a Quadlet assignment and neutralize later systemd ``$`` expansion."""
    assignment = systemd_environment_assignment(key, value)
    return assignment.replace("$", "$$")


def podman_secret_source(spec: str) -> str:
    """Validate one bounded Quadlet ``Secret=`` spec and return its source name."""
    _validate_unit_text(spec, field_name="Podman secret spec")
    source, *raw_options = spec.split(",")
    validate_podman_secret_name(source, field_name="Podman secret source")

    options: dict[str, str] = {}
    for raw_option in raw_options:
        key, separator, value = raw_option.partition("=")
        if not separator or key not in {"target", "mode"} or not value or key in options:
            msg = "Podman secret specs support unique target=<absolute-path> and mode=<octal> options only"
            raise ValueError(msg)
        options[key] = value

    target = options.get("target")
    if target is not None:
        path = PurePosixPath(target)
        if (
            not path.is_absolute()
            or str(path) != target
            or ".." in path.parts
            or any(char.isspace() for char in target)
            or any(char in "'\"" for char in target)
        ):
            msg = "Podman secret target must be one normalized absolute container path"
            raise ValueError(msg)
    mode = options.get("mode")
    if mode is not None and _SECRET_MODE.fullmatch(mode) is None:
        msg = "Podman secret mode must be a four-digit octal value"
        raise ValueError(msg)
    return source


def _validated_publish_port(value: str) -> tuple[int, int]:
    """Validate one loopback-only Quadlet publish mapping."""
    _validate_unit_text(value, field_name="QuadletPod.publish_ports")
    match = _PUBLISH_PORT.fullmatch(value)
    if match is None:
        msg = "PublishPort entries must use 127.0.0.1:<host-port>:<container-port>"
        raise ValueError(msg)
    host_port, container_port = (int(part) for part in match.groups())
    if not 1 <= host_port <= _MAX_PORT or not 1 <= container_port <= _MAX_PORT:
        msg = "PublishPort host and container ports must be between 1 and 65535"
        raise ValueError(msg)
    return host_port, container_port


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
            if not MIN_VOLUME_PARTS <= len(parts) <= INDEX_OPTIONS + 1:
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
    def validate_contract(self) -> MountData:
        """Validate the path relation and the bounded Podman option grammar."""
        for field_name, path in (("host_path", self.host_path), ("container_path", self.container_path)):
            rendered_path = str(path)
            _validate_unit_text(rendered_path, field_name=f"MountData.{field_name}")
            if any(char in ":'\"" for char in rendered_path):
                msg = f"MountData.{field_name} cannot contain volume delimiters or systemd quote characters"
                raise ValueError(msg)
        unknown = sorted(set(self.options) - _MOUNT_OPTIONS)
        if unknown:
            msg = f"Unsupported or unsafe volume option(s): {', '.join(unknown)}"
            raise ValueError(msg)
        if len(self.options) != len(set(self.options)):
            msg = "Volume options must not contain duplicates"
            raise ValueError(msg)
        if {"ro", "rw"}.issubset(self.options):
            msg = "Volume options cannot request both ro and rw"
            raise ValueError(msg)
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
    binds_to: list[str] = Field(default_factory=list)
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

    @field_validator(
        "description",
        "image",
        "container_name",
        "pod",
        "pod_service",
        "user_ns",
        "exec",
        "restart_policy",
    )
    @classmethod
    def validate_scalar_directives(cls, value: str | None, info: ValidationInfo) -> str | None:
        """Keep scalar values confined to their generated unit directive."""
        if value is not None:
            _validate_unit_text(value, field_name=f"QuadletContainer.{info.field_name}")
        return value

    @field_validator("user")
    @classmethod
    def validate_user(cls, value: str | None) -> str | None:
        """Permit the one intentional systemd user specifier and no others."""
        if value is not None:
            _validate_unit_text(
                value,
                field_name="QuadletContainer.user",
                allow_specifier=value == "%U",
            )
        return value

    @field_validator(
        "wants",
        "requires",
        "after",
        "binds_to",
        "conflicts",
        "targets",
        "podman_args",
        "devices",
        "secrets",
        "wanted_by",
    )
    @classmethod
    def validate_list_directives(cls, values: list[str], info: ValidationInfo) -> list[str]:
        """Reject line and systemd-specifier injection in repeated directives."""
        for value in values:
            _validate_unit_text(value, field_name=f"QuadletContainer.{info.field_name}")
            if info.field_name == "devices" and any(char.isspace() for char in value):
                msg = "QuadletContainer.devices entries cannot contain whitespace"
                raise ValueError(msg)
            if info.field_name == "secrets":
                podman_secret_source(value)
        return values

    @field_validator("env_vars")
    @classmethod
    def validate_environment(cls, values: dict[str, str]) -> dict[str, str]:
        """Validate environment assignments before rendering them without a shell."""
        for key, value in values.items():
            systemd_environment_assignment(key, value)
        return values

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
    shm_size: str | None = None

    # [Install] section
    wanted_by: list[str] = Field(default_factory=lambda: ["default.target"])

    @field_validator("description", "pod_name", "user_ns", "shm_size")
    @classmethod
    def validate_scalar_directives(cls, value: str | None, info: ValidationInfo) -> str | None:
        """Keep pod scalar values confined to one generated directive."""
        if value is not None:
            _validate_unit_text(value, field_name=f"QuadletPod.{info.field_name}")
        if info.field_name == "pod_name" and value is not None and _UNIT_COMPONENT.fullmatch(value) is None:
            msg = "QuadletPod.pod_name must be one safe unit-name component"
            raise ValueError(msg)
        if info.field_name == "shm_size" and value is not None and _MEMORY_SIZE.fullmatch(value) is None:
            msg = "QuadletPod.shm_size must be a positive integer with an optional k/m/g/t suffix"
            raise ValueError(msg)
        return value

    @field_validator("publish_ports")
    @classmethod
    def validate_publish_ports(cls, values: list[str]) -> list[str]:
        """Accept only unique loopback host-port mappings."""
        seen_host_ports: set[int] = set()
        for value in values:
            host_port, _ = _validated_publish_port(value)
            if host_port in seen_host_ports:
                msg = f"QuadletPod.publish_ports contains duplicate host port {host_port}"
                raise ValueError(msg)
            seen_host_ports.add(host_port)
        return values

    @field_validator("wanted_by")
    @classmethod
    def validate_wanted_by(cls, values: list[str]) -> list[str]:
        for value in values:
            _validate_unit_text(value, field_name="QuadletPod.wanted_by")
        return values


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

    @field_validator("name", "description", "part_of")
    @classmethod
    def validate_scalar_directives(cls, value: str, info: ValidationInfo) -> str:
        """Keep target scalar values confined to one generated directive."""
        _validate_unit_text(value, field_name=f"QuadletTarget.{info.field_name}")
        if info.field_name == "name" and (_UNIT_COMPONENT.fullmatch(value) is None or ".." in value):
            msg = "QuadletTarget.name must be one safe unit-name component"
            raise ValueError(msg)
        return value

    @field_validator("wanted_by")
    @classmethod
    def validate_wanted_by(cls, values: list[str]) -> list[str]:
        for value in values:
            _validate_unit_text(value, field_name="QuadletTarget.wanted_by")
        return values


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

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Confine the filename to one safe unit-name component."""
        _validate_unit_text(value, field_name="SystemdService.name")
        if _UNIT_COMPONENT.fullmatch(value) is None or ".." in value:
            msg = "SystemdService.name must be one safe unit-name component"
            raise ValueError(msg)
        return value

    @field_validator("description", "exec_start", "restart", "wanted_by")
    @classmethod
    def validate_scalar_directives(cls, value: str, info: ValidationInfo) -> str:
        """Keep plain-unit scalar values inside their generated directives."""
        return _validate_unit_text(value, field_name=f"SystemdService.{info.field_name}")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, values: dict[str, str]) -> dict[str, str]:
        """Validate plain-unit assignments with the shared systemd grammar."""
        for key, value in values.items():
            systemd_environment_assignment(key, value)
        return values

    @property
    def filename(self) -> str:
        """The on-disk unit filename (e.g. ``lychd-vessel.service``)."""
        return f"{self.name}.service"

    def render(self) -> str:
        """Render the [Unit]/[Service]/[Install] text with deterministic key order.

        Environment keys are emitted sorted so the output is diff-stable across
        rewrites (Scribe idempotency); the section order is fixed.
        """
        env_lines = [
            f"Environment={systemd_environment_assignment(key, value)}"
            for key, value in sorted(self.environment.items())
        ]
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
