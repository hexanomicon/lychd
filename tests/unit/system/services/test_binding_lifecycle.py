"""Production-path safety checks for exact binding cleanup."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from lychd.system.operator import ProcessResult
from lychd.system.services.lifecycle import (
    BindingLifecycleService,
    LifecycleError,
)
from lychd.system.services.scribe import ScribeService


@dataclass
class _SystemctlRunner:
    active_returncodes: list[int] = field(default_factory=list)
    enabled_returncodes: list[int] = field(default_factory=list)
    reload_returncodes: list[int] = field(default_factory=list)
    show_results: list[tuple[int, str]] = field(default_factory=list)
    calls: list[tuple[tuple[str, ...], float]] = field(default_factory=list)

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        self.calls.append((argv, timeout_s))
        if "daemon-reload" in argv:
            returncode = self.reload_returncodes.pop(0)
            stderr = "Failed to connect to bus" if returncode else ""
            stdout = ""
        elif "is-active" in argv:
            returncode = self.active_returncodes.pop(0)
            stderr = ""
            stdout = ""
        elif "is-enabled" in argv:
            returncode = self.enabled_returncodes.pop(0)
            stderr = ""
            stdout = ""
        elif "show" in argv:
            returncode, stdout = self.show_results.pop(0)
            stderr = ""
        else:  # pragma: no cover - catches unexpected production argv
            message = f"Unexpected systemctl invocation: {argv}"
            raise AssertionError(message)
        return ProcessResult(
            argv=argv,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )


def _bound_service(
    tmp_path: Path,
    runner: _SystemctlRunner,
) -> tuple[ScribeService, BindingLifecycleService, Path]:
    quadlet_dir = tmp_path / "containers" / "systemd"
    systemd_dir = tmp_path / "systemd" / "user"
    quadlet_dir.mkdir(parents=True)
    systemd_dir.mkdir(parents=True)
    scribe = ScribeService(
        output_dir=quadlet_dir,
        systemd_dir=systemd_dir,
    )
    source = scribe.write_plain_unit(
        "lychd-vessel.service",
        "[Service]\nExecStart=/usr/bin/true\n",
    )
    lifecycle = BindingLifecycleService(
        scribe,
        runner=runner,
        systemctl_bin="/usr/bin/systemctl",
    )
    return scribe, lifecycle, source


def test_reload_failure_retains_exact_authority_for_idempotent_retry(
    tmp_path: Path,
) -> None:
    runner = _SystemctlRunner(
        active_returncodes=[3, 3, 3, 3],
        enabled_returncodes=[1, 1, 1, 1],
        reload_returncodes=[1, 0],
        show_results=[
            (
                0,
                "LoadState=not-found\nActiveState=inactive\nUnitFileState=\n",
            )
        ],
    )
    scribe, lifecycle, source = _bound_service(tmp_path, runner)
    lifecycle.plan_destroy().require_executable()

    with pytest.raises(LifecycleError, match="daemon-reload failed"):
        lifecycle.destroy()

    retained = scribe.inspect_owned_bindings()
    assert retained.receipt_present
    assert retained.systemd_sources == (source,)
    assert retained.runtime_units == ("lychd-vessel.service",)
    assert not source.exists()
    assert scribe.ownership_path.exists()

    lifecycle.plan_destroy().require_executable()
    lifecycle.destroy()

    assert not scribe.ownership_path.exists()
    assert not source.exists()
    assert all(timeout_s in {3.0, 30.0} for _, timeout_s in runner.calls)


def test_unit_restart_after_reload_blocks_authority_release(
    tmp_path: Path,
) -> None:
    runner = _SystemctlRunner(
        active_returncodes=[3, 3],
        enabled_returncodes=[1, 1],
        reload_returncodes=[0],
        show_results=[
            (
                0,
                "LoadState=loaded\nActiveState=active\nUnitFileState=disabled\n",
            )
        ],
    )
    scribe, lifecycle, source = _bound_service(tmp_path, runner)
    lifecycle.plan_destroy().require_executable()

    with pytest.raises(LifecycleError, match="not stably inactive"):
        lifecycle.destroy()

    retained = scribe.inspect_owned_bindings()
    assert retained.receipt_present
    assert retained.systemd_sources == (source,)
    assert retained.runtime_units == ("lychd-vessel.service",)
    assert not source.exists()
    assert scribe.ownership_path.exists()
