"""Request-local commitment state, separate from generation worker capacity."""

from __future__ import annotations

from lychd.compositions.reach.conversation_session import ContextTurnOutcome
from lychd.compositions.reach.operator_limits import TurnDeadline
from lychd.compositions.reach.schemas import ReachEvent


class OperatorSession:
    """Bind progress and one terminal attempt to one admitted event and deadline."""

    def __init__(self, event: ReachEvent, deadline: TurnDeadline) -> None:
        """Pin the admitted event and captured lifetime before any asynchronous work."""
        self._event = event
        self._deadline = deadline
        self.plan_delivered = False
        self.terminal_started = False
        self.outcome: ContextTurnOutcome | None = None
        self.closed = False

    @property
    def event(self) -> ReachEvent:
        return self._event

    @property
    def deadline(self) -> TurnDeadline:
        return self._deadline

    @property
    def candidate(self) -> bool:
        return self.event.trigger in {"reply", "followup"}

    def confirm_plan(self, *, delivered: bool) -> bool:
        if self.closed or self.terminal_started:
            return False
        self.deadline.check()
        self.plan_delivered = self.plan_delivered or delivered
        return delivered

    def visible(self) -> bool:
        if self.outcome is not None:
            result = self.outcome.result
            if result.status == "ignore":
                return False
            if self.outcome.stop is not None or result.status not in {"error", "refused"}:
                return True
        return self.plan_delivered if self.candidate else self.outcome is not None

    def can_report_failure(self) -> bool:
        return not self.closed and not self.terminal_started and (not self.candidate or self.plan_delivered)

    def begin_terminal(self) -> None:
        self.deadline.check()
        if self.closed or self.terminal_started:
            msg = "terminal_already_started"
            raise ValueError(msg)
        self.terminal_started = True

    def retire(self) -> None:
        self.closed = True
