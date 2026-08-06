"""Run lifecycle vocabulary: `RunStatus`, `RunRecord`, `RunHandle` (A4 §2).

`RunStatus` is the canonical state machine (spec-00-FINAL C2). `RunRecord` is the
loop-confined, storage-agnostic run truth the `RunLedger` fronts; `RunHandle` is
what `RunEngine.submit` returns to a caller (its run id, chosen workflow, and live
channel). Single-writer discipline (A4 §2): `RunEngine` owns QUEUED/CANCELLED and
the consent re-enqueue; the ghoul task (`perform_run`) owns RUNNING + terminal
states; stasis states are written from inside the run.

Consent and delegated waits are durable states. Their exact verdict/job owners
re-admit through a new sequence-fenced delivery; no resume payload carries authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from lychd.agents.router import ContentPart, Intent
    from lychd.domain.cortex.events import RunChannel

__all__ = [
    "LEGAL_TRANSITIONS",
    "TERMINAL_STATUSES",
    "ConsentPending",
    "IllegalRunTransitionError",
    "RunDeliveryRecord",
    "RunDeliveryState",
    "RunHandle",
    "RunParked",
    "RunRecord",
    "RunStatus",
    "can_transition",
]


class RunStatus(StrEnum):
    """The run lifecycle state machine (A4 §2, spec-00-FINAL C2)."""

    QUEUED = "queued"  # Run + delivery intent exist; the broker hop is not yet claimed
    RUNNING = "running"  # ghoul claimed; graph iterating
    AWAITING_HARDWARE = "awaiting_hardware"  # parked in stasis; orchestrator transitioning
    AWAITING_CONSENT = "awaiting_consent"  # parked on HitL; durable checkpoint written
    AWAITING_DELEGATE = "awaiting_delegate"  # parked on isolated delegated-agent labor
    CANCELLING = "cancelling"  # containment elected; terminal truth waits for acknowledgement
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATUSES: frozenset[RunStatus] = frozenset(
    {RunStatus.DONE, RunStatus.FAILED, RunStatus.CANCELLED},
)


class RunDeliveryState(StrEnum):
    """Durable publication lifecycle for one exact ``(run_id, enqueue_seq)`` hop."""

    HELD = "held"
    PENDING = "pending"
    PUBLISHED = "published"
    CLAIMED = "claimed"
    SETTLED = "settled"


# Legal transitions (A4 §2). Anything else is a bug and must raise in the ledger.
LEGAL_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    # QUEUED→FAILED covers admission-context failure and explicit reconciliation
    # refusal. Broker publication loss remains QUEUED because its delivery intent is
    # durable and can be republished under the same exact key.
    RunStatus.QUEUED: frozenset({RunStatus.RUNNING, RunStatus.FAILED, RunStatus.CANCELLING}),
    RunStatus.RUNNING: frozenset(
        {
            RunStatus.AWAITING_HARDWARE,
            RunStatus.AWAITING_CONSENT,
            RunStatus.AWAITING_DELEGATE,
            RunStatus.DONE,
            RunStatus.FAILED,
            RunStatus.CANCELLING,
        }
    ),
    RunStatus.AWAITING_HARDWARE: frozenset(
        {RunStatus.RUNNING, RunStatus.FAILED, RunStatus.CANCELLING},
    ),
    # AWAITING_CONSENT → QUEUED on approve OR refuse (both re-enqueue, C3).
    RunStatus.AWAITING_CONSENT: frozenset({RunStatus.QUEUED, RunStatus.CANCELLING}),
    # Result adoption re-enqueues one durable resume hop; cancellation remains terminal.
    RunStatus.AWAITING_DELEGATE: frozenset({RunStatus.QUEUED, RunStatus.CANCELLING}),
    RunStatus.CANCELLING: frozenset({RunStatus.CANCELLED}),
    RunStatus.DONE: frozenset(),
    RunStatus.FAILED: frozenset(),
    RunStatus.CANCELLED: frozenset(),
}


class IllegalRunTransitionError(RuntimeError):
    """Raised when a `set_status` violates the run state machine."""

    def __init__(self, run_id: str, current: RunStatus, target: RunStatus) -> None:
        """Record the offending run and the illegal edge."""
        self.run_id = run_id
        self.current = current
        self.target = target
        super().__init__(f"Illegal run transition for {run_id}: {current} → {target}")


class ConsentPending(Exception):  # noqa: N818 - a control-flow suspension signal, not an error
    """A Gate node parked on a consent verdict; the run must suspend, not fail.

    Carries `tool_name` (S4) so `perform_run` can emit the `CONSENT` event AFTER the
    status write, without a codex read.
    """

    def __init__(self, consent_id: str, run_id: str, tool_name: str) -> None:
        """Record the parked consent, its run, and the parked tool name."""
        self.consent_id = consent_id
        self.run_id = run_id
        self.tool_name = tool_name
        super().__init__(f"run {run_id} parked on consent {consent_id}")


@dataclass(frozen=True, kw_only=True)
class RunParked:
    """Graph→substrate sentinel: the run suspended on a consent. NOT a terminal.

    Carries `tool_name` (S4) so `perform_run` emits `CONSENT` only after the status
    is written — a verdict can never race the `engine.approve` status guard.
    """

    consent_id: str
    tool_name: str


def can_transition(current: RunStatus, target: RunStatus) -> bool:
    """Whether ``current → target`` is a legal run transition."""
    return target in LEGAL_TRANSITIONS.get(current, frozenset())


@dataclass
class RunRecord:
    """Storage-agnostic run truth. The `RunLedger` fronts one of these per run."""

    run_id: str
    session_id: str
    workflow_name: str
    pattern_manifest: dict[str, Any]
    source: str
    queue_name: str
    priority: int
    status: RunStatus
    prompt: str
    sigil_name: str = "magus"
    sigil_scopes: frozenset[str] = field(default_factory=frozenset)
    content: tuple[ContentPart, ...] = ()
    requested_priority: int | None = None
    attempt: int = 0
    enqueue_seq: int = 0
    error: str | None = None
    consent_id: str | None = None
    delegated_job_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def to_intent(self) -> Intent:
        """Rebuild the `Intent` that spawned this run (for `workflow.make_state`)."""
        from lychd.agents.router import Intent  # deferred: avoid a cortex→agents import cycle

        return Intent(
            session_id=self.session_id,
            run_id=self.run_id,
            prompt=self.prompt,
            content=self.content,
            source=self.source,
            sigil_name=self.sigil_name,
            sigil_scopes=self.sigil_scopes,
            priority=self.priority,
        )


@dataclass(frozen=True, kw_only=True)
class RunDeliveryRecord:
    """Storage-agnostic truth for one durable broker-publication hop."""

    run_id: str
    enqueue_seq: int
    queue_name: str
    priority: int
    resume: bool
    state: RunDeliveryState
    publish_attempts: int = 0
    last_error: str | None = None
    published_at: datetime | None = None
    claimed_at: datetime | None = None
    settled_at: datetime | None = None


@dataclass(frozen=True, kw_only=True)
class RunHandle:
    """Authoritative admission receipt and a live channel when work remains active."""

    run_id: str
    workflow_name: str
    pattern_id: str
    pattern_revision: str
    evidence_capture: Literal["process_local", "durable_best_effort"]
    channel: RunChannel | None
