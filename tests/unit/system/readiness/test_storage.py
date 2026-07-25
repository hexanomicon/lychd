from __future__ import annotations

import json
from pathlib import Path

import pytest

from lychd.system.operator import ProcessResult
from lychd.system.readiness import HostReadinessTools, ReadinessState
from lychd.system.readiness.storage import StorageReadinessProbe


class _StorageRunner:
    def __init__(
        self,
        *,
        filesystem: str,
        mount_options: str = "rw",
        lsattr: ProcessResult | None = None,
    ) -> None:
        self.filesystem = filesystem
        self.mount_options = mount_options
        self.lsattr = lsattr
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        assert timeout_s == 3.0
        self.calls.append(argv)
        if argv[0] == "/findmnt":
            target = argv[argv.index("--target") + 1]
            return ProcessResult(
                argv=argv,
                returncode=0,
                stdout=json.dumps(
                    {
                        "filesystems": [
                            {
                                "target": target,
                                "source": "/dev/test",
                                "fstype": self.filesystem,
                                "options": self.mount_options,
                                "fsroot": "/",
                            }
                        ]
                    }
                ),
            )
        if argv[0] == "/lsattr" and self.lsattr is not None:
            return self.lsattr
        message = f"Unexpected host probe: {argv}"
        raise AssertionError(message)


def _tools(*, complete: bool = True) -> HostReadinessTools:
    return HostReadinessTools(
        systemctl="/systemctl",
        podman="/podman",
        quadlet_user_generator="/quadlet",
        findmnt="/findmnt",
        btrfs="/btrfs" if complete else None,
        chattr="/chattr" if complete else None,
        lsattr="/lsattr" if complete else None,
        getenforce="/getenforce",
    )


def test_existing_btrfs_data_reports_verified_nocow_policy(tmp_path: Path) -> None:
    data = tmp_path / "postgres" / "data"
    data.mkdir(parents=True)
    runner = _StorageRunner(
        filesystem="btrfs",
        lsattr=ProcessResult(
            argv=(),
            returncode=0,
            stdout=f"---------------C------ {data}\n",
        ),
    )

    btrfs, postgres = StorageReadinessProbe(
        runner=runner,
        tools=_tools(),
        postgres_data=data,
    ).inspect()

    assert btrfs.state is ReadinessState.VERIFIED
    assert postgres.state is ReadinessState.VERIFIED
    assert postgres.detail == "Btrfs directory · No-COW directory policy active"


@pytest.mark.parametrize(
    ("lsattr", "expected_state", "expected_detail"),
    [
        (
            ProcessResult(argv=(), returncode=0, stdout="---------------------- /data\n"),
            ReadinessState.DEGRADED,
            "COW active",
        ),
        (
            ProcessResult(argv=(), returncode=1, stderr="unsupported"),
            ReadinessState.UNKNOWN,
            "state unknown",
        ),
        (
            ProcessResult(argv=(), returncode=0, stdout=""),
            ReadinessState.UNKNOWN,
            "state unknown",
        ),
    ],
)
def test_existing_btrfs_data_never_infers_nocow(
    tmp_path: Path,
    lsattr: ProcessResult,
    expected_state: ReadinessState,
    expected_detail: str,
) -> None:
    data = tmp_path / "postgres" / "data"
    data.mkdir(parents=True)

    _btrfs, postgres = StorageReadinessProbe(
        runner=_StorageRunner(filesystem="btrfs", lsattr=lsattr),
        tools=_tools(),
        postgres_data=data,
    ).inspect()

    assert postgres.state is expected_state
    assert expected_detail in postgres.detail


def test_global_nodatacow_mount_policy_does_not_require_lsattr(tmp_path: Path) -> None:
    data = tmp_path / "postgres" / "data"
    data.mkdir(parents=True)
    runner = _StorageRunner(filesystem="btrfs", mount_options="rw,nodatacow")

    _btrfs, postgres = StorageReadinessProbe(
        runner=runner,
        tools=_tools(),
        postgres_data=data,
    ).inspect()

    assert postgres.state is ReadinessState.VERIFIED
    assert not any(call[0] == "/lsattr" for call in runner.calls)


def test_absent_data_on_btrfs_is_planned_not_claimed_active(tmp_path: Path) -> None:
    postgres_root = tmp_path / "postgres"
    postgres_root.mkdir()
    data = postgres_root / "data"

    btrfs, postgres = StorageReadinessProbe(
        runner=_StorageRunner(filesystem="btrfs"),
        tools=_tools(),
        postgres_data=data,
    ).inspect()

    assert btrfs.state is ReadinessState.VERIFIED
    assert postgres.state is ReadinessState.PLANNED
    assert postgres.detail == "absent · Btrfs subvolume + No-COW policy will be attempted"
    assert not data.exists()


def test_non_btrfs_storage_is_an_explicit_optional_fallback(tmp_path: Path) -> None:
    data = tmp_path / "postgres" / "data"
    data.mkdir(parents=True)

    btrfs, postgres = StorageReadinessProbe(
        runner=_StorageRunner(filesystem="ext4"),
        tools=_tools(),
        postgres_data=data,
    ).inspect()

    assert btrfs.state is ReadinessState.OPTIONAL
    assert "ext4" in btrfs.detail
    assert postgres.state is ReadinessState.OPTIONAL
    assert postgres.detail == "ext4 directory · No-COW not applicable"
