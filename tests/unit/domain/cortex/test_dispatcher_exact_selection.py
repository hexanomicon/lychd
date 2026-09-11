"""Exact selection retains the real registry's readiness and lease boundaries.

Runtime observations and models are inert; these cases never launch a service,
load model weights, or contact an endpoint.
"""

from __future__ import annotations

import asyncio
from collections import deque

import pytest

from lychd.domain.animation.animators import RuntimeAnimator
from lychd.domain.animation.capabilities import CapabilityPhase, CapabilitySpec, CapabilityState
from lychd.domain.animation.errors import CapabilityUnavailable, HardwareTransitionRequired
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import OpenAIPortalConfig, PortalModelConfig
from lychd.domain.animation.services.adapters.contracts import PortalDefinition
from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector
from lychd.domain.animation.services.declarations import AnimatorDeclarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.leases import LeaseLedger
from lychd.extensions.builtin.animator.register import build_openai_portal
from tests.capability_workflows import CapabilityScenario, build_capability_scenario


@pytest.fixture
def scenario() -> CapabilityScenario:
    return build_capability_scenario(models={"a": ("shared",), "z": ("shared",)}, active={"a", "z"})


def _observe(
    scenario: CapabilityScenario,
    monkeypatch: pytest.MonkeyPatch,
    *phases: CapabilityPhase,
) -> None:
    observations = deque(phases)

    async def probe(animator: RuntimeAnimator, specs: list[CapabilitySpec]) -> list[CapabilityState]:
        scenario.world.probes.append(animator.name)
        phase = observations[0]
        if len(observations) > 1:
            observations.popleft()
        return [CapabilityState(capability_key=spec.key, phase=phase) for spec in specs]

    monkeypatch.setattr(scenario.world, "probe_capability_states", probe)


@pytest.mark.asyncio
async def test_exact_key_selects_animator_despite_duplicate_model_alias(scenario: CapabilityScenario) -> None:
    async with scenario.dispatcher.lease_grant(family="chat", model_name="shared", run_id="pool") as pooled:
        assert pooled.spec.key == "a:chat:shared"

    scenario.world.probes.clear()
    async with scenario.dispatcher.lease_grant(
        family="chat", model_name="shared", capability_key="z:chat:shared", run_id="exact"
    ) as exact:
        assert exact.spec.key == "z:chat:shared"
        assert [row.capability_key for row in scenario.leases.active()] == ["z:chat:shared"]
    assert scenario.world.probes == ["z", "z"]
    assert scenario.leases.active() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["missing:chat:shared", "z:chat:missing", "", " z:chat:shared "])
async def test_unknown_exact_key_never_falls_back_to_a_matching_alias(scenario: CapabilityScenario, key: str) -> None:
    with pytest.raises(CapabilityUnavailable) as error:
        async with scenario.dispatcher.lease_grant(
            family="chat", model_name="shared", capability_key=key, run_id="missing"
        ):
            pytest.fail("an exact key must identify one declared capability")
    assert error.value.capability_key == key
    assert scenario.world.probes == []
    assert scenario.leases.active() == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("family", "model_name", "modalities", "requires_tools"),
    [
        ("stt", None, (), False),
        ("chat", "different", (), False),
        ("chat", None, ("image",), False),
        ("chat", None, (), True),
    ],
    ids=["family", "model", "modalities", "tools"],
)
async def test_exact_key_cannot_bypass_other_demand_constraints(
    scenario: CapabilityScenario,
    family: str,
    model_name: str | None,
    modalities: tuple[str, ...],
    *,
    requires_tools: bool,
) -> None:
    with pytest.raises(CapabilityUnavailable) as error:
        async with scenario.dispatcher.lease_grant(
            family=family,
            model_name=model_name,
            capability_key="z:chat:shared",
            require_modalities=modalities,
            requires_tools=requires_tools,
            run_id="incompatible",
        ):
            pytest.fail("pinning a capability does not establish demand compatibility")
    assert error.value.capability_key == "z:chat:shared"
    assert scenario.world.probes == []
    assert scenario.leases.active() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", [CapabilityPhase.COLD, CapabilityPhase.ACTIVATABLE, CapabilityPhase.WARMING])
@pytest.mark.parametrize("at_issue", [False, True], ids=["preflight", "issue"])
async def test_exact_unready_capability_parks_without_substituting_a_warm_alias(
    scenario: CapabilityScenario,
    monkeypatch: pytest.MonkeyPatch,
    phase: CapabilityPhase,
    *,
    at_issue: bool,
) -> None:
    _observe(scenario, monkeypatch, *([CapabilityPhase.WARM, phase] if at_issue else [phase]))

    with pytest.raises(HardwareTransitionRequired) as error:
        async with scenario.dispatcher.lease_grant(family="chat", capability_key="z:chat:shared", run_id="unready"):
            pytest.fail("an exact capability waits for its own readiness")
    assert error.value.capability_key == "z:chat:shared"
    assert scenario.world.probes == ["z"] * (2 if at_issue else 1)
    assert scenario.world.activations == []
    assert scenario.leases.active() == []

    _observe(scenario, monkeypatch, CapabilityPhase.WARM)
    async with scenario.dispatcher.lease_grant(
        family="chat", capability_key="z:chat:shared", run_id="ready-again"
    ) as grant:
        assert grant.spec.key == "z:chat:shared"
    assert scenario.leases.active() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", [CapabilityPhase.UNKNOWN, CapabilityPhase.ERROR])
