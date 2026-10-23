"""Typed one-cell native companion contracts; mock HTTP is not live game proof."""

from __future__ import annotations

import json
import time
from typing import Any
from uuid import uuid4

import httpx
import pytest

from lychd.compositions.blockworld.companion import (
    CellAction,
    CellObservation,
    CompanionRequest,
    CompanionResult,
    CompanionService,
    companion_workflow,
    decode_request,
    parse_text,
)
from lychd.compositions.blockworld.companion_feedback import MAX_FEEDBACK_CHARS, feedback_text, reply_text
from lychd.domain.cortex.runs import RunStatus
from lychd.system.services.companion_bridge import CompanionBridge
from lychd.system.services.companion_session import CompanionSession, LocalCompanionRunner
from tests.integration.test_companion import FakeBridge, policy


class CellBridgeFixture(FakeBridge):
    """Reuse existing authenticated fake; supply one independently known cell."""

    def __init__(self, fault: str | None = None) -> None:
        super().__init__()
        self.fault = fault
        self.routes: list[tuple[str, str]] = []
        self.actor_position: list[float] = [0.0, 64.0, 0.0]
        self.actor_unavailable = False
        self.active_controller = str(uuid4())
        self.bound_bridge: CompanionBridge | None = None
        self.block = "minecraft:oak_stairs"
        self.properties = {"facing": "north", "half": "bottom", "shape": "straight", "waterlogged": "false"}

    def state(self) -> dict[str, Any]:
        state = super().state()
        state.update(mode="follow", position=self.actor_position, active_action_id=self.active_controller)
        if self.actor_unavailable:
            state.update(mode="unavailable", position=None, yaw=None, pitch=None, active_action_id=None)
        return state

    def cell(self) -> dict[str, Any]:
        return {
            "profile": "blockworld.cell@1",
            "boot_id": self.boot,
            "generation": self.generation,
            "actor_id": self.actor,
            "dimension": "minecraft:overworld",
            "position": [1, 64, 0],
            "available": True,
            "block": self.block,
            "properties": dict(self.properties),
            "world_tick": 123,
            "timestamp_ms": int(time.time() * 1000),
        }

    async def handle(  # noqa: C901, PLR0912 - independent named wire faults stay visible in one fixture
        self, request: httpx.Request
    ) -> httpx.Response:
        self.routes.append((request.method, request.url.path))
        response = await super().handle(request)
        if request.url.path != "/v1/actions":
            return response
        outgoing = json.loads(request.content)
        if outgoing["kind"] != "inspect" and self.fault != "cross_kind":
            return response
        if self.fault == "old_server":
            return httpx.Response(400, json={"detail": "unsupported action kind"})
        if self.fault == "lost_ack":
            msg = "Fixture lost acknowledgement"
            raise httpx.ReadError(msg, request=request)
        record = response.json()
        record["observation"] = self.cell()
        cell = record["observation"]
        if self.fault == "unloaded":
            record["status"] = "refused"
            cell.update(available=False, block=None, properties={})
        elif self.fault == "pose":
            record["observation"] = self.state()
        elif self.fault == "missing_cell":
            record["observation"] = None
        elif self.fault == "cell_position":
            cell["position"] = [2, 64, 0]
        elif self.fault in {"action_id", "run_id", "boot_id"}:
            record[self.fault] = str(uuid4())
        elif self.fault == "generation":
            record["generation"] += 1
        elif self.fault == "cell_boot":
            cell["boot_id"] = str(uuid4())
        elif self.fault == "cell_actor":
            cell["actor_id"] = str(uuid4())
        elif self.fault == "cell_generation":
            cell["generation"] += 1
        elif self.fault == "stale":
            cell["timestamp_ms"] -= 60_000
        elif self.fault == "future":
            cell["timestamp_ms"] += 60_000
        elif self.fault == "profile":
            cell["profile"] = "blockworld.cell@2"
        elif self.fault == "float_cell":
            cell["position"][0] = 1.0
        elif self.fault == "boolean_cell":
            cell["position"][0] = True
        elif self.fault == "extra_authority":
            cell["can_place"] = True
        return httpx.Response(202, json=record)


