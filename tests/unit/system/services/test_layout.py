from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import ANY, patch

import pytest

from lychd.system.atomic_paths import rename_noreplace_at
from lychd.system.btrfs_identity import BtrfsSubvolumeObservation
from lychd.system.operator import ProcessInvocationError
from lychd.system.services.btrfs import (
    BtrfsCreationError,
    BtrfsCreationEvidence,
    BtrfsCreationState,
    PreparedBtrfsSubvolume,
)
from lychd.system.services.layout import LayoutService
from lychd.system.services.layout_directories import (
    DirectoryProvisioning,
    DirectoryRollbackError,
)
from lychd.system.services.lifecycle import CreatedResources


@pytest.fixture
def test_layout(tmp_path: Path) -> list[Path]:
    """Create a temporary set of directories for testing LayoutService."""
    return [
        tmp_path / "codex",
        tmp_path / "crypt",
        tmp_path / "forge",
    ]


def test_initialize_layout_genesis(
    test_layout: list[Path],
) -> None:
    """Verify that initialize_layout creates the directory structure and handles Btrfs."""
    with patch("lychd.system.services.layout.Btrfs") as mock_btrfs_cls:
        service = LayoutService(paths=test_layout)
        service.initialize()

    # Verify results via side effects
    for path in test_layout:
        assert path.exists()
        assert path.is_dir()

    # Ensure no btrfs commands were run
    mock_btrfs_cls.return_value.create_subvolume.assert_not_called()


