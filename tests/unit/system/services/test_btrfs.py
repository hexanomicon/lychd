from __future__ import annotations

from pathlib import Path

from lychd.system.operator import ProcessResult
from lychd.system.services.btrfs import Btrfs, BtrfsTools


class _Runner:
    def __init__(self, responses: list[ProcessResult]) -> None:
        self.responses = responses
        self.calls: list[tuple[tuple[str, ...], float]] = []

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        self.calls.append((argv, timeout_s))
        return self.responses.pop(0)


class _CreatingRunner(_Runner):
    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        result = super().run(argv, timeout_s=timeout_s)
        if argv[1:3] == ("subvolume", "create") and result.returncode == 0:
            Path(argv[3]).mkdir()
        return result


def _tools() -> BtrfsTools:
    return BtrfsTools(
        btrfs="/btrfs",
        chattr="/chattr",
        lsattr="/lsattr",
    )


def test_subvolume_creation_is_bounded_and_verified(tmp_path: Path) -> None:
    target = tmp_path / "postgres" / "data"
    runner = _CreatingRunner(
        [
            ProcessResult(argv=(), returncode=0),
            ProcessResult(argv=(), returncode=0),
        ]
    )

    created = Btrfs(runner=runner, tools=_tools()).create_subvolume(target)

    assert created
    assert runner.calls == [
        (("/btrfs", "subvolume", "create", str(target)), 30.0),
        (("/btrfs", "subvolume", "show", str(target)), 3.0),
    ]


def test_subvolume_identity_comes_from_btrfs_not_inode_heuristics(tmp_path: Path) -> None:
    target = tmp_path / "data"
    target.mkdir()
    runner = _Runner([ProcessResult(argv=(), returncode=1, stderr="not a btrfs subvolume")])

    assert not Btrfs(runner=runner, tools=_tools()).is_subvolume(target)
    assert runner.calls == [(("/btrfs", "subvolume", "show", str(target)), 3.0)]


def test_nocow_policy_is_applied_only_after_verification(tmp_path: Path) -> None:
    target = tmp_path / "data"
    target.mkdir()
    runner = _Runner(
        [
            ProcessResult(argv=(), returncode=0, stdout=f"---------------------- {target}\n"),
            ProcessResult(argv=(), returncode=0),
            ProcessResult(argv=(), returncode=0, stdout=f"---------------C------ {target}\n"),
        ]
    )

    applied = Btrfs(runner=runner, tools=_tools()).apply_no_cow(target)

    assert applied
    assert runner.calls == [
        (("/lsattr", "-d", str(target)), 3.0),
        (("/chattr", "+C", str(target)), 30.0),
        (("/lsattr", "-d", str(target)), 3.0),
    ]
