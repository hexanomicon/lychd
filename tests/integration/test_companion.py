from __future__ import annotations

import asyncio
import contextlib
import json
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import httpx
import pytest

from lychd.agents.router import Intent
from lychd.agents.workflows import builtin_workflow_registry
from lychd.compositions.blockworld.companion import (
    CompanionPolicy,
    CompanionRequest,
    CompanionResult,
    CompanionService,
    CompanionState,
    FollowAction,
    companion_workflow,
    decode_request,
    parse_text,
)
from lychd.domain.cortex.runs import RunStatus
from lychd.system.services.companion_bridge import BridgeBinding, CompanionBridge, CompanionBridgeError
from lychd.system.services.companion_session import CompanionSession, LocalCompanionRunner


def policy() -> CompanionPolicy:
    return CompanionPolicy(
        session_id="test-companion",
        principal="operator",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        min_x=-24.0,
        max_x=24.0,
        min_y=-64.0,
        max_y=320.0,
        min_z=-24.0,
        max_z=24.0,
    )


class FakeBridge:
    def __init__(self) -> None:
        self.boot, self.actor, self.player = str(uuid4()), str(uuid4()), str(uuid4())
        self.generation = 0
        self.requests: list[dict[str, Any]] = []
        self.stop_ids: list[str] = []
        self.action_started = asyncio.Event()
        self.release_action = asyncio.Event()
        self.delay = False
        self.bad_response: str | None = None
        self.reads = 0

    def state(self) -> dict[str, Any]:
        return {
            "protocol": 1,
            "boot_id": self.boot,
            "generation": self.generation,
            "actor_id": self.actor,
            "mode": "idle",
            "position": [0.0, 64.0, 0.0],
            "yaw": 0.0,
            "pitch": 0.0,
            "queue_depth": 0,
            "active_action_id": None,
            "players": [{"id": self.player, "name": "Operator", "position": [1.0, 64.0, 0.0]}],
            "timestamp_ms": int(time.time() * 1000),
        }

    async def handle(self, request: httpx.Request) -> httpx.Response:  # noqa: PLR0911 - explicit protocol failure branches
        assert request.headers["authorization"] == "Bearer " + "a" * 64
        assert request.headers["accept-encoding"] == "identity"
        if request.url.path == "/v1/state":
            self.reads += 1
            if self.bad_response == "redirect":
                return httpx.Response(302, headers={"location": "http://127.0.0.1:9999/private"})
            if self.bad_response == "unauthorized":
                return httpx.Response(401)
            if self.bad_response == "oversize":
                return httpx.Response(200, content=b" " * 65537, headers={"content-type": "application/json"})
            state = self.state()
            if self.bad_response == "identity":
                state["actor_id"] = str(uuid4())
            if self.bad_response == "unknown":
                state["unexpected"] = "never retained"
            if self.bad_response == "duplicate":
                return httpx.Response(
                    200, content=b'{"protocol":1,"protocol":1}', headers={"content-type": "application/json"}
                )
            return httpx.Response(200, json=state)
        body = json.loads(request.content)
        if request.url.path == "/v1/stop":
            self.generation += 1
            self.stop_ids.append(body["action_id"])
            self.release_action.set()
            return httpx.Response(
                202,
                json={
                    "protocol": 1,
                    "boot_id": self.boot,
                    "action_id": body["action_id"],
                    "run_id": body["run_id"],
                    "generation": self.generation,
                    "status": "applied",
                    "detail": "Controller stopped on tick.",
                    "observation": self.state(),
                },
            )
        assert request.url.path == "/v1/actions"
        self.requests.append(body)
        self.action_started.set()
        if self.delay:
            await self.release_action.wait()
        return httpx.Response(
            202,
            json={
                "protocol": 1,
                "boot_id": self.boot,
                "action_id": body["action_id"],
                "run_id": body["run_id"],
                "generation": body["generation"],
                "status": "applied",
                "detail": "Bounded goal started.",
                "observation": self.state(),
            },
        )

    def bridge(self) -> CompanionBridge:
        return CompanionBridge(
            BridgeBinding("http://127.0.0.1:18184", "a" * 64, self.actor), transport=httpx.MockTransport(self.handle)
        )


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("state", "state"),
        ("stav!", "state"),
        ("look 1 64 0", "look"),
        ("pozri 1 64 0", "look"),
        ("podívej 1 64 0", "look"),
        ("choď 1 64 0", "goto"),
        ("jdi 1 64 0", "goto"),
        ("čakaj", "idle"),
        ("cakaj", "idle"),
        ("čekej", "idle"),
        ("cekej", "idle"),
        ("oddychuj", "idle"),
        ("odpočívej", "idle"),
        ("say hello", "say"),
        ("povedz ahoj", "say"),
        ("řekni ahoj", "say"),
    ],
)
def test_exact_language_parser(text: str, kind: str) -> None:
    assert parse_text(text).kind == kind


@pytest.mark.parametrize(
    "text",
    [
        "/op player",
        "say /op player",
        "stop",
        "zastav",
        "state then goto 0 64 0",
        "goto nan 64 0",
        "goto inf 64 0",
        "goto 1 2",
        "follow someone",
        "say hi\n/op",
        "say\x00hello",
    ],
)
def test_parser_refuses_console_and_ambiguity(text: str) -> None:
    with pytest.raises(ValueError, match=r"Unsupported|Chat|Instruction|Coordinates|coordinates|validation"):
        parse_text(text)


def test_follow_requires_explicit_uuid_and_strict_requests() -> None:
    target = str(uuid4())
    action = parse_text("nasleduj", target_id=target)
    assert isinstance(action, FollowAction)
    assert action.target_id == target
    with pytest.raises(ValueError, match="Duplicate"):
        decode_request('{"request_id":"x","request_id":"y","action":{"kind":"state"}}')
    with pytest.raises(ValueError, match="extra"):
        decode_request(json.dumps({"request_id": str(uuid4()), "action": {"kind": "state"}, "console": "op"}))


@pytest.mark.parametrize("mode", ["redirect", "unauthorized", "oversize", "identity", "unknown", "duplicate"])
@pytest.mark.asyncio
async def test_http_boundary_refuses_without_followup(mode: str) -> None:
    fake = FakeBridge()
    fake.bad_response = mode
    bridge = fake.bridge()
    with pytest.raises(CompanionBridgeError, match=r"HTTP|length|identity|schema|JSON"):
        await bridge.open()
    assert fake.reads == 1
    await bridge.aclose()


@pytest.mark.asyncio
async def test_real_native_graph_and_idempotence() -> None:
    fake = FakeBridge()
    bridge = fake.bridge()
    service = CompanionService(policy(), bridge)
    runner = LocalCompanionRunner(service, bridge)
    records: list[dict[str, Any]] = []

    async def record(document: dict[str, Any]) -> None:
        records.append(document)

    session = CompanionSession(runner, bridge, record=record)
    await session.open()
    try:
        request = CompanionRequest(request_id=str(uuid4()), action=parse_text("say Ahoj"))
        first = session.enqueue(request)
        assert session.enqueue(request) is first
        outcome = await first
        assert outcome.request_id == request.request_id
        assert outcome.kind == "applied"
        assert outcome.evidence_status == "recorded"
        assert outcome.run_id is not None
        assert runner.services is not None
        run = await runner.services.ledger.get(outcome.run_id)
        assert run is not None
        assert run.status is RunStatus.DONE
        events = await runner.services.ledger.list_events(outcome.run_id)
        assert [event.data for event in events if event.kind == "node" and event.meta.get("phase") == "entered"] == [
            "validate",
            "execute",
            "report",
        ]
        assert len(fake.requests) == 1
        assert fake.requests[0]["kind"] == "say"
        assert all(workflow.name != "blockworld.companion" for workflow in builtin_workflow_registry().all())
        with pytest.raises(ValueError, match="changed content"):
            session.enqueue(request.model_copy(update={"action": parse_text("say changed")}))
        assert len(records) == 1
        assert records[0]["request_id"] == request.request_id
        assert records[0]["run_id"] == outcome.run_id
        assert records[0]["events"]
    finally:
        await session.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("limiter", ["lease", "instruction", "session"])
