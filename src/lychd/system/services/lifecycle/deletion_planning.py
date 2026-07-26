"""Zero-effect planning for staged, fail-closed installation deletion."""

from __future__ import annotations

import os
from pathlib import Path

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
    DeletionPaths,
    DeletionPlan,
    DeletionStage,
)
from lychd.system.services.lifecycle.deletion_ports import (
    BtrfsSubvolumeProbe,
    DedicatedRootAuthorityPort,
    ScribeOwnershipPort,
    StorageInventoryPort,
    UnitRetirementPort,
)
from lychd.system.services.lifecycle.deletion_storage import (
    DeletionStoragePlanner,
)
from lychd.system.services.lifecycle.models import (
    DedicatedRootIdentity,
)
from lychd.system.services.lifecycle.paths import is_within
from lychd.system.services.lifecycle.trees import ManagedTreeService
from lychd.system.services.scribe.models import OwnedBindings


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
            initialized_subvolumes=root_authority,
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
        deferred_subvolumes = deferred_mounts
        for root in self.paths.dedicated_roots:
            inspection = self._trees.inspect(
                root,
                deferred_mounts=deferred_mounts,
                deferred_subvolumes=deferred_subvolumes,
            )
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


__all__ = ("DeletionPlanner",)
