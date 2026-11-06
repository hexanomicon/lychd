"""Ownership of effectful SDK callbacks and generation background work."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import AsyncGenerator, Callable, Coroutine
from contextlib import asynccontextmanager
from functools import wraps
from types import CoroutineType
from typing import Any, Concatenate, Protocol, get_type_hints

SHUTDOWN_SECONDS = 5


class EdgeTasks:
    """Close business admission, then cancel and join owned work before its dependencies."""

    def __init__(self, *, on_failure: Callable[[], None] | None = None) -> None:
        """Start a generation with open callback admission and no detached work."""
        self._on_failure = on_failure
        self.closing = False
        self.retired = False
        self._tasks: dict[asyncio.Task[Any], int] = {}
        self._closing: asyncio.Task[None] | None = None

    @asynccontextmanager
    async def callback(self) -> AsyncGenerator[None]:
        if self.closing:
            raise asyncio.CancelledError
        task = asyncio.current_task()
        if task is None:
            msg = "callback_task_missing"
            raise RuntimeError(msg)
        self._tasks[task] = self._tasks.get(task, 0) + 1
        try:
            yield
        finally:
            depth = self._tasks.get(task, 1) - 1
            if depth:
                self._tasks[task] = depth
            else:
                self._tasks.pop(task, None)

    def spawn[Result](self, work: Coroutine[Any, Any, Result]) -> asyncio.Task[Result]:
        if self.closing:
            work.close()
            msg = "generation_closing"
            raise RuntimeError(msg)
        task = asyncio.create_task(work)
        self._tasks[task] = 1
        task.add_done_callback(self._finished)
        return task

    def _finished(self, task: asyncio.Task[Any]) -> None:
        self._tasks.pop(task, None)
        if not task.cancelled() and task.exception() is not None and self._on_failure is not None:
            self._on_failure()

    async def close(self) -> None:
        if self._closing is None:
            self.closing = True
            caller = asyncio.current_task()

            async def retire() -> None:
                tasks = [task for task in self._tasks if task is not caller and not task.done()]
                for task in tasks:
                    task.cancel()
                if tasks:
                    _, pending = await asyncio.wait(tasks, timeout=SHUTDOWN_SECONDS)
                    if pending:
                        raise TimeoutError
                    await asyncio.gather(*tasks, return_exceptions=True)
                self.retired = True

            self._closing = asyncio.create_task(retire())
        try:
            await asyncio.shield(self._closing)
        except asyncio.CancelledError:
            await self._closing
            raise


class _Service(Protocol):
    @property
    def tasks(self) -> EdgeTasks: ...


class _Owner(Protocol):
    @property
    def service(self) -> _Service: ...


def service_callback[Owner: _Owner, Result, **Parameters](
    callback: Callable[Concatenate[Owner, Parameters], CoroutineType[Any, Any, Result]],
) -> Callable[Concatenate[Owner, Parameters], CoroutineType[Any, Any, Result]]:
    """Register actual command/UI/event entry, retaining its inspected SDK signature."""

    @wraps(callback)
    async def owned(self: Owner, *args: Parameters.args, **kwargs: Parameters.kwargs) -> Result:
        async with self.service.tasks.callback():
            return await callback(self, *args, **kwargs)

    owned.__annotations__ = get_type_hints(callback)
    setattr(owned, "__signature__", inspect.signature(callback, eval_str=True))  # noqa: B010 - runtime SDK metadata
    return owned
