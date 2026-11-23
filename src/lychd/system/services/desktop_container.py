"""Bounded lifecycle operations on an explicitly provisioned local container."""

from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
import ssl
import stat
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import JsonValue, TypeAdapter

from lychd.domain.orchestration.actuator import RuntimePreconditionError
from lychd.system.desktop.private import check_native_inputs

if TYPE_CHECKING:
    from lychd.config.settings.orchestration import DesktopContainerBinding

_STOPPED = frozenset({"created", "configured", "exited", "stopped"})
_ENGINE_INFO = TypeAdapter(dict[str, JsonValue])
_INSPECT_RESPONSE = TypeAdapter(list[dict[str, JsonValue]])


def _record(value: JsonValue | None) -> dict[str, JsonValue]:
    if isinstance(value, dict):
        return value
    message = "Container engine response is missing a required identity record."
    raise RuntimePreconditionError(message)


class UnsettledContainerError(RuntimeError):
    """An engine operation may still take effect. Keep the transition fenced."""


class DesktopContainer:
    """Inspect, start and stop one exact container on its explicitly selected local engine."""

    def __init__(self, binding: DesktopContainerBinding, *, timeout: float) -> None:
        """Bind immutable operator-supplied engine and container identity."""
        self.binding = binding
        self.timeout = timeout

    def _command(self, *arguments: str) -> str:
        binding = self.binding
        if os.name == "nt":
            # Docker Desktop's Linux backend is exposed through this local named pipe.
            if binding.engine != "docker" or binding.endpoint != "npipe:////./pipe/dockerDesktopLinuxEngine":
                message = "Windows desktop containers require Docker Desktop's local Linux engine pipe."
                raise RuntimePreconditionError(message)
            executable = Path(os.environ["PROGRAMFILES"]) / "Docker/Docker/resources/bin/docker.exe"
        else:
            if not binding.endpoint.startswith("unix:///"):
                message = "This host requires an absolute local container engine socket."
                raise RuntimePreconditionError(message)
            socket_path = Path(binding.endpoint.removeprefix("unix://"))
            metadata = socket_path.lstat()
            if not stat.S_ISSOCK(metadata.st_mode) or metadata.st_uid != os.getuid():
                message = "Desktop container engine socket must be owned by the runtime account."
                raise RuntimePreconditionError(message)
            binary = shutil.which(binding.engine)
            if binary is None:
                message = f"Desktop container engine client is unavailable: {binding.engine}"
                raise RuntimePreconditionError(message)
            executable = Path(binary).resolve(strict=True)
            check_native_inputs(executable, socket_path.parent)
        env = {
            key: os.environ[key]
            for key in ("SYSTEMROOT", "WINDIR", "HOME", "USERPROFILE", "XDG_RUNTIME_DIR")
            if key in os.environ
        }
        option = "--host" if binding.engine == "docker" else "--url"
        result = subprocess.run(  # noqa: S603 - trusted binary, local engine and typed verbs only
            [str(executable), option, binding.endpoint, *arguments],
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=True,
        )
        return result.stdout

    def verify_engine(self) -> None:
        """Admit rootless Linux engines and Docker Desktop's local Linux engine."""
        binding = self.binding
        if binding.engine == "docker":
            info = _ENGINE_INFO.validate_json(self._command("info", "--format", "{{json .}}"))
            options = info.get("SecurityOptions")
            rootless = isinstance(options, list) and any(
                isinstance(item, str) and "name=rootless" in item.split(",") for item in options
            )
            approved = info.get("OSType") == "linux" and (rootless or info.get("OperatingSystem") == "Docker Desktop")
        else:
            info = _ENGINE_INFO.validate_json(self._command("info", "--format", "json"))
            approved = _record(_record(info.get("host")).get("security")).get("rootless") is True
        if not approved:
            message = "Desktop container engine must be rootless or a local Docker Desktop Linux engine."
            raise RuntimePreconditionError(message)

    def observe(self, *, stopped_incarnation: str | None = None) -> str | None:
        """Return the running incarnation or a verified stopped state for this binding."""
        binding = self.binding
        entries = _INSPECT_RESPONSE.validate_json(self._command("container", "inspect", binding.container_id))
        if len(entries) != 1:
            message = "Expected exactly one container inspection."
            raise RuntimePreconditionError(message)
        return self._inspect(entries[0], stopped_incarnation=stopped_incarnation)

    def _inspect(self, entry: dict[str, JsonValue], *, stopped_incarnation: str | None) -> str | None:
        binding = self.binding
        config = _record(entry.get("Config"))
        host = _record(entry.get("HostConfig"))
        state = _record(entry.get("State"))
        network = host.get("NetworkMode")
        ports = {f"{binding.container_port}/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(binding.host_port)}]}
        if (
            entry.get("Id") != binding.container_id
            or _record(config.get("Labels")).get("io.lychd.soulstone") != binding.animator
            or host.get("PortBindings") != ports
            or host.get("Privileged") is not False
            or entry.get("Pod")
            or entry.get("Dependencies")
            or host.get("Links")
            or host.get("VolumesFrom")
            or not isinstance(network, str)
            or network in ("host", "none")
            or network.startswith("container:")
            or host.get("PublishAllPorts") is True
            or host.get("AutoRemove") is not False
            or _record(host.get("RestartPolicy")).get("Name") not in ("no", "none", "")
        ):
            message = f"Container identity, loopback binding or lifecycle ownership changed for {binding.animator!r}."
            raise RuntimePreconditionError(message)
        if any(state.get(flag) for flag in ("Paused", "Restarting", "Dead", "RemovalInProgress")):
            message = "Container is not in a settled lifecycle state."
            raise UnsettledContainerError(message)
        status = state.get("Status")
        if isinstance(status, str) and status in _STOPPED and state.get("Running") is False:
            if stopped_incarnation is not None and state.get("StartedAt") != stopped_incarnation:
                message = "Stopped container incarnation differs from the authorized owner."
                raise UnsettledContainerError(message)
            return None
        if (
            status == "running"
            and state.get("Running") is True
            and isinstance(started := state.get("StartedAt"), str)
            and started
        ):
            return started
        message = "Container inspection did not establish a settled incarnation."
        raise UnsettledContainerError(message)

    def change(self, action: Literal["start", "stop"], *, expected: str | None = None) -> str | None:
        """Recheck authority before changing only the pinned ID; classify ambiguous submission."""
        self.verify_engine()
        previous = self.observe()
        if previous != expected or (action == "start") != (previous is None):
            message = f"Container {self.binding.animator!r} changed before {action}."
            raise RuntimePreconditionError(message)
        try:
            self._command("container", action, self.binding.container_id)
            current = self.observe(stopped_incarnation=expected)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            message = "Container operation outcome is unresolved."
            raise UnsettledContainerError(message) from exc
        if (action == "start") != (current is not None):
            message = "Container did not reach its requested state."
            raise UnsettledContainerError(message)
        return current

    async def connect(self, incarnation: str) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Verify the TLS peer and running incarnation before sending private inference bytes."""
        # The operator pins the exact leaf certificate, including private/self-signed issuers.
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        reader, writer = await asyncio.open_connection("127.0.0.1", self.binding.host_port, ssl=context)
        try:
            await self._verify_peer(writer, incarnation)
        except BaseException:
            writer.close()
            raise
        return reader, writer

    async def _verify_peer(self, writer: asyncio.StreamWriter, incarnation: str) -> None:
        peer = writer.get_extra_info("ssl_object").getpeercert(binary_form=True)
        if (
            not peer
            or hashlib.sha256(peer).hexdigest() != self.binding.tls_sha256
            or await asyncio.to_thread(self.observe) != incarnation
        ):
            message = "Container TLS listener or running incarnation differs from its binding."
            raise RuntimePreconditionError(message)
