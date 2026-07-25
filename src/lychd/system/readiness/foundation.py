"""Systemd, Podman/Quadlet, cgroup, and SELinux host probes."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

from lychd.system.operator.process import (
    ProcessInvocationError,
    ProcessResult,
    ProcessRunner,
)
from lychd.system.readiness.models import (
    HostReadinessItem,
    ReadinessSection,
    ReadinessState,
)
from lychd.system.readiness.tools import HostReadinessTools

_PROBE_TIMEOUT_SECONDS: Final = 3.0
_MINIMUM_PODMAN_VERSION: Final = (5, 4)
_VERSION_PATTERN: Final = re.compile(r"\b(\d+)\.(\d+)(?:\.(\d+))?\b")


class FoundationReadinessProbe:
    """Inspect required runtime foundation and optional SELinux posture."""

    def __init__(
        self,
        *,
        runner: ProcessRunner,
        tools: HostReadinessTools,
        selinux_enforce_path: Path,
        cgroup_v2_controllers_path: Path,
        current_uid: int,
    ) -> None:
        """Bind probes to explicit process, tool, path, and identity inputs."""
        self._runner = runner
        self._tools = tools
        self._selinux_enforce_path = selinux_enforce_path
        self._cgroup_v2_controllers_path = cgroup_v2_controllers_path
        self._current_uid = current_uid

    def systemd(self) -> HostReadinessItem:
        """Verify that the current user's systemd manager is reachable."""
        systemctl = self._tools.systemctl
        if systemctl is None:
            return self._failed_systemd("trusted systemctl executable is unavailable")
        result = self._run(
            (systemctl, "--user", "show", "--property=Version", "--value"),
        )
        if isinstance(result, str):
            return self._failed_systemd(f"manager probe failed: {result}")
        if result.returncode != 0:
            return self._failed_systemd(
                f"not reachable: {self._result_error(result)}",
            )
        version = self._display_version(result.stdout)
        return HostReadinessItem(
            key="systemd-user",
            label="systemd user manager",
            section=ReadinessSection.FOUNDATION,
            state=ReadinessState.VERIFIED,
            detail=f"systemd {version} · reachable" if version else "reachable",
            required_for_bind=True,
        )

    def podman_quadlet(self) -> HostReadinessItem:  # noqa: PLR0911 - each prerequisite has a precise verdict
        """Verify compatible Podman, effective Quadlet, cgroup v2, and user scope."""
        if self._current_uid == 0:
            return self._failed_podman("run LychD as an ordinary user, not root")
        podman = self._tools.podman
        generator = self._tools.quadlet_user_generator
        if podman is None:
            return self._failed_podman("trusted Podman CLI unavailable")
        if generator is None:
            return self._failed_podman("Quadlet user generator unavailable")
        if not self._cgroup_v2_controllers_path.is_file():
            return self._failed_podman("cgroup v2 controllers are unavailable")

        podman_version = self._probe_version(podman)
        generator_version = self._probe_version(generator)
        if isinstance(podman_version, str):
            return self._failed_podman(f"Podman version probe failed: {podman_version}")
        if isinstance(generator_version, str):
            return self._failed_podman(f"Quadlet version probe failed: {generator_version}")
        minimum = ".".join(str(part) for part in _MINIMUM_PODMAN_VERSION)
        if podman_version[:2] < _MINIMUM_PODMAN_VERSION:
            return self._failed_podman(
                f"Podman {self._version_text(podman_version)} is older than required {minimum}",
            )
        if generator_version[:2] < _MINIMUM_PODMAN_VERSION:
            return self._failed_podman(
                f"Quadlet {self._version_text(generator_version)} is older than required {minimum}",
            )
        versions = (
            f"Podman {self._version_text(podman_version)}"
            if podman_version == generator_version
            else (
                f"Podman {self._version_text(podman_version)} · "
                f"Quadlet {self._version_text(generator_version)}"
            )
        )
        return HostReadinessItem(
            key="podman-quadlet",
            label="Podman / Quadlet",
            section=ReadinessSection.FOUNDATION,
            state=ReadinessState.VERIFIED,
            detail=f"{versions} · user generator · cgroup v2",
            required_for_bind=True,
        )

    def selinux(self) -> HostReadinessItem:
        """Observe the runtime SELinux mode without making it a bind blocker."""
        try:
            raw_mode = self._selinux_enforce_path.read_text(encoding="ascii").strip()
        except OSError:
            raw_mode = self._getenforce_mode()
        mode = raw_mode.casefold()
        if mode in {"1", "enforcing"}:
            state = ReadinessState.VERIFIED
            detail = "enforcing · private :Z labels active"
        elif mode in {"0", "permissive"}:
            state = ReadinessState.DEGRADED
            detail = "permissive · label enforcement inactive"
        elif mode == "disabled":
            state = ReadinessState.OPTIONAL
            detail = "disabled · optional MAC hardening unavailable"
        else:
            state = ReadinessState.UNKNOWN
            detail = "runtime mode could not be verified"
        return HostReadinessItem(
            key="selinux",
            label="SELinux",
            section=ReadinessSection.FOUNDATION,
            state=state,
            detail=detail,
        )

    def _probe_version(self, executable: str) -> tuple[int, int, int] | str:
        result = self._run((executable, "--version"))
        if isinstance(result, str):
            return result
        if result.returncode != 0:
            return self._result_error(result)
        match = _VERSION_PATTERN.search(f"{result.stdout}\n{result.stderr}")
        if match is None:
            return "version could not be verified"
        major, minor, patch = match.groups()
        return (int(major), int(minor), int(patch or 0))

    def _getenforce_mode(self) -> str:
        getenforce = self._tools.getenforce
        if getenforce is None:
            return ""
        result = self._run((getenforce,))
        return result.stdout.strip() if isinstance(result, ProcessResult) and result.returncode == 0 else ""

    def _run(self, argv: tuple[str, ...]) -> ProcessResult | str:
        try:
            return self._runner.run(argv, timeout_s=_PROBE_TIMEOUT_SECONDS)
        except ProcessInvocationError as exc:
            return self._brief(str(exc))

    @staticmethod
    def _brief(value: str) -> str:
        return " ".join(value.split())[:240]

    @classmethod
    def _result_error(cls, result: ProcessResult) -> str:
        return cls._brief(result.stderr) or f"exit {result.returncode}"

    @staticmethod
    def _version_text(version: tuple[int, int, int]) -> str:
        return ".".join(str(part) for part in version)

    @staticmethod
    def _display_version(value: str) -> str:
        match = _VERSION_PATTERN.search(value)
        if match is None:
            return ""
        return ".".join(part for part in match.groups() if part is not None)

    @staticmethod
    def _failed_systemd(detail: str) -> HostReadinessItem:
        return HostReadinessItem.failed(
            key="systemd-user",
            label="systemd user manager",
            detail=detail,
            required=True,
        )

    @staticmethod
    def _failed_podman(detail: str) -> HostReadinessItem:
        return HostReadinessItem.failed(
            key="podman-quadlet",
            label="Podman / Quadlet",
            detail=detail,
            required=True,
        )


__all__ = ("FoundationReadinessProbe",)
