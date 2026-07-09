"""Small asyncio correctness primitives shared across cancellation boundaries."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable

__all__ = ["complete_under_cancellation"]


async def complete_under_cancellation[T](operation: Awaitable[T]) -> T:
    """Finish ``operation`` despite caller cancellation, including repeated cancels."""
    task = asyncio.ensure_future(operation)
    while True:
        try:
            result = await asyncio.shield(task)
        except asyncio.CancelledError:
            if task.done():
                return task.result()
        else:
            return result
