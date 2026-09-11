"""Real capability coordination with inert model, adapter, and actuator effects."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from pydantic_ai.models import Model
from pydantic_ai.models.test import TestModel

from lychd.config import QuadletConfig
from lychd.config.settings.orchestration import SwitchingSettings
from lychd.domain.animation.animators import RuntimeAnimator
from lychd.domain.animation.capabilities import (
    ActivationResult,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
    SourceKind,
)
from lychd.domain.animation.connectors import Connector, ModelConnector
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import CapabilityFamily, GenericSoulstoneConfig, SoulstoneConfig
from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.animation.services.adapters.contracts import RuntimePlan
from lychd.domain.animation.services.adapters.surfaces import SoulstoneAnimator
from lychd.domain.animation.services.declarations import AnimatorDeclarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.leases import AnimatorAdmission, LeaseLedger
from lychd.domain.orchestration.actuator import TransitionIntent
from lychd.domain.orchestration.arbiter import TransitionArbiter
from lychd.domain.orchestration.broker import GhoulBroker
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.policies import resolve_switch_policy


class InertModelConnector(Connector, ModelConnector):
    @property
    def link(self) -> Link:
        return Link(up=False)

    @property
    def base_url(self) -> str:
        return ""

    def get_model(self, *, model_id: str | None = None) -> Model:
        _ = model_id
        return TestModel()


class InertRuntimeAdapter:
    runtime = "scenario"

    def __init__(self, models: dict[str, tuple[str, ...]], active: set[str]) -> None:
        self.models = models
        self.active = set(active)
        self.loaded = {name: values[0] for name, values in models.items()}
        self.probes: list[str] = []
        self.activations: list[str] = []
        self.before_probe: Callable[[str], Awaitable[None]] | None = None

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        _ = soulstone
        return RuntimePlan()

    def build_runtime(self, soulstone: SoulstoneConfig) -> RuntimeAnimator:
        return SoulstoneAnimator(rune=soulstone, connector=InertModelConnector())

    def build_capability_specs(self, animator: RuntimeAnimator) -> list[CapabilitySpec]:
        soulstone = animator.rune
        assert isinstance(soulstone, SoulstoneConfig)
        return [
            CapabilitySpec(
                key=f"{soulstone.name}:chat:{model}",
                animator_name=soulstone.name,
                runtime=self.runtime,
                source_kind=SourceKind.SOULSTONE,
                family=CapabilityFamily.CHAT,
                model_id=model,
                is_dynamic=len(self.models[soulstone.name]) > 1,
                concurrency=soulstone.concurrency,
            )
            for model in self.models[soulstone.name]
        ]

    async def probe_capability_states(
        self,
        animator: RuntimeAnimator,
        specs: list[CapabilitySpec],
    ) -> list[CapabilityState]:
        self.probes.append(animator.name)
        if self.before_probe is not None:
            await self.before_probe(animator.name)
        return [
            CapabilityState(
                capability_key=spec.key,
                phase=(
                    CapabilityPhase.COLD
                    if animator.name not in self.active
                    else CapabilityPhase.WARM
                    if self.loaded[animator.name] == spec.model_id
                    else CapabilityPhase.ACTIVATABLE
                ),
                health="ok" if animator.name in self.active else "down",
            )
            for spec in specs
        ]

    async def activate_capability(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> ActivationResult:
        self.activations.append(spec.key)
        self.loaded[animator.name] = spec.model_id
        return ActivationResult(accepted=True)


class InertRuntimeActuator:
    def __init__(self, world: InertRuntimeAdapter, leases: LeaseLedger, broker: GhoulBroker) -> None:
        self.world = world
        self.leases = leases
        self.broker = broker
        self.intents: list[TransitionIntent] = []
        self.before_apply: Callable[[TransitionIntent], Awaitable[None]] | None = None

    async def apply(self, intent: TransitionIntent) -> None:
        assert self.broker.paused
        for name in (*intent.evict_animators, *intent.launch_animators):
            assert self.leases.admission(name) is AnimatorAdmission.DRAINING
            assert self.leases.active(animator_name=name) == []
        assert set(intent.expected_active_animators) == self.world.active
        self.intents.append(intent)
        if self.before_apply is not None:
            await self.before_apply(intent)
        self.world.active.difference_update(intent.evict_animators)
        self.world.active.update(intent.launch_animators)


@dataclass
class CapabilityScenario:
    world: InertRuntimeAdapter
    registry: AnimatorRegistry
    leases: LeaseLedger
    broker: GhoulBroker
    actuator: InertRuntimeActuator
    manager: OrchestratorManager
    dispatcher: Dispatcher


def build_capability_scenario(
    *,
    models: dict[str, tuple[str, ...]] | None = None,
    active: set[str] | None = None,
    coexist: tuple[str, ...] = (),
    conflict_domains: dict[str, tuple[str, ...]] | None = None,
    policy: str = "declared-conflicts",
) -> CapabilityScenario:
    models = models or {"a": ("a-model",), "b": ("b-model",)}
    world = InertRuntimeAdapter(models, active or set())
    stones = tuple(
        GenericSoulstoneConfig(
            name=name,
            runtime=world.runtime,
            quadlet=QuadletConfig(image="invalid.example/scenario:inert"),
            concurrency=ConcurrencyIntent(
                conflict_domains=(conflict_domains or {}).get(name, () if name in coexist else ("gpu-0",))
            ),
        )
        for name in models
    )
    registry = AnimatorRegistry(
        declarations=AnimatorDeclarations(soulstones=stones, portals=()),
        runtime_adapters=[world],
    )
    registry.load()
    world.probes.clear()
    leases = LeaseLedger()
    broker = GhoulBroker()
    actuator = InertRuntimeActuator(world, leases, broker)
    switching = SwitchingSettings(drain_timeout_s=0.2, warmup_timeout_s=0.2, planning_timeout_s=0.06)
    manager = OrchestratorManager(
        broker,
        registry,
        leases=leases,
        policy=resolve_switch_policy(policy),
        arbiter=TransitionArbiter(),
        actuator=actuator,
        switching=switching,
    )
    return CapabilityScenario(world, registry, leases, broker, actuator, manager, Dispatcher(registry, leases=leases))
