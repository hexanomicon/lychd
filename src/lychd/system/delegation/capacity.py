"""Bounded provider-capacity decisions for delegated-agent scheduling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import ceil
from typing import Final, TypeGuard

_MAX_PROVIDER_SLOTS: Final[int] = 128
_MAX_QUOTA_REQUESTS: Final[int] = 10_000_000


class ProviderCapacityMode(StrEnum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    MAXIMIZE = "maximize"


class CapacityReason(StrEnum):
    ADMITTED = "admitted"
    NO_REQUEST = "no_request"
    AUTOMATION_DISABLED = "automation_disabled"
    COOLDOWN = "cooldown"
    SLOT_CEILING = "slot_ceiling"
    QUOTA_RESERVE = "quota_reserve"
    UNKNOWN_QUOTA = "unknown_quota"


@dataclass(frozen=True, slots=True)
class ProviderCapacityState:
    """Observed provider/account limits; no policy may widen these facts."""

    authorized_slots: int
    provider_ceiling: int
    configured_ceiling: int
    active_slots: int = 0
    quota_limit: int | None = None
    quota_used: int = 0
    cooldown_until: datetime | None = None
    automation_allowed: bool = True

    def __post_init__(self) -> None:
        """Validate observed limits before the scheduler relies on them."""
        for field_name in ("authorized_slots", "provider_ceiling", "configured_ceiling"):
            _bounded_slots(getattr(self, field_name), field=field_name)
        if not _is_strict_integer(self.active_slots) or not 0 <= self.active_slots <= _MAX_PROVIDER_SLOTS:
            message = f"active_slots must be between 0 and {_MAX_PROVIDER_SLOTS}"
            raise ValueError(message)
        if self.quota_limit is not None and (
            not _is_strict_integer(self.quota_limit) or not 1 <= self.quota_limit <= _MAX_QUOTA_REQUESTS
        ):
            message = "quota_limit is outside the supported range"
            raise ValueError(message)
        if (
            not _is_strict_integer(self.quota_used)
            or self.quota_used < 0
            or self.quota_used > _MAX_QUOTA_REQUESTS
            or (self.quota_limit is not None and self.quota_used > self.quota_limit)
        ):
            message = "quota_used must be non-negative and no greater than quota_limit"
            raise ValueError(message)
        if self.cooldown_until is not None and (
            self.cooldown_until.tzinfo is None or self.cooldown_until.utcoffset() is None
        ):
            message = "cooldown_until must be timezone-aware"
            raise ValueError(message)

    @property
    def hard_ceiling(self) -> int:
        return min(self.authorized_slots, self.provider_ceiling, self.configured_ceiling)


@dataclass(frozen=True, slots=True)
class CapacityDecision:
    admitted: int
    effective_slot_ceiling: int
    quota_headroom: int | None
    reason: CapacityReason
    degraded_to_conservative: bool = False


@dataclass(frozen=True, slots=True)
class ProviderCapacityPolicy:
    mode: ProviderCapacityMode

    def __post_init__(self) -> None:
        """Reject stringly typed modes that could fall through to maximize."""
        if not _is_capacity_mode(self.mode):
            message = "Capacity mode must be a fixed provider-capacity mode"
            raise TypeError(message)

    def decide(
        self,
        state: ProviderCapacityState,
        *,
        requested: int,
        now: datetime,
    ) -> CapacityDecision:
        if not _is_strict_integer(requested) or requested < 0:
            message = "requested capacity must be non-negative"
            raise ValueError(message)
        if now.tzinfo is None or now.utcoffset() is None:
            message = "now must be timezone-aware"
            raise ValueError(message)

        slot_ceiling = _mode_ceiling(self.mode, state.hard_ceiling)
        unknown_quota = state.quota_limit is None
        if unknown_quota:
            slot_ceiling = min(slot_ceiling, 1)

        quota_headroom = _quota_headroom(self.mode, state)
        if requested == 0:
            return CapacityDecision(0, slot_ceiling, quota_headroom, CapacityReason.NO_REQUEST, unknown_quota)
        if not state.automation_allowed:
            return CapacityDecision(
                0,
                slot_ceiling,
                quota_headroom,
                CapacityReason.AUTOMATION_DISABLED,
                unknown_quota,
            )
        if state.cooldown_until is not None and now < state.cooldown_until:
            return CapacityDecision(0, slot_ceiling, quota_headroom, CapacityReason.COOLDOWN, unknown_quota)

        open_slots = max(0, slot_ceiling - state.active_slots)
        if open_slots == 0:
            return CapacityDecision(0, slot_ceiling, quota_headroom, CapacityReason.SLOT_CEILING, unknown_quota)
        effective_quota = 1 if quota_headroom is None else quota_headroom
        admitted = min(requested, open_slots, effective_quota)
        if admitted == 0:
            reason = CapacityReason.UNKNOWN_QUOTA if unknown_quota else CapacityReason.QUOTA_RESERVE
            return CapacityDecision(0, slot_ceiling, quota_headroom, reason, unknown_quota)
        return CapacityDecision(
            admitted,
            slot_ceiling,
            quota_headroom,
            CapacityReason.ADMITTED,
            unknown_quota,
        )


def _mode_ceiling(mode: ProviderCapacityMode, hard_ceiling: int) -> int:
    if mode is ProviderCapacityMode.CONSERVATIVE:
        return min(1, hard_ceiling)
    if mode is ProviderCapacityMode.BALANCED:
        return max(1, ceil(hard_ceiling / 2))
    return hard_ceiling


def _quota_headroom(mode: ProviderCapacityMode, state: ProviderCapacityState) -> int | None:
    if state.quota_limit is None:
        return None
    reserve_ratio = {
        ProviderCapacityMode.CONSERVATIVE: 0.5,
        ProviderCapacityMode.BALANCED: 0.2,
        ProviderCapacityMode.MAXIMIZE: 0.0,
    }[mode]
    reserve = ceil(state.quota_limit * reserve_ratio)
    return max(0, state.quota_limit - state.quota_used - reserve)


def _bounded_slots(value: object, *, field: str) -> None:
    if not _is_strict_integer(value) or not 1 <= value <= _MAX_PROVIDER_SLOTS:
        message = f"{field} must be between 1 and {_MAX_PROVIDER_SLOTS}"
        raise ValueError(message)


def _is_capacity_mode(value: object) -> bool:
    return isinstance(value, ProviderCapacityMode)


def _is_strict_integer(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)


__all__ = (
    "CapacityDecision",
    "CapacityReason",
    "ProviderCapacityMode",
    "ProviderCapacityPolicy",
    "ProviderCapacityState",
)
