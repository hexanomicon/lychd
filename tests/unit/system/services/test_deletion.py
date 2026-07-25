"""Focused safety evidence for the staged nuclear deletion lifecycle."""

from __future__ import annotations

import os
import stat
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import pytest

from lychd.system.operator.retirement import UnitRetirementPlan
from lychd.system.operator.storage import MountObservation, MountTreeObservation
from lychd.system.services.lifecycle import (
    DedicatedRootIdentity,
    DeletionActionKind,
    DeletionCheckpointStore,
    DeletionDisposition,
    DeletionExecutor,
    DeletionOutcome,
    DeletionPaths,
    DeletionPlanner,
    DeletionStage,
    LifecycleAction,
    LifecycleDisposition,
    LifecycleError,
    LifecyclePlan,
    LifecycleReceiptStore,
    LifecycleResourceKind,
    ManagedTreeService,
    ObservedBtrfsSubvolume,
)
from lychd.system.services.lifecycle.deletion import (
    BindingCleanupPort,
    BtrfsSubvolumeProbe,
    DedicatedRootAuthorityPort,
    ScribeOwnershipPort,
    StorageInventoryPort,
    UnitRetirementPort,
)
from lychd.system.services.scribe import OwnedBindings

_SUBVOLUME_UUID = "12345678-1234-5678-1234-567812345678"
_FILESYSTEM_UUID = "87654321-4321-8765-4321-876543218765"


def _fd_mount_id(descriptor: int) -> int:
    content = Path(f"/proc/self/fdinfo/{descriptor}").read_text(encoding="utf-8")
    return int(next(line.partition(":")[2].strip() for line in content.splitlines() if line.startswith("mnt_id:")))


def _root_identity(root: Path) -> DedicatedRootIdentity:
    metadata = root.lstat()
    return DedicatedRootIdentity(
        path=root,
        device=metadata.st_dev,
        inode=metadata.st_ino,
    )


@dataclass
class _Retirement:
    current: UnitRetirementPlan
    execute_calls: int = 0

    def plan(self) -> UnitRetirementPlan:
        return self.current

    def execute(self, plan: UnitRetirementPlan) -> None:
        assert plan == self.current
        self.execute_calls += 1
        self.current = UnitRetirementPlan(
            generation=plan.generation,
            owned_units=plan.owned_units,
            stop_units=(),
            disable_units=(),
        )

    def clear(self) -> None:
        self.current = UnitRetirementPlan(
            generation=None,
            owned_units=(),
            stop_units=(),
            disable_units=(),
        )


@dataclass
class _Scribe:
    ownership_path: Path
    owned: OwnedBindings

    def inspect_owned_bindings(self) -> OwnedBindings:
        return self.owned

    def clear(self) -> None:
        for path in (*self.owned.quadlet_sources, *self.owned.systemd_sources):
            path.unlink(missing_ok=True)
        self.ownership_path.unlink(missing_ok=True)
        self.owned = OwnedBindings(receipt_present=False)


@dataclass
class _Storage:
    observation: MountTreeObservation
    exact: dict[Path, MountObservation] = field(default_factory=dict)

    def observe(self, target: Path) -> MountObservation:
        return self.exact.get(
            target,
            MountObservation(
                target=target,
                exists=os.path.lexists(target),
                mounted=False,
            ),
        )

    def observe_under(self, roots: tuple[Path, ...]) -> MountTreeObservation:
        assert roots
        return self.observation


@dataclass
class _Subvolumes:
    identities: dict[Path, ObservedBtrfsSubvolume]

    def inspect(self, path: Path) -> ObservedBtrfsSubvolume | None:
        return self.identities.get(path)


@dataclass
class _Bindings:
    scribe: _Scribe
    retirement: _Retirement
    destroy_calls: int = 0

    def plan_destroy(self) -> LifecyclePlan:
        if not self.scribe.owned.receipt_present:
            return LifecyclePlan()
        return LifecyclePlan(
            actions=(
                LifecycleAction(
                    LifecycleDisposition.WOULD_REMOVE,
                    LifecycleResourceKind.RECEIPT,
                    str(self.scribe.ownership_path),
                    "exact fake Scribe receipt",
                ),
            )
        )

    def destroy(self) -> None:
        self.destroy_calls += 1
        self.scribe.clear()
        self.retirement.clear()


@dataclass
class _RootAuthority:
    path: Path
    identities: dict[Path, DedicatedRootIdentity]
    error: str | None = None

    def require_dedicated_root_identities(
        self,
        expected_roots: tuple[Path, ...],
    ) -> tuple[DedicatedRootIdentity, ...]:
        if self.error is not None:
            raise LifecycleError(self.error)
        if set(expected_roots) != set(self.identities):
            msg = "root authority does not match the exact requested set"
            raise LifecycleError(msg)
        result: list[DedicatedRootIdentity] = []
        for root in expected_roots:
            identity = self.identities[root]
            if root.exists():
                metadata = root.lstat()
                if metadata.st_dev != identity.device or metadata.st_ino != identity.inode:
                    msg = f"root identity drifted: {root}"
                    raise LifecycleError(msg)
            result.append(identity)
        return tuple(result)


