from __future__ import annotations

import errno
import os
import stat
from pathlib import Path

import pytest

from lychd.system.atomic_paths import rename_noreplace_at
from lychd.system.atomic_retirement import (
    AtomicRetirementError,
    AtomicRetirementService,
    RetirementIdentity,
    is_retirement_quarantine_name,
    new_retirement_quarantine_name,
)
from lychd.system.interruptions import iter_exception_graph


def _identity(path: Path) -> RetirementIdentity:
    return RetirementIdentity.from_stat(path.lstat())


def test_retirement_name_producer_matches_recovery_recognizer() -> None:
    name = new_retirement_quarantine_name()

    assert is_retirement_quarantine_name(name)


def test_failed_file_retirement_restores_public_name_for_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "owned.txt"
    target.write_text("owned", encoding="utf-8")
    expected = _identity(target)
    real_unlink = os.unlink

    def fail_unlink(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        del path, dir_fd
        message = "simulated unlink failure"
        raise OSError(message)

    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        monkeypatch.setattr(
            "lychd.system.atomic_retirement.os.unlink",
            fail_unlink,
        )
        with pytest.raises(AtomicRetirementError, match="restored") as raised:
            AtomicRetirementService().retire_file(
                parent_fd=parent_fd,
                leaf=target.name,
                expected=expected,
                display_path=target,
            )
        assert raised.value.recovery is None
        assert target.read_text(encoding="utf-8") == "owned"

        monkeypatch.setattr(
            "lychd.system.atomic_retirement.os.unlink",
            real_unlink,
        )
        AtomicRetirementService().retire_file(
            parent_fd=parent_fd,
            leaf=target.name,
            expected=expected,
            display_path=target,
        )
    finally:
        os.close(parent_fd)

    assert not target.exists()


def test_blocked_restore_surfaces_typed_retained_file_quarantine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "owned.txt"
    target.write_text("owned", encoding="utf-8")
    expected = _identity(target)

    def occupy_public_name_then_fail(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        del path, dir_fd
        target.write_text("foreign", encoding="utf-8")
        message = "simulated unlink failure"
        raise OSError(message)

    monkeypatch.setattr(
        "lychd.system.atomic_retirement.os.unlink",
        occupy_public_name_then_fail,
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(
            AtomicRetirementError,
            match="preserved the quarantined entry",
        ) as raised:
            AtomicRetirementService().retire_file(
                parent_fd=parent_fd,
                leaf=target.name,
                expected=expected,
                display_path=target,
            )
    finally:
        os.close(parent_fd)

    recovery = raised.value.recovery
    assert recovery is not None
    assert recovery.resource == target
    assert recovery.expected == expected
    assert recovery.observed == expected
    assert target.read_text(encoding="utf-8") == "foreign"
    assert recovery.quarantine.read_text(encoding="utf-8") == "owned"


def test_failed_directory_retirement_preserves_late_content_for_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "owned"
    target.mkdir()
    expected = _identity(target)
    real_rmdir = os.rmdir

    def populate_quarantine_then_fail(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        assert isinstance(path, str)
        assert dir_fd is not None
        parent = Path(f"/proc/self/fd/{dir_fd}").readlink()
        (parent / path / "late.txt").write_text("preserve", encoding="utf-8")
        real_rmdir(path, dir_fd=dir_fd)

    monkeypatch.setattr(
        "lychd.system.atomic_retirement.os.rmdir",
        populate_quarantine_then_fail,
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(AtomicRetirementError, match="restored") as raised:
            AtomicRetirementService().retire_directory(
                parent_fd=parent_fd,
                leaf=target.name,
                expected=expected,
                display_path=target,
            )
    finally:
        os.close(parent_fd)

    assert raised.value.recovery is None
    assert (target / "late.txt").read_text(encoding="utf-8") == "preserve"


@pytest.mark.parametrize("terminal", [KeyboardInterrupt(), SystemExit(31)])
def test_rename_return_interruption_restores_exact_public_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    terminal: BaseException,
) -> None:
    target = tmp_path / "owned.txt"
    target.write_text("owned", encoding="utf-8")
    expected = _identity(target)
    interrupted = False

    def rename_then_interrupt(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal interrupted
        rename_noreplace_at(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )
        if not interrupted:
            interrupted = True
            raise terminal

    monkeypatch.setattr(
        "lychd.system.atomic_retirement.rename_noreplace_at",
        rename_then_interrupt,
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(type(terminal)):
            AtomicRetirementService().retire_file(
                parent_fd=parent_fd,
                leaf=target.name,
                expected=expected,
                display_path=target,
            )
    finally:
        os.close(parent_fd)

    assert target.read_text(encoding="utf-8") == "owned"
    assert not tuple(tmp_path.glob(".lychd-retire-*"))


@pytest.mark.parametrize("effect", ["before", "after"])
@pytest.mark.parametrize(
    "failure_kind",
    ["generic", "eexist", "enoent", "keyboard", "systemexit"],
)
def test_quarantine_rename_failure_matrix_has_exact_settlement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_kind: str,
    effect: str,
) -> None:
    """Every rename return path proves collision, restoration, or absence."""
    target = tmp_path / "owned.txt"
    target.write_text("owned", encoding="utf-8")
    expected_identity = _identity(target)
    failures: dict[str, BaseException] = {
        "generic": OSError(errno.EIO, "generic rename failure"),
        "eexist": OSError(errno.EEXIST, "candidate collision"),
        "enoent": OSError(errno.ENOENT, "source absent"),
        "keyboard": KeyboardInterrupt(),
        "systemexit": SystemExit(131),
    }
    primary = failures[failure_kind]
    real_rename = rename_noreplace_at
    injected = False
    collisions: list[Path] = []

    def fail_rename(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal injected
        if injected:
            real_rename(
                source_name,
                destination_name,
                source_dir_fd=source_dir_fd,
                destination_dir_fd=destination_dir_fd,
            )
            return
        injected = True
        if failure_kind == "eexist" and effect == "before":
            collision = tmp_path / destination_name
            collision.write_text("foreign collision", encoding="utf-8")
            collisions.append(collision)
        elif effect == "after":
            real_rename(
                source_name,
                destination_name,
                source_dir_fd=source_dir_fd,
                destination_dir_fd=destination_dir_fd,
            )
        raise primary

    monkeypatch.setattr(
        "lychd.system.atomic_retirement.rename_noreplace_at",
        fail_rename,
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        if failure_kind == "eexist" and effect == "before":
            AtomicRetirementService().retire_file(
                parent_fd=parent_fd,
                leaf=target.name,
                expected=expected_identity,
                display_path=target,
            )
        else:
            expected_error = AtomicRetirementError if isinstance(primary, Exception) else type(primary)
            with pytest.raises(expected_error) as raised:
                AtomicRetirementService().retire_file(
                    parent_fd=parent_fd,
                    leaf=target.name,
                    expected=expected_identity,
                    display_path=target,
                )

            assert primary in tuple(iter_exception_graph(raised.value))
            if isinstance(primary, Exception):
                assert isinstance(raised.value, AtomicRetirementError)
                assert raised.value.outcome == "restored"
                assert raised.value.outcome_verified
                assert raised.value.recovery is None
            else:
                assert raised.value is primary
    finally:
        os.close(parent_fd)

    assert injected
    if collisions:
        assert not target.exists()
        assert collisions[0].read_text(encoding="utf-8") == "foreign collision"
        assert tuple(tmp_path.glob(".lychd-retire-*")) == tuple(collisions)
    else:
        assert target.read_text(encoding="utf-8") == "owned"
        assert tuple(tmp_path.glob(".lychd-retire-*")) == ()


def test_eexist_same_identity_candidate_is_recovery_not_collision_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A same-inode candidate cannot authorize a second quarantine attempt."""
    target = tmp_path / "owned.txt"
    target.write_text("owned", encoding="utf-8")
    expected_identity = _identity(target)
    primary = OSError(errno.EEXIST, "ambiguous same-identity candidate")
    calls = 0

    def duplicate_expected_then_fail(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal calls
        calls += 1
        rename_noreplace_at(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )
        os.link(
            destination_name,
            source_name,
            src_dir_fd=destination_dir_fd,
            dst_dir_fd=source_dir_fd,
            follow_symlinks=False,
        )
        raise primary

    monkeypatch.setattr(
        "lychd.system.atomic_retirement.rename_noreplace_at",
        duplicate_expected_then_fail,
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(AtomicRetirementError) as raised:
            AtomicRetirementService().retire_file(
                parent_fd=parent_fd,
                leaf=target.name,
                expected=expected_identity,
                display_path=target,
            )
    finally:
        os.close(parent_fd)

    assert calls == 1
    assert raised.value.recovery is not None
    assert raised.value.recovery.expected == expected_identity
    assert raised.value.recovery.observed == expected_identity
    assert raised.value.recovery.quarantine.exists()
    assert _identity(target) == expected_identity


def test_enoent_is_idempotent_only_after_proved_dual_absence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The initial retirement may succeed only after both exact names are absent."""
    target = tmp_path / "owned.txt"
    target.write_text("owned", encoding="utf-8")
    expected_identity = _identity(target)
    primary = OSError(errno.ENOENT, "source disappeared")

    def remove_source_then_fail(
        source_name: str,
        _destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        del destination_dir_fd
        os.unlink(source_name, dir_fd=source_dir_fd)
        raise primary

    monkeypatch.setattr(
        "lychd.system.atomic_retirement.rename_noreplace_at",
        remove_source_then_fail,
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        AtomicRetirementService().retire_file(
            parent_fd=parent_fd,
            leaf=target.name,
            expected=expected_identity,
            display_path=target,
        )
    finally:
        os.close(parent_fd)

    assert not target.exists()
    assert tuple(tmp_path.glob(".lychd-retire-*")) == ()


@pytest.mark.parametrize(
    "observation_failure",
    [OSError("rename observation failed"), KeyboardInterrupt(), SystemExit(137)],
)
def test_quarantine_observation_failure_names_both_exact_paths_and_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    observation_failure: BaseException,
) -> None:
    """Unobservable rename effect retains its public and candidate coordinates."""
    target = tmp_path / "owned.txt"
    target.write_text("owned", encoding="utf-8")
    expected_identity = _identity(target)
    primary = OSError(errno.EIO, "rename completed without a receipt")
    candidate: Path | None = None

    def rename_then_fail(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal candidate
        rename_noreplace_at(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )
        candidate = tmp_path / destination_name
        raise primary

    def fail_observation(
        *,
        parent_fd: int,
        name: str,
    ) -> RetirementIdentity | None:
        del parent_fd, name
        raise observation_failure

    monkeypatch.setattr(
        "lychd.system.atomic_retirement.rename_noreplace_at",
        rename_then_fail,
    )
    monkeypatch.setattr(
        AtomicRetirementService,
        "_observe_name",
        staticmethod(fail_observation),
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(AtomicRetirementError) as raised:
            AtomicRetirementService().retire_file(
                parent_fd=parent_fd,
                leaf=target.name,
                expected=expected_identity,
                display_path=target,
            )
    finally:
        os.close(parent_fd)

    assert candidate is not None
    assert not target.exists()
    assert candidate.exists()
    recovery = raised.value.recovery
    assert recovery is not None
    assert recovery.resource == target
    assert recovery.quarantine == candidate
    assert recovery.expected == expected_identity
    assert recovery.observed is None
    assert primary in raised.value.failures
    assert observation_failure in raised.value.failures
    assert raised.value.outcome == "recovery"
    assert not raised.value.outcome_verified


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_ordinary_delete_after_effect_emits_verified_retired_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """An ordinary unlink/rmdir return failure is classified after its effect."""
    target = tmp_path / "owned"
    if kind == "directory":
        target.mkdir()
        real_remove = os.rmdir
    else:
        target.write_text("owned", encoding="utf-8")
        real_remove = os.unlink
    expected_identity = _identity(target)
    primary = OSError(errno.EIO, f"{kind} removal lost its receipt")

    def remove_then_fail(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        real_remove(path, dir_fd=dir_fd)
        raise primary

    monkeypatch.setattr(
        f"lychd.system.atomic_retirement.os.{'rmdir' if kind == 'directory' else 'unlink'}",
        remove_then_fail,
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    service = AtomicRetirementService()
    retire = service.retire_directory if kind == "directory" else service.retire_file
    try:
        with pytest.raises(AtomicRetirementError) as raised:
            retire(
                parent_fd=parent_fd,
                leaf=target.name,
                expected=expected_identity,
                display_path=target,
            )
    finally:
        os.close(parent_fd)

    assert raised.value.outcome == "retired"
    assert raised.value.outcome_verified
    assert primary in tuple(iter_exception_graph(raised.value))
    assert not target.exists()
    assert tuple(tmp_path.glob(".lychd-retire-*")) == ()


@pytest.mark.parametrize(
    ("terminal", "effect"),
    [
        (KeyboardInterrupt(), "before"),
        (SystemExit(37), "before"),
        (KeyboardInterrupt(), "after"),
        (SystemExit(41), "after"),
    ],
)
def test_delete_interruption_is_settled_by_exact_postcondition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    terminal: BaseException,
    effect: str,
) -> None:
    target = tmp_path / "owned.txt"
    target.write_text("owned", encoding="utf-8")
    expected = _identity(target)
    real_unlink = os.unlink

    def interrupt_unlink(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        if effect == "after":
            real_unlink(path, dir_fd=dir_fd)
        raise terminal

    monkeypatch.setattr(
        "lychd.system.atomic_retirement.os.unlink",
        interrupt_unlink,
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(type(terminal)):
            AtomicRetirementService().retire_file(
                parent_fd=parent_fd,
                leaf=target.name,
                expected=expected,
                display_path=target,
            )
    finally:
        os.close(parent_fd)

    assert target.exists() is (effect == "before")
    assert not tuple(tmp_path.glob(".lychd-retire-*"))


@pytest.mark.parametrize("observation_terminal", [KeyboardInterrupt(), SystemExit(59)])
def test_post_effect_observation_terminal_is_typed_with_named_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    observation_terminal: BaseException,
) -> None:
    target = tmp_path / "owned.txt"
    target.write_text("owned", encoding="utf-8")
    expected = _identity(target)

    def interrupt_unlink(
        _path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        del dir_fd
        raise KeyboardInterrupt

    def interrupt_observation(
        *,
        parent_fd: int,
        name: str,
    ) -> RetirementIdentity | None:
        del parent_fd, name
        raise observation_terminal

    monkeypatch.setattr(
        "lychd.system.atomic_retirement.os.unlink",
        interrupt_unlink,
    )
    monkeypatch.setattr(
        AtomicRetirementService,
        "_observe_name",
        staticmethod(interrupt_observation),
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(AtomicRetirementError) as raised:
            AtomicRetirementService().retire_file(
                parent_fd=parent_fd,
                leaf=target.name,
                expected=expected,
                display_path=target,
            )
    finally:
        os.close(parent_fd)

    assert raised.value.recovery is not None
    assert raised.value.recovery.quarantine.parent == tmp_path
    assert isinstance(raised.value.__cause__, KeyboardInterrupt)
    assert observation_terminal in raised.value.failures


@pytest.mark.parametrize(
    "close_failure",
    [OSError("retirement close failed"), KeyboardInterrupt(), SystemExit(97)],
)
def test_retired_file_close_failure_preserves_verified_outcome_and_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    close_failure: BaseException,
) -> None:
    """Descriptor failure after unlink cannot obscure the exact retired state."""
    target = tmp_path / "owned.txt"
    target.write_text("owned", encoding="utf-8")
    expected_identity = _identity(target)
    real_close = os.close
    real_fstat = os.fstat
    injected = False

    def close_then_fail(descriptor: int) -> None:
        nonlocal injected
        is_regular = stat.S_ISREG(real_fstat(descriptor).st_mode)
        real_close(descriptor)
        if is_regular and not injected:
            injected = True
            raise close_failure

    monkeypatch.setattr(
        "lychd.system.descriptor_settlement.os.close",
        close_then_fail,
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        expected = AtomicRetirementError if isinstance(close_failure, Exception) else type(close_failure)
        with pytest.raises(expected) as raised:
            AtomicRetirementService().retire_file(
                parent_fd=parent_fd,
                leaf=target.name,
                expected=expected_identity,
                display_path=target,
            )

        graph = tuple(iter_exception_graph(raised.value))
        assert close_failure in graph
        if isinstance(raised.value, AtomicRetirementError):
            assert raised.value.outcome == "retired"
            assert raised.value.outcome_verified
        else:
            assert raised.value is close_failure
        assert injected
        assert not target.exists()
        assert tuple(tmp_path.glob(".lychd-retire-*")) == ()

        AtomicRetirementService().retire_file(
            parent_fd=parent_fd,
            leaf=target.name,
            expected=expected_identity,
            display_path=target,
        )
    finally:
        os.close(parent_fd)


@pytest.mark.parametrize(
    "close_failure",
    [OSError("restore close failed"), KeyboardInterrupt(), SystemExit(103)],
)
def test_restore_primary_and_close_failure_preserve_both_peers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    close_failure: BaseException,
) -> None:
    """An unlink primary and descriptor peer retain exact restored truth."""
    target = tmp_path / "owned.txt"
    target.write_text("owned", encoding="utf-8")
    expected_identity = _identity(target)
    primary = OSError("unlink failed")
    real_close = os.close
    real_fstat = os.fstat
    real_unlink = os.unlink
    injected = False

    def fail_unlink(
        _path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        del dir_fd
        raise primary

    def close_then_fail(descriptor: int) -> None:
        nonlocal injected
        is_regular = stat.S_ISREG(real_fstat(descriptor).st_mode)
        real_close(descriptor)
        if is_regular and not injected:
            injected = True
            raise close_failure

    monkeypatch.setattr(
        "lychd.system.atomic_retirement.os.unlink",
        fail_unlink,
    )
    monkeypatch.setattr(
        "lychd.system.descriptor_settlement.os.close",
        close_then_fail,
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        expected = AtomicRetirementError if isinstance(close_failure, Exception) else type(close_failure)
        with pytest.raises(expected) as raised:
            AtomicRetirementService().retire_file(
                parent_fd=parent_fd,
                leaf=target.name,
                expected=expected_identity,
                display_path=target,
            )

        graph = tuple(iter_exception_graph(raised.value))
        assert primary in graph
        assert close_failure in graph
        if isinstance(raised.value, AtomicRetirementError):
            assert raised.value.outcome == "restored"
            assert raised.value.outcome_verified
        else:
            assert raised.value is close_failure
        assert injected
        assert target.read_text(encoding="utf-8") == "owned"
        assert tuple(tmp_path.glob(".lychd-retire-*")) == ()

        monkeypatch.setattr(
            "lychd.system.atomic_retirement.os.unlink",
            real_unlink,
        )
        AtomicRetirementService().retire_file(
            parent_fd=parent_fd,
            leaf=target.name,
            expected=expected_identity,
            display_path=target,
        )
    finally:
        os.close(parent_fd)
