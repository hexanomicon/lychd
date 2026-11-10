"""Read-only host and secret-boundary checks shared by bind preview and apply."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol

from lychd.system.constants import PATH_LYCHD_TOML, PATH_SYSTEMD_USER_UNITS_DIR
from lychd.system.path_safety import path_has_symlink_component
from lychd.system.readiness import (
    BindingFoundation,
    HostFoundationError,
    HostFoundationInspection,
    HostReadinessService,
    ReadinessState,
)

_REACTOR_DIRECTORY_MODE = 0o700

if TYPE_CHECKING:
    from lychd.config.settings.root import Settings

type BindingPreflightIssueCode = Literal[
    "codex-shape",
    "codex-mode",
    "codex-owner",
    "host-foundation",
    "legacy-vessel-unit",
    "caged-actuator",
    "reactor-shape",
    "reactor-mode",
    "reactor-owner",
    "retired-vessel-binding",
]


class HostReadinessPort(Protocol):
    """Read-only source of the one authoritative host-foundation report."""

    def inspect(self) -> HostFoundationInspection:
        """Return current capability, site, and trusted-tool evidence."""
        ...


@dataclass(frozen=True, slots=True)
class BindingPreflightIssue:
    """One stable, operator-renderable reason binding cannot proceed."""

    code: BindingPreflightIssueCode
    target: str
    detail: str


@dataclass(frozen=True, slots=True)
class BindingPreflightReport:
    """The complete read-only prerequisite result for one bind plan."""

    issues: tuple[BindingPreflightIssue, ...]
    foundation: BindingFoundation | None

    @property
    def systemctl_bin(self) -> str | None:
        """Retain the concise renderer projection of trusted systemctl."""
        return self.foundation.systemctl_bin if self.foundation is not None else None

    @property
    def ready(self) -> bool:
        """Return whether the same plan may be previewed or applied as coherent."""
        return not self.issues

    def require_ready(self) -> BindingFoundation:
        """Return every attested authority tool or fail with the full report."""
        if self.issues:
            raise BindingPreflightError(self)
        if self.foundation is None:  # pragma: no cover - enforced by the foundation issue
            msg = "A ready binding preflight must contain trusted host-foundation evidence."
            raise AssertionError(msg)
        return self.foundation


class BindingPreflightError(RuntimeError):
    """Raised after rendering when a binding preflight is not executable."""

    def __init__(self, report: BindingPreflightReport) -> None:
        """Retain the report while exposing a concise command-boundary message."""
        self.report = report
        detail = "; ".join(f"{issue.target}: {issue.detail}" for issue in report.issues)
        super().__init__(f"Binding preflight failed: {detail}")


class BindingPreflightService:
    """Inspect bind prerequisites without loading configuration or mutating the host."""

    def __init__(
        self,
        *,
        codex_path: Path = PATH_LYCHD_TOML,
        legacy_vessel_unit_path: Path = PATH_SYSTEMD_USER_UNITS_DIR / "lychd-vessel.service",
        current_uid: int | None = None,
        host_readiness: HostReadinessPort | None = None,
    ) -> None:
        """Bind inspection to explicit, replaceable host dependencies."""
        self._codex_path = codex_path
        self._legacy_vessel_unit_path = legacy_vessel_unit_path
        self._current_uid = os.getuid() if current_uid is None else current_uid
        self._host_readiness = host_readiness or HostReadinessService(
            current_uid=self._current_uid,
        )

    def inspect(self, settings: Settings) -> BindingPreflightReport:
        """Return every blocker for the sole container binding generation."""
        issues = [*self._inspect_codex(), *self._inspect_legacy_vessel_unit()]
        host = self._host_readiness.inspect()
        report = host.report
        foundation: BindingFoundation | None = None
        issues.extend(
            BindingPreflightIssue(
                code="host-foundation",
                target=item.label,
                detail=item.detail,
            )
            for item in report.items
            if item.required_for_bind and item.state is not ReadinessState.VERIFIED
        )
        if not any(issue.code == "host-foundation" for issue in issues):
            try:
                foundation = host.require_ready_for_bind()
            except HostFoundationError as exc:
                issues.append(
                    BindingPreflightIssue(
                        code="host-foundation",
                        target="host foundation",
                        detail=str(exc),
                    )
                )

        issues.extend(self._inspect_caged(settings))
        if foundation is not None:
            issues.extend(self._inspect_retired_vessel_bindings(foundation))

        return BindingPreflightReport(
            issues=tuple(issues),
            foundation=foundation,
        )

    @staticmethod
    def _inspect_retired_vessel_bindings(foundation: BindingFoundation) -> list[BindingPreflightIssue]:
        """Preserve retired host-native generations instead of reconciling them away."""
        from lychd.system.services.scribe import ScribeService

        retired_unit = "lychd-uncaged-vessel.service"
        sources = (
            foundation.sites.systemd_user.path / retired_unit,
            foundation.sites.quadlet.path / "lychd-uncaged-vessel.container",
        )
        owned = ScribeService(expected_sites=foundation.sites).inspect_owned_bindings()
        if retired_unit not in owned.runtime_units and not any(os.path.lexists(path) for path in sources):
            return []
        return [
            BindingPreflightIssue(
                code="retired-vessel-binding",
                target="existing host-native Vessel binding",
                detail=(
                    "Container binding refuses a retired host-native or mixed generation; "
                    "no conversion, removal, or service control is performed."
                ),
            )
        ]

    def _inspect_legacy_vessel_unit(self) -> list[BindingPreflightIssue]:
        """Reject the obsolete static unit before preview and locked apply."""
        if not os.path.lexists(self._legacy_vessel_unit_path):
            return []
        return [
            BindingPreflightIssue(
                code="legacy-vessel-unit",
                target=str(self._legacy_vessel_unit_path),
                detail=(
                    "legacy static unit shadows the caged Quadlet service; disable and remove it "
                    "before binding through a separately reviewed operator recovery"
                ),
            )
        ]

    def _inspect_codex(self) -> list[BindingPreflightIssue]:
        issues: list[BindingPreflightIssue] = []
        if symlink := path_has_symlink_component(self._codex_path):
            return [
                BindingPreflightIssue(
                    code="codex-shape",
                    target=str(self._codex_path),
                    detail=f"Codex traverses an untrusted symlink component: {symlink}",
                )
            ]
        try:
            metadata = self._codex_path.lstat()
        except OSError as exc:
            issues.append(
                BindingPreflightIssue(
                    code="codex-shape",
                    target=str(self._codex_path),
                    detail=f"Codex must exist as a real regular file: {exc}",
                )
            )
            return issues

        if self._codex_path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            issues.append(
                BindingPreflightIssue(
                    code="codex-shape",
                    target=str(self._codex_path),
                    detail="Codex must exist as a real regular file",
                )
            )
            return issues

        if metadata.st_uid != self._current_uid:
            issues.append(
                BindingPreflightIssue(
                    code="codex-owner",
                    target=str(self._codex_path),
                    detail=f"Codex is owned by uid {metadata.st_uid}; expected {self._current_uid}",
                )
            )
        mode = stat.S_IMODE(metadata.st_mode)
        if mode & 0o077:
            issues.append(
                BindingPreflightIssue(
                    code="codex-mode",
                    target=str(self._codex_path),
                    detail=f"Codex mode is {oct(mode)}; group and other access must be closed",
                )
            )
        return issues

    def _inspect_caged(self, settings: Settings) -> list[BindingPreflightIssue]:
        switching = settings.orchestration.switching
        issues: list[BindingPreflightIssue] = []
        if switching.actuator != "host-reactor":
            issues.append(
                BindingPreflightIssue(
                    code="caged-actuator",
                    target="orchestration.switching.actuator",
                    detail="caged binding requires 'host-reactor'",
                )
            )
        issues.extend(self._inspect_reactor_directory(switching.host_reactor_dir, label="inbox"))
        issues.extend(
            self._inspect_reactor_directory(
                switching.host_reactor_journal_dir,
                label="journal",
            )
        )
        return issues

    def _inspect_reactor_directory(
        self,
        path: Path,
        *,
        label: str,
    ) -> list[BindingPreflightIssue]:
        issues: list[BindingPreflightIssue] = []
        if symlink := path_has_symlink_component(path):
            return [
                BindingPreflightIssue(
                    code="reactor-shape",
                    target=str(path),
                    detail=(f"Host Reactor {label} traverses an untrusted symlink component: {symlink}"),
                )
            ]
        try:
            metadata = path.lstat()
        except OSError as exc:
            issues.append(
                BindingPreflightIssue(
                    code="reactor-shape",
                    target=str(path),
                    detail=f"Host Reactor {label} must exist as a real directory: {exc}",
                )
            )
            return issues

        if path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
            issues.append(
                BindingPreflightIssue(
                    code="reactor-shape",
                    target=str(path),
                    detail=f"Host Reactor {label} must exist as a real directory",
                )
            )
            return issues

        if metadata.st_uid != self._current_uid:
            issues.append(
                BindingPreflightIssue(
                    code="reactor-owner",
                    target=str(path),
                    detail=(f"Host Reactor {label} is owned by uid {metadata.st_uid}; expected {self._current_uid}"),
                )
            )
        mode = stat.S_IMODE(metadata.st_mode)
        if mode != _REACTOR_DIRECTORY_MODE:
            issues.append(
                BindingPreflightIssue(
                    code="reactor-mode",
                    target=str(path),
                    detail=f"Host Reactor {label} mode is {oct(mode)}; expected 0o700",
                )
            )
        return issues
