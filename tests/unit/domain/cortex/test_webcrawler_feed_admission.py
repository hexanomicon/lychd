"""Actual in-memory RunEngine admission; fixture catalogue/retention/queue are not native delivery."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from lychd.agents.router import Intent
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.runs import RunDeliveryState, RunStatus
from lychd.domain.webcrawler.feed import WebcrawlerFeedBinding, WebcrawlerFeedDeclarationProof
from lychd.domain.webcrawler.profile import WebcrawlerWorkflowError
from tests.webcrawler_feed_fixtures import Scenario, scenario


class Queue:
    def __init__(self) -> None:
        self.enqueued: list[dict[str, Any]] = []

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any:
        self.enqueued.append({"function": job_or_func, **kwargs})
        return SimpleNamespace(key=kwargs["key"])

    async def job(self, job_key: str, /) -> Any:
        _ = job_key
        return None

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = job, error, ttl


class AdmissionCatalogue:
    """An inert manifest stub, deliberately not registered or executable Graph evidence."""

    def route(self, intent: Intent) -> Any:
        assert intent.source == "scavenger"
        return SimpleNamespace(
            name="scavenger.observe_market",
            manifest=SimpleNamespace(
                key="scavenger.observe_market",
                revision="2",
                snapshot=lambda: {"key": "scavenger.observe_market", "revision": "2", "synthetic_admission_only": True},
            ),
        )


@dataclass
class Setup:
    source: Scenario
    engine: RunEngine
    ledger: InMemoryRunLedger
    queue: Queue
    intent: Intent
    proof: WebcrawlerFeedDeclarationProof


async def setup() -> Setup:
    s = await scenario()
    ledger, queue = InMemoryRunLedger(), Queue()
    engine = RunEngine(
        ledger=ledger,
        bus=InProcessEventBus(ledger=ledger),
        workflows=AdmissionCatalogue(),
        queue_router=QueueRouter({"default": RouteRule(queue="runs", priority=50)}),
        queues={"runs": queue},
        feed_webcrawler=s.binding.profile,
        feed_webcrawler_admission=s.admission,
        bridge_capability_key="ordinary-bridge-chat-not-a-feed-demand",
    )
    intent = Intent(
        session_id=str(uuid4()),
        run_id="advisory-only",
        source="scavenger",
        prompt=str(s.binding.consumer.application_admission_id),
    )
    proof = s.admission.declare(
        consumer=s.binding.consumer,
        request_id=s.binding.request_id,
        deadline=datetime.now(UTC) + timedelta(hours=1),
        authentication=s.authentication,
    )
    return Setup(s, engine, ledger, queue, intent, proof)


@pytest.mark.asyncio
async def test_feed_run_is_held_until_receiving_owner_returns_and_never_borrows_chat_key() -> None:
    s = await setup()
    retained: list[str] = []

    async def retain(run_id: str) -> None:
        run = await s.ledger.get(run_id)
        assert run is not None
        delivery = await s.ledger.get_delivery(run_id, enqueue_seq=run.enqueue_seq)
        assert delivery is not None
        assert delivery.state is RunDeliveryState.HELD
        assert not s.queue.enqueued
        assert type(run.admitted_webcrawler) is WebcrawlerFeedBinding
        assert run.admitted_capability_key is None
        retained.append(run_id)

    first = await s.engine.submit(
        s.intent, feed_declaration=s.proof, retain_before_publish=retain, idempotency_key="synthetic-feed-request"
    )
    assert first.run_id != s.intent.run_id
    assert retained == [first.run_id]
    assert len(s.queue.enqueued) == 1
    run = await s.ledger.get(first.run_id)
    assert run is not None
    assert type(run.admitted_webcrawler) is WebcrawlerFeedBinding
    assert run.admitted_webcrawler.consumer == s.proof.consumer
    assert run.admitted_capability_key is None
    raw = run.to_intent().model_dump_json()
    assert Intent.model_validate_json(raw).admitted_webcrawler == run.admitted_webcrawler
    assert '"seed":' not in raw
    assert '"filter":' not in raw
    assert '"items":' not in raw


@pytest.mark.asyncio
async def test_feed_exact_replay_keeps_original_review_time_and_expiry_without_second_publication() -> None:
    s = await setup()

    async def retained(_run_id: str) -> None:
        return None

    first = await s.engine.submit(
        s.intent, feed_declaration=s.proof, retain_before_publish=retained, idempotency_key="synthetic-replay"
    )
    await asyncio.sleep(0)
    fresh = s.source.admission.declare(
        consumer=s.proof.consumer,
        request_id=s.proof.request_id,
        deadline=datetime.now(UTC) + timedelta(hours=1),
        authentication=s.source.authentication,
    )
    assert fresh.expires_at > s.proof.expires_at
    replay = await s.engine.submit(s.intent, feed_declaration=fresh, idempotency_key="synthetic-replay")
    assert replay.run_id == first.run_id
    run = await s.ledger.get(first.run_id)
    assert run is not None
    assert type(run.admitted_webcrawler) is WebcrawlerFeedBinding
    assert run.admitted_webcrawler.declaration.declared_at == s.proof.declaration.declared_at
    assert run.admitted_webcrawler.expires_at == s.proof.expires_at
    assert len(s.queue.enqueued) == 1
    changed = s.proof.consumer.model_validate(s.proof.consumer.model_dump() | {"seed_digest": "f" * 64})
    conflicting = s.source.admission.declare(
        consumer=changed,
        request_id=s.proof.request_id,
        deadline=datetime.now(UTC) + timedelta(hours=1),
        authentication=s.source.authentication,
    )
    with pytest.raises(WebcrawlerWorkflowError):
        await s.engine.submit(s.intent, feed_declaration=conflicting, idempotency_key="synthetic-replay")
    assert len(s.queue.enqueued) == 1


@pytest.mark.asyncio
async def test_feed_fresh_admission_without_seed_retention_owner_refuses_before_creation() -> None:
    s = await setup()
    created = AsyncMock(wraps=s.ledger.create)
    s.ledger.create = created
    with pytest.raises(WebcrawlerWorkflowError):
        await s.engine.submit(s.intent, feed_declaration=s.proof)
    created.assert_not_awaited()
    assert not s.queue.enqueued


@pytest.mark.asyncio
async def test_feed_revocation_after_commit_refuses_held_run_before_owner_callback() -> None:
    s = await setup()
    original = s.ledger.create
    created: list[str] = []

    async def create(*args: Any, **kwargs: Any) -> Any:
        run = await original(*args, **kwargs)
        created.append(run.run_id)
        s.source.access.revoke()
        return run

    s.ledger.create = create
    retain = AsyncMock()
    with pytest.raises(WebcrawlerWorkflowError):
        await s.engine.submit(s.intent, feed_declaration=s.proof, retain_before_publish=retain)
    retain.assert_not_awaited()
    assert len(created) == 1
    run = await s.ledger.get(created[0])
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert not s.queue.enqueued


@pytest.mark.asyncio
async def test_feed_revocation_during_retention_refuses_publication() -> None:
    s = await setup()
    retained: list[str] = []

    async def retain(run_id: str) -> None:
        retained.append(run_id)
        await asyncio.sleep(0)
        s.source.access.revoke()

    with pytest.raises(WebcrawlerWorkflowError):
        await s.engine.submit(s.intent, feed_declaration=s.proof, retain_before_publish=retain)
    assert len(retained) == 1
    run = await s.ledger.get(retained[0])
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert not s.queue.enqueued


@pytest.mark.asyncio
async def test_feed_wait_rechecks_authentication_before_any_new_run_commit() -> None:
    s = await setup()
    key = ("idempotency", "synthetic-wait")
    assert s.engine.admissions.begin(key)
    created = AsyncMock(wraps=s.ledger.create_idempotent)
    s.ledger.create_idempotent = created
    call = asyncio.create_task(
        s.engine.submit(s.intent, feed_declaration=s.proof, retain_before_publish=AsyncMock(), idempotency_key=key[1])
    )
    await asyncio.sleep(0)
    s.source.access.revoke()
    s.engine.admissions.finish(key)
    with pytest.raises(WebcrawlerWorkflowError):
        await call
    created.assert_not_awaited()
    assert not s.queue.enqueued


@pytest.mark.asyncio
async def test_feed_caller_cannot_submit_its_own_retained_binding_even_with_real_marker() -> None:
    s = await setup()
    binding = s.source.admission(s.intent, s.proof, s.source.binding.profile)
    with pytest.raises(ValueError, match="server-owned"):
        await s.engine.submit(
            s.intent.model_copy(update={"admitted_webcrawler": binding}),
            feed_declaration=s.proof,
            retain_before_publish=AsyncMock(),
        )
    assert not s.queue.enqueued
