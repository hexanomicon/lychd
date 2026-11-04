"""Independent neutral consumers exercise the native Run and delivered-plan boundary.

The synthetic transports below qualify shared choreography only. Source acquisition
and model execution are effect spies; no provider SDK or live network is involved.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import pytest
from pydantic_ai.models import override_allow_model_requests
from scripts import reach_research_broker as broker_module
from scripts.reach_worker import build_runtime

from lychd.compositions.reach import conversation_workflow
from lychd.compositions.reach.conversation_session import drive_context_turn
from lychd.compositions.reach.documents import CorpusDocument, CorpusManifest, PublicCorpus, verify_corpus
from lychd.compositions.reach.operator_client import PipeWorker
from lychd.compositions.reach.operator_model_wire import (
    OperatorConversationProfile,
    canonical_json,
    validate_generation_payload,
)
from lychd.compositions.reach.operator_wire import (
    HistoryState,
    ReachHistoryEntry,
    ReachWorkerRequest,
    ReachWorkerResult,
    ReachWorkerStatus,
    protocol_bytes,
)
from lychd.compositions.reach.research_wire import (
    OperatorResearchRequest,
    OperatorResearchResponse,
    ReachResearchAcknowledgement,
    ReachResearchProgress,
    ResearchOptions,
    ResearchRuntimeProfile,
    ResearchSource,
    SourceReadResult,
)
from lychd.compositions.reach.schemas import ReachEvent, ReachPolicy, ReachRule
from lychd.domain.cortex.events import RunEventKind
from lychd.domain.cortex.runs import RunStatus

NOW = datetime(2026, 11, 1, 12, tzinfo=UTC)
STARTED = NOW - timedelta(seconds=10)
PLATFORMS = ("test-wire-a", "test-wire-b")
SOURCE_TEXT = "A bounded external observation, retained only during synthesis."
PLAN = "I will compare the admitted document with the approved public guide."


def corpus() -> PublicCorpus:
    raw = b"# Graph\nNative serial Graph retains declared continuation state."
    revision = "a" * 40
    document = CorpusDocument(
        path="docs/graph.md",
        url=f"https://github.com/hexanomicon/lychd/blob/{revision}/docs/graph.md",
        sha256=sha256(raw).hexdigest(),
        file="000.md",
    )
    return verify_corpus(CorpusManifest(source_revision=revision, documents=(document,)), (raw,))


def policy(platform: str) -> ReachPolicy:
    return ReachPolicy(
        platform=platform,
        account_id=f"account/{platform}/opaque",
        agent_subject_id="agent/opaque",
        space_id="space/opaque",
        allowed_conversation_ids=("-9001" if platform == PLATFORMS[1] else "conversation/opaque",),
        rules=(ReachRule(name="operator", subject_ids=("sender/opaque",), actions=("converse",)),),
    )


def event(platform: str = PLATFORMS[0]) -> ReachEvent:
    return ReachEvent(
        platform=platform,
        account_id=policy(platform).account_id,
        event_id="event/opaque",
        space_id="space/opaque",
        conversation_id=policy(platform).allowed_conversation_ids[0],
        subject_id="sender/opaque",
        mention_subject_ids=("agent/opaque",),
        trigger="mention",
        action="converse",
        question="Compare the Graph continuation document with the public guide.",
        occurred_at=NOW - timedelta(seconds=1),
    )


def completion(text: str) -> str:
    return canonical_json(
        {
            "id": "neutral-local-completion",
            "object": "chat.completion",
            "created": 1,
            "model": "Qwen3.8-27B",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
        }
    )


class NativeLoop:
    """Connect the real native worker, host broker and neutral pipe in memory."""

    def __init__(self, root: Path, platform: str, monkeypatch: pytest.MonkeyPatch) -> None:
        self.event = event(platform)
        self.policy = policy(platform)
        self.corpus = corpus()
        research = ResearchOptions(
            enabled=True,
            sources=(ResearchSource(id="guide", title="Public guide", url="https://public.example/guide"),),
        )
        self.binding = OperatorConversationProfile(
            persona_name="Nadir",
            persona_instructions="Answer precisely from the supplied evidence.",
            adaptive_context=True,
            research=research,
        )
        authority, state = root / "authority", root / "state"
        authority.mkdir(mode=0o700)
        state.mkdir(mode=0o700)
        runtime_profile = ResearchRuntimeProfile(
            source_kind="operator_public_catalogue",
            public_catalogue_authorized=True,
            policy_revision=1,
            revocation_generation=0,
            expires_at=NOW + timedelta(minutes=10),
            catalogue=research,
            allowed_subject_ids=(self.event.subject_id,),
            allowed_channel_ids=(self.event.conversation_id,),
            resolver_address="1.1.1.1",
            resolver_custody_statement="The operator selects this fixed public resolver.",
        )
        path = authority / "profile.json"
        path.write_text(runtime_profile.model_dump_json(), encoding="utf-8")
        path.chmod(0o600)
        monkeypatch.setattr(broker_module, "_now", lambda: NOW)
        monkeypatch.delenv("DOCKER_HOST", raising=False)
        self.broker = broker_module.OperatorResearchBroker(
            self.binding,
            self.policy,
            runtime_profile_path=path,
            state_dir=state,
            image="sha256:" + "a" * 64,
        )
        self.timeline: list[str] = []
        self.frames: list[dict[str, Any]] = []
        self.scout_calls: list[OperatorResearchRequest] = []
        self.document_reads: list[str] = []
        self.model_run_ids: list[str] = []
        self.delivery: Literal["succeeded", "rejected", "unknown", "cancelled"] = "succeeded"
        self.progress_shape: Literal["ordinary", "foreign", "duplicate"] = "ordinary"
        self.progress_frame: bytes | None = None
        self.tasks: list[asyncio.Task[None]] = []
        self.reader = asyncio.StreamReader()
        original_read = conversation_workflow.read_research_document

        def read_document(
            selected: PublicCorpus,
            source_id: str,
            *,
            question: str,
            focus: str = "",
            reference_labels: tuple[str, ...] = (),
            projection_mode: Literal["balanced", "complete_quotes"] | None = None,
        ) -> SourceReadResult:
            self.timeline.append("document")
            self.document_reads.append(source_id)
            assert self.timeline[:4] == ["model_plan", "delivered_plan", "ack", "scout"]
            assert focus == PLAN
            assert reference_labels == ()
            return original_read(
                selected,
                source_id,
                question=question,
                focus=focus,
                reference_labels=reference_labels,
                projection_mode=projection_mode,
            )

        monkeypatch.setattr(conversation_workflow, "read_research_document", read_document)
        monkeypatch.setattr(self.broker, "_scout", self.scout)
        self.runtime = build_runtime(
            self.policy,
            self.corpus,
            profile=self.binding,
            model_relay=self.model,
            research_relay=self.research,
            started_at=STARTED,
            clock=lambda: NOW,
        )
        self.client = PipeWorker(self.reader, self.runtime.ready, write_frame=self.write_frame)
        self.client.progress = self.deliver_plan

    async def model(self, operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [self.binding.model_id]})
        body = validate_generation_payload(self.binding, payload)
        assert "tools" not in body
        sessions = await self.runtime.sessions.list_sessions()
        assert len(sessions) == 1
        runs = await self.runtime.substrate.ledger.list_for_session(sessions[0].id)
        assert len(runs) == 1
        self.model_run_ids.append(runs[0].run_id)
        prompt = json.loads(body["messages"][-1]["content"])
        if len(self.model_run_ids) == 1:
            self.timeline.append("model_plan")
            assert SOURCE_TEXT not in payload
            assert prompt["research_phase"] == "planning"
            return completion(
                canonical_json({"kind": "research", "text": PLAN, "source_ids": ["web:guide", "doc:docs/graph.md"]})
            )
        self.timeline.append("model_synthesize")
        assert prompt["research_phase"] == "synthesis"
        assert {item["id"] for item in prompt["research_sources"]} == {"web:guide", "doc:docs/graph.md"}
        assert SOURCE_TEXT in payload
        assembled = self.runtime.substrate.context.get(runs[0].run_id)
        assert assembled is not None
        assert SOURCE_TEXT not in assembled.query
        return completion(
            canonical_json(
                {
                    "kind": "answer",
                    "text": "The evidence describes bounded continuation.",
                    "citations": ["web:guide", "doc:docs/graph.md"],
                }
            )
        )

    async def scout(self, request: OperatorResearchRequest) -> tuple[SourceReadResult, ...]:
        assert self.timeline == ["model_plan", "delivered_plan", "ack"]
        assert request.event == self.event
        self.timeline.append("scout")
        self.scout_calls.append(request)
        if self.progress_shape == "duplicate":
            assert self.progress_frame is not None
            self.reader.feed_data(self.progress_frame)
        return (
            SourceReadResult(
                id="web:guide",
                title="Public guide",
                url="https://public.example/guide",
                status="ok",
                text=SOURCE_TEXT,
                source_digest="c" * 64,
                text_digest=sha256(SOURCE_TEXT.encode()).hexdigest(),
                source_chars=len(SOURCE_TEXT),
                receipt_id="d" * 64,
            ),
        )

    async def research(self, request: OperatorResearchRequest) -> OperatorResearchResponse:
        async def send_progress(progress: ReachResearchProgress) -> None:
            if self.progress_shape == "foreign":
                progress = progress.model_copy(update={"request_id": "foreign/request"})
            frame = progress.model_dump_json().encode() + b"\n"
            self.progress_frame = frame
            self.reader.feed_data(frame)

        return await self.broker.handle(request, send_progress)

    async def deliver_plan(self, observed: ReachEvent, progress: ReachResearchProgress) -> bool:
        assert observed == self.event
        assert progress.text == PLAN
        assert self.scout_calls == self.document_reads == []
        self.timeline.append("delivered_plan")
        if self.delivery == "cancelled":
            raise asyncio.CancelledError
        return self.delivery == "succeeded"

    def write_frame(self, raw: bytes) -> None:
        frame = json.loads(raw)
        self.frames.append(frame)
        if frame["kind"] == "progress_ack":
            self.timeline.append("ack")
            self.broker.acknowledge(ReachResearchAcknowledgement.model_validate_json(raw))
            return
        assert frame["kind"] == "request"
        request = ReachWorkerRequest.model_validate_json(raw)

        async def execute() -> None:
            result = await self.runtime.process(request)
            self.reader.feed_data(protocol_bytes(result))

        self.tasks.append(asyncio.create_task(execute()))

    async def close(self) -> None:
        for task in self.tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        await self.runtime.aclose()


@pytest.fixture
def native_loop(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[str], NativeLoop]]:
    # Keep private broker fixtures outside both the source tree and OCI /work.
    with tempfile.TemporaryDirectory(prefix="reach-neutral-", dir="/tmp") as temporary:
        root = Path(temporary)

        def create(platform: str) -> NativeLoop:
            target = root / platform
            target.mkdir(mode=0o700)
            return NativeLoop(target, platform, monkeypatch)

        yield create


@pytest.mark.parametrize("platform", PLATFORMS)
@pytest.mark.asyncio
async def test_independent_neutral_edges_share_native_research_graph_and_exact_plan_receipt(
    platform: str, native_loop: Callable[[str], NativeLoop]
) -> None:
    loop = native_loop(platform)
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - all model requests use the in-memory relay
            result = await drive_context_turn(loop.client, loop.event, Pager([((), "disabled")]))
        assert result.status == "conversation"
        assert result.run_id is not None
        assert loop.model_run_ids == [result.run_id, result.run_id]
        assert loop.timeline == [
            "model_plan",
            "delivered_plan",
            "ack",
            "scout",
            "document",
            "model_synthesize",
        ]
        assert [frame["kind"] for frame in loop.frames] == ["request", "progress_ack"]
        assert loop.frames[-1]["accepted"] is True
        assert len(loop.scout_calls) == 1
        assert loop.document_reads == ["doc:docs/graph.md"]
        run = await loop.runtime.substrate.ledger.get(result.run_id)
        assert run is not None
        assert run.status is RunStatus.DONE
        assert run.pattern_manifest["key"] == "reach.operator_converse"
        assert run.pattern_manifest["revision"] == "8"
        events = await loop.runtime.substrate.ledger.list_events(result.run_id)
        assert {item.data for item in events if item.kind is RunEventKind.NODE} == {
            "revalidate",
            "generate",
            "research",
            "settle",
        }
        assert loop.runtime.substrate.leases.active() == []
        assert "https://public.example/guide" in result.text
        assert SOURCE_TEXT not in result.text
        assert loop.client.available
    finally:
        await loop.close()


@pytest.mark.parametrize("delivery", ["rejected", "unknown"])
@pytest.mark.asyncio
async def test_unconfirmed_plan_delivery_prevents_both_web_and_local_document_reads(
    delivery: Literal["rejected", "unknown"], native_loop: Callable[[str], NativeLoop]
) -> None:
    loop = native_loop(PLATFORMS[0])
    loop.delivery = delivery
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - all model requests use the in-memory relay
            result = await loop.client.request(loop.event, ())
        assert result.status == "error"
        assert loop.timeline == ["model_plan", "delivered_plan", "ack"]
        assert loop.frames[-1]["accepted"] is False
        assert loop.scout_calls == loop.document_reads == []
        assert len(loop.model_run_ids) == 1
    finally:
        await loop.close()


@pytest.mark.asyncio
async def test_foreign_progress_fences_the_client_without_acknowledgement_or_acquisition(
    native_loop: Callable[[str], NativeLoop],
) -> None:
    loop = native_loop(PLATFORMS[0])
    loop.progress_shape = "foreign"
    try:
        with (
            override_allow_model_requests(True),  # noqa: FBT003 - all model requests use the in-memory relay
            pytest.raises(ValueError, match="worker_progress_binding"),
        ):
            await loop.client.request(loop.event, ())
        assert not loop.client.available
    finally:
        await loop.close()
    assert [frame["kind"] for frame in loop.frames] == ["request"]
    assert loop.scout_calls == loop.document_reads == []
    assert len(loop.model_run_ids) == 1
    assert loop.timeline.count("delivered_plan") == 0


@pytest.mark.asyncio
async def test_duplicate_progress_fences_the_client_after_the_first_acknowledgement_permits_acquisition(
    native_loop: Callable[[str], NativeLoop],
) -> None:
    loop = native_loop(PLATFORMS[0])
    loop.progress_shape = "duplicate"
    try:
        with (
            override_allow_model_requests(True),  # noqa: FBT003 - all model requests use the in-memory relay
            pytest.raises(ValueError, match="worker_progress_binding"),
        ):
            await loop.client.request(loop.event, ())
        assert not loop.client.available
    finally:
        await loop.close()
    assert [frame["kind"] for frame in loop.frames] == ["request", "progress_ack"]
    assert loop.frames[-1]["accepted"] is True
    assert len(loop.scout_calls) == 1
    assert loop.timeline[:4] == ["model_plan", "delivered_plan", "ack", "scout"]
    assert loop.timeline.count("delivered_plan") == 1


@pytest.mark.asyncio
async def test_cancelled_plan_delivery_writes_no_ack_and_cannot_acquire(
    native_loop: Callable[[str], NativeLoop],
) -> None:
    loop = native_loop(PLATFORMS[0])
    loop.delivery = "cancelled"
    try:
        with (
            override_allow_model_requests(True),  # noqa: FBT003 - all model requests use the in-memory relay
            pytest.raises(asyncio.CancelledError),
        ):
            await loop.client.request(loop.event, ())
        assert not loop.client.available
    finally:
        await loop.close()
    assert [frame["kind"] for frame in loop.frames] == ["request"]
    assert loop.scout_calls == loop.document_reads == []


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("platform", "wrong_platform"),
        ("account_id", "wrong_account"),
        ("subject_id", "subject_not_allowed"),
        ("conversation_id", "conversation_not_allowed"),
    ],
)
@pytest.mark.asyncio
async def test_native_admission_keeps_neutral_platform_account_actor_and_place_binding(
    field: str, reason: str, native_loop: Callable[[str], NativeLoop]
) -> None:
    loop = native_loop(PLATFORMS[0])
    rejected = loop.event.model_copy(update={field: "foreign/opaque" if field != "platform" else PLATFORMS[1]})
    try:
        result = await loop.client.request(rejected, ())
        assert result.status == "refused"
        assert result.reason == reason
        assert result.run_id is None
        assert await loop.runtime.sessions.list_sessions() == []
        assert loop.model_run_ids == loop.scout_calls == loop.document_reads == []
        assert loop.timeline == []
    finally:
        await loop.close()


@pytest.mark.asyncio
async def test_real_broker_independently_refuses_a_foreign_neutral_conversation(
    native_loop: Callable[[str], NativeLoop],
) -> None:
    loop = native_loop(PLATFORMS[0])
    delivered: list[ReachResearchProgress] = []

    async def send(progress: ReachResearchProgress) -> None:
        delivered.append(progress)

    request = OperatorResearchRequest(
        call_id=str(uuid4()),
        request_id="foreign/place/request",
        binding_digest=loop.binding.digest,
        event=loop.event.model_copy(update={"conversation_id": "foreign/opaque"}),
        plan=PLAN,
        source_ids=("guide",),
    )
    try:
        response = await loop.broker.handle(request, send)
        assert response.status == "refused"
        assert response.reason == "research_event"
        assert delivered == loop.scout_calls == loop.document_reads == []
    finally:
        await loop.close()


def history(identity: str, seconds: int, *, conversation_id: str = "conversation/opaque") -> ReachHistoryEntry:
    return ReachHistoryEntry(
        subject_id="sender/opaque",
        event_id=identity,
        conversation_id=conversation_id,
        text=f"Quoted context {identity}",
        occurred_at=NOW - timedelta(seconds=seconds),
    )


class Pager:
    def __init__(self, pages: list[tuple[tuple[ReachHistoryEntry, ...], HistoryState]]) -> None:
        self.pages = iter(pages)
        self.entries: tuple[ReachHistoryEntry, ...] = ()
        self.state: HistoryState = "more"
        self.reads = 0

    async def next_page(self) -> None:
        self.reads += 1
        self.entries, self.state = next(self.pages)


class Requester:
    def __init__(self, statuses: list[ReachWorkerStatus]) -> None:
        self.statuses = iter(statuses)
        self.requests: list[ReachWorkerRequest] = []

    async def request(
        self,
        observed: ReachEvent,
        entries: tuple[ReachHistoryEntry, ...],
        *,
        context_round: int = 0,
        history_state: str = "exhausted",
        reply_to_event_id: str | None = None,
        reply_anchor: ReachHistoryEntry | None = None,
        continuation_anchor: ReachHistoryEntry | None = None,
    ) -> ReachWorkerResult:
        request = ReachWorkerRequest.model_validate(
            {
                "request_id": f"round/{context_round}",
                "event": observed,
                "history": entries,
                "context_round": context_round,
                "history_state": history_state,
                "reply_to_event_id": reply_to_event_id,
                "reply_anchor": reply_anchor,
                "continuation_anchor": continuation_anchor,
            }
        )
        self.requests.append(request)
        return ReachWorkerResult(
            request_id=request.request_id,
            run_id=f"run/{context_round}",
            status=next(self.statuses),
            text="A native decision.",
            policy_digest="a" * 64,
            corpus_digest="b" * 64,
            model_binding_digest="c" * 64,
        )


@pytest.mark.asyncio
async def test_shared_context_driver_skips_filtered_pages_and_retains_exact_reply_metadata() -> None:
    observed = event(PLATFORMS[1])
    recent = history("recent", 3, conversation_id=observed.conversation_id)
    older = history("older", 5, conversation_id=observed.conversation_id)
    anchor = history("anchor", 8, conversation_id=observed.conversation_id)
    pager = Pager([((), "more"), ((recent,), "more"), ((older, recent), "exhausted")])
    worker = Requester(["need_context", "conversation"])
    result = await drive_context_turn(worker, observed, pager, reply_to_event_id="anchor", reply_anchor=anchor)
    assert result.status == "conversation"
    assert pager.reads == 3
    assert [item.context_round for item in worker.requests] == [0, 1]
    assert [item.history for item in worker.requests] == [(recent,), (older, recent)]
    assert [item.history_state for item in worker.requests] == ["more", "exhausted"]
    assert all(
        item.event == observed and item.reply_to_event_id == "anchor" and item.reply_anchor == anchor
        for item in worker.requests
    )


@pytest.mark.asyncio
async def test_shared_context_driver_does_not_readmit_a_run_when_paging_adds_no_context() -> None:
    recent = history("recent", 3)
    pager = Pager([((recent,), "more"), ((recent,), "exhausted")])
    worker = Requester(["need_context"])
    result = await drive_context_turn(worker, event(), pager)
    assert result.status == "clarify"
    assert result.run_id == "run/0"
    assert result.request_id == "round/0"
    assert len(worker.requests) == 1
    assert pager.reads == 2


@pytest.mark.parametrize("state", ["exhausted", "budget", "disabled", "unavailable"])
@pytest.mark.asyncio
async def test_shared_context_driver_returns_bounded_clarification_after_initial_exhaustion(
    state: HistoryState,
) -> None:
    pager = Pager([((), state)])
    worker = Requester(["need_context"])
    result = await drive_context_turn(worker, event(), pager)
    assert result.status == "clarify"
    assert result.run_id == "run/0"
    assert result.model_binding_digest == "c" * 64
    assert len(worker.requests) == pager.reads == 1


@pytest.mark.asyncio
async def test_shared_context_driver_stops_after_three_native_context_decisions() -> None:
    recent, older, oldest = history("recent", 3), history("older", 5), history("oldest", 7)
    pager = Pager([((recent,), "more"), ((older, recent), "more"), ((oldest, older, recent), "more")])
    worker = Requester(["need_context", "need_context", "need_context"])
    result = await drive_context_turn(worker, event(), pager)
    assert result.status == "clarify"
    assert result.run_id == "run/2"
    assert [item.context_round for item in worker.requests] == [0, 1, 2]
    assert pager.reads == 3


@pytest.mark.asyncio
async def test_shared_context_driver_bounds_a_source_that_keeps_offering_filtered_pages() -> None:
    class FilteredSource:
        entries: tuple[ReachHistoryEntry, ...] = ()
        state: HistoryState = "more"
        reads = 0

        async def next_page(self) -> None:
            self.reads += 1
            if self.reads > 3:
                pytest.fail("Shared context driver exceeded its page allowance")

    pager = FilteredSource()
    worker = Requester(["need_context"])
    result = await drive_context_turn(worker, event(), pager)
    assert pager.reads == 3
    assert pager.state == "more"
    assert len(worker.requests) == 1
    assert worker.requests[0].history_state == "budget"
    assert result.status == "clarify"
    assert result.run_id == "run/0"


def test_shared_native_research_imports_with_provider_sdks_blocked() -> None:
    script = """
import importlib.abc
import sys

class NoProviderSdk(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'discord', 'telegram'} or fullname.startswith('lychd.interface.discord'):
            raise ImportError('provider SDK boundary: ' + fullname)
        return None

sys.meta_path.insert(0, NoProviderSdk())
from lychd.compositions.reach.operator_client import PipeWorker
from lychd.compositions.reach.conversation_session import drive_context_turn, ContextRounds
from scripts.reach_worker import build_runtime
from scripts.reach_research_broker import OperatorResearchBroker
assert not any(name.split('.')[0] in {'discord', 'telegram'} for name in sys.modules)
"""
    result = subprocess.run(  # noqa: S603 - fixed interpreter and in-repository import probe, inside the OCI test image
        [sys.executable, "-c", script], capture_output=True, text=True, check=False, timeout=30
    )
    assert result.returncode == 0, result.stderr
