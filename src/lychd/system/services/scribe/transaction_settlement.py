"""Rollback, recovery, and workspace settlement for Scribe commits."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Never

import structlog

from lychd.system.interruptions import (
    find_terminal_interruption,
    iter_exception_graph,
)
from lychd.system.services.scribe.errors import (
    ScribeTransactionError,
    ScribeTransactionState,
)
from lychd.system.services.scribe.storage import (
    AtomicMutation,
    AtomicPathStorage,
    PathDriftError,
    PathState,
    PinnedPath,
    capture_pinned_path_state,
)
from lychd.system.services.scribe.transaction_state import (
    CommitProgress,
    PreparedCommit,
    collect_recovery_paths,
    collect_workspace_recovery,
)

logger = structlog.get_logger()


class TransactionSettlementMixin:
    """Classify failures and settle every private transaction workspace."""

    _storage: AtomicPathStorage

    if TYPE_CHECKING:

        def _validate_authority_state(
            self,
            path: PinnedPath,
            state: PathState,
        ) -> None:
            """Validate a restored authority receipt."""
            raise NotImplementedError

    def _raise_transaction_failure(
        self,
        error: BaseException,
        *,
        progress: CommitProgress,
        prepared: PreparedCommit,
    ) -> Never:
        """Roll back proven transitions and classify the final binding state."""
        if not progress.mutations and not progress.indeterminate_paths:
            raise error

        # Once rollback begins, cleanup has no authority to discard evidence
        # until the entire reversal has completed and been classified.
        progress.retain_recovery_evidence = True
        rollback_error: BaseException | None = None
        try:
            self._rollback(progress.mutations, prepared=prepared)
        except BaseException as exc:  # noqa: BLE001 - interrupts make state indeterminate
            rollback_error = exc

        indeterminate = bool(progress.indeterminate_paths) or rollback_error is not None
        progress.retain_recovery_evidence = indeterminate
        state = ScribeTransactionState.INDETERMINATE if indeterminate else ScribeTransactionState.ROLLED_BACK
        recovery = ""
        workspace_recovery_paths: tuple[Path, ...] = ()
        recovery_observation_errors: tuple[BaseException, ...] = ()
        if indeterminate:
            (
                collected_paths,
                recovery_observation_errors,
            ) = collect_workspace_recovery(prepared)
            workspace_recovery_paths = collected_paths
            rendered_paths = ", ".join(str(path) for path in workspace_recovery_paths)
            recovery = f" Recovery evidence was retained at: {rendered_paths}."
        if indeterminate and rollback_error is None:
            message = (
                f"Scribe binding failed ({error!r}); proven mutations were "
                "rolled back, but at least one attempted path remains "
                f"indeterminate.{recovery}"
            )
        elif rollback_error is None:
            message = f"Scribe binding failed ({error!r}); exact mutations were rolled back."
        else:
            message = (
                f"Scribe binding failed ({error!r}) and exact rollback failed "
                f"or was interrupted ({rollback_error!r}).{recovery}"
            )
        terminal_cause = next(
            (
                candidate
                for candidate in (error, rollback_error)
                if candidate is not None and not isinstance(candidate, Exception)
            ),
            None,
        )
        raise ScribeTransactionError(
            message,
            state=state,
            forward_error=error,
            rollback_error=rollback_error,
            cleanup_errors=recovery_observation_errors,
            recovery_paths=tuple(
                dict.fromkeys(
                    (
                        *workspace_recovery_paths,
                        *collect_recovery_paths(error, rollback_error),
                    )
                )
            ),
        ) from (terminal_cause or error)

    def _rollback(
        self,
        mutations: Sequence[AtomicMutation],
        *,
        prepared: PreparedCommit,
    ) -> None:
        """Restore only exact pinned generations and persist every reversal."""
        for mutation in reversed(mutations):
            if capture_pinned_path_state(mutation.target) != mutation.after:
                message = f"Scribe rollback refused to clobber a concurrent edit at {mutation.target}."
                raise PathDriftError(message)
            expected_quarantine = mutation.before if mutation.before is not None else None
            if capture_pinned_path_state(mutation.quarantine) != expected_quarantine:
                message = f"Scribe rollback evidence changed at {mutation.quarantine}."
                raise PathDriftError(message)

        for mutation in reversed(mutations):
            self._storage.restore(mutation)
            self._set_quarantine_identity(
                prepared,
                mutation,
                state=mutation.after,
            )
            if mutation.authority and mutation.before is not None:
                self._validate_authority_state(
                    mutation.target,
                    mutation.before,
                )
            os.fsync(mutation.target.directory_fd)

    @staticmethod
    def _set_quarantine_identity(
        prepared: PreparedCommit,
        mutation: AtomicMutation,
        *,
        state: PathState | None,
    ) -> None:
        """Teach cleanup which exact object occupies a quarantine name."""
        workspace = next(
            (
                candidate
                for candidate in prepared.workspaces.values()
                if candidate.directory_fd == mutation.quarantine.directory_fd
            ),
            None,
        )
        if workspace is None:  # pragma: no cover - preparation invariant
            message = f"Scribe quarantine is outside every prepared workspace: {mutation.quarantine}."
            raise RuntimeError(message)
        if state is None:
            workspace.forget(mutation.quarantine)
            return
        workspace.claim(
            mutation.quarantine,
            device=state.device,
            inode=state.inode,
        )

    @staticmethod
    def _dispose_workspaces(
        prepared: PreparedCommit,
        *,
        retain: bool,
    ) -> tuple[BaseException, ...]:
        """Settle every workspace and return cleanup failures without masking peers."""
        failures: list[BaseException] = []
        for workspace in prepared.workspaces.values():
            try:
                if retain:
                    workspace.close()
                    continue
                workspace.cleanup()
            except BaseException as exc:  # noqa: BLE001 - settle every peer before surfacing
                failures.append(exc)
                logger.warning(
                    "scribe_transaction_cleanup_failed",
                    path=str(workspace.path),
                    error=str(exc),
                )
        return tuple(failures)

    def _settle_commit_workspaces(
        self,
        prepared: PreparedCommit,
        *,
        progress: CommitProgress,
        committed_generation: str,
        active_error: BaseException | None,
    ) -> None:
        """Surface every workspace-cleanup failure with exact public state."""
        cleanup_errors = self._dispose_workspaces(
            prepared,
            retain=progress.retain_recovery_evidence,
        )
        if not cleanup_errors:
            if active_error is not None:
                outcome = next(
                    (
                        candidate
                        for candidate in iter_exception_graph(active_error)
                        if isinstance(candidate, ScribeTransactionError)
                    ),
                    None,
                )
                causal_errors = (
                    tuple(
                        error
                        for error in (
                            outcome.forward_error,
                            outcome.rollback_error,
                        )
                        if error is not None
                    )
                    if outcome is not None
                    else ()
                )
                terminal = (
                    self._first_cleanup_terminal(
                        outcome.cleanup_errors,
                        excluding=causal_errors,
                    )
                    if outcome is not None
                    else None
                )
                if terminal is None and outcome is not None and outcome.rollback_error is None:
                    terminal = find_terminal_interruption(active_error)
                if outcome is not None and terminal is not None:
                    self._raise_terminal_with_cleanup_outcome(
                        terminal,
                        outcome=outcome,
                        note=(
                            "Scribe settled every transaction workspace before "
                            "preserving this interruption; public binding state "
                            f"is {outcome.state.value}."
                        ),
                    )
            return
        outcome = self._cleanup_outcome(
            active_error=active_error,
            committed_generation=committed_generation,
            cleanup_errors=cleanup_errors,
        )
        causal_errors = tuple(
            error
            for error in (
                outcome.forward_error,
                outcome.rollback_error,
            )
            if error is not None
        )
        terminal = self._first_cleanup_terminal(
            outcome.cleanup_errors,
            excluding=causal_errors,
        )
        if terminal is None and active_error is not None and outcome.rollback_error is None:
            terminal = find_terminal_interruption(active_error)
        if terminal is not None:
            self._raise_terminal_with_cleanup_outcome(
                terminal,
                outcome=outcome,
                note=(
                    "Scribe settled every transaction workspace after cleanup "
                    f"interruption; public binding state is "
                    f"{outcome.state.value}."
                ),
            )
        if outcome is not active_error:
            raise outcome from (active_error or cleanup_errors[0])

    @staticmethod
    def _first_cleanup_terminal(
        failures: tuple[BaseException, ...],
        *,
        excluding: tuple[BaseException, ...] = (),
    ) -> BaseException | None:
        """Find a native terminal only after every workspace was settled."""
        excluded: set[int] = {
            id(candidate)
            for error in excluding
            for candidate in iter_exception_graph(error)
            if not isinstance(candidate, Exception)
        }
        return next(
            (
                candidate
                for failure in failures
                for candidate in iter_exception_graph(failure)
                if not isinstance(candidate, Exception) and id(candidate) not in excluded
            ),
            None,
        )

    @staticmethod
    def _cleanup_outcome(
        *,
        active_error: BaseException | None,
        committed_generation: str,
        cleanup_errors: tuple[BaseException, ...],
    ) -> ScribeTransactionError:
        """Attach exact public truth to a native cleanup interruption."""
        if active_error is not None:
            settled = next(
                (
                    candidate
                    for candidate in iter_exception_graph(active_error)
                    if isinstance(candidate, ScribeTransactionError)
                ),
                None,
            )
            if settled is not None:
                settled.cleanup_errors = (
                    *settled.cleanup_errors,
                    *cleanup_errors,
                )
                settled.recovery_paths = tuple(
                    dict.fromkeys(
                        (
                            *settled.recovery_paths,
                            *collect_recovery_paths(*cleanup_errors),
                        )
                    )
                )
                return settled
        if active_error is not None:
            return ScribeTransactionError(
                "Scribe cleanup was interrupted after an unclassified transaction failure.",
                state=ScribeTransactionState.INDETERMINATE,
                forward_error=active_error,
                cleanup_errors=cleanup_errors,
                recovery_paths=collect_recovery_paths(
                    active_error,
                    *cleanup_errors,
                ),
            )
        return ScribeTransactionError(
            "Scribe commit succeeded, but transaction workspace cleanup was interrupted.",
            state=ScribeTransactionState.COMMITTED,
            generation=committed_generation,
            cleanup_errors=cleanup_errors,
            recovery_paths=collect_recovery_paths(*cleanup_errors),
        )

    @staticmethod
    def _raise_terminal_with_cleanup_outcome(
        terminal: BaseException,
        *,
        outcome: ScribeTransactionError,
        note: str,
    ) -> Never:
        """Preserve prior close evidence before attaching transaction progress."""
        prior_cause = terminal.__cause__
        if (
            prior_cause is not None
            and prior_cause is not outcome
            and all(prior_cause is not error for error in outcome.cleanup_errors)
        ):
            outcome.cleanup_errors = (
                *outcome.cleanup_errors,
                prior_cause,
            )
        terminal.add_note(note)
        raise terminal from outcome


__all__ = ("TransactionSettlementMixin",)
