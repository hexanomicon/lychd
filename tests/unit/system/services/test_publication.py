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
from lychd.system.services import file_publication_transaction as transaction_module
from lychd.system.services import publication as publication_facade
from lychd.system.services.publication import (
    JournaledCreation,
    PublicationRollbackError,
)

if TYPE_CHECKING:
    from pathlib import Path

    from lychd.system.services.lifecycle import CreatedResources


def test_publication_facade_preserves_provenance_and_os_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Extraction keeps public introspection and the existing fault-injection seam."""

    def injected_fsync(_descriptor: int) -> None:
        return

    monkeypatch.setattr(publication_facade.os, "fsync", injected_fsync)

    assert JournaledCreation.__module__ == "lychd.system.services.publication"
    assert PublicationRollbackError.__module__ == "lychd.system.services.publication"
    assert repr(JournaledCreation) == "<class 'lychd.system.services.publication.JournaledCreation'>"
    assert transaction_module.os.fsync is injected_fsync
    assert settlement_module.os.fsync is injected_fsync


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
    [OSError("staging close failed"), KeyboardInterrupt(), SystemExit(89)],
)
def test_staging_primary_and_close_failure_remove_exact_private_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    close_failure: BaseException,
) -> None:
    """A close peer cannot mask the primary or leave private staging residue."""
    target = tmp_path / "lychd.toml"
    primary = ValueError("staging validation failed")
    real_close = os.close
    real_fstat = os.fstat
    injected = False

    def fail_validation(
        _metadata: os.stat_result,
        *,
        path: Path,
    ) -> None:
        del path
        raise primary

    def close_then_fail(descriptor: int) -> None:
        nonlocal injected
        is_regular = stat.S_ISREG(real_fstat(descriptor).st_mode)
        real_close(descriptor)
        if is_regular and not injected:
            injected = True
            raise close_failure

    monkeypatch.setattr(
        "lychd.system.services.file_publication_settlement.require_regular_file",
        fail_validation,
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
    [OSError("attestation close failed"), KeyboardInterrupt(), SystemExit(90)],
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


@pytest.mark.parametrize(
    "open_failure",
    [OSError("create return failed"), KeyboardInterrupt(), SystemExit(105)],
)
def test_staging_open_after_effect_retains_named_unverified_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    open_failure: BaseException,
) -> None:
    """A create without a returned descriptor cannot grant unlink authority."""
    target = tmp_path / "lychd.toml"
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
    assert recovery.is_file()
    assert not target.exists()


def test_staging_open_error_preserves_indistinguishable_peer_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-error pathname observation never adopts a racer's file identity."""
    target = tmp_path / "lychd.toml"
    primary = OSError("create failed before effect")
    real_open = os.open
    real_close = os.close
    peer_name = ""

    def race_then_fail(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal peer_name
        if flags & os.O_CREAT and flags & os.O_EXCL:
            descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
            os.write(descriptor, b"peer")
            real_close(descriptor)
            peer_name = os.fsdecode(path)
            raise primary
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(
        "lychd.system.services.file_publication_transaction.os.open",
        race_then_fail,
    )

    with pytest.raises(PublicationRollbackError) as raised:
        JournaledCreation().create_text_file(
            target,
            "answer = 42\n",
            mode=0o600,
        )

    peer = tmp_path / peer_name
    assert primary in tuple(iter_exception_graph(raised.value))
    assert raised.value.outcome == "recovery"
    assert not raised.value.outcome_verified
    assert raised.value.recovery_paths == (peer,)
    assert peer.read_bytes() == b"peer"
    assert not target.exists()


@pytest.mark.parametrize(
    "metadata_failure",
    [OSError("metadata return failed"), KeyboardInterrupt(), SystemExit(106)],
)
def test_pre_identity_staging_failure_retains_exact_recovery_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    metadata_failure: BaseException,
) -> None:
    """A returned descriptor does not authorize deletion before identity capture."""
    target = tmp_path / "lychd.toml"

    def fail_before_identity(_descriptor: int, _mode: int) -> None:
        raise metadata_failure

    monkeypatch.setattr(
        "lychd.system.services.file_publication_transaction.os.fchmod",
        fail_before_identity,
    )

    with pytest.raises(PublicationRollbackError) as raised:
        JournaledCreation().create_text_file(
            target,
            "answer = 42\n",
            mode=0o600,
        )

    recoveries = tuple(tmp_path.glob(".lychd-create-*"))
    assert metadata_failure in tuple(iter_exception_graph(raised.value))
    assert raised.value.outcome == "recovery"
    assert not raised.value.outcome_verified
    assert raised.value.recovery_paths == recoveries
    assert len(recoveries) == 1
    assert recoveries[0].read_bytes() == b""
    assert not target.exists()


