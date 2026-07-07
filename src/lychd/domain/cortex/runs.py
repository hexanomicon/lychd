"""Run lifecycle vocabulary: `RunStatus`, `RunRecord`, `RunHandle` (A4 §2).

`RunStatus` is the canonical state machine (spec-00-FINAL C2). `RunRecord` is the
loop-confined, storage-agnostic run truth the `RunLedger` fronts; `RunHandle` is
what `RunEngine.submit` returns to a caller (its run id, chosen workflow, and live
channel). Single-writer discipline (A4 §2): `RunEngine` owns QUEUED/CANCELLED and
the consent re-enqueue; the ghoul task (`perform_run`) owns RUNNING + terminal
states; stasis states are written from inside the run.

Consent stays a Wave-1 placeholder this wave — the AWAITING_CONSENT state and the
`AWAITING_CONSENT → QUEUED` edge exist as the seam for honest HitL (Wave 4). A4's
`ConsentPark`/`ResumePayload`/`resume_run` are NOT built (deleted per C2/C3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lychd.agents.router import Intent
    from lychd.domain.cortex.events import RunChannel

__all__ = [
    "LEGAL_TRANSITIONS",
    "TERMINAL_STATUSES",
    "ConsentPending",
    "IllegalRunTransitionError",
    "RunHandle",
    "RunParked",
    "RunRecord",
    "RunStatus",
    "can_transition",
]


class RunStatus(StrEnum):
    """The run lifecycle state machine (A4 §2, spec-00-FINAL C2)."""

    QUEUED = "queued"  # Run row exists; SAQ job enqueued; not yet claimed
    RUNNING = "running"  # ghoul claimed; graph iterating
    AWAITING_HARDWARE = "awaiting_hardware"  # parked in stasis; orchestrator transitioning
    AWAITING_CONSENT = "awaiting_consent"  # parked on HitL; durable checkpoint written
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATUSES: frozenset[RunStatus] = frozenset(
    {RunStatus.DONE, RunStatus.FAILED, RunStatus.CANCELLED},
)

# Legal transitions (A4 §2). Anything else is a bug and must raise in the ledger.
LEGAL_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    # QUEUED→FAILED is the uncompensated-enqueue escape (F3/H2): if `_enqueue`
    # raises, `engine.submit` fails the QUEUED row instead of black-holing it, and
    # `reconcile_runs` sweeps QUEUED rows whose enqueue was lost across a restart.
    RunStatus.QUEUED: frozenset({RunStatus.RUNNING, RunStatus.FAILED, RunStatus.CANCELLED}),
    RunStatus.RUNNING: frozenset(
        {
            RunStatus.AWAITING_HARDWARE,
            RunStatus.AWAITING_CONSENT,
            RunStatus.DONE,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        }
    ),
    RunStatus.AWAITING_HARDWARE: frozenset(
        {RunStatus.RUNNING, RunStatus.FAILED, RunStatus.CANCELLED},
    ),
    # AWAITING_CONSENT → QUEUED on approve OR refuse (both re-enqueue, C3); → CANCELLED only via engine.cancel.
    RunStatus.AWAITING_CONSENT: frozenset({RunStatus.QUEUED, RunStatus.CANCELLED}),
    RunStatus.DONE: frozenset(),
    RunStatus.FAILED: frozenset({RunStatus.QUEUED}),  # explicit retry (bumps attempt)
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
    source: str
    queue_name: str
    priority: int
    status: RunStatus
    prompt: str
    sigil_scopes: frozenset[str] = field(default_factory=frozenset)
    attempt: int = 0
    enqueue_seq: int = 0
    error: str | None = None
    consent_id: str | None = None
    stasis_path: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def to_intent(self) -> Intent:
        """Rebuild the `Intent` that spawned this run (for `workflow.make_state`)."""
        from lychd.agents.router import Intent  # deferred: avoid a cortex→agents import cycle

        return Intent(
            session_id=self.session_id,
            run_id=self.run_id,
            prompt=self.prompt,
            source=self.source,
            sigil_scopes=self.sigil_scopes,
            priority=self.priority,
        )


@dataclass(frozen=True, kw_only=True)
class RunHandle:
    """What `RunEngine.submit` returns: the run id, chosen workflow, live channel."""

    run_id: str
    workflow_name: str
    channel: RunChannel
