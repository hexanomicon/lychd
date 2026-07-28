"""Cross-site Scribe transaction orchestration and failure classification."""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Never, cast

import structlog

from lychd.system.binding_sites import AttestedBindingSites
from lychd.system.descriptor_settlement import DescriptorSet, FailureLedger
from lychd.system.interruptions import (
    find_terminal_interruption,
    iter_exception_graph,
)
from lychd.system.services.scribe.authority import AUTHORITY_MODE, BindingAuthority
from lychd.system.services.scribe.errors import (
    ScribeGenerationError,
    ScribeTransactionError,
    ScribeTransactionState,
)
from lychd.system.services.scribe.models import BindingWriteSet, OwnershipManifest, SitePlan
from lychd.system.services.scribe.planning import validate_plans
from lychd.system.services.scribe.storage import (
    AtomicMutation,
    AtomicOutcome,
    AtomicPathStorage,
    AttestedPath,
    PathDriftError,
    PathState,
    PathStateIndeterminateError,
    PinnedPath,
    capture_path_state,
    capture_pinned_path_state,
)
from lychd.system.services.scribe.workspace import (
    TransactionWorkspace,
    WorkspaceParentIdentityError,
)

logger = structlog.get_logger()


def _collect_recovery_paths(
    *errors: BaseException | None,
) -> tuple[Path, ...]:
    """Collect exact operator-visible paths across nested settlement evidence."""
    paths: list[Path] = []
    for error in errors:
        if error is None:
            continue
        for candidate in iter_exception_graph(error):
            recovery_paths: object = getattr(candidate, "recovery_paths", ())
            if not isinstance(recovery_paths, tuple):
                continue
            paths.extend(path for path in cast("tuple[object, ...]", recovery_paths) if isinstance(path, Path))
    return tuple(dict.fromkeys(paths))


def _site_attestation_ledger(
    path: Path,
    *,
    indeterminate: bool,
) -> FailureLedger:
    """Bind descriptor settlement to the correct Scribe site-state type."""

    def error_factory(
        message: str,
        *,
        failures: tuple[BaseException, ...],
        outcome: str,
        verified: bool,
    ) -> BaseException:
        if indeterminate:
            return PathStateIndeterminateError(
                message,
                paths=frozenset({path}),
                cause=failures[0] if failures else None,
                failures=failures,
                outcome=outcome,
                verified=verified,
            )
        return ScribeGenerationError(
            message,
            failures=failures,
            outcome=outcome,
            verified=verified,
        )

    return FailureLedger(
        error_factory=error_factory,
        subject="Scribe binding-site attestation",
    )


@dataclass(frozen=True)
class _PreparedPath:
    """One pinned target, its pre-state, staging object, and rollback name."""

    target: PinnedPath
    before: PathState | None
    staged: AttestedPath | None
    quarantine: PinnedPath


@dataclass
class _PreparedCommit:
    """Pinned directories and complete per-path transaction preparations."""

    workspaces: dict[Path, TransactionWorkspace]
    sites: dict[tuple[Path, str], _PreparedPath]
    authority: _PreparedPath | None


def _collect_workspace_recovery(
    prepared: _PreparedCommit,
) -> tuple[tuple[Path, ...], tuple[BaseException, ...]]:
    """Resolve retained workspaces once without letting observation replace truth."""
    paths: list[Path] = []
    failures: list[BaseException] = []
    for workspace in prepared.workspaces.values():
        try:
            recovery_path = workspace.recovery_path()
        except BaseException as exc:  # noqa: BLE001 - lexical path remains safe evidence
            failures.append(exc)
            paths.append(workspace.path)
        else:
            paths.append(recovery_path)
    return tuple(dict.fromkeys(paths)), tuple(failures)


@dataclass
class _CommitProgress:
    """Proven mutations and paths whose post-attempt state is not classifiable."""

    mutations: list[AtomicMutation] = field(default_factory=list)
    indeterminate_paths: set[Path] = field(default_factory=set)
    retain_recovery_evidence: bool = False


