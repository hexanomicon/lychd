"""Native weather admission and result contracts; mocked HTTP does not prove engine weather."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest

from lychd.compositions.blockworld.companion import (
    CompanionPolicy,
    CompanionRefusalError,
    CompanionRequest,
    CompanionResult,
    CompanionService,
    WeatherAction,
    WeatherObservation,
    companion_workflow,
    decode_request,
    parse_text,
)
from lychd.compositions.blockworld.companion_feedback import MAX_FEEDBACK_CHARS, feedback_text, reply_text
from lychd.compositions.blockworld.companion_intent import validate_raw_instruction
from lychd.domain.codex.sigil import Sigil
from lychd.domain.cortex.runs import RunStatus
from lychd.system.services.companion_session import CompanionSession, LocalCompanionRunner
from tests.integration.test_companion import FakeBridge, policy


class WeatherBridgeFixture(FakeBridge):
    def __init__(self, fault: str | None = None) -> None:
        super().__init__()
        self.fault = fault

    def weather(self, mode: str = "clear") -> dict[str, Any]:
        return {
            "profile": "blockworld.weather@1",
            "boot_id": self.boot,
            "generation": self.generation,
            "actor_id": self.actor,
            "scope": "server_weather",
            "anchor_dimension": "minecraft:overworld",
            "mode": mode,
            "duration_ticks": 600,
            "clear_time": 600 if mode == "clear" else 0,
            "rain_time": 600 if mode == "rain" else 0,
            "thunder_time": 600 if mode == "rain" else 0,
            "raining": mode == "rain",
            "thundering": False,
            "weather_advancing": True,
            "world_tick": 123,
            "timestamp_ms": int(time.time() * 1000),
        }

    async def handle(  # noqa: C901, PLR0912 - independently named wire faults remain explicit
        self, request: httpx.Request
    ) -> httpx.Response:
        response = await super().handle(request)
        if request.url.path != "/v1/actions":
            return response
        outgoing = json.loads(request.content)
        if outgoing["kind"] != "weather" and self.fault != "cross_kind":
            return response
        if self.fault == "lost_ack":
            msg = "Fixture lost acknowledgement after effect"
            raise httpx.ReadError(msg, request=request)
        record = response.json()
        weather = self.weather(outgoing["args"].get("mode", "clear"))
        record["observation"] = weather
        if self.fault in {"server_disabled", "advance_disabled"}:
            record.update(status="refused", observation=None)
        elif self.fault == "missing":
            record["observation"] = None
        elif self.fault == "pose":
            record["observation"] = self.state()
        elif self.fault == "cell":
            record["observation"] = {
                "profile": "blockworld.cell@1",
                "boot_id": self.boot,
                "generation": self.generation,
                "actor_id": self.actor,
                "dimension": "minecraft:overworld",
                "position": [0, 64, 0],
                "available": True,
                "block": "minecraft:air",
                "properties": {},
                "world_tick": 123,
                "timestamp_ms": int(time.time() * 1000),
            }
        elif self.fault == "mode":
            record["observation"] = self.weather("rain")
        elif self.fault in {"boot_id", "actor_id"}:
            weather[self.fault] = str(uuid4())
        elif self.fault == "generation":
            weather["generation"] += 1
        elif self.fault == "stale":
            weather["timestamp_ms"] -= 60_000
        elif self.fault == "future":
            weather["timestamp_ms"] += 60_000
        elif self.fault == "anchor":
            weather["anchor_dimension"] = "minecraft:the_nether"
        elif self.fault == "scope":
            weather["scope"] = "npc_radius"
        elif self.fault == "timer":
            weather["clear_time"] = 601
        elif self.fault == "boolean_timer":
            weather["duration_ticks"] = True
        elif self.fault == "extra":
            weather["console"] = "/weather clear"
        return httpx.Response(202, json=record)


def weather_request(text: str = "počasie jasno") -> CompanionRequest:
    return CompanionRequest(request_id=str(uuid4()), action=parse_text(text))


def local_session(fake: WeatherBridgeFixture, *, enabled: bool = True) -> CompanionSession:
    selected = CompanionPolicy.model_validate({**policy().model_dump(), "allow_weather": enabled})
    bridge = fake.bridge()
    return CompanionSession(LocalCompanionRunner(CompanionService(selected, bridge), bridge), bridge)


@pytest.mark.parametrize(
    ("text", "mode"),
    [
        ("weather clear", "clear"),
        ("weather rain", "rain"),
        ("Počasie jasno.", "clear"),
        ("počasie dážď", "rain"),
        ("pocasie dazd", "rain"),
        ("počasí déšť", "rain"),
        ("pocasi dest", "rain"),
        ("daj jasno", "clear"),
        ("spusti dážď!", "rain"),
        ("nastav jasno", "clear"),
        ("spusť déšť", "rain"),
        ("clear weather", "clear"),
        ("make it rain", "rain"),
    ],
)
def test_exact_weather_grammar_has_only_fixed_typed_authority(text: str, mode: str) -> None:
    action = parse_text(text)
    assert isinstance(action, WeatherAction)
    assert action.model_dump() == {
        "kind": "weather",
        "revision": 1,
        "scope": "server_weather",
        "mode": mode,
        "duration_ticks": 600,
    }
    with pytest.raises(ValueError, match="bounded interpretation"):
        validate_raw_instruction(text)


@pytest.mark.parametrize(
    "text",
    [
        "weather",
        "weather toggle",
        "prepni počasie",
        "weather thunder",
        "weather clear 100",
        "weather clear then follow",
        "weather rain\n",
        "/weather clear",
        "počasie jasno dážď",
    ],
)
def test_ambiguous_weather_never_becomes_a_weather_action(text: str) -> None:
    with pytest.raises(ValueError, match=r"Weather|Instruction|Unsupported"):
        parse_text(text)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("revision", True),
        ("revision", 1.0),
        ("revision", "1"),
        ("revision", 2),
        ("duration_ticks", True),
        ("duration_ticks", 600.0),
        ("duration_ticks", "600"),
        ("duration_ticks", 601),
        ("scope", "npc_radius"),
        ("mode", "thunder"),
        ("command", "weather clear"),
    ],
)
def test_wire_refuses_unbounded_authority_and_coercion(field: str, value: Any) -> None:
    request = weather_request().model_dump()
    request["action"][field] = value
    with pytest.raises(ValueError, match="validation error"):
        decode_request(json.dumps(request))


@pytest.mark.parametrize(("enabled", "scope"), [(False, False), (False, True), (True, False)])
@pytest.mark.asyncio
async def test_both_host_policy_and_distinct_scope_are_required_at_both_checks(*, enabled: bool, scope: bool) -> None:
    bridge = FakeBridge().bridge()
    selected = CompanionPolicy.model_validate({**policy().model_dump(), "allow_weather": enabled})
    service = CompanionService(selected, bridge)
    principal = Sigil(
        name=selected.principal,
        scopes=frozenset({"blockworld:companion", "blockworld:weather"} if scope else {"blockworld:companion"}),
    )
    try:
        state = await bridge.open()
        for check in (
            lambda: service.validate(weather_request(), principal),
            lambda: service._authorize(weather_request(), principal, state),  # pyright: ignore[reportPrivateUsage] - effect-time grant oracle
        ):
            with pytest.raises(CompanionRefusalError) as error:
                check()
            assert error.value.reason == "weather_not_authorized"
    finally:
        await bridge.aclose()


@pytest.mark.asyncio
async def test_default_native_session_does_not_post_weather() -> None:
    fake = WeatherBridgeFixture()
    session = local_session(fake, enabled=False)
    await session.open()
    try:
        outcome = await session.enqueue(weather_request())
        assert outcome.kind == "refused"
        assert outcome.reason == "weather_not_authorized"
        assert fake.requests == []
    finally:
        await session.aclose()


@pytest.mark.parametrize("text", ["počasie jasno", "počasí déšť", "weather rain"])
@pytest.mark.asyncio
async def test_weather_crosses_real_native_graph_once_and_retains_specific_observation(text: str) -> None:
    fake = WeatherBridgeFixture()
    session = local_session(fake)
    await session.open()
    try:
        request = weather_request(text)
        future = session.enqueue(request)
        assert session.enqueue(request) is future
        outcome = await future
        assert outcome.kind == "applied"
        assert outcome.result is not None
        assert outcome.result.weather is not None
        assert isinstance(request.action, WeatherAction)
        assert outcome.result.weather.mode == request.action.mode
        assert outcome.result.controller_expires_at_ms is None
        assert outcome.result.observation is outcome.result.cell is None
        assert len(fake.requests) == 1
        assert fake.requests[0]["args"] == request.action.model_dump(exclude={"kind"})
        assert fake.requests[0]["action_id"] == request.request_id
        assert fake.requests[0]["run_id"] == outcome.run_id
        services = session.runner.services
        assert services is not None
        assert outcome.run_id is not None
        run = await services.ledger.get(outcome.run_id)
        assert run is not None
        assert run.status is RunStatus.DONE
        events = await services.ledger.list_events(outcome.run_id)
        assert [event.data for event in events if event.kind == "node" and event.meta.get("phase") == "entered"] == [
            "validate",
            "execute",
            "report",
        ]
        workflow = companion_workflow(session.runner.service)
        assert workflow.manifest is not None
        assert (
            workflow.manifest.revision,
            workflow.manifest.implementation_revision,
            workflow.manifest.checkpoint_schema,
        ) == ("4", "py.6", "companion-state-v6")
        with pytest.raises(ValueError, match="changed content"):
            session.enqueue(request.model_copy(update={"action": parse_text("idle")}))
        assert len(fake.requests) == 1
    finally:
        await session.aclose()


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "pose",
        "cell",
        "mode",
        "boot_id",
        "actor_id",
        "generation",
        "stale",
        "future",
        "anchor",
        "scope",
        "timer",
        "boolean_timer",
        "extra",
        "lost_ack",
    ],
)
@pytest.mark.asyncio
async def test_mismatched_or_lost_weather_receipt_is_unknown_without_repost(fault: str) -> None:
    fake = WeatherBridgeFixture(fault)
    session = local_session(fake)
    await session.open()
    try:
        outcome = await session.enqueue(weather_request())
        assert outcome.kind == "unknown"
        assert len(fake.requests) == 1
        assert outcome.result is not None
        assert outcome.result.weather is None
    finally:
        await session.aclose()


@pytest.mark.parametrize("fault", ["server_disabled", "advance_disabled"])
@pytest.mark.asyncio
async def test_explicit_server_refusal_is_not_success(fault: str) -> None:
    fake = WeatherBridgeFixture(fault)
    session = local_session(fake)
    await session.open()
    try:
        outcome = await session.enqueue(weather_request())
        assert outcome.kind == "refused"
        assert outcome.result is not None
        assert outcome.result.weather is None
        assert len(fake.requests) == 1
    finally:
        await session.aclose()


@pytest.mark.asyncio
async def test_weather_observation_cannot_confirm_an_existing_state_action() -> None:
    fake = WeatherBridgeFixture("cross_kind")
    session = local_session(fake)
    await session.open()
    try:
        outcome = await session.enqueue(CompanionRequest(request_id=str(uuid4()), action=parse_text("state")))
        assert outcome.kind == "unknown"
    finally:
        await session.aclose()


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
@pytest.mark.parametrize("mode", ["clear", "rain"])
def test_feedback_uses_only_matching_typed_weather_and_reports_global_timer(language: str, mode: str) -> None:
    fake = WeatherBridgeFixture()
    request = weather_request(f"weather {mode}")
    result = CompanionResult(
        request_id=request.request_id,
        kind="applied",
        detail="foreign private text",
        weather=WeatherObservation.model_validate(fake.weather(mode)),
    )
    text = feedback_text(request, result, kind="applied", language=language)
    assert "600" in text
    assert "server" in text.casefold()
    assert "foreign" not in text
    assert len(text) <= MAX_FEEDBACK_CHARS
    other = "rain" if mode == "clear" else "clear"
    mismatch = result.model_copy(update={"weather": WeatherObservation.model_validate(fake.weather(other))})
    assert feedback_text(request, mismatch, kind="applied", language=language) == reply_text("unknown", language)
    missing = result.model_copy(update={"weather": None})
    assert feedback_text(request, missing, kind="applied", language=language) == reply_text("unknown", language)


def test_weather_qualification_keeps_global_effect_and_human_speech_boundaries_explicit() -> None:
    receipt = json.loads(
        (Path(__file__).resolve().parents[2] / "tests/fixtures/blockworld/companion-cpu-runtime.json").read_text()
    )
    current = receipt["weather_requalification"]
    assert (current["operation"], current["scope"], current["duration_ticks"]) == ("weather@1", "server_weather", 600)
    assert current["modes"] == ["clear", "rain"]
    assert (current["pattern_revision"], current["implementation_revision"], current["checkpoint_schema"]) == (
        "3",
        "py.5",
        "companion-state-v5",
    )
    assert current["portable_new_cases"] == 77
    assert current["java_junit_cases"] == 35
    assert current["weather_required_game_tests"] == current["controller_required_game_tests"] == 2
    assert current["weather_fixture_npc"] == "fake finite actuator"
    assert current["real_npc_continuity_probe"] == "direct production composite during original short follow"
    for key in (
        "weather_engine_timer_progression_and_transitions",
        "real_npc_original_deadline_preserved",
        "fixture_weather_and_rules_restored",
        "existing_queue_controls_preserved",
        "server_default_deny",
        "host_policy_and_scope_rechecked",
        "weather_unknown_never_reposted",
        "ambiguous_weather_never_enters_interpretation",
        "live_weather_preserved_controller_and_limit",
        "live_closed_stopped",
        "server_artifact_test_assets_excluded",
    ):
        assert current[key] is True
    assert current["live_text_native_runs_applied"] == 3
    assert current["live_synthetic_voice_cases"] == 5
    assert current["live_synthetic_voice_runs_applied"] == current["generated_reply_wavs"] == 2
    assert current["live_synthetic_voice_unexpected_refusals"] == 3
    assert current["live_synthetic_voice_applied_languages"] == ["en", "cs"]
    assert current["live_synthetic_voice_refused_languages"] == ["sk", "sk", "sk"]
    for key in (
        "human_microphone",
        "physical_playback",
        "human_accuracy_benchmark",
        "gpu_or_interpreter_used",
        "paid_or_hosted_voice_requested",
        "model_or_speech_provider_changed",
        "day_night_or_building_or_wakeword_added",
        "unchanged_historical_cohorts_reexecuted",
    ):
        assert current[key] is False
    assert current["coupled_synthetic_failures_attributed_to_one_model"] is False
    assert current["graceful_world_save_attested"] is False
    assert current["server_artifact_production_classes_matched"] == 29