@dataclass
class _Harness:
    paths: DeletionPaths
    retirement: _Retirement
    scribe: _Scribe
    storage: _Storage
    subvolumes: _Subvolumes
    bindings: _Bindings
    checkpoint: DeletionCheckpointStore
    trees: ManagedTreeService
    root_authority: _RootAuthority
    planner: DeletionPlanner
    executor: DeletionExecutor


def _build_harness(
    tmp_path: Path,
    *,
    active: bool = True,
    storage_observation: MountTreeObservation | None = None,
    subvolumes: dict[Path, ObservedBtrfsSubvolume] | None = None,
    sudo_bin: str | None = "/usr/bin/sudo",
) -> _Harness:
    config_home = tmp_path / "config"
    data_home = tmp_path / "data"
    cache_home = tmp_path / "cache"
    for root in (config_home, data_home, cache_home):
        root.mkdir()
    codex = config_home / "lychd"
    crypt = data_home / "lychd"
    cache = cache_home / "lychd"
    postgres_data = crypt / "postgres" / "data"
    for root in (codex, postgres_data, cache):
        root.mkdir(parents=True)
    (codex / "lychd.toml").write_text("generated = true\n", encoding="utf-8")
    (postgres_data / "PG_VERSION").write_text("17\n", encoding="utf-8")
    (cache / "assembly").mkdir()

    binding_root = config_home / "containers" / "systemd"
    binding_root.mkdir(parents=True)
    source = binding_root / "lychd-vessel.container"
    source.write_text("[Container]\n", encoding="utf-8")
    ownership = binding_root / ".lychd-owned.json"
    ownership.write_text("{}\n", encoding="utf-8")
    scribe = _Scribe(
        ownership_path=ownership,
        owned=OwnedBindings(
            receipt_present=True,
            generation="generation-1",
            quadlet_sources=(source,),
            runtime_units=("lychd-vessel.service",),
        ),
    )
    retirement = _Retirement(
        UnitRetirementPlan(
            generation="generation-1",
            owned_units=("lychd-vessel.service",),
            stop_units=("lychd-vessel.service",) if active else (),
            disable_units=("lychd-vessel.service",) if active else (),
        )
    )
    storage = _Storage(storage_observation or MountTreeObservation(roots=(codex, crypt, cache)))
    subvolume_probe = _Subvolumes(subvolumes or {})
    source_checkout = tmp_path / "source-checkout"
    paths = DeletionPaths(
        codex_root=codex,
        crypt_root=crypt,
        cache_root=cache,
        postgres_data=postgres_data,
        lifecycle_receipt=codex / ".lychd-lifecycle.json",
        source_checkout=source_checkout,
    )
    paths.lifecycle_receipt.write_text(
        ('{"version":1,"dedicated_roots":[],"directories":[],"files":[]}\n'),
        encoding="utf-8",
    )
    paths.lifecycle_receipt.chmod(0o600)
    source_checkout.mkdir()
    checkpoint = DeletionCheckpointStore(
        codex / ".lychd-del-state.json",
        codex_root=codex,
    )
    trees = ManagedTreeService(paths.dedicated_roots)
    root_authority = _RootAuthority(
        path=paths.lifecycle_receipt,
        identities={
            root: DedicatedRootIdentity(
                path=root,
                device=root.lstat().st_dev,
                inode=root.lstat().st_ino,
            )
            for root in paths.dedicated_roots
        },
    )
    planner = DeletionPlanner(
        paths=paths,
        retirement=cast("UnitRetirementPort", retirement),
        scribe=cast("ScribeOwnershipPort", scribe),
        storage=cast("StorageInventoryPort", storage),
        subvolumes=cast("BtrfsSubvolumeProbe", subvolume_probe),
        checkpoint=checkpoint,
        trees=trees,
        root_authority=root_authority,
        umount_bin="/usr/bin/umount",
        btrfs_bin="/usr/bin/btrfs",
        sudo_bin=sudo_bin,
    )
    bindings = _Bindings(scribe=scribe, retirement=retirement)
    executor = DeletionExecutor(
        planner=planner,
        retirement=cast("UnitRetirementPort", retirement),
        bindings=cast("BindingCleanupPort", bindings),
        checkpoint=checkpoint,
        trees=trees,
        lock_factory=lambda: nullcontext(),
    )
    return _Harness(
        paths=paths,
        retirement=retirement,
        scribe=scribe,
        storage=storage,
        subvolumes=subvolume_probe,
        bindings=bindings,
        checkpoint=checkpoint,
        trees=trees,
        root_authority=root_authority,
        planner=planner,
        executor=executor,
    )


