"""Adversarial tests for journal-bound initialization publication."""

from __future__ import annotations

import os
import stat
from typing import TYPE_CHECKING

import pytest

from lychd.system.atomic_paths import rename_noreplace_at
from lychd.system.descriptor_settlement import (
    DescriptorSet,
    find_settlement_outcome,
)
from lychd.system.interruptions import iter_exception_graph
from lychd.system.services import file_publication_settlement as settlement_module
from lychd.system.services.file_publication_models import PublicationRollbackError
from lychd.system.services.file_publication_transaction import JournaledCreation

if TYPE_CHECKING:
    from pathlib import Path

    from lychd.system.services.lifecycle.models import CreatedResources


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
        "lychd.system.services.file_publication_transaction.os.fsync",
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


def test_parent_close_signal_after_commit_preserves_journal_truth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A final close signal cannot make a committed publication look rolled back."""
    terminal = KeyboardInterrupt()
    target = tmp_path / "lychd.toml"
    journal: list[CreatedResources] = []
    creation = JournaledCreation(on_created=journal.append)
    real_settle = DescriptorSet.settle

    def settle_then_interrupt(descriptors: DescriptorSet) -> tuple[BaseException, ...]:
        return (*real_settle(descriptors), terminal)

    monkeypatch.setattr(
        "lychd.system.services.file_publication_transaction.DescriptorSet.settle",
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
        "lychd.system.services.file_publication_transaction.DescriptorSet.settle",
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


@pytest.mark.parametrize(
    "close_failure",
    [OSError("staging close failed"), KeyboardInterrupt()],
)
def test_staging_primary_and_close_failure_remove_exact_private_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    close_failure: BaseException,
) -> None:
    """A close peer cannot mask the primary or leave private staging residue."""
    target = tmp_path / "lychd.toml"
    primary = OSError("staging chmod failed")
    real_close = os.close
    real_fstat = os.fstat
    injected = False

    def fail_chmod(_descriptor: int, _mode: int) -> None:
        raise primary

    def close_then_fail(descriptor: int) -> None:
        nonlocal injected
        is_regular = stat.S_ISREG(real_fstat(descriptor).st_mode)
        real_close(descriptor)
        if is_regular and not injected:
            injected = True
            raise close_failure

    monkeypatch.setattr(
        "lychd.system.services.file_publication_transaction.os.fchmod",
        fail_chmod,
    )
    monkeypatch.setattr(
        "lychd.system.descriptor_settlement.os.close",
        close_then_fail,
    )

    expected = PublicationRollbackError if isinstance(close_failure, Exception) else type(close_failure)
    with pytest.raises(expected) as raised:
        JournaledCreation().create_text_file(
            target,
            "answer = 42\n",
            mode=0o600,
        )

    graph = tuple(iter_exception_graph(raised.value))
    assert primary in graph
    assert close_failure in graph
    if isinstance(raised.value, PublicationRollbackError):
        assert raised.value.outcome == "rolled_back"
        assert raised.value.outcome_verified
    else:
        assert raised.value is close_failure
    assert injected
    assert not target.exists()
    assert tuple(tmp_path.glob(".lychd-create-*")) == ()


@pytest.mark.parametrize(
    "close_failure",
    [OSError("attestation close failed"), KeyboardInterrupt()],
)
def test_attestation_close_failure_is_rescoped_after_exact_rollback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    close_failure: BaseException,
) -> None:
    """A published intermediate cannot remain the reported final outcome."""
    target = tmp_path / "lychd.toml"
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

    expected = PublicationRollbackError if isinstance(close_failure, Exception) else type(close_failure)
    with pytest.raises(expected) as raised:
        JournaledCreation().create_text_file(
            target,
            "answer = 42\n",
            mode=0o600,
        )

    assert close_failure in tuple(iter_exception_graph(raised.value))
    if isinstance(raised.value, PublicationRollbackError):
        assert raised.value.outcome == "rolled_back"
        assert raised.value.outcome_verified
    else:
        assert raised.value is close_failure
    assert injected
    assert not target.exists()
    assert tuple(tmp_path.glob(".lychd-*")) == ()


def test_staging_open_after_effect_retains_named_unverified_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A create without a returned descriptor cannot grant unlink authority."""
    target = tmp_path / "lychd.toml"
    open_failure = KeyboardInterrupt()
    real_open = os.open
    real_close = os.close
    created_name = ""

    def create_then_raise(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal created_name
        if flags & os.O_CREAT and flags & os.O_EXCL:
            descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
            os.write(descriptor, b"peer")
            real_close(descriptor)
            created_name = os.fsdecode(path)
            raise open_failure
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(
        "lychd.system.services.file_publication_transaction.os.open",
        create_then_raise,
    )

    with pytest.raises(PublicationRollbackError) as raised:
        JournaledCreation().create_text_file(
            target,
            "answer = 42\n",
            mode=0o600,
        )

    recovery = tmp_path / created_name
    assert open_failure in tuple(iter_exception_graph(raised.value))
    assert raised.value.outcome == "recovery"
    assert not raised.value.outcome_verified
    assert raised.value.recovery_paths == (recovery,)
    assert recovery.read_bytes() == b"peer"
    assert not target.exists()


def test_named_staging_recovery_survives_parent_close_peer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Outer descriptor settlement keeps exact unverified recovery evidence."""
    target = tmp_path / "lychd.toml"
    primary = OSError("ambiguous create")
    close_failure = KeyboardInterrupt()
    real_open = os.open
    real_close = os.close
    real_settle = DescriptorSet.settle
    created_name = ""

    def create_then_raise(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal created_name
        if flags & os.O_CREAT and flags & os.O_EXCL:
            descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
            real_close(descriptor)
            created_name = os.fsdecode(path)
            raise primary
        return real_open(path, flags, mode, dir_fd=dir_fd)

    def settle_then_fail(descriptors: DescriptorSet) -> tuple[BaseException, ...]:
        return (*real_settle(descriptors), close_failure)

    monkeypatch.setattr(
        "lychd.system.services.file_publication_transaction.os.open",
        create_then_raise,
    )
    monkeypatch.setattr(
        "lychd.system.services.file_publication_transaction.DescriptorSet.settle",
        settle_then_fail,
    )

    with pytest.raises(PublicationRollbackError) as raised:
        JournaledCreation().create_text_file(
            target,
            "answer = 42\n",
            mode=0o600,
        )

    recovery = tmp_path / created_name
    graph = tuple(iter_exception_graph(raised.value))
    assert primary in graph
    assert close_failure in graph
    assert raised.value.outcome == "recovery"
    assert not raised.value.outcome_verified
    assert raised.value.recovery_paths == (recovery,)
    assert recovery.is_file()


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
        "lychd.system.services.file_publication_transaction.os.link",
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


def test_publication_return_signal_rolls_back_exact_file_and_stays_native(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A signal after hard-link publication is classified before propagation."""
    terminal = KeyboardInterrupt()
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
        "lychd.system.services.file_publication_transaction.os.link",
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


@pytest.mark.parametrize(
    "observation_failure",
    [OSError("link observation failed"), KeyboardInterrupt()],
)
def test_link_after_effect_observation_failure_rolls_back_possible_public_exposure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    observation_failure: BaseException,
) -> None:
    """An unreadable link return is conservatively rolled back as published."""
    target = tmp_path / "lychd.toml"
    link_failure = OSError("link completed before adapter failure")
    real_link = os.link
    real_observe = settlement_module.observe_name
    linked = False
    observation_failed = False

    def link_then_raise(
        source: str,
        destination: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
        follow_symlinks: bool,
    ) -> None:
        nonlocal linked
        real_link(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )
        linked = True
        raise link_failure

    def fail_first_classification(
        *,
        parent_fd: int,
        name: str,
    ) -> os.stat_result | None:
        nonlocal observation_failed
        if linked and not observation_failed:
            observation_failed = True
            raise observation_failure
        return real_observe(parent_fd=parent_fd, name=name)

    monkeypatch.setattr(
        "lychd.system.services.file_publication_transaction.os.link",
        link_then_raise,
    )
    monkeypatch.setattr(
        settlement_module,
        "observe_name",
        fail_first_classification,
    )

    expected = PublicationRollbackError if isinstance(observation_failure, Exception) else type(observation_failure)
    with pytest.raises(expected) as raised:
        JournaledCreation().create_text_file(
            target,
            "lychd = true\n",
            mode=0o600,
        )

    graph = tuple(iter_exception_graph(raised.value))
    assert link_failure in graph
    assert observation_failure in graph
    settlement = find_settlement_outcome(raised.value)
    assert settlement is not None
    assert settlement.name == "rolled_back"
    assert settlement.verified
    if isinstance(raised.value, PublicationRollbackError):
        assert raised.value.recovery_paths == ()
    assert not target.exists()
    assert tuple(tmp_path.glob(".lychd-*")) == ()


