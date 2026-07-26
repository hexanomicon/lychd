"""Focused authority tests for resumable Phylactery deletion."""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from lychd.system.operator.process import (
    ProcessInvocationError,
    ProcessResult,
)
from lychd.system.operator.storage import MountObservation, MountTreeObservation
from lychd.system.services.lifecycle import (
    BtrfsSubvolumeIdentity,
    CreatedBtrfsSubvolume,
    DeletionActionKind,
    DeletionCheckpointStore,
    DeletionDisposition,
    DeletionPaths,
    DeletionPlan,
    ObservedBtrfsSubvolume,
)
from lychd.system.services.lifecycle.deletion_storage import (
    CommandBtrfsSubvolumeProbe,
    DeletionStoragePlanner,
)

_SUBVOLUME_UUID = "12345678-1234-5678-1234-567812345678"
_OTHER_SUBVOLUME_UUID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
_FILESYSTEM_UUID = "87654321-4321-8765-4321-876543218765"


@dataclass
class _UnusedStorage:
    calls: int = 0

    def observe(self, target: Path) -> MountObservation:
        self.calls += 1
        return MountObservation(target=target, exists=False, mounted=False)

    def observe_under(self, roots: tuple[Path, ...]) -> MountTreeObservation:
        self.calls += 1
        return MountTreeObservation(roots=roots)


@dataclass
class _UnusedSubvolumes:
    calls: int = 0

    def inspect(self, path: Path) -> ObservedBtrfsSubvolume | None:
        del path
        self.calls += 1
        return None


@dataclass
class _NoInitializedSubvolumes:
    def created_subvolume(
        self,
        path: Path,
    ) -> CreatedBtrfsSubvolume | None:
        del path


@dataclass
class _InitializedSubvolumes:
    identity: CreatedBtrfsSubvolume | None
    calls: int = 0

    def created_subvolume(
        self,
        path: Path,
    ) -> CreatedBtrfsSubvolume | None:
        self.calls += 1
        if self.identity is None or self.identity.path != path:
            return None
        return self.identity


@dataclass
class _SubvolumeEvidence:
    target: Path
    observation: ObservedBtrfsSubvolume | None
    calls: int = 0

    def inspect(self, path: Path) -> ObservedBtrfsSubvolume | None:
        self.calls += 1
        return self.observation if path == self.target else None


@dataclass
class _UnmountedStorage:
    covering: MountObservation
    observe_calls: int = 0
    tree_calls: int = 0

    def observe(self, target: Path) -> MountObservation:
        assert target == self.covering.target
        self.observe_calls += 1
        return self.covering

    def observe_under(self, roots: tuple[Path, ...]) -> MountTreeObservation:
        self.tree_calls += 1
        return MountTreeObservation(roots=roots)


def _unmounted_paths(tmp_path: Path) -> DeletionPaths:
    codex = tmp_path / "codex"
    codex.mkdir()
    return DeletionPaths(
        codex_root=codex,
        crypt_root=tmp_path / "crypt",
        cache_root=tmp_path / "cache",
        postgres_data=tmp_path / "crypt" / "postgres" / "data",
        lifecycle_receipt=codex / ".lychd-lifecycle.json",
    )


def _created_subvolume(path: Path) -> CreatedBtrfsSubvolume:
    metadata = path.lstat()
    return CreatedBtrfsSubvolume(
        path=path,
        device=metadata.st_dev,
        inode=metadata.st_ino,
        subvolume_uuid=_SUBVOLUME_UUID,
        subvolume_id=259,
    )


def _unmounted_planner(
    tmp_path: Path,
    *,
    paths: DeletionPaths,
    authority: CreatedBtrfsSubvolume | None,
    observation: ObservedBtrfsSubvolume | None,
) -> tuple[
    DeletionStoragePlanner,
    _UnmountedStorage,
    _SubvolumeEvidence,
    _InitializedSubvolumes,
]:
    storage = _UnmountedStorage(
        MountObservation(
            target=paths.postgres_data,
            exists=paths.postgres_data.exists(),
            mounted=False,
            mount_target=tmp_path,
            source="/dev/test",
            source_device="/dev/test",
            filesystem="btrfs",
            filesystem_uuid=_FILESYSTEM_UUID,
            fs_root="/",
            subvolume_id=5,
            options=("rw", "subvolid=5", "subvol=/"),
            top_level_mount=tmp_path,
        )
    )
    subvolumes = _SubvolumeEvidence(paths.postgres_data, observation)
    initialized = _InitializedSubvolumes(authority)
    checkpoint = DeletionCheckpointStore(
        paths.codex_root / ".lychd-del-state.json",
        codex_root=paths.codex_root,
    )
    planner = DeletionStoragePlanner(
        paths=paths,
        storage=storage,
        subvolumes=subvolumes,
        initialized_subvolumes=initialized,
        checkpoint=checkpoint,
        umount_bin="/usr/bin/umount",
        btrfs_bin="/usr/bin/btrfs",
        sudo_bin="/usr/bin/sudo",
    )
    return planner, storage, subvolumes, initialized


