"""Keep clock opt-in independent from weather and outside optional interpretation."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Literal, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from scripts import companion_lab
from scripts.voice_probe import PrivateWorkspace

from lychd.agents.router import Intent
from lychd.compositions.blockworld.companion import CompanionRequest, CompanionService, parse_text
from lychd.compositions.blockworld.companion_intent import CompanionIntentProfile
from lychd.interface.web.altar_services import AltarServices
from lychd.system.services.companion_bridge import BridgeBinding, CompanionBridge
from lychd.system.services.companion_session import CompanionSession, LocalCompanionRunner
from tests.integration.test_companion import FakeBridge
from tests.unit.cli.test_companion_lab import ConsoleSession

CHECKOUT = Path(__file__).resolve().parents[3]


@pytest.fixture
def workspace() -> Iterator[Path]:
    with TemporaryDirectory(prefix="lychd-companion-time-") as name:
        yield Path(name)


@pytest.mark.parametrize("allow_time", [False, True])
@pytest.mark.parametrize("allow_weather", [False, True])
@pytest.mark.asyncio
async def test_time_and_weather_options_control_independent_assembled_native_scopes(
    workspace: Path, monkeypatch: pytest.MonkeyPatch, *, allow_time: bool, allow_weather: bool
) -> None:
    fake = FakeBridge()
    bridge = fake.bridge()
    bridge_path = workspace / "bridge.json"
    bridge_path.write_text(json.dumps({"endpoint": bridge.binding.endpoint, "token": "a" * 64, "actor_id": fake.actor}))
    bridge_path.chmod(0o600)
    arguments = [
        "--workspace",
        str(workspace),
        "--checkout-root",
        str(CHECKOUT),
        "--bridge-profile",
        str(bridge_path),
        "--bounds",
        "-24",
        "-64",
        "-24",
        "24",
        "320",
        "24",
    ]
    if allow_time:
        arguments.append("--allow-time")
    if allow_weather:
        arguments.append("--allow-weather")
    options = companion_lab.parser().parse_args(arguments)
    assert (options.allow_time, options.allow_weather) == (allow_time, allow_weather)
    runners: list[LocalCompanionRunner] = []

    class AssemblyObservedError(Exception):
        pass

    def assembled(
        service: CompanionService,
        selected_bridge: CompanionBridge,
        *,
        intent_profile: CompanionIntentProfile | None,
    ) -> LocalCompanionRunner:
        assert intent_profile is None
        runners.append(LocalCompanionRunner(service, selected_bridge))
        raise AssemblyObservedError

    def selected_bridge(_binding: BridgeBinding) -> CompanionBridge:
        return bridge

    monkeypatch.setattr(companion_lab, "CompanionBridge", selected_bridge)
    monkeypatch.setattr(companion_lab, "LocalCompanionRunner", assembled)
    try:
        with pytest.raises(AssemblyObservedError):
            await companion_lab.run(options)
        assert len(runners) == 1
        runner = runners[0]
        assert runner.service.policy.allow_time is allow_time
        assert runner.service.policy.allow_weather is allow_weather
        run_id = str(uuid4())
        submit = AsyncMock(return_value=SimpleNamespace(run_id=run_id))
        runner.services = cast("AltarServices", SimpleNamespace(run_engine=SimpleNamespace(submit=submit)))
        request = CompanionRequest(request_id=str(uuid4()), action=parse_text("state"))
        assert await runner.submit(request) == run_id
        submit.assert_awaited_once()
        intent = submit.call_args.args[0]
        assert isinstance(intent, Intent)
        expected = {"blockworld:companion"}
        if allow_time:
            expected.add("blockworld:time")
        if allow_weather:
            expected.add("blockworld:weather")
        assert intent.sigil_scopes == frozenset(expected)
        assert intent.sigil_name == runner.service.policy.principal
        assert intent.session_id == runner.service.policy.session_id
        assert intent.source == "blockworld.companion"
        assert fake.reads == 0
        assert fake.requests == fake.stop_ids == []
    finally:
        await bridge.aclose()


@pytest.mark.parametrize(
    "text",
    [
        "time",
        "čas",
        "cas",
        "day",
        "night",
        "deň",
        "den",
        "noc",
        "time tomorrow",
        "time day extra",
        "čas deň noc",
        "prepni deň",
        "prepni noc",
        "prepni deň noc extra",
        "prepni deň/noc extra",
        "přepni den",
        "toggle day",
        "toggle day night extra",
        "day night",
        "Could you make it day please",
        "Please tell me the time",
        "wait until night",
    ],
)
@pytest.mark.parametrize("source", ["text", "transcript"])
@pytest.mark.asyncio
async def test_malformed_or_ambiguous_time_refuses_before_optional_interpretation(
    workspace: Path, text: str, source: Literal["text", "transcript"]
) -> None:
    state = ConsoleSession()
    console = companion_lab.CompanionConsole(
        PrivateWorkspace(workspace, (CHECKOUT,)),
        cast("CompanionSession", state),
        intent_profile=CompanionIntentProfile(base_url="http://127.0.0.1:28761/v1", model_id="fixture-intent"),
    )
    with pytest.raises(ValueError, match="bounded interpretation"):
        console.submit(text, source=source)
    assert state.enqueued == []
    assert not console.replies
    assert console.voice_task is None


@pytest.mark.parametrize(
    ("text", "mode"),
    [
        ("time day", "day"),
        ("time night", "night"),
        ("time toggle", "toggle"),
        ("čas deň", "day"),
        ("čas den", "day"),
        ("čas noc", "night"),
        ("cas den", "day"),
        ("cas noc", "night"),
        ("prepni deň noc", "toggle"),
        ("prepni deň/noc", "toggle"),
        ("prepni den noc", "toggle"),
        ("prepni den/noc", "toggle"),
        ("přepni den noc", "toggle"),
        ("toggle day night", "toggle"),
    ],
)
@pytest.mark.parametrize("source", ["text", "transcript"])
@pytest.mark.asyncio
async def test_exact_time_text_and_transcript_keep_the_fixed_action_route(
    workspace: Path, monkeypatch: pytest.MonkeyPatch, text: str, mode: str, source: Literal["text", "transcript"]
) -> None:
    def forbidden(_text: str) -> str:
        pytest.fail("An exact clock instruction reached optional interpretation admission")

    monkeypatch.setattr(companion_lab, "validate_raw_instruction", forbidden)
    state = ConsoleSession()
    console = companion_lab.CompanionConsole(
        PrivateWorkspace(workspace, (CHECKOUT,)),
        cast("CompanionSession", state),
        intent_profile=CompanionIntentProfile(base_url="http://127.0.0.1:28761/v1", model_id="fixture-intent"),
    )
    outcome = await console.submit(text, source=source)
    await asyncio.gather(*console.replies)
    (request,) = state.enqueued
    assert isinstance(request, CompanionRequest)
    assert request.request_id == outcome.request_id
    assert request.source == source
    assert request.transcript == text
    assert request.action.model_dump() == {
        "kind": "time",
        "revision": 1,
        "scope": "overworld_clock",
        "mode": mode,
    }