def _wire_root_authority(
    harness: _Harness,
    root_authority: DedicatedRootAuthorityPort,
) -> tuple[DeletionPlanner, DeletionExecutor]:
    planner = DeletionPlanner(
        paths=harness.paths,
        retirement=cast("UnitRetirementPort", harness.retirement),
        scribe=cast("ScribeOwnershipPort", harness.scribe),
        storage=cast("StorageInventoryPort", harness.storage),
        subvolumes=cast("BtrfsSubvolumeProbe", harness.subvolumes),
        checkpoint=harness.checkpoint,
        trees=harness.trees,
        root_authority=root_authority,
        umount_bin="/usr/bin/umount",
        btrfs_bin="/usr/bin/btrfs",
        sudo_bin="/usr/bin/sudo",
    )
    executor = DeletionExecutor(
        planner=planner,
        retirement=cast("UnitRetirementPort", harness.retirement),
        bindings=cast("BindingCleanupPort", harness.bindings),
        checkpoint=harness.checkpoint,
        trees=harness.trees,
        lock_factory=lambda: nullcontext(),
    )
    return planner, executor


def _patch_receipt_authority(
    monkeypatch: pytest.MonkeyPatch,
    harness: _Harness,
) -> None:
    from lychd.system.services import lifecycle as lifecycle_facade

    for name, value in {
        "PATH_CODEX_ROOT": harness.paths.codex_root,
        "PATH_CRYPT_ROOT": harness.paths.crypt_root,
        "PATH_CACHE_ROOT": harness.paths.cache_root,
        "PATH_LIFECYCLE_RECEIPT": harness.paths.lifecycle_receipt,
    }.items():
        monkeypatch.setattr(lifecycle_facade, name, value)


def _tree_snapshot(root: Path) -> tuple[tuple[str, str], ...]:
    return tuple(
        (str(path.relative_to(root)), "symlink" if path.is_symlink() else "path") for path in sorted(root.rglob("*"))
    )


def test_plan_is_effect_free_and_preserves_unreceipted_external_resources(
    tmp_path: Path,
) -> None:
    harness = _build_harness(tmp_path)
    before = _tree_snapshot(tmp_path)

    plan = harness.planner.plan()

    assert _tree_snapshot(tmp_path) == before
    assert not harness.checkpoint.exists
    assert harness.retirement.execute_calls == 0
    assert harness.bindings.destroy_calls == 0
    preserved = {action.kind for action in plan.actions if action.disposition is DeletionDisposition.PRESERVE}
    assert DeletionActionKind.PRESERVE_RUNTIME in preserved
    assert DeletionActionKind.PRESERVE_SECRET in preserved
    assert DeletionActionKind.PRESERVE_PACKAGE in preserved


def test_successful_init_root_seal_authorizes_complete_deletion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real lifecycle receipt bridges explicit init into recursive del authority."""
    harness = _build_harness(tmp_path, active=False)
    _patch_receipt_authority(monkeypatch, harness)
    root_authority = LifecycleReceiptStore(harness.paths.lifecycle_receipt)
    root_authority.seal_dedicated_roots()
    planner, executor = _wire_root_authority(harness, root_authority)

    plan = planner.plan()
    result = executor.execute(plan.fingerprint)

    assert not any(
        action.kind is DeletionActionKind.VERIFY_ROOT_AUTHORITY and action.disposition is DeletionDisposition.BLOCKED
        for action in plan.actions
    )
    assert result.outcome is DeletionOutcome.COMPLETE
    assert harness.bindings.destroy_calls == 1
    assert all(not root.exists() for root in harness.paths.dedicated_roots)
    assert harness.paths.source_checkout is not None
    assert harness.paths.source_checkout.exists()


def test_late_codex_removal_failure_retains_receipt_for_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Codex authority is consumed only after every sibling is removed."""
    harness = _build_harness(tmp_path, active=False)
    _patch_receipt_authority(monkeypatch, harness)
    root_authority = LifecycleReceiptStore(harness.paths.lifecycle_receipt)
    root_authority.seal_dedicated_roots()
    planner, executor = _wire_root_authority(harness, root_authority)
    late_entry = harness.paths.codex_root / "late-failure"
    late_entry.write_text("retry me", encoding="utf-8")
    real_unlink = os.unlink
    failed_once = False

    def fail_one_codex_unlink(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal failed_once
        if path == late_entry.name and dir_fd is not None and not failed_once:
            failed_once = True
            message = "simulated late Codex removal failure"
            raise OSError(message)
        real_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(
        "lychd.system.services.lifecycle.trees.os.unlink",
        fail_one_codex_unlink,
    )

    first_plan = planner.plan()
    first = executor.execute(first_plan.fingerprint)

    assert first.outcome is DeletionOutcome.PARTIAL
    assert late_entry.exists()
    assert harness.paths.lifecycle_receipt.exists()

    retry_plan = planner.plan()
    retried = executor.execute(retry_plan.fingerprint)

    assert retried.outcome is DeletionOutcome.COMPLETE
    assert not harness.paths.codex_root.exists()


@pytest.mark.parametrize(
    "receipt_content",
    [
        None,
        "not-json",
    ],
)
def test_missing_or_corrupt_root_authority_blocks_before_unbind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt_content: str | None,
) -> None:
    """Recursive removal needs a valid explicit-init seal, not known geography."""
    harness = _build_harness(tmp_path, active=False)
    _patch_receipt_authority(monkeypatch, harness)
    if receipt_content is None:
        harness.paths.lifecycle_receipt.unlink()
    else:
        harness.paths.lifecycle_receipt.write_text(receipt_content, encoding="utf-8")
        harness.paths.lifecycle_receipt.chmod(0o600)
    root_authority = LifecycleReceiptStore(harness.paths.lifecycle_receipt)
    planner, executor = _wire_root_authority(harness, root_authority)

    plan = planner.plan()
    result = executor.execute(plan.fingerprint)

    assert any(
        action.kind is DeletionActionKind.VERIFY_ROOT_AUTHORITY and action.disposition is DeletionDisposition.BLOCKED
        for action in plan.actions
    )
    assert result.outcome is DeletionOutcome.BLOCKED
    assert harness.bindings.destroy_calls == 0
    assert harness.scribe.ownership_path.exists()
    assert all(root.exists() for root in harness.paths.dedicated_roots)


