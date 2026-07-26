from __future__ import annotations

import os
from pathlib import Path

import pytest

from lychd.system.btrfs_identity import BtrfsSubvolumeObservation
from lychd.system.operator import ProcessInvocationError, ProcessResult
from lychd.system.services.btrfs import (
    Btrfs,
    BtrfsCreationError,
    BtrfsCreationState,
    BtrfsTools,
)


class _Runner:
    def __init__(self, responses: list[ProcessResult]) -> None:
        self.responses = responses
        self.calls: list[tuple[tuple[str, ...], float]] = []
        self.fd_calls: list[tuple[tuple[str, ...], float, tuple[int, ...]]] = []

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        self.calls.append((argv, timeout_s))
        return self.responses.pop(0)

    def run_with_fds(
        self,
        argv: tuple[str, ...],
        *,
        timeout_s: float,
        pass_fds: tuple[int, ...],
    ) -> ProcessResult:
        self.fd_calls.append((argv, timeout_s, pass_fds))
        return self.responses.pop(0)


class _CreatingRunner(_Runner):
    def run_with_fds(
        self,
        argv: tuple[str, ...],
        *,
        timeout_s: float,
        pass_fds: tuple[int, ...],
    ) -> ProcessResult:
        result = super().run_with_fds(
            argv,
            timeout_s=timeout_s,
            pass_fds=pass_fds,
        )
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
    target.parent.mkdir()
    runner = _CreatingRunner(
        [
            ProcessResult(argv=(), returncode=0),
            ProcessResult(
                argv=(),
                returncode=0,
                stdout=("UUID: 12345678-1234-5678-1234-567812345678\nSubvolume ID: 259\n"),
            ),
        ]
    )

    parent_fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        created = Btrfs(runner=runner, tools=_tools()).create_subvolume(
            target,
            parent_fd=parent_fd,
        )
    finally:
        os.close(parent_fd)

    assert created is not None
    assert created.uuid == "12345678-1234-5678-1234-567812345678"
    assert created.subvolume_id == 259
    descriptor_target = f"/proc/self/fd/{parent_fd}/{target.name}"
    assert runner.fd_calls == [
        (
            ("/btrfs", "subvolume", "create", descriptor_target),
            30.0,
            (parent_fd,),
        ),
        (
            ("/btrfs", "subvolume", "show", descriptor_target),
            3.0,
            (parent_fd,),
        ),
    ]


@pytest.mark.parametrize(
    ("outcome", "cause_type"),
    [
        (ProcessResult(argv=(), returncode=1, stderr="failed"), None),
        (ProcessInvocationError("timed out"), ProcessInvocationError),
        (KeyboardInterrupt(), KeyboardInterrupt),
        (SystemExit(17), SystemExit),
    ],
)
def test_materialized_creation_failure_returns_typed_pinned_evidence(
    tmp_path: Path,
    outcome: ProcessResult | BaseException,
    cause_type: type[BaseException] | None,
) -> None:
    """No failed mutator may turn a present leaf into directory fallback."""
    target = tmp_path / "postgres" / "data"
    target.parent.mkdir()

    class _MaterializingRunner(_Runner):
        def run_with_fds(
            self,
            argv: tuple[str, ...],
            *,
            timeout_s: float,
            pass_fds: tuple[int, ...],
        ) -> ProcessResult:
            del timeout_s, pass_fds
            Path(argv[3]).mkdir()
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome

    parent_fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(BtrfsCreationError) as raised:
            Btrfs(
                runner=_MaterializingRunner([]),
                tools=_tools(),
            ).create_subvolume(
                target,
                parent_fd=parent_fd,
            )
    finally:
        os.close(parent_fd)

    assert raised.value.evidence.state is BtrfsCreationState.PRESENT_UNATTESTED
    assert target.is_dir()
    if cause_type is None:
        assert raised.value.cause is None
    else:
        assert isinstance(raised.value.cause, cause_type)


def test_successful_create_with_unverifiable_show_is_typed_not_fallback(
    tmp_path: Path,
) -> None:
    target = tmp_path / "postgres" / "data"
    target.parent.mkdir()
    runner = _CreatingRunner(
        [
            ProcessResult(argv=(), returncode=0),
            ProcessResult(argv=(), returncode=1, stderr="show unavailable"),
        ]
    )
    parent_fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(BtrfsCreationError) as raised:
            Btrfs(runner=runner, tools=_tools()).create_subvolume(
                target,
                parent_fd=parent_fd,
            )
    finally:
        os.close(parent_fd)

    assert raised.value.evidence.state is BtrfsCreationState.PRESENT_UNATTESTED
    assert target.is_dir()