async def test_controller_result_retains_the_actual_clipped_outgoing_deadline(limiter: str) -> None:
    fake = FakeBridge()
    bridge = fake.bridge()
    now = datetime.now(UTC)
    selected = policy().model_copy(
        update={"lease_s": 5.0, "expires_at": now + timedelta(seconds=2 if limiter == "session" else 60)}
    )
    original = int((now.timestamp() + (2 if limiter == "instruction" else 60)) * 1000)
    service = CompanionService(selected, bridge)
    session = CompanionSession(LocalCompanionRunner(service, bridge), bridge)
    await session.open()
    try:
        command = CompanionRequest(request_id=str(uuid4()), action=parse_text("idle"), expires_at_ms=original)
        before = int(datetime.now(UTC).timestamp() * 1000)
        future = session.enqueue(command)
        outcome = await future
        after = int(datetime.now(UTC).timestamp() * 1000)
        assert outcome.kind == "applied"
        assert outcome.result is not None
        deadline = outcome.result.controller_expires_at_ms
        assert deadline == fake.requests[0]["expires_at_ms"]
        assert deadline is not None
        assert "controller_expires_at_ms" not in fake.requests[0]
        if limiter == "instruction":
            assert deadline == original
        elif limiter == "session":
            assert deadline == int(selected.expires_at.timestamp() * 1000)
        else:
            assert before + 5000 <= deadline <= after + 5000
        assert session.enqueue(command) is future
        assert service.results[command.request_id].controller_expires_at_ms == deadline
        assert len(fake.requests) == 1
        assert outcome.run_id is not None
        assert session.runner.services is not None
        events = await session.runner.services.ledger.list_events(outcome.run_id)
        documents: list[dict[str, Any]] = [
            json.loads(event.data) for event in events if event.kind == "log" and event.data.startswith("{")
        ]
        assert any(
            document.get("request_id") == command.request_id and document.get("controller_expires_at_ms") == deadline
            for document in documents
        )
    finally:
        await session.aclose()


@pytest.mark.parametrize(
    ("instruction", "kind"),
    [("state", "applied"), ("say hello", "applied"), ("idle", "unknown"), ("idle", "refused"), ("idle", "applied")],
)
@pytest.mark.asyncio
async def test_only_correlated_applied_controllers_get_host_authored_deadlines(
    instruction: str, kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeBridge()
    bridge = fake.bridge()
    invoked: list[int] = []

    async def supplied(request: CompanionRequest, _run_id: str, **kwargs: Any) -> CompanionResult:
        invoked.append(kwargs["expires_at_ms"])
        return CompanionResult.model_validate(
            {
                "request_id": request.request_id,
                "kind": kind,
                "detail": "Port cannot supply host deadline metadata.",
                "controller_expires_at_ms": 1,
            }
        )

    monkeypatch.setattr(bridge, "invoke", supplied)
    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge)
    await session.open()
    try:
        outcome = await session.enqueue(CompanionRequest(request_id=str(uuid4()), action=parse_text(instruction)))
        assert outcome.result is not None
        expected = invoked[0] if instruction == "idle" and kind == "applied" else None
        assert outcome.result.controller_expires_at_ms == expected
        assert len(invoked) == 1
    finally:
        await session.aclose()


@pytest.mark.asyncio
async def test_legacy_result_shape_is_parseable_under_new_checkpoint_closure() -> None:
    """Shape compatibility does not migrate a retained Pattern pin."""
    bridge = FakeBridge().bridge()
    selected = policy()
    command = CompanionRequest(request_id=str(uuid4()), action=parse_text("idle"))
    run_id = str(uuid4())
    intent = Intent(
        run_id=run_id,
        session_id=selected.session_id,
        prompt=command.model_dump_json(),
        source="blockworld.companion",
        sigil_name=selected.principal,
        sigil_scopes=frozenset({"blockworld:companion"}),
    )
    state = CompanionState.model_validate(
        {
            "run_id": run_id,
            "session_id": selected.session_id,
            "prompt": command.model_dump_json(),
            "request": command,
            "result": {"request_id": command.request_id, "kind": "applied", "detail": "legacy"},
        }
    )
    try:
        workflow = companion_workflow(CompanionService(selected, bridge))
        assert workflow.manifest is not None
        assert workflow.manifest.implementation_revision == "py.6"
        assert workflow.manifest.checkpoint_schema == "companion-state-v6"
        assert workflow.validate_state is not None
        workflow.validate_state(intent, state)
        assert state.result is not None
        assert state.result.controller_expires_at_ms is None
    finally:
        await bridge.aclose()


@pytest.mark.asyncio
async def test_follow_refuses_actor_outside_local_admission_bounds() -> None:
    class OutsideActor(FakeBridge):
        def state(self) -> dict[str, Any]:
            document = super().state()
            document["position"] = [25.0, 64.0, 0.0]
            document["players"][0]["position"] = [23.0, 64.0, 0.0]
            return document

    fake = OutsideActor()
    bridge = fake.bridge()
    runner = LocalCompanionRunner(CompanionService(policy(), bridge), bridge)
    session = CompanionSession(runner, bridge)
    await session.open()
    try:
        result = await session.enqueue(
            CompanionRequest(request_id=str(uuid4()), action=FollowAction(kind="follow", target_id=fake.player))
        )
        assert result.kind == "refused"
        assert result.reason == "bounds"
        assert result.result is not None
        assert result.result.reason == "bounds"
        assert fake.requests == []
    finally:
        await session.aclose()


@pytest.mark.asyncio
async def test_fifo_capacity_expiry_and_order() -> None:
    fake = FakeBridge()
    fake.delay = True
    bridge = fake.bridge()
    service = CompanionService(policy(), bridge)
    runner = LocalCompanionRunner(service, bridge)
    now = [0.0]
    session = CompanionSession(runner, bridge, capacity=2, max_age_s=2.0, clock=lambda: now[0])
    await session.open()
    try:
        first = session.enqueue(CompanionRequest(request_id=str(uuid4()), action=parse_text("say first")))
        await asyncio.wait_for(fake.action_started.wait(), 2)
        second = session.enqueue(CompanionRequest(request_id=str(uuid4()), action=parse_text("say second")))
        third = session.enqueue(CompanionRequest(request_id=str(uuid4()), action=parse_text("say third")))
        with pytest.raises(ValueError, match="full"):
            session.enqueue(CompanionRequest(request_id=str(uuid4()), action=parse_text("state")))
        now[0] = 3.0
        fake.release_action.set()
        assert (await first).kind == "applied"
        assert (await second).kind == "expired"
        assert (await third).kind == "expired"
        assert len(fake.requests) == 1
    finally:
        await session.aclose()


