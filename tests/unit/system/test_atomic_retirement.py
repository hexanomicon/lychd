from __future__ import annotations

import os
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