def cell_request(text: str = "inspect 1 64 0") -> CompanionRequest:
    return CompanionRequest(request_id=str(uuid4()), action=parse_text(text))


def local_session(fake: CellBridgeFixture, **policy_changes: Any) -> CompanionSession:
    selected = policy().model_copy(update=policy_changes)
    bridge = fake.bridge()
    fake.bound_bridge = bridge
    return CompanionSession(LocalCompanionRunner(CompanionService(selected, bridge), bridge), bridge)


@pytest.mark.parametrize("verb", ["inspect", "block", "blok", "INSPECT"])
def test_cell_exact_sk_cs_en_grammar_retains_original_integer_cell(verb: str) -> None:
    action = parse_text(f"{verb} -1 64 0")
    assert isinstance(action, CellAction)
    assert action.model_dump() == {"kind": "inspect", "revision": 1, "x": -1, "y": 64, "z": 0}
    assert all(type(value) is int for value in (action.x, action.y, action.z, action.revision))


@pytest.mark.parametrize(
    "text",
    [
        "inspect 1.0 64 0",
        "inspect 1e0 64 0",
        "inspect +1 64 0",
        "inspect nan 64 0",
        "inspect \u0661 64 0",
        "inspect \uff11 64 0",
        "inspect --1 64 0",
        "inspect 1 64",
        "inspect 1 64 0 2",
        "inspect 1 64 0 then build",
        "inspect\n1 64 0",
        "inspect 30000001 64 0",
        "inspect -30000001 64 0",
        "place 1 64 0",
    ],
)
def test_cell_parser_refuses_rounding_repair_multiple_actions_and_writes(text: str) -> None:
    with pytest.raises(ValueError, match=r"Inspection|Instruction|Unsupported|validation error"):
        parse_text(text)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("x", True),
        ("x", 1.0),
        ("x", "1"),
        ("revision", True),
        ("revision", 1.0),
        ("revision", "1"),
        ("revision", 2),
        ("revision", None),
        ("console", "setblock"),
    ],
)
def test_cell_wire_refuses_coercion_and_unknown_authority(field: str, value: Any) -> None:
    action: dict[str, Any] = {"kind": "inspect", "revision": 1, "x": 1, "y": 64, "z": 0}
    action[field] = value
    with pytest.raises(ValueError, match="validation error"):
        decode_request(json.dumps({"request_id": str(uuid4()), "action": action}))


def test_cell_wire_duplicate_revision_is_not_an_override() -> None:
    raw = (
        '{"request_id":"' + str(uuid4()) + '","action":{"kind":"inspect","revision":1,"revision":2,"x":1,"y":64,"z":0}}'
    )
    with pytest.raises(ValueError, match="Duplicate"):
        decode_request(raw)


