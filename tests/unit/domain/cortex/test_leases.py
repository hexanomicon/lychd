from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from lychd.domain.animation.capabilities import (
    CapabilityGrant,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
    GrantLease,
    SourceKind,
)
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.schemas.generation import GenerationProfile
from lychd.domain.cortex.leases import AnimatorAdmission, LeaseAdmissionClosed, LeaseLedger


def _grant(*, grant_id: str, animator_name: str = "titan") -> CapabilityGrant:
    spec = CapabilitySpec(
        key=f"{animator_name}:chat:model",
        animator_name=animator_name,
        runtime="llamacpp",
        source_kind=SourceKind.SOULSTONE,
        family=CapabilityFamily.CHAT,
        model_id="model",
    )
    state = CapabilityState(
        capability_key=spec.key,
        is_dynamic=False,
        phase=CapabilityPhase.WARM,
    )
    return CapabilityGrant(
        spec=spec,
        state=state,
        lease=GrantLease(grant_id=grant_id, holder="run:r1", issued_at=datetime.now(UTC)),
        generation=GenerationProfile(),
        model=None,
    )


def test_acquire_then_active_by_animator() -> None:
    ledger = LeaseLedger()
    ledger.acquire(_grant(grant_id="g1", animator_name="titan"), priority=50)

    rows = ledger.active(animator_name="titan")
    assert len(rows) == 1
    assert rows[0].grant_id == "g1"
    assert rows[0].capability_key == "titan:chat:model"
    assert ledger.active(animator_name="coding") == []
    assert len(ledger.active()) == 1


def test_duplicate_grant_id_raises() -> None:
    ledger = LeaseLedger()
    ledger.acquire(_grant(grant_id="dup"), priority=50)
    with pytest.raises(RuntimeError) as exc_info:
        ledger.acquire(_grant(grant_id="dup"), priority=50)
    assert not isinstance(exc_info.value, LeaseAdmissionClosed)


def test_release_is_idempotent() -> None:
    ledger = LeaseLedger()
    ledger.acquire(_grant(grant_id="g1"), priority=50)
    ledger.release("g1")
    ledger.release("g1")  # no raise
    ledger.release("never-existed")  # no raise
    assert ledger.active() == []


def test_drain_admission_refuses_new_lease_then_reopens() -> None:
    ledger = LeaseLedger()
    existing = _grant(grant_id="existing", animator_name="titan")
    ledger.acquire(existing, priority=50)

    ledger.begin_drain(["titan"])

    assert ledger.admission("titan") is AnimatorAdmission.DRAINING
    assert ledger.active(animator_name="titan")[0].grant_id == "existing"
    with pytest.raises(LeaseAdmissionClosed, match="is draining") as exc_info:
        ledger.acquire(_grant(grant_id="new", animator_name="titan"), priority=50)
    assert exc_info.value.animator_name == "titan"
    ledger.acquire(_grant(grant_id="other", animator_name="coding"), priority=50)

    ledger.end_drain(["titan"])

    assert ledger.admission("titan") is AnimatorAdmission.OPEN
    ledger.acquire(_grant(grant_id="new", animator_name="titan"), priority=50)


@pytest.mark.asyncio
async def test_drained_true_immediately_when_clear() -> None:
    ledger = LeaseLedger()
    assert await ledger.drained(["titan"], timeout=5.0) is True


@pytest.mark.asyncio
async def test_drained_wakes_on_release() -> None:
    ledger = LeaseLedger()
    ledger.acquire(_grant(grant_id="g1", animator_name="titan"), priority=50)

    async def _release_soon() -> None:
        await asyncio.sleep(0.01)
        ledger.release("g1")

    task = asyncio.create_task(_release_soon())
    assert await ledger.drained(["titan"], timeout=5.0) is True
    await task


@pytest.mark.asyncio
async def test_drained_false_on_timeout_with_survivor() -> None:
    ledger = LeaseLedger()
    ledger.acquire(_grant(grant_id="g1", animator_name="titan"), priority=50)
    assert await ledger.drained(["titan"], timeout=0.05) is False
