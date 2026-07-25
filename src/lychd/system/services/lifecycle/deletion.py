"""Staged, fail-closed deletion of one local LychD installation."""

from __future__ import annotations

import os
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Protocol

from lychd.system.operator.retirement import UnitRetirementPlan
from lychd.system.services.lifecycle.deletion_checkpoint import (
    DeletionCheckpointStore,
)
from lychd.system.services.lifecycle.deletion_models import (
    DELETION_STAGE_ORDER,
    BtrfsSubvolumeIdentity,
    DeletionAction,
    DeletionActionKind,
    DeletionDisposition,
    DeletionOutcome,
    DeletionPaths,
    DeletionPlan,
    DeletionResult,
    DeletionStage,
)
from lychd.system.services.lifecycle.deletion_storage import (
    BtrfsSubvolumeProbe,
    CommandBtrfsSubvolumeProbe,
    DeletionStoragePlanner,
    ObservedBtrfsSubvolume,
    StorageInventoryPort,
)
from lychd.system.services.lifecycle.lock import LifecycleLock
from lychd.system.services.lifecycle.models import (
    DedicatedRootIdentity,
    LifecycleError,
    LifecyclePlan,
)
from lychd.system.services.lifecycle.paths import is_within
from lychd.system.services.lifecycle.trees import ManagedTreeService
from lychd.system.services.scribe import OwnedBindings


class UnitRetirementPort(Protocol):
    """Exact Scribe-owned unit retirement supplied by the operator layer."""

    def plan(self) -> UnitRetirementPlan:
        """Return one immutable stop/disable plan."""
        ...

    def execute(self, plan: UnitRetirementPlan) -> None:
        """Apply one unchanged retirement plan."""
        ...


class ScribeOwnershipPort(Protocol):
    """Read-only Scribe authority needed by the deletion planner."""

    @property
    def ownership_path(self) -> Path:
        """Return the exact ownership receipt path."""
        ...

    def inspect_owned_bindings(self) -> OwnedBindings:
        """Return exact generated binding and runtime-unit ownership."""
        ...


class BindingCleanupPort(Protocol):
    """Existing exact Scribe binding cleanup transaction."""

    def plan_destroy(self) -> LifecyclePlan:
        """Verify exact units are inert and bindings remain unchanged."""
        ...

    def destroy(self) -> None:
        """Remove exact bindings and reload the user manager."""
        ...


class DedicatedRootAuthorityPort(Protocol):
    """Initialization-issued authority for recursive dedicated-root removal."""

    path: Path

    def require_dedicated_root_identities(
        self,
        expected_roots: tuple[Path, ...],
    ) -> tuple[DedicatedRootIdentity, ...]:
        """Return exact live identities or fail closed."""
        ...