def test_matched_init_created_unmounted_subvolume_requires_id_handoff(
    tmp_path: Path,
) -> None:
    paths = _unmounted_paths(tmp_path)
    paths.postgres_data.mkdir(parents=True)
    authority = _created_subvolume(paths.postgres_data)
    observed = ObservedBtrfsSubvolume(
        uuid=_SUBVOLUME_UUID,
        subvolume_id=259,
    )
    planner, storage, subvolumes, initialized = _unmounted_planner(
        tmp_path,
        paths=paths,
        authority=authority,
        observation=observed,
    )

    evidence = planner.plan()

    assert len(evidence.actions) == 1
    assert evidence.actions[0].disposition is DeletionDisposition.REQUIRES_ROOT
    assert evidence.actions[0].kind is DeletionActionKind.DELETE_SUBVOLUME
    assert evidence.identity is not None
    assert evidence.identity.source_path == paths.postgres_data
    assert evidence.identity.subvolume_uuid == _SUBVOLUME_UUID
    assert evidence.handoffs[0].argv[-3:] == (
        "--subvolid",
        "259",
        str(tmp_path),
    )
    assert storage.observe_calls == 1
    assert subvolumes.calls == 1
    assert initialized.calls == 1


def test_unmounted_subvolume_maps_covering_home_root_under_top_level_mount(
    tmp_path: Path,
) -> None:
    """A target under /home maps through /@home into the top-level Btrfs view."""
    home_mount = tmp_path / "home"
    top_level_mount = tmp_path / "mnt" / "btrfs"
    codex = tmp_path / "config" / "lychd"
    target = home_mount / "magus" / ".local" / "share" / "lychd" / "postgres" / "data"
    source_path = top_level_mount / "@home" / "magus" / ".local" / "share" / "lychd" / "postgres" / "data"
    codex.mkdir(parents=True)
    target.mkdir(parents=True)
    source_path.mkdir(parents=True)
    paths = DeletionPaths(
        codex_root=codex,
        crypt_root=home_mount / "magus" / ".local" / "share" / "lychd",
        cache_root=home_mount / "magus" / ".cache" / "lychd",
        postgres_data=target,
        lifecycle_receipt=codex / ".lychd-lifecycle.json",
    )
    authority = _created_subvolume(target)
    storage = _UnmountedStorage(
        MountObservation(
            target=target,
            exists=True,
            mounted=False,
            mount_target=home_mount,
            source="/dev/test[/@home]",
            source_device="/dev/test",
            filesystem="btrfs",
            filesystem_uuid=_FILESYSTEM_UUID,
            fs_root="/@home",
            subvolume_id=5,
            options=("rw", "subvolid=5", "subvol=/@home"),
            top_level_mount=top_level_mount,
        )
    )
    planner = DeletionStoragePlanner(
        paths=paths,
        storage=storage,
        subvolumes=_SubvolumeEvidence(
            target,
            ObservedBtrfsSubvolume(
                uuid=_SUBVOLUME_UUID,
                subvolume_id=259,
            ),
        ),
        initialized_subvolumes=_InitializedSubvolumes(authority),
        checkpoint=DeletionCheckpointStore(
            codex / ".lychd-del-state.json",
            codex_root=codex,
        ),
        umount_bin="/usr/bin/umount",
        btrfs_bin="/usr/bin/btrfs",
        sudo_bin="/usr/bin/sudo",
    )

    evidence = planner.plan()

    assert evidence.identity is not None
    assert evidence.identity.fs_root == "/@home/magus/.local/share/lychd/postgres/data"
    assert evidence.identity.source_path == source_path
    assert evidence.handoffs[0].argv[-1] == str(top_level_mount)
    assert evidence.actions[0].disposition is DeletionDisposition.REQUIRES_ROOT