def test_journal_signal_rolls_back_exact_file_and_stays_native(
    tmp_path: Path,
) -> None:
    """Rollback completes before a terminal journal interruption escapes."""
    terminal = KeyboardInterrupt()
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


def test_rollback_rename_signal_settles_peers_then_preserves_original_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A signal after quarantine rename cannot hide clean rollback truth."""
    terminal = KeyboardInterrupt()
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
        "lychd.system.services.file_publication_recovery.rename_noreplace_at",
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


def test_quarantine_after_effect_observation_failure_retains_exact_random_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rollback cannot forget a detached candidate when observation fails."""
    target = tmp_path / "lychd.toml"
    journal_primary = ValueError("journal rejected")
    rename_failure = OSError("quarantine rename returned failure")
    observation_failure = KeyboardInterrupt()
    real_rename = rename_noreplace_at
    real_observe = settlement_module.observe_name
    detached = False
    observation_failed = False

    def detach_then_raise(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal detached
        real_rename(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )
        if destination_name.startswith(".lychd-rollback-") and not detached:
            detached = True
            raise rename_failure

    def fail_detachment_observation(
        *,
        parent_fd: int,
        name: str,
    ) -> os.stat_result | None:
        nonlocal observation_failed
        if detached and not observation_failed:
            observation_failed = True
            raise observation_failure
        return real_observe(parent_fd=parent_fd, name=name)

    def reject_journal(_resources: CreatedResources) -> None:
        raise journal_primary

    monkeypatch.setattr(
        "lychd.system.services.file_publication_recovery.rename_noreplace_at",
        detach_then_raise,
    )
    monkeypatch.setattr(
        settlement_module,
        "observe_name",
        fail_detachment_observation,
    )

    with pytest.raises(PublicationRollbackError) as raised:
        JournaledCreation(on_created=reject_journal).create_text_file(
            target,
            "lychd = true\n",
            mode=0o600,
        )

    recoveries = tuple(tmp_path.glob(".lychd-rollback-*"))
    assert len(recoveries) == 1
    graph = tuple(iter_exception_graph(raised.value))
    assert journal_primary in graph
    assert rename_failure in graph
    assert observation_failure in graph
    assert raised.value.outcome == "recovery"
    assert not raised.value.outcome_verified
    assert recoveries[0] in raised.value.recovery_paths
    assert recoveries[0].read_text(encoding="utf-8") == "lychd = true\n"
    assert not target.exists()
    assert tuple(tmp_path.glob(".lychd-create-*")) == ()


@pytest.mark.parametrize(
    ("effect", "restore_failure"),
    [
        ("complete", OSError("foreign restore failed")),
        ("complete", KeyboardInterrupt()),
        ("none", KeyboardInterrupt()),
    ],
)
def test_foreign_quarantine_restore_failure_classifies_both_names(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    effect: str,
    restore_failure: BaseException,
) -> None:
    """Foreign data is either restored publicly or retained at its exact name."""
    target = tmp_path / "lychd.toml"
    journal_primary = ValueError("journal rejected")
    real_rename = rename_noreplace_at
    replaced = False

    def replace_quarantine_then_fail_restore(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal replaced
        if destination_name.startswith(".lychd-rollback-") and not replaced:
            real_rename(
                source_name,
                destination_name,
                source_dir_fd=source_dir_fd,
                destination_dir_fd=destination_dir_fd,
            )
            os.unlink(destination_name, dir_fd=destination_dir_fd)
            descriptor = os.open(
                destination_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=destination_dir_fd,
            )
            try:
                os.write(descriptor, b"foreign\n")
            finally:
                os.close(descriptor)
            replaced = True
            return
        if source_name.startswith(".lychd-rollback-") and destination_name == target.name:
            if effect == "complete":
                real_rename(
                    source_name,
                    destination_name,
                    source_dir_fd=source_dir_fd,
                    destination_dir_fd=destination_dir_fd,
                )
            raise restore_failure
        real_rename(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    def reject_journal(_resources: CreatedResources) -> None:
        raise journal_primary

    monkeypatch.setattr(
        "lychd.system.services.file_publication_recovery.rename_noreplace_at",
        replace_quarantine_then_fail_restore,
    )

    expected = (
        PublicationRollbackError
        if effect == "none" or isinstance(restore_failure, Exception)
        else type(restore_failure)
    )
    with pytest.raises(expected) as raised:
        JournaledCreation(on_created=reject_journal).create_text_file(
            target,
            "lychd = true\n",
            mode=0o600,
        )

    graph = tuple(iter_exception_graph(raised.value))
    assert journal_primary in graph
    assert restore_failure in graph
    settlement = find_settlement_outcome(raised.value)
    assert settlement is not None
    if effect == "complete":
        assert settlement.name == "rolled_back"
        assert settlement.verified
        assert target.read_bytes() == b"foreign\n"
        assert tuple(tmp_path.glob(".lychd-rollback-*")) == ()
    else:
        recoveries = tuple(tmp_path.glob(".lychd-rollback-*"))
        assert len(recoveries) == 1
        assert settlement.name == "recovery"
        assert not settlement.verified
        assert recoveries[0].read_bytes() == b"foreign\n"
        evidence = next(
            error
            for error in iter_exception_graph(raised.value)
            if isinstance(error, PublicationRollbackError) and recoveries[0] in error.recovery_paths
        )
        assert evidence.outcome == "recovery"
        assert not target.exists()
    assert tuple(tmp_path.glob(".lychd-create-*")) == ()


def test_foreign_restore_source_disappearance_requires_target_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A vanished source does not prove which inode reached the public name."""
    target = tmp_path / "lychd.toml"
    journal_primary = ValueError("journal rejected")
    restore_failure = KeyboardInterrupt()
    real_rename = rename_noreplace_at
    replaced = False

    def replace_then_lose_foreign_identity(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal replaced
        if destination_name.startswith(".lychd-rollback-") and not replaced:
            real_rename(
                source_name,
                destination_name,
                source_dir_fd=source_dir_fd,
                destination_dir_fd=destination_dir_fd,
            )
            os.unlink(destination_name, dir_fd=destination_dir_fd)
            descriptor = os.open(
                destination_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=destination_dir_fd,
            )
            try:
                os.write(descriptor, b"foreign\n")
            finally:
                os.close(descriptor)
            replaced = True
            return
        if source_name.startswith(".lychd-rollback-") and destination_name == target.name:
            os.unlink(source_name, dir_fd=source_dir_fd)
            descriptor = os.open(
                destination_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=destination_dir_fd,
            )
            try:
                os.write(descriptor, b"unrelated\n")
            finally:
                os.close(descriptor)
            raise restore_failure
        real_rename(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    def reject_journal(_resources: CreatedResources) -> None:
        raise journal_primary

    monkeypatch.setattr(
        "lychd.system.services.file_publication_recovery.rename_noreplace_at",
        replace_then_lose_foreign_identity,
    )

    with pytest.raises(PublicationRollbackError) as raised:
        JournaledCreation(on_created=reject_journal).create_text_file(
            target,
            "lychd = true\n",
            mode=0o600,
        )

    graph = tuple(iter_exception_graph(raised.value))
    assert journal_primary in graph
    assert restore_failure in graph
    assert raised.value.outcome == "recovery"
    assert not raised.value.outcome_verified
    assert raised.value.recovery_paths == (target,)
    assert target.read_bytes() == b"unrelated\n"
    assert tuple(tmp_path.glob(".lychd-*")) == ()


def test_quarantine_unlink_terminal_after_effect_keeps_journal_primary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exact rollback preserves both journal and terminal cleanup failures."""
    terminal = KeyboardInterrupt()
    target = tmp_path / "lychd.toml"
    journal_primary = ValueError("journal rejected")
    real_unlink = os.unlink
    interrupted = False

    def unlink_then_interrupt(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal interrupted
        real_unlink(path, dir_fd=dir_fd)
        if os.fsdecode(path).startswith(".lychd-rollback-") and not interrupted:
            interrupted = True
            raise terminal

    def reject_journal(_resources: CreatedResources) -> None:
        raise journal_primary

    monkeypatch.setattr(
        "lychd.system.services.file_publication_settlement.os.unlink",
        unlink_then_interrupt,
    )

    with pytest.raises(type(terminal)) as raised:
        JournaledCreation(on_created=reject_journal).create_text_file(
            target,
            "lychd = true\n",
            mode=0o600,
        )

    graph = tuple(iter_exception_graph(raised.value))
    assert raised.value is terminal
    assert journal_primary in graph
    assert terminal in graph
    settlement = find_settlement_outcome(raised.value)
    assert settlement is not None
    assert settlement.name == "rolled_back"
    assert settlement.verified
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
