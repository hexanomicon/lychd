"""CAS, preparation, and binding-site attestation for Scribe commits."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Never

from lychd.system.binding_sites import AttestedBindingSite
from lychd.system.descriptor_settlement import DescriptorSet, FailureLedger
from lychd.system.interruptions import find_terminal_interruption
from lychd.system.services.scribe.authority import (
    AUTHORITY_MODE,
    BindingAuthority,
)
from lychd.system.services.scribe.errors import (
    ScribeGenerationError,
    ScribeTransactionError,
    ScribeTransactionState,
)
from lychd.system.services.scribe.models import (
    BindingWriteSet,
    OwnershipManifest,
    SitePlan,
)
from lychd.system.services.scribe.storage import (
    AtomicPathStorage,
    PathDriftError,
    PathState,
    PathStateIndeterminateError,
    PinnedPath,
    capture_path_state,
    capture_pinned_path_state,
)
from lychd.system.services.scribe.transaction_state import (
    CommitProgress,
    PreparedCommit,
    PreparedPath,
    collect_recovery_paths,
)
from lychd.system.services.scribe.workspace import (
    TransactionWorkspace,
    WorkspaceParentIdentityError,
)


def site_attestation_ledger(
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


class TransactionPreflightMixin:
    """Validate and prepare all state before a Scribe live mutation."""

    _authority: BindingAuthority
    _storage: AtomicPathStorage
    _expected_sites: dict[Path, AttestedBindingSite]

    if TYPE_CHECKING:

        @staticmethod
        def _dispose_workspaces(
            prepared: PreparedCommit,
            *,
            retain: bool,
        ) -> tuple[BaseException, ...]:
            """Settle every prepared workspace."""
            raise NotImplementedError

        @staticmethod
        def _raise_terminal_with_cleanup_outcome(
            terminal: BaseException,
            *,
            outcome: ScribeTransactionError,
            note: str,
        ) -> Never:
            """Resurface a native terminal with settlement evidence."""
            raise NotImplementedError

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
    ) -> PreparedCommit:
        """Prepare all staged objects before the first live mutation."""
        prepared = PreparedCommit(workspaces={}, sites={}, authority=None)
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
            prepared.authority = PreparedPath(
                target=target,
                before=before,
                staged=staged,
                quarantine=workspace.reserve(prefix="manifest-quarantine-"),
            )
        except BaseException as primary:
            cleanup_errors = self._dispose_workspaces(
                prepared,
                retain=False,
            )
            outcome = ScribeTransactionError(
                "Scribe preparation failed after every private workspace was settled.",
                state=ScribeTransactionState.ROLLED_BACK,
                forward_error=primary,
                cleanup_errors=cleanup_errors,
                recovery_paths=collect_recovery_paths(
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
        prepared: PreparedCommit,
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
                prepared.sites[(plan.directory, name)] = PreparedPath(
                    target=target,
                    before=self._capture_regular_state(
                        target,
                        role="binding",
                    ),
                    staged=staged,
                    quarantine=workspace.reserve(prefix="quarantine-"),
                )

    @staticmethod
    def _capture_regular_state(
        path: PinnedPath,
        *,
        role: str,
    ) -> PathState | None:
        """Capture one absent or regular path and reject every other file kind."""
        state = capture_pinned_path_state(path)
        if state is None or state.content is not None:
            return state
        message = f"Scribe {role} path is not a regular file: {path}."
        raise RuntimeError(message)

    def _require_pre_state(
        self,
        item: PreparedPath,
        *,
        prepared: PreparedCommit,
        progress: CommitProgress,
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
        prepared: PreparedCommit,
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

    def _validate_authority_state(
        self,
        path: PinnedPath,
        state: PathState,
    ) -> None:
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
                        "Binding-site identity changed after foundation "
                        "approval; refusing Scribe commit: "
                        f"{expected.path}."
                    )
                    primary = self._site_attestation_error(
                        message,
                        path=expected.path,
                        indeterminate=indeterminate,
                    )
            except BaseException as exc:  # noqa: BLE001 - descriptor close remains a peer
                message = (
                    "Binding site became unavailable after foundation "
                    f"approval; refusing Scribe commit: {expected.path}."
                )
                primary = self._site_attestation_error(
                    message,
                    path=expected.path,
                    indeterminate=indeterminate,
                    cause=exc,
                )
            settlement = site_attestation_ledger(
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
                    else (f"Scribe binding-site attestation settled with failures for {expected.path}.")
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
    def _require_state(
        state: PathState | None,
        target: PinnedPath,
    ) -> PathState:
        if state is not None:
            return state
        message = f"Missing required Scribe path state for {target}."
        raise RuntimeError(message)

    @staticmethod
    def _fsync_directory(workspace: TransactionWorkspace) -> None:
        """Persist one site through the descriptor pinned during preparation."""
        workspace.fsync_parent()


__all__ = ("TransactionPreflightMixin",)
