"""The real native operator dispatcher keeps settled failures local to a command."""
# pyright: reportPrivateUsage=false
# pyright: reportArgumentType=false

from __future__ import annotations

from dataclasses import replace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from scripts.intercom_native_lab import NativeLabQueue, NativePeerRuntime, operate_native

from lychd.db.sessions import DbBridgeSessionStore
from lychd.domain.codex.peer import PeerAuthorityError
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.substrate import reset_run_substrate, set_run_substrate
from lychd.domain.intercom.native import PeerTaskOutcomeError
from tests.unit.system.services.test_peer_runs import rig


async def _runtime() -> tuple[Any, ...]:
    peer, engine, substrate, ledger, custody, authority, marker, handle, intercom = await rig()
    queue = NativeLabQueue()
    substrate.queues = {"runs": queue}
    engine.queues = substrate.queues
    runtime = NativePeerRuntime(peer, engine, substrate, cast("DbBridgeSessionStore", substrate.turns), queue)
    set_run_substrate(substrate)
    await runtime.run_once(handle.run_id)
    return runtime, ledger, custody, authority, marker, handle, intercom


@pytest.mark.asyncio
async def test_unknown_tick_returns_settled_outcome_then_accepts_another_operator_command() -> None:
    runtime, ledger, custody, _, marker, handle, _ = await _runtime()
    try:
        result = await operate_native(runtime, marker, {"operation": "tick", "run_id": handle.run_id})
        assert result["status"] == "failed"
        assert result["outcome"] == "unknown"
        assert result["tasks"][0]["remote_outcome_unknown"] is True
        assert "reply" not in result
        assert "source" not in result
        assert custody.claims == 1
        assert (await ledger.get(handle.run_id)).status is RunStatus.FAILED
        again = await operate_native(runtime, marker, {"operation": "status", "run_id": handle.run_id})
        assert again["status"] == "failed"
        assert "reply" not in again
        assert custody.claims == 1
    finally:
        await runtime.substrate.bus.aclose()
        reset_run_substrate()


@pytest.mark.asyncio
async def test_remote_noncompletion_tick_returns_only_local_outcome_and_metadata() -> None:
    runtime, ledger, custody, _, marker, handle, _ = await _runtime()
    try:
        run = await ledger.get(handle.run_id)
        custody.terminal(UUID(run.peer_task_id))
        task = custody.tasks[UUID(run.peer_task_id)]
        task["foreign_status"] = "TASK_STATE_FAILED"
        task["settlement"]["foreign_status"] = "TASK_STATE_FAILED"
        custody.terminals[UUID(run.peer_task_id)]["settlement"]["foreign_status"] = "TASK_STATE_FAILED"
        custody.transmissions[UUID(run.peer_task_id)]["settlement"]["foreign_status"] = "TASK_STATE_FAILED"
        result = await operate_native(runtime, marker, {"operation": "tick", "run_id": handle.run_id})
        assert result["status"] == "failed"
        assert result["outcome"] == "remote_noncompletion"
        assert "Public companion planning answer." not in str(result)
        assert "reply" not in result
    finally:
        await runtime.substrate.bus.aclose()
        reset_run_substrate()


@pytest.mark.asyncio
async def test_normal_completed_result_still_requires_separate_current_read_permission() -> None:
    runtime, ledger, custody, authority, marker, handle, _ = await _runtime()
    try:
        run = await ledger.get(handle.run_id)
        custody.terminal(UUID(run.peer_task_id))
        result = await operate_native(runtime, marker, {"operation": "tick", "run_id": handle.run_id})
        assert result["status"] == "done"
        assert result["reply"] == "Public companion planning answer."
        authority.replace_policy(
            replace(
                authority.policy,
                generation=authority.policy.generation + 1,
                actions=authority.policy.actions - {"read"},
            )
        )
        inspection = await runtime.peer.status(marker, run_id=handle.run_id)
        assert inspection["status"] == "done"
        assert "reply" not in inspection
        with pytest.raises(PeerAuthorityError, match="policy"):
            await operate_native(runtime, marker, {"operation": "status", "run_id": handle.run_id})
    finally:
        await runtime.substrate.bus.aclose()
        reset_run_substrate()


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [RuntimeError("arbitrary worker failure"), PeerTaskOutcomeError("unexpected")])
async def test_tick_does_not_swallow_other_worker_failures(error: Exception, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime, _, _, _, marker, handle, _ = await _runtime()
    try:
        monkeypatch.setattr(runtime.peer, "drive_wait", AsyncMock(return_value=False))
        monkeypatch.setattr(runtime, "run_once", AsyncMock(side_effect=error))
        with pytest.raises(type(error)) as raised:
            await operate_native(runtime, marker, {"operation": "tick", "run_id": handle.run_id})
        assert raised.value is error
    finally:
        await runtime.substrate.bus.aclose()
        reset_run_substrate()


@pytest.mark.asyncio
async def test_known_outcome_without_durable_terminal_truth_is_not_reported_as_settled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, ledger, _, _, marker, handle, _ = await _runtime()
    try:
        monkeypatch.setattr(runtime.peer, "drive_wait", AsyncMock(return_value=False))
        monkeypatch.setattr(runtime, "run_once", AsyncMock(side_effect=PeerTaskOutcomeError("unknown")))
        with pytest.raises(PeerTaskOutcomeError, match="unknown"):
            await operate_native(runtime, marker, {"operation": "tick", "run_id": handle.run_id})
        assert (await ledger.get(handle.run_id)).status is RunStatus.AWAITING_PEER
        with pytest.raises(PeerAuthorityError, match="authentication"):
            await operate_native(runtime, replace(marker), {"operation": "status", "run_id": handle.run_id})
    finally:
        await runtime.substrate.bus.aclose()
        reset_run_substrate()
