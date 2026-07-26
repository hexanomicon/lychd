"""Effectful staged execution for one approved deletion plan."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path

import structlog

from lychd.system.interruptions import find_terminal_interruption
from lychd.system.services.lifecycle.deletion_checkpoint import (
    DeletionCheckpointStore,
)
from lychd.system.services.lifecycle.deletion_models import (
    DeletionDisposition,
    DeletionOutcome,
    DeletionPlan,
    DeletionResult,
    DeletionStage,
)
from lychd.system.services.lifecycle.deletion_planning import DeletionPlanner
from lychd.system.services.lifecycle.deletion_ports import (
    BindingCleanupPort,
    UnitRetirementPort,
)
from lychd.system.services.lifecycle.lock import LifecycleLock
from lychd.system.services.lifecycle.models import LifecycleError
from lychd.system.services.lifecycle.trees import ManagedTreeService

logger = structlog.get_logger()


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
            if terminal := find_terminal_interruption(exc):
                logger.warning(
                    "deletion_unbind_interrupted",
                    error_type=type(terminal).__name__,
                    applied=[stage.value for stage in applied],
                )
                terminal.add_note(
                    "LychD del was interrupted during exact binding cleanup; "
                    "some Scribe paths may already be removed or restored. "
                    "Rerun `lychd del` to replan from durable ownership evidence."
                )
                raise terminal from None
            return self._partial(
                applied,
                f"exact binding cleanup did not complete: {exc}",
            )
        except BaseException as exc:
            logger.warning(
                "deletion_unbind_interrupted",
                error_type=type(exc).__name__,
                applied=[stage.value for stage in applied],
            )
            exc.add_note(
                "LychD del was interrupted during exact binding cleanup; "
                "rerun `lychd del` to replan from durable ownership evidence."
            )
            raise
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
                    final_entries=self._final_tree_entries(root),
                )
            except LifecycleError as exc:
                if terminal := find_terminal_interruption(exc):
                    logger.warning(
                        "deletion_tree_interrupted",
                        root=str(root),
                        error_type=type(terminal).__name__,
                        detail=str(exc),
                        applied=[stage.value for stage in applied],
                    )
                    terminal.add_note(
                        f"LychD del stopped during dedicated-root retirement: {exc}. "
                        "Rerun `lychd del` after reconciling any named recovery path."
                    )
                    raise terminal from None
                return self._partial(
                    applied,
                    f"dedicated-root removal stopped safely: {exc}",
                )
            if DeletionStage.FILESYSTEM not in applied:
                applied.append(DeletionStage.FILESYSTEM)
        return None

    def _final_tree_entries(self, root: Path) -> tuple[Path, ...]:
        """Keep recovery authorities behind ordinary Codex entries."""
        if root != self._planner.paths.codex_root:
            return ()
        checkpoint = (self._checkpoint.path,) if self._checkpoint.exists else ()
        return (*checkpoint, self._planner.paths.lifecycle_receipt)

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


__all__ = ("DeletionExecutor",)