def test_initialize_records_only_directories_whose_creation_it_won(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A concurrent creator is preserved without entering lifecycle authority."""
    target = tmp_path / "codex"
    real_rename = rename_noreplace_at
    raced = False

    def race_once(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal raced
        if destination_name == target.name and not raced:
            raced = True
            target.mkdir()
        real_rename(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    monkeypatch.setattr(
        "lychd.system.atomic_paths.rename_noreplace_at",
        race_once,
    )

    resources = LayoutService(paths=(target,)).initialize()

    assert target.is_dir()
    assert target not in resources.directories


@pytest.mark.parametrize("terminal", [KeyboardInterrupt(), SystemExit(59)])
def test_publication_return_interruption_retains_typed_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    terminal: BaseException,
) -> None:
    """A signal after publish cannot leave an unjournaled public directory."""
    target = tmp_path / "codex"
    real_rename = rename_noreplace_at
    interrupted = False

    def publish_then_interrupt(
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
        if destination_name == target.name and not interrupted:
            interrupted = True
            raise terminal

    monkeypatch.setattr(
        "lychd.system.atomic_paths.rename_noreplace_at",
        publish_then_interrupt,
    )

    with pytest.raises(DirectoryRollbackError) as raised:
        DirectoryProvisioning().create(target)

    assert not target.exists()
    quarantines = tuple(tmp_path.glob(".lychd-rollback-*"))
    assert len(quarantines) == 1
    assert quarantines[0].is_dir()
    assert _exception_chain_contains(raised.value, type(terminal))


@pytest.mark.parametrize("terminal", [KeyboardInterrupt(), SystemExit(61)])
def test_rollback_quarantine_return_interruption_retains_exact_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    terminal: BaseException,
) -> None:
    """A signal after rollback rename surfaces its exact private recovery."""
    target = tmp_path / "codex"
    provisioning = DirectoryProvisioning()
    provisioning.create(target)
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

    monkeypatch.setattr(
        "lychd.system.atomic_paths.rename_noreplace_at",
        quarantine_then_interrupt,
    )

    with pytest.raises(DirectoryRollbackError) as raised:
        provisioning.rollback()

    assert not target.exists()
    quarantines = tuple(tmp_path.glob(".lychd-rollback-*"))
    assert len(quarantines) == 1
    assert quarantines[0].is_dir()
    assert _exception_chain_contains(raised.value, type(terminal))


def test_race_loser_cleanup_failure_is_not_retried_with_consumed_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed private-candidate cleanup retains its first recovery evidence."""
    target = tmp_path / "codex"
    real_rename = rename_noreplace_at
    raced = False
    quarantines: list[str] = []

    def race_once(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal raced
        if destination_name == target.name and not raced:
            raced = True
            target.mkdir()
        if destination_name.startswith(".lychd-rollback-"):
            quarantines.append(destination_name)
        real_rename(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    def fail_quarantine_removal(
        path: str,
        *,
        dir_fd: int | None = None,
    ) -> None:
        del path, dir_fd
        message = "simulated quarantine removal failure"
        raise OSError(message)

    monkeypatch.setattr(
        "lychd.system.atomic_paths.rename_noreplace_at",
        race_once,
    )
    monkeypatch.setattr(
        "lychd.system.services.layout_directory_recovery.os.rmdir",
        fail_quarantine_removal,
    )

    with pytest.raises(
        DirectoryRollbackError,
        match="removal failed",
    ):
        LayoutService(paths=(target,)).initialize()

    assert target.is_dir()
    assert len(quarantines) == 1


def test_existing_layout_rejects_an_intermediate_symlink(
    tmp_path: Path,
) -> None:
    """Existing paths are opened component-by-component without following links."""
    outside = tmp_path / "outside"
    target = outside / "codex"
    target.mkdir(parents=True)
    linked_parent = tmp_path / "linked"
    linked_parent.symlink_to(outside, target_is_directory=True)

    with pytest.raises(
        RuntimeError,
        match="Could not traverse managed layout directory",
    ):
        LayoutService(paths=(linked_parent / target.name,)).initialize()

    assert target.is_dir()


def test_existing_layout_closes_descriptor_when_attestation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed descriptor inspection cannot leak the opened layout leaf."""
    target = tmp_path / "existing"
    target.mkdir()
    real_fstat = os.fstat
    failed_descriptor: int | None = None

    def fail_target_attestation(descriptor: int) -> os.stat_result:
        nonlocal failed_descriptor
        descriptor_target = Path(f"/proc/self/fd/{descriptor}").readlink()
        if descriptor_target == target:
            failed_descriptor = descriptor
            raise PermissionError(target)
        return real_fstat(descriptor)

    monkeypatch.setattr(
        "lychd.system.services.layout_directory_traversal.os.fstat",
        fail_target_attestation,
    )

    with pytest.raises(PermissionError):
        LayoutService(paths=(target,)).initialize()

    assert failed_descriptor is not None
    with pytest.raises(OSError, match="Bad file descriptor"):
        real_fstat(failed_descriptor)


def test_initialize_rolls_back_only_successful_component_creations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A later mkdir failure cannot leak an unreceipted parent."""
    parent = tmp_path / "crypt"
    target = parent / "blocked"
    real_rename = rename_noreplace_at

    def fail_leaf(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        if destination_name == target.name:
            raise PermissionError(target)
        real_rename(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    monkeypatch.setattr(
        "lychd.system.atomic_paths.rename_noreplace_at",
        fail_leaf,
    )

    with pytest.raises(
        DirectoryRollbackError,
        match="Linux cannot bind rmdir to the attested inode",
    ):
        LayoutService(paths=(target,)).initialize()

    assert not parent.exists()
    quarantines = tuple(tmp_path.glob(".lychd-rollback-*"))
    assert len(quarantines) == 1
    assert quarantines[0].is_dir()


def test_initialize_rolls_back_staging_when_first_attestation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An identity-less candidate is quarantined, never deleted by pathname."""
    target = tmp_path / "attestation-failure"
    real_fstat = os.fstat
    failed = False

    def fail_first_attestation(descriptor: int) -> os.stat_result:
        nonlocal failed
        descriptor_target = Path(f"/proc/self/fd/{descriptor}").readlink()
        if not failed and descriptor_target.name.startswith(".lychd-mkdir-"):
            failed = True
            raise PermissionError(target)
        return real_fstat(descriptor)

    monkeypatch.setattr(
        "lychd.system.services.layout_directory_traversal.os.fstat",
        fail_first_attestation,
    )

    with pytest.raises(
        DirectoryRollbackError,
        match="Unattested staged layout directory is retained",
    ):
        LayoutService(paths=(target,)).initialize()

    assert failed is True
    assert not target.exists()
    quarantines = tuple(tmp_path.glob(".lychd-rollback-*"))
    assert len(quarantines) == 1
    assert quarantines[0].is_dir()


def test_attestation_terminal_retains_typed_unverified_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A terminal failed attestation cannot flatten named recovery to success."""
    target = tmp_path / "attestation-interruption"
    real_fstat = os.fstat
    interrupted = False

    def interrupt_first_attestation(descriptor: int) -> os.stat_result:
        nonlocal interrupted
        descriptor_target = Path(f"/proc/self/fd/{descriptor}").readlink()
        if not interrupted and descriptor_target.name.startswith(".lychd-mkdir-"):
            interrupted = True
            raise KeyboardInterrupt
        return real_fstat(descriptor)

    monkeypatch.setattr(
        "lychd.system.services.layout_directory_traversal.os.fstat",
        interrupt_first_attestation,
    )

    with pytest.raises(DirectoryRollbackError) as raised:
        DirectoryProvisioning().create(target)

    assert not target.exists()
    assert len(tuple(tmp_path.glob(".lychd-rollback-*"))) == 1
    assert _exception_graph_contains(raised.value, KeyboardInterrupt)


@pytest.mark.parametrize(
    ("terminal", "phase"),
    [
        (KeyboardInterrupt(), "before"),
        (SystemExit(67), "after"),
    ],
)
def test_created_identity_is_published_before_final_descriptor_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    terminal: BaseException,
    phase: str,
) -> None:
    """A final close signal cannot strand an untracked public creation."""
    target = tmp_path / "managed"
    provisioning = DirectoryProvisioning()
    real_close = os.close
    interrupted_fd: int | None = None

    def interrupt_leaf_close(descriptor: int) -> None:
        nonlocal interrupted_fd
        descriptor_target = Path(f"/proc/self/fd/{descriptor}").readlink()
        if interrupted_fd is None and descriptor_target == target:
            interrupted_fd = descriptor
            if phase == "after":
                real_close(descriptor)
            raise terminal
        real_close(descriptor)

    monkeypatch.setattr(
        "lychd.system.descriptor_settlement.os.close",
        interrupt_leaf_close,
    )

    with pytest.raises(type(terminal)) as raised:
        provisioning.create(target)

    assert provisioning.created_paths == (target,)
    assert target.is_dir()
    assert any("recorded every created directory" in note for note in raised.value.__notes__)
    monkeypatch.undo()
    if phase == "before":
        assert interrupted_fd is not None
        real_close(interrupted_fd)
    provisioning.commit()


def test_commit_close_terminal_settles_every_peer_and_reports_public_truth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Committed publication survives while all descriptor peers are attempted."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    provisioning = DirectoryProvisioning()
    provisioning.create(first)
    provisioning.create(second)
    real_close = os.close
    close_calls: list[int] = []

    def interrupt_then_fail(descriptor: int) -> None:
        close_calls.append(descriptor)
        if len(close_calls) == 1:
            raise KeyboardInterrupt
        real_close(descriptor)
        message = "post-close peer failure"
        raise OSError(message)

    monkeypatch.setattr(
        "lychd.system.descriptor_settlement.os.close",
        interrupt_then_fail,
    )

    with pytest.raises(KeyboardInterrupt) as raised:
        provisioning.commit()

    assert len(close_calls) == 2
    assert first.is_dir()
    assert second.is_dir()
    assert any("committed the public directory publication" in note for note in raised.value.__notes__)
    monkeypatch.undo()
    real_close(close_calls[0])
    provisioning.commit()


def test_rollback_close_terminal_settles_every_peer_before_typed_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rollback attempts every entry and close even when one close is interrupted."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    provisioning = DirectoryProvisioning()
    provisioning.create(first)
    provisioning.create(second)
    real_close = os.close
    close_calls: list[int] = []

    def interrupt_first_close(descriptor: int) -> None:
        close_calls.append(descriptor)
        if len(close_calls) == 1:
            raise KeyboardInterrupt
        real_close(descriptor)

    monkeypatch.setattr(
        "lychd.system.descriptor_settlement.os.close",
        interrupt_first_close,
    )

    with pytest.raises(DirectoryRollbackError) as raised:
        provisioning.rollback()

    assert len(close_calls) == 2
    assert not first.exists()
    assert not second.exists()
    assert len(tuple(tmp_path.glob(".lychd-rollback-*"))) == 2
    assert _exception_graph_contains(raised.value, KeyboardInterrupt)
    monkeypatch.undo()
    real_close(close_calls[0])


def test_staging_rollback_precedes_a_terminal_descriptor_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A staging close interruption cannot prevent exact private rollback."""
    target = tmp_path / "managed"
    real_rename = rename_noreplace_at
    real_close = os.close
    events: list[str] = []

    def reject_publication(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        if destination_name == target.name:
            message = "publication rejected"
            raise RuntimeError(message)
        events.append("rollback")
        real_rename(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    def interrupt_staging_close(descriptor: int) -> None:
        descriptor_target = Path(f"/proc/self/fd/{descriptor}").readlink()
        real_close(descriptor)
        if ".lychd-" in str(descriptor_target):
            events.append("close")
            raise KeyboardInterrupt

    monkeypatch.setattr(
        "lychd.system.atomic_paths.rename_noreplace_at",
        reject_publication,
    )
    monkeypatch.setattr(
        "lychd.system.descriptor_settlement.os.close",
        interrupt_staging_close,
    )

    with pytest.raises(KeyboardInterrupt) as raised:
        DirectoryProvisioning().create(target)

    assert not target.exists()
    assert tuple(tmp_path.iterdir()) == ()
    assert events == ["rollback", "close"]
    assert any("rolled back every proven directory effect" in note for note in raised.value.__notes__)


def test_publication_observation_terminal_retains_unverified_public_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Observation cancellation after publish never authorizes pathname deletion."""
    target = tmp_path / "managed"
    real_rename = rename_noreplace_at
    observation_failed = False
    rmdir_calls = 0

    def publish_then_interrupt(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        real_rename(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )
        if destination_name == target.name:
            raise KeyboardInterrupt

    def interrupt_observation(*, parent_fd: int, name: str) -> os.stat_result | None:
        nonlocal observation_failed
        del parent_fd, name
        if not observation_failed:
            observation_failed = True
            raise SystemExit(71)
        pytest.fail("indeterminate publication was observed again")

    def reject_delete(path: str, *, dir_fd: int | None = None) -> None:
        nonlocal rmdir_calls
        del path, dir_fd
        rmdir_calls += 1
        pytest.fail("unverified publication reached rmdir")

    monkeypatch.setattr(
        "lychd.system.atomic_paths.rename_noreplace_at",
        publish_then_interrupt,
    )
    monkeypatch.setattr(
        "lychd.system.services.layout_directory_traversal.observe_directory",
        interrupt_observation,
    )
    monkeypatch.setattr(
        "lychd.system.services.layout_directory_recovery.os.rmdir",
        reject_delete,
    )

    with pytest.raises(DirectoryRollbackError) as raised:
        DirectoryProvisioning().create(target)

    assert target.is_dir()
    assert rmdir_calls == 0
    assert _exception_graph_contains(raised.value, KeyboardInterrupt)
    assert _exception_graph_contains(raised.value, SystemExit)


def test_quarantine_observation_terminal_retains_named_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed post-rename observation cannot delete the quarantine."""
    target = tmp_path / "managed"
    provisioning = DirectoryProvisioning()
    provisioning.create(target)
    real_rename = rename_noreplace_at
    interrupted = False
    observed = False

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
            raise KeyboardInterrupt

    def interrupt_observation(*, parent_fd: int, name: str) -> os.stat_result | None:
        nonlocal observed
        del parent_fd, name
        if not observed:
            observed = True
            raise SystemExit(73)
        pytest.fail("indeterminate quarantine was observed again")

    monkeypatch.setattr(
        "lychd.system.atomic_paths.rename_noreplace_at",
        quarantine_then_interrupt,
    )
    monkeypatch.setattr(
        "lychd.system.services.layout_directory_traversal.observe_directory",
        interrupt_observation,
    )

    with pytest.raises(DirectoryRollbackError) as raised:
        provisioning.rollback()

    assert not target.exists()
    assert len(tuple(tmp_path.glob(".lychd-rollback-*"))) == 1
    assert _exception_graph_contains(raised.value, KeyboardInterrupt)
    assert _exception_graph_contains(raised.value, SystemExit)


def test_private_removal_observation_terminal_retains_named_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An interrupted rmdir is never treated as success without observation."""
    target = tmp_path / "managed"
    real_rename = rename_noreplace_at
    quarantine_name: str | None = None

    def reject_publication(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal quarantine_name
        if destination_name == target.name:
            message = "publication rejected"
            raise RuntimeError(message)
        quarantine_name = destination_name
        real_rename(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    def interrupt_removal(path: str, *, dir_fd: int | None = None) -> None:
        del dir_fd
        if path == quarantine_name:
            raise KeyboardInterrupt
        pytest.fail("unexpected directory removal")

    def interrupt_observation(*, parent_fd: int, name: str) -> os.stat_result | None:
        del parent_fd
        if name == quarantine_name:
            raise SystemExit(77)
        pytest.fail("unexpected directory observation")

    monkeypatch.setattr(
        "lychd.system.atomic_paths.rename_noreplace_at",
        reject_publication,
    )
    monkeypatch.setattr(
        "lychd.system.services.layout_directory_recovery.os.rmdir",
        interrupt_removal,
    )
    monkeypatch.setattr(
        "lychd.system.services.layout_directory_traversal.observe_directory",
        interrupt_observation,
    )

    with pytest.raises(DirectoryRollbackError) as raised:
        DirectoryProvisioning().create(target)

    assert quarantine_name is not None
    assert not target.exists()
    assert (tmp_path / quarantine_name).is_dir()
    assert _exception_graph_contains(raised.value, KeyboardInterrupt)
    assert _exception_graph_contains(raised.value, SystemExit)


def test_restore_observation_terminal_never_deletes_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An indeterminate restore preserves both foreign and created identities."""
    target = tmp_path / "managed"
    displaced = tmp_path / "created"
    provisioning = DirectoryProvisioning()
    provisioning.create(target)
    target.rename(displaced)
    target.mkdir()
    real_rename = rename_noreplace_at
    restore_interrupted = False

    def restore_then_interrupt(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal restore_interrupted
        real_rename(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )
        if source_name.startswith(".lychd-rollback-") and destination_name == target.name:
            restore_interrupted = True
            raise KeyboardInterrupt

    def interrupt_restore_observation(*, parent_fd: int, name: str) -> os.stat_result | None:
        del parent_fd, name
        if restore_interrupted:
            raise SystemExit(79)
        pytest.fail("unexpected pre-restore observation")

    monkeypatch.setattr(
        "lychd.system.atomic_paths.rename_noreplace_at",
        restore_then_interrupt,
    )
    monkeypatch.setattr(
        "lychd.system.services.layout_directory_traversal.observe_directory",
        interrupt_restore_observation,
    )

    with pytest.raises(DirectoryRollbackError) as raised:
        provisioning.rollback()

    assert target.is_dir()
    assert displaced.is_dir()
    assert _exception_graph_contains(raised.value, KeyboardInterrupt)
    assert _exception_graph_contains(raised.value, SystemExit)


@pytest.mark.parametrize(
    ("terminal", "phase"),
    [
        (KeyboardInterrupt(), "before"),
        (SystemExit(83), "after"),
    ],
)
def test_staging_mkdir_terminal_is_classified_by_postcondition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    terminal: BaseException,
    phase: str,
) -> None:
    """Pre-effect cancellation is native; post-effect cancellation is recovery."""
    target = tmp_path / "managed"
    real_mkdir = os.mkdir

    def interrupt_mkdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        if phase == "after":
            real_mkdir(path, mode, dir_fd=dir_fd)
        raise terminal

    monkeypatch.setattr(
        "lychd.system.services.layout_directory_publication.os.mkdir",
        interrupt_mkdir,
    )

    if phase == "after":
        with pytest.raises(DirectoryRollbackError) as raised:
            DirectoryProvisioning().create(target)
        assert _exception_graph_contains(raised.value, type(terminal))
        assert len(tuple(tmp_path.glob(".lychd-rollback-*"))) == 1
    else:
        with pytest.raises(type(terminal)):
            DirectoryProvisioning().create(target)
        assert tuple(tmp_path.iterdir()) == ()
    assert not target.exists()


def test_receipt_failure_preserves_replacement_and_uses_creation_identity(
    tmp_path: Path,
) -> None:
    """Rollback tokens remain pinned until the journal callback succeeds."""
    parent = tmp_path / "managed"
    target = parent / "leaf"
    displaced_parent = parent.with_name("managed-created-by-init")

    def replace_then_reject(resources: CreatedResources) -> None:
        assert resources.directories[-1] == target
        target_identity = resources.directory_identities[-1]
        assert target_identity.path == target
        assert target_identity.device == target.lstat().st_dev
        assert target_identity.inode == target.lstat().st_ino
        parent.rename(displaced_parent)
        target.mkdir(parents=True)
        msg = "simulated receipt failure"
        raise RuntimeError(msg)

    with pytest.raises(
        DirectoryRollbackError,
        match="Exact directory rollback did not complete",
    ):
        LayoutService(paths=(target,)).initialize(
            on_created=replace_then_reject,
        )

    assert target.is_dir()
    assert displaced_parent.is_dir()
    assert not (displaced_parent / target.name).exists()


def test_receipt_failure_surfaces_nonempty_exact_rollback_quarantine(
    tmp_path: Path,
) -> None:
    """An exact creation that became nonempty is quarantined, never suppressed."""
    target = tmp_path / "managed"

    def make_nonempty_then_reject(_resources: CreatedResources) -> None:
        (target / "foreign.txt").write_text("preserve me", encoding="utf-8")
        msg = "simulated receipt failure"
        raise RuntimeError(msg)

    with pytest.raises(
        DirectoryRollbackError,
        match="Exact directory rollback did not complete",
    ):
        LayoutService(paths=(target,)).initialize(
            on_created=make_nonempty_then_reject,
        )

    assert not target.exists()
    quarantines = tuple(tmp_path.glob(".lychd-rollback-*"))
    assert len(quarantines) == 1
    assert (quarantines[0] / "foreign.txt").read_text(encoding="utf-8") == "preserve me"


def test_published_rollback_never_pathname_deletes_after_attestation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A same-UID swap cannot redirect rollback into a foreign rmdir."""
    target = tmp_path / "managed"
    rmdir_attempts: list[str] = []

    def reject_pathname_delete(
        path: str,
        *,
        dir_fd: int | None = None,
    ) -> None:
        del dir_fd
        rmdir_attempts.append(path)
        pytest.fail("published rollback attempted pathname rmdir")

    def reject_receipt(_resources: CreatedResources) -> None:
        msg = "simulated receipt failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        "lychd.system.services.layout_directory_recovery.os.rmdir",
        reject_pathname_delete,
    )

    with pytest.raises(
        DirectoryRollbackError,
        match="Linux cannot bind rmdir to the attested inode",
    ):
        LayoutService(paths=(target,)).initialize(on_created=reject_receipt)

    assert rmdir_attempts == []
    assert not target.exists()
    assert len(tuple(tmp_path.glob(".lychd-rollback-*"))) == 1


def test_pinned_directory_rejects_public_parent_replacement(
    tmp_path: Path,
) -> None:
    """A later Btrfs effect cannot inherit a substituted parent pathname."""
    parent = tmp_path / "postgres"
    displaced = tmp_path / "postgres-created-by-init"
    provisioning = DirectoryProvisioning()
    provisioning.create(parent)

    parent.rename(displaced)
    parent.mkdir()

    try:
        with (
            pytest.raises(RuntimeError, match="changed identity before use"),
            provisioning.pin(parent),
        ):
            pytest.fail("replacement parent unexpectedly received authority")
    finally:
        provisioning.commit()


def test_initialize_layout_btrfs(
    tmp_path: Path,
) -> None:
    """Verify that LayoutService applies Btrfs rituals when detected."""
    crypt_root = tmp_path / "crypt"
    postgres_data_dir = crypt_root / "postgres" / "data"
    layout = [crypt_root, postgres_data_dir]

    with (
        patch("lychd.system.services.layout.PATH_POSTGRESS_DATA_DIR", postgres_data_dir),
        patch("lychd.system.services.layout.Btrfs") as mock_btrfs_cls,
    ):
        mock_btrfs = mock_btrfs_cls.return_value
        observation = BtrfsSubvolumeObservation(
            uuid="12345678-1234-5678-1234-567812345678",
            subvolume_id=259,
        )

        def create(
            path: Path,
            *,
            parent_fd: int,
        ) -> BtrfsSubvolumeObservation:
            del parent_fd
            path.mkdir(parents=True)
            return observation

        def prepare(
            path: Path,
            *,
            parent_fd: int,
            expected: BtrfsSubvolumeObservation,
        ) -> PreparedBtrfsSubvolume:
            del parent_fd
            metadata = path.lstat()
            return PreparedBtrfsSubvolume(
                observation=expected,
                device=metadata.st_dev,
                inode=metadata.st_ino,
                nocow=True,
            )

        mock_btrfs.create_subvolume.side_effect = create
        mock_btrfs.prepare_created_subvolume.side_effect = prepare

        service = LayoutService(paths=layout)
        resources = service.initialize()

    mock_btrfs.create_subvolume.assert_called_once_with(
        postgres_data_dir,
        parent_fd=ANY,
    )
    mock_btrfs.prepare_created_subvolume.assert_called_once_with(
        postgres_data_dir,
        parent_fd=ANY,
        expected=observation,
    )
    assert tuple(item.path for item in resources.subvolumes) == (postgres_data_dir,)
    assert postgres_data_dir not in resources.directories
    assert resources.subvolumes[0].subvolume_uuid == observation.uuid
    assert resources.subvolumes[0].subvolume_id == observation.subvolume_id


def test_unverified_nocow_policy_does_not_discard_created_subvolume(
    tmp_path: Path,
) -> None:
    """A false No-COW result is a warning, not indeterminate provisioning."""
    postgres_data_dir = tmp_path / "crypt" / "postgres" / "data"
    observation = BtrfsSubvolumeObservation(
        uuid="12345678-1234-5678-1234-567812345678",
        subvolume_id=259,
    )

    with (
        patch("lychd.system.services.layout.PATH_POSTGRESS_DATA_DIR", postgres_data_dir),
        patch("lychd.system.services.layout.Btrfs") as mock_btrfs_cls,
        patch("lychd.system.services.layout.logger.warning") as log_warning,
    ):
        mock_btrfs = mock_btrfs_cls.return_value

        def create(
            path: Path,
            *,
            parent_fd: int,
        ) -> BtrfsSubvolumeObservation:
            del parent_fd
            path.mkdir(parents=True)
            return observation

        def prepare(
            path: Path,
            *,
            parent_fd: int,
            expected: BtrfsSubvolumeObservation,
        ) -> PreparedBtrfsSubvolume:
            del parent_fd
            metadata = path.lstat()
            return PreparedBtrfsSubvolume(
                observation=expected,
                device=metadata.st_dev,
                inode=metadata.st_ino,
                nocow=False,
            )

        mock_btrfs.create_subvolume.side_effect = create
        mock_btrfs.prepare_created_subvolume.side_effect = prepare

        resources = LayoutService(paths=(postgres_data_dir,)).initialize()

    assert tuple(item.path for item in resources.subvolumes) == (postgres_data_dir,)
    assert log_warning.call_args.args == ("layout_db_subvolume_unoptimized",)


def test_receipt_failure_defers_typed_subvolume_to_attested_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A pathname replacement race can never redirect Btrfs rollback deletion."""
    postgres_data_dir = tmp_path / "crypt" / "postgres" / "data"
    displaced = postgres_data_dir.with_name("data-created-by-init")
    observation = BtrfsSubvolumeObservation(
        uuid="12345678-1234-5678-1234-567812345678",
        subvolume_id=259,
    )
    rmdir_attempts: list[Path] = []
    real_rmdir = Path.rmdir

    def guarded_rmdir(path: Path) -> None:
        rmdir_attempts.append(path)
        if path == postgres_data_dir:
            pytest.fail("typed subvolume reached generic rmdir rollback")
        real_rmdir(path)

    def reject_receipt(resources: CreatedResources) -> None:
        assert tuple(item.path for item in resources.subvolumes) == (postgres_data_dir,)
        postgres_data_dir.rename(displaced)
        postgres_data_dir.mkdir()
        msg = "simulated receipt failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(Path, "rmdir", guarded_rmdir)
    with (
        patch("lychd.system.services.layout.PATH_POSTGRESS_DATA_DIR", postgres_data_dir),
        patch("lychd.system.services.layout.Btrfs") as mock_btrfs_cls,
        patch("lychd.system.services.layout.logger.error") as log_error,
    ):
        mock_btrfs = mock_btrfs_cls.return_value

        def create(
            path: Path,
            *,
            parent_fd: int,
        ) -> BtrfsSubvolumeObservation:
            del parent_fd
            path.mkdir(parents=True)
            return observation

        def prepare(
            path: Path,
            *,
            parent_fd: int,
            expected: BtrfsSubvolumeObservation,
        ) -> PreparedBtrfsSubvolume:
            del parent_fd
            metadata = path.lstat()
            return PreparedBtrfsSubvolume(
                observation=expected,
                device=metadata.st_dev,
                inode=metadata.st_ino,
                nocow=True,
            )

        mock_btrfs.create_subvolume.side_effect = create
        mock_btrfs.prepare_created_subvolume.side_effect = prepare
        service = LayoutService(paths=(postgres_data_dir,))

        with pytest.raises(RuntimeError, match="simulated receipt failure"):
            service.initialize(on_created=reject_receipt)

    assert postgres_data_dir.is_dir()
    assert displaced.is_dir()
    assert postgres_data_dir not in rmdir_attempts
    assert log_error.call_args.args == ("layout_created_subvolume_rollback_handoff_required",)
    mock_btrfs.inspect_subvolume.assert_not_called()
    mock_btrfs.delete_subvolume.assert_not_called()


def test_failed_subvolume_provision_defers_typed_target_to_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A post-create failure never feeds a typed subvolume to pathname deletion."""
    postgres_data_dir = tmp_path / "crypt" / "postgres" / "data"
    observation = BtrfsSubvolumeObservation(
        uuid="12345678-1234-5678-1234-567812345678",
        subvolume_id=259,
    )
    rmdir_attempts: list[Path] = []
    real_rmdir = Path.rmdir

    def guarded_rmdir(path: Path) -> None:
        rmdir_attempts.append(path)
        if path == postgres_data_dir:
            pytest.fail("materialized subvolume reached generic rmdir rollback")
        real_rmdir(path)

    monkeypatch.setattr(Path, "rmdir", guarded_rmdir)
    with (
        patch("lychd.system.services.layout.PATH_POSTGRESS_DATA_DIR", postgres_data_dir),
        patch("lychd.system.services.layout.Btrfs") as mock_btrfs_cls,
    ):
        mock_btrfs = mock_btrfs_cls.return_value

        def create(
            path: Path,
            *,
            parent_fd: int,
        ) -> BtrfsSubvolumeObservation:
            del parent_fd
            path.mkdir(parents=True)
            return observation

        mock_btrfs.create_subvolume.side_effect = create
        mock_btrfs.prepare_created_subvolume.side_effect = RuntimeError("simulated No-COW failure")
        service = LayoutService(paths=(postgres_data_dir,))

        with pytest.raises(RuntimeError, match="simulated No-COW failure"):
            service.initialize()

    assert postgres_data_dir.is_dir()
    assert postgres_data_dir not in rmdir_attempts
    mock_btrfs.inspect_subvolume.assert_not_called()
    mock_btrfs.delete_subvolume.assert_not_called()


def _exception_chain_contains(
    error: BaseException,
    expected_type: type[BaseException],
) -> bool:
    """Return whether one explicit cause chain retains the expected failure."""
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        if isinstance(current, expected_type):
            return True
        seen.add(id(current))
        current = current.__cause__
    return False


def _exception_graph_contains(
    error: BaseException,
    expected_type: type[BaseException],
) -> bool:
    """Search explicit chains and retained settlement peers without cycles."""
    pending = [error]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, expected_type):
            return True
        pending.extend(
            linked
            for linked in (
                current.__cause__,
                current.__context__,
                *getattr(current, "failures", ()),
            )
            if isinstance(linked, BaseException)
        )
    return False


@pytest.mark.parametrize(
    ("cause", "raised_type"),
    [
        (ProcessInvocationError("timed out"), BtrfsCreationError),
        (KeyboardInterrupt(), KeyboardInterrupt),
        (SystemExit(23), SystemExit),
    ],
)
def test_materialized_creation_interruption_retains_ancestry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cause: BaseException,
    raised_type: type[BaseException],
) -> None:
    """Creation residue and its descriptor ancestry never reach mkdir rollback."""
    postgres_data = tmp_path / "crypt" / "postgres" / "data"
    commits = 0
    real_commit = DirectoryProvisioning.commit

    def record_commit(provisioning: DirectoryProvisioning) -> None:
        nonlocal commits
        commits += 1
        real_commit(provisioning)

    def reject_rollback(_provisioning: DirectoryProvisioning) -> None:
        pytest.fail("possible Btrfs creation residue reached directory rollback")

    monkeypatch.setattr(DirectoryProvisioning, "commit", record_commit)
    monkeypatch.setattr(DirectoryProvisioning, "rollback", reject_rollback)
    with (
        patch("lychd.system.services.layout.PATH_POSTGRESS_DATA_DIR", postgres_data),
        patch("lychd.system.services.layout.Btrfs") as mock_btrfs_cls,
    ):

        def materialize_then_fail(
            path: Path,
            *,
            parent_fd: int,
        ) -> BtrfsSubvolumeObservation:
            del parent_fd
            path.mkdir()
            evidence = BtrfsCreationEvidence(
                path=path,
                state=BtrfsCreationState.PRESENT_UNATTESTED,
            )
            message = "creation interrupted"
            raise BtrfsCreationError(
                message,
                evidence=evidence,
                cause=cause,
            ) from cause

        mock_btrfs_cls.return_value.create_subvolume.side_effect = materialize_then_fail
        with pytest.raises(raised_type):
            LayoutService(paths=(postgres_data,)).initialize()

    assert commits == 1
    assert postgres_data.is_dir()
    assert postgres_data.parent.is_dir()