async def test_exact_unresolved_issue_is_unavailable_without_fallback_or_lease(
    scenario: CapabilityScenario, monkeypatch: pytest.MonkeyPatch, phase: CapabilityPhase
) -> None:
    _observe(scenario, monkeypatch, CapabilityPhase.WARM, phase)
    with pytest.raises(CapabilityUnavailable) as error:
        async with scenario.dispatcher.lease_grant(
            family="chat", capability_key="z:chat:shared", run_id="failed-issue"
        ):
            pytest.fail("a failed exact route cannot dispatch another model alias")
    assert error.value.capability_key == "z:chat:shared"
    assert scenario.world.probes == ["z", "z"]
    assert scenario.leases.active() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("fresh_phase", [CapabilityPhase.WARM, CapabilityPhase.ERROR])
async def test_exact_cached_error_refreshes_only_the_pinned_route(
    scenario: CapabilityScenario, monkeypatch: pytest.MonkeyPatch, fresh_phase: CapabilityPhase
) -> None:
    _observe(scenario, monkeypatch, CapabilityPhase.ERROR)
    await scenario.registry.refresh_capability_state("z:chat:shared")
    scenario.world.probes.clear()
    _observe(scenario, monkeypatch, fresh_phase)

    if fresh_phase is CapabilityPhase.WARM:
        async with scenario.dispatcher.lease_grant(
            family="chat", model_name="shared", capability_key="z:chat:shared", run_id="recovered-exact"
        ) as grant:
            assert grant.spec.key == "z:chat:shared"
            assert [row.capability_key for row in scenario.leases.active()] == ["z:chat:shared"]
    else:
        with pytest.raises(CapabilityUnavailable) as error:
            async with scenario.dispatcher.lease_grant(
                family="chat", model_name="shared", capability_key="z:chat:shared", run_id="still-error"
            ):
                pytest.fail("a fresh exact ERROR cannot bypass readiness or substitute the warm alias")
        assert error.value.capability_key == "z:chat:shared"
    assert scenario.world.probes == ["z"] * (2 if fresh_phase is CapabilityPhase.WARM else 1)
    assert scenario.world.activations == []
    assert scenario.actuator.intents == []
    assert scenario.leases.active() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("during_issue", [False, True], ids=["already-draining", "drain-race"])
async def test_exact_draining_capability_parks_and_never_uses_an_open_alias(
    scenario: CapabilityScenario, *, during_issue: bool
) -> None:
    if during_issue:

        async def close_gate(name: str) -> None:
            if len(scenario.world.probes) == 2:
                scenario.leases.begin_drain([name])

        scenario.world.before_probe = close_gate
    else:
        scenario.leases.begin_drain(["z"])

    with pytest.raises(HardwareTransitionRequired) as error:
        async with scenario.dispatcher.lease_grant(family="chat", capability_key="z:chat:shared", run_id="draining"):
            pytest.fail("the chosen runtime's admission gate governs the exact binding")
    assert error.value.capability_key == "z:chat:shared"
    assert scenario.world.probes == (["z", "z"] if during_issue else [])
    assert scenario.leases.active() == []


@pytest.mark.asyncio
async def test_exact_grant_releases_on_consumer_cancellation(scenario: CapabilityScenario) -> None:
    async def consume() -> None:
        async with scenario.dispatcher.lease_grant(family="chat", capability_key="z:chat:shared", run_id="cancelled"):
            assert len(scenario.leases.active()) == 1
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await consume()
    assert scenario.leases.active() == []


@pytest.mark.asyncio
async def test_exact_warm_portal_remains_quarantined_without_an_execution_probe() -> None:
    probes: list[str] = []

    async def probe(animator: RuntimeAnimator) -> None:
        probes.append(animator.name)
        assert isinstance(animator.connector, OpenAICompatibleConnector)
        animator.connector.set_link(Link(up=True))

    portal = OpenAIPortalConfig(name="remote", models=(PortalModelConfig(id="shared"),), probe=True)
    registry = AnimatorRegistry(
        declarations=AnimatorDeclarations(soulstones=(), portals=(portal,)),
        runtime_adapters=[],
        portal_definitions=[PortalDefinition(rune_schema=OpenAIPortalConfig, factory=build_openai_portal, probe=probe)],
    )
    registry.load()
    state = registry.get_capability_state("remote:chat:shared")
    assert state is not None
    assert state.phase is CapabilityPhase.WARM
    leases = LeaseLedger()
    dispatcher = Dispatcher(registry, leases=leases)

    with pytest.raises(CapabilityUnavailable, match="portal egress admission") as error:
        async with dispatcher.lease_grant(family="chat", capability_key="remote:chat:shared", run_id="portal"):
            pytest.fail("an exact remote binding is not an egress authority")
    assert error.value.capability_key == "remote:chat:shared"
    assert probes == ["remote"]
    assert leases.active() == []
