"""Explicit lifecycle owner for SAQ queues used outside request dependency scopes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

import structlog

logger = structlog.get_logger()

__all__ = ["ManagedRunQueue", "connect_run_queues", "disconnect_run_queues"]


@runtime_checkable
class ManagedRunQueue(Protocol):
    """The broker-pool lifecycle shared by SAQ's concrete queue types."""

    name: str

    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...


def _require_managed_queue(name: str, queue: object) -> ManagedRunQueue:
    if isinstance(queue, ManagedRunQueue):
        return queue
    msg = f"Configured run queue '{name}' has no managed connect/disconnect lifecycle."
    raise TypeError(msg)


async def connect_run_queues(queues: Mapping[str, object]) -> tuple[ManagedRunQueue, ...]:
    """Connect every queue or roll back the already-connected prefix."""
    connected: list[ManagedRunQueue] = []
    try:
        for name, queue in queues.items():
            managed = _require_managed_queue(name, queue)
            await managed.connect()
            connected.append(managed)
    except BaseException:
        await disconnect_run_queues(connected)
        raise
    return tuple(connected)


async def disconnect_run_queues(queues: Sequence[ManagedRunQueue]) -> None:
    """Disconnect queues in reverse construction order, logging every failure."""
    for queue in reversed(queues):
        try:
            await queue.disconnect()
        except Exception as exc:
            logger.exception("saq_queue_disconnect_failed", queue_name=queue.name, error=str(exc))
