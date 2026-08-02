"""`TicketStore` — the loop-confined registry of in-flight coven swaps (§TD-5).

Replaces the `nexus._TICKETS` module-global dict. Loop-confined like
`BridgeSessionStore`: every mutation is synchronous and only ever touched from a
single event loop, so no locks are needed. Agent 4 may later subsume swap
transitions into real runs — then `TicketStore` becomes a projection over run
records behind the same controller-facing interface.
"""

from __future__ import annotations

import uuid
from contextlib import suppress
from dataclasses import dataclass
from functools import partial
from time import monotonic
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Callable

    from lychd.domain.orchestration.schema import TransitionTrace

_DEFAULT_CAPACITY = 256
_DEFAULT_TERMINAL_RETENTION_S = 60.0


class TicketCapacityError(RuntimeError):
    """Raised before a transition launch when retained ticket truth fills the store."""


def _new_ticket_id() -> str:
    """Return a fresh, collision-resistant swap-ticket id."""
    return f"ticket_{uuid.uuid4().hex[:12]}"


@dataclass
class TicketRecord:
    """An in-flight coven transition tracked for the polling ticket strip."""

    id: str
    target: str
    action_type: str
    total_metabolic_cost: float
    trace: TransitionTrace
    task: asyncio.Task[Any]
    created_at: float
    terminal_at: float | None = None


class TicketStore:
    """Bounded in-memory swap tickets with a terminal reconnect window."""

    def __init__(
        self,
        *,
        capacity: int = _DEFAULT_CAPACITY,
        terminal_retention_s: float = _DEFAULT_TERMINAL_RETENTION_S,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        """Initialize a bounded store without retiring active or fresh terminal truth."""
        if capacity < 1:
            message = "Ticket capacity must be positive."
            raise ValueError(message)
        if terminal_retention_s <= 0:
            message = "Ticket terminal retention must be positive."
            raise ValueError(message)
        self._tickets: dict[str, TicketRecord] = {}
        self._reservations: set[str] = set()
        self._capacity = capacity
        self._terminal_retention_s = terminal_retention_s
        self._clock = clock

    def ensure_capacity(self) -> None:
        """Retire expired terminals or refuse launch without evicting live truth."""
        self._retire_expired()
        if len(self._tickets) + len(self._reservations) >= self._capacity:
            message = "The process-local transition ticket store is at capacity."
            raise TicketCapacityError(message)

    def reserve_capacity(self, request_id: str) -> None:
        """Reserve one launch slot synchronously across an asynchronous durable claim."""
        if request_id in self._reservations:
            message = f"Transition request {request_id!r} already has a pending ticket reservation."
            raise TicketCapacityError(message)
        self.ensure_capacity()
        self._reservations.add(request_id)

    def release_capacity(self, request_id: str) -> None:
        """Release an unused launch reservation."""
        self._reservations.discard(request_id)

    def open(
        self,
        *,
        target: str,
        action_type: str,
        total_metabolic_cost: float,
        trace: TransitionTrace | None = None,
        task: asyncio.Task[Any],
        reservation: str | None = None,
    ) -> TicketRecord:
        """Register a launched transition task and return its ticket record."""
        if reservation is None:
            try:
                self.ensure_capacity()
            except TicketCapacityError:
                task.cancel()
                raise
        elif reservation not in self._reservations:
            task.cancel()
            message = f"Transition request {reservation!r} has no ticket capacity reservation."
            raise TicketCapacityError(message)
        else:
            self._reservations.remove(reservation)
        from lychd.domain.orchestration.schema import TransitionTrace

        now = self._clock()
        trace = trace or TransitionTrace(target_capability_key=target, priority=100.0)
        ticket_id = _new_ticket_id()
        record = TicketRecord(
            id=ticket_id,
            target=target,
            action_type=action_type,
            total_metabolic_cost=total_metabolic_cost,
            trace=trace,
            task=task,
            created_at=now,
            terminal_at=now if task.done() else None,
        )
        self._tickets[ticket_id] = record
        if task.done():
            self._observe_terminal(task)
        else:
            task.add_done_callback(partial(self._task_done, ticket_id))
        return record

    def get(self, ticket_id: str) -> TicketRecord | None:
        """Return the ticket record, or `None` if unknown."""
        self._retire_expired()
        record = self._tickets.get(ticket_id)
        if record is not None and record.task.done() and record.terminal_at is None:
            record.terminal_at = self._clock()
            self._observe_terminal(record.task)
        return record

    def get_by_request_id(self, request_id: str) -> TicketRecord | None:
        """Return the retained process-local ticket for one orchestration request."""
        self._retire_expired()
        for record in self._tickets.values():
            if record.trace.request_id == request_id:
                if record.task.done() and record.terminal_at is None:
                    record.terminal_at = self._clock()
                    self._observe_terminal(record.task)
                return record
        return None

    @property
    def count(self) -> int:
        """Return retained active and fresh-terminal tickets after expiry pruning."""
        self._retire_expired()
        return len(self._tickets)

    async def aclose(self) -> None:
        """Cancel any still-in-flight transition tasks on shutdown."""
        for record in list(self._tickets.values()):
            if not record.task.done():
                record.task.cancel()
                with suppress(BaseException):
                    await record.task
            else:
                self._observe_terminal(record.task)
        self._tickets.clear()
        self._reservations.clear()

    def _task_done(self, ticket_id: str, task: asyncio.Task[Any]) -> None:
        """Stamp terminal time without removing truth needed by GET/SSE reconnect."""
        record = self._tickets.get(ticket_id)
        if record is not None and record.task is task and record.terminal_at is None:
            record.terminal_at = self._clock()
        self._observe_terminal(task)

    @staticmethod
    def _observe_terminal(task: asyncio.Task[Any]) -> None:
        """Retrieve a task failure while leaving it available for ticket projection."""
        if task.cancelled():
            return
        with suppress(BaseException):
            task.exception()

    def _retire_expired(self) -> None:
        """Remove only terminal tickets whose reconnect window elapsed."""
        now = self._clock()
        for ticket_id, record in list(self._tickets.items()):
            if record.terminal_at is None and record.task.done():
                record.terminal_at = now
                self._observe_terminal(record.task)
            if record.terminal_at is not None and now - record.terminal_at >= self._terminal_retention_s:
                self._tickets.pop(ticket_id, None)