@pytest.mark.asyncio
async def test_stop_fences_synchronously_and_late_transcript_refuses() -> None:
    fake = FakeBridge()
    fake.delay = True
    bridge = fake.bridge()
    service = CompanionService(policy(), bridge)
    runner = LocalCompanionRunner(service, bridge)
    session = CompanionSession(runner, bridge)
    await session.open()
    try:
        captured = session.capture_generation()
        first = session.enqueue(CompanionRequest(request_id=str(uuid4()), action=parse_text("goto 1 64 0")))
        await asyncio.wait_for(fake.action_started.wait(), 2)
        queued = session.enqueue(CompanionRequest(request_id=str(uuid4()), action=parse_text("say queued")))
        pending_stop = session.stop()
        assert session.capture_generation() == captured + 1
        assert queued.done()
        assert queued.result().kind == "cancelled"
        with pytest.raises(ValueError, match="predates"):
            session.enqueue(
                CompanionRequest(request_id=str(uuid4()), action=parse_text("say late"), source="transcript"),
                captured_generation=captured,
            )
        assert (await asyncio.wait_for(pending_stop, 3)).kind == "applied"
        await first
        assert len(fake.requests) == 1
        fresh = session.enqueue(
            CompanionRequest(
                request_id=str(uuid4()), action=parse_text("state"), generation=session.capture_generation()
            )
        )
        assert (await fresh).kind == "applied"
    finally:
        await session.aclose()


@pytest.mark.asyncio
async def test_stop_during_native_admission_never_sends_action(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeBridge()
    bridge = fake.bridge()
    runner = LocalCompanionRunner(CompanionService(policy(), bridge), bridge)
    session = CompanionSession(runner, bridge)
    entered, release = asyncio.Event(), asyncio.Event()
    original = runner.submit

    async def delayed(request: CompanionRequest) -> str:
        entered.set()
        await release.wait()
        return await original(request)

    monkeypatch.setattr(runner, "submit", delayed)
    await session.open()
    try:
        future = session.enqueue(CompanionRequest(request_id=str(uuid4()), action=parse_text("say never")))
        await asyncio.wait_for(entered.wait(), 2)
        stopping = session.stop()
        assert session.capture_generation() == 1
        release.set()
        assert (await asyncio.wait_for(stopping, 3)).kind == "applied"
        assert (await future).kind == "cancelled"
        assert not fake.requests
        assert len(fake.stop_ids) == 1
    finally:
        release.set()
        await session.aclose()


@pytest.mark.asyncio
async def test_fifo_executes_exact_operator_order_without_idle_ticks() -> None:
    fake = FakeBridge()
    bridge = fake.bridge()
    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge)
    await session.open()
    try:
        futures = [
            session.enqueue(CompanionRequest(request_id=str(uuid4()), action=parse_text(f"say {word}")))
            for word in ("first", "second", "third")
        ]
        assert all(result.kind == "applied" for result in await asyncio.gather(*futures))
        assert [request["args"]["text"] for request in fake.requests] == ["first", "second", "third"]
        await asyncio.sleep(0.05)
        assert len(fake.requests) == 3
    finally:
        await session.aclose()


@pytest.mark.asyncio
async def test_lost_post_ack_is_unknown_and_identical_request_never_reposts() -> None:
    fake = FakeBridge()
    calls = 0

    async def lost(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        if request.url.path == "/v1/actions":
            calls += 1
            msg = "Synthetic lost acknowledgement."
            raise httpx.ReadError(msg, request=request)
        return await fake.handle(request)

    bridge = CompanionBridge(
        BridgeBinding("http://127.0.0.1:18184", "a" * 64, fake.actor), transport=httpx.MockTransport(lost)
    )
    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge)
    await session.open()
    try:
        request = CompanionRequest(request_id=str(uuid4()), action=parse_text("state"))
        future = session.enqueue(request)
        assert (await future).kind == "unknown"
        assert session.enqueue(request) is future
        assert (await session.enqueue(request)).kind == "unknown"
        assert calls == 1
    finally:
        await session.aclose()


@pytest.mark.asyncio
async def test_mismatched_action_identity_is_unknown() -> None:
    fake = FakeBridge()

    async def wrong_identity(request: httpx.Request) -> httpx.Response:
        response = await fake.handle(request)
        if request.url.path == "/v1/actions":
            document = response.json()
            document["run_id"] = str(uuid4())
            return httpx.Response(202, json=document)
        return response

    bridge = CompanionBridge(
        BridgeBinding("http://127.0.0.1:18184", "a" * 64, fake.actor), transport=httpx.MockTransport(wrong_identity)
    )
    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge)
    await session.open()
    try:
        result = await session.enqueue(CompanionRequest(request_id=str(uuid4()), action=parse_text("state")))
        assert result.kind == "unknown"
        assert result.reason is None
        assert result.result is not None
        assert result.result.reason is None
        assert len(fake.requests) == 1
    finally:
        await session.aclose()


@pytest.mark.parametrize("text", ["follow me", "nasleduj ma", "následuj mě", "nasleduj me"])
def test_follow_me_requires_the_explicit_operator_target(text: str) -> None:
    target = str(uuid4())
    action = parse_text(text, target_id=target)
    assert isinstance(action, FollowAction)
    assert action.target_id == target
    with pytest.raises(ValueError, match=r"canonical|UUID|Identity|validation"):
        parse_text(text)


@pytest.mark.parametrize("text", ["- Czekaj.", "Čekaj.", "follow everybody", "follow ma"])
def test_speech_artifacts_and_unlisted_phrases_are_never_normalized(text: str) -> None:
    with pytest.raises(ValueError, match=r"Unsupported|canonical|UUID|Identity|validation"):
        parse_text(text, target_id=str(uuid4()))


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://localhost:18184",
        "https://127.0.0.1:18184",
        "http://192.0.2.1:18184",
        "http://user:secret@127.0.0.1:18184",
        "http://127.0.0.1:18184/v1",
    ],
)
def test_binding_refuses_nonliteral_or_expanded_endpoints(endpoint: str) -> None:
    with pytest.raises(ValueError, match="literal"):
        BridgeBinding(endpoint, "a" * 64, str(uuid4()))


def test_json_refuses_exponent_overflow_boolean_protocol_and_unicode_controls() -> None:
    from lychd.compositions.blockworld.companion import BridgeState, strict_json

    with pytest.raises(ValueError, match="Non-finite"):
        strict_json('{"value":1e9999}')
    state = FakeBridge().state()
    state["protocol"] = True
    with pytest.raises(ValueError, match="original integer"):
        BridgeState.model_validate(state)
    with pytest.raises(ValueError, match="Instruction"):
        parse_text("say hi\u0085there")


@pytest.mark.asyncio
async def test_finite_native_action_deadline_retains_unknown_without_replay() -> None:
    fake = FakeBridge()
    fake.delay = True
    bridge = fake.bridge()
    finite_policy = policy().model_copy(update={"action_timeout_s": 0.25})
    session = CompanionSession(LocalCompanionRunner(CompanionService(finite_policy, bridge), bridge), bridge)
    await session.open()
    try:
        request = CompanionRequest(request_id=str(uuid4()), action=parse_text("goto 1 64 0"))
        result = await session.enqueue(request)
        assert result.kind == "unknown"
        assert result.reason is None
        assert "deadline" in result.detail
        assert len(fake.requests) == 1
        assert (await session.enqueue(request)).kind == "unknown"
        assert len(fake.requests) == 1
    finally:
        await session.aclose()


