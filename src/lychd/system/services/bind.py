"""Transactional bind use case over already-compiled host intent."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from enum import StrEnum
from typing import Never, Protocol

import structlog

from lychd.system.interruptions import find_terminal_interruption
from lychd.system.readiness import BindingFoundation
from lychd.system.schemas import QuadletBase
from lychd.system.services.scribe.errors import (
    ScribeGenerationError,
    ScribeTransactionError,
    ScribeTransactionState,
)
from lychd.system.services.scribe.models import BindingReconcilePlan

logger = structlog.get_logger()


class BindingPlanDriftError(RuntimeError):
    """Raised when an approved bind observation changes before mutation."""


class BindingRequirementError(RuntimeError):
    """Raised when externally supplied bind requirements are absent."""


class BindingCommitState(StrEnum):
    """What the bind use case can prove about Scribe-owned files."""

    NOT_ATTEMPTED = "not_attempted"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"
    INDETERMINATE = "indeterminate"
    COMMITTED = "committed"


@dataclass(frozen=True, slots=True)
class BindProgress:
    """Confirmed effects completed before a bind failure."""

    created_secrets: tuple[str, ...] = ()
    secret_reconciliation_indeterminate: bool = False
    binding_commit_state: BindingCommitState = BindingCommitState.NOT_ATTEMPTED
    binding_generation: str | None = None
    systemd_reloaded: bool = False

    def __post_init__(self) -> None:
        """Forbid claiming a generation without a confirmed commit."""
        committed = self.binding_commit_state is BindingCommitState.COMMITTED
        if committed != (self.binding_generation is not None):
            msg = "A binding generation is valid only for a confirmed commit."
            raise ValueError(msg)


class BindApplyError(RuntimeError):
    """A bind failed after zero or more confirmed effects."""

    def __init__(self, message: str, *, progress: BindProgress) -> None:
        """Retain exact confirmed progress alongside the operator message."""
        super().__init__(message)
        self.progress = progress


class BindingScribePort(Protocol):
    """Narrow Scribe surface required by one complete bind transaction."""

    def plan_reconcile_all(
        self,
        manifests: Sequence[QuadletBase],
        *,
        plain_units: Mapping[str, str],
    ) -> BindingReconcilePlan:
        """Inspect the complete desired binding generation."""
        ...

    def reconcile_all(
        self,
        manifests: Sequence[QuadletBase],
        *,
        plain_units: Mapping[str, str],
        expected_generation: str | None = None,
        expected_desired_generation: str | None = None,
    ) -> str:
        """Commit the complete desired binding generation and return its identity."""
        ...


class SecretStorePort(Protocol):
    """Secret operations required by binding."""

    def exists(self, name: str) -> bool:
        """Return whether one exact secret exists."""
        ...

    def ensure_present(self, name: str, value: str) -> bool:
        """Create one absent secret and report whether creation occurred."""
        ...


class SystemdReloadPort(Protocol):
    """The sole systemd effect owned by binding."""

    def daemon_reload(self) -> None:
        """Reload the user manager after a successful Scribe commit."""
        ...


@dataclass(frozen=True, slots=True)
class CoreSecret:
    """One LychD-owned secret whose value may be generated when absent."""

    name: str
    factory: Callable[[], str]


@dataclass(frozen=True, slots=True)
class BindRequest:
    """Immutable, already-compiled intent consumed by the bind transaction."""

    manifests: tuple[QuadletBase, ...]
    plain_units: tuple[tuple[str, str], ...]
    core_secrets: tuple[CoreSecret, ...]
    required_secret_names: tuple[str, ...]

    @classmethod
    def compile(
        cls,
        *,
        manifests: Sequence[QuadletBase],
        plain_units: Mapping[str, str],
        core_secret_factories: Mapping[str, Callable[[], str]],
        required_secret_names: Sequence[str],
    ) -> BindRequest:
        """Canonicalize caller-owned collections into deterministic intent."""
        core_names = tuple(sorted(core_secret_factories))
        if len(core_names) != len(set(core_names)):  # pragma: no cover - Mapping law
            msg = "Core secret names must be unique."
            raise ValueError(msg)
        required = tuple(sorted(set(required_secret_names)))
        overlap = sorted(set(core_names) & set(required))
        if overlap:
            msg = f"Secrets cannot be both generated and operator-supplied: {', '.join(overlap)}"
            raise ValueError(msg)
        return cls(
            manifests=tuple(manifests),
            plain_units=tuple(sorted(plain_units.items())),
            core_secrets=tuple(CoreSecret(name=name, factory=core_secret_factories[name]) for name in core_names),
            required_secret_names=required,
        )

    @property
    def secret_names(self) -> tuple[str, ...]:
        """Return every secret whose presence belongs to plan equality."""
        return tuple(
            sorted(
                {
                    *(secret.name for secret in self.core_secrets),
                    *self.required_secret_names,
                }
            )
        )

    def plain_unit_mapping(self) -> dict[str, str]:
        """Return a fresh mapping for the Scribe port."""
        return dict(self.plain_units)


@dataclass(frozen=True, slots=True)
class BindPlan:
    """Complete read-only observation approved before binding."""

    foundation: BindingFoundation
    bindings: BindingReconcilePlan
    observed_secrets: tuple[tuple[str, bool], ...]
    missing_core_secrets: tuple[str, ...]
    missing_required_secrets: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BindResult:
    """Effects completed by one bind transaction."""

    created_secrets: tuple[str, ...]
    binding_generation: str
    systemd_reloaded: bool


class BindUseCase:
    """Plan and commit one lock-serialized, generation-checked binding."""

    def __init__(
        self,
        *,
        scribe: BindingScribePort,
        secrets: SecretStorePort,
        systemd_factory: Callable[[], SystemdReloadPort],
        foundation: BindingFoundation,
        foundation_probe: Callable[[], BindingFoundation],
        lock_factory: Callable[[], AbstractContextManager[object]],
    ) -> None:
        """Bind the use case to narrow mutation and revalidation ports."""
        self._scribe = scribe
        self._secrets = secrets
        self._systemd_factory = systemd_factory
        self._foundation = foundation
        self._foundation_probe = foundation_probe
        self._lock_factory = lock_factory

    def plan(
        self,
        request: BindRequest,
    ) -> BindPlan:
        """Observe binding and secret generations without applying effects."""
        observed_secrets = self._observe_secrets(request.secret_names)
        presence = dict(observed_secrets)
        core_names = tuple(secret.name for secret in request.core_secrets)
        plan = BindPlan(
            foundation=self._foundation,
            bindings=self._scribe.plan_reconcile_all(
                request.manifests,
                plain_units=request.plain_unit_mapping(),
            ),
            observed_secrets=observed_secrets,
            missing_core_secrets=tuple(name for name in core_names if not presence[name]),
            missing_required_secrets=tuple(name for name in request.required_secret_names if not presence[name]),
        )
        logger.debug(
            "bind_plan_observed",
            binding_changes=len(plan.bindings.changes),
            secret_count=len(plan.observed_secrets),
            missing_core_secret_count=len(plan.missing_core_secrets),
            missing_required_secret_count=len(plan.missing_required_secrets),
        )
        return plan

    def apply(self, request: BindRequest, approved: BindPlan) -> BindResult:
        """Revalidate and commit the approved plan under the lifecycle lock."""
        self._require_external_secrets(approved)

        with self._lock_factory():
            self._require_approved_state(request, approved)
            created = self._reconcile_core_secrets(request, approved)
            self._require_secrets_at_commit(request, created=created)
            committed_generation = self._commit_bindings(
                request,
                approved,
                created=created,
            )
            self._reload_systemd(
                created=created,
                committed_generation=committed_generation,
            )
        return BindResult(
            created_secrets=created,
            binding_generation=committed_generation,
            systemd_reloaded=True,
        )

    @staticmethod
    def _require_external_secrets(approved: BindPlan) -> None:
        """Reject a plan whose operator-supplied secrets are absent."""
        if not approved.missing_required_secrets:
            return
        missing = ", ".join(approved.missing_required_secrets)
        msg = f"Missing required Podman secrets: {missing}"
        raise BindingRequirementError(msg)

    def _require_approved_state(
        self,
        request: BindRequest,
        approved: BindPlan,
    ) -> None:
        """Revalidate foundation, binding bytes, and secret presence under lock."""
        if approved.foundation != self._foundation:
            msg = "Approved bind plan belongs to a different host foundation; rerun `lychd bind`."
            raise BindingPlanDriftError(msg)
        if self._foundation_probe() != self._foundation:
            msg = "Trusted host foundation changed after planning; rerun `lychd bind`."
            raise BindingPlanDriftError(msg)
        current_bindings = self._scribe.plan_reconcile_all(
            request.manifests,
            plain_units=request.plain_unit_mapping(),
        )
        if current_bindings != approved.bindings:
            msg = "Binding state changed after planning; rerun `lychd bind`."
            raise BindingPlanDriftError(msg)
        if self._observe_secrets(request.secret_names) != approved.observed_secrets:
            msg = "Podman secret state changed after planning; rerun `lychd bind`."
            raise BindingPlanDriftError(msg)

    def _reconcile_core_secrets(
        self,
        request: BindRequest,
        approved: BindPlan,
    ) -> tuple[str, ...]:
        """Create only absent generated secrets and report confirmed effects."""
        core_by_name = {secret.name: secret for secret in request.core_secrets}
        created: list[str] = []
        for name in approved.missing_core_secrets:
            try:
                value = core_by_name[name].factory()
            except BaseException as exc:  # noqa: BLE001 - preserve cancellation and confirmed prior effects
                self._raise_partial(
                    "Core-secret value generation failed",
                    phase="core-secret-value",
                    progress=BindProgress(created_secrets=tuple(created)),
                    error=exc,
                )
            try:
                created_now = self._secrets.ensure_present(
                    name,
                    value,
                )
            except BaseException as exc:  # noqa: BLE001 - the adapter may have mutated before interruption
                progress = BindProgress(
                    created_secrets=tuple(created),
                    secret_reconciliation_indeterminate=True,
                )
                self._raise_partial(
                    "Core-secret reconciliation failed",
                    phase="core-secret",
                    progress=progress,
                    error=exc,
                )
            if created_now:
                created.append(name)
                logger.info("bind_core_secret_created", secret_name=name)
        return tuple(created)

    def _require_secrets_at_commit(
        self,
        request: BindRequest,
        *,
        created: tuple[str, ...],
    ) -> None:
        """Require every secret after generated-secret reconciliation."""
        missing = tuple(name for name, present in self._observe_secrets(request.secret_names) if not present)
        if not missing:
            return
        msg = f"Podman secrets disappeared before binding commit: {', '.join(missing)}"
        if not created:
            raise BindingPlanDriftError(msg)
        self._raise_partial(
            msg,
            phase="secret-revalidation",
            progress=BindProgress(created_secrets=created),
        )

    def _commit_bindings(
        self,
        request: BindRequest,
        approved: BindPlan,
        *,
        created: tuple[str, ...],
    ) -> str:
        """Commit the exact approved desired generation."""
        try:
            generation = self._scribe.reconcile_all(
                request.manifests,
                plain_units=request.plain_unit_mapping(),
                expected_generation=approved.bindings.observed_generation,
                expected_desired_generation=approved.bindings.desired_generation,
            )
        except ScribeGenerationError as exc:
            progress = BindProgress(
                created_secrets=created,
                binding_commit_state=BindingCommitState.REJECTED,
            )
            if created:
                self._raise_partial(
                    "Binding state changed during commit; rerun `lychd bind`",
                    phase="binding-cas",
                    progress=progress,
                    error=exc,
                )
            msg = "Binding state changed during commit; rerun `lychd bind`."
            raise BindingPlanDriftError(msg) from exc
        except ScribeTransactionError as exc:
            binding_state, generation, message = self._scribe_failure_progress(exc)
            terminal_cause = find_terminal_interruption(exc)
            if terminal_cause is not None:
                self._raise_partial(
                    message,
                    phase="binding-commit",
                    progress=BindProgress(
                        created_secrets=created,
                        binding_commit_state=binding_state,
                        binding_generation=generation,
                    ),
                    error=terminal_cause,
                )
            self._raise_partial(
                message,
                phase="binding-commit",
                progress=BindProgress(
                    created_secrets=created,
                    binding_commit_state=binding_state,
                    binding_generation=generation,
                ),
                error=exc,
            )
        except BaseException as exc:  # noqa: BLE001 - cancellation still carries effect truth
            cleanup_outcome = exc.__cause__
            if (
                isinstance(cleanup_outcome, ScribeTransactionError)
                and cleanup_outcome.state is ScribeTransactionState.COMMITTED
                and cleanup_outcome.generation is not None
            ):
                terminal = find_terminal_interruption(exc) or exc
                self._raise_partial(
                    "Binding commit succeeded, but Scribe workspace cleanup was interrupted",
                    phase="binding-cleanup",
                    progress=BindProgress(
                        created_secrets=created,
                        binding_commit_state=BindingCommitState.COMMITTED,
                        binding_generation=cleanup_outcome.generation,
                    ),
                    error=terminal,
                )
            self._raise_partial(
                "Binding commit failed with indeterminate binding state",
                phase="binding-commit",
                progress=BindProgress(
                    created_secrets=created,
                    binding_commit_state=BindingCommitState.INDETERMINATE,
                ),
                error=exc,
            )
        logger.info("bind_binding_generation_committed", generation=generation)
        return generation

    @staticmethod
    def _scribe_failure_progress(
        error: ScribeTransactionError,
    ) -> tuple[BindingCommitState, str | None, str]:
        """Translate Scribe's exact public outcome into bind progress."""
        if error.state is ScribeTransactionState.COMMITTED and error.generation is not None:
            return (
                BindingCommitState.COMMITTED,
                error.generation,
                "Binding commit succeeded, but Scribe workspace cleanup was interrupted",
            )
        if error.state is ScribeTransactionState.ROLLED_BACK:
            return (
                BindingCommitState.ROLLED_BACK,
                None,
                "Binding commit failed and exact mutations were rolled back",
            )
        return (
            BindingCommitState.INDETERMINATE,
            None,
            "Binding commit failed with indeterminate binding state",
        )

    def _reload_systemd(
        self,
        *,
        created: tuple[str, ...],
        committed_generation: str,
    ) -> None:
        """Reload the user manager or report the already committed generation."""
        progress = BindProgress(
            created_secrets=created,
            binding_commit_state=BindingCommitState.COMMITTED,
            binding_generation=committed_generation,
        )
        try:
            self._systemd_factory().daemon_reload()
        except BaseException as exc:  # noqa: BLE001 - binding is already committed at this boundary
            self._raise_partial(
                f"Bindings committed but systemd --user reload failed: {exc}",
                phase="systemd-reload",
                progress=progress,
                error=exc,
            )
        logger.info("bind_systemd_user_reloaded")

    def _raise_partial(
        self,
        message: str,
        *,
        phase: str,
        progress: BindProgress,
        error: BaseException | None = None,
    ) -> Never:
        """Raise one typed partial failure after recording structured progress."""
        self._log_partial_failure(
            phase=phase,
            progress=progress,
            error=error,
        )
        rendered = self._partial_message(message, progress=progress)
        if error is None:
            raise BindApplyError(rendered, progress=progress)
        if isinstance(error, Exception):
            raise BindApplyError(rendered, progress=progress) from error
        error.add_note(f"LychD bind progress: {rendered}")
        raise error

    def _observe_secrets(
        self,
        names: Sequence[str],
    ) -> tuple[tuple[str, bool], ...]:
        """Capture one deterministic secret-presence generation."""
        return tuple((name, self._secrets.exists(name)) for name in names)

    @staticmethod
    def _partial_message(
        message: str,
        *,
        progress: BindProgress,
    ) -> str:
        """Describe confirmed residue without exposing secret values."""
        facts: list[str] = []
        if progress.created_secrets:
            facts.append("created core secrets remain: " + ", ".join(progress.created_secrets))
        if progress.secret_reconciliation_indeterminate:
            facts.append("the current core-secret operation is indeterminate")
        if progress.binding_generation is not None:
            facts.append(f"binding generation committed: {progress.binding_generation}")
        elif progress.binding_commit_state is BindingCommitState.REJECTED:
            facts.append("binding commit rejected before mutation")
        elif progress.binding_commit_state is BindingCommitState.ROLLED_BACK:
            facts.append("binding mutations rolled back cleanly")
        elif progress.binding_commit_state is BindingCommitState.INDETERMINATE:
            facts.append("binding commit state is indeterminate")
        suffix = "; ".join(facts) or "no effects were confirmed"
        return f"{message}; {suffix}."

    @staticmethod
    def _log_partial_failure(
        *,
        phase: str,
        progress: BindProgress,
        error: BaseException | None = None,
    ) -> None:
        """Emit structured effect truth for an interrupted bind."""
        logger.error(
            "bind_apply_partial_failure",
            phase=phase,
            created_secrets=progress.created_secrets,
            secret_reconciliation_indeterminate=progress.secret_reconciliation_indeterminate,
            binding_commit_state=progress.binding_commit_state,
            binding_generation=progress.binding_generation,
            systemd_reloaded=progress.systemd_reloaded,
            error_type=type(error).__name__ if error is not None else None,
        )
