"""The real edge pipe gates source work on this admitted audience's delivered plan."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from lychd.compositions.reach.operator_wire import ReachWorkerResult, protocol_bytes
from lychd.compositions.reach.research_wire import ReachResearchProgress
from lychd.interface.discord import live
from lychd.interface.discord.rest import EffectResult
from tests.unit.interface.test_nadir_dialogue import direct_message, policy, worker


@pytest.mark.asyncio
@pytest.mark.parametrize("plan_delivered", [False, True])
async def test_research_progress_is_acknowledged_only_after_same_dm_delivery(
    monkeypatch: pytest.MonkeyPatch, *, plan_delivered: bool
) -> None:
    configured, message = policy(), direct_message()
    readiness = worker(configured).ready.model_copy(
        update={"model_binding_digest": "b" * 64, "adaptive_context": True, "research_enabled": True}
    )
    reader = asyncio.StreamReader()
    frames: list[dict[str, Any]] = []
    timeline: list[str] = []

    class Output:
        def write(self, data: bytes) -> None:
            value = json.loads(data)
            frames.append(value)
            if value["kind"] == "request":
                timeline.append("request")
                progress = ReachResearchProgress(
                    call_id=str(uuid4()),
                    request_id=value["request_id"],
                    binding_digest="b" * 64,
                    text="I will read the Lich documentation and compare the approved public source.",
                )
                reader.feed_data(progress.model_dump_json().encode() + b"\n")
            else:
                assert value["kind"] == "progress_ack"
                assert value["accepted"] is plan_delivered
                timeline.append("receipt")
                result = ReachWorkerResult(
                    request_id=value["request_id"],
                    status="conversation" if plan_delivered else "clarify",
                    text="A sourced answer." if plan_delivered else "The source work did not begin.",
                    policy_digest=readiness.policy_digest,
                    corpus_digest=readiness.corpus_digest,
                    model_binding_digest=readiness.model_binding_digest,
                )
                reader.feed_data(protocol_bytes(result))

        def flush(self) -> None:
            pass

    async def send(_channel: str, _text: str, **kwargs: Any) -> EffectResult:
        assert _channel == "204"
        assert kwargs["event_id"] == kwargs["reply_to"] == "110"
        timeline.append(kwargs["phase"])
        if kwargs["phase"] == "plan":
            assert kwargs["silent"] is True
            return EffectResult(status="succeeded" if plan_delivered else "unknown")
        return EffectResult(status="succeeded")

    pipe = live.PipeWorker(reader, readiness)
    rest = Mock(bind_direct_channel=AsyncMock(), send_message=AsyncMock(side_effect=send))
    service = live.ReachService(
        configured, pipe, rest, admin_users=frozenset(), history_enabled=False, conversation=True
    )
    cog = live.ReachCog(service)
    with monkeypatch.context() as scoped:
        scoped.setattr(live.sys, "stdout", SimpleNamespace(buffer=Output()))
        await cog.on_message(message)
    assert timeline == ["ack", "request", "plan", "receipt", "final"]
    assert [frame["kind"] for frame in frames] == ["request", "progress_ack"]
    assert pipe.available


@pytest.mark.asyncio
async def test_foreign_progress_never_reaches_discord_and_fences_pipe(monkeypatch: pytest.MonkeyPatch) -> None:
    configured, message = policy(), direct_message()
    readiness = worker(configured).ready.model_copy(
        update={"model_binding_digest": "b" * 64, "adaptive_context": True, "research_enabled": True}
    )
    reader = asyncio.StreamReader()
    reader.feed_data(
        ReachResearchProgress(call_id=str(uuid4()), request_id="foreign", binding_digest="b" * 64, text="Foreign plan.")
        .model_dump_json()
        .encode()
        + b"\n"
    )
    pipe = live.PipeWorker(reader, readiness)
    callback = AsyncMock(return_value=True)
    pipe.progress = callback
    event = live.event_from_message(message, configured, conversation=True)
    assert event is not None
    with monkeypatch.context() as scoped:
        scoped.setattr(live.sys, "stdout", SimpleNamespace(buffer=Mock()))
        with pytest.raises(ValueError, match="worker_progress_binding"):
            await pipe.request(event, ())
    callback.assert_not_awaited()
    assert not pipe.available
