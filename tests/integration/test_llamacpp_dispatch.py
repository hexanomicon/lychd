"""Real router readiness, dispatch, and orchestration with an isolated HTTP peer."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import httpx2
import pytest
import respx
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models import override_allow_model_requests

from lychd.config.settings.orchestration import SwitchingSettings
from lychd.domain.animation.capabilities import CapabilityPhase
from lychd.domain.animation.errors import CapabilityUnavailable, HardwareTransitionRequired
from lychd.domain.animation.schemas import LocalModelConfig
from lychd.domain.animation.services.declarations import AnimatorDeclarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.orchestration.arbiter import TransitionArbiter
from lychd.domain.orchestration.broker import GhoulBroker
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.policies import DeclaredConflictPolicy
from lychd.extensions.builtin.animator import LlamaCppMode, LlamaCppSoulstoneConfig
from lychd.extensions.builtin.animator.runtimes import LlamaCppRuntimeAdapter
from tests.runtime_guards import InertSoftActivationGuard

pytestmark = pytest.mark.httpx2(assert_all_called=False)


def _router_registry(model_id: str = "target") -> AnimatorRegistry:
    stone = LlamaCppSoulstoneConfig(
        name="router",
        port=8080,
        startup_mode=LlamaCppMode.ROUTER,
        models_dir="/models",
        models=(LocalModelConfig(id=model_id, path=Path(f"/models/{model_id}.gguf")),),
    )
    registry = AnimatorRegistry(
        declarations=AnimatorDeclarations(soulstones=(stone,), portals=()),
        runtime_adapters=(LlamaCppRuntimeAdapter(),),
    )
    registry.load()
    return registry


@pytest.mark.asyncio
async def test_loading_router_model_converges_without_duplicate_load(httpx2_mock: respx.MockRouter) -> None:
    inventory_probes = 0

    def inventory(_request: httpx.Request) -> httpx.Response:
        nonlocal inventory_probes
        inventory_probes += 1
        # Hydration, dispatch, and both planning probes all observe loading.
        status = "loaded" if inventory_probes >= 6 else "loading"
        return httpx.Response(200, json={"data": [{"id": "target", "status": {"value": status}}]})

    httpx2_mock.get("http://localhost:8080/health").respond(200, json={"status": "ok"})
    httpx2_mock.get("http://localhost:8080/models").mock(side_effect=inventory)
    duplicate_load = httpx2_mock.post("http://localhost:8080/models/load").respond(
        400, json={"error": {"message": "model is already running"}}
    )
    registry = _router_registry()
    leases = LeaseLedger()
    dispatcher = Dispatcher(registry, leases=leases)
    broker = GhoulBroker()
    actuator = AsyncMock()
    manager = OrchestratorManager(
        broker,
        registry,
        leases=leases,
        policy=DeclaredConflictPolicy(),
        arbiter=TransitionArbiter(),
        actuator=actuator,
        switching=SwitchingSettings(),
        soft_activation_guard=InertSoftActivationGuard(),
    )

    with pytest.raises(HardwareTransitionRequired):
        async with dispatcher.lease_grant(family="chat", model_name="target", run_id="loading"):
            pytest.fail("a loading model must not issue a grant")
    assert leases.active() == []
    async with asyncio.timeout(2):
        plan = await manager.request_transition("router:chat:target", priority=50)
    assert plan.action_type == "SOFT_SWAP"
    assert not duplicate_load.called
    actuator.apply.assert_not_awaited()
    assert manager.containment_reason is None
    assert not broker.paused
    async with dispatcher.lease_grant(family="chat", model_name="target", run_id="loading") as grant:
        assert grant.state.phase is CapabilityPhase.WARM
        assert grant.model is not None
    assert leases.active() == []


@pytest.mark.asyncio
async def test_missing_router_model_cannot_request_hardware(httpx2_mock: respx.MockRouter) -> None:
    httpx2_mock.get("http://localhost:8080/health").respond(200, json={"status": "ok"})
    httpx2_mock.get("http://localhost:8080/models").respond(200, json={"data": []})
    registry = _router_registry("missing")
    dispatcher = Dispatcher(registry, leases=LeaseLedger())

    with pytest.raises(CapabilityUnavailable):
        async with dispatcher.lease_grant(family="chat", model_name="missing", run_id="missing"):
            pytest.fail("an absent model cannot issue a grant")


@pytest.mark.asyncio
async def test_router_inference_cannot_autoload_after_losing_warmth(
    httpx2_mock: respx.MockRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    httpx2_mock.get("http://localhost:8080/health").respond(200, json={"status": "ok"})
    httpx2_mock.get("http://localhost:8080/models").respond(
        200, json={"data": [{"id": "target", "status": {"value": "loaded"}}]}
    )
    requests: list[httpx2.Request] = []

    def reject_unloaded(request: httpx2.Request) -> httpx2.Response:
        assert request.method == "POST"
        assert str(request.url) == "http://localhost:8080/v1/chat/completions?autoload=false"
        requests.append(request)
        return httpx2.Response(400, json={"error": {"message": "model is not loaded"}})

    monkeypatch.setattr(
        "lychd.domain.animation.model_factory._model_http_client",
        lambda: httpx2.AsyncClient(transport=httpx2.MockTransport(reject_unloaded)),
    )
    registry = _router_registry()
    leases = LeaseLedger()
    dispatcher = Dispatcher(registry, leases=leases)

    # The runtime may lose a model after the final issue probe. The request
    # must refuse it instead of letting the router start or evict a model.
    async with (
        dispatcher.lease_grant(family="chat", model_name="target", run_id="lost-warmth") as grant,
        Agent(model=grant.model) as agent,
    ):
        with override_allow_model_requests(True), pytest.raises(ModelHTTPError):  # noqa: FBT003 - third-party API
            await agent.run("Local test prompt")
    assert len(requests) == 1
    assert requests[0].url.params["autoload"] == "false"
    assert leases.active() == []


@pytest.mark.parametrize(("schema", "with_tool"), [(True, False), (True, True), (False, False)])
@pytest.mark.asyncio
async def test_fixed_model_structured_output_wire(
    monkeypatch: pytest.MonkeyPatch, *, schema: bool, with_tool: bool
) -> None:
    import json

    from pydantic_ai import DeferredToolRequests

    from lychd.agents.outputs import BridgeReply
    from lychd.domain.animation.connectors import ModelConnector

    def inspect(request: httpx2.Request) -> httpx2.Response:
        payload = json.loads(request.content)
        assert request.url.path == "/v1/chat/completions"
        if schema and not with_tool:
            assert "tools" not in payload
            shape = payload["response_format"]
            assert shape["type"] == "json_schema"
            definition = shape["json_schema"]["schema"]
            assert definition["properties"]["answer"]["type"] == "string"
            assert definition["properties"]["fragments"]["items"]["type"] == "object"
            assert "$defs" not in definition
        else:
            assert "response_format" not in payload
            functions = {tool["function"]["name"] for tool in payload["tools"]}
            assert "final_result" in functions
            assert ("lookup" in functions) == with_tool
        return httpx2.Response(400, json={"error": {"message": "checked wire format"}})

    monkeypatch.setattr(
        "lychd.domain.animation.model_factory._model_http_client",
        lambda: httpx2.AsyncClient(transport=httpx2.MockTransport(inspect)),
    )
    stone = LlamaCppSoulstoneConfig(
        name="personal",
        startup_mode=LlamaCppMode.SINGLE,
        model_path="/models/personal.gguf",
        served_model_id="personal",
        port=8081,
        structured_output="json-schema" if schema else None,
    )
    runtime = LlamaCppRuntimeAdapter().build_runtime(stone)
    assert runtime is not None
    assert isinstance(runtime.connector, ModelConnector)
    async with Agent(runtime.connector.get_model(), output_type=[BridgeReply, DeferredToolRequests]) as agent:
        if with_tool:

            @agent.tool_plain
            def lookup() -> str:
                return "test"

        with override_allow_model_requests(True), pytest.raises(ModelHTTPError, match="checked wire format"):  # noqa: FBT003
            await agent.run("test")
