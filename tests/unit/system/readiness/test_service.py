from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from lychd.system.host_foundation import (
    QUADLET_SOURCES_READINESS_KEY,
    SYSTEMD_USER_UNITS_READINESS_KEY,
)
from lychd.system.host_tools import TrustedExecutable
from lychd.system.operator import ProcessResult
from lychd.system.readiness import HostReadinessService, HostReadinessTools


class _Runner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        assert timeout_s == 3.0
        self.calls.append(argv)
        return ProcessResult(
            argv=argv,
            returncode=0,
            stdout="257.5\n",
        )


def _tools(systemctl: str) -> HostReadinessTools:
    return HostReadinessTools(
        systemctl=TrustedExecutable(
            path=systemctl,
            device=1,
            inode=abs(hash(systemctl)) + 1,
        ),
        podman=None,
        quadlet_user_generator=None,
        findmnt=None,
        btrfs=None,
        chattr=None,
        lsattr=None,
        getenforce=None,
    )


def _service(
    tmp_path: Path,
    *,
    runner: _Runner,
    tools: HostReadinessTools | None = None,
    tools_factory: Callable[[], HostReadinessTools],
) -> HostReadinessService:
    return HostReadinessService(
        runner=runner,
        tools=tools,
        tools_factory=tools_factory,
        postgres_data=tmp_path / "postgres" / "data",
        binding_sites=(
            (
                QUADLET_SOURCES_READINESS_KEY,
                "Quadlet sources",
                tmp_path / "quadlet",
            ),
            (
                SYSTEMD_USER_UNITS_READINESS_KEY,
                "systemd user units",
                tmp_path / "systemd",
            ),
        ),
        selinux_enforce_path=tmp_path / "selinux-enforce",
        cgroup_v2_controllers_path=tmp_path / "cgroup.controllers",
        current_uid=1000,
    )


def test_production_inspection_rediscovers_one_tool_snapshot_per_call(
    tmp_path: Path,
) -> None:
    runner = _Runner()
    discovered = iter((_tools("/systemctl-a"), _tools("/systemctl-b")))
    calls = 0

    def discover() -> HostReadinessTools:
        nonlocal calls
        calls += 1
        return next(discovered)

    service = _service(
        tmp_path,
        runner=runner,
        tools_factory=discover,
    )

    first = service.inspect()
    second = service.inspect()

    assert calls == 2
    assert first.tools.systemctl is not None
    assert second.tools.systemctl is not None
    assert first.tools.systemctl.path == "/systemctl-a"
    assert second.tools.systemctl.path == "/systemctl-b"
    assert (
        "/systemctl-a",
        "--user",
        "show",
        "--property=Version",
        "--value",
    ) in runner.calls
    assert (
        "/systemctl-b",
        "--user",
        "show",
        "--property=Version",
        "--value",
    ) in runner.calls


def test_explicit_tools_remain_stable_across_inspections(tmp_path: Path) -> None:
    runner = _Runner()
    fixed = _tools("/fixed-systemctl")
    discovery_calls = 0

    def unexpected_discovery() -> HostReadinessTools:
        nonlocal discovery_calls
        discovery_calls += 1
        return _tools("/unexpected-systemctl")

    service = _service(
        tmp_path,
        runner=runner,
        tools=fixed,
        tools_factory=unexpected_discovery,
    )

    first = service.inspect()
    second = service.inspect()

    assert first.tools is fixed
    assert second.tools is fixed
    assert discovery_calls == 0