@pytest.mark.asyncio
async def test_stop_retains_each_queued_identity_and_joins_receipts_after_physical_stop() -> None:
    fake = FakeBridge()
    fake.delay = True
    bridge = fake.bridge()
    records: list[dict[str, Any]] = []
    receipt_started, release_receipts = asyncio.Event(), asyncio.Event()

    async def record(document: dict[str, Any]) -> None:
        if document["run_id"] is None:
            receipt_started.set()
            await release_receipts.wait()
        records.append(document)

    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge, record=record)
    await session.open()
    try:
        active = session.enqueue(CompanionRequest(request_id=str(uuid4()), action=parse_text("say active")))
        await asyncio.wait_for(fake.action_started.wait(), 2)
        requests = [CompanionRequest(request_id=str(uuid4()), action=parse_text(f"say queued {i}")) for i in range(3)]
        queued = [session.enqueue(request) for request in requests]
        captured = session.capture_generation()
        stopping = session.stop()
        assert session.capture_generation() == captured + 1
        assert all(future.done() for future in queued)
        assert [future.result().request_id for future in queued] == [request.request_id for request in requests]
        assert all(future.result().run_id is None and future.result().kind == "cancelled" for future in queued)
        assert all(future.result().reason == "cancelled_before_execution" for future in queued)
        assert all(future.result().result is None for future in queued)
        stop_task = asyncio.create_task(stopping)
        await asyncio.wait_for(receipt_started.wait(), 2)
        assert len(fake.stop_ids) == 1
        assert not stop_task.done()
        stop_task.cancel()
        await asyncio.sleep(0)
        assert not stop_task.done()
        release_receipts.set()
        assert (await asyncio.wait_for(stop_task, 3)).kind == "applied"
        await active
        queued_ids = {request.request_id for request in requests}
        queued_records = [document for document in records if document["request_id"] in queued_ids]
        assert {document["request_id"] for document in queued_records} == queued_ids
        assert len(queued_records) == 3
        assert all(document["kind"] == "cancelled" and document["run_id"] is None for document in queued_records)
        assert all(document["reason"] == "cancelled_before_execution" for document in queued_records)
        assert all("events" not in document for document in queued_records)
        assert queued_ids.isdisjoint(session.run_ids)
        assert all(session.outcomes[request_id].evidence_status == "recorded" for request_id in queued_ids)
        assert len(records) == 4
        assert len(fake.requests) == 1
    finally:
        release_receipts.set()
        await session.aclose()


@pytest.mark.parametrize("expire_during_enqueue", [False, True])
@pytest.mark.parametrize("fail_private_receipts", [False, True])
@pytest.mark.asyncio
async def test_expired_queue_retains_distinct_identities_and_private_records(
    *, expire_during_enqueue: bool, fail_private_receipts: bool
) -> None:
    fake = FakeBridge()
    fake.delay = True
    bridge = fake.bridge()
    records: list[dict[str, Any]] = []
    now = [0.0]

    async def record(document: dict[str, Any]) -> None:
        records.append(document)
        if fail_private_receipts and document["run_id"] is None:
            msg = "Private expiry receipt error."
            raise OSError(msg)

    session = CompanionSession(
        LocalCompanionRunner(CompanionService(policy(), bridge), bridge),
        bridge,
        max_age_s=2.0,
        record=record,
        clock=lambda: now[0],
    )
    await session.open()
    try:
        active = session.enqueue(CompanionRequest(request_id=str(uuid4()), action=parse_text("say active")))
        await asyncio.wait_for(fake.action_started.wait(), 2)
        requests = [CompanionRequest(request_id=str(uuid4()), action=parse_text(f"say expired {i}")) for i in range(3)]
        queued = [session.enqueue(request) for request in requests]
        now[0] = 3.0
        fresh = None
        if expire_during_enqueue:
            fresh = session.enqueue(CompanionRequest(request_id=str(uuid4()), action=parse_text("state")))
            assert all(future.done() for future in queued)
        fake.release_action.set()
        assert (await active).kind == "applied"
        outcomes = await asyncio.gather(*queued)
        assert [outcome.request_id for outcome in outcomes] == [request.request_id for request in requests]
        assert all(outcome.kind == "expired" and outcome.run_id is None for outcome in outcomes)
        assert all(outcome.reason == "expired_before_execution" and outcome.result is None for outcome in outcomes)
        if fresh is not None:
            assert (await fresh).kind == "applied"
        stopped = await session.stop()
        assert stopped.kind == "applied"
        expired_ids = {request.request_id for request in requests}
        expired_records = [document for document in records if document["request_id"] in expired_ids]
        assert {document["request_id"] for document in expired_records} == expired_ids
        assert len(expired_records) == 3
        assert all(document["kind"] == "expired" and document["run_id"] is None for document in expired_records)
        assert all(document["reason"] == "expired_before_execution" for document in expired_records)
        assert all("events" not in document for document in expired_records)
        assert expired_ids.isdisjoint(session.run_ids)
        assert all(
            session.outcomes[request_id].evidence_status == ("failed" if fail_private_receipts else "recorded")
            for request_id in expired_ids
        )
        if fail_private_receipts:
            assert "Private command evidence publication failed" in stopped.detail
            assert "Private expiry receipt error" not in stopped.detail
        assert len(fake.requests) == (2 if expire_during_enqueue else 1)
        assert len(records) == len(fake.requests) + 3
    finally:
        await session.aclose()


@pytest.mark.asyncio
async def test_publication_failure_preserves_known_outcomes_and_close_joins_queued_receipts() -> None:
    fake = FakeBridge()
    fake.delay = True
    bridge = fake.bridge()
    attempted: list[dict[str, Any]] = []
    receipt_started, release_receipts = asyncio.Event(), asyncio.Event()

    async def record(document: dict[str, Any]) -> None:
        attempted.append(document)
        if document["run_id"] is None:
            receipt_started.set()
            await release_receipts.wait()
        msg = "Private sink exception must never enter a result."
        raise OSError(msg)

    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge, record=record)
    await session.open()
    try:
        active_request = CompanionRequest(request_id=str(uuid4()), action=parse_text("say active"))
        active = session.enqueue(active_request)
        await asyncio.wait_for(fake.action_started.wait(), 2)
        queued_request = CompanionRequest(request_id=str(uuid4()), action=parse_text("say queued"))
        queued = session.enqueue(queued_request)
        closing = asyncio.create_task(session.aclose())
        await asyncio.wait_for(receipt_started.wait(), 2)
        assert len(fake.stop_ids) == 1
        assert queued.done()
        assert queued.result().kind == "cancelled"
        assert not closing.done()
        release_receipts.set()
        await asyncio.wait_for(closing, 3)
        await active
        assert session.runner.services is None
        assert {document["request_id"] for document in attempted} == {
            active_request.request_id,
            queued_request.request_id,
        }
        assert len(attempted) == 2
        outcome = session.outcomes[queued_request.request_id]
        assert (outcome.request_id, outcome.run_id, outcome.kind, outcome.evidence_status) == (
            queued_request.request_id,
            None,
            "cancelled",
            "failed",
        )
        assert "Private sink exception" not in json.dumps(attempted)
        assert "Private sink exception" not in outcome.detail
    finally:
        release_receipts.set()
        if session.runner.services is not None:
            await session.aclose()


