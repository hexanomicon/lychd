"""Explicit lifecycle owner for SAQ queues used outside request dependency scopes."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import structlog

logger = structlog.get_logger()

if TYPE_CHECKING:
    from lychd.domain.cortex.engine import RunQueue

__all__ = [
    "CancellationSafePostgresRunQueue",
    "ManagedRunQueue",
    "connect_run_queues",
    "disconnect_run_queues",
    "protect_run_queues",
]


class CancellationSafePostgresRunQueue:
    """SAQ PostgreSQL facade with atomic terminal guards and abort acknowledgement.

    SAQ 0.26 moves any non-queued job to ``ABORTING``, including a job that became
    terminal between a caller's probe and abort. This facade performs the status
    decision under the queue row lock, treats terminal jobs as no-ops, and waits for
    active work to acknowledge cancellation before returning.
    """

    __slots__ = ("_queue",)

    def __init__(self, queue: Any) -> None:
        """Wrap one connected SAQ PostgreSQL queue."""
        self._queue = queue

    @property
    def name(self) -> str:
        return str(self._queue.name)

    def __getattr__(self, name: str) -> Any:
        """Delegate non-cancellation queue operations unchanged."""
        return getattr(self._queue, name)

    async def connect(self) -> None:
        """Connect SAQ and close a pool opened before a failed schema initialization."""
        try:
            await self._queue.connect()
        except BaseException as connect_error:
            cleanup_errors: list[BaseException] = []
            try:
                await self._queue.disconnect()
            except (Exception, asyncio.CancelledError) as exc:  # noqa: BLE001 - preserve cleanup evidence
                cleanup_errors.append(exc)
            if getattr(self._queue, "_manage_pool_lifecycle", False) and not getattr(
                self._queue.pool,
                "closed",
                False,
            ):
                try:
                    await self._queue.pool.close()
                except (Exception, asyncio.CancelledError) as exc:  # noqa: BLE001 - preserve cleanup evidence
                    cleanup_errors.append(exc)
            if cleanup_errors:
                message = f"SAQ queue {self.name!r} failed to connect and clean up its partial pool."
                raise BaseExceptionGroup(message, [connect_error, *cleanup_errors]) from None
            raise

    async def disconnect(self) -> None:
        """Disconnect the wrapped SAQ queue."""
        await self._queue.disconnect()

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any | None:
        return await self._queue.enqueue(job_or_func, **kwargs)

    async def job(self, job_key: str, /) -> Any | None:
        return await self._queue.job(job_key)

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        """Request abort atomically and wait for an active worker's terminal ack."""
        must_wait = await self._request_abort(job, error=error, force=False)
        if not must_wait:
            return
        await job.refresh(until_complete=ttl)
        if not self._job_is_terminal(job):
            msg = f"SAQ job {job.key!r} did not acknowledge cancellation within {ttl}s."
            raise TimeoutError(msg)

    async def abort_orphan(self, job: Any, error: str, /) -> None:
        """Fence a pre-boot job whose former worker process cannot acknowledge."""
        await self._request_abort(job, error=error, force=True)

    async def _request_abort(self, job: Any, *, error: str, force: bool) -> bool:
        from saq.job import TERMINAL_STATUSES, Status

        async with self._queue.pool.connection() as connection, connection.transaction():
            status = await self._queue.get_job_status(
                job.key,
                for_update=True,
                connection=connection,
            )
            if status is None or status in TERMINAL_STATUSES:
                return False
            if force or status is Status.QUEUED:
                await self._queue.finish(
                    job,
                    Status.ABORTED,
                    error=error,
                    connection=connection,
                )
                return False
            await self._queue.update(
                job,
                status=Status.ABORTING,
                error=error,
                connection=connection,
            )
            return True

    @staticmethod
    def _job_is_terminal(job: Any) -> bool:
        from saq.job import TERMINAL_STATUSES

        return job.status in TERMINAL_STATUSES


def protect_run_queues(queues: Mapping[str, RunQueue]) -> dict[str, RunQueue]:
    """Wrap concrete PostgreSQL queues at the application composition boundary."""
    from saq.queue.postgres import PostgresQueue

    return {
        name: CancellationSafePostgresRunQueue(queue) if isinstance(queue, PostgresQueue) else queue
        for name, queue in queues.items()
    }


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
    """Connect every queue or roll back every queue whose connect was attempted."""
    connected: list[ManagedRunQueue] = []
    try:
        for name, queue in queues.items():
            managed = _require_managed_queue(name, queue)
            connected.append(managed)
            await managed.connect()
    except BaseException:
        await disconnect_run_queues(connected)
        raise
    return tuple(connected)


async def disconnect_run_queues(queues: Sequence[ManagedRunQueue]) -> None:
    """Attempt every reverse-order disconnect and report any incomplete teardown."""
    errors: list[Exception] = []
    cancellations: list[asyncio.CancelledError] = []
    for queue in reversed(queues):
        cancellation, error = await _disconnect_queue_under_cancellation(queue)
        if cancellation is not None:
            cancellations.append(cancellation)
            logger.warning("saq_queue_disconnect_cancelled", queue_name=queue.name)
        if error is not None:
            errors.append(error)
            logger.error("saq_queue_disconnect_failed", queue_name=queue.name, error=str(error))
    if cancellations and errors:
        message = "SAQ queue disconnect was cancelled and one or more queues also failed."
        raise BaseExceptionGroup(message, [*cancellations, *errors])
    if cancellations:
        raise cancellations[0]
    if errors:
        message = "One or more SAQ queues failed to disconnect."
        raise ExceptionGroup(message, errors)


async def _disconnect_queue_under_cancellation(
    queue: ManagedRunQueue,
) -> tuple[asyncio.CancelledError | None, Exception | None]:
    """Finish one teardown before reporting caller or queue-task cancellation."""
    task = asyncio.create_task(queue.disconnect(), name=f"lychd-disconnect-{queue.name}")
    cancellation: asyncio.CancelledError | None = None
    while True:
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError as exc:
            cancellation = cancellation or exc
            if not task.done():
                continue
            try:
                task.result()
            except asyncio.CancelledError as task_cancelled:
                cancellation = cancellation or task_cancelled
            except Exception as task_error:  # noqa: BLE001 - retain teardown error through the reverse sweep
                return cancellation, task_error
            return cancellation, None
        except Exception as exc:  # noqa: BLE001 - retain teardown error through the reverse sweep
            return cancellation, exc
        else:
            return cancellation, None
