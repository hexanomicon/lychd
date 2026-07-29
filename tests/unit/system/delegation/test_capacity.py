from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from lychd.system.delegation.capacity import (
    CapacityReason,
    ProviderCapacityMode,
    ProviderCapacityPolicy,
    ProviderCapacityState,
)

_NOW = datetime(2026, 7, 29, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (ProviderCapacityMode.CONSERVATIVE, 1),
        (ProviderCapacityMode.BALANCED, 5),
        (ProviderCapacityMode.MAXIMIZE, 10),
    ],
)
def test_capacity_modes_have_distinct_but_bounded_parallelism(
    mode: ProviderCapacityMode,
    expected: int,
) -> None:
    state = ProviderCapacityState(
        authorized_slots=12,
        provider_ceiling=10,
        configured_ceiling=11,
        quota_limit=1_000,
    )

    decision = ProviderCapacityPolicy(mode).decide(state, requested=20, now=_NOW)

    assert decision.admitted == expected
    assert decision.effective_slot_ceiling == expected
    assert decision.reason is CapacityReason.ADMITTED


@pytest.mark.parametrize(
    ("mode", "expected_headroom"),
    [
        (ProviderCapacityMode.CONSERVATIVE, 40),
        (ProviderCapacityMode.BALANCED, 70),
        (ProviderCapacityMode.MAXIMIZE, 90),
    ],
)
def test_capacity_modes_preserve_their_quota_reserve(
    mode: ProviderCapacityMode,
    expected_headroom: int,
) -> None:
    state = ProviderCapacityState(
        authorized_slots=10,
        provider_ceiling=10,
        configured_ceiling=10,
        quota_limit=100,
        quota_used=10,
    )

    decision = ProviderCapacityPolicy(mode).decide(state, requested=1, now=_NOW)

    assert decision.quota_headroom == expected_headroom


def test_maximize_never_exceeds_the_smallest_real_ceiling() -> None:
    state = ProviderCapacityState(
        authorized_slots=12,
        provider_ceiling=8,
        configured_ceiling=3,
        active_slots=2,
        quota_limit=100,
    )

    decision = ProviderCapacityPolicy(ProviderCapacityMode.MAXIMIZE).decide(
        state,
        requested=100,
        now=_NOW,
    )

    assert decision.effective_slot_ceiling == 3
    assert decision.admitted == 1


def test_unknown_quota_degrades_every_mode_to_one_slot() -> None:
    state = ProviderCapacityState(
        authorized_slots=20,
        provider_ceiling=20,
        configured_ceiling=20,
    )

    decision = ProviderCapacityPolicy(ProviderCapacityMode.MAXIMIZE).decide(
        state,
        requested=20,
        now=_NOW,
    )

    assert decision.admitted == 1
    assert decision.quota_headroom is None
    assert decision.degraded_to_conservative is True


@pytest.mark.parametrize(
    ("state", "reason"),
    [
        (
            ProviderCapacityState(
                authorized_slots=2,
                provider_ceiling=2,
                configured_ceiling=2,
                automation_allowed=False,
            ),
            CapacityReason.AUTOMATION_DISABLED,
        ),
        (
            ProviderCapacityState(
                authorized_slots=2,
                provider_ceiling=2,
                configured_ceiling=2,
                cooldown_until=_NOW + timedelta(minutes=1),
            ),
            CapacityReason.COOLDOWN,
        ),
        (
            ProviderCapacityState(
                authorized_slots=2,
                provider_ceiling=2,
                configured_ceiling=2,
                active_slots=2,
                quota_limit=100,
            ),
            CapacityReason.SLOT_CEILING,
        ),
        (
            ProviderCapacityState(
                authorized_slots=2,
                provider_ceiling=2,
                configured_ceiling=2,
                quota_limit=100,
                quota_used=100,
            ),
            CapacityReason.QUOTA_RESERVE,
        ),
    ],
)
def test_capacity_policy_honors_stops(
    state: ProviderCapacityState,
    reason: CapacityReason,
) -> None:
    decision = ProviderCapacityPolicy(ProviderCapacityMode.MAXIMIZE).decide(
        state,
        requested=2,
        now=_NOW,
    )

    assert decision.admitted == 0
    assert decision.reason is reason


def test_capacity_state_rejects_ceiling_and_time_bypass() -> None:
    with pytest.raises(ValueError, match="authorized_slots"):
        ProviderCapacityState(
            authorized_slots=129,
            provider_ceiling=1,
            configured_ceiling=1,
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        ProviderCapacityState(
            authorized_slots=1,
            provider_ceiling=1,
            configured_ceiling=1,
            cooldown_until=_NOW.replace(tzinfo=None),
        )
    with pytest.raises(TypeError, match="fixed provider-capacity mode"):
        ProviderCapacityPolicy("maximize")  # type: ignore[arg-type]