@pytest.mark.parametrize("cancel_publication", [False, True])
@pytest.mark.asyncio
async def test_native_publication_failure_keeps_known_game_result_and_identity_without_retry(
    *, cancel_publication: bool
) -> None:
    fake = FakeBridge()
    bridge = fake.bridge()
    attempted: list[dict[str, Any]] = []

    async def record(document: dict[str, Any]) -> None:
        attempted.append(document)
        if cancel_publication:
            raise asyncio.CancelledError
        msg = "Private publication error."
        raise RuntimeError(msg)

    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge, record=record)
    await session.open()
    try:
        request = CompanionRequest(request_id=str(uuid4()), action=parse_text("state"))
        future = session.enqueue(request)
        outcome = await future
        assert outcome.request_id == request.request_id
        assert outcome.kind == "applied"
        assert outcome.result is not None
        assert outcome.result.kind == "applied"
        assert outcome.evidence_status == "failed"
        assert outcome.run_id is not None
        assert session.enqueue(request) is future
        assert len(attempted) == 1
        assert len(fake.requests) == 1
        stopped = await session.stop()
        assert stopped.kind == "applied"
        assert "Private command evidence publication failed" in stopped.detail
        assert "Private publication error" not in stopped.detail
        assert len(attempted) == 1
    finally:
        await session.aclose()


@pytest.mark.parametrize("cancel_while_queued", [False, True])
@pytest.mark.asyncio
async def test_caller_cancelled_future_does_not_discard_command_custody(*, cancel_while_queued: bool) -> None:
    fake = FakeBridge()
    fake.delay = True
    bridge = fake.bridge()
    records: list[dict[str, Any]] = []
    published = asyncio.Event()
    request = CompanionRequest(request_id=str(uuid4()), action=parse_text("say owned"))

    async def record(document: dict[str, Any]) -> None:
        records.append(document)
        if document["request_id"] == request.request_id:
            published.set()

    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge, record=record)
    await session.open()
    try:
        active = None
        if cancel_while_queued:
            active = session.enqueue(CompanionRequest(request_id=str(uuid4()), action=parse_text("say active")))
            await asyncio.wait_for(fake.action_started.wait(), 2)
        future = session.enqueue(request)
        if not cancel_while_queued:
            await asyncio.wait_for(fake.action_started.wait(), 2)
        assert future.cancel()
        if cancel_while_queued:
            await session.stop()
            assert active is not None
            await active
        else:
            fake.release_action.set()
            await asyncio.wait_for(published.wait(), 2)
            await session.stop()
        assert future.cancelled()
        assert session.enqueue(request) is future
        outcome = session.outcomes[request.request_id]
        assert outcome.request_id == request.request_id
        assert outcome.kind == ("cancelled" if cancel_while_queued else "applied")
        assert outcome.evidence_status == "recorded"
        retained = [document for document in records if document["request_id"] == request.request_id]
        assert len(retained) == 1
        assert retained[0]["run_id"] == outcome.run_id
        assert len(fake.requests) == 1
    finally:
        await session.aclose()


class FakeIntentServer:
    """A task-owned literal-loopback OpenAI fixture; no inference or external route."""

    def __init__(
        self,
        *,
        content: str = '{"decision":"state"}',
        finish: str | None = "stop",
        model: str = "fixture-model",
        tools: bool = False,
        reasoning: str | None = None,
        available: bool = True,
    ) -> None:
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from threading import Event, Thread

        self.content, self.finish, self.model, self.tools = content, finish, model, tools
        self.reasoning = reasoning
        self.available = available
        self.posts: list[dict[str, Any]] = []
        self.reads = 0
        self.entered, self.release = Event(), Event()
        self.delay = False
        self.delay_inventory = False
        self.inventory_entered, self.inventory_release = Event(), Event()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib override
                _ = format, args

            def respond(self, document: dict[str, Any]) -> None:
                raw = json.dumps(document).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                with contextlib.suppress(BrokenPipeError):
                    self.wfile.write(raw)

            def do_GET(self) -> None:
                assert self.path == "/v1/models"
                owner.reads += 1
                if owner.delay_inventory:
                    owner.inventory_entered.set()
                    assert owner.inventory_release.wait(5)
                self.respond(
                    {"object": "list", "data": [{"id": "fixture-model", "object": "model"}] if owner.available else []}
                )

            def do_POST(self) -> None:
                assert self.path == "/v1/chat/completions"
                size = int(self.headers["Content-Length"])
                assert size <= 8192
                owner.posts.append(json.loads(self.rfile.read(size)))
                owner.entered.set()
                if owner.delay:
                    assert owner.release.wait(5)
                message: dict[str, Any] = {"role": "assistant", "content": owner.content}
                if owner.reasoning is not None:
                    message["reasoning_content"] = owner.reasoning
                if owner.tools:
                    message["tool_calls"] = [
                        {"id": "forbidden", "type": "function", "function": {"name": "forbidden", "arguments": "{}"}}
                    ]
                choice: dict[str, Any] = {"index": 0, "message": message}
                if owner.finish is not None:
                    choice["finish_reason"] = owner.finish
                self.respond(
                    {
                        "id": "fixture-response",
                        "object": "chat.completion",
                        "created": 1,
                        "model": owner.model,
                        "choices": [choice],
                        "usage": {"prompt_tokens": 40, "completion_tokens": 20, "total_tokens": 60},
                    }
                )

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def profile(self) -> Any:
        from lychd.compositions.blockworld.companion_intent import CompanionIntentProfile

        return CompanionIntentProfile(
            base_url=f"http://127.0.0.1:{self.server.server_port}/v1", model_id="fixture-model"
        )

    def close(self) -> None:
        self.release.set()
        self.inventory_release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        assert not self.thread.is_alive()


