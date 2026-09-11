"""Workflow scenarios across real declaration, registry, dispatch, and lease boundaries.

Only the external runtime is substituted: no endpoint, host service, or model
provider is contacted. Probe scripts represent consecutive observed realities.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.models.test import TestModel
from pydantic_ai.toolsets import AbstractToolset, FunctionToolset

from lychd.domain.animation.animators import RuntimeAnimator
from lychd.domain.animation.capabilities import CapabilityPhase, CapabilitySpec, CapabilityState
from lychd.domain.animation.errors import CapabilityUnavailable, HardwareTransitionRequired
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import (
    CapabilityFamily,
    ConcurrencyIntent,
    LocalModelConfig,
    ModelCapabilityHints,
    SoulstoneConfig,
)
from lychd.domain.animation.services.adapters.runtimes.openai_compat import OpenAICompatibleRuntimeAdapter
from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector, SoulstoneAnimator
from lychd.domain.animation.services.declarations import AnimatorDeclarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.leases import LeaseLedger
from lychd.extensions.builtin.animator import VllmSoulstoneConfig


class OfflineConnector(OpenAICompatibleConnector):
    """Hydrate only deterministic local models while retaining the connector contract."""

    def __init__(self, *, toolsets: Sequence[AbstractToolset[Any]] = ()) -> None:
        super().__init__(link=Link(up=True), base_url="http://runtime.invalid/v1", toolsets=toolsets)
        self.model_requests: list[str | None] = []

    def get_model(self, *, model_id: str | None = None) -> Model:
        self.model_requests.append(model_id)
        return TestModel(custom_output_text="local reply")


class ScriptedRuntimeAdapter(OpenAICompatibleRuntimeAdapter):
    """Use production catalogue synthesis and script only external observations."""

    def __init__(self) -> None:
        super().__init__(runtime="vllm", config_type=VllmSoulstoneConfig)
        self.observations: dict[str, deque[CapabilityPhase | Exception]] = {}
        self.probes: list[str] = []
        self.connectors: dict[str, OfflineConnector] = {}
        self.toolsets: dict[str, tuple[AbstractToolset[Any], ...]] = {}

    def observe(self, animator: str, *phases: CapabilityPhase | Exception) -> None:
        self.observations[animator] = deque(phases)

    def build_runtime(self, soulstone: SoulstoneConfig) -> RuntimeAnimator:
        connector = OfflineConnector(toolsets=self.toolsets.get(soulstone.name, ()))
        self.connectors[soulstone.name] = connector
        return SoulstoneAnimator(rune=soulstone, connector=connector)

    async def probe_capability_states(
        self,
        animator: RuntimeAnimator,
        specs: list[CapabilitySpec],
    ) -> list[CapabilityState]:
        self.probes.append(animator.name)
        script = self.observations.get(animator.name)
        observed = script[0] if script else CapabilityPhase.WARM
        if script and len(script) > 1:
            script.popleft()
        if isinstance(observed, Exception):
            raise observed
        return [CapabilityState(capability_key=spec.key, phase=observed) for spec in specs]


def _stone(
    name: str,
    *,
    model: str = "main",
    family: CapabilityFamily = CapabilityFamily.CHAT,
    modalities: tuple[str, ...] = ("text",),
    tools: bool = True,
    dedicated: bool = True,
) -> VllmSoulstoneConfig:
    return VllmSoulstoneConfig(
        name=name,
        concurrency=ConcurrencyIntent(dedicated=dedicated),
        models=(
            LocalModelConfig(
                id=model,
                path=Path("/models/offline"),
                capabilities=ModelCapabilityHints(families=(family,), modalities_in=modalities, supports_tools=tools),
            ),
        ),
    )


def _dispatch(
    *stones: VllmSoulstoneConfig,
    adapter: ScriptedRuntimeAdapter | None = None,
) -> tuple[Dispatcher, AnimatorRegistry, LeaseLedger, ScriptedRuntimeAdapter]:
    runtime = adapter or ScriptedRuntimeAdapter()
    registry = AnimatorRegistry(
        declarations=AnimatorDeclarations(soulstones=stones, portals=()),
        runtime_adapters=[runtime],
    )
    registry.load()
    leases = LeaseLedger()
    return Dispatcher(registry=registry, leases=leases), registry, leases, runtime


@pytest.mark.asyncio
async def test_image_chat_selects_one_candidate_meeting_every_requirement() -> None:
    dispatcher, _, leases, adapter = _dispatch(
        _stone("a-text"),
        _stone("b-image-no-tools", modalities=("text", "image"), tools=False),
        _stone("c-wrong-model", model="other", modalities=("text", "image")),
        _stone("z-qualified", modalities=("text", "image")),
    )

    async with dispatcher.lease_grant(
        family="chat",
        model_name="main",
        require_modalities=("text", "image"),
        requires_tools=True,
        run_id="image-review",
    ) as grant:
        assert grant.spec.animator_name == "z-qualified"
        assert len(leases.active()) == 1
        assert grant.model is not None
    assert leases.active() == []
    assert adapter.connectors["a-text"].model_requests == []
    assert adapter.connectors["b-image-no-tools"].model_requests == []
    assert adapter.connectors["c-wrong-model"].model_requests == []


@pytest.mark.asyncio
async def test_model_pin_never_substitutes_a_different_healthy_model() -> None:
    dispatcher, _, leases, adapter = _dispatch(_stone("available", model="other"))

    with pytest.raises(CapabilityUnavailable):
        async with dispatcher.lease_grant(family="chat", model_name="required", run_id="pinned"):
            pytest.fail("a different model does not fulfill an exact model pin")
    assert leases.active() == []
    assert adapter.connectors["available"].model_requests == []


@pytest.mark.asyncio
async def test_text_only_catalogue_cannot_admit_image_material() -> None:
    dispatcher, _, leases, adapter = _dispatch(_stone("text-only"))

    with pytest.raises(CapabilityUnavailable):
        async with dispatcher.lease_grant(family="chat", require_modalities=("image",), run_id="image"):
            pytest.fail("image input requires an explicit image declaration")
    assert leases.active() == []
    assert adapter.connectors["text-only"].model_requests == []


@pytest.mark.asyncio
async def test_text_chat_stream_consumes_admitted_model_and_releases_lease() -> None:
    dispatcher, _, leases, _ = _dispatch(_stone("chat"))

    async with dispatcher.lease_grant(family="chat", run_id="stream") as grant:
        assert grant.model is not None
        agent = Agent(model=grant.model)
        async with agent.run_stream("Hello") as result:
            assert await result.get_output() == "local reply"
            assert len(leases.active()) == 1
    assert leases.active() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", [CapabilityPhase.COLD, CapabilityPhase.ACTIVATABLE, CapabilityPhase.WARMING])
async def test_managed_runtime_losing_warmth_at_issue_requests_hardware_remedy(phase: CapabilityPhase) -> None:
    adapter = ScriptedRuntimeAdapter()
    adapter.observe("chat", CapabilityPhase.WARM, CapabilityPhase.WARM, phase)
    dispatcher, _, leases, _ = _dispatch(_stone("chat"), adapter=adapter)

    with pytest.raises(HardwareTransitionRequired) as error:
        async with dispatcher.lease_grant(family="chat", run_id="runtime-restarted"):
            pytest.fail("the issue-time observation must govern transition or admission")
    assert error.value.capability_key == "chat:chat:main"
    assert leases.active() == []
    assert adapter.connectors["chat"].model_requests == []


@pytest.mark.asyncio
async def test_shared_runtime_losing_warmth_at_issue_remains_unavailable() -> None:
    adapter = ScriptedRuntimeAdapter()
    adapter.observe("shared", CapabilityPhase.WARM, CapabilityPhase.WARM, CapabilityPhase.COLD)
    dispatcher, _, leases, _ = _dispatch(_stone("shared", dedicated=False), adapter=adapter)

    with pytest.raises(CapabilityUnavailable):
        async with dispatcher.lease_grant(family="chat", run_id="shared-down"):
            pytest.fail("LychD must not request lifecycle control over a shared runtime")
    assert leases.active() == []
    assert adapter.connectors["shared"].model_requests == []


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", [CapabilityPhase.UNKNOWN, CapabilityPhase.ERROR])
async def test_unresolved_or_error_observation_at_issue_cannot_request_hardware(phase: CapabilityPhase) -> None:
    adapter = ScriptedRuntimeAdapter()
    adapter.observe("chat", CapabilityPhase.WARM, CapabilityPhase.WARM, phase)
    dispatcher, _, leases, _ = _dispatch(_stone("chat"), adapter=adapter)

    with pytest.raises(CapabilityUnavailable):
        async with dispatcher.lease_grant(family="chat", run_id="unresolved-issue"):
            pytest.fail("an unresolved or failed probe is not a hardware-remedy request")
    assert adapter.probes == ["chat", "chat", "chat"]
    assert leases.active() == []
    assert adapter.connectors["chat"].model_requests == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "family",
    [
        CapabilityFamily.VISION,
        CapabilityFamily.EMBEDDING,
        CapabilityFamily.STT,
        CapabilityFamily.TTS,
        CapabilityFamily.RERANK,
    ],
)
@pytest.mark.parametrize("phase", [CapabilityPhase.COLD, CapabilityPhase.WARM])
async def test_metadata_only_family_is_refused_before_readiness_or_hardware_work(
    family: CapabilityFamily,
    phase: CapabilityPhase,
) -> None:
    adapter = ScriptedRuntimeAdapter()
    adapter.observe("media", phase)
    dispatcher, _, leases, _ = _dispatch(_stone("media", family=family), adapter=adapter)
    hydrated_probes = len(adapter.probes)

    with pytest.raises(CapabilityUnavailable, match="executable"):
        async with dispatcher.lease_grant(family=family, run_id="media-workflow"):
            pytest.fail("metadata cannot authorize a media call or request its hardware")
    assert len(adapter.probes) == hydrated_probes
    assert leases.active() == []
    assert adapter.connectors["media"].model_requests == []


@pytest.mark.asyncio
async def test_tool_execution_requires_a_nonempty_toolset_and_never_hydrates_model() -> None:
    adapter = ScriptedRuntimeAdapter()
    toolset: FunctionToolset[Any] = FunctionToolset(id="offline-tools")
    toolset.add_function(lambda: "result", name="read_status")
    adapter.toolsets["with-tools"] = (toolset,)
    dispatcher, _, leases, _ = _dispatch(
        _stone("empty", model="empty", family=CapabilityFamily.TOOL_EXECUTION),
        _stone("with-tools", model="available", family=CapabilityFamily.TOOL_EXECUTION),
        adapter=adapter,
    )

    with pytest.raises(CapabilityUnavailable, match="toolset"):
        async with dispatcher.lease_grant(family="tool_execution", model_name="empty", run_id="tools"):
            pytest.fail("an empty tool connector is not an executable capability")
    async with dispatcher.lease_grant(family="tool_execution", model_name="available", run_id="tools") as grant:
        assert grant.model is None
        assert grant.toolsets == (toolset,)
    assert leases.active() == []
    assert all(connector.model_requests == [] for connector in adapter.connectors.values())


@pytest.mark.asyncio
async def test_next_step_reselects_after_drain_without_retaining_previous_lease() -> None:
    dispatcher, _, leases, _ = _dispatch(_stone("a"), _stone("b"))

    async with dispatcher.lease_grant(family="chat", run_id="multistep") as first:
        assert first.spec.animator_name == "a"
        first_grant_id = first.lease.grant_id
    leases.begin_drain(["a"])
    assert await leases.drained(["a"], timeout=0.1)
    async with dispatcher.lease_grant(family="chat", run_id="multistep") as second:
        assert second.spec.animator_name == "b"
        assert second.lease.grant_id != first_grant_id
        assert [row.grant_id for row in leases.active()] == [second.lease.grant_id]
    assert leases.active() == []


@pytest.mark.asyncio
async def test_probe_failure_does_not_turn_invalidated_warmth_into_a_new_grant() -> None:
    adapter = ScriptedRuntimeAdapter()
    dispatcher, registry, leases, _ = _dispatch(_stone("chat"), adapter=adapter)
    adapter.observe("chat", RuntimeError("runtime probe interrupted"))

    with pytest.raises(RuntimeError, match="probe interrupted"):
        async with dispatcher.lease_grant(family="chat", run_id="interrupted-probe"):
            pytest.fail("probe failure must not reuse cached warmth")
    assert registry.get_capability_state("chat:chat:main") is None
    assert leases.active() == []
    assert adapter.connectors["chat"].model_requests == []

    # A new request must be able to observe the recovered endpoint. No operator
    # refresh or unrelated status request should be needed after invalidation.
    adapter.observe("chat", CapabilityPhase.WARM)
    async with dispatcher.lease_grant(family="chat", run_id="recovered") as grant:
        assert grant.state.phase is CapabilityPhase.WARM
    assert leases.active() == []


@pytest.mark.asyncio
async def test_next_exact_request_recovers_after_grant_issue_observed_an_error() -> None:
    adapter = ScriptedRuntimeAdapter()
    adapter.observe("chat", CapabilityPhase.WARM, CapabilityPhase.WARM, CapabilityPhase.ERROR)
    dispatcher, registry, leases, _ = _dispatch(_stone("chat"), adapter=adapter)

    with pytest.raises(CapabilityUnavailable):
        async with dispatcher.lease_grant(family="chat", capability_key="chat:chat:main", run_id="issue-error"):
            pytest.fail("fresh issue-time ERROR cannot issue a grant or request hardware")
    assert adapter.probes == ["chat", "chat", "chat"]
    state = registry.get_capability_state("chat:chat:main")
    assert state is not None
    assert state.phase is CapabilityPhase.ERROR
    assert leases.active() == []
    assert adapter.connectors["chat"].model_requests == []

    # A later exact request observes recovery itself, without an operator refresh
    # or unrelated Orchestrator transition removing the cached error first.
    adapter.observe("chat", CapabilityPhase.WARM)
    async with dispatcher.lease_grant(family="chat", capability_key="chat:chat:main", run_id="recovered") as grant:
        assert grant.state.phase is CapabilityPhase.WARM
        assert [row.grant_id for row in leases.active()] == [grant.lease.grant_id]
    assert adapter.probes == ["chat"] * 5
    assert leases.active() == []


@pytest.mark.asyncio
async def test_stale_first_candidate_does_not_silently_fallback_to_another_route() -> None:
    adapter = ScriptedRuntimeAdapter()
    adapter.observe("a", CapabilityPhase.WARM, CapabilityPhase.ERROR)
    dispatcher, _, leases, _ = _dispatch(_stone("a"), _stone("b"), adapter=adapter)

    with pytest.raises(CapabilityUnavailable):
        async with dispatcher.lease_grant(family="chat", run_id="first-candidate-failed"):
            pytest.fail("v1 selects one candidate; it has no admitted fallback policy")
    assert adapter.connectors["b"].model_requests == []
    assert leases.active() == []
