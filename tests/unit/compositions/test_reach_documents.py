"""Public export integrity, history boundaries and real native operator Workflow behavior."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

import pytest
from pydantic import ValidationError
from scripts.reach_worker import build_runtime

from lychd.compositions.reach.documents import (
    CorpusDocument,
    CorpusManifest,
    PublicCorpus,
    context_excerpts,
    search_documents,
    validate_history,
    verify_corpus,
)
from lychd.compositions.reach.documents_workflow import make_documents_intent, reach_documents_workflow
from lychd.compositions.reach.operator_wire import ReachHistoryEntry, ReachWorkerRequest, parse_request_line
from lychd.compositions.reach.schemas import ReachEvent, ReachPolicy, ReachRule
from lychd.domain.cortex.events import RunEventKind
from lychd.domain.cortex.runs import RunStatus

NOW = datetime(2026, 10, 27, 12, tzinfo=UTC)
STARTED = NOW - timedelta(seconds=10)
REVISION = "a" * 40


def make_corpus(
    text: str = "# Graph\nNative serial Graph stations preserve declared continuation state.",
) -> PublicCorpus:
    raw = text.encode()
    document = CorpusDocument(
        path="docs/graph.md",
        url=f"https://github.com/hexanomicon/lychd/blob/{REVISION}/docs/graph.md",
        sha256=sha256(raw).hexdigest(),
        file="000.md",
    )
    return verify_corpus(CorpusManifest(source_revision=REVISION, documents=(document,)), (raw,))


def make_policy(**changes: Any) -> ReachPolicy:
    values: dict[str, Any] = {
        "platform": "discord",
        "account_id": "app:one",
        "agent_subject_id": "bot:one",
        "space_id": "guild:one",
        "allowed_conversation_ids": ("channel:one",),
        "rules": (
            ReachRule(name="operator", subject_ids=("person:one",), actions=("answer_docs", "summarize_context")),
        ),
    }
    return ReachPolicy(**(values | changes))


def make_request(**changes: Any) -> ReachWorkerRequest:
    values: dict[str, Any] = {
        "platform": "discord",
        "account_id": "app:one",
        "event_id": "event:one",
        "space_id": "guild:one",
        "conversation_id": "channel:one",
        "subject_id": "person:one",
        "mention_subject_ids": ("bot:one",),
        "trigger": "mention",
        "action": "answer_docs",
        "question": "How does Graph continuation work?",
        "occurred_at": NOW - timedelta(seconds=1),
    }
    return ReachWorkerRequest(request_id="request:one", event=ReachEvent(**(values | changes)))


@pytest.mark.parametrize("platform", ["discord", "telegram"])
@pytest.mark.asyncio
async def test_real_native_worker_settles_exact_guest_result(platform: str) -> None:
    policy, corpus = make_policy(platform=platform), make_corpus()
    runtime = build_runtime(policy, corpus, started_at=STARTED, clock=lambda: NOW)
    try:
        result = await runtime.process(make_request(platform=platform))
        assert result.status == "docs"
        assert result.run_id is not None
        assert result.policy_digest == policy.digest
        assert result.corpus_digest == corpus.digest
        assert "Native serial Graph" in result.text
        assert f"/blob/{REVISION}/docs/graph.md" in result.text
        run = await runtime.substrate.ledger.get(result.run_id)
        assert run is not None
        assert run.status is RunStatus.DONE
        assert run.sigil_name == "reach.guest"
        assert run.sigil_scopes == frozenset()
        assert run.pattern_manifest["key"] == "reach.documents"
        assert run.pattern_manifest["revision"] == "1"
        turn = await runtime.sessions.settled_turn_for_run(run.run_id)
        assert turn is not None
        assert turn.content == result.model_dump_json()
        events = await runtime.substrate.ledger.list_events(run.run_id)
        assert {event.data for event in events if event.kind is RunEventKind.NODE} == {"revalidate", "search", "settle"}
        duplicate = await runtime.process(make_request(platform=platform))
        assert duplicate.status == "refused"
        assert duplicate.reason == "duplicate"
        assert duplicate.text == ""
        assert duplicate.run_id is None
        changed = await runtime.process(make_request(platform=platform, question="Changed payload"))
        assert changed.reason == "duplicate_conflict"
        assert changed.run_id is None
    finally:
        await runtime.aclose()


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"subject_id": "unknown"}, "subject_not_allowed"),
        ({"occurred_at": STARTED - timedelta(microseconds=1)}, "before_generation"),
        ({"occurred_at": NOW + timedelta(seconds=1)}, "event_from_future"),
    ],
)
@pytest.mark.asyncio
async def test_refused_ingress_has_no_session_or_native_run(changes: dict[str, Any], reason: str) -> None:
    runtime = build_runtime(make_policy(), make_corpus(), started_at=STARTED, clock=lambda: NOW)
    try:
        result = await runtime.process(make_request(**changes))
        assert result.reason == reason
        assert result.run_id is None
        assert result.text == ""
        assert await runtime.sessions.list_sessions() == []
    finally:
        await runtime.aclose()


def test_checkpoint_binds_policy_corpus_question_history_run_and_session() -> None:
    policy, corpus, request = make_policy(), make_corpus(), make_request()
    workflow = reach_documents_workflow(policy, corpus, started_at=STARTED, clock=lambda: NOW)
    intent = make_documents_intent(policy, corpus, request, session_id="session", started_at=STARTED, now=NOW)
    admitted = intent.model_copy(update={"run_id": "canonical"})
    state = workflow.make_state(admitted)
    assert workflow.validate_state is not None
    workflow.validate_state(admitted, state)
    for changes in ({"run_id": "other"}, {"session_id": "other"}, {"sigil_scopes": frozenset({"*"})}):
        with pytest.raises(ValueError, match=r"documents_(checkpoint|guest)"):
            workflow.validate_state(admitted.model_copy(update=changes), state)
    other_policy = reach_documents_workflow(
        make_policy(event_ttl_seconds=200), corpus, started_at=STARTED, clock=lambda: NOW
    )
    other_corpus = reach_documents_workflow(
        policy, make_corpus("Changed corpus"), started_at=STARTED, clock=lambda: NOW
    )
    for changed in (other_policy, other_corpus):
        with pytest.raises(ValueError, match="documents_binding"):
            changed.make_state(admitted)
    replacement = make_documents_intent(
        policy, corpus, make_request(question="Different"), session_id="session", started_at=STARTED, now=NOW
    ).model_copy(update={"run_id": "canonical"})
    with pytest.raises(ValueError, match="documents_checkpoint"):
        workflow.validate_state(replacement, state)


def test_lexical_search_normalizes_slovak_and_has_explicit_no_match() -> None:
    corpus = make_corpus("# Pokračovanie\nGraf uchováva pokračovanie a deklarovaný stav.")
    status, text = search_documents(corpus, make_request(question="pokracovanie"))
    assert status == "docs"
    assert "pokračovanie" in text
    assert search_documents(corpus, make_request(question="unfindable-zqx"))[0] == "empty"


def test_source_hash_and_revision_url_are_independent_integrity_checks() -> None:
    corpus = make_corpus()
    with pytest.raises(ValueError, match="corpus_content"):
        verify_corpus(corpus.manifest, (b"Tampered content",))
    document = corpus.manifest.documents[0]
    with pytest.raises(ValidationError, match="corpus_url"):
        CorpusManifest(source_revision="b" * 40, documents=(document,))
    with pytest.raises(ValidationError):
        CorpusDocument(**(document.model_dump() | {"path": "docs/../private.md"}))


def test_history_requires_explicit_bounds_and_exact_conversation_and_time() -> None:
    entry = ReachHistoryEntry(
        subject_id="person:two",
        event_id="previous",
        conversation_id="channel:one",
        text="Graph context",
        occurred_at=NOW - timedelta(seconds=2),
    )
    request = make_request().model_copy(update={"history": (entry,)})
    with pytest.raises(ValueError, match="history_limit"):
        validate_history(make_policy(), request)
    policy = make_policy(context_message_limit=3)
    validate_history(policy, request)
    assert context_excerpts((entry,))[0] == "context"
    for changes in ({"conversation_id": "foreign"}, {"occurred_at": NOW}, {"occurred_at": NOW - timedelta(hours=1)}):
        with pytest.raises(ValueError, match="history_binding"):
            validate_history(policy, request.model_copy(update={"history": (entry.model_copy(update=changes),)}))


@pytest.mark.asyncio
async def test_context_action_quotes_evidence_without_claiming_an_ai_summary() -> None:
    entry = ReachHistoryEntry(
        subject_id="person:two",
        event_id="previous",
        conversation_id="channel:one",
        text="One explicit source excerpt.",
        occurred_at=NOW - timedelta(seconds=2),
    )
    runtime = build_runtime(make_policy(context_message_limit=3), make_corpus(), started_at=STARTED, clock=lambda: NOW)
    try:
        request = make_request(action="summarize_context").model_copy(update={"history": (entry,)})
        result = await runtime.process(request)
        assert result.status == "context"
        assert "no AI summary" in result.text
        assert "> One explicit source excerpt." in result.text
    finally:
        await runtime.aclose()


@pytest.mark.parametrize("raw", [b'{"kind":"request","kind":"request"}', b'{"event":{"x":1,"x":2}}', b'{"a":NaN}'])
def test_wire_rejects_duplicate_keys_and_nonfinite_json(raw: bytes) -> None:
    with pytest.raises(ValueError, match=r"duplicate_key|invalid_json"):
        parse_request_line(raw)


def test_wire_round_trip_is_strict_and_rejects_transport_credentials() -> None:
    request = make_request()
    assert parse_request_line(request.model_dump_json().encode()) == request
    with pytest.raises(ValidationError):
        parse_request_line(
            request.model_dump_json().replace('"kind":"request"', '"kind":"request","token":"secret"').encode()
        )


@pytest.mark.asyncio
async def test_timeout_joins_worker_and_never_authorizes_replay() -> None:
    runtime = build_runtime(make_policy(), make_corpus(), started_at=STARTED, clock=lambda: NOW)
    try:
        result = await runtime.process(make_request(), timeout=0)
        assert result.status == "error"
        assert result.reason == "run_timeout"
        assert runtime.queue.jobs == {}
        assert (await runtime.process(make_request())).reason == "duplicate"
    finally:
        await runtime.aclose()