def test_root_authority_identity_drift_blocks_before_unbind(tmp_path: Path) -> None:
    """A same-path replacement does not inherit recursive deletion authority."""
    harness = _build_harness(tmp_path, active=False)
    cache = harness.paths.cache_root
    original = cache.with_name("lychd-cache-original")
    cache.rename(original)
    cache.mkdir()
    sentinel = cache / "foreign"
    sentinel.write_text("preserve", encoding="utf-8")

    plan = harness.planner.plan()
    result = harness.executor.execute(plan.fingerprint)

    assert any(
        action.kind is DeletionActionKind.VERIFY_ROOT_AUTHORITY
        and action.disposition is DeletionDisposition.BLOCKED
        and "drifted" in action.detail
        for action in plan.actions
    )
    assert result.outcome is DeletionOutcome.BLOCKED
    assert harness.bindings.destroy_calls == 0
    assert sentinel.read_text(encoding="utf-8") == "preserve"


def test_executor_rejects_plan_drift_before_any_effect(tmp_path: Path) -> None:
    harness = _build_harness(tmp_path)
    approved = harness.planner.plan()
    harness.retirement.current = UnitRetirementPlan(
        generation="generation-1",
        owned_units=("lychd-vessel.service",),
        stop_units=(),
        disable_units=("lychd-vessel.service",),
    )

    with pytest.raises(LifecycleError, match="changed after confirmation"):
        harness.executor.execute(approved.fingerprint)

    assert harness.retirement.execute_calls == 0
    assert harness.bindings.destroy_calls == 0
    assert harness.paths.codex_root.exists()