def raw_instruction(
    profile: Any,
    *,
    target: str | None = None,
    text: str = "Please tell me how you are",
    expires_at_ms: int | None = None,
) -> Any:
    from lychd.compositions.blockworld.companion_intent import CompanionInstruction

    return CompanionInstruction(
        request_id=str(uuid4()),
        original_text=text,
        generation=0,
        target_id=target,
        profile_digest=profile.digest,
        expires_at_ms=expires_at_ms or int(time.time() * 1000) + 30000,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "decision", "kind"),
    [
        ("Ako sa máš?", "state", "applied"),
        ("Můžeš tu počkat?", "idle", "applied"),
        ("Please come with me", "follow_bound", "applied"),
        ("Do not follow me", "no_action", "no_action"),
        ("Build me a house", "no_action", "no_action"),
        ("Please follow and tell me your state", "no_action", "no_action"),
        ("Perhaps do that", "clarification", "clarification"),
    ],
)
async def test_native_intent_one_run_exact_grant_and_closed_effect(
    monkeypatch: pytest.MonkeyPatch, text: str, decision: str, kind: str
) -> None:
    import pydantic_ai.models

    monkeypatch.setattr(pydantic_ai.models, "ALLOW_MODEL_REQUESTS", True)
    model = FakeIntentServer(content=json.dumps({"decision": decision}))
    fake = FakeBridge()
    bridge = fake.bridge()
    runner = LocalCompanionRunner(CompanionService(policy(), bridge), bridge, intent_profile=model.profile)
    records: list[dict[str, Any]] = []

    async def record(document: dict[str, Any]) -> None:
        records.append(document)

    session = CompanionSession(runner, bridge, record=record)
    try:
        await session.open()
        instruction = raw_instruction(model.profile, target=fake.player, text=text)
        future = session.enqueue(instruction)
        assert session.enqueue(instruction) is future
        outcome = await future
        assert outcome.kind == kind
        assert outcome.reason is None
        assert outcome.run_id is not None
        assert len(session.run_ids) == 1
        assert len(model.posts) == 1
        assert model.reads >= 3
        post = model.posts[0]
        assert post["model"] == "fixture-model"
        assert not post.get("tools")
        assert post["max_completion_tokens"] == 512
        prompt = json.loads(post["messages"][-1]["content"])
        assert prompt == {"instruction": text, "bound_player_available": True}
        assert fake.player not in json.dumps(post)
        assert len(fake.requests) == (kind == "applied")
        if fake.requests:
            assert fake.requests[0]["kind"] == ("follow" if decision == "follow_bound" else decision)
            assert fake.requests[0]["expires_at_ms"] <= instruction.expires_at_ms
            if decision == "follow_bound":
                assert fake.requests[0]["args"]["target_id"] == fake.player
        assert runner.services is not None
        events = await runner.services.ledger.list_events(outcome.run_id)
        assert [e.data for e in events if e.kind == "node" and e.meta.get("phase") == "entered"] == [
            "validate",
            "interpret",
            *(["execute"] if kind == "applied" else []),
            "report",
        ]
        assert len([e for e in events if e.kind == "dispatch"]) == 1
        assert not runner.services.leases.active()
        assert records[0]["input"] == instruction.model_dump(mode="json")
        with pytest.raises(ValueError, match="changed content"):
            session.enqueue(instruction.model_copy(update={"original_text": "Different request"}))
        assert len(model.posts) == 1
    finally:
        await session.aclose()
        model.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content", "finish", "model_id", "tools"),
    [
        ("not json", "stop", "fixture-model", False),
        ('{"decision":"state","extra":1}', "stop", "fixture-model", False),
        ('{"decision":"state","decision":"idle"}', "stop", "fixture-model", False),
        ('{"decision":"goto"}', "stop", "fixture-model", False),
        ('{"decision":"state"}', "length", "fixture-model", False),
        ('{"decision":"state"}', None, "fixture-model", False),
        ('{"decision":"state"}', "stop", "other-model", False),
        ('{"decision":"state"}', "tool_calls", "fixture-model", True),
    ],
)
async def test_native_intent_invalid_response_has_no_game_effect(
    monkeypatch: pytest.MonkeyPatch, content: str, finish: str | None, model_id: str, *, tools: bool
) -> None:
    import pydantic_ai.models

    monkeypatch.setattr(pydantic_ai.models, "ALLOW_MODEL_REQUESTS", True)
    model = FakeIntentServer(content=content, finish=finish, model=model_id, tools=tools)
    fake = FakeBridge()
    bridge = fake.bridge()
    runner = LocalCompanionRunner(CompanionService(policy(), bridge), bridge, intent_profile=model.profile)
    session = CompanionSession(runner, bridge)
    try:
        await session.open()
        outcome = await session.enqueue(raw_instruction(model.profile))
        assert outcome.kind == "refused"
        assert outcome.reason == "interpretation_response_refused"
        assert outcome.result is not None
        assert outcome.result.reason == outcome.reason
        assert fake.requests == []
        assert len(model.posts) == 1
        assert runner.services is not None
        assert not runner.services.leases.active()
    finally:
        await session.aclose()
        model.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["dispatch", "inference"])
async def test_native_intent_stop_during_wait_prevents_handoff(monkeypatch: pytest.MonkeyPatch, stage: str) -> None:
    import pydantic_ai.models

    monkeypatch.setattr(pydantic_ai.models, "ALLOW_MODEL_REQUESTS", True)
    model = FakeIntentServer()
    fake = FakeBridge()
    bridge = fake.bridge()
    runner = LocalCompanionRunner(CompanionService(policy(), bridge), bridge, intent_profile=model.profile)
    session = CompanionSession(runner, bridge)
    try:
        await session.open()
        model.delay, model.delay_inventory = stage == "inference", stage == "dispatch"
        future = session.enqueue(raw_instruction(model.profile))
        entered = model.entered if stage == "inference" else model.inventory_entered
        async with asyncio.timeout(5):
            while not entered.is_set():  # noqa: ASYNC110 - task-owned HTTP fixture exposes a threading.Event
                await asyncio.sleep(0.005)
        priority = session.stop()
        model.release.set()
        model.inventory_release.set()
        await priority
        outcome = await future
        assert outcome.kind in {"cancelled", "refused"}
        assert outcome.reason is None
        assert fake.requests == []
        assert len(model.posts) == (stage == "inference")
        assert runner.services is not None
        assert not runner.services.leases.active()
    finally:
        await session.aclose()
        model.close()


@pytest.mark.asyncio
async def test_native_intent_missing_target_budget_and_typed_independence(monkeypatch: pytest.MonkeyPatch) -> None:
    import pydantic_ai.models

    monkeypatch.setattr(pydantic_ai.models, "ALLOW_MODEL_REQUESTS", True)
    model = FakeIntentServer(content='{"decision":"follow_bound"}')
    profile = model.profile.model_copy(update={"max_requests": 1})
    fake = FakeBridge()
    bridge = fake.bridge()
    runner = LocalCompanionRunner(CompanionService(policy(), bridge), bridge, intent_profile=profile)
    session = CompanionSession(runner, bridge)
    try:
        await session.open()
        missing = await session.enqueue(raw_instruction(profile))
        assert missing.kind == "clarification"
        assert missing.reason == "target_unbound"
        assert fake.requests == []
        assert len(model.posts) == 1
        assert json.loads(model.posts[0]["messages"][-1]["content"])["bound_player_available"] is False
        assert runner.services is not None
        assert missing.run_id is not None
        events = await runner.services.ledger.list_events(missing.run_id)
        assert any(e.data == '{"intent_decision": "follow_bound"}' for e in events)
        exhausted = await session.enqueue(raw_instruction(profile))
        assert exhausted.kind == "refused"
        assert exhausted.reason == "interpretation_budget_exhausted"
        assert exhausted.result is not None
        assert exhausted.result.reason == exhausted.reason
        assert len(model.posts) == 1
        typed = await session.enqueue(CompanionRequest(request_id=str(uuid4()), action=parse_text("state")))
        assert typed.kind == "applied"
        assert len(fake.requests) == 1
        assert len(model.posts) == 1
        assert typed.run_id is not None
        events = await runner.services.ledger.list_events(typed.run_id)
        assert [e.data for e in events if e.kind == "node" and e.meta.get("phase") == "entered"] == [
            "validate",
            "execute",
            "report",
        ]
        assert not runner.services.leases.active()
    finally:
        await session.aclose()
        model.close()


@pytest.mark.asyncio
async def test_raw_pre_run_expiry_retains_original_private_input_without_run() -> None:
    from lychd.compositions.blockworld.companion_intent import CompanionIntentProfile
    from lychd.domain.artifacts import ArtifactRef

    profile = CompanionIntentProfile(base_url="http://127.0.0.1:19732/v1", model_id="never-contacted")
    fake = FakeBridge()
    bridge = fake.bridge()
    runner = LocalCompanionRunner(CompanionService(policy(), bridge), bridge)
    records: list[dict[str, Any]] = []

    async def record(document: dict[str, Any]) -> None:
        records.append(document)

    session = CompanionSession(runner, bridge, record=record)
    await session.open()
    try:
        instruction = raw_instruction(profile, expires_at_ms=1).model_copy(
            update={
                "source_artifacts": (
                    ArtifactRef(artifact_id="source", digest="sha256:" + "a" * 64, media_type="audio/wav", size=40),
                )
            }
        )
        future = session.enqueue(instruction)
        outcome = await future
        assert outcome.kind == "expired"
        assert outcome.run_id is None
        assert outcome.reason == "expired_before_execution"
        assert outcome.evidence_status == "pending"
        await session.stop()
        assert session.outcomes[instruction.request_id].evidence_status == "recorded"
        assert fake.requests == []
        assert records[0]["input"] == instruction.model_dump(mode="json")
        assert "events" not in records[0]
    finally:
        await session.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("fence", ["deadline", "stop"])