def test_unreceipted_unmounted_subvolume_is_never_adopted(
    tmp_path: Path,
) -> None:
    paths = _unmounted_paths(tmp_path)
    paths.postgres_data.mkdir(parents=True)
    planner, storage, subvolumes, initialized = _unmounted_planner(
        tmp_path,
        paths=paths,
        authority=None,
        observation=ObservedBtrfsSubvolume(
            uuid=_SUBVOLUME_UUID,
            subvolume_id=259,
        ),
    )

    evidence = planner.plan()

    assert len(evidence.actions) == 1
    assert evidence.actions[0].disposition is DeletionDisposition.BLOCKED
    assert evidence.actions[0].kind is DeletionActionKind.VERIFY
    assert "lacks initialization receipt authority" in evidence.actions[0].detail
    assert evidence.identity is None
    assert evidence.handoffs == ()
    assert storage.observe_calls == 0
    assert subvolumes.calls == 1
    assert initialized.calls == 1


def test_init_created_unmounted_subvolume_identity_drift_blocks(
    tmp_path: Path,
) -> None:
    paths = _unmounted_paths(tmp_path)
    paths.postgres_data.mkdir(parents=True)
    authority = _created_subvolume(paths.postgres_data)
    planner, storage, subvolumes, initialized = _unmounted_planner(
        tmp_path,
        paths=paths,
        authority=authority,
        observation=ObservedBtrfsSubvolume(
            uuid=_OTHER_SUBVOLUME_UUID,
            subvolume_id=259,
        ),
    )

    evidence = planner.plan()

    assert len(evidence.actions) == 1
    assert evidence.actions[0].disposition is DeletionDisposition.BLOCKED
    assert "identity drifted" in evidence.actions[0].detail
    assert evidence.identity is None
    assert evidence.handoffs == ()
    assert storage.observe_calls == 0
    assert subvolumes.calls == 1
    assert initialized.calls == 1


def test_absent_init_created_subvolume_is_already_satisfied(
    tmp_path: Path,
) -> None:
    paths = _unmounted_paths(tmp_path)
    paths.postgres_data.mkdir(parents=True)
    authority = _created_subvolume(paths.postgres_data)
    paths.postgres_data.rmdir()
    planner, storage, subvolumes, initialized = _unmounted_planner(
        tmp_path,
        paths=paths,
        authority=authority,
        observation=None,
    )

    evidence = planner.plan()

    assert len(evidence.actions) == 1
    assert evidence.actions[0].disposition is DeletionDisposition.SATISFIED
    assert evidence.actions[0].kind is DeletionActionKind.DELETE_SUBVOLUME
    assert "init-created subvolume is absent" in evidence.actions[0].detail
    assert evidence.identity is None
    assert evidence.handoffs == ()
    assert storage.observe_calls == 0
    assert subvolumes.calls == 0
    assert initialized.calls == 1