class DeletionPlanner:
    """Assemble one complete zero-effect deletion plan from exact authority."""

    def __init__(
        self,
        *,
        paths: DeletionPaths,
        retirement: UnitRetirementPort,
        scribe: ScribeOwnershipPort,
        storage: StorageInventoryPort,
        subvolumes: BtrfsSubvolumeProbe,
        checkpoint: DeletionCheckpointStore,
        trees: ManagedTreeService,
        root_authority: DedicatedRootAuthorityPort,
        umount_bin: str | None,
        btrfs_bin: str | None,
        sudo_bin: str | None = "",
    ) -> None:
        """Bind read-only authority and already-resolved host tools."""
        self.paths = paths
        self._retirement = retirement
        self._scribe = scribe
        self._checkpoint = checkpoint
        self._trees = trees
        self._root_authority = root_authority
        self._storage = DeletionStoragePlanner(
            paths=paths,
            storage=storage,
            subvolumes=subvolumes,
            checkpoint=checkpoint,
            umount_bin=umount_bin,
            btrfs_bin=btrfs_bin,
            sudo_bin=sudo_bin,
        )

    def plan(self) -> DeletionPlan:
        """Inspect every stage without changing units, files, mounts, or receipts."""
        actions: list[DeletionAction] = []
        unit_plan, owned, authority_actions = self._authority_plan()
        actions.extend(authority_actions)
        if owned is not None and unit_plan is not None:
            actions.extend(self._unit_actions(unit_plan))
            actions.extend(self._binding_actions(owned))

        actions.append(self._runtime_preservation())
        storage = self._storage.plan()
        actions.extend(storage.actions)
        actions.append(self._secret_preservation())
        root_identities, root_authority_action = self._root_authority_plan()
        actions.append(root_authority_action)
        actions.extend(
            self._tree_actions(
                storage_actions=storage.actions,
                storage_identity=storage.identity,
                root_authorized=(root_authority_action.disposition is not DeletionDisposition.BLOCKED),
            )
        )
        actions.append(self._package_action())
        actions.append(
            self._action(
                DeletionStage.VERIFY,
                DeletionDisposition.SATISFIED,
                DeletionActionKind.VERIFY,
                "post-deletion inventory",
                "executor replans after every irreversible stage",
            )
        )
        stage_index = {stage: index for index, stage in enumerate(DELETION_STAGE_ORDER)}
        kind_index = {kind: index for index, kind in enumerate(DeletionActionKind)}
        ordered = tuple(
            sorted(
                actions,
                key=lambda action: (
                    stage_index[action.stage],
                    kind_index[action.kind],
                    action.target,
                    action.disposition.value,
                ),
            )
        )
        return DeletionPlan(
            actions=ordered,
            unit_plan=unit_plan,
            storage_identity=storage.identity,
            root_identities=root_identities,
            handoffs=(
                () if any(action.disposition is DeletionDisposition.BLOCKED for action in ordered) else storage.handoffs
            ),
        )

    def _root_authority_plan(
        self,
    ) -> tuple[tuple[DedicatedRootIdentity, ...], DeletionAction]:
        """Validate the init-issued root set before proposing recursive removal."""
        if not any(os.path.lexists(root) for root in self.paths.dedicated_roots):
            return (), self._action(
                DeletionStage.FILESYSTEM,
                DeletionDisposition.SATISFIED,
                DeletionActionKind.VERIFY_ROOT_AUTHORITY,
                str(self._root_authority.path),
                "all dedicated roots are already absent",
            )
        try:
            identities = self._root_authority.require_dedicated_root_identities(self.paths.dedicated_roots)
        except Exception as exc:  # noqa: BLE001 - invalid authority becomes plan evidence
            return (), self._action(
                DeletionStage.FILESYSTEM,
                DeletionDisposition.BLOCKED,
                DeletionActionKind.VERIFY_ROOT_AUTHORITY,
                str(self._root_authority.path),
                f"cannot validate initialization-issued root authority: {exc}",
            )
        return identities, self._action(
            DeletionStage.FILESYSTEM,
            DeletionDisposition.SATISFIED,
            DeletionActionKind.VERIFY_ROOT_AUTHORITY,
            str(self._root_authority.path),
            "exact dedicated-root paths and device/inode identities are attested",
        )

    def _authority_plan(
        self,
    ) -> tuple[
        UnitRetirementPlan | None,
        OwnedBindings | None,
        list[DeletionAction],
    ]:
        actions: list[DeletionAction] = []
        owned: OwnedBindings | None = None
        unit_plan: UnitRetirementPlan | None = None
        try:
            owned = self._scribe.inspect_owned_bindings()
        except Exception as exc:  # noqa: BLE001 - corrupt authority becomes plan evidence
            actions.append(
                self._quiesce_blocker(
                    "Scribe ownership",
                    f"cannot validate exact unit authority: {exc}",
                )
            )
        try:
            unit_plan = self._retirement.plan()
        except Exception as exc:  # noqa: BLE001 - operator probe failures are blockers
            actions.append(
                self._quiesce_blocker(
                    "Scribe-owned units",
                    f"cannot produce an exact retirement plan: {exc}",
                )
            )
        if owned is not None and unit_plan is not None and owned.generation != unit_plan.generation:
            actions.append(
                self._quiesce_blocker(
                    "Scribe generation",
                    "binding and operator inventories disagree",
                )
            )
            unit_plan = None
        return unit_plan, owned, actions

    def _quiesce_blocker(self, target: str, detail: str) -> DeletionAction:
        return self._action(
            DeletionStage.QUIESCE,
            DeletionDisposition.BLOCKED,
            DeletionActionKind.VERIFY_UNIT,
            target,
            detail,
        )

    def _unit_actions(self, plan: UnitRetirementPlan) -> list[DeletionAction]:
        if not plan.owned_units:
            return [
                self._action(
                    DeletionStage.QUIESCE,
                    DeletionDisposition.SATISFIED,
                    DeletionActionKind.VERIFY_UNIT,
                    "Scribe-owned units",
                    "no exact runtime units are recorded",
                )
            ]
        stop = set(plan.stop_units)
        disable = set(plan.disable_units)
        actions: list[DeletionAction] = []
        for unit in plan.owned_units:
            actions.append(self._unit_stop_action(unit, stop=stop))
            if unit in disable:
                actions.append(
                    self._action(
                        DeletionStage.QUIESCE,
                        DeletionDisposition.WOULD_APPLY,
                        DeletionActionKind.DISABLE_UNIT,
                        unit,
                        "disable exact enabled unit",
                    )
                )
        return actions

    def _unit_stop_action(self, unit: str, *, stop: set[str]) -> DeletionAction:
        pending = unit in stop
        return self._action(
            DeletionStage.QUIESCE,
            (DeletionDisposition.WOULD_APPLY if pending else DeletionDisposition.SATISFIED),
            (DeletionActionKind.STOP_UNIT if pending else DeletionActionKind.VERIFY_UNIT),
            unit,
            "stop exact active unit" if pending else "unit is already inactive",
        )

    def _binding_actions(self, owned: OwnedBindings) -> list[DeletionAction]:
        if not owned.receipt_present:
            return [
                self._action(
                    DeletionStage.UNBIND,
                    DeletionDisposition.SATISFIED,
                    DeletionActionKind.REMOVE_BINDING,
                    str(self._scribe.ownership_path),
                    "no Scribe ownership receipt is present",
                )
            ]
        actions = [
            self._action(
                DeletionStage.UNBIND,
                (DeletionDisposition.WOULD_APPLY if os.path.lexists(path) else DeletionDisposition.SATISFIED),
                DeletionActionKind.REMOVE_BINDING,
                str(path),
                "remove exact Scribe-owned binding source",
            )
            for path in (*owned.quadlet_sources, *owned.systemd_sources)
        ]
        actions.extend(
            (
                self._action(
                    DeletionStage.UNBIND,
                    DeletionDisposition.WOULD_APPLY,
                    DeletionActionKind.REMOVE_BINDING,
                    str(self._scribe.ownership_path),
                    "remove empty Scribe authority after daemon reload",
                ),
                self._action(
                    DeletionStage.UNBIND,
                    DeletionDisposition.WOULD_APPLY,
                    DeletionActionKind.RELOAD_MANAGER,
                    "systemctl --user daemon-reload",
                    "reload after the exact owned fileset is cleared",
                ),
            )
        )
        return actions

    def _tree_actions(
        self,
        *,
        storage_actions: tuple[DeletionAction, ...],
        storage_identity: BtrfsSubvolumeIdentity | None,
        root_authorized: bool,
    ) -> list[DeletionAction]:
        actions = self._source_checkout_blockers()
        storage_blocked = any(action.disposition is DeletionDisposition.BLOCKED for action in storage_actions)
        storage_deferred = any(action.disposition is DeletionDisposition.REQUIRES_ROOT for action in storage_actions)
        deferred_mounts: frozenset[Path] = (
            frozenset({self.paths.postgres_data})
            if storage_identity is not None and storage_deferred and not storage_blocked
            else frozenset[Path]()
        )
        for root in self.paths.dedicated_roots:
            inspection = self._trees.inspect(root, deferred_mounts=deferred_mounts)
            disposition = (
                DeletionDisposition.BLOCKED
                if not inspection.removable or (inspection.exists and not root_authorized)
                else (DeletionDisposition.WOULD_APPLY if inspection.exists else DeletionDisposition.SATISFIED)
            )
            actions.append(
                self._action(
                    DeletionStage.FILESYSTEM,
                    disposition,
                    DeletionActionKind.REMOVE_TREE,
                    str(root),
                    (
                        inspection.detail
                        if root_authorized or not inspection.exists
                        else "recursive removal lacks initialization-issued root authority"
                    ),
                )
            )
        return actions

    def _source_checkout_blockers(self) -> list[DeletionAction]:
        source = self.paths.source_checkout
        if source is None:
            return []
        return [
            self._action(
                DeletionStage.FILESYSTEM,
                DeletionDisposition.BLOCKED,
                DeletionActionKind.REMOVE_TREE,
                str(root),
                f"source checkout must be preserved but lies beneath this root: {source}",
            )
            for root in self.paths.dedicated_roots
            if is_within(source, root)
        ]

    def _runtime_preservation(self) -> DeletionAction:
        return self._action(
            DeletionStage.RUNTIME,
            DeletionDisposition.PRESERVE,
            DeletionActionKind.PRESERVE_RUNTIME,
            "Podman containers and pods",
            "no immutable runtime-object receipt exists; names and prefixes are not deletion authority",
        )

    def _secret_preservation(self) -> DeletionAction:
        return self._action(
            DeletionStage.SECRETS,
            DeletionDisposition.PRESERVE,
            DeletionActionKind.PRESERVE_SECRET,
            "Podman secrets",
            "no immutable creation receipt exists; referenced or same-name secrets remain operator-owned",
        )

    def _package_action(self) -> DeletionAction:
        source = self.paths.source_checkout
        target = str(source) if source is not None else "LychD package"
        detail = (
            "source checkout is explicitly outside deletion authority"
            if source is not None
            else "installer provenance is unavailable; package removal is not guessed"
        )
        return self._action(
            DeletionStage.PACKAGE,
            DeletionDisposition.PRESERVE,
            DeletionActionKind.PRESERVE_PACKAGE,
            target,
            detail,
        )

    @staticmethod
    def _action(
        stage: DeletionStage,
        disposition: DeletionDisposition,
        kind: DeletionActionKind,
        target: str,
        detail: str,
    ) -> DeletionAction:
        return DeletionAction(stage, disposition, kind, target, detail)


