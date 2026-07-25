from __future__ import annotations

from pathlib import Path

import pytest

from lychd.system.operator import ProcessResult
from lychd.system.readiness import HostReadinessTools, ReadinessState
from lychd.system.readiness.foundation import FoundationReadinessProbe


class _Runner:
    def __init__(self, responses: dict[tuple[str, ...], ProcessResult]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        assert timeout_s == 3.0
        self.calls.append(argv)
        return self.responses[argv]


def _tools() -> HostReadinessTools:
    return HostReadinessTools(
        systemctl="/systemctl",
        podman="/podman",
        quadlet_user_generator="/quadlet",
        findmnt="/findmnt",
        btrfs="/btrfs",
        chattr="/chattr",
        lsattr="/lsattr",
        getenforce="/getenforce",
    )


def _probe(
    tmp_path: Path,
    *,
    podman_version: str = "podman version 5.8.3",
    quadlet_version: str = "5.8.3",
) -> FoundationReadinessProbe:
    cgroup = tmp_path / "cgroup.controllers"
    cgroup.write_text("cpu memory", encoding="ascii")
    enforcing = tmp_path / "enforce"
    enforcing.write_text("1\n", encoding="ascii")
    return FoundationReadinessProbe(
        runner=_Runner(
            {
                (
                    "/systemctl",
                    "--user",
                    "show",
                    "--property=Version",
                    "--value",
                ): ProcessResult(argv=(), returncode=0, stdout="257.5\n"),
                ("/podman", "--version"): ProcessResult(
                    argv=(),
                    returncode=0,
                    stdout=podman_version,
                ),
                ("/quadlet", "--version"): ProcessResult(
                    argv=(),
                    returncode=0,
                    stdout=quadlet_version,
                ),
            }
        ),
        tools=_tools(),
        selinux_enforce_path=enforcing,
        cgroup_v2_controllers_path=cgroup,
        current_uid=1000,
    )


def test_required_foundation_is_verified_from_bounded_probes(tmp_path: Path) -> None:
    probe = _probe(tmp_path)

    systemd = probe.systemd()
    podman = probe.podman_quadlet()
    selinux = probe.selinux()

    assert systemd.state is ReadinessState.VERIFIED
    assert systemd.required_for_bind
    assert systemd.detail == "systemd 257.5 · reachable"
    assert podman.state is ReadinessState.VERIFIED
    assert podman.required_for_bind
    assert podman.detail == "Podman 5.8.3 · user generator · cgroup v2"
    assert selinux.state is ReadinessState.VERIFIED
    assert "enforcing" in selinux.detail


@pytest.mark.parametrize(
    ("podman_version", "quadlet_version", "expected"),
    [
        ("podman version 5.3.2", "5.8.3", "Podman 5.3.2 is older"),
        ("podman version 5.8.3", "5.3.2", "Quadlet 5.3.2 is older"),
        ("not-a-version", "5.8.3", "version could not be verified"),
    ],
)
def test_incompatible_or_unverifiable_versions_block_bind_foundation(
    tmp_path: Path,
    podman_version: str,
    quadlet_version: str,
    expected: str,
) -> None:
    item = _probe(
        tmp_path,
        podman_version=podman_version,
        quadlet_version=quadlet_version,
    ).podman_quadlet()

    assert item.state is ReadinessState.BLOCKED
    assert item.required_for_bind
    assert expected in item.detail


@pytest.mark.parametrize(
    ("mode", "expected_state", "expected_detail"),
    [
        ("1", ReadinessState.VERIFIED, "enforcing"),
        ("0", ReadinessState.DEGRADED, "permissive"),
        ("Disabled", ReadinessState.OPTIONAL, "disabled"),
        ("mystery", ReadinessState.UNKNOWN, "could not be verified"),
    ],
)
def test_selinux_runtime_modes_are_informational(
    tmp_path: Path,
    mode: str,
    expected_state: ReadinessState,
    expected_detail: str,
) -> None:
    probe = _probe(tmp_path)
    probe._selinux_enforce_path.write_text(mode, encoding="ascii")  # pyright: ignore[reportPrivateUsage]

    item = probe.selinux()

    assert item.state is expected_state
    assert not item.required_for_bind
    assert expected_detail in item.detail


def test_missing_cgroup_v2_blocks_quadlet_foundation(tmp_path: Path) -> None:
    probe = _probe(tmp_path)
    probe._cgroup_v2_controllers_path.unlink()  # pyright: ignore[reportPrivateUsage]

    item = probe.podman_quadlet()

    assert item.state is ReadinessState.BLOCKED
    assert item.detail == "cgroup v2 controllers are unavailable"
