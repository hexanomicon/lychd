"""Focused safety evidence for the staged nuclear deletion lifecycle."""

from __future__ import annotations

import errno
import os
import stat
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import pytest

from lychd.system import (
    protected_retirement as protected_retirement_module,
)
from lychd.system import (
    protected_retirement_recovery as protected_retirement_recovery_module,
)
from lychd.system.atomic_paths import rename_noreplace_at
from lychd.system.atomic_retirement import (
    AtomicRetirementError,
    AtomicRetirementService,
    RetirementIdentity,
    is_retirement_quarantine_name,
)
from lychd.system.descriptor_settlement import find_settlement_outcome
from lychd.system.interruptions import iter_exception_graph
from lychd.system.operator.retirement import UnitRetirementPlan
from lychd.system.operator.storage import MountObservation, MountTreeObservation
from lychd.system.protected_retirement import ProtectedRootRetirementService
from lychd.system.protected_retirement_models import (
    ProtectedRetirementEntry,
    ProtectedRootRetirementError,
)
from lychd.system.protected_retirement_naming import (
    is_protected_authority_name,
    new_protected_authority_name,
)
from lychd.system.services.lifecycle import (
    CreatedBtrfsSubvolume,
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
from lychd.system.services.lifecycle.trees import ManagedTreeSettlementError
from lychd.system.services.scribe import (
    OwnedBindings,
    ScribeTransactionError,
    ScribeTransactionState,
)

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


def _retirement_identity(path: Path) -> RetirementIdentity:
    return RetirementIdentity.from_stat(path.lstat())


class _ProtectedDetachProbe(ProtectedRootRetirementService):
    """Expose only root detachment for focused state-machine tests."""

    def detach(
        self,
        *,
        parent_fd: int,
        leaf: str,
        expected: RetirementIdentity,
        display_path: Path,
    ) -> str:
        return self._detach_root(
            parent_fd=parent_fd,
            leaf=leaf,
            expected=expected,
            display_path=display_path,
        )


def test_protected_authority_producer_matches_recovery_recognizer() -> None:
    name = new_protected_authority_name()

    assert is_protected_authority_name(name)


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
                filesystem="ext4",
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
    subvolume: CreatedBtrfsSubvolume | None = None

    def created_subvolume(
        self,
        path: Path,
    ) -> CreatedBtrfsSubvolume | None:
        if self.subvolume is None or self.subvolume.path != path:
            return None
        return self.subvolume

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
    late_inode = late_entry.lstat().st_ino
    real_unlink = os.unlink
    failed_once = False

    def fail_one_codex_unlink(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal failed_once
        metadata = os.stat(path, dir_fd=dir_fd, follow_symlinks=False) if dir_fd is not None else None
        if metadata is not None and metadata.st_ino == late_inode and not failed_once:
            failed_once = True
            message = "simulated late Codex removal failure"
            raise OSError(message)
        real_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(
        "lychd.system.atomic_retirement.os.unlink",
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


def test_init_receipted_unmounted_subvolume_pauses_before_generic_tree_removal(
    tmp_path: Path,
) -> None:
    """The joined plan defers a typed subvolume to the ID-bound storage handoff."""
    harness = _build_harness(tmp_path, active=False)
    target = harness.paths.postgres_data
    metadata = target.lstat()
    harness.root_authority.subvolume = CreatedBtrfsSubvolume(
        path=target,
        device=metadata.st_dev,
        inode=metadata.st_ino,
        subvolume_uuid=_SUBVOLUME_UUID,
        subvolume_id=259,
    )
    harness.subvolumes.identities[target] = ObservedBtrfsSubvolume(
        uuid=_SUBVOLUME_UUID,
        subvolume_id=259,
    )
    harness.storage.exact[target] = MountObservation(
        target=target,
        exists=True,
        mounted=False,
        mount_target=tmp_path,
        source="/dev/nvme0n1p3",
        source_device="/dev/nvme0n1p3",
        filesystem="btrfs",
        filesystem_uuid=_FILESYSTEM_UUID,
        fs_root="/",
        subvolume_id=5,
        options=("rw", "subvolid=5", "subvol=/"),
        top_level_mount=tmp_path,
    )

    plan = harness.planner.plan()
    result = harness.executor.execute(plan.fingerprint)

    assert [(action.kind, action.disposition) for action in plan.actions_for(DeletionStage.STORAGE)] == [
        (
            DeletionActionKind.DELETE_SUBVOLUME,
            DeletionDisposition.REQUIRES_ROOT,
        )
    ]
    assert not any(
        action.disposition is DeletionDisposition.BLOCKED for action in plan.actions_for(DeletionStage.FILESYSTEM)
    )
    assert len(plan.handoffs) == 1
    assert plan.handoffs[0].argv[-3:] == (
        "--subvolid",
        "259",
        str(tmp_path),
    )
    assert result.outcome is DeletionOutcome.PARTIAL
    assert harness.checkpoint.exists
    assert harness.bindings.destroy_calls == 0
    assert target.exists()


def test_unreceipted_unmounted_subvolume_blocks_every_generic_effect(
    tmp_path: Path,
) -> None:
    """Live Btrfs identity alone cannot become deletion authority."""
    harness = _build_harness(tmp_path)
    target = harness.paths.postgres_data
    harness.subvolumes.identities[target] = ObservedBtrfsSubvolume(
        uuid=_SUBVOLUME_UUID,
        subvolume_id=259,
    )

    plan = harness.planner.plan()
    result = harness.executor.execute(plan.fingerprint)

    assert any(
        action.disposition is DeletionDisposition.BLOCKED and "lacks initialization receipt authority" in action.detail
        for action in plan.actions_for(DeletionStage.STORAGE)
    )
    assert plan.handoffs == ()
    assert result.outcome is DeletionOutcome.BLOCKED
    assert harness.retirement.execute_calls == 0
    assert harness.bindings.destroy_calls == 0
    assert target.exists()


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


def test_any_subvolume_boundary_is_never_removed_generically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unlisted Btrfs boundary cannot be emptied by recursive deletion."""
    root = tmp_path / "crypt"
    candidate = root / "postgres-data"
    candidate.mkdir(parents=True)
    sentinel = candidate / "keep"
    sentinel.write_text("operator data", encoding="utf-8")
    service = ManagedTreeService((root,))
    real_stat = os.stat

    def boundary_stat(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes] | int,
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        result = real_stat(
            path,
            dir_fd=dir_fd,
            follow_symlinks=follow_symlinks,
        )
        if path == candidate.name and dir_fd is not None and follow_symlinks is False:
            values = list(result)
            values[stat.ST_INO] = 256
            return os.stat_result(values)
        return result

    monkeypatch.setattr(
        "lychd.system.services.lifecycle.trees.os.stat",
        boundary_stat,
    )

    with pytest.raises(LifecycleError, match="Btrfs subvolume boundary"):
        service.remove(root, expected_identity=_root_identity(root))

    assert sentinel.read_text(encoding="utf-8") == "operator data"


def test_dedicated_root_subvolume_boundary_is_never_emptied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A dedicated root may itself be a subvolume without being a mountpoint."""
    root = tmp_path / "crypt"
    root.mkdir()
    sentinel = root / "keep"
    sentinel.write_text("operator data", encoding="utf-8")
    expected_identity = _root_identity(root)
    service = ManagedTreeService((root,))
    real_lstat = Path.lstat

    def boundary_lstat(path: Path) -> os.stat_result:
        result = real_lstat(path)
        if path == root:
            values = list(result)
            values[stat.ST_INO] = 256
            return os.stat_result(values)
        return result

    monkeypatch.setattr(Path, "lstat", boundary_lstat)

    with pytest.raises(LifecycleError, match="Btrfs subvolume boundary"):
        service.remove(root, expected_identity=expected_identity)

    assert sentinel.read_text(encoding="utf-8") == "operator data"


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


def test_root_swap_at_retirement_is_restored_without_clobbering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Atomic quarantine detects a replacement after root traversal."""
    root = tmp_path / "codex"
    displaced = tmp_path / "codex-traversed"
    replacement = tmp_path / "codex-replacement"
    root.mkdir()
    replacement.mkdir()
    sentinel = replacement / "keep"
    sentinel.write_text("replacement", encoding="utf-8")
    service = ManagedTreeService((root,))
    swapped = False

    def swap_before_quarantine(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal swapped
        if source_name == root.name and destination_name.startswith(".lychd-retire-") and not swapped:
            root.rename(displaced)
            replacement.rename(root)
            swapped = True
        rename_noreplace_at(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    monkeypatch.setattr(
        "lychd.system.atomic_retirement.rename_noreplace_at",
        swap_before_quarantine,
    )

    with pytest.raises(LifecycleError, match="identity changed before retirement"):
        service.remove(root, expected_identity=_root_identity(root))

    assert displaced.is_dir()
    assert (root / sentinel.name).read_text(encoding="utf-8") == "replacement"


def test_child_directory_swap_at_retirement_is_restored_without_clobbering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A traversed child cannot transfer deletion authority to a replacement."""
    root = tmp_path / "codex"
    child = root / "managed"
    displaced = tmp_path / "managed-traversed"
    replacement = tmp_path / "managed-replacement"
    child.mkdir(parents=True)
    replacement.mkdir()
    sentinel = replacement / "keep"
    sentinel.write_text("replacement", encoding="utf-8")
    service = ManagedTreeService((root,))
    swapped = False

    def swap_before_quarantine(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal swapped
        if source_name == child.name and destination_name.startswith(".lychd-retire-") and not swapped:
            child.rename(displaced)
            replacement.rename(child)
            swapped = True
        rename_noreplace_at(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    monkeypatch.setattr(
        "lychd.system.atomic_retirement.rename_noreplace_at",
        swap_before_quarantine,
    )

    with pytest.raises(LifecycleError, match="identity changed before retirement"):
        service.remove(root, expected_identity=_root_identity(root))

    assert displaced.is_dir()
    assert (child / sentinel.name).read_text(encoding="utf-8") == "replacement"


def test_file_swap_at_retirement_is_restored_without_clobbering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An opened file cannot transfer unlink authority to a replacement."""
    root = tmp_path / "codex"
    root.mkdir()
    target = root / "owned.txt"
    displaced = tmp_path / "owned-opened.txt"
    replacement = tmp_path / "owned-replacement.txt"
    target.write_text("owned", encoding="utf-8")
    replacement.write_text("replacement", encoding="utf-8")
    service = ManagedTreeService((root,))
    swapped = False

    def swap_before_quarantine(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal swapped
        if source_name == target.name and destination_name.startswith(".lychd-retire-") and not swapped:
            target.rename(displaced)
            replacement.rename(target)
            swapped = True
        rename_noreplace_at(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    monkeypatch.setattr(
        "lychd.system.atomic_retirement.rename_noreplace_at",
        swap_before_quarantine,
    )

    with pytest.raises(LifecycleError, match="identity changed before retirement"):
        service.remove(root, expected_identity=_root_identity(root))

    assert displaced.read_text(encoding="utf-8") == "owned"
    assert target.read_text(encoding="utf-8") == "replacement"


@pytest.mark.parametrize(
    "close_failure",
    [OSError("tree entry close failed"), KeyboardInterrupt(), SystemExit(99)],
)
def test_tree_close_failure_preserves_partial_outcome_and_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    close_failure: BaseException,
) -> None:
    """A retired child and retained root remain explicit after a close failure."""
    root = tmp_path / "codex"
    root.mkdir()
    target = root / "owned.txt"
    target.write_text("owned", encoding="utf-8")
    expected_identity = _root_identity(root)
    service = ManagedTreeService((root,))
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

    expected = ManagedTreeSettlementError if isinstance(close_failure, Exception) else type(close_failure)
    with pytest.raises(expected) as raised:
        service.remove(root, expected_identity=expected_identity)

    graph = tuple(iter_exception_graph(raised.value))
    assert close_failure in graph
    if not isinstance(close_failure, Exception):
        assert raised.value is close_failure
    settlement = find_settlement_outcome(raised.value)
    assert settlement is not None
    assert settlement.name == "partial"
    assert settlement.verified
    assert injected
    assert root.is_dir()
    assert not target.exists()
    assert tuple(root.glob(".lychd-retire-*")) == ()

    service.remove(root, expected_identity=expected_identity)
    assert not root.exists()


@pytest.mark.parametrize(
    "close_failure",
    [OSError("root descriptor close failed"), KeyboardInterrupt(), SystemExit(101)],
)
def test_retired_tree_settles_remaining_descriptor_after_close_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    close_failure: BaseException,
) -> None:
    """A root-descriptor failure cannot skip settlement of its parent peer."""
    root = tmp_path / "codex"
    root.mkdir()
    expected_identity = _root_identity(root)
    service = ManagedTreeService((root,))
    real_close = os.close
    close_calls = 0

    def close_then_fail(descriptor: int) -> None:
        nonlocal close_calls
        close_calls += 1
        real_close(descriptor)
        if close_calls == 2:
            raise close_failure

    monkeypatch.setattr(
        "lychd.system.descriptor_settlement.os.close",
        close_then_fail,
    )

    expected = ManagedTreeSettlementError if isinstance(close_failure, Exception) else type(close_failure)
    with pytest.raises(expected) as raised:
        service.remove(root, expected_identity=expected_identity)

    assert close_failure in tuple(iter_exception_graph(raised.value))
    if not isinstance(close_failure, Exception):
        assert raised.value is close_failure
    settlement = find_settlement_outcome(raised.value)
    assert settlement is not None
    assert settlement.name == "retired"
    assert settlement.verified
    assert close_calls == 3
    assert not root.exists()
    assert tuple(tmp_path.glob(".lychd-retire-*")) == ()

    service.remove(root, expected_identity=expected_identity)


def test_retained_file_quarantine_surfaces_through_lifecycle_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Managed-tree failure preserves typed recovery evidence and blocks retry."""
    root = tmp_path / "codex"
    root.mkdir()
    target = root / "owned.txt"
    target.write_text("owned", encoding="utf-8")
    service = ManagedTreeService((root,))

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

    with pytest.raises(LifecycleError, match="preserved the quarantined entry") as raised:
        service.remove(root, expected_identity=_root_identity(root))

    cause = raised.value.__cause__
    assert isinstance(cause, AtomicRetirementError)
    assert cause.recovery is not None
    assert cause.recovery.quarantine.exists()
    assert target.read_text(encoding="utf-8") == "foreign"
    assert service.inspect(root).detail.startswith("retained atomic-retirement quarantine requires recovery")


def test_tree_failure_preserves_receipt_and_checkpoint_for_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recovery authorities are retired only after ordinary Codex entries."""
    root = tmp_path / "codex"
    root.mkdir()
    ordinary = root / "late-failure"
    checkpoint = root / ".lychd-del-state.json"
    receipt = root / ".lychd-lifecycle.json"
    ordinary.write_text("retry", encoding="utf-8")
    checkpoint.write_text("checkpoint", encoding="utf-8")
    receipt.write_text("receipt", encoding="utf-8")
    ordinary_inode = ordinary.lstat().st_ino
    root_identity = _root_identity(root)
    service = ManagedTreeService((root,))
    real_unlink = os.unlink
    failed_once = False

    def fail_ordinary_once(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal failed_once
        metadata = os.stat(path, dir_fd=dir_fd, follow_symlinks=False) if dir_fd is not None else None
        if metadata is not None and metadata.st_ino == ordinary_inode and not failed_once:
            failed_once = True
            message = "simulated ordinary-entry failure"
            raise OSError(message)
        real_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(
        "lychd.system.atomic_retirement.os.unlink",
        fail_ordinary_once,
    )

    with pytest.raises(LifecycleError, match="restored"):
        service.remove(
            root,
            expected_identity=root_identity,
            final_entries=(checkpoint, receipt),
        )

    assert ordinary.exists()
    assert checkpoint.read_text(encoding="utf-8") == "checkpoint"
    assert receipt.read_text(encoding="utf-8") == "receipt"

    service.remove(
        root,
        expected_identity=root_identity,
        final_entries=(checkpoint, receipt),
    )

    assert not root.exists()


def test_late_root_writer_restores_root_and_authorities_for_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late child cannot strand deletion after its authorities disappear."""
    root = tmp_path / "codex"
    root.mkdir()
    checkpoint = root / ".lychd-del-state.json"
    receipt = root / ".lychd-lifecycle.json"
    checkpoint.write_text("checkpoint", encoding="utf-8")
    receipt.write_text("receipt", encoding="utf-8")
    service = ManagedTreeService((root,))
    real_rmdir = os.rmdir

    def populate_detached_root(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        assert isinstance(path, str)
        assert dir_fd is not None
        if path.startswith(".lychd-retire-"):
            parent = Path(f"/proc/self/fd/{dir_fd}").readlink()
            (parent / path / "late.txt").write_text("preserve", encoding="utf-8")
        real_rmdir(path, dir_fd=dir_fd)

    monkeypatch.setattr(
        "lychd.system.protected_retirement.os.rmdir",
        populate_detached_root,
    )

    with pytest.raises(LifecycleError, match="restored for retry"):
        service.remove(
            root,
            expected_identity=_root_identity(root),
            final_entries=(checkpoint, receipt),
        )

    assert (root / "late.txt").read_text(encoding="utf-8") == "preserve"
    assert checkpoint.read_text(encoding="utf-8") == "checkpoint"
    assert receipt.read_text(encoding="utf-8") == "receipt"
    assert not tuple(tmp_path.glob(".lychd-retire-authority-*"))


@pytest.mark.parametrize("effect", ["before", "after"])
@pytest.mark.parametrize(
    "failure_kind",
    ["generic", "eexist", "enoent", "keyboard", "systemexit"],
)
def test_protected_detach_rename_failure_matrix_has_exact_settlement(  # noqa: PLR0915 - explicit fault matrix
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_kind: str,
    effect: str,
) -> None:
    """Every protected-root rename failure proves collision or exact state."""
    root = tmp_path / "codex"
    root.mkdir()
    expected_identity = _retirement_identity(root)
    failures: dict[str, BaseException] = {
        "generic": OSError(errno.EIO, "generic detach failure"),
        "eexist": OSError(errno.EEXIST, "root candidate collision"),
        "enoent": OSError(errno.ENOENT, "root source absent"),
        "keyboard": KeyboardInterrupt(),
        "systemexit": SystemExit(139),
    }
    primary = failures[failure_kind]
    real_rename = rename_noreplace_at
    injected = False
    collisions: list[Path] = []
    detached: Path | None = None

    def fail_detach(
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
            collision.mkdir()
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
        protected_retirement_module,
        "rename_noreplace_at",
        fail_detach,
    )
    service = _ProtectedDetachProbe()
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        if failure_kind == "eexist" and effect == "before":
            detached_name = service.detach(
                parent_fd=parent_fd,
                leaf=root.name,
                expected=expected_identity,
                display_path=root,
            )
            detached = tmp_path / detached_name
        else:
            expected_error = ProtectedRootRetirementError if isinstance(primary, Exception) else type(primary)
            with pytest.raises(expected_error) as raised:
                service.detach(
                    parent_fd=parent_fd,
                    leaf=root.name,
                    expected=expected_identity,
                    display_path=root,
                )

            assert primary in tuple(iter_exception_graph(raised.value))
            if isinstance(primary, Exception):
                assert isinstance(raised.value, ProtectedRootRetirementError)
                assert raised.value.outcome == "restored"
                assert raised.value.outcome_verified
                assert raised.value.root_recovery is None
            else:
                assert raised.value is primary
    finally:
        os.close(parent_fd)

    assert injected
    if collisions:
        assert detached is not None
        assert not root.exists()
        assert _retirement_identity(detached) == expected_identity
        assert collisions[0].is_dir()
        assert tuple(tmp_path.glob(".lychd-retire-*")) == (
            collisions[0],
            detached,
        ) or tuple(tmp_path.glob(".lychd-retire-*")) == (
            detached,
            collisions[0],
        )
    else:
        assert root.is_dir()
        assert _retirement_identity(root) == expected_identity
        assert tuple(tmp_path.glob(".lychd-retire-*")) == ()


def test_protected_enoent_dual_absence_emits_both_exact_root_names(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A vanished protected root is recovery, not idempotent success."""
    root = tmp_path / "codex"
    lost = tmp_path / "codex-lost"
    root.mkdir()
    expected_identity = _retirement_identity(root)
    primary = OSError(errno.ENOENT, "protected root disappeared")
    candidate: Path | None = None

    def displace_root_then_fail(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal candidate
        del source_name, source_dir_fd, destination_dir_fd
        root.rename(lost)
        candidate = tmp_path / destination_name
        raise primary

    monkeypatch.setattr(
        protected_retirement_module,
        "rename_noreplace_at",
        displace_root_then_fail,
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(ProtectedRootRetirementError) as raised:
            _ProtectedDetachProbe().detach(
                parent_fd=parent_fd,
                leaf=root.name,
                expected=expected_identity,
                display_path=root,
            )
    finally:
        os.close(parent_fd)

    assert candidate is not None
    recovery = raised.value.root_recovery
    assert recovery is not None
    assert recovery.root == root
    assert recovery.root_quarantine == candidate
    assert not root.exists()
    assert not candidate.exists()
    assert _retirement_identity(lost) == expected_identity
    assert raised.value.outcome == "recovery"
    assert raised.value.outcome_verified
    assert primary in raised.value.failures


@pytest.mark.parametrize(
    "observation_failure",
    [OSError("detach observation failed"), KeyboardInterrupt(), SystemExit(149)],
)
def test_protected_detach_observation_failure_retains_full_root_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    observation_failure: BaseException,
) -> None:
    """Unobservable detachment names the root containing every authority."""
    root = tmp_path / "codex"
    root.mkdir()
    authorities = tuple(root / name for name in ("checkpoint.json", "receipt.json"))
    for authority in authorities:
        authority.write_text(authority.name, encoding="utf-8")
    expected_identity = _retirement_identity(root)
    primary = OSError(errno.EIO, "detach completed without a receipt")
    candidate_name: str | None = None
    real_observe = protected_retirement_module.observe_retirement_name

    def detach_then_fail(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal candidate_name
        rename_noreplace_at(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )
        candidate_name = destination_name
        raise primary

    def fail_candidate_observation(
        *,
        parent_fd: int,
        name: str,
    ) -> RetirementIdentity | None:
        if name == candidate_name:
            raise observation_failure
        return real_observe(parent_fd=parent_fd, name=name)

    monkeypatch.setattr(
        protected_retirement_module,
        "rename_noreplace_at",
        detach_then_fail,
    )
    monkeypatch.setattr(
        protected_retirement_module,
        "observe_retirement_name",
        fail_candidate_observation,
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(ProtectedRootRetirementError) as raised:
            _ProtectedDetachProbe().detach(
                parent_fd=parent_fd,
                leaf=root.name,
                expected=expected_identity,
                display_path=root,
            )
    finally:
        os.close(parent_fd)

    assert candidate_name is not None
    candidate = tmp_path / candidate_name
    recovery = raised.value.root_recovery
    assert recovery is not None
    assert recovery.root == root
    assert recovery.root_quarantine == candidate
    assert not root.exists()
    assert _retirement_identity(candidate) == expected_identity
    assert all((candidate / authority.name).read_text(encoding="utf-8") == authority.name for authority in authorities)
    assert primary in raised.value.failures
    assert observation_failure in raised.value.failures
    assert raised.value.outcome == "recovery"
    assert not raised.value.outcome_verified


def test_protected_root_rmdir_after_effect_emits_verified_retired_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An ordinary rmdir return failure cannot obscure full-root retirement."""
    root = tmp_path / "codex"
    root.mkdir()
    authorities = tuple(root / name for name in ("checkpoint.json", "receipt.json"))
    for authority in authorities:
        authority.write_text(authority.name, encoding="utf-8")
    entries = tuple(
        ProtectedRetirementEntry(
            leaf=authority.name,
            resource=authority,
            expected=_retirement_identity(authority),
        )
        for authority in authorities
    )
    primary = OSError(errno.EIO, "root rmdir lost its receipt")
    real_rmdir = os.rmdir

    def remove_then_fail(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        real_rmdir(path, dir_fd=dir_fd)
        raise primary

    monkeypatch.setattr(
        protected_retirement_module.os,
        "rmdir",
        remove_then_fail,
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(ProtectedRootRetirementError) as raised:
            ProtectedRootRetirementService().retire(
                parent_fd=parent_fd,
                directory_fd=directory_fd,
                leaf=root.name,
                expected=_retirement_identity(root),
                display_path=root,
                protected=entries,
            )
    finally:
        os.close(directory_fd)
        os.close(parent_fd)

    assert raised.value.outcome == "retired"
    assert raised.value.outcome_verified
    assert primary in tuple(iter_exception_graph(raised.value))
    assert not root.exists()
    assert tuple(tmp_path.glob(".lychd-retire-*")) == ()


@pytest.mark.parametrize(
    "transfer_failure",
    [OSError("authority transfer lost its receipt"), KeyboardInterrupt(), SystemExit(151)],
)
def test_authority_transfer_after_effect_settles_every_peer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    transfer_failure: BaseException,
) -> None:
    """A first-authority return failure cannot skip a second authority."""
    root = tmp_path / "codex"
    root.mkdir()
    authorities = tuple(root / name for name in ("checkpoint.json", "receipt.json"))
    for authority in authorities:
        authority.write_text(authority.name, encoding="utf-8")
    entries = tuple(
        ProtectedRetirementEntry(
            leaf=authority.name,
            resource=authority,
            expected=_retirement_identity(authority),
        )
        for authority in authorities
    )
    real_rename = rename_noreplace_at
    injected = False

    def transfer_then_fail(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal injected
        real_rename(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )
        if source_name == authorities[0].name and not injected:
            injected = True
            raise transfer_failure

    monkeypatch.setattr(
        protected_retirement_module,
        "rename_noreplace_at",
        transfer_then_fail,
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        expected_error = (
            ProtectedRootRetirementError if isinstance(transfer_failure, Exception) else type(transfer_failure)
        )
        with pytest.raises(expected_error) as raised:
            ProtectedRootRetirementService().retire(
                parent_fd=parent_fd,
                directory_fd=directory_fd,
                leaf=root.name,
                expected=_retirement_identity(root),
                display_path=root,
                protected=entries,
            )
    finally:
        os.close(directory_fd)
        os.close(parent_fd)

    assert injected
    assert transfer_failure in tuple(iter_exception_graph(raised.value))
    if isinstance(transfer_failure, Exception):
        assert isinstance(raised.value, ProtectedRootRetirementError)
    else:
        assert raised.value is transfer_failure
    settlement = find_settlement_outcome(raised.value)
    assert settlement is not None
    assert settlement.name == "restored"
    assert settlement.verified
    assert root.is_dir()
    assert all(authority.read_text(encoding="utf-8") == authority.name for authority in authorities)
    assert tuple(tmp_path.glob(".lychd-retire-*")) == ()


@pytest.mark.parametrize("terminal", [KeyboardInterrupt(), SystemExit(43)])
def test_root_retirement_interruption_before_effect_restores_authorities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    terminal: BaseException,
) -> None:
    root = tmp_path / "codex"
    root.mkdir()
    checkpoint = root / ".lychd-del-state.json"
    receipt = root / ".lychd-lifecycle.json"
    checkpoint.write_text("checkpoint", encoding="utf-8")
    receipt.write_text("receipt", encoding="utf-8")
    service = ManagedTreeService((root,))

    def interrupt_rmdir(
        _path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        del dir_fd
        raise terminal

    monkeypatch.setattr(
        "lychd.system.protected_retirement.os.rmdir",
        interrupt_rmdir,
    )

    with pytest.raises(type(terminal)):
        service.remove(
            root,
            expected_identity=_root_identity(root),
            final_entries=(checkpoint, receipt),
        )

    assert root.is_dir()
    assert checkpoint.read_text(encoding="utf-8") == "checkpoint"
    assert receipt.read_text(encoding="utf-8") == "receipt"
    assert not tuple(tmp_path.glob(".lychd-retire-authority-*"))


@pytest.mark.parametrize("terminal", [KeyboardInterrupt(), SystemExit(47)])
def test_root_retirement_interruption_after_effect_finalizes_authorities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    terminal: BaseException,
) -> None:
    root = tmp_path / "codex"
    root.mkdir()
    checkpoint = root / ".lychd-del-state.json"
    receipt = root / ".lychd-lifecycle.json"
    checkpoint.write_text("checkpoint", encoding="utf-8")
    receipt.write_text("receipt", encoding="utf-8")
    service = ManagedTreeService((root,))
    real_rmdir = os.rmdir

    def remove_then_interrupt(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        real_rmdir(path, dir_fd=dir_fd)
        raise terminal

    monkeypatch.setattr(
        "lychd.system.protected_retirement.os.rmdir",
        remove_then_interrupt,
    )

    with pytest.raises(type(terminal)):
        service.remove(
            root,
            expected_identity=_root_identity(root),
            final_entries=(checkpoint, receipt),
        )

    assert not root.exists()
    assert not tuple(tmp_path.glob(".lychd-retire-authority-*"))
    assert not tuple(tmp_path.glob(".lychd-retire-*"))


@pytest.mark.parametrize("observation_failure", [OSError("EIO"), KeyboardInterrupt(), SystemExit(61)])
def test_post_detach_observation_failure_names_exact_root_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    observation_failure: BaseException,
) -> None:
    root = tmp_path / "codex"
    root.mkdir()
    authority = root / ".lychd-lifecycle.json"
    authority.write_text("receipt", encoding="utf-8")
    root_expected = _retirement_identity(root)
    entry = ProtectedRetirementEntry(
        leaf=authority.name,
        resource=authority,
        expected=_retirement_identity(authority),
    )
    real_observe = protected_retirement_module.observe_retirement_name

    def fail_detached_observation(
        *,
        parent_fd: int,
        name: str,
    ) -> RetirementIdentity | None:
        if name.startswith(".lychd-retire-") and not name.startswith(".lychd-retire-authority-"):
            raise observation_failure
        return real_observe(parent_fd=parent_fd, name=name)

    monkeypatch.setattr(
        "lychd.system.protected_retirement.observe_retirement_name",
        fail_detached_observation,
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(ProtectedRootRetirementError) as raised:
            ProtectedRootRetirementService().retire(
                parent_fd=parent_fd,
                directory_fd=directory_fd,
                leaf=root.name,
                expected=root_expected,
                display_path=root,
                protected=(entry,),
            )
    finally:
        os.close(directory_fd)
        os.close(parent_fd)

    recovery = raised.value.root_recovery
    assert recovery is not None
    assert recovery.root_quarantine is not None
    assert recovery.root_quarantine.parent == tmp_path
    assert recovery.root_quarantine.exists()
    assert raised.value.__cause__ is observation_failure


@pytest.mark.parametrize(
    "restore_failure",
    [OSError("authority restore lost its receipt"), KeyboardInterrupt(), SystemExit(67)],
)
def test_authority_restore_after_effect_settles_all_peers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    restore_failure: BaseException,
) -> None:
    root = tmp_path / "codex"
    root.mkdir()
    authorities = tuple(root / name for name in ("checkpoint.json", "receipt.json"))
    for authority in authorities:
        authority.write_text(authority.name, encoding="utf-8")
    entries = tuple(
        ProtectedRetirementEntry(
            leaf=authority.name,
            resource=authority,
            expected=_retirement_identity(authority),
        )
        for authority in authorities
    )
    real_rename = rename_noreplace_at
    interrupted = False

    def restore_then_interrupt(
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
        if source_name.startswith(".lychd-retire-authority-") and not interrupted:
            interrupted = True
            raise restore_failure

    def reject_root_removal(
        _path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        del dir_fd
        message = "late writer"
        raise OSError(message)

    monkeypatch.setattr(
        "lychd.system.protected_retirement_recovery.rename_noreplace_at",
        restore_then_interrupt,
    )
    monkeypatch.setattr(
        "lychd.system.protected_retirement.os.rmdir",
        reject_root_removal,
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        expected_error = (
            ProtectedRootRetirementError if isinstance(restore_failure, Exception) else type(restore_failure)
        )
        with pytest.raises(expected_error) as raised:
            ProtectedRootRetirementService().retire(
                parent_fd=parent_fd,
                directory_fd=directory_fd,
                leaf=root.name,
                expected=_retirement_identity(root),
                display_path=root,
                protected=entries,
            )
    finally:
        os.close(directory_fd)
        os.close(parent_fd)

    assert restore_failure in tuple(iter_exception_graph(raised.value))
    if isinstance(restore_failure, Exception):
        assert isinstance(raised.value, ProtectedRootRetirementError)
    else:
        assert raised.value is restore_failure
    settlement = find_settlement_outcome(raised.value)
    assert settlement is not None
    assert settlement.name == "restored"
    assert settlement.verified
    assert all(authority.exists() for authority in authorities)
    assert not tuple(tmp_path.glob(".lychd-retire-authority-*"))
    assert not tuple(tmp_path.glob(".lychd-retire-*"))


@pytest.mark.parametrize("candidate_kind", ["root-quarantine", "authority-backup"])
@pytest.mark.parametrize(
    "observation_failure",
    [OSError("unreadable absence"), KeyboardInterrupt(), SystemExit(69)],
)
def test_expected_absence_observation_failure_never_proves_exact_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    candidate_kind: str,
    observation_failure: BaseException,
) -> None:
    root = tmp_path / "codex"
    root.mkdir()
    authority = root / "receipt.json"
    authority.write_text("receipt", encoding="utf-8")
    entry = ProtectedRetirementEntry(
        leaf=authority.name,
        resource=authority,
        expected=_retirement_identity(authority),
    )
    real_observe = protected_retirement_recovery_module.observe_retirement_name
    observations = 0

    def fail_expected_absence(
        *,
        parent_fd: int,
        name: str,
    ) -> RetirementIdentity | None:
        nonlocal observations
        targets_root = candidate_kind == "root-quarantine" and is_retirement_quarantine_name(name)
        targets_authority = candidate_kind == "authority-backup" and is_protected_authority_name(name)
        if targets_root or targets_authority:
            observations += 1
            failure_threshold = 2 if targets_root else 3
            if observations >= failure_threshold:
                raise observation_failure
        return real_observe(parent_fd=parent_fd, name=name)

    def reject_root_removal(
        _path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        del dir_fd
        message = "force protected-root recovery"
        raise OSError(message)

    monkeypatch.setattr(
        protected_retirement_recovery_module,
        "observe_retirement_name",
        fail_expected_absence,
    )
    monkeypatch.setattr(
        protected_retirement_module.os,
        "rmdir",
        reject_root_removal,
    )
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(ProtectedRootRetirementError) as raised:
            ProtectedRootRetirementService().retire(
                parent_fd=parent_fd,
                directory_fd=directory_fd,
                leaf=root.name,
                expected=_retirement_identity(root),
                display_path=root,
                protected=(entry,),
            )
    finally:
        os.close(directory_fd)
        os.close(parent_fd)

    recovery = raised.value.root_recovery
    assert recovery is not None
    assert observation_failure in raised.value.failures
    assert root.is_dir()
    assert authority.read_text(encoding="utf-8") == "receipt"
    if candidate_kind == "root-quarantine":
        assert recovery.root_quarantine is not None
        assert is_retirement_quarantine_name(recovery.root_quarantine.name)
    else:
        assert any(
            retained.observed is None and is_protected_authority_name(retained.recovery_path.name)
            for retained in recovery.authorities
        )
    if not isinstance(observation_failure, Exception):
        assert raised.value.__cause__ is observation_failure


def test_retained_finalization_uses_later_peer_terminal_as_cause(
    tmp_path: Path,
) -> None:
    root = tmp_path / "codex"
    root.mkdir()
    authorities = tuple(root / name for name in ("checkpoint.json", "receipt.json"))
    for authority in authorities:
        authority.write_text(authority.name, encoding="utf-8")
    entries = tuple(
        ProtectedRetirementEntry(
            leaf=authority.name,
            resource=authority,
            expected=_retirement_identity(authority),
        )
        for authority in authorities
    )
    terminal = KeyboardInterrupt()

    class FailingEntries(AtomicRetirementService):
        def __init__(self) -> None:
            self.calls = 0

        def retire_file(
            self,
            *,
            parent_fd: int,
            leaf: str,
            expected: RetirementIdentity,
            display_path: Path,
        ) -> None:
            del parent_fd, leaf, expected, display_path
            self.calls += 1
            if self.calls == 1:
                message = "ordinary peer failure"
                raise AtomicRetirementError(message)
            raise terminal

    failing_entries = FailingEntries()
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(ProtectedRootRetirementError) as raised:
            ProtectedRootRetirementService(entries=failing_entries).retire(
                parent_fd=parent_fd,
                directory_fd=directory_fd,
                leaf=root.name,
                expected=_retirement_identity(root),
                display_path=root,
                protected=entries,
            )
    finally:
        os.close(directory_fd)
        os.close(parent_fd)

    assert failing_entries.calls == 2
    assert raised.value.__cause__ is terminal
    assert terminal in raised.value.failures
    assert raised.value.root_recovery is not None
    assert len(raised.value.root_recovery.authorities) == 2
    assert not root.exists()


def test_terminal_root_failure_names_retained_recovery_without_flattening(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "codex"
    root.mkdir()
    checkpoint = root / ".lychd-del-state.json"
    receipt = root / ".lychd-lifecycle.json"
    checkpoint.write_text("checkpoint", encoding="utf-8")
    receipt.write_text("receipt", encoding="utf-8")
    service = ManagedTreeService((root,))
    real_rename = rename_noreplace_at

    def fail_checkpoint_restore(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        if source_name.startswith(".lychd-retire-authority-") and destination_name == checkpoint.name:
            message = "simulated authority restoration failure"
            raise OSError(message)
        real_rename(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    def interrupt_root_removal(
        _path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        del dir_fd
        raise KeyboardInterrupt

    monkeypatch.setattr(
        "lychd.system.protected_retirement_recovery.rename_noreplace_at",
        fail_checkpoint_restore,
    )
    monkeypatch.setattr(
        "lychd.system.protected_retirement.os.rmdir",
        interrupt_root_removal,
    )

    with pytest.raises(KeyboardInterrupt) as raised:
        service.remove(
            root,
            expected_identity=_root_identity(root),
            final_entries=(checkpoint, receipt),
        )

    recovery_note = "\n".join(raised.value.__notes__)
    assert ".lychd-retire-" in recovery_note
    assert ".lychd-retire-authority-" in recovery_note
    assert tuple(tmp_path.glob(".lychd-retire-*"))


def test_retained_sibling_authority_blocks_a_later_delete_plan(
    tmp_path: Path,
) -> None:
    root = tmp_path / "codex"
    residue = tmp_path / f".lychd-retire-authority-{'a' * 32}"
    residue.write_text("recovery", encoding="utf-8")

    inspection = ManagedTreeService((root,)).inspect(root)

    assert not inspection.removable
    assert inspection.exists is False
    assert str(residue) in inspection.detail


@pytest.mark.parametrize("terminal", [KeyboardInterrupt(), SystemExit(53)])
def test_wrapped_scribe_interruption_is_not_flattened_into_partial_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    terminal: BaseException,
) -> None:
    harness = _build_harness(tmp_path)

    def interrupt_bindings() -> None:
        error = ScribeTransactionError(
            "binding cleanup interrupted",
            state=ScribeTransactionState.ROLLED_BACK,
            forward_error=terminal,
        )
        raise error from terminal

    monkeypatch.setattr(harness.bindings, "destroy", interrupt_bindings)
    plan = harness.planner.plan()

    with pytest.raises(type(terminal)) as raised:
        harness.executor.execute(plan.fingerprint)

    assert any("Rerun `lychd del`" in note for note in raised.value.__notes__)
    assert harness.scribe.ownership_path.exists()


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
