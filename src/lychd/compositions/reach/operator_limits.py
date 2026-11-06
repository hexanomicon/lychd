"""Shared operator ceilings and a monotonic lifetime bounded by event expiry."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class OperatorLimits:
    native_seconds: int
    pipe_seconds: int
    session_seconds: int


def operator_limits(*, conversation: bool, research: bool) -> OperatorLimits:
    """Select the existing paired-process ceilings without extending any allowance."""
    if research:
        return OperatorLimits(900, 910, 960)
    if conversation:
        return OperatorLimits(750, 760, 810)
    return OperatorLimits(15, 90, 180)


def event_seconds_remaining(occurred_at: datetime, ttl_seconds: int, *, now: datetime) -> float:
    return max(0.0, (occurred_at + timedelta(seconds=ttl_seconds) - now).total_seconds())


@dataclass(frozen=True)
class TurnDeadline:
    """A captured lifetime which later wall-clock adjustments cannot extend."""

    end: float
    clock: Callable[[], float] = field(repr=False, compare=False)

    @classmethod
    def start(
        cls,
        occurred_at: datetime,
        ttl_seconds: int,
        maximum: float,
        *,
        now: datetime | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> TurnDeadline:
        remaining = event_seconds_remaining(occurred_at, ttl_seconds, now=now or datetime.now(UTC))
        return cls(clock() + min(maximum, remaining), clock)

    def remaining(self, maximum: float | None = None) -> float:
        remaining = max(0.0, self.end - self.clock())
        return remaining if maximum is None else min(maximum, remaining)

    def check(self) -> None:
        if self.remaining() <= 0:
            raise TimeoutError
