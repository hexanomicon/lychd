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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncio


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
    task: asyncio.Task[Any]


class TicketStore:
    """In-memory store of in-flight swap tickets, keyed by ticket id."""

    def __init__(self) -> None:
        """Initialize the empty, loop-confined ticket store."""
        self._tickets: dict[str, TicketRecord] = {}

    def open(
        self,
        *,
        target: str,
        action_type: str,
        total_metabolic_cost: float,
        task: asyncio.Task[Any],
    ) -> TicketRecord:
        """Register a launched transition task and return its ticket record."""
        ticket_id = _new_ticket_id()
        record = TicketRecord(
            id=ticket_id,
            target=target,
            action_type=action_type,
            total_metabolic_cost=total_metabolic_cost,
            task=task,
        )
        self._tickets[ticket_id] = record
        return record

    def get(self, ticket_id: str) -> TicketRecord | None:
        """Return the ticket record, or `None` if unknown."""
        return self._tickets.get(ticket_id)

    def settle(self, ticket_id: str) -> TicketRecord | None:
        """Pop and return a ticket that has finished (or `None` if unknown)."""
        return self._tickets.pop(ticket_id, None)

    async def aclose(self) -> None:
        """Cancel any still-in-flight transition tasks on shutdown."""
        for record in list(self._tickets.values()):
            if not record.task.done():
                record.task.cancel()
                with suppress(BaseException):
                    await record.task
        self._tickets.clear()