async def test_native_intent_late_ignored_cancellation_does_not_act(
    monkeypatch: pytest.MonkeyPatch, fence: str
) -> None:
    import pydantic_ai.models
    from pydantic_ai.messages import ModelResponse, TextPart

    from lychd.system.services.companion_intent import CompanionIntentModel

    monkeypatch.setattr(pydantic_ai.models, "ALLOW_MODEL_REQUESTS", True)
    original = CompanionIntentModel.request

    async def late_response(self: Any, *args: Any, **kwargs: Any) -> ModelResponse:
        try:
            return await original(self, *args, **kwargs)
        except asyncio.CancelledError:
            return ModelResponse(
                parts=[TextPart('{"decision":"state"}')],
                model_name="fixture-model",
                finish_reason="stop",
                provider_details={"finish_reason": "stop"},
            )

    monkeypatch.setattr(CompanionIntentModel, "request", late_response)
    model = FakeIntentServer()
    fake = FakeBridge()
    bridge = fake.bridge()
    runner = LocalCompanionRunner(CompanionService(policy(), bridge), bridge, intent_profile=model.profile)
    session = CompanionSession(runner, bridge)
    try:
        await session.open()
        model.delay = True
        deadline = int(time.time() * 1000) + (300 if fence == "deadline" else 30000)
        future = session.enqueue(raw_instruction(model.profile, expires_at_ms=deadline))
        async with asyncio.timeout(5):
            while not model.entered.is_set():  # noqa: ASYNC110 - bounded wait on a task-owned HTTP thread
                await asyncio.sleep(0.005)
        if fence == "stop":
            await session.stop()
        outcome = await future
        assert outcome.kind in {"expired", "cancelled", "refused"}
        assert outcome.reason is None
        assert fake.requests == []
        assert len(model.posts) == 1
        assert runner.services is not None
        assert not runner.services.leases.active()
    finally:
        model.release.set()
        await session.aclose()
        model.close()


@pytest.mark.asyncio
async def test_companion_checkpoint_cannot_substitute_raw_or_typed_authority() -> None:
    from lychd.agents.router import Intent
    from lychd.compositions.blockworld.companion import CompanionState, PointAction, companion_workflow
    from lychd.compositions.blockworld.companion_intent import CompanionIntentProfile

    profile = CompanionIntentProfile(base_url="http://127.0.0.1:19732/v1", model_id="never-contacted")
    fake = FakeBridge()
    bridge = fake.bridge()
    service = CompanionService(policy(), bridge)
    runner = LocalCompanionRunner(service, bridge, intent_profile=profile)
    workflow = companion_workflow(service, runner.interpreter)
    validate = workflow.validate_state
    assert validate is not None
    instruction = raw_instruction(profile, target=fake.player)
    intent = Intent(
        run_id=str(uuid4()),
        session_id=service.policy.session_id,
        source="blockworld.companion",
        prompt=instruction.model_dump_json(),
    )
    state = workflow.make_state(intent)
    assert isinstance(state, CompanionState)
    state.instruction = instruction
    state.intent_decision = "follow_bound"
    state.request = CompanionRequest(
        request_id=instruction.request_id,
        action=FollowAction(kind="follow", target_id=fake.player),
        transcript=instruction.original_text,
        source=instruction.source,
        generation=instruction.generation,
        expires_at_ms=instruction.expires_at_ms,
        source_artifacts=instruction.source_artifacts,
    )
    validate(intent, state)
    assert state.request is not None
    attacks = [
        state.model_copy(update={"instruction": instruction.model_copy(update={"target_id": str(uuid4())})}),
        state.model_copy(
            update={"instruction": instruction.model_copy(update={"expires_at_ms": instruction.expires_at_ms + 1})}
        ),
        state.model_copy(update={"instruction": instruction.model_copy(update={"generation": False})}),
        state.model_copy(
            update={"request": state.request.model_copy(update={"expires_at_ms": instruction.expires_at_ms + 1})}
        ),
        state.model_copy(
            update={
                "request": state.request.model_copy(
                    update={"action": FollowAction(kind="follow", target_id=str(uuid4()))}
                )
            }
        ),
        state.model_copy(
            update={
                "request": state.request.model_copy(update={"action": PointAction(kind="goto", x=1.0, y=64.0, z=0.0)})
            }
        ),
        state.model_copy(update={"request": state.request.model_copy(update={"action": parse_text("say forbidden")})}),
        state.model_copy(update={"intent_decision": "idle"}),
        state.model_copy(update={"profile_digest": "sha256:" + "b" * 64}),
    ]
    try:
        for attack in attacks:
            with pytest.raises(ValueError, match=r"Checkpoint|Graph state|validation"):
                validate(intent, attack)
        unbound = instruction.model_copy(update={"target_id": None})
        unbound_intent = intent.model_copy(update={"prompt": unbound.model_dump_json()})
        unbound_state = state.model_copy(update={"prompt": unbound_intent.prompt, "instruction": unbound})
        with pytest.raises(ValueError, match="proposal"):
            validate(unbound_intent, unbound_state)
        typed = CompanionRequest(request_id=str(uuid4()), action=parse_text("state"))
        typed_intent = intent.model_copy(update={"prompt": typed.model_dump_json()})
        typed_state = workflow.make_state(typed_intent)
        assert isinstance(typed_state, CompanionState)
        typed_state.request = typed
        validate(typed_intent, typed_state)
        typed_state.request = typed.model_copy(update={"action": parse_text("say changed")})
        with pytest.raises(ValueError, match="typed request"):
            validate(typed_intent, typed_state)
    finally:
        await bridge.aclose()


@pytest.mark.asyncio
async def test_model_copy_cannot_bypass_profile_or_input_admission() -> None:
    from lychd.compositions.blockworld.companion_intent import CompanionIntentProfile
    from lychd.domain.artifacts import ArtifactRef
    from lychd.system.services.companion_session import NativeCompanionInterpreter

    profile = CompanionIntentProfile(base_url="http://127.0.0.1:19732/v1", model_id="never-contacted")
    fake = FakeBridge()
    bridge = fake.bridge()
    service = CompanionService(policy(), bridge)
    poisoned = profile.model_copy(
        update={
            "base_url": "http://example.invalid:19732/v1",
            "max_requests": 1000000,
            "max_tokens": 1000000,
            "inference_timeout_s": 600.0,
        }
    )
    with pytest.raises(ValueError, match="validation"):
        LocalCompanionRunner(service, bridge, intent_profile=poisoned)
    with pytest.raises(ValueError, match="validation"):
        NativeCompanionInterpreter(poisoned, service)
    runner = LocalCompanionRunner(service, bridge)
    session = CompanionSession(runner, bridge)
    await session.open()
    try:
        original = raw_instruction(profile)
        attacks = [
            original.model_copy(update={"original_text": "a" * 1001}),
            original.model_copy(update={"original_text": "look! around"}),
            original.model_copy(update={"generation": False}),
            original.model_copy(update={"expires_at_ms": float("inf")}),
            original.model_copy(
                update={
                    "source_artifacts": (
                        ArtifactRef(
                            artifact_id="a" * 8193, digest="sha256:" + "a" * 64, media_type="audio/wav", size=1
                        ),
                    )
                }
            ),
        ]
        for attack in attacks:
            with pytest.raises(ValueError, match=r"validation|byte limit"):
                session.enqueue(attack)
        assert session.outcomes == {}
        assert session.run_ids == {}
        assert fake.requests == []
    finally:
        await session.aclose()


