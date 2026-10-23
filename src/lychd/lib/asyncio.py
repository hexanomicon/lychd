"""Small asyncio correctness primitives shared across cancellation boundaries."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable

__all__ = ["complete_under_cancellation"]


async def complete_under_cancellation[T](operation: Awaitable[T]) -> T:
    """Finish despite repeated caller cancellation without adding diagnostic callbacks.

    The operation's own outcome propagates after completion. Existing callbacks
    installed by callers remain owned by those callers.
    """
    task = asyncio.ensure_future(operation)
    if not task.done() and task.get_loop() is not asyncio.get_running_loop():
        msg = "Cannot await a pending operation from a different event loop."
        raise RuntimeError(msg)
    while not task.done():
        try:
            await asyncio.wait((task,))
        except asyncio.CancelledError:
            continue
    return task.result()