@pytest.mark.asyncio
async def test_cell_crosses_real_native_run_once_with_full_state_and_no_controller_lease() -> None:
    fake = CellBridgeFixture()
    session = local_session(fake)
    await session.open()
    try:
        request = cell_request()
        future = session.enqueue(request)
        assert session.enqueue(request) is future
        outcome = await future
        assert outcome.kind == "applied"
        assert outcome.request_id == request.request_id
        assert outcome.run_id is not None
        assert outcome.result is not None
        cell = outcome.result.cell
        assert cell is not None
        assert cell.position == (1, 64, 0)
        assert cell.block == "minecraft:oak_stairs"
        assert cell.properties == {"facing": "north", "half": "bottom", "shape": "straight", "waterlogged": "false"}
        assert cell.dimension == "minecraft:overworld"
        assert cell.world_tick == 123
        assert (cell.boot_id, cell.actor_id) == (fake.boot, fake.actor)
        assert outcome.result.observation is None
        assert outcome.result.controller_expires_at_ms is None
        runner = session.runner
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
        sent = fake.requests[0]
        assert sent["kind"] == "inspect"
        assert sent["args"] == {"revision": 1, "x": 1, "y": 64, "z": 0}
        assert sent["action_id"] == request.request_id
        assert sent["run_id"] == outcome.run_id
        assert fake.bound_bridge is not None
        assert fake.bound_bridge.state is not None
        assert fake.bound_bridge.state.mode == "follow"
        assert fake.bound_bridge.state.active_action_id == fake.active_controller
        # This checks host result separation; a mock cannot prove server controller preservation.
        with pytest.raises(ValueError, match="changed content"):
            session.enqueue(request.model_copy(update={"action": parse_text("inspect 2 64 0")}))
        assert len(fake.requests) == 1
    finally:
        await session.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault",
    [
        "pose",
        "missing_cell",
        "cell_position",
        "action_id",
        "run_id",
        "boot_id",
        "generation",
        "cell_boot",
        "cell_actor",
        "cell_generation",
        "stale",
        "future",
        "profile",
        "float_cell",
        "boolean_cell",
        "extra_authority",
        "lost_ack",
        "old_server",
        "cross_kind",
    ],
)
async def test_bad_cell_provenance_variant_or_lost_ack_is_unknown_without_repost(fault: str) -> None:
    fake = CellBridgeFixture(fault)
    session = local_session(fake)
    await session.open()
    try:
        request = cell_request("state" if fault == "cross_kind" else "inspect 1 64 0")
        future = session.enqueue(request)
        outcome = await future
        assert outcome.kind == "unknown"
        assert outcome.result is not None
        assert outcome.result.cell is None
        assert outcome.result.reason is None
        assert session.enqueue(request) is future
        assert (await session.enqueue(request)).kind == "unknown"
        assert len(fake.requests) == 1
        assert not any(method == "GET" and path.startswith("/v1/actions/") for method, path in fake.routes)
    finally:
        await session.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("whole_x", "bounds"),
        ("whole_y", "bounds"),
        ("whole_z", "bounds"),
        ("distance", "bounds"),
        ("actor_outside", "bounds"),
        ("actor_unavailable", "actor_unavailable"),
    ],
)
async def test_cell_refuses_whole_cell_distance_and_actor_bounds_before_post(case: str, reason: str) -> None:
    fake = CellBridgeFixture()
    changes: dict[str, Any] = {}
    text = "inspect 1 64 0"
    if case == "whole_x":
        changes["max_x"] = 1.5
    elif case == "whole_y":
        changes["max_y"] = 64.5
    elif case == "whole_z":
        changes["max_z"] = 0.5
    elif case == "distance":
        text = "inspect 17 64 0"
    elif case == "actor_outside":
        fake.actor_position = [25.0, 64.0, 0.0]
    else:
        fake.actor_unavailable = True
    session = local_session(fake, **changes)
    await session.open()
    try:
        outcome = await session.enqueue(cell_request(text))
        assert outcome.kind == "refused"
        assert outcome.reason == reason
        assert fake.requests == []
    finally:
        await session.aclose()


@pytest.mark.asyncio
async def test_cell_expired_original_deadline_cannot_start_a_fresh_read() -> None:
    fake = CellBridgeFixture()
    session = local_session(fake)
    await session.open()
    entered = False
    original = fake.state

    def expired_during_observation() -> dict[str, Any]:
        nonlocal entered
        entered = True
        return original()

    # Use an already elapsed original deadline, never an artificial new lease.
    fake.state = expired_during_observation
    try:
        request = cell_request().model_copy(update={"expires_at_ms": int(time.time() * 1000) - 1})
        outcome = await session.enqueue(request)
        assert outcome.kind in {"expired", "refused"}
        assert fake.requests == []
        assert not entered
    finally:
        await session.aclose()


