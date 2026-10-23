"""Keep server weather opt-in explicit across CLI policy and native admission."""

from __future__ import annotations

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
    with TemporaryDirectory(prefix="lychd-companion-weather-") as name:
        yield Path(name)


@pytest.mark.parametrize("allow_weather", [False, True])
@pytest.mark.asyncio
async def test_weather_option_controls_assembled_native_scope(
    workspace: Path, monkeypatch: pytest.MonkeyPatch, *, allow_weather: bool
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
    if allow_weather:
        arguments.append("--allow-weather")
    options = companion_lab.parser().parse_args(arguments)
    assert options.allow_weather is allow_weather
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
        assert runner.service.policy.allow_weather is allow_weather
        run_id = str(uuid4())
        submit = AsyncMock(return_value=SimpleNamespace(run_id=run_id))
        runner.services = cast("AltarServices", SimpleNamespace(run_engine=SimpleNamespace(submit=submit)))
        request = CompanionRequest(request_id=str(uuid4()), action=parse_text("state"))
        assert await runner.submit(request) == run_id
        submit.assert_awaited_once()
        intent = submit.call_args.args[0]
        assert isinstance(intent, Intent)
        expected = {"blockworld:companion", "blockworld:weather"} if allow_weather else {"blockworld:companion"}
        assert intent.sigil_scopes == frozenset(expected)
        assert intent.sigil_name == runner.service.policy.principal
        assert intent.session_id == runner.service.policy.session_id
        assert intent.source == "blockworld.companion"
        assert fake.reads == 0
        assert fake.requests == fake.stop_ids == []
    finally:
        await bridge.aclose()


@pytest.mark.parametrize("text", ["prepni počasie", "zmeň počasie", "change weather", "toggle weather", "změň počasí"])
@pytest.mark.parametrize("source", ["text", "transcript"])
@pytest.mark.asyncio
async def test_weather_toggle_refuses_before_optional_interpretation(
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