class DeletionExecutor:
    """Apply the safe prefix of one approved plan and replan after each stage."""

    def __init__(
        self,
        *,
        planner: DeletionPlanner,
        retirement: UnitRetirementPort,
        bindings: BindingCleanupPort,
        checkpoint: DeletionCheckpointStore,
        trees: ManagedTreeService,
        lock_factory: Callable[[], AbstractContextManager[object]] = LifecycleLock,
    ) -> None:
        """Bind effect ports; confirmation remains the caller's responsibility."""
        self._planner = planner
        self._retirement = retirement
        self._bindings = bindings
        self._checkpoint = checkpoint
        self._trees = trees
        self._lock_factory = lock_factory

    def execute(self, approved_fingerprint: str) -> DeletionResult:
        """Apply an unchanged plan until completion or the first safe barrier."""
        with self._lock_factory():
            current = self._planner.plan()
            if current.fingerprint != approved_fingerprint:
                msg = "Deletion plan changed after confirmation; no action was taken."
                raise LifecycleError(msg)
            return self._execute_locked(current)

    def _execute_locked(self, current: DeletionPlan) -> DeletionResult:
        applied: list[DeletionStage] = []
        if current.first_blocked_stage is not None:
            return DeletionResult(
                DeletionOutcome.BLOCKED,
                current,
                detail=("the confirmed plan contains a safety blocker; no deletion effect was applied"),
            )
        result = self._retire_units(current, applied)
        if result is not None:
            return result

        current = self._planner.plan()
        result = self._pre_unbind_barrier(current, applied)
        if result is not None:
            return result

        result = self._unbind(applied)
        if result is not None:
            return result

        result = self._remove_roots(applied)
        if result is not None:
            return result
        return self._finish(applied)

    def _retire_units(
        self,
        current: DeletionPlan,
        applied: list[DeletionStage],
    ) -> DeletionResult | None:
        if self._blocked_in(current, DeletionStage.QUIESCE):
            return DeletionResult(
                DeletionOutcome.BLOCKED,
                current,
                detail="exact unit authority could not be proven",
            )
        unit_plan = current.unit_plan
        if unit_plan is None or not (unit_plan.stop_units or unit_plan.disable_units):
            return None
        try:
            self._retirement.execute(unit_plan)
        except Exception as exc:  # noqa: BLE001 - return explicit partial progress
            return self._partial(
                applied,
                f"owned unit retirement did not complete: {exc}",
            )
        applied.append(DeletionStage.QUIESCE)
        converged = self._planner.plan()
        if self._pending_in(converged, DeletionStage.QUIESCE):
            return DeletionResult(
                DeletionOutcome.PARTIAL,
                converged,
                tuple(applied),
                "owned units did not converge to inactive and disabled",
            )
        return None

    def _pre_unbind_barrier(
        self,
        current: DeletionPlan,
        applied: list[DeletionStage],
    ) -> DeletionResult | None:
        if self._blocked_in(current, DeletionStage.STORAGE):
            return DeletionResult(
                DeletionOutcome.BLOCKED,
                current,
                tuple(applied),
                "storage safety could not be proven; bindings were retained",
            )
        if self._blocked_in(current, DeletionStage.FILESYSTEM):
            return DeletionResult(
                DeletionOutcome.BLOCKED,
                current,
                tuple(applied),
                "dedicated-root safety could not be proven; bindings were retained",
            )
        if current.requires_root:
            return self._checkpoint_and_pause(current, applied)
        return None

    def _checkpoint_and_pause(
        self,
        current: DeletionPlan,
        applied: list[DeletionStage],
    ) -> DeletionResult:
        identity = current.storage_identity
        if identity is None:
            return DeletionResult(
                DeletionOutcome.BLOCKED,
                current,
                tuple(applied),
                "privileged storage work lacks an attested identity",
            )
        try:
            self._checkpoint.record(identity)
        except LifecycleError as exc:
            return DeletionResult(
                DeletionOutcome.BLOCKED,
                current,
                tuple(applied),
                f"could not retain privileged-handoff evidence: {exc}",
            )
        return DeletionResult(
            DeletionOutcome.PARTIAL,
            self._planner.plan(),
            tuple(applied),
            "privileged storage handoff required; bindings and lifecycle evidence were retained",
        )

    def _unbind(self, applied: list[DeletionStage]) -> DeletionResult | None:
        binding_plan = self._bindings.plan_destroy()
        if binding_plan.blockers:
            return DeletionResult(
                DeletionOutcome.BLOCKED,
                self._planner.plan(),
                tuple(applied),
                "exact binding cleanup remains blocked after unit retirement",
            )
        if not binding_plan.mutates:
            return None
        try:
            self._bindings.destroy()
        except Exception as exc:  # noqa: BLE001 - retain resumable partial state
            return self._partial(
                applied,
                f"exact binding cleanup did not complete: {exc}",
            )
        applied.append(DeletionStage.UNBIND)
        current = self._planner.plan()
        if self._pending_in(current, DeletionStage.UNBIND):
            return DeletionResult(
                DeletionOutcome.PARTIAL,
                current,
                tuple(applied),
                "binding cleanup did not converge",
            )
        return None

    def _remove_roots(
        self,
        applied: list[DeletionStage],
    ) -> DeletionResult | None:
        for root in self._planner.paths.dedicated_roots:
            current = self._planner.plan()
            if self._blocked_in(current, DeletionStage.STORAGE) or current.requires_root:
                return DeletionResult(
                    DeletionOutcome.BLOCKED,
                    current,
                    tuple(applied),
                    "storage identity changed before dedicated-root deletion",
                )
            inspection = self._trees.inspect(root)
            if not inspection.removable:
                return DeletionResult(
                    DeletionOutcome.BLOCKED,
                    current,
                    tuple(applied),
                    f"dedicated root became unsafe: {root}: {inspection.detail}",
                )
            if not inspection.exists:
                continue
            identities = {identity.path: identity for identity in current.root_identities}
            expected_identity = identities.get(root)
            if expected_identity is None:
                return DeletionResult(
                    DeletionOutcome.BLOCKED,
                    current,
                    tuple(applied),
                    f"initialization-issued authority disappeared before removing {root}",
                )
            try:
                self._trees.remove(
                    root,
                    expected_identity=expected_identity,
                    final_entry=(
                        self._planner.paths.lifecycle_receipt if root == self._planner.paths.codex_root else None
                    ),
                )
            except LifecycleError as exc:
                return self._partial(
                    applied,
                    f"dedicated-root removal stopped safely: {exc}",
                )
            if DeletionStage.FILESYSTEM not in applied:
                applied.append(DeletionStage.FILESYSTEM)
        return None

    def _finish(self, applied: list[DeletionStage]) -> DeletionResult:
        final = self._planner.plan()
        if final.complete:
            return DeletionResult(
                DeletionOutcome.COMPLETE,
                final,
                tuple(applied),
                "all safely owned installation resources were removed or explicitly preserved",
            )
        outcome = DeletionOutcome.BLOCKED if final.first_blocked_stage is not None else DeletionOutcome.PARTIAL
        return DeletionResult(
            outcome,
            final,
            tuple(applied),
            "deletion stopped with remaining planned work",
        )

    def _partial(
        self,
        applied: list[DeletionStage],
        detail: str,
    ) -> DeletionResult:
        try:
            plan = self._planner.plan()
        except Exception:  # noqa: BLE001 - preserve the explicit effect failure
            plan = DeletionPlan(actions=())
        return DeletionResult(
            DeletionOutcome.PARTIAL,
            plan,
            tuple(applied),
            detail,
        )

    @staticmethod
    def _blocked_in(plan: DeletionPlan, stage: DeletionStage) -> bool:
        return any(action.disposition is DeletionDisposition.BLOCKED for action in plan.actions_for(stage))

    @staticmethod
    def _pending_in(plan: DeletionPlan, stage: DeletionStage) -> bool:
        pending = {
            DeletionDisposition.WOULD_APPLY,
            DeletionDisposition.BLOCKED,
            DeletionDisposition.REQUIRES_ROOT,
        }
        return any(action.disposition in pending for action in plan.actions_for(stage))


__all__ = (
    "BindingCleanupPort",
    "BtrfsSubvolumeProbe",
    "CommandBtrfsSubvolumeProbe",
    "DedicatedRootAuthorityPort",
    "DeletionCheckpointStore",
    "DeletionExecutor",
    "DeletionPlanner",
    "ObservedBtrfsSubvolume",
    "ScribeOwnershipPort",
    "StorageInventoryPort",
    "UnitRetirementPort",
)
