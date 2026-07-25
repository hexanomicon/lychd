"""Focused authority tests for resumable Phylactery deletion."""

from __future__ import annotations

import json
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
