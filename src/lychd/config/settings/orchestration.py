"""Settings for run routing, durable stasis, and runtime switching."""

from __future__ import annotations

import os
import posixpath
import re
from pathlib import Path
from typing import Literal, cast

from pydantic import ConfigDict, Field, field_validator, model_validator

from lychd.config.settings.section import SettingsSection
from lychd.config.settings.server import QUEUE_NAMES
from lychd.system.constants import PATH_REACTOR_INBOX_DIR


class RoutingRule(SettingsSection):
    """One semantic run source's physical queue and priority."""

    queue: str = "runs"
    """Physical queue that receives intents from this semantic source."""
    priority: int = Field(default=50, ge=0, le=100)
    """Default urgency from 0 (background) through 100 (most urgent)."""


class DesktopContainerBinding(SettingsSection):
    """Operator-owned identity of a pre-provisioned fixed-model desktop container."""

    model_config = ConfigDict(frozen=True)

    animator: str = Field(min_length=1)
    engine: Literal["docker", "podman"]
    endpoint: str
    container_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    container_port: int = Field(ge=1, le=65535)
    host_port: int = Field(ge=1, le=65535)
    tls_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("endpoint")
    @classmethod
    def local_engine_endpoint(cls, value: str) -> str:
        """Admit only an absolute local Unix socket or a local named pipe."""
        if re.fullmatch(r"npipe:////[.]/pipe/[a-zA-Z0-9_.-]+", value):
            return value
        if value.startswith("unix:///"):
            path = value.removeprefix("unix://")
            if (
                not path.startswith("//")
                and not any(char in path for char in ("%", "?", "#", chr(92)))
                and path.isprintable()
                and posixpath.normpath(path) == path
                and ".." not in path.split("/")
            ):
                return value
        message = "Container endpoint must name one local Unix socket or named pipe."
        raise ValueError(message)


class SwitchingSettings(SettingsSection):
    """Hard-swap and Host Reactor policy."""

    policy: Literal["declared-conflicts", "evict-idle"] = "declared-conflicts"
    """Default conflict policy used when a requested runtime needs a hardware transition."""
    actuator: Literal["systemd", "host-reactor", "native-process"] = "host-reactor"
    """Transition executor: caged Host Reactor by default, direct systemd only for development."""
    native_state_dir: Path | None = None
    """Private installation directory for the personal native process journal."""
    native_llama_server: Path | None = None
    """Trusted absolute llama-server executable for locally owned single-model processes."""
    native_model_root: Path | None = None
    """Local directory containing the operator's native GGUF files."""
    containers: tuple[DesktopContainerBinding, ...] = ()
    """Locally provisioned fixed containers authorized for desktop lifecycle operations."""
    host_reactor_dir: Path = PATH_REACTOR_INBOX_DIR
    """Owner-only Host Reactor inbox; its sibling journal is derived automatically."""
    min_priority_for_hard_swap: int = Field(default=40, ge=0, le=100)
    """Lowest request priority allowed to trigger a disruptive hard runtime swap."""
    planning_timeout_s: float = Field(default=30.0, gt=0, allow_inf_nan=False)
    """Maximum seconds for all managed-runtime observations in each preflight or replan."""
    drain_timeout_s: float = Field(default=120.0, gt=0, allow_inf_nan=False)
    """Maximum seconds to wait for active work to reach a safe transition boundary."""
    warmup_timeout_s: float = Field(default=180.0, gt=0, allow_inf_nan=False)
    """Maximum seconds to wait for a newly activated runtime to become usable."""
    systemctl_timeout_s: float = Field(default=120.0, gt=0, allow_inf_nan=False)
    """Maximum seconds for each trusted systemctl client process to respond."""
    reactor_ack_timeout_s: float = Field(default=120.0, gt=0, allow_inf_nan=False)
    """Maximum seconds for the Host Reactor to claim an inbox transition intent."""

    @model_validator(mode="after")
    def validate_native_profile(self) -> SwitchingSettings:
        for field in ("animator", "container_id", "host_port"):
            if len({getattr(binding, field) for binding in self.containers}) != len(self.containers):
                message = f"Duplicate desktop container {field}."
                raise ValueError(message)
        if self.actuator == "native-process":
            if self.native_state_dir is None or not self.native_state_dir.is_absolute():
                msg = "native-process requires an absolute native_state_dir"
                raise ValueError(msg)
            if (self.native_llama_server is None) != (self.native_model_root is None):
                msg = "native_llama_server and native_model_root must be configured together"
                raise ValueError(msg)
            for path in (self.native_llama_server, self.native_model_root):
                if path is not None and not path.is_absolute():
                    msg = "Native executable and model root paths must be absolute"
                    raise ValueError(msg)
        return self

    @staticmethod
    def _normalize_control_path(value: Path | str, *, field_name: str) -> Path:
        """Return one safe, lexical spelling of a systemd-facing control path."""
        try:
            candidate = Path(value).expanduser()
        except (TypeError, ValueError, RuntimeError) as exc:
            msg = f"{field_name} is not a valid filesystem path: {value}"
            raise ValueError(msg) from exc
        path_text = os.fspath(candidate)
        if "%" in path_text or "\\" in path_text or any(not char.isprintable() for char in path_text):
            msg = f"{field_name} contains characters that are unsafe in a systemd path"
            raise ValueError(msg)
        if not candidate.is_absolute():
            msg = f"{field_name} must be an absolute path: {value}"
            raise ValueError(msg)
        normalized = os.path.normpath(candidate)
        if normalized.startswith("//"):
            normalized = f"/{normalized.lstrip('/')}"
        return Path(normalized)

    @field_validator("host_reactor_dir", mode="before")
    @classmethod
    def validate_host_reactor_dir(cls, value: Path | str) -> Path:
        inbox = cls._normalize_control_path(
            value,
            field_name="orchestration.switching.host_reactor_dir",
        )
        if inbox.name != "inbox":
            msg = "orchestration.switching.host_reactor_dir must be an 'inbox' directory"
            raise ValueError(msg)
        return inbox

    @property
    def host_reactor_journal_dir(self) -> Path:
        return self.host_reactor_dir.parent / "journal"


def _default_routing_settings() -> dict[str, RoutingRule]:
    return {
        "default": RoutingRule(queue="runs", priority=50),
        "cli": RoutingRule(queue="runs", priority=50),
        "bridge": RoutingRule(queue="runs", priority=70),
        "rite": RoutingRule(queue="rites", priority=20),
    }


class OrchestrationSettings(SettingsSection):
    """Run routing, durable stasis, and runtime switching policy."""

    routing: dict[str, RoutingRule] = Field(default_factory=_default_routing_settings)
    """Mapping from intent source to its queue and default priority."""
    switching: SwitchingSettings = Field(default_factory=SwitchingSettings)
    """Hardware-transition and Host Reactor policy."""

    @model_validator(mode="before")
    @classmethod
    def merge_required_routing(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(cast("dict[str, object]", value))
        configured_routing = data.get("routing")
        if isinstance(configured_routing, dict):
            routing: dict[str, object] = dict(_default_routing_settings())
            routing.update(cast("dict[str, object]", configured_routing))
            data["routing"] = routing
        return data

    @model_validator(mode="after")
    def validate_routing_topology(self) -> OrchestrationSettings:
        missing = sorted({rule.queue for rule in self.routing.values()}.difference(QUEUE_NAMES))
        if missing:
            msg = f"Orchestration routing references unknown queues: {', '.join(missing)}"
            raise ValueError(msg)
        return self
