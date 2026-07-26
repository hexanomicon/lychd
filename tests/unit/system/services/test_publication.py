"""Adversarial tests for journal-bound initialization publication."""

from __future__ import annotations

import os
import stat
from typing import TYPE_CHECKING

import pytest

from lychd.system.atomic_paths import rename_noreplace_at
from lychd.system.descriptor_settlement import DescriptorSet
from lychd.system.services.publication import (
    JournaledCreation,
    PublicationRollbackError,
)

if TYPE_CHECKING:
    from pathlib import Path

    from lychd.system.services.lifecycle import CreatedResources


def test_text_publication_is_durable_journaled_and_stable_on_rerun(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A winner is synced before journaling and an existing peer is preserved."""
    target = tmp_path / "lychd.toml"
    journal: list[CreatedResources] = []
    synced_modes: list[int] = []
    real_fsync = os.fsync

    def observe_sync(descriptor: int) -> None:
        synced_modes.append(os.fstat(descriptor).st_mode)
        real_fsync(descriptor)

    monkeypatch.setattr(
        "lychd.system.services.publication.os.fsync",
        observe_sync,
    )
    creation = JournaledCreation(on_created=journal.append)

    created = creation.create_text_file(
        target,
        "answer = 42\n",
        mode=0o600,
    )
    repeated = creation.create_text_file(
        target,
        "replacement = false\n",
        mode=0o600,
    )

    assert created.files == (target,)
    assert repeated.files == ()
    assert creation.resources.files == (target,)
    assert [batch.files for batch in journal] == [(target,)]
    assert target.read_text(encoding="utf-8") == "answer = 42\n"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert any(stat.S_ISREG(mode) for mode in synced_modes)
    assert any(stat.S_ISDIR(mode) for mode in synced_modes)
    assert tuple(tmp_path.glob(".lychd-*")) == ()


def test_text_publication_never_creates_a_hidden_parent(tmp_path: Path) -> None:
    """File publishers require the Layout-created parent to exist already."""
    parent = tmp_path / "missing"
    target = parent / "lychd.toml"

    with pytest.raises(
        RuntimeError,
        match="parent must already be a real directory",
    ):
        JournaledCreation().create_text_file(
            target,
            "answer = 42\n",
            mode=0o600,
        )

    assert not parent.exists()


@pytest.mark.parametrize("terminal", [KeyboardInterrupt(), SystemExit(71)])
def test_parent_close_signal_after_commit_preserves_journal_truth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    terminal: BaseException,
) -> None:
    """A final close signal cannot make a committed publication look rolled back."""
    target = tmp_path / "lychd.toml"
    journal: list[CreatedResources] = []
    creation = JournaledCreation(on_created=journal.append)
    real_settle = DescriptorSet.settle

    def settle_then_interrupt(descriptors: DescriptorSet) -> tuple[BaseException, ...]:
        return (*real_settle(descriptors), terminal)

    monkeypatch.setattr(
        "lychd.system.services.publication.DescriptorSet.settle",
        settle_then_interrupt,
    )

    with pytest.raises(type(terminal)):
        creation.create_text_file(
            target,
            "answer = 42\n",
            mode=0o600,
        )

    assert target.read_text(encoding="utf-8") == "answer = 42\n"
    assert creation.resources.files == (target,)
    assert [batch.files for batch in journal] == [(target,)]


def test_parent_close_failure_reports_committed_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An ordinary final-close failure carries the already committed state."""
    target = tmp_path / "lychd.toml"
    close_failure = OSError("parent close failed")
    real_settle = DescriptorSet.settle

    def settle_then_fail(descriptors: DescriptorSet) -> tuple[BaseException, ...]:
        return (*real_settle(descriptors), close_failure)

    monkeypatch.setattr(
        "lychd.system.services.publication.DescriptorSet.settle",
        settle_then_fail,
    )

    with pytest.raises(PublicationRollbackError) as captured:
        JournaledCreation().create_text_file(
            target,
            "answer = 42\n",
            mode=0o600,
        )

    assert captured.value.outcome == "committed"
    assert close_failure in captured.value.failures
    assert target.read_text(encoding="utf-8") == "answer = 42\n"


def test_text_publication_race_loser_is_never_journaled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A peer that wins the public name remains foreign to init ownership."""
    target = tmp_path / "lychd.toml"
    journal: list[CreatedResources] = []
    real_link = os.link
    raced = False

    def install_peer_then_link(
        source: str,
        destination: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
        follow_symlinks: bool,
    ) -> None:
        nonlocal raced
        if not raced:
            raced = True
            descriptor = os.open(
                destination,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=dst_dir_fd,
            )
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write("peer = true\n")
        real_link(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(
        "lychd.system.services.publication.os.link",
        install_peer_then_link,
    )

    resources = JournaledCreation(on_created=journal.append).create_text_file(
        target,
        "lychd = true\n",
        mode=0o600,
    )

    assert resources.files == ()
    assert journal == []
    assert target.read_text(encoding="utf-8") == "peer = true\n"
    assert tuple(tmp_path.glob(".lychd-*")) == ()


@pytest.mark.parametrize("terminal", [KeyboardInterrupt(), SystemExit(73)])
def test_publication_return_signal_rolls_back_exact_file_and_stays_native(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    terminal: BaseException,
) -> None:
    """A signal after hard-link publication is classified before propagation."""
    target = tmp_path / "lychd.toml"
    journal: list[CreatedResources] = []
    real_link = os.link
    interrupted = False

    def publish_then_interrupt(
        source: str,
        destination: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
        follow_symlinks: bool,
    ) -> None:
        nonlocal interrupted
        real_link(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )
        if not interrupted:
            interrupted = True
            raise terminal

    monkeypatch.setattr(
        "lychd.system.services.publication.os.link",
        publish_then_interrupt,
    )

    with pytest.raises(type(terminal)):
        JournaledCreation(on_created=journal.append).create_text_file(
            target,
            "lychd = true\n",
            mode=0o600,
        )

    assert journal == []
    assert not target.exists()
    assert tuple(tmp_path.glob(".lychd-*")) == ()


@pytest.mark.parametrize("terminal", [KeyboardInterrupt(), SystemExit(79)])
def test_journal_signal_rolls_back_exact_file_and_stays_native(
    tmp_path: Path,
    terminal: BaseException,
) -> None:
    """Rollback completes before a terminal journal interruption escapes."""
    target = tmp_path / "lychd.toml"

    def interrupt_journal(_resources: CreatedResources) -> None:
        raise terminal

    with pytest.raises(type(terminal)):
        JournaledCreation(on_created=interrupt_journal).create_text_file(
            target,
            "lychd = true\n",
            mode=0o600,
        )

    assert not target.exists()
    assert tuple(tmp_path.glob(".lychd-*")) == ()


def test_callback_replacement_is_preserved_during_rollback(tmp_path: Path) -> None:
    """A failed journal cannot redirect rollback into a concurrent replacement."""
    target = tmp_path / "lychd.toml"

    def replace_then_reject(_resources: CreatedResources) -> None:
        target.unlink()
        target.write_text("peer = true\n", encoding="utf-8")
        message = "journal rejected"
        raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="journal rejected"):
        JournaledCreation(on_created=replace_then_reject).create_text_file(
            target,
            "lychd = true\n",
            mode=0o600,
        )

    assert target.read_text(encoding="utf-8") == "peer = true\n"
    assert tuple(tmp_path.glob(".lychd-*")) == ()


@pytest.mark.parametrize("terminal", [KeyboardInterrupt(), SystemExit(83)])
def test_rollback_rename_signal_settles_peers_then_preserves_original_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    terminal: BaseException,
) -> None:
    """A signal after quarantine rename cannot hide clean rollback truth."""
    target = tmp_path / "lychd.toml"
    real_rename = rename_noreplace_at
    interrupted = False

    def quarantine_then_interrupt(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal interrupted
        real_rename(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )
        if destination_name.startswith(".lychd-rollback-") and not interrupted:
            interrupted = True
            raise terminal

    def interrupt_journal(_resources: CreatedResources) -> None:
        raise terminal

    monkeypatch.setattr(
        "lychd.system.services.publication.rename_noreplace_at",
        quarantine_then_interrupt,
    )

    with pytest.raises(type(terminal)):
        JournaledCreation(on_created=interrupt_journal).create_text_file(
            target,
            "lychd = true\n",
            mode=0o600,
        )

    assert not target.exists()
    assert tuple(tmp_path.glob(".lychd-*")) == ()


def test_directory_race_loser_is_not_reported_or_journaled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Descriptor-relative no-replace preserves and excludes a peer directory."""
    target = tmp_path / "inbox"
    journal: list[CreatedResources] = []
    real_rename = rename_noreplace_at
    raced = False

    def install_peer_then_rename(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal raced
        if destination_name == target.name and not raced:
            raced = True
            os.mkdir(destination_name, 0o700, dir_fd=destination_dir_fd)
        real_rename(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    monkeypatch.setattr(
        "lychd.system.atomic_paths.rename_noreplace_at",
        install_peer_then_rename,
    )

    resources = JournaledCreation(on_created=journal.append).create_directory(
        target,
        mode=0o700,
    )

    assert resources.directories == ()
    assert resources.directory_identities == ()
    assert journal == []
    assert target.is_dir()
