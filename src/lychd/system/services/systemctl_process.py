"""Bounded lifecycle helpers for trusted ``systemctl`` client processes."""

from __future__ import annotations

import asyncio
import math
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from asyncio.subprocess import Process
    from collections.abc import Awaitable

__all__ = [
    "SystemctlClientTimeoutError",
    "communicate_systemctl_client",
    "validate_systemctl_timeout",
    "wait_systemctl_client",
]

_TERMINATE_GRACE_SECONDS = 1.0


class SystemctlClientTimeoutError(TimeoutError):
    """The local ``systemctl`` client exceeded its bounded response budget."""

    def __init__(self, operation: str, timeout_s: float) -> None:
        """Preserve the bounded operation and budget for typed classification."""
        super().__init__(f"{operation} timed out after {timeout_s:g}s")
        self.operation = operation
        self.timeout_s = timeout_s


def validate_systemctl_timeout(timeout_s: float) -> float:
    """Require a finite positive client timeout at every construction seam."""
    if not math.isfinite(timeout_s) or timeout_s <= 0:
        msg = "systemctl client timeout must be finite and positive"
        raise ValueError(msg)
    return timeout_s


async def wait_systemctl_client(
    process: Process,
    *,
    timeout_s: float,
    operation: str,
) -> int:
    """Wait for one client, terminating and reaping it when its budget expires."""
    await _bounded_process_call(
        process.wait(),
        process=process,
        timeout_s=timeout_s,
        operation=operation,
    )
    if process.returncode is None:
        msg = f"{operation} client exited without a terminal return code"
        raise RuntimeError(msg)
    return process.returncode


async def communicate_systemctl_client(
    process: Process,
    *,
    timeout_s: float,
    operation: str,
) -> tuple[bytes, bytes]:
    """Collect one client response within budget, then terminate and reap on timeout."""
    stdout, stderr = await _bounded_process_call(
        process.communicate(),
        process=process,
        timeout_s=timeout_s,
        operation=operation,
    )
    if process.returncode is None:
        msg = f"{operation} client exited without a terminal return code"
        raise RuntimeError(msg)
    return stdout or b"", stderr or b""


async def _bounded_process_call[ResultT](
    awaitable: Awaitable[ResultT],
    *,
    process: Process,
    timeout_s: float,
    operation: str,
) -> ResultT:
    timeout_s = validate_systemctl_timeout(timeout_s)
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout_s)
    except TimeoutError as exc:
        await _terminate_and_reap(process, operation=operation)
        raise SystemctlClientTimeoutError(operation, timeout_s) from exc
    except asyncio.CancelledError:
        await _terminate_and_reap(process, operation=operation)
        raise


async def _terminate_and_reap(process: Process, *, operation: str) -> None:
    """Escalate TERM to KILL, bounding both reaping waits."""
    if process.returncode is not None:
        return
    with suppress(ProcessLookupError):
        process.terminate()
    if await _wait_for_exit(process):
        return

    with suppress(ProcessLookupError):
        process.kill()
    if await _wait_for_exit(process):
        return
    msg = f"{operation} client did not exit after terminate and kill"
    raise RuntimeError(msg)


async def _wait_for_exit(process: Process) -> bool:
    try:
        await asyncio.wait_for(process.wait(), timeout=_TERMINATE_GRACE_SECONDS)
    except TimeoutError:
        return False
    return True
