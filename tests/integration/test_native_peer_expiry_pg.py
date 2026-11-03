"""Disposable PostgreSQL expiry settlement through the complete migration lineage."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, tzinfo
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lychd.db.intercom import IntercomStoreError
from lychd.db.models.intercom import IntercomTask
from lychd.db.models.run import Run
from lychd.domain.intercom.native import PeerRunBinding
from tests.integration import test_db_run_ledger_pg as database
from tests.integration import test_intercom_pg as custody

pytestmark = [pytest.mark.integration, pytest.mark.container, pytest.mark.asyncio]
pg_url = database.pg_url
factory = custody.factory


async def test_expired_native_authorization_commits_only_local_settlement(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = await custody.seed(factory)
    async with factory() as session, session.begin():
        task = await session.get(IntercomTask, rig.task_id)
        assert task is not None
        binding = PeerRunBinding(
            request_id=uuid4(),
            declaration_id=task.declaration_id,
            operation_id=task.operation_id,
            peer_id=task.peer_id,
            purpose=task.purpose,
            task_schema=task.task_schema,
            endpoint="https://peer.example:443/a2a",
            source_digest="a" * 64,
            text_digest="b" * 64,
            expires_at=task.expires_at,
        )
        run = Run(
            id=uuid4(),
            workflow_name="native_public_peer",
            source="peer_public",
            status="queued",
            sigil_name="test:operator",
            queue_name="runs",
            intent={"admitted_peer": binding.model_dump(mode="json")},
            pattern_manifest={"digest": "c" * 64},
        )
        session.add(run)
        await session.flush()
        task.native_run_id, task.native_station = run.id, "peer_wait"
        task.native_request_id, task.native_binding_digest = binding.request_id, binding.digest
        task.native_pattern_digest, task.native_enqueue_seq = "c" * 64, 0
        task.native_step_id, task.native_occurrence_id = str(uuid4()), str(uuid4())
        await session.flush()
        run.peer_task_id, run.status = task.id, "awaiting_peer"
        run_id, expiry = run.id, task.expires_at

    class ExpiredClock(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> datetime:
            return (expiry + timedelta(seconds=1)).astimezone(tz)

    monkeypatch.setattr("lychd.db.intercom.datetime", ExpiredClock)
    record = {
        "subject": "synthetic-operator",
        "authentication_generation": str(uuid4()),
        "actions": ["adopt", "resume"],
        "reaffirm_public_source": False,
        "authorized_at": datetime.now(UTC).isoformat(),
        "binding_digest": binding.digest,
    }
    checks = 0

    def current() -> None:
        nonlocal checks
        checks += 1

    await rig.store.record_native_authorization(str(run_id), rig.task_id, record, current=current)
    assert checks == 2
    for action in ("submit", "poll", "read"):
        with pytest.raises(IntercomStoreError, match="closed"):
            await rig.store.record_native_authorization(
                str(run_id), rig.task_id, {**record, "actions": ["adopt", "resume", action]}, current=current
            )
    async with factory() as session, session.begin():
        task = await session.get(IntercomTask, rig.task_id)
        assert task is not None
        assert task.native_reauthorizations == [record]
        assert task.expires_at == expiry
        task.adoption_closed = True
    with pytest.raises(IntercomStoreError, match="closed"):
        await rig.store.record_native_authorization(str(run_id), rig.task_id, record, current=current)
    async with factory() as session:
        task = await session.get(IntercomTask, rig.task_id)
        assert task is not None
        assert task.native_reauthorizations == [record]
    assert not await custody.capacities(factory)