@pytest.mark.asyncio
async def test_cell_operation_pins_new_checkpoint_closure() -> None:
    fake = CellBridgeFixture()
    bridge = fake.bridge()
    try:
        workflow = companion_workflow(CompanionService(policy(), bridge))
        assert workflow.manifest is not None
        assert workflow.manifest.implementation_revision == "py.6"
        assert workflow.manifest.checkpoint_schema == "companion-state-v6"
    finally:
        await bridge.aclose()


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
@pytest.mark.parametrize("block", ["minecraft:air", "minecraft:oak_stairs"])
def test_cell_feedback_localizes_full_state_and_retains_air_as_observed_air(language: str, block: str) -> None:
    fake = CellBridgeFixture()
    fake.block = block
    if block == "minecraft:air":
        fake.properties = {}
    request = cell_request()
    cell = CellObservation.model_validate(fake.cell())
    result = CompanionResult(
        request_id=request.request_id, kind="applied", detail="private foreign diagnostic", cell=cell
    )
    text = feedback_text(request, result, kind="applied", language=language)
    assert text.startswith("Observed block" if language == "en" else "Pozorovaný blok")
    assert all(axis in text for axis in ("X 1", "Y 64", "Z 0"))
    assert block in text
    assert all(f"{key}={value}" in text for key, value in fake.properties.items())
    assert len(text) <= MAX_FEEDBACK_CHARS
    assert all(secret not in text for secret in (request.request_id, fake.boot, fake.actor, "private", "Operator"))
    assert "placed" not in text
    assert "inventory" not in text


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
@pytest.mark.parametrize("conflict", ["no_cell", "wrong_cell", "wrong_request", "unknown_result", "pose_only"])
def test_cell_feedback_never_promotes_unmatched_or_uncertain_data(language: str, conflict: str) -> None:
    fake = CellBridgeFixture()
    request = cell_request()
    result = CompanionResult(
        request_id=request.request_id,
        kind="applied",
        detail="foreign",
        cell=CellObservation.model_validate(fake.cell()),
    )
    if conflict == "no_cell":
        result = result.model_copy(update={"cell": None})
    elif conflict == "wrong_cell":
        assert result.cell is not None
        result = result.model_copy(update={"cell": result.cell.model_copy(update={"position": (2, 64, 0)})})
    elif conflict == "wrong_request":
        result = result.model_copy(update={"request_id": str(uuid4())})
    elif conflict == "unknown_result":
        result = result.model_copy(update={"kind": "unknown"})
    else:
        result = result.model_copy(update={"cell": None, "observation": fake.state()})
    assert feedback_text(request, result, kind="applied", language=language) == reply_text("unknown", language)


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
def test_long_full_cell_state_uses_bounded_notice_without_losing_retained_properties(language: str) -> None:
    fake = CellBridgeFixture()
    fake.properties = {f"property_{index}": "v" * 50 for index in range(32)}
    cell = CellObservation.model_validate(fake.cell())
    request = cell_request()
    result = CompanionResult(request_id=request.request_id, kind="applied", detail="foreign", cell=cell)
    text = feedback_text(request, result, kind="applied", language=language)
    assert 0 < len(text) <= MAX_FEEDBACK_CHARS
    assert text != reply_text("applied", language)
    assert "property_" not in text
    assert "private record" in text if language == "en" else "záznam" in text
    assert result.cell is not None
    assert result.cell.properties == fake.properties
    assert len(result.cell.properties) == 32


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("profile", "blockworld.cell@2"),
        ("position", [True, 64, 0]),
        ("position", [1.0, 64, 0]),
        ("world_tick", True),
        ("timestamp_ms", -1),
        ("dimension", "overworld"),
        ("properties", {"bad key": "value"}),
        ("inventory", {"stone": 64}),
        ("available", 1),
        ("block", None),
    ],
)
def test_cell_codec_refuses_profile_coercion_and_unowned_contents(field: str, value: Any) -> None:
    raw = CellBridgeFixture().cell()
    raw[field] = value
    with pytest.raises(ValueError, match="validation error"):
        CellObservation.model_validate(raw)


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["sk", "cs", "en"])
async def test_unloaded_cell_is_refused_with_typed_availability_and_no_read_retry(language: str) -> None:
    fake = CellBridgeFixture("unloaded")
    session = local_session(fake)
    await session.open()
    try:
        request = cell_request()
        outcome = await session.enqueue(request)
        assert outcome.kind == "refused"
        result = outcome.result
        assert result is not None
        assert result.cell is not None
        assert result.cell.available is False
        assert result.cell.block is None
        assert result.cell.properties == {}
        text = feedback_text(request, result, kind="refused", language=language, outcome=outcome)
        assert text != reply_text("refused", language)
        assert "X 1, Y 64, Z 0" in text
        assert "not loaded" in text if language == "en" else "nač" in text
        assert len(text) <= MAX_FEEDBACK_CHARS
        assert len(fake.requests) == 1
    finally:
        await session.aclose()