def test_symlinked_dedicated_root_blocks_before_unbind_and_preserves_target(
    tmp_path: Path,
) -> None:
    harness = _build_harness(tmp_path, active=False)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "keep"
    sentinel.write_text("operator data", encoding="utf-8")
    crypt = harness.paths.crypt_root
    for path in sorted(crypt.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
        else:
            path.rmdir()
    crypt.rmdir()
    crypt.symlink_to(outside, target_is_directory=True)

    plan = harness.planner.plan()
    result = harness.executor.execute(plan.fingerprint)

    assert result.outcome is DeletionOutcome.BLOCKED
    assert harness.bindings.destroy_calls == 0
    assert harness.scribe.ownership_path.exists()
    assert sentinel.read_text(encoding="utf-8") == "operator data"


def test_unknown_nested_mount_is_a_true_storage_blocker(tmp_path: Path) -> None:
    harness = _build_harness(tmp_path, active=False)
    unknown_target = harness.paths.crypt_root / "operator-mount"
    unknown_target.mkdir()
    harness.storage.observation = MountTreeObservation(
        roots=harness.paths.dedicated_roots,
        mounts=(
            MountObservation(
                target=unknown_target,
                exists=True,
                mounted=True,
                mount_target=unknown_target,
                source="/dev/other",
                source_device="/dev/other",
                filesystem="ext4",
                fs_root="/",
            ),
        ),
    )

    plan = harness.planner.plan()
    result = harness.executor.execute(plan.fingerprint)

    assert any(
        action.stage.value == "storage" and action.disposition is DeletionDisposition.BLOCKED for action in plan.actions
    )
    assert result.outcome is DeletionOutcome.BLOCKED
    assert harness.bindings.destroy_calls == 0


def test_attested_btrfs_handoff_retires_units_and_retains_evidence(
    tmp_path: Path,
) -> None:
    harness = _build_harness(tmp_path)
    top_level = tmp_path / "btrfs-top"
    source_path = top_level / "@phylactery"
    source_path.mkdir(parents=True)
    mount = MountObservation(
        target=harness.paths.postgres_data,
        exists=True,
        mounted=True,
        mount_target=harness.paths.postgres_data,
        source="/dev/nvme0n1p3[/@phylactery]",
        source_device="/dev/nvme0n1p3",
        filesystem="btrfs",
        filesystem_uuid=_FILESYSTEM_UUID,
        fs_root="/@phylactery",
        subvolume_id=259,
        options=("rw", "subvolid=259", "subvol=/@phylactery"),
        top_level_mount=top_level,
    )
    harness.storage.observation = MountTreeObservation(
        roots=harness.paths.dedicated_roots,
        mounts=(mount,),
    )
    harness.subvolumes.identities[harness.paths.postgres_data] = ObservedBtrfsSubvolume(
        uuid=_SUBVOLUME_UUID, subvolume_id=259
    )
    plan = harness.planner.plan()
    result = harness.executor.execute(plan.fingerprint)

    assert plan.requires_root
    assert [action.kind for action in plan.actions_for(DeletionStage.STORAGE)] == [
        DeletionActionKind.UNMOUNT,
        DeletionActionKind.DELETE_SUBVOLUME,
    ]
    assert not any(
        action.stage.value == "filesystem" and action.disposition is DeletionDisposition.BLOCKED
        for action in plan.actions
    )
    assert result.outcome is DeletionOutcome.PARTIAL
    assert harness.retirement.execute_calls == 1
    assert harness.bindings.destroy_calls == 0
    assert harness.checkpoint.exists
    assert harness.checkpoint.path.stat().st_mode & 0o777 == 0o600
    assert harness.checkpoint.load() == plan.storage_identity
    assert harness.scribe.ownership_path.exists()
    assert harness.paths.codex_root.exists()
    assert all(handoff.argv[0] == "/usr/bin/sudo" for handoff in result.plan.handoffs)
    assert any(handoff.argv[-3:] == ("--subvolid", "259", str(top_level)) for handoff in result.plan.handoffs)


def test_exact_btrfs_mount_blocks_when_subvolume_probe_is_unavailable(
    tmp_path: Path,
) -> None:
    harness = _build_harness(tmp_path)
    top_level = tmp_path / "btrfs-top"
    (top_level / "@phylactery").mkdir(parents=True)
    harness.storage.observation = MountTreeObservation(
        roots=harness.paths.dedicated_roots,
        mounts=(
            MountObservation(
                target=harness.paths.postgres_data,
                exists=True,
                mounted=True,
                mount_target=harness.paths.postgres_data,
                source="/dev/nvme0n1p3[/@phylactery]",
                source_device="/dev/nvme0n1p3",
                filesystem="btrfs",
                filesystem_uuid=_FILESYSTEM_UUID,
                fs_root="/@phylactery",
                subvolume_id=259,
                options=("rw", "subvolid=259", "subvol=/@phylactery"),
                top_level_mount=top_level,
            ),
        ),
    )

    plan = harness.planner.plan()

    assert any(
        action.disposition is DeletionDisposition.BLOCKED and "could not attest" in action.detail
        for action in plan.actions_for(DeletionStage.STORAGE)
    )
    assert plan.handoffs == ()


def test_privileged_handoff_blocks_without_trusted_absolute_sudo(
    tmp_path: Path,
) -> None:
    harness = _build_harness(tmp_path, sudo_bin=None)
    top_level = tmp_path / "btrfs-top"
    (top_level / "@phylactery").mkdir(parents=True)
    harness.storage.observation = MountTreeObservation(
        roots=harness.paths.dedicated_roots,
        mounts=(
            MountObservation(
                target=harness.paths.postgres_data,
                exists=True,
                mounted=True,
                mount_target=harness.paths.postgres_data,
                source="/dev/nvme0n1p3[/@phylactery]",
                source_device="/dev/nvme0n1p3",
                filesystem="btrfs",
                filesystem_uuid=_FILESYSTEM_UUID,
                fs_root="/@phylactery",
                subvolume_id=259,
                options=("rw", "subvolid=259", "subvol=/@phylactery"),
                top_level_mount=top_level,
            ),
        ),
    )
    harness.subvolumes.identities[harness.paths.postgres_data] = ObservedBtrfsSubvolume(
        uuid=_SUBVOLUME_UUID, subvolume_id=259
    )

    plan = harness.planner.plan()

    assert any(
        action.disposition is DeletionDisposition.BLOCKED and "trusted sudo" in action.detail
        for action in plan.actions_for(DeletionStage.STORAGE)
    )
    assert plan.handoffs == ()


def test_known_blocker_suppresses_root_handoff_and_every_effect(
    tmp_path: Path,
) -> None:
    """A plan that cannot complete never invites or applies an earlier deletion."""
    harness = _build_harness(tmp_path)
    top_level = tmp_path / "btrfs-top"
    (top_level / "@phylactery").mkdir(parents=True)
    harness.storage.observation = MountTreeObservation(
        roots=harness.paths.dedicated_roots,
        mounts=(
            MountObservation(
                target=harness.paths.postgres_data,
                exists=True,
                mounted=True,
                mount_target=harness.paths.postgres_data,
                source="/dev/nvme0n1p3[/@phylactery]",
                source_device="/dev/nvme0n1p3",
                filesystem="btrfs",
                filesystem_uuid=_FILESYSTEM_UUID,
                fs_root="/@phylactery",
                subvolume_id=259,
                options=("rw", "subvolid=259", "subvol=/@phylactery"),
                top_level_mount=top_level,
            ),
        ),
    )
    harness.subvolumes.identities[harness.paths.postgres_data] = ObservedBtrfsSubvolume(
        uuid=_SUBVOLUME_UUID, subvolume_id=259
    )
    harness.root_authority.error = "missing initialization authority"

    plan = harness.planner.plan()
    result = harness.executor.execute(plan.fingerprint)

    assert plan.requires_root
    assert plan.first_blocked_stage is DeletionStage.FILESYSTEM
    assert plan.handoffs == ()
    assert result.outcome is DeletionOutcome.BLOCKED
    assert result.applied_stages == ()
    assert harness.retirement.execute_calls == 0
    assert harness.bindings.destroy_calls == 0
    assert not harness.checkpoint.exists


def test_root_handoff_resume_completes_then_reruns_idempotently(
    tmp_path: Path,
) -> None:
    harness = _build_harness(tmp_path)
    top_level = tmp_path / "btrfs-top"
    source_path = top_level / "@phylactery"
    source_path.mkdir(parents=True)
    harness.storage.observation = MountTreeObservation(
        roots=harness.paths.dedicated_roots,
        mounts=(
            MountObservation(
                target=harness.paths.postgres_data,
                exists=True,
                mounted=True,
                mount_target=harness.paths.postgres_data,
                source="/dev/nvme0n1p3[/@phylactery]",
                source_device="/dev/nvme0n1p3",
                filesystem="btrfs",
                filesystem_uuid=_FILESYSTEM_UUID,
                fs_root="/@phylactery",
                subvolume_id=259,
                options=("rw", "subvolid=259", "subvol=/@phylactery"),
                top_level_mount=top_level,
            ),
        ),
    )
    harness.subvolumes.identities[harness.paths.postgres_data] = ObservedBtrfsSubvolume(
        uuid=_SUBVOLUME_UUID, subvolume_id=259
    )
    first = harness.planner.plan()
    paused = harness.executor.execute(first.fingerprint)
    assert paused.outcome is DeletionOutcome.PARTIAL

    # Simulate the exact commands printed for the operator; LychD never runs them.
    harness.storage.observation = MountTreeObservation(
        roots=harness.paths.dedicated_roots,
    )
    harness.storage.exact[top_level] = MountObservation(
        target=top_level,
        exists=True,
        mounted=True,
        mount_target=top_level,
        source="/dev/nvme0n1p3",
        source_device="/dev/nvme0n1p3",
        filesystem="btrfs",
        filesystem_uuid=_FILESYSTEM_UUID,
        fs_root="/",
        subvolume_id=5,
        options=("rw", "subvolid=5", "subvol=/"),
        top_level_mount=top_level,
    )
    source_path.rmdir()
    harness.subvolumes.identities.clear()

    resumed_plan = harness.planner.plan()
    completed = harness.executor.execute(resumed_plan.fingerprint)

    assert completed.outcome is DeletionOutcome.COMPLETE
    assert harness.bindings.destroy_calls == 1
    assert not harness.paths.codex_root.exists()
    assert not harness.paths.crypt_root.exists()
    assert not harness.paths.cache_root.exists()
    assert harness.paths.source_checkout is not None
    assert harness.paths.source_checkout.exists()

    rerun_plan = harness.planner.plan()
    rerun = harness.executor.execute(rerun_plan.fingerprint)
    assert rerun.outcome is DeletionOutcome.COMPLETE
    assert harness.bindings.destroy_calls == 1
    assert harness.paths.source_checkout.exists()


def test_checkpoint_resume_blocks_on_top_level_filesystem_drift(
    tmp_path: Path,
) -> None:
    harness = _build_harness(tmp_path)
    top_level = tmp_path / "btrfs-top"
    source_path = top_level / "@phylactery"
    source_path.mkdir(parents=True)
    harness.storage.observation = MountTreeObservation(
        roots=harness.paths.dedicated_roots,
        mounts=(
            MountObservation(
                target=harness.paths.postgres_data,
                exists=True,
                mounted=True,
                mount_target=harness.paths.postgres_data,
                source="/dev/nvme0n1p3[/@phylactery]",
                source_device="/dev/nvme0n1p3",
                filesystem="btrfs",
                filesystem_uuid=_FILESYSTEM_UUID,
                fs_root="/@phylactery",
                subvolume_id=259,
                options=("rw", "subvolid=259", "subvol=/@phylactery"),
                top_level_mount=top_level,
            ),
        ),
    )
    harness.subvolumes.identities[harness.paths.postgres_data] = ObservedBtrfsSubvolume(
        uuid=_SUBVOLUME_UUID, subvolume_id=259
    )
    first = harness.planner.plan()
    assert harness.executor.execute(first.fingerprint).outcome is DeletionOutcome.PARTIAL

    harness.storage.observation = MountTreeObservation(
        roots=harness.paths.dedicated_roots,
    )
    harness.storage.exact[top_level] = MountObservation(
        target=top_level,
        exists=True,
        mounted=True,
        mount_target=top_level,
        source="/dev/nvme0n1p3",
        source_device="/dev/nvme0n1p3",
        filesystem="btrfs",
        filesystem_uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        fs_root="/",
        subvolume_id=5,
        options=("rw", "subvolid=5", "subvol=/"),
        top_level_mount=top_level,
    )

    drifted = harness.planner.plan()
    result = harness.executor.execute(drifted.fingerprint)

    assert result.outcome is DeletionOutcome.BLOCKED
    assert not drifted.handoffs
    assert harness.bindings.destroy_calls == 0
    assert harness.checkpoint.exists
    assert harness.paths.codex_root.exists()


def test_checkpoint_resume_blocks_same_id_with_different_subvolume_uuid(
    tmp_path: Path,
) -> None:
    harness = _build_harness(tmp_path)
    top_level = tmp_path / "btrfs-top"
    source_path = top_level / "@phylactery"
    source_path.mkdir(parents=True)
    harness.storage.observation = MountTreeObservation(
        roots=harness.paths.dedicated_roots,
        mounts=(
            MountObservation(
                target=harness.paths.postgres_data,
                exists=True,
                mounted=True,
                mount_target=harness.paths.postgres_data,
                source="/dev/nvme0n1p3[/@phylactery]",
                source_device="/dev/nvme0n1p3",
                filesystem="btrfs",
                filesystem_uuid=_FILESYSTEM_UUID,
                fs_root="/@phylactery",
                subvolume_id=259,
                options=("rw", "subvolid=259", "subvol=/@phylactery"),
                top_level_mount=top_level,
            ),
        ),
    )
    harness.subvolumes.identities[harness.paths.postgres_data] = ObservedBtrfsSubvolume(
        uuid=_SUBVOLUME_UUID, subvolume_id=259
    )
    first = harness.planner.plan()
    assert harness.executor.execute(first.fingerprint).outcome is DeletionOutcome.PARTIAL

    harness.storage.observation = MountTreeObservation(
        roots=harness.paths.dedicated_roots,
    )
    harness.storage.exact[top_level] = MountObservation(
        target=top_level,
        exists=True,
        mounted=True,
        mount_target=top_level,
        source="/dev/nvme0n1p3",
        source_device="/dev/nvme0n1p3",
        filesystem="btrfs",
        filesystem_uuid=_FILESYSTEM_UUID,
        fs_root="/",
        subvolume_id=5,
        options=("rw", "subvolid=5", "subvol=/"),
        top_level_mount=top_level,
    )
    harness.subvolumes.identities.clear()

    unavailable = harness.planner.plan()

    assert any(
        action.disposition is DeletionDisposition.BLOCKED and "cannot re-attest" in action.detail
        for action in unavailable.actions_for(DeletionStage.STORAGE)
    )
    assert unavailable.handoffs == ()

    harness.subvolumes.identities[source_path] = ObservedBtrfsSubvolume(
        uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        subvolume_id=259,
    )

    resumed = harness.planner.plan()

    assert any(
        action.disposition is DeletionDisposition.BLOCKED and "different subvolume UUID or ID" in action.detail
        for action in resumed.actions_for(DeletionStage.STORAGE)
    )
    assert resumed.handoffs == ()
    assert harness.checkpoint.exists


def test_final_root_identity_replacement_is_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "codex"
    root.mkdir()
    service = ManagedTreeService((root,))
    real_stat = os.stat

    def replacement_stat(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes] | int,
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        result = real_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        if path == root.name and dir_fd is not None and follow_symlinks is False:
            values = list(result)
            values[stat.ST_INO] = result.st_ino + 1
            return os.stat_result(values)
        return result

    monkeypatch.setattr(
        "lychd.system.services.lifecycle.trees.os.stat",
        replacement_stat,
    )

    with pytest.raises(LifecycleError, match="identity changed"):
        service.remove(root, expected_identity=_root_identity(root))

    assert root.exists()


def test_nested_directory_identity_replacement_is_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "codex"
    nested = root / "managed"
    nested.mkdir(parents=True)
    service = ManagedTreeService((root,))
    real_stat = os.stat

    def replacement_stat(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes] | int,
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        result = real_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        if path == nested.name and dir_fd is not None and follow_symlinks is False:
            values = list(result)
            values[stat.ST_INO] = result.st_ino + 1
            return os.stat_result(values)
        return result

    monkeypatch.setattr(
        "lychd.system.services.lifecycle.trees.os.stat",
        replacement_stat,
    )

    with pytest.raises(LifecycleError, match="identity changed"):
        service.remove(root, expected_identity=_root_identity(root))

    assert nested.exists()
    assert root.exists()


def test_root_replacement_between_stat_and_descriptor_open_is_preserved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "codex"
    original = tmp_path / "codex-original"
    replacement = tmp_path / "codex-replacement"
    root.mkdir()
    replacement.mkdir()
    original_sentinel = root / "keep-original"
    replacement_sentinel = replacement / "keep-replacement"
    original_sentinel.write_text("original", encoding="utf-8")
    replacement_sentinel.write_text("replacement", encoding="utf-8")
    service = ManagedTreeService((root,))
    real_open = os.open
    swapped = False

    def racing_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        if path == root.name and dir_fd is not None and not swapped:
            root.rename(original)
            replacement.rename(root)
            swapped = True
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(
        "lychd.system.services.lifecycle.trees.os.open",
        racing_open,
    )

    with pytest.raises(LifecycleError, match="identity changed before deletion"):
        service.remove(root, expected_identity=_root_identity(root))

    assert (original / original_sentinel.name).read_text(encoding="utf-8") == ("original")
    assert (root / replacement_sentinel.name).read_text(encoding="utf-8") == ("replacement")


def test_root_mount_id_change_blocks_before_contents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "codex"
    root.mkdir()
    sentinel = root / "keep"
    sentinel.write_text("operator data", encoding="utf-8")
    service = ManagedTreeService((root,))

    def changed_root_mount_id(descriptor: int) -> int:
        observed = _fd_mount_id(descriptor)
        opened_path = Path(f"/proc/self/fd/{descriptor}").readlink()
        return observed + 1 if opened_path == root else observed

    monkeypatch.setattr(
        "lychd.system.services.lifecycle.trees._mount_id_for_fd",
        changed_root_mount_id,
    )

    with pytest.raises(LifecycleError, match="became a mount boundary"):
        service.remove(root, expected_identity=_root_identity(root))

    assert sentinel.read_text(encoding="utf-8") == "operator data"


def test_same_device_nested_bind_mount_id_blocks_before_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "codex"
    nested = root / "mounted"
    nested.mkdir(parents=True)
    sentinel = nested / "keep"
    sentinel.write_text("operator data", encoding="utf-8")
    service = ManagedTreeService((root,))

    def changed_nested_mount_id(descriptor: int) -> int:
        observed = _fd_mount_id(descriptor)
        opened_path = Path(f"/proc/self/fd/{descriptor}").readlink()
        return observed + 1 if opened_path == nested else observed

    monkeypatch.setattr(
        "lychd.system.services.lifecycle.trees._mount_id_for_fd",
        changed_nested_mount_id,
    )

    with pytest.raises(LifecycleError, match="Mount boundary appeared"):
        service.remove(root, expected_identity=_root_identity(root))

    assert sentinel.read_text(encoding="utf-8") == "operator data"


def test_same_device_file_bind_mount_id_blocks_before_unlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "codex"
    root.mkdir()
    mounted_file = root / "mounted-file"
    mounted_file.write_text("operator data", encoding="utf-8")
    service = ManagedTreeService((root,))

    def changed_file_mount_id(descriptor: int) -> int:
        observed = _fd_mount_id(descriptor)
        opened_path = Path(f"/proc/self/fd/{descriptor}").readlink()
        return observed + 1 if opened_path == mounted_file else observed

    monkeypatch.setattr(
        "lychd.system.services.lifecycle.trees._mount_id_for_fd",
        changed_file_mount_id,
    )

    with pytest.raises(LifecycleError, match="Mount boundary appeared"):
        service.remove(root, expected_identity=_root_identity(root))

    assert mounted_file.read_text(encoding="utf-8") == "operator data"


def test_unreadable_mount_identity_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "codex"
    root.mkdir()
    sentinel = root / "keep"
    sentinel.write_text("operator data", encoding="utf-8")
    service = ManagedTreeService((root,))

    def unavailable_mount_id(_descriptor: int) -> int:
        msg = "simulated unreadable mount identity"
        raise LifecycleError(msg)

    monkeypatch.setattr(
        "lychd.system.services.lifecycle.trees._mount_id_for_fd",
        unavailable_mount_id,
    )

    with pytest.raises(LifecycleError, match="unreadable mount identity"):
        service.remove(root, expected_identity=_root_identity(root))

    assert sentinel.read_text(encoding="utf-8") == "operator data"
