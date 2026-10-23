"""Clock admission and native result challenges; inert HTTP does not prove engine placement."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from uuid import uuid4

import httpx
import pytest

from lychd.compositions.blockworld.companion import (
    ClockObservation,
    CompanionPolicy,
    CompanionRefusalError,
    CompanionRequest,
    CompanionResult,
    CompanionService,
    TimeAction,
    decode_request,
    parse_text,
)
from lychd.compositions.blockworld.companion_feedback import MAX_FEEDBACK_CHARS, feedback_text, reply_text
from lychd.compositions.blockworld.companion_intent import validate_raw_instruction
from lychd.domain.codex.sigil import Sigil
from lychd.domain.cortex.runs import RunStatus
from lychd.system.services.companion_session import CompanionSession, LocalCompanionRunner
from tests.integration.test_companion import FakeBridge, policy
from tests.integration.test_companion_weather import WeatherBridgeFixture


class ClockBridgeFixture(FakeBridge):
    def __init__(self, fault: str | None = None) -> None:
        super().__init__()
        self.fault = fault
        self.before = 1001
        self.after = 25_000
        self.resolved = "day"

    def clock(self, requested: str = "day") -> dict[str, Any]:
        return {
            "profile": "blockworld.clock@1",
            "boot_id": self.boot,
            "generation": self.generation,
            "actor_id": self.actor,
            "scope": "overworld_clock",
            "anchor_dimension": "minecraft:overworld",
            "clock": "minecraft:overworld",
            "requested_mode": requested,
            "mode": self.resolved,
            "before_ticks": self.before,
            "after_ticks": self.after,
            "delta_ticks": self.after - self.before,
            "before_phase": self.before % 24_000,
            "after_phase": self.after % 24_000,
            "before_cycle": self.before // 24_000,
            "after_cycle": self.after // 24_000,
            "cycle_increment": self.after // 24_000 - self.before // 24_000,
            "before_partial_tick": 0.25,
            "partial_tick": 0.25 if self.before == self.after else 0.0,
            "rate": -0.5,
            "paused": True,
            "time_advancing": False,
            "world_tick": 123,
            "timestamp_ms": int(time.time() * 1000),
        }

    async def handle(self, request: httpx.Request) -> httpx.Response:  # noqa: C901 - distinct wire faults
        response = await super().handle(request)
        if request.url.path != "/v1/actions":
            return response
        outgoing = json.loads(request.content)
        if outgoing["kind"] != "time" and self.fault != "cross_kind":
            return response
        if self.fault == "lost_ack":
            msg = "Lost clock acknowledgement after effect"
            raise httpx.ReadError(msg, request=request)
        record = response.json()
        observation = self.clock(outgoing["args"].get("mode", "day"))
        record["observation"] = observation
        replacements: dict[str, Any] = {
            "boot_id": str(uuid4()),
            "actor_id": str(uuid4()),
            "generation": self.generation + 1,
            "scope": "server_weather",
            "anchor_dimension": "minecraft:the_end",
            "clock": "minecraft:the_end",
            "requested_mode": "toggle",
            "mode": "night",
            "before_ticks": -1,
            "after_ticks": 1000,
            "delta_ticks": 0,
            "before_phase": 1000,
            "after_phase": 0,
            "before_cycle": 1,
            "after_cycle": 0,
            "cycle_increment": True,
            "partial_tick": 0.5,
            "rate": "1.0",
            "paused": 1,
            "time_advancing": "true",
            "extra": "/time set day",
        }
        if self.fault in replacements:
            observation[self.fault] = replacements[self.fault]
        elif self.fault == "foreign_request":
            observation["requested_mode"] = "toggle"
            observation["mode"] = "night"
            observation.update(
                after_ticks=13_000, after_phase=13_000, after_cycle=0, delta_ticks=11_999, cycle_increment=0
            )
        elif self.fault == "stale":
            observation["timestamp_ms"] -= 60_000
        elif self.fault == "future":
            observation["timestamp_ms"] += 60_000
        elif self.fault == "missing":
            record["observation"] = None
        elif self.fault == "pose":
            record["observation"] = self.state()
        elif self.fault == "weather":
            record["observation"] = WeatherBridgeFixture().weather()
        elif self.fault == "disabled":
            record.update(status="refused", observation=None)
        elif self.fault == "server_unknown":
            record.update(status="unknown", observation=None)
        return httpx.Response(202, json=record)


def clock_request(text: str = "čas deň") -> CompanionRequest:
    return CompanionRequest(request_id=str(uuid4()), action=parse_text(text))


def session_for(fake: ClockBridgeFixture, *, enabled: bool = True) -> CompanionSession:
    selected = CompanionPolicy.model_validate({**policy().model_dump(), "allow_time": enabled})
    bridge = fake.bridge()
    return CompanionSession(LocalCompanionRunner(CompanionService(selected, bridge), bridge), bridge)


@pytest.mark.parametrize(
    ("text", "mode"),
    [
        ("time day", "day"),
        ("time night", "night"),
        ("time toggle", "toggle"),
        ("Čas deň!", "day"),
        ("cas den", "day"),
        ("čas noc", "night"),
        ("prepni deň noc", "toggle"),
        ("prepni deň/noc", "toggle"),
        ("prepni den noc", "toggle"),
        ("prepni den/noc", "toggle"),
        ("přepni den noc", "toggle"),
        ("přepni den/noc", "toggle"),
        ("toggle day night", "toggle"),
        ("toggle day/night", "toggle"),
        ("nastav deň", "day"),
        ("nastav den", "day"),
        ("nastav noc", "night"),
        ("set day", "day"),
        ("set night", "night"),
        ("make it day", "day"),
        ("make it night", "night"),
    ],
)
def test_exact_clock_commands_have_no_numeric_clock_authority(text: str, mode: str) -> None:
    action = parse_text(text)
    assert isinstance(action, TimeAction)
    assert action.model_dump() == {"kind": "time", "revision": 1, "scope": "overworld_clock", "mode": mode}
    with pytest.raises(ValueError, match="bounded interpretation"):
        validate_raw_instruction(text)


@pytest.mark.parametrize(
    "text",
    [
        "time",
        "time 13000",
        "time day night",
        "time day then follow",
        "/time set day",
        "čas",
        "čas ráno",
        "prepni deň na noc",
        "zmeň čas",
        "change time",
        "time day\n",
    ],
)
def test_malformed_clock_commands_never_enter_interpretation(text: str) -> None:
    with pytest.raises(ValueError, match=r"Time|Unsupported|Instruction"):
        parse_text(text)
    with pytest.raises(ValueError, match="bounded interpretation"):
        validate_raw_instruction(text)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("revision", True),
        ("revision", 1.0),
        ("revision", "1"),
        ("revision", 2),
        ("scope", "server_weather"),
        ("mode", "noon"),
        ("ticks", 1000),
        ("command", "time set day"),
    ],
)
def test_time_schema_refuses_coercion_and_expanded_effects(field: str, value: Any) -> None:
    request = clock_request().model_dump()
    request["action"][field] = value
    with pytest.raises(ValueError, match="validation error"):
        decode_request(json.dumps(request))


@pytest.mark.parametrize(("enabled", "scope"), [(False, False), (False, True), (True, False)])
@pytest.mark.asyncio
async def test_time_requires_policy_and_scope_both_at_admission_and_handoff(*, enabled: bool, scope: bool) -> None:
    bridge = FakeBridge().bridge()
    selected = CompanionPolicy.model_validate({**policy().model_dump(), "allow_time": enabled, "allow_weather": True})
    service = CompanionService(selected, bridge)
    scopes = {"blockworld:companion", "blockworld:weather"}
    if scope:
        scopes.add("blockworld:time")
    principal = Sigil(name=selected.principal, scopes=frozenset(scopes))
    try:
        state = await bridge.open()
        for check in (
            lambda: service.validate(clock_request(), principal),
            lambda: service._authorize(clock_request(), principal, state),  # pyright: ignore[reportPrivateUsage] - effect-time grant oracle
        ):
            with pytest.raises(CompanionRefusalError) as error:
                check()
            assert error.value.reason == "time_not_authorized"
    finally:
        await bridge.aclose()


@pytest.mark.asyncio
async def test_default_session_never_posts_clock_action() -> None:
    fake = ClockBridgeFixture()
    session = session_for(fake, enabled=False)
    await session.open()
    try:
        result = await session.enqueue(clock_request())
        assert (result.kind, result.reason) == ("refused", "time_not_authorized")
        assert fake.requests == []
    finally:
        await session.aclose()


@pytest.mark.parametrize(
    ("before", "mode", "after", "resolved"),
    [
        (1001, "day", 25_000, "day"),
        (1000, "day", 1000, "day"),
        (25_000, "day", 25_000, "day"),
        (0, "toggle", 13_000, "night"),
        (11_999, "toggle", 13_000, "night"),
        (12_000, "toggle", 25_000, "day"),
        (13_000, "toggle", 25_000, "day"),
        (49_000, "night", 61_000, "night"),
    ],
)
@pytest.mark.asyncio
async def test_clock_crosses_native_graph_once_with_closed_readback(
    before: int, mode: str, after: int, resolved: str
) -> None:
    fake = ClockBridgeFixture()
    fake.before, fake.after, fake.resolved = before, after, resolved
    session = session_for(fake)
    await session.open()
    try:
        request = clock_request(f"time {mode}")
        future = session.enqueue(request)
        assert session.enqueue(request) is future
        outcome = await future
        assert outcome.kind == "applied"
        assert outcome.result is not None
        result = outcome.result
        assert result.clock is not None
        assert (result.clock.before_ticks, result.clock.after_ticks, result.clock.mode) == (before, after, resolved)
        assert result.clock.delta_ticks == after - before
        assert (result.clock.rate, result.clock.paused, result.clock.time_advancing) == (-0.5, True, False)
        assert result.cell is result.weather is result.observation is result.controller_expires_at_ms is None
        assert len(fake.requests) == 1
        assert fake.requests[0]["args"] == request.action.model_dump(exclude={"kind"})
        assert fake.requests[0]["run_id"] == outcome.run_id
        assert session.runner.services is not None
        assert outcome.run_id is not None
        run = await session.runner.services.ledger.get(outcome.run_id)
        assert run is not None
        assert run.status is RunStatus.DONE
        with pytest.raises(ValueError, match="changed content"):
            session.enqueue(request.model_copy(update={"action": parse_text("idle")}))
        assert len(fake.requests) == 1
    finally:
        await session.aclose()


@pytest.mark.parametrize(
    "fault",
    [
        "boot_id",
        "actor_id",
        "generation",
        "scope",
        "anchor_dimension",
        "clock",
        "requested_mode",
        "mode",
        "before_ticks",
        "after_ticks",
        "delta_ticks",
        "before_phase",
        "after_phase",
        "before_cycle",
        "after_cycle",
        "cycle_increment",
        "partial_tick",
        "rate",
        "paused",
        "time_advancing",
        "extra",
        "foreign_request",
        "stale",
        "future",
        "missing",
        "pose",
        "weather",
        "lost_ack",
        "server_unknown",
    ],
)
@pytest.mark.asyncio
async def test_bad_clock_receipts_are_unknown_without_repost(fault: str) -> None:
    fake = ClockBridgeFixture(fault)
    session = session_for(fake)
    await session.open()
    try:
        outcome = await session.enqueue(clock_request())
        assert outcome.kind == "unknown"
        assert outcome.result is not None
        assert outcome.result.clock is None
        assert len(fake.requests) == 1
    finally:
        await session.aclose()


@pytest.mark.asyncio
async def test_clock_cannot_confirm_state_and_server_disabled_is_not_success() -> None:
    for fault in ("cross_kind", "disabled"):
        fake = ClockBridgeFixture(fault)
        session = session_for(fake)
        await session.open()
        try:
            request = clock_request("state" if fault == "cross_kind" else "time day")
            outcome = await session.enqueue(request)
            assert outcome.kind == ("unknown" if fault == "cross_kind" else "refused")
            assert outcome.result is not None
            assert outcome.result.clock is None
        finally:
            await session.aclose()


@pytest.mark.asyncio
async def test_stop_cancels_queued_toggle_without_replay() -> None:
    fake = ClockBridgeFixture()
    fake.delay = True
    session = session_for(fake)
    await session.open()
    try:
        first = session.enqueue(clock_request())
        await fake.action_started.wait()
        toggle = clock_request("prepni deň/noc")
        queued = session.enqueue(toggle)
        await session.stop()
        assert (await queued).kind == "cancelled"
        await asyncio.gather(first, return_exceptions=True)
        assert all(request["action_id"] != toggle.request_id for request in fake.requests)
        assert len(fake.stop_ids) == 1
    finally:
        await session.aclose()


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
def test_clock_feedback_reports_cycles_delta_and_preserved_settings(language: str) -> None:
    request = clock_request()
    clock = ClockObservation.model_validate(ClockBridgeFixture().clock())
    result = CompanionResult(request_id=request.request_id, kind="applied", detail="private untrusted", clock=clock)
    text = feedback_text(request, result, kind="applied", language=language)
    assert "23999" in text
    assert "0 → 1" in text
    assert "-0.5" in text
    assert "private" not in text
    assert len(text) <= MAX_FEEDBACK_CHARS
    assert feedback_text(
        request, result.model_copy(update={"clock": None}), kind="applied", language=language
    ) == reply_text("unknown", language)
    other = clock_request("time night")
    assert feedback_text(
        other, result.model_copy(update={"request_id": other.request_id}), kind="applied", language=language
    ) == reply_text("unknown", language)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("before_ticks", True),
        ("before_ticks", 1001.0),
        ("after_ticks", 9_223_372_036_854_775_808),
        ("rate", float("inf")),
        ("rate", float("nan")),
        ("partial_tick", float("inf")),
        ("before_partial_tick", float("nan")),
        ("cycle_increment", 1.0),
    ],
)
def test_clock_observation_refuses_nonfinite_coerced_or_overflowed_fields(field: str, value: Any) -> None:
    document = ClockBridgeFixture().clock()
    document[field] = value
    with pytest.raises(ValueError, match="validation error"):
        ClockObservation.model_validate(document)


def test_clock_qualification_keeps_engine_synthetic_and_human_boundaries_distinct() -> None:
    from pathlib import Path

    receipt = json.loads(
        (Path(__file__).resolve().parents[2] / "tests/fixtures/blockworld/companion-cpu-runtime.json").read_text()
    )
    current = receipt["clock_requalification"]
    assert (current["operation"], current["scope"], current["observation_profile"]) == (
        "time@1",
        "overworld_clock",
        "blockworld.clock@1",
    )
    assert (current["pattern_revision"], current["implementation_revision"], current["checkpoint_schema"]) == (
        "4",
        "py.6",
        "companion-state-v6",
    )
    assert current["placement_policy"] == "next-or-equal-forward-marker"
    assert current["modes"] == ["day", "night", "toggle"]
    assert current["portable_new_cases"] == 171
    assert current["java_junit_cases"] == 43
    assert current["clock_immediate_engine_placements"] == 252
    for key in ("clock_required_game_tests", "controller_required_game_tests", "weather_required_game_tests"):
        assert current[key] == 2
    assert current["real_npc_continuity_probe"] == "direct production composite during original short follow"
    for key in (
        "no_op_fraction_preserved",
        "settings_preserved_including_negative_rate",
        "overflow_refuses",
        "current_profile_checked_before_mutation",
        "incompatible_profile_matcher_negatives",
        "other_clock_simulation_weather_preserved",
        "fixture_exact_clock_fraction_settings_rule_restored",
        "real_npc_original_deadline_preserved",
        "post_mutation_readback_unknown",
        "unknown_never_reposted",
        "independent_host_server_permission",
        "host_policy_scope_rechecked",
        "malformed_time_before_interpretation",
        "live_clock_preserved_original_controller_limit",
        "live_closed_stopped",
        "server_artifact_test_assets_excluded",
        "fifine_default_source_inventory_only",
    ):
        assert current[key] is True
    assert current["server_artifact_production_classes_matched"] == 34
    assert current["live_text_native_runs_applied"] == 4
    assert current["live_synthetic_voice_cases"] == 5
    assert current["live_synthetic_voice_runs_applied"] == current["generated_reply_wavs"] == 3
    assert current["live_synthetic_voice_unexpected_refusals"] == 2
    assert current["live_synthetic_voice_applied_languages"] == ["cs", "en", "sk"]
    assert current["live_synthetic_voice_refused_languages"] == ["sk", "sk"]
    assert current["actual_stt_calls"] == 5
    assert current["actual_tts_calls"] == 8
    for key in (
        "human_microphone",
        "physical_playback",
        "human_accuracy_benchmark",
        "game_client_launched",
        "wakeword_or_continuous_capture_added",
        "player_bot_or_building_added",
        "gpu_or_interpreter_used",
        "paid_or_hosted_voice_requested",
        "model_or_speech_provider_changed",
        "host_routing_changed",
        "unchanged_historical_live_cohorts_reexecuted",
        "old_pattern_closures_migrated",
        "incompatible_runtime_registry_datapack_replaced",
        "engine_readback_failure_forced",
        "graceful_world_save_attested",
    ):
        assert current[key] is False