@pytest.mark.asyncio
async def test_original_deadline_rechecked_after_physical_observation() -> None:
    class SlowObservation(FakeBridge):
        async def handle(self, request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/state" and self.reads:
                await asyncio.sleep(0.05)
            return await super().handle(request)

    fake = SlowObservation()
    bridge = fake.bridge()
    runner = LocalCompanionRunner(CompanionService(policy(), bridge), bridge)
    session = CompanionSession(runner, bridge)
    await session.open()
    try:
        command = CompanionRequest(
            request_id=str(uuid4()), action=parse_text("state"), expires_at_ms=int(time.time() * 1000) + 30
        )
        result = await session.enqueue(command)
        assert result.kind in {"expired", "refused"}
        assert fake.reads == 2
        assert fake.requests == []
    finally:
        await session.aclose()


@pytest.mark.asyncio
async def test_native_intent_retains_only_decision_from_reasoning_response(monkeypatch: pytest.MonkeyPatch) -> None:
    import pydantic_ai.models

    monkeypatch.setattr(pydantic_ai.models, "ALLOW_MODEL_REQUESTS", True)
    model = FakeIntentServer(reasoning="fixture-reasoning-must-never-be-retained")
    fake = FakeBridge()
    bridge = fake.bridge()
    runner = LocalCompanionRunner(CompanionService(policy(), bridge), bridge, intent_profile=model.profile)
    records: list[dict[str, Any]] = []

    async def record(document: dict[str, Any]) -> None:
        records.append(document)

    session = CompanionSession(runner, bridge, record=record)
    try:
        await session.open()
        outcome = await session.enqueue(raw_instruction(model.profile))
        assert outcome.kind == "applied"
        assert len(model.posts) == 1
        assert len(fake.requests) == 1
        assert any(event["data"] == '{"intent_decision": "state"}' for event in records[0]["events"])
        assert model.reasoning is not None
        assert model.reasoning not in json.dumps(records)
        assert runner.services is not None
        assert not runner.services.leases.active()
    finally:
        await session.aclose()
        model.close()


@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("absent_target", "target_unavailable"),
        ("full_snapshot", "target_unavailable"),
        ("distant_target", "target_distant"),
        ("target_outside", "bounds"),
        ("unavailable_actor", "actor_unavailable"),
        ("point_outside", "bounds"),
        ("point_distant", "bounds"),
        ("point_unavailable_actor", "actor_unavailable"),
    ],
)
@pytest.mark.asyncio
async def test_native_host_spatial_reasons_prevent_every_game_post(case: str, reason: str) -> None:
    class SpatialRefusal(FakeBridge):
        def state(self) -> dict[str, Any]:
            document = super().state()
            if case == "absent_target":
                document["players"] = []
            elif case == "full_snapshot":
                document["players"] = [
                    {"id": str(uuid4()), "name": "OtherPlayer", "position": [1.0, 64.0, 0.0]} for _ in range(16)
                ]
            elif case == "distant_target":
                document["players"][0]["position"] = [17.0, 64.0, 0.0]
            elif case == "target_outside":
                document["players"][0]["position"] = [25.0, 64.0, 0.0]
            elif case in {"unavailable_actor", "point_unavailable_actor"}:
                document.update(mode="unavailable", position=None, yaw=None, pitch=None)
            return document

    fake = SpatialRefusal()
    bridge = fake.bridge()
    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge)
    await session.open()
    try:
        text = "goto 25 64 0" if case == "point_outside" else "look 17 64 0" if case.startswith("point_") else "follow"
        request = CompanionRequest(request_id=str(uuid4()), action=parse_text(text, target_id=fake.player))
        outcome = await session.enqueue(request)
        assert outcome.request_id == request.request_id
        assert outcome.run_id is not None
        assert outcome.kind == "refused"
        assert outcome.reason == reason
        assert outcome.result is not None
        assert outcome.result.reason == reason
        assert fake.requests == []
    finally:
        await session.aclose()


@pytest.mark.asyncio
async def test_native_unavailable_model_keeps_exact_commands_usable(monkeypatch: pytest.MonkeyPatch) -> None:
    import pydantic_ai.models

    monkeypatch.setattr(pydantic_ai.models, "ALLOW_MODEL_REQUESTS", True)
    model = FakeIntentServer(available=False)
    fake = FakeBridge()
    bridge = fake.bridge()
    runner = LocalCompanionRunner(CompanionService(policy(), bridge), bridge, intent_profile=model.profile)
    session = CompanionSession(runner, bridge)
    try:
        await session.open()
        unavailable = await session.enqueue(raw_instruction(model.profile))
        assert unavailable.kind == "refused"
        assert unavailable.reason == "interpretation_unavailable"
        assert unavailable.result is not None
        assert unavailable.result.reason == unavailable.reason
        assert fake.requests == []
        assert model.posts == []
        assert model.reads > 0
        exact = await session.enqueue(CompanionRequest(request_id=str(uuid4()), action=parse_text("state")))
        assert exact.kind == "applied"
        assert exact.reason is None
        assert len(fake.requests) == 1
        assert model.posts == []
    finally:
        await session.aclose()
        model.close()


@pytest.mark.parametrize("decision", ["clarification", "no_action"])
@pytest.mark.asyncio
async def test_native_unbound_ambiguous_instruction_has_no_invented_target_cause(
    monkeypatch: pytest.MonkeyPatch, decision: str
) -> None:
    import pydantic_ai.models

    monkeypatch.setattr(pydantic_ai.models, "ALLOW_MODEL_REQUESTS", True)
    model = FakeIntentServer(content=json.dumps({"decision": decision}))
    fake = FakeBridge()
    bridge = fake.bridge()
    runner = LocalCompanionRunner(CompanionService(policy(), bridge), bridge, intent_profile=model.profile)
    session = CompanionSession(runner, bridge)
    try:
        await session.open()
        instruction = raw_instruction(model.profile, text="Perhaps do that")
        assert instruction.target_id is None
        outcome = await session.enqueue(instruction)
        assert outcome.kind == decision
        assert outcome.reason is None
        assert outcome.result is not None
        assert outcome.result.reason is None
        assert fake.requests == []
        assert len(model.posts) == 1
    finally:
        await session.aclose()
        model.close()


@pytest.mark.asyncio
async def test_foreign_refusal_diagnostic_never_becomes_a_host_reason() -> None:
    class ForeignRefusal(FakeBridge):
        async def handle(self, request: httpx.Request) -> httpx.Response:
            response = await super().handle(request)
            if request.url.path == "/v1/actions":
                document = response.json()
                document.update(status="refused", detail="target_unavailable: private foreign bounds diagnosis")
                return httpx.Response(202, json=document)
            return response

    fake = ForeignRefusal()
    bridge = fake.bridge()
    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge)
    await session.open()
    try:
        outcome = await session.enqueue(CompanionRequest(request_id=str(uuid4()), action=parse_text("state")))
        assert outcome.kind == "refused"
        assert outcome.reason is None
        assert outcome.result is not None
        assert outcome.result.reason is None
        assert len(fake.requests) == 1
    finally:
        await session.aclose()