def test_subvolume_creation_cannot_follow_a_replaced_public_parent(
    tmp_path: Path,
) -> None:
    """The child process creates only beneath the inherited parent descriptor."""
    target = tmp_path / "postgres" / "data"
    target.parent.mkdir()
    displaced_parent = tmp_path / "postgres-created-by-init"

    class _ParentSwappingRunner(_CreatingRunner):
        def run_with_fds(
            self,
            argv: tuple[str, ...],
            *,
            timeout_s: float,
            pass_fds: tuple[int, ...],
        ) -> ProcessResult:
            if argv[1:3] == ("subvolume", "create"):
                target.parent.rename(displaced_parent)
                target.parent.mkdir()
            return super().run_with_fds(
                argv,
                timeout_s=timeout_s,
                pass_fds=pass_fds,
            )

    runner = _ParentSwappingRunner(
        [
            ProcessResult(argv=(), returncode=0),
            ProcessResult(
                argv=(),
                returncode=0,
                stdout=("UUID: 12345678-1234-5678-1234-567812345678\nSubvolume ID: 259\n"),
            ),
        ]
    )
    parent_fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)

    try:
        created = Btrfs(runner=runner, tools=_tools()).create_subvolume(
            target,
            parent_fd=parent_fd,
        )
    finally:
        os.close(parent_fd)

    assert created is not None
    assert (displaced_parent / target.name).is_dir()
    assert not target.exists()


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


def test_created_subvolume_drift_is_rejected_before_descriptor_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replacement path cannot receive the original creation's No-COW effect."""
    target = tmp_path / "data"
    target.mkdir()
    expected = BtrfsSubvolumeObservation(
        uuid="12345678-1234-5678-1234-567812345678",
        subvolume_id=259,
    )
    replacement = BtrfsSubvolumeObservation(
        uuid="87654321-4321-8765-4321-876543218765",
        subvolume_id=260,
    )
    runner = _Runner(
        [
            ProcessResult(
                argv=(),
                returncode=0,
                stdout=(f"UUID: {replacement.uuid}\nSubvolume ID: {replacement.subvolume_id}\n"),
            ),
            ProcessResult(
                argv=(),
                returncode=0,
                stdout=(f"UUID: {replacement.uuid}\nSubvolume ID: {replacement.subvolume_id}\n"),
            ),
        ]
    )
    mutated = False

    def reject_mutation(_descriptor: int, *, path: Path) -> bool:
        nonlocal mutated
        mutated = True
        return True

    monkeypatch.setattr(
        Btrfs,
        "_apply_no_cow_descriptor",
        staticmethod(reject_mutation),
    )

    parent_fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(RuntimeError, match="changed identity"):
            Btrfs(runner=runner, tools=_tools()).prepare_created_subvolume(
                target,
                parent_fd=parent_fd,
                expected=expected,
            )
    finally:
        os.close(parent_fd)

    assert mutated is False


def test_created_subvolume_nocow_mutation_remains_bound_to_open_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A swap during No-COW preparation affects only the pinned original inode."""
    target = tmp_path / "data"
    target.mkdir()
    displaced = tmp_path / "data-created-by-init"
    expected = BtrfsSubvolumeObservation(
        uuid="12345678-1234-5678-1234-567812345678",
        subvolume_id=259,
    )
    replacement = BtrfsSubvolumeObservation(
        uuid="87654321-4321-8765-4321-876543218765",
        subvolume_id=260,
    )
    runner = _Runner(
        [
            ProcessResult(
                argv=(),
                returncode=0,
                stdout=(f"UUID: {expected.uuid}\nSubvolume ID: {expected.subvolume_id}\n"),
            ),
            ProcessResult(
                argv=(),
                returncode=0,
                stdout=(f"UUID: {expected.uuid}\nSubvolume ID: {expected.subvolume_id}\n"),
            ),
            ProcessResult(
                argv=(),
                returncode=0,
                stdout=(f"UUID: {replacement.uuid}\nSubvolume ID: {replacement.subvolume_id}\n"),
            ),
            ProcessResult(
                argv=(),
                returncode=0,
                stdout=(f"UUID: {replacement.uuid}\nSubvolume ID: {replacement.subvolume_id}\n"),
            ),
        ]
    )
    flag_reads = iter((0, 0x00800000))
    mutated_inode: int | None = None

    def read_flags(_descriptor: int) -> int:
        return next(flag_reads)

    def write_flags(descriptor: int, _flags: int) -> None:
        nonlocal mutated_inode
        mutated_inode = os.fstat(descriptor).st_ino
        target.rename(displaced)
        target.mkdir()

    monkeypatch.setattr(Btrfs, "_inode_flags", staticmethod(read_flags))
    monkeypatch.setattr(Btrfs, "_write_inode_flags", staticmethod(write_flags))

    parent_fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(RuntimeError, match="changed identity"):
            Btrfs(runner=runner, tools=_tools()).prepare_created_subvolume(
                target,
                parent_fd=parent_fd,
                expected=expected,
            )
    finally:
        os.close(parent_fd)

    assert mutated_inode == displaced.stat().st_ino
    assert mutated_inode != target.stat().st_ino