class BindingTransaction:
    """Apply one validated write set through descriptor-pinned transitions."""

    def __init__(
        self,
        authority: BindingAuthority,
        *,
        expected_sites: AttestedBindingSites | None = None,
    ) -> None:
        """Bind commits to the receipt that grants their exact authority."""
        self._authority = authority
        self._storage = AtomicPathStorage()
        self._expected_sites = (
            {site.path: site for site in expected_sites.identities} if expected_sites is not None else {}
        )

    def commit(
        self,
        write_set: BindingWriteSet,
        *,
        expected_generation: str | None = None,
        expected_desired_generation: str | None = None,
        release_empty_authority: bool = False,
    ) -> str:
        """Apply one generation and optionally remove its empty authority receipt."""
        plans = write_set.plans
        validate_plans(plans)
        self._validate_release_request(
            write_set.ownership,
            release_empty_authority=release_empty_authority,
            expected_generation=expected_generation,
        )
        self._require_generation(
            write_set,
            expected=expected_generation,
            expected_desired=expected_desired_generation,
        )
        self._require_expected_sites_now()
        if not self._mutates(
            write_set,
            release_empty_authority=release_empty_authority,
        ):
            observed_generation = self._authority.observed_generation(plans)
            self._require_expected_sites_now()
            return observed_generation

        prepared = self._prepare_commit(
            write_set,
            release_empty_authority=release_empty_authority,
        )
        progress = _CommitProgress()
        committed_generation = ""
        try:
            validate_plans(plans)
            self._require_generation(
                write_set,
                expected=expected_generation,
                expected_desired=expected_desired_generation,
            )
            self._require_namespaces(prepared, indeterminate=False)
            self._apply_sites(plans, prepared=prepared, progress=progress)
            self._apply_authority(
                write_set,
                prepared=prepared,
                progress=progress,
                release_empty_authority=release_empty_authority,
            )
            self._require_namespaces(prepared, indeterminate=True)
            try:
                committed_generation = self._authority.observed_generation(plans)
            except BaseException:
                self._require_namespaces(
                    prepared,
                    indeterminate=bool(progress.mutations),
                )
                raise
            self._require_namespaces(prepared, indeterminate=True)
            self._require_expected_sites_now(
                indeterminate=bool(progress.mutations),
            )
            if release_empty_authority:
                self._require_release_sources_unchanged(write_set)
        except PathDriftError as exc:
            error = ScribeGenerationError(str(exc))
            self._raise_transaction_failure(error, progress=progress, prepared=prepared)
        except PathStateIndeterminateError as exc:
            progress.indeterminate_paths.update(exc.paths)
            self._raise_transaction_failure(exc, progress=progress, prepared=prepared)
        except BaseException as exc:  # noqa: BLE001 - rollback covers interrupts after mutation
            self._raise_transaction_failure(exc, progress=progress, prepared=prepared)
        finally:
            self._settle_commit_workspaces(
                prepared,
                progress=progress,
                committed_generation=committed_generation,
                active_error=sys.exception(),
            )
        return committed_generation

    def _apply_sites(
        self,
        plans: Sequence[SitePlan],
        *,
        prepared: _PreparedCommit,
        progress: _CommitProgress,
    ) -> None:
        """Apply changed desired files and stale removals at each site."""
        for plan in plans:
            desired_mutated = self._apply_desired_files(
                plan,
                prepared=prepared,
                progress=progress,
            )
            stale_mutated = self._remove_stale_files(
                plan,
                prepared=prepared,
                progress=progress,
            )
            if desired_mutated or stale_mutated:
                self._fsync_directory(prepared.workspaces[plan.directory])
                self._require_namespaces(prepared, indeterminate=True)

    def _apply_desired_files(
        self,
        plan: SitePlan,
        *,
        prepared: _PreparedCommit,
        progress: _CommitProgress,
    ) -> bool:
        """Install changed desired files through no-overwrite or exchange."""
        mutated = False
        for name, content in sorted(plan.files.items()):
            item = prepared.sites[(plan.directory, name)]
            self._require_pre_state(item, prepared=prepared, progress=progress)
            if item.before is not None and item.before.content == content:
                continue
            staged = item.staged
            if staged is None:  # pragma: no cover - preparation invariant
                message = f"Scribe staging file is absent for {item.target}."
                raise RuntimeError(message)
            outcome = self._storage.replace(
                staged,
                item.target,
                expected_before=item.before,
                rollback_quarantine=item.quarantine,
            )
            self._record_outcome(outcome, prepared=prepared, progress=progress)
            mutated = True
        return mutated

    def _remove_stale_files(
        self,
        plan: SitePlan,
        *,
        prepared: _PreparedCommit,
        progress: _CommitProgress,
    ) -> bool:
        """Quarantine stale exact-owned paths rather than unlinking them."""
        mutated = False
        for name in sorted(plan.previous_names - frozenset(plan.files)):
            item = prepared.sites[(plan.directory, name)]
            self._require_pre_state(item, prepared=prepared, progress=progress)
            if item.before is None:
                continue
            outcome = self._storage.remove(
                item.target,
                item.quarantine,
                expected_before=item.before,
            )
            self._record_outcome(outcome, prepared=prepared, progress=progress)
            mutated = True
        return mutated

    def _apply_authority(
        self,
        write_set: BindingWriteSet,
        *,
        prepared: _PreparedCommit,
        progress: _CommitProgress,
        release_empty_authority: bool,
    ) -> None:
        """Commit or transactionally remove the exact authority receipt."""
        item = prepared.authority
        if item is None:  # pragma: no cover - preparation invariant
            message = "Scribe authority preparation is absent."
            raise RuntimeError(message)
        self._require_pre_state(item, prepared=prepared, progress=progress)
        if release_empty_authority:
            if item.before is None:
                return
            outcome = self._storage.remove(
                item.target,
                item.quarantine,
                expected_before=item.before,
                authority=True,
            )
            self._record_outcome(outcome, prepared=prepared, progress=progress)
            self._fsync_directory(prepared.workspaces[self._authority.path.parent])
            self._require_namespaces(prepared, indeterminate=True)
            return

        desired = self._authority.encode(write_set.ownership)
        if item.before is not None and item.before.content == desired:
            return
        staged = item.staged
        if staged is None:  # pragma: no cover - preparation invariant
            message = "Scribe authority staging file is absent."
            raise RuntimeError(message)
        outcome = self._storage.replace(
            staged,
            item.target,
            expected_before=item.before,
            rollback_quarantine=item.quarantine,
            authority=True,
        )
        self._record_outcome(outcome, prepared=prepared, progress=progress)
        self._validate_authority_state(
            item.target,
            self._require_state(outcome.mutation.after, item.target),
        )
        self._fsync_directory(prepared.workspaces[self._authority.path.parent])
        self._require_namespaces(prepared, indeterminate=True)

    def _record_outcome(
        self,
        outcome: AtomicOutcome,
        *,
        prepared: _PreparedCommit,
        progress: _CommitProgress,
    ) -> None:
        """Record a proven mutation before any later check can fail."""
        progress.mutations.append(outcome.mutation)
        self._set_quarantine_identity(
            prepared,
            outcome.mutation,
            state=outcome.mutation.before,
        )
        self._require_namespaces(prepared, indeterminate=True)
        if outcome.adapter_error is not None:
            raise outcome.adapter_error

    def _mutates(
        self,
        write_set: BindingWriteSet,
        *,
        release_empty_authority: bool,
    ) -> bool:
        """Return whether the exact write set changes a live source or receipt."""
        for plan in write_set.plans:
            for name, content in plan.files.items():
                current = capture_path_state(plan.directory / name)
                if current is None or current.content != content:
                    return True
            stale_names = plan.previous_names - frozenset(plan.files)
            if any(capture_path_state(plan.directory / name) is not None for name in stale_names):
                return True
        authority_state = capture_path_state(self._authority.path)
        if release_empty_authority:
            return authority_state is not None
        if authority_state is None:
            return True
        return authority_state.content != self._authority.encode(write_set.ownership)

    def _require_generation(
        self,
        write_set: BindingWriteSet,
        *,
        expected: str | None,
        expected_desired: str | None,
    ) -> None:
        """CAS both the planner's full receipt snapshot and any caller token."""
        observed_authority, observed_generation = self._authority.observe(
            write_set.base.sources,
        )
        if observed_authority != write_set.base.authority or observed_generation != write_set.base.generation:
            message = "Binding authority changed after planning; refusing stale Scribe commit."
            raise ScribeGenerationError(message)
        if expected is not None and observed_generation != expected:
            message = "Binding generation changed after planning; refusing Scribe commit."
            raise ScribeGenerationError(message)
        if expected_desired is not None and self._authority.desired_generation(write_set) != expected_desired:
            message = "Desired binding bytes changed after planning; refusing Scribe commit."
            raise ScribeGenerationError(message)

    def _require_release_sources_unchanged(
        self,
        write_set: BindingWriteSet,
    ) -> None:
        """Keep every recorded source at its approved state through authority release."""
        observed_generation = self._authority.generation(
            authority=write_set.base.authority,
            sources=write_set.base.sources,
        )
        if observed_generation == write_set.base.generation:
            return
        message = "Recorded binding sources changed during Scribe authority release; restoring the authority receipt."
        raise ScribeGenerationError(message)

    @staticmethod
    def _validate_release_request(
        ownership: OwnershipManifest,
        *,
        release_empty_authority: bool,
        expected_generation: str | None,
    ) -> None:
        """Allow receipt deletion only for an explicitly empty next authority."""
        if not release_empty_authority:
            return
        if expected_generation is None:
            message = "Scribe authority release requires an exact observed generation."
            raise ValueError(message)
        if ownership.quadlet or ownership.systemd:
            message = "Scribe cannot release a non-empty binding authority."
            raise ValueError(message)

    def _prepare_commit(
        self,
        write_set: BindingWriteSet,
        *,
        release_empty_authority: bool,
    ) -> _PreparedCommit:
        """Prepare all staged objects before the first live mutation."""
        prepared = _PreparedCommit(workspaces={}, sites={}, authority=None)
        try:
            directories = {
                *(plan.directory for plan in write_set.plans),
                self._authority.path.parent,
            }
            for directory in sorted(directories, key=os.fsencode):
                workspace = self._create_workspace(directory)
                prepared.workspaces[directory] = workspace
            self._prepare_site_files(write_set.plans, prepared=prepared)
            workspace = prepared.workspaces[self._authority.path.parent]
            target = workspace.parent_entry(self._authority.path.name)
            before = self._capture_regular_state(target, role="authority")
            staged = (
                None
                if release_empty_authority
                else workspace.prepare_file(
                    self._authority.encode(write_set.ownership),
                    mode=AUTHORITY_MODE,
                    prefix="manifest-new-",
                )
            )
            prepared.authority = _PreparedPath(
                target=target,
                before=before,
                staged=staged,
                quarantine=workspace.reserve(prefix="manifest-quarantine-"),
            )
        except BaseException as primary:
            cleanup_errors = self._dispose_workspaces(prepared, retain=False)
            outcome = ScribeTransactionError(
                "Scribe preparation failed after every private workspace was settled.",
                state=ScribeTransactionState.ROLLED_BACK,
                forward_error=primary,
                cleanup_errors=cleanup_errors,
                recovery_paths=_collect_recovery_paths(
                    primary,
                    *cleanup_errors,
                ),
            )
            terminal = find_terminal_interruption(outcome)
            if terminal is not None:
                self._raise_terminal_with_cleanup_outcome(
                    terminal,
                    outcome=outcome,
                    note=(
                        "Scribe settled every prepared workspace after cleanup "
                        "interruption; no live binding mutation had begun."
                    ),
                )
            if cleanup_errors:
                raise outcome from primary
            raise
        else:
            return prepared

    def _prepare_site_files(
        self,
        plans: Sequence[SitePlan],
        *,
        prepared: _PreparedCommit,
    ) -> None:
        """Capture pre-states and stage desired bytes through pinned descriptors."""
        for plan in plans:
            workspace = prepared.workspaces[plan.directory]
            names = plan.previous_names | frozenset(plan.files)
            for name in sorted(names):
                target = workspace.parent_entry(name)
                staged = (
                    workspace.prepare_file(
                        plan.files[name],
                        mode=0o644,
                        prefix="new-",
                    )
                    if name in plan.files
                    else None
                )
                prepared.sites[(plan.directory, name)] = _PreparedPath(
                    target=target,
                    before=self._capture_regular_state(target, role="binding"),
                    staged=staged,
                    quarantine=workspace.reserve(prefix="quarantine-"),
                )

    @staticmethod
    def _capture_regular_state(path: PinnedPath, *, role: str) -> PathState | None:
        """Capture one absent or regular path and reject every other file kind."""
        state = capture_pinned_path_state(path)
        if state is None or state.content is not None:
            return state
        message = f"Scribe {role} path is not a regular file: {path}."
        raise RuntimeError(message)

    def _raise_transaction_failure(
        self,
        error: BaseException,
        *,
        progress: _CommitProgress,
        prepared: _PreparedCommit,
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
                workspace_recovery_paths,
                recovery_observation_errors,
            ) = _collect_workspace_recovery(prepared)
            rendered_paths = ", ".join(str(path) for path in workspace_recovery_paths)
            recovery = f" Recovery evidence was retained at: {rendered_paths}."
        if indeterminate and rollback_error is None:
            message = (
                f"Scribe binding failed ({error!r}); proven mutations were rolled back, "
                f"but at least one attempted path remains indeterminate.{recovery}"
            )
        elif rollback_error is None:
            message = f"Scribe binding failed ({error!r}); exact mutations were rolled back."
        else:
            message = (
                f"Scribe binding failed ({error!r}) and exact rollback failed or was "
                f"interrupted ({rollback_error!r}).{recovery}"
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
                        *_collect_recovery_paths(error, rollback_error),
                    )
                )
            ),
        ) from (terminal_cause or error)

    def _rollback(
        self,
        mutations: Sequence[AtomicMutation],
        *,
        prepared: _PreparedCommit,
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
                self._validate_authority_state(mutation.target, mutation.before)
            os.fsync(mutation.target.directory_fd)

    @staticmethod
    def _set_quarantine_identity(
        prepared: _PreparedCommit,
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

    def _require_pre_state(
        self,
        item: _PreparedPath,
        *,
        prepared: _PreparedCommit,
        progress: _CommitProgress,
    ) -> None:
        """Reject namespace or path drift immediately before one transition."""
        self._require_namespaces(
            prepared,
            indeterminate=bool(progress.mutations),
        )
        if capture_pinned_path_state(item.target) == item.before:
            return
        message = f"Binding path changed after Scribe preparation; refusing commit: {item.target}."
        raise ScribeGenerationError(message)

    @staticmethod
    def _require_namespaces(
        prepared: _PreparedCommit,
        *,
        indeterminate: bool,
    ) -> None:
        """Require public names to keep identifying every pinned directory."""
        drifted = frozenset(
            path for workspace in prepared.workspaces.values() for path in workspace.namespace_drift_paths()
        )
        if not drifted:
            return
        rendered = ", ".join(str(path) for path in sorted(drifted, key=os.fsencode))
        message = f"Scribe directory identity changed during commit: {rendered}."
        if indeterminate:
            raise PathStateIndeterminateError(message, paths=drifted)
        raise PathDriftError(message)

    def _validate_authority_state(self, path: PinnedPath, state: PathState) -> None:
        """Validate receipt type, owner, and mode from the pinned observation."""
        self._authority.validate_metadata(
            path.display,
            mode=state.mode,
            user_id=state.user_id,
        )

    def _create_workspace(self, directory: Path) -> TransactionWorkspace:
        """Pin and verify a site before creating any transaction entry."""
        expected = self._expected_sites.get(directory)
        expected_identity = (expected.device, expected.inode) if expected is not None else None
        try:
            return TransactionWorkspace.create(
                directory,
                expected_parent_identity=expected_identity,
            )
        except WorkspaceParentIdentityError as exc:
            message = f"Binding-site identity changed after foundation approval; refusing Scribe commit: {directory}."
            raise ScribeGenerationError(message) from exc

    def _require_expected_sites_now(
        self,
        *,
        indeterminate: bool = False,
    ) -> None:
        """Re-attest approved site identities before every successful return."""
        for expected in self._expected_sites.values():
            descriptors = DescriptorSet()
            primary: BaseException | None = None
            try:
                descriptor = descriptors.add(
                    os.open(
                        expected.path,
                        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
                    )
                )
                metadata = os.fstat(descriptor)
                if metadata.st_dev != expected.device or metadata.st_ino != expected.inode:
                    message = (
                        f"Binding-site identity changed after foundation approval; "
                        f"refusing Scribe commit: {expected.path}."
                    )
                    primary = self._site_attestation_error(
                        message,
                        path=expected.path,
                        indeterminate=indeterminate,
                    )
            except BaseException as exc:  # noqa: BLE001 - descriptor close remains a peer
                message = (
                    "Binding site became unavailable after foundation approval; "
                    f"refusing Scribe commit: {expected.path}."
                )
                primary = self._site_attestation_error(
                    message,
                    path=expected.path,
                    indeterminate=indeterminate,
                    cause=exc,
                )
            settlement = _site_attestation_ledger(
                expected.path,
                indeterminate=indeterminate,
            )
            if primary is not None:
                settlement.record(primary)
            settlement.record_all(descriptors.settle())
            settlement.raise_if_any(
                message=(
                    str(primary)
                    if primary is not None
                    else f"Scribe binding-site attestation settled with failures for {expected.path}."
                ),
                outcome=("indeterminate" if indeterminate else "unchanged"),
                terminal_note=(
                    f"Scribe settled the approved-site descriptor for {expected.path} without mutating the filesystem."
                ),
                verified=not indeterminate,
            )

    @staticmethod
    def _site_attestation_error(
        message: str,
        *,
        path: Path,
        indeterminate: bool,
        cause: BaseException | None = None,
    ) -> BaseException:
        """Construct approved-site drift for the current mutation boundary."""
        if indeterminate:
            error: BaseException = PathStateIndeterminateError(
                message,
                paths=frozenset({path}),
                cause=cause,
            )
        else:
            error = ScribeGenerationError(message)
        if cause is not None:
            error.__cause__ = cause
        return error

    @staticmethod
    def _require_state(state: PathState | None, target: PinnedPath) -> PathState:
        if state is not None:
            return state
        message = f"Missing required Scribe path state for {target}."
        raise RuntimeError(message)

    @staticmethod
    def _fsync_directory(workspace: TransactionWorkspace) -> None:
        """Persist one site through the descriptor pinned during preparation."""
        workspace.fsync_parent()

    @staticmethod
    def _dispose_workspaces(
        prepared: _PreparedCommit,
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
        prepared: _PreparedCommit,
        *,
        progress: _CommitProgress,
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
                            f"preserving this interruption; public binding state "
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
                    f"interruption; public binding state is {outcome.state.value}."
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
                settled.cleanup_errors = (*settled.cleanup_errors, *cleanup_errors)
                settled.recovery_paths = tuple(
                    dict.fromkeys(
                        (
                            *settled.recovery_paths,
                            *_collect_recovery_paths(*cleanup_errors),
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
                recovery_paths=_collect_recovery_paths(
                    active_error,
                    *cleanup_errors,
                ),
            )
        return ScribeTransactionError(
            "Scribe commit succeeded, but transaction workspace cleanup was interrupted.",
            state=ScribeTransactionState.COMMITTED,
            generation=committed_generation,
            cleanup_errors=cleanup_errors,
            recovery_paths=_collect_recovery_paths(*cleanup_errors),
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
            outcome.cleanup_errors = (*outcome.cleanup_errors, prior_cause)
        terminal.add_note(note)
        raise terminal from outcome
