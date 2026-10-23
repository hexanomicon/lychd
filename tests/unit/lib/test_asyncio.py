from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager
from typing import Any, Literal

import pytest

from lychd.lib.asyncio import complete_under_cancellation


@asynccontextmanager
async def no_loop_exceptions() -> AsyncGenerator[None, None]:  # noqa: UP043 - Python 3.12 requires both type arguments
    loop = asyncio.get_running_loop()
    contexts: list[dict[str, Any]] = []
    previous = loop.get_exception_handler()
    loop.set_exception_handler(lambda _loop, context: contexts.append(context))
    try:
        yield
    finally:
        try:
            for _ in range(3):
                await asyncio.sleep(0)
            assert contexts == []
        finally:
            loop.set_exception_handler(previous)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["task", "future"])
@pytest.mark.parametrize("outcome", ["success", "error", "cancel"])
async def test_repeated_caller_cancellation_preserves_operation_outcome(
    kind: Literal["task", "future"], outcome: Literal["success", "error", "cancel"]
) -> None:
    async with no_loop_exceptions():
        completion: asyncio.Future[object] = asyncio.get_running_loop().create_future()
        value = object()
        error = RuntimeError("operation failure")
        executions: list[asyncio.Task[Any] | None] = []
        cancellations: list[asyncio.CancelledError] = []

        async def operation() -> object:
            executions.append(asyncio.current_task())
            try:
                return await completion
            except asyncio.CancelledError as exc:
                cancellations.append(exc)
                raise

        inner: asyncio.Future[object] = asyncio.create_task(operation()) if kind == "task" else completion
        outer = asyncio.create_task(complete_under_cancellation(inner))
        await asyncio.sleep(0)
        for index in range(3):
            assert outer.cancel(f"caller cancellation {index}")
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            assert not outer.done()
            assert not inner.cancelled()
            assert cancellations == []
        if outcome == "error":
            completion.set_exception(error)
        elif outcome == "cancel":
            completion.cancel("operation cancellation")
        else:
            completion.set_result(value)

        if outcome == "error":
            with pytest.raises(RuntimeError) as raised:
                await outer
            assert raised.value is error
            assert inner.exception() is error
        elif outcome == "cancel":
            with pytest.raises(asyncio.CancelledError, match="operation cancellation"):
                await outer
            assert inner.cancelled()
        else:
            assert await outer is value
            assert inner.result() is value
        assert outer.cancelling() == 3
        assert executions == ([inner] if kind == "task" else [])


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["success", "error", "cancel"])
@pytest.mark.parametrize("foreign_loop", [False, True])
async def test_completed_future_propagates_without_suspending(
    outcome: Literal["success", "error", "cancel"], *, foreign_loop: bool
) -> None:
    async with no_loop_exceptions():
        loop = asyncio.new_event_loop() if foreign_loop else asyncio.get_running_loop()
        value = object()
        error = RuntimeError("completed failure")
        inner: asyncio.Future[object] = loop.create_future()
        if outcome == "error":
            inner.set_exception(error)
        elif outcome == "cancel":
            inner.cancel("completed cancellation")
        else:
            inner.set_result(value)
        yielded: list[str] = []
        asyncio.get_running_loop().call_soon(yielded.append, "yielded")
        try:
            if outcome == "error":
                with pytest.raises(RuntimeError) as raised:
                    await complete_under_cancellation(inner)
                assert raised.value is error
            elif outcome == "cancel":
                with pytest.raises(asyncio.CancelledError, match="completed cancellation"):
                    await complete_under_cancellation(inner)
            else:
                assert await complete_under_cancellation(inner) is value
            assert yielded == []
        finally:
            if foreign_loop:
                loop.close()


@pytest.mark.asyncio
async def test_pending_foreign_future_refuses_without_cancelling_it() -> None:
    async with no_loop_exceptions():
        foreign_loop = asyncio.new_event_loop()
        inner: asyncio.Future[object] = foreign_loop.create_future()
        try:
            with pytest.raises(RuntimeError, match="different event loop"):
                await complete_under_cancellation(inner)
            assert not inner.done()
        finally:
            inner.cancel()
            foreign_loop.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("custom_awaitable", [False, True])
async def test_awaitable_is_scheduled_once_despite_repeated_cancellation(*, custom_awaitable: bool) -> None:
    async with no_loop_exceptions():
        started = asyncio.Event()
        release = asyncio.Event()
        value = object()
        executions: list[asyncio.Task[Any] | None] = []
        await_calls: list[bool] = []

        async def operation() -> object:
            executions.append(asyncio.current_task())
            started.set()
            await release.wait()
            return value

        class Operation:
            def __await__(self) -> Generator[Any, None, object]:
                await_calls.append(True)
                return operation().__await__()

        supplied = Operation() if custom_awaitable else operation()
        outer = asyncio.create_task(complete_under_cancellation(supplied))
        await started.wait()
        for _ in range(3):
            outer.cancel()
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            assert not outer.done()
        release.set()
        assert await outer is value
        assert len(executions) == 1
        assert executions[0] is not outer
        assert await_calls == ([True] if custom_awaitable else [])
        assert outer.cancelling() == 3