@pytest.mark.parametrize(
    "close_failure",
    [OSError("parent close failed"), KeyboardInterrupt(), SystemExit(107)],
)
def test_named_staging_recovery_survives_parent_close_peer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    close_failure: BaseException,
) -> None:
    """Outer descriptor settlement keeps exact unverified recovery evidence."""
    target = tmp_path / "lychd.toml"
    primary = OSError("ambiguous create")
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
    [OSError("link observation failed"), KeyboardInterrupt(), SystemExit(109)],
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


@pytest.mark.parametrize(
    "observation_failure",
    [OSError("quarantine observation failed"), KeyboardInterrupt(), SystemExit(111)],
)
def test_quarantine_after_effect_observation_failure_retains_exact_random_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    observation_failure: BaseException,
) -> None:
    """Rollback cannot forget a detached candidate when observation fails."""
    target = tmp_path / "lychd.toml"
    journal_primary = ValueError("journal rejected")
    rename_failure = OSError("quarantine rename returned failure")
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


@pytest.mark.parametrize("effect", ["complete", "none"])
@pytest.mark.parametrize(
    "restore_failure",
    [OSError("foreign restore failed"), KeyboardInterrupt(), SystemExit(113)],
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


@pytest.mark.parametrize(
    "restore_failure",
    [OSError("foreign restore failed"), KeyboardInterrupt(), SystemExit(114)],
)
def test_foreign_restore_source_disappearance_requires_target_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    restore_failure: BaseException,
) -> None:
    """A vanished source does not prove which inode reached the public name."""
    target = tmp_path / "lychd.toml"
    journal_primary = ValueError("journal rejected")
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


@pytest.mark.parametrize("terminal", [KeyboardInterrupt(), SystemExit(115)])
def test_staging_unlink_terminal_after_effect_keeps_cleanup_priority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    terminal: BaseException,
) -> None:
    """A verified staging unlink cannot swallow its terminal cleanup peer."""
    target = tmp_path / "lychd.toml"
    primary = ValueError("staging validation failed")
    real_unlink = os.unlink
    interrupted = False

    def fail_validation(
        _metadata: os.stat_result,
        *,
        path: Path,
    ) -> None:
        del path
        raise primary

    def unlink_then_interrupt(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal interrupted
        real_unlink(path, dir_fd=dir_fd)
        if os.fsdecode(path).startswith(".lychd-create-") and not interrupted:
            interrupted = True
            raise terminal

    monkeypatch.setattr(
        "lychd.system.services.file_publication_settlement.require_regular_file",
        fail_validation,
    )
    monkeypatch.setattr(
        "lychd.system.services.file_publication_settlement.os.unlink",
        unlink_then_interrupt,
    )

    with pytest.raises(type(terminal)) as raised:
        JournaledCreation().create_text_file(
            target,
            "lychd = true\n",
            mode=0o600,
        )

    graph = tuple(iter_exception_graph(raised.value))
    assert raised.value is terminal
    assert primary in graph
    assert terminal in graph
    settlement = find_settlement_outcome(raised.value)
    assert settlement is not None
    assert settlement.name == "rolled_back"
    assert settlement.verified
    assert tuple(tmp_path.glob(".lychd-*")) == ()


@pytest.mark.parametrize("terminal", [KeyboardInterrupt(), SystemExit(117)])
def test_quarantine_unlink_terminal_after_effect_keeps_journal_primary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    terminal: BaseException,
) -> None:
    """Exact rollback preserves both journal and terminal cleanup failures."""
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
