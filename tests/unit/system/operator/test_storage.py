from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from lychd.system.operator import ProcessResult, StorageInventoryService


class _Runner:
    def __init__(self, responses: list[ProcessResult]) -> None:
        self.responses = responses
        self.calls: list[tuple[tuple[str, ...], float]] = []

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        self.calls.append((argv, timeout_s))
        return self.responses.pop(0)


def _findmnt_payload(*filesystems: dict[str, object]) -> str:
    return json.dumps({"filesystems": list(filesystems)})


def test_exact_btrfs_mount_exposes_safe_source_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "data"
    target.mkdir()
    runner = _Runner(
        [
            ProcessResult(
                argv=(),
                returncode=0,
                stdout=_findmnt_payload(
                    {
                        "target": str(target),
                        "source": "/dev/nvme0n1p3[/@phylactery]",
                        "fstype": "btrfs",
                        "options": ("rw,compress=zstd:3,subvolid=259,subvol=/@phylactery"),
                        "fsroot": "/@phylactery",
                        "uuid": "87654321-4321-8765-4321-876543218765",
                    }
                ),
            ),
            ProcessResult(
                argv=(),
                returncode=0,
                stdout=_findmnt_payload(
                    {
                        "target": "/home",
                        "source": "/dev/nvme0n1p3",
                        "fstype": "btrfs",
                        "options": "rw,subvol=/",
                        "fsroot": "/",
                        "uuid": "87654321-4321-8765-4321-876543218765",
                    }
                ),
            ),
        ]
    )

    def ismount(path: str | os.PathLike[str]) -> bool:
        return Path(path) == target

    monkeypatch.setattr("os.path.ismount", ismount)

    observed = StorageInventoryService(runner, findmnt_bin="/usr/bin/findmnt").observe(target)

    assert observed.mounted is True
    assert observed.source_device == "/dev/nvme0n1p3"
    assert observed.filesystem_uuid == "87654321-4321-8765-4321-876543218765"
    assert observed.fs_root == "/@phylactery"
    assert observed.subvolume_id == 259
    assert observed.top_level_mount == Path("/home")
    assert observed.btrfs_source_path == Path("/home/@phylactery")
    assert observed.read_only is False
    assert runner.calls[0][0][:4] == (
        "/usr/bin/findmnt",
        "--json",
        "--target",
        str(target),
    )


def test_observe_under_returns_only_exact_nested_mountpoints(tmp_path: Path) -> None:
    crypt = tmp_path / "crypt"
    nested = crypt / "postgres" / "data"
    outside = tmp_path / "models"
    runner = _Runner(
        [
            ProcessResult(
                argv=(),
                returncode=0,
                stdout=_findmnt_payload(
                    {
                        "target": "/home",
                        "source": "/dev/disk",
                        "fstype": "btrfs",
                        "options": "rw",
                        "fsroot": "/",
                        "uuid": "87654321-4321-8765-4321-876543218765",
                        "children": [
                            {
                                "target": str(nested),
                                "source": "/dev/disk[/@db]",
                                "fstype": "btrfs",
                                "options": "rw,subvolid=259,subvol=/@db",
                                "fsroot": "/@db",
                                "uuid": "87654321-4321-8765-4321-876543218765",
                            }
                        ],
                    },
                    {
                        "target": str(outside),
                        "source": "/dev/disk[/@models]",
                        "fstype": "btrfs",
                        "options": "rw",
                        "fsroot": "/@models",
                    },
                ),
            )
        ]
    )

    tree = StorageInventoryService(runner, findmnt_bin="/usr/bin/findmnt").observe_under((crypt,))

    assert tree.warning is None
    assert [mount.target for mount in tree.mounts] == [nested]
    assert tree.mounts[0].top_level_mount == Path("/home")
    assert tree.mounts[0].btrfs_source_path == Path("/home/@db")
    assert tree.mounts[0].subvolume_id == 259
    assert tree.mounts[0].filesystem_uuid == "87654321-4321-8765-4321-876543218765"


def test_missing_findmnt_never_claims_filesystem_identity(tmp_path: Path) -> None:
    runner = _Runner([])

    observed = StorageInventoryService(runner, findmnt_bin=None).observe(tmp_path / "missing")
    tree = StorageInventoryService(runner, findmnt_bin=None).observe_under((tmp_path,))

    assert observed.mounted is False
    assert observed.filesystem is None
    assert observed.warning is not None
    assert tree.mounts == ()
    assert tree.warning is not None
    assert runner.calls == []


def test_malformed_findmnt_identity_is_not_promoted(tmp_path: Path) -> None:
    target = tmp_path / "data"
    runner = _Runner(
        [
            ProcessResult(
                argv=(),
                returncode=0,
                stdout=_findmnt_payload(
                    {
                        "target": str(target),
                        "source": "/dev/disk[/@db]",
                        "fstype": "btrfs",
                        "options": ("rw,subvolid=259,subvolid=260,subvol=/@db"),
                        "fsroot": "/@db",
                        "uuid": "not-a-uuid",
                    }
                ),
            )
        ]
    )

    tree = StorageInventoryService(
        runner,
        findmnt_bin="/usr/bin/findmnt",
    ).observe_under((target,))

    assert len(tree.mounts) == 1
    assert tree.mounts[0].filesystem_uuid is None
    assert tree.mounts[0].subvolume_id is None
