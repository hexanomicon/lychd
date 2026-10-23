"""Explicit local native delivery primitives shared by finite Blockworld labs.

This memory worker owns no persistence or default application registration.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from typing import Any


@dataclass
class LocalJob:
    key: str
    run_id: str
    enqueue_seq: int
    task: asyncio.Task[dict[str, Any]] | None = None


class LocalRunQueue:
    """Own finite worker invocations; never retry an interrupted local action."""

    def __init__(self) -> None:
        """Create an unpublished local queue with no worker task."""
        self.jobs: dict[str, LocalJob] = {}

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> LocalJob:
        if job_or_func != "perform_run":
            msg = "Local delivery accepts only perform_run."
            raise ValueError(msg)
        key = str(kwargs["key"])
        if key in self.jobs:
            return self.jobs[key]
        job = LocalJob(key=key, run_id=kwargs["run_id"], enqueue_seq=kwargs["enqueue_seq"])
        self.jobs[key] = job
        from lychd.ghouls.runs import perform_run

        job.task = asyncio.create_task(perform_run({}, run_id=job.run_id, enqueue_seq=job.enqueue_seq), name=key)
        return job

    async def job(self, job_key: str, /) -> LocalJob | None:
        return self.jobs.get(job_key)

    async def abort(self, job: LocalJob, error: str, /, ttl: float = 5) -> None:
        del error, ttl
        if job.task is not None and not job.task.done():
            job.task.cancel()
            with suppress(asyncio.CancelledError):
                await job.task

    async def close(self) -> None:
        """Drain every task, preserving failures for the invoking runner."""
        tasks = [job.task for job in self.jobs.values() if job.task is not None]
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


class RefuseHostTransitions:
    """No host transition is authorized by this local client profile."""

    async def apply(self, intent: Any) -> None:
        """Refuse every host transition rather than touching the operator's host."""
        del intent
        msg = "This local profile cannot transition host runtimes."
        raise RuntimeError(msg)

    def assert_clear(self) -> None:
        """Retain no host state because the profile cannot activate host runtimes."""

    def arm(self, record: Any) -> None:
        """Refuse attempts to acquire host activation custody."""
        del record
        msg = "This local profile cannot arm a host activation."
        raise RuntimeError(msg)

    def clear(self, record: Any) -> None:
        """Refuse attempts to change a host activation record."""
        del record
        msg = "This local profile cannot clear a host activation."
        raise RuntimeError(msg)