def test_unreceipted_btrfs_boundary_blocks_when_probe_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed command probe cannot turn a possible subvolume into a directory."""
    paths = _unmounted_paths(tmp_path)
    paths.postgres_data.mkdir(parents=True)
    real_lstat = Path.lstat

    def boundary_lstat(path: Path) -> os.stat_result:
        result = real_lstat(path)
        if path == paths.postgres_data:
            values = list(result)
            values[stat.ST_INO] = 256
            return os.stat_result(values)
        return result

    monkeypatch.setattr(Path, "lstat", boundary_lstat)
    planner, storage, subvolumes, initialized = _unmounted_planner(
        tmp_path,
        paths=paths,
        authority=None,
        observation=None,
    )

    evidence = planner.plan()

    assert evidence.actions[0].disposition is DeletionDisposition.BLOCKED
    assert "possible Btrfs subvolume boundary" in evidence.actions[0].detail
    assert evidence.handoffs == ()
    assert storage.observe_calls == 1
    assert subvolumes.calls == 1
    assert initialized.calls == 1


def test_unreceipted_ordinary_btrfs_directory_remains_removable(
    tmp_path: Path,
) -> None:
    """A non-reserved inode on an attested Btrfs filesystem is not a subvolume."""
    paths = _unmounted_paths(tmp_path)
    paths.postgres_data.mkdir(parents=True)
    assert paths.postgres_data.lstat().st_ino not in {2, 256}
    planner, storage, subvolumes, initialized = _unmounted_planner(
        tmp_path,
        paths=paths,
        authority=None,
        observation=None,
    )

    evidence = planner.plan()

    assert evidence.actions[0].disposition is DeletionDisposition.SATISFIED
    assert "ordinary directory" in evidence.actions[0].detail
    assert storage.observe_calls == 1
    assert subvolumes.calls == 1
    assert initialized.calls == 1


def test_checkpoint_must_match_current_phylactery_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid old checkpoint cannot migrate deletion authority to another target."""
    codex = tmp_path / "codex"
    codex.mkdir()
    current_target = tmp_path / "crypt" / "postgres" / "data"
    paths = DeletionPaths(
        codex_root=codex,
        crypt_root=tmp_path / "crypt",
        cache_root=tmp_path / "cache",
        postgres_data=current_target,
        lifecycle_receipt=codex / ".lychd-lifecycle.json",
    )
    checkpoint = DeletionCheckpointStore(
        codex / ".lychd-del-state.json",
        codex_root=codex,
    )
    stale_identity = BtrfsSubvolumeIdentity(
        mount_target=tmp_path / "former-crypt" / "postgres" / "data",
        top_level_mount=tmp_path,
        source_device="/dev/test",
        filesystem_uuid="87654321-4321-8765-4321-876543218765",
        subvolume_uuid=_SUBVOLUME_UUID,
        fs_root="/@former-phylactery",
        source_path=tmp_path / "@former-phylactery",
        subvolume_id=259,
    )
    monkeypatch.setattr(checkpoint, "load", lambda: stale_identity)
    storage = _UnusedStorage()
    subvolumes = _UnusedSubvolumes()
    planner = DeletionStoragePlanner(
        paths=paths,
        storage=storage,
        subvolumes=subvolumes,
        initialized_subvolumes=_NoInitializedSubvolumes(),
        checkpoint=checkpoint,
        umount_bin="/usr/bin/umount",
        btrfs_bin="/usr/bin/btrfs",
        sudo_bin="/usr/bin/sudo",
    )

    evidence = planner.plan()

    assert len(evidence.actions) == 1
    assert evidence.actions[0].disposition is DeletionDisposition.BLOCKED
    assert "current Phylactery target" in evidence.actions[0].detail
    assert storage.calls == 0
    assert subvolumes.calls == 0


def test_checkpoint_and_plan_fingerprint_persist_subvolume_uuid(
    tmp_path: Path,
) -> None:
    codex = tmp_path / "codex"
    codex.mkdir()
    checkpoint = DeletionCheckpointStore(
        codex / ".lychd-del-state.json",
        codex_root=codex,
    )
    identity = BtrfsSubvolumeIdentity(
        mount_target=tmp_path / "crypt" / "postgres" / "data",
        top_level_mount=tmp_path,
        source_device="/dev/test",
        filesystem_uuid="87654321-4321-8765-4321-876543218765",
        subvolume_uuid=_SUBVOLUME_UUID.upper(),
        fs_root="/@phylactery",
        source_path=tmp_path / "@phylactery",
        subvolume_id=259,
    )

    checkpoint.record(identity)

    document = json.loads(checkpoint.path.read_text(encoding="utf-8"))
    assert document["version"] == 3
    assert document["identity"]["subvolume_uuid"] == _SUBVOLUME_UUID
    assert checkpoint.load() == identity
    changed_uuid = replace(identity, subvolume_uuid=_OTHER_SUBVOLUME_UUID)
    assert (
        DeletionPlan(actions=(), storage_identity=identity).fingerprint
        != DeletionPlan(
            actions=(),
            storage_identity=changed_uuid,
        ).fingerprint
    )


@dataclass
class _InvocationFailureRunner:
    calls: int = 0

    def run(
        self,
        argv: tuple[str, ...],
        *,
        timeout_s: float,
    ) -> ProcessResult:
        del argv, timeout_s
        self.calls += 1
        message = "simulated process failure"
        raise ProcessInvocationError(message)


def test_command_probe_converts_process_invocation_error_to_unverifiable(
    tmp_path: Path,
) -> None:
    runner = _InvocationFailureRunner()
    probe = CommandBtrfsSubvolumeProbe(
        runner,
        btrfs_bin="/usr/bin/btrfs",
    )

    assert probe.inspect(tmp_path / "phylactery") is None
    assert runner.calls == 1
