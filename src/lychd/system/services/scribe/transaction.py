"""Stable facade for cross-site Scribe transaction orchestration."""

from __future__ import annotations

import os  # compatibility seam for fault-injection tests
import sys
from collections.abc import Sequence
from pathlib import Path

from lychd.system.binding_sites import (
    AttestedBindingSite,
    AttestedBindingSites,
)
from lychd.system.descriptor_settlement import DescriptorSet
from lychd.system.services.scribe.authority import BindingAuthority
from lychd.system.services.scribe.errors import ScribeGenerationError
from lychd.system.services.scribe.models import BindingWriteSet, SitePlan
from lychd.system.services.scribe.planning import validate_plans
from lychd.system.services.scribe.storage import (
    AtomicOutcome,
    AtomicPathStorage,
    PathDriftError,
    PathStateIndeterminateError,
)
from lychd.system.services.scribe.transaction_preflight import (
    TransactionPreflightMixin,
)
from lychd.system.services.scribe.transaction_settlement import (
    TransactionSettlementMixin,
)
from lychd.system.services.scribe.transaction_state import (
    CommitProgress as _CommitProgress,
)
from lychd.system.services.scribe.transaction_state import (
    PreparedCommit as _PreparedCommit,
)


class BindingTransaction(
    TransactionPreflightMixin,
    TransactionSettlementMixin,
):
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
        self._expected_sites: dict[Path, AttestedBindingSite] = (
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
            self._apply_sites(
                plans,
                prepared=prepared,
                progress=progress,
            )
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
            self._raise_transaction_failure(
                error,
                progress=progress,
                prepared=prepared,
            )
        except PathStateIndeterminateError as exc:
            progress.indeterminate_paths.update(exc.paths)
            self._raise_transaction_failure(
                exc,
                progress=progress,
                prepared=prepared,
            )
        except BaseException as exc:  # noqa: BLE001 - rollback covers interrupts after mutation
            self._raise_transaction_failure(
                exc,
                progress=progress,
                prepared=prepared,
            )
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
                self._require_namespaces(
                    prepared,
                    indeterminate=True,
                )

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
            self._require_pre_state(
                item,
                prepared=prepared,
                progress=progress,
            )
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
            self._record_outcome(
                outcome,
                prepared=prepared,
                progress=progress,
            )
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
            self._require_pre_state(
                item,
                prepared=prepared,
                progress=progress,
            )
            if item.before is None:
                continue
            outcome = self._storage.remove(
                item.target,
                item.quarantine,
                expected_before=item.before,
            )
            self._record_outcome(
                outcome,
                prepared=prepared,
                progress=progress,
            )
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
        self._require_pre_state(
            item,
            prepared=prepared,
            progress=progress,
        )
        if release_empty_authority:
            if item.before is None:
                return
            outcome = self._storage.remove(
                item.target,
                item.quarantine,
                expected_before=item.before,
                authority=True,
            )
            self._record_outcome(
                outcome,
                prepared=prepared,
                progress=progress,
            )
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
        self._record_outcome(
            outcome,
            prepared=prepared,
            progress=progress,
        )
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


__all__ = (
    "BindingTransaction",
    "DescriptorSet",
    "os",
)
