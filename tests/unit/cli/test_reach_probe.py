"""Headless operator boundaries use synthetic frames, without model or OCI access."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from scripts import reach_probe as probe
from scripts.reach_trace_archive import TraceArchive, query_archive

from lychd.compositions.reach.documents import read_research_document
from lychd.compositions.reach.operator_model_wire import (
    OperatorConversationProfile,
    OperatorModelRequest,
    OperatorModelResponse,
    canonical_json,
)
from lychd.compositions.reach.operator_trace import ReachTraceEvent, TraceCorrelation, trace_bytes
from lychd.compositions.reach.operator_wire import ReachWorkerReady, ReachWorkerResult, protocol_bytes
from lychd.compositions.reach.policy import prepare_turn
from lychd.compositions.reach.research_wire import OperatorResearchRequest, ResearchOptions
from tests.unit.compositions.test_reach_documents import make_corpus

CANARY = "private persona provider body or source text"
IMAGE = "sha256:" + "a" * 64


@pytest.fixture
def turn(tmp_path: Path) -> Any:
    scenario = probe.Scenario(question="What is LychD?")
    policy, request = probe.make_request(scenario, datetime.now(UTC))
    profile = OperatorConversationProfile(
        persona_name="Fixture",
        persona_instructions=CANARY,
        adaptive_context=True,
        research=ResearchOptions(enabled=True),
    )
    archive = TraceArchive(tmp_path / "traces")
    value = probe.Turn(scenario, policy, request, profile, make_corpus(), archive)
    yield value
    archive.close()


def ready(turn: probe.Turn) -> None:
    turn.accept_ready(
        ReachWorkerReady(
            generation=str(uuid4()),
            started_at=datetime.now(UTC),
            policy_digest=turn.policy.digest,
            corpus_digest=turn.corpus.digest,
            model_binding_digest=turn.profile.digest,
            adaptive_context=True,
            research_enabled=True,
        )
    )


@pytest.mark.parametrize("direct", [False, True])
def test_ready_refreshes_synthetic_event_and_history_after_startup_preserving_identity(
    turn: probe.Turn, *, direct: bool
) -> None:
    turn.scenario = probe.Scenario(
        question="The same question after startup",
        direct=direct,
        history=(
            probe.HistoryItem(text="Earlier question", age_seconds=17),
            probe.HistoryItem(text="Earlier answer", speaker="agent", age_seconds=5),
        ),
    )
    started_at = datetime.now(UTC) + timedelta(seconds=1)
    turn.policy, turn.request = probe.make_request(turn.scenario, started_at - timedelta(minutes=1))
    original_policy, original_request = turn.policy, turn.request
    turn.accept_ready(
        ReachWorkerReady(
            generation=str(uuid4()),
            started_at=started_at,
            policy_digest=turn.policy.digest,
            corpus_digest=turn.corpus.digest,
            model_binding_digest=turn.profile.digest,
            adaptive_context=True,
            research_enabled=True,
        )
    )
    assert turn.request.request_id == original_request.request_id
    assert turn.policy == original_policy
    assert turn.request.event.occurred_at >= started_at
    assert turn.request.event.model_dump(exclude={"occurred_at"}) == original_request.event.model_dump(
        exclude={"occurred_at"}
    )
    for item, original, specification in zip(
        turn.request.history, original_request.history, turn.scenario.history, strict=True
    ):
        assert item.model_dump(exclude={"occurred_at"}) == original.model_dump(exclude={"occurred_at"})
        assert turn.request.event.occurred_at - item.occurred_at == timedelta(seconds=specification.age_seconds)


def correlation(turn: probe.Turn) -> TraceCorrelation:
    assert turn.ready is not None
    return TraceCorrelation(
        generation=turn.ready.generation, request_id=turn.request.request_id, run_id=turn.run_id or str(uuid4())
    )


def generation(turn: probe.Turn, prompt: dict[str, Any]) -> OperatorModelRequest:
    return OperatorModelRequest(
        call_id=str(uuid4()),
        binding_digest=turn.profile.digest,
        operation="generate",
        correlation=correlation(turn),
        payload_json=canonical_json(
            {
                "model": turn.profile.model_id,
                "messages": [
                    {"role": "system", "content": CANARY},
                    {"role": "user", "content": canonical_json(prompt)},
                ],
                "max_tokens": turn.profile.max_tokens,
                "temperature": turn.profile.temperature,
                "stream": False,
                "chat_template_kwargs": {"enable_thinking": False},
            }
        ),
    )


def planned(turn: probe.Turn, *, text: str = "Read the selected document.") -> OperatorResearchRequest:
    if turn.ready is None:
        ready(turn)
    source_id = f"doc:{turn.corpus.manifest.documents[0].path}"
    frame = generation(
        turn,
        {
            "question": turn.scenario.question,
            "research_phase": "planning",
            "available_research_sources": [{"id": source_id}],
        },
    )
    turn.before_model(frame)
    response = OperatorModelResponse(
        call_id=frame.call_id,
        binding_digest=turn.profile.digest,
        status="ok",
        payload_json=canonical_json(
            {
                "choices": [
                    {
                        "message": {
                            "content": canonical_json(
                                {
                                    "kind": "research",
                                    "text": text,
                                    "source_ids": [source_id],
                                }
                            )
                        }
                    }
                ]
            }
        ),
    )
    turn.after_model(frame, response)
    return OperatorResearchRequest(
        call_id=str(uuid4()),
        request_id=turn.request.request_id,
        binding_digest=turn.profile.digest,
        event=turn.request.event,
        plan="Read the selected document.",
        correlation=correlation(turn),
    )


@pytest.mark.parametrize("text", [" Read the selected document. ", "\nRead the selected document.\t"])
def test_plan_binding_matches_native_whitespace_normalization(turn: probe.Turn, text: str) -> None:
    request = planned(turn, text=text)
    assert turn.research(request).status == "ok"
    assert turn.plan == "Read the selected document."


@pytest.mark.parametrize("direct", [False, True])
def test_synthetic_policy_admits_channel_and_opted_in_dm(*, direct: bool) -> None:
    scenario = probe.Scenario(
        question="Hello", direct=direct, history=(probe.HistoryItem(text="Earlier", speaker="agent"),)
    )
    now = datetime.now(UTC)
    policy, request = probe.make_request(scenario, now)
    assert prepare_turn(policy, request.event, now=now).allowed
    assert request.event.trigger == ("message" if direct else "mention")
    assert request.history[0].subject_id == policy.agent_subject_id
    assert request.history[0].conversation_id == request.event.conversation_id


def test_scenario_rejects_duplicate_keys() -> None:
    with pytest.raises(ValueError, match="duplicate_key"):
        probe.strict_json(b'{"question":"a","question":"b"}')


def test_scenario_preserves_strict_boolean_shape() -> None:
    with pytest.raises(ValidationError, match="valid boolean"):
        probe.Scenario.model_validate_json(b'{"question":"x","direct":1}')


def test_bootstrap_probe_is_only_uncorrelated_exception(turn: probe.Turn) -> None:
    frame = OperatorModelRequest(
        call_id=str(uuid4()), binding_digest=turn.profile.digest, operation="probe", payload_json="{}"
    )
    turn.before_model(frame)
    with pytest.raises(probe.ProbeError, match="bootstrap"):
        turn.before_model(frame.model_copy(update={"call_id": str(uuid4())}))
    ready(turn)
    with pytest.raises(probe.ProbeError, match="correlation"):
        turn.before_model(frame.model_copy(update={"call_id": str(uuid4())}))


def test_ready_digests_and_request_correlation_are_exact(turn: probe.Turn) -> None:
    ready(turn)
    assert turn.ready is not None
    with pytest.raises(probe.ProbeError, match="ready_binding"):
        turn.accept_ready(turn.ready)
    with pytest.raises(probe.ProbeError, match="correlation"):
        turn.correlation(correlation(turn).model_copy(update={"request_id": str(uuid4())}))


@pytest.mark.parametrize("delivery", ["succeeded", "rejected", "unknown"])
def test_doc_plan_receipt_returns_only_exact_empty_web_response(turn: probe.Turn, delivery: str) -> None:
    turn.scenario = turn.scenario.model_copy(update={"plan_delivery": delivery})
    frame = planned(turn)
    response = turn.research(frame)
    assert response.status == ("ok" if delivery == "succeeded" else "refused")
    assert response.sources == ()
    assert (response.call_id, response.request_id, response.binding_digest) == (
        frame.call_id,
        frame.request_id,
        frame.binding_digest,
    )
    with pytest.raises(probe.ProbeError, match="research_binding"):
        turn.research(frame)


def test_plan_text_event_and_binding_cannot_be_substituted(turn: probe.Turn) -> None:
    frame = planned(turn)
    for changed in (
        frame.model_copy(update={"plan": "Different plan"}),
        frame.model_copy(update={"binding_digest": "f" * 64}),
        frame.model_copy(update={"event": frame.event.model_copy(update={"question": "Different"})}),
    ):
        with pytest.raises(probe.ProbeError, match="research_binding"):
            turn.research(changed)


def test_any_web_selection_refuses_without_fabricated_evidence(turn: probe.Turn) -> None:
    frame = planned(turn)
    with pytest.raises(probe.ProbeError, match="web_refused"):
        turn.research(frame.model_copy(update={"source_ids": ("example",)}))
    assert not turn.reads


def test_synthesis_retains_exact_projection_metadata_without_source_bodies(turn: probe.Turn) -> None:
    turn.research(planned(turn))
    source = read_research_document(turn.corpus, turn.planned_ids[0], question=turn.scenario.question)
    record = source.model_dump(mode="json")
    record.update({"projection_digest": source.text_digest, "projection_truncated": False})
    prompt = {
        "question": turn.scenario.question,
        "research_phase": "synthesis",
        "research_request_id": turn.request.request_id,
        "research_plan": turn.plan,
        "corpus_digest": turn.corpus.digest,
        "research_sources": [record],
        "omitted_recent_messages": 0,
    }
    turn.before_model(generation(turn, prompt))
    assert turn.reads[0]["source_digest"] == source.source_digest
    assert turn.reads[0]["projection_digest"] == source.text_digest
    assert "text" not in turn.reads[0]
    assert turn.debug == []


def test_rejected_plan_forbids_synthesis_and_source_read(turn: probe.Turn) -> None:
    turn.scenario = turn.scenario.model_copy(update={"plan_delivery": "rejected"})
    turn.research(planned(turn))
    with pytest.raises(probe.ProbeError, match="synthesis_binding"):
        turn.before_model(generation(turn, {"question": turn.scenario.question, "research_phase": "synthesis"}))
    turn.capture.child(
        ReachTraceEvent(
            producer="core",
            name="source_read",
            request_id=turn.request.request_id,
            run_id=turn.run_id,
            source_id=turn.planned_ids[0],
            status="ok",
        ),
        "core",
    )
    assert "read_before_delivery" in turn.oracle()


@pytest.mark.asyncio
async def test_diagnostics_binds_core_custody_and_ignores_bounded_warning_bodies(turn: probe.Turn) -> None:
    reader = asyncio.StreamReader()
    reader.feed_data(CANARY.encode() + b"\n")
    reader.feed_eof()
    await turn.diagnostics(reader)
    assert turn.unstructured_diagnostics == 1
    forged = asyncio.StreamReader()
    forged.feed_data(trace_bytes(ReachTraceEvent(producer="host", name="session_finished")))
    forged.feed_eof()
    with pytest.raises(probe.ProbeError, match="trace_custody"):
        await turn.diagnostics(forged)
    assert turn.archive.flush()
    assert CANARY not in json.dumps(query_archive(turn.archive.directory))


def test_foreign_run_source_metadata_cannot_satisfy_oracle(turn: probe.Turn) -> None:
    turn.research(planned(turn))
    turn.capture.child(
        ReachTraceEvent(
            producer="core",
            name="source_read",
            request_id=turn.request.request_id,
            run_id=str(uuid4()),
            source_id=turn.planned_ids[0],
            status="ok",
        ),
        "core",
    )
    assert "trace_binding" in turn.oracle()


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        (b'{"kind":"result","kind":"ready"}\n', "duplicate_key"),
        (b"{" + b"a" * probe.MAX_WIRE_BYTES + b"\n", "probe_frame_budget"),
        (b"truncated", "probe_truncated_frame"),
    ],
)
@pytest.mark.asyncio
async def test_malformed_overlong_and_partial_frames_refuse(raw: bytes, code: str) -> None:
    reader = asyncio.StreamReader(limit=probe.MAX_WIRE_BYTES)
    reader.feed_data(raw)
    reader.feed_eof()
    with pytest.raises(ValueError, match=code):
        probe.strict_json(await probe.read_line(reader))


class Writer:
    def write(self, _raw: bytes) -> None:
        pass

    async def drain(self) -> None:
        pass

    def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_post_result_frames_refuse(turn: probe.Turn) -> None:
    ready(turn)
    result = ReachWorkerResult(
        request_id=turn.request.request_id,
        status="error",
        policy_digest=turn.policy.digest,
        corpus_digest=turn.corpus.digest,
        model_binding_digest=turn.profile.digest,
    )
    reader = asyncio.StreamReader()
    reader.feed_data(protocol_bytes(result) + protocol_bytes(result))
    reader.feed_eof()
    process = cast("asyncio.subprocess.Process", type("Process", (), {"stdin": Writer(), "stdout": reader})())
    with pytest.raises(probe.ProbeError, match="after_result"):
        await probe.exchange(turn, process, cast("Any", None))


@pytest.mark.asyncio
async def test_timeout_retires_process_and_exact_owned_cid(
    turn: probe.Turn,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Process:
        stdin = Writer()
        stdout = asyncio.StreamReader()
        stderr = asyncio.StreamReader()
        returncode = None

    process = Process()
    process.stderr.feed_eof()
    spawning = AsyncMock(return_value=process)
    retire, remove = AsyncMock(), AsyncMock()
    monkeypatch.setattr(probe.asyncio, "create_subprocess_exec", spawning)
    monkeypatch.setattr(probe.operator, "retire", retire)
    monkeypatch.setattr(probe.operator, "remove_owned", remove)
    cid = tmp_path / "core.cid"
    cid.write_text("a" * 64)
    with pytest.raises(TimeoutError):
        await probe.supervise(turn, ["engine"], cid, engine="docker", model_transport="http", budget_seconds=0.01)
    retire.assert_awaited_once_with(process)
    remove.assert_awaited_once_with("docker", cid)
    assert turn.cleanup["container_id"] == "a" * 64
    assert turn.cleanup["container_removed"]


def test_uncertain_cleanup_retains_private_workspace(tmp_path: Path) -> None:
    with probe.workspace(tmp_path, {"process_retired": True, "container_removed": False}) as frozen:
        probe.operator.write_private(frozen / "core.cid", b"a" * 64)
    assert frozen.is_dir()
    assert (frozen / "core.cid").stat().st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_missing_cid_after_engine_spawn_retains_uncertainty_without_global_cleanup(
    turn: probe.Turn,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = cast("asyncio.subprocess.Process", object())
    retire, remove = AsyncMock(), AsyncMock()
    monkeypatch.setattr(probe.operator, "retire", retire)
    monkeypatch.setattr(probe.operator, "remove_owned", remove)
    with probe.workspace(tmp_path, turn.cleanup) as frozen:
        probe.operator.write_private(frozen / "policy.json", b"{}")
        with pytest.raises(probe.ProbeError, match="container_identity_missing"):
            await probe.cleanup_owned(turn, process, frozen / "core.cid", "docker", [])
    retire.assert_awaited_once_with(process)
    remove.assert_not_awaited()
    assert turn.cleanup["process_retired"]
    assert turn.cleanup["container_removed"] is False
    assert turn.cleanup["container_id"] is None
    assert turn.cleanup["retained_workspace"] == str(frozen)
    assert frozen.is_dir()
    assert (frozen / "policy.json").stat().st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_repeated_cancellation_joins_spawn_then_cleanup(
    turn: probe.Turn,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spawn_started, spawn_release, cleanup_started, cleanup_release = (asyncio.Event() for _ in range(4))
    process = cast("asyncio.subprocess.Process", object())

    async def spawn(*args: Any, **kwargs: Any) -> asyncio.subprocess.Process:
        spawn_started.set()
        await spawn_release.wait()
        return process

    async def retire(_process: asyncio.subprocess.Process) -> None:
        cleanup_started.set()
        await cleanup_release.wait()

    remove = AsyncMock()
    monkeypatch.setattr(probe.asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(probe.operator, "retire", retire)
    monkeypatch.setattr(probe.operator, "remove_owned", remove)
    cid = tmp_path / "core.cid"
    cid.write_text("a" * 64)
    task = asyncio.create_task(
        probe.supervise(turn, ["engine"], cid, engine="docker", model_transport="http", budget_seconds=5)
    )
    await spawn_started.wait()
    task.cancel()
    await asyncio.sleep(0)
    task.cancel()
    spawn_release.set()
    await cleanup_started.wait()
    task.cancel()
    await asyncio.sleep(0)
    task.cancel()
    cleanup_release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    remove.assert_awaited_once_with("docker", cid)
    assert turn.cleanup["process_retired"]
    assert turn.cleanup["container_removed"]


def test_parser_never_echoes_private_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        probe.main(["--private", CANARY])
    assert CANARY not in capsys.readouterr().err
