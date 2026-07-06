"""O3: GhoulBroker (claim-gate pause + lease-count drain) and QuiescentBroker."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from lychd.domain.animation.capabilities import CapabilityLifecycle, CapabilitySpec, GrantLease
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.orchestration.broker import GhoulBroker, QuiescentBroker


def _spec(animator: str) -> CapabilitySpec:
    return CapabilitySpec(
        key=f"{animator}:chat:{animator}-m",
        animator_name=animator,
        runtime="llamacpp",
        source_kind="soulstone",
        family=CapabilityFamily.CHAT,
        model_id=f"{animator}-m",
        lifecycle=CapabilityLifecycle.DYNAMIC,
    )


@pytest.mark.asyncio
async def test_ghoul_broker_pause_toggles_claim_gate() -> None:
    broker = GhoulBroker(queues={}, leases=LeaseLedger())
    assert broker.paused is False
    assert broker.claim_gate.is_set() is True

    await broker.pause_queues()
    assert broker.paused is True
    assert broker.claim_gate.is_set() is False

    await broker.unpause_queues()
    assert broker.paused is False
    assert broker.claim_gate.is_set() is True


@pytest.mark.asyncio
async def test_ghoul_broker_counts_leases_not_jobs() -> None:
    leases = LeaseLedger()
    broker = GhoulBroker(queues={}, leases=leases)
    assert await broker.get_active_worker_count() == 0

    spec = _spec("titan")
    grant = SimpleNamespace(lease=GrantLease(grant_id="g1", holder="run:1", issued_at=datetime.now(UTC)), spec=spec)
    leases.acquire(grant, priority=50)  # type: ignore[arg-type]
    assert await broker.get_active_worker_count() == 1

    leases.release("g1")
    assert await broker.get_active_worker_count() == 0


@pytest.mark.asyncio
async def test_ghoul_broker_soft_stop_is_honest_noop() -> None:
    broker = GhoulBroker(queues={}, leases=LeaseLedger())
    assert await broker.broadcast_soft_stop() is None


@pytest.mark.asyncio
async def test_quiescent_broker_is_inert() -> None:
    broker = QuiescentBroker()
    await broker.pause_queues()
    await broker.broadcast_soft_stop()
    await broker.unpause_queues()
    assert await broker.get_active_worker_count() == 0
