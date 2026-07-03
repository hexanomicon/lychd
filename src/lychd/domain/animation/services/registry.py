from __future__ import annotations

from collections.abc import Callable, Sequence
from inspect import Parameter, signature
from typing import TYPE_CHECKING

import structlog

from lychd.domain.animation.animators import Animator
from lychd.domain.animation.capabilities import CapabilitySpec, CapabilityState
from lychd.domain.animation.connectors import Connector, ModelConnector
from lychd.domain.animation.schemas import ModelInfo, PortalConfig, SoulstoneConfig
from lychd.domain.animation.services.binder import AnimatorBinder
from lychd.domain.animation.services.loader import AnimatorLoader

if TYPE_CHECKING:
    from pydantic_ai.models import Model
    from pydantic_ai.toolsets import AbstractToolset

    from lychd.config.runes import RuneConfig
    from lychd.domain.animation.services.adapters.contracts import RuntimePlan, SoulstoneRuntimeAdapter
    from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
    from lychd.extensions.builtin.animator.llamacpp import LlamaCppControlPlane, LlamaCppLifecycle
    from lychd.system.schemas import QuadletContainer


type RuntimeAnimator = Animator[Connector, SoulstoneConfig | PortalConfig]
type AnimatorConfigDeclaration = SoulstoneConfig | PortalConfig
type AnimatorFactory = Callable[..., RuntimeAnimator | None]

logger = structlog.get_logger()
_RUNTIME_FACTORY_WITH_QUADLET_ARITY = 2


class AnimatorRegistry:
    """Registry for animation Runes and resolved runtime animators.

    Stores two distinct layers:
    - rune declarations (``SoulstoneConfig`` / ``PortalConfig``)
    - resolved runtime animators (``Animator`` handles with connectors/links)

    Runtime animator creation is delegated to factories. By default, the registry
    wires in ``RuntimeAdapterRegistry.runtime_factory`` so built-in Soulstone and
    portal runtimes resolve without extra setup.
    """

    def __init__(
        self,
        *,
        rune_schemas: Sequence[type[RuneConfig]],
        runtime_adapters: Sequence[SoulstoneRuntimeAdapter],
        binder: AnimatorBinder | None = None,
    ) -> None:
        """Initialize with required rune schemas and runtime adapters (injected by the host)."""
        from lychd.domain.animation.services.adapters.registry import (
            RuntimeAdapterRegistry as _RuntimeAdapterRegistry,
        )

        self._loader = AnimatorLoader(rune_schemas=list(rune_schemas))
        self._binder = binder or AnimatorBinder()
        self._runtime_adapters: RuntimeAdapterRegistry = _RuntimeAdapterRegistry(adapters=list(runtime_adapters))
        self._runtime_factories: list[AnimatorFactory] = [self._runtime_adapters.runtime_factory]
        self._llamacpp_control: LlamaCppControlPlane | None = None

        self._soulstones: dict[str, SoulstoneConfig] = {}
        self._portals: dict[str, PortalConfig] = {}
        self._groups: dict[str, list[SoulstoneConfig]] = {}
        self._animators: dict[str, RuntimeAnimator] = {}
        self._capabilities: dict[str, CapabilitySpec] = {}
        self._capability_states: dict[str, CapabilityState] = {}
        self._loaded = False

    def register_runtime_factory(self, factory: AnimatorFactory) -> None:
        """Register a runtime animator factory used during `load()`."""
        self._runtime_factories.append(factory)

    def register_runtime(self, animator: RuntimeAnimator) -> None:
        """Register/replace a runtime animator handle directly by id."""
        self._animators[animator.id] = animator

    def load(self) -> None:
        """Load Runes and build runtime animators via registered factories."""
        raw_soulstones, raw_portals = self._loader.load_all()

        new_soulstones = {stone.name: stone for stone in raw_soulstones}
        new_portals = {portal.name: portal for portal in raw_portals}
        new_groups: dict[str, list[SoulstoneConfig]] = {}
        for stone in raw_soulstones:
            for group in stone.groups:
                new_groups.setdefault(group, []).append(stone)

        quadlets = self._transmute_soulstone_quadlets(raw_soulstones, raw_portals)
        new_animators: dict[str, RuntimeAnimator] = {}
        new_capabilities: dict[str, CapabilitySpec] = {}
        new_capability_states: dict[str, CapabilityState] = {}
        for rune in [*raw_soulstones, *raw_portals]:
            resolved = False
            for factory in self._runtime_factories:
                runtime = self._call_runtime_factory(
                    factory,
                    rune,
                    quadlets.get(rune.name) if isinstance(rune, SoulstoneConfig) else None,
                )
                if runtime is None:
                    continue
                new_animators[runtime.id] = runtime
                specs = self._runtime_adapters.build_capability_specs(rune, runtime)
                for spec in specs:
                    new_capabilities[spec.key] = spec
                for state in self._runtime_adapters.probe_capability_states(runtime, specs):
                    new_capability_states[state.capability_key] = state
                resolved = True
                break
            if not resolved:
                logger.warning(
                    "runtime_unresolved",
                    rune_name=rune.name,
                    rune_type=type(rune).__name__,
                )

        self._soulstones = new_soulstones
        self._portals = new_portals
        self._groups = new_groups
        self._animators = new_animators
        self._capabilities = new_capabilities
        self._capability_states = new_capability_states
        self._loaded = True

        logger.info(
            "registry_loaded",
            soulstones=len(self._soulstones),
            portals=len(self._portals),
            groups=list(self._groups.keys()),
            runtime_animators=len(self._animators),
            capabilities=len(self._capabilities),
        )

    def _transmute_soulstone_quadlets(
        self,
        soulstones: list[SoulstoneConfig],
        portals: list[PortalConfig],
    ) -> dict[str, QuadletContainer]:
        """Transmute loaded Soulstones into generated Quadlet manifests keyed by Soulstone name."""
        if not soulstones:
            return {}

        from lychd.domain.animation.transmute import Transmuter
        from lychd.system.schemas import QuadletContainer

        manifests = Transmuter(runtime_planner=self._runtime_adapters).transmute_all(soulstones, portals=portals)
        soulstone_names = {stone.name for stone in soulstones}
        quadlets: dict[str, QuadletContainer] = {}
        for manifest in manifests:
            if not isinstance(manifest, QuadletContainer):
                continue
            if not manifest.container_name.startswith("lychd-"):
                continue
            soulstone_name = manifest.container_name.removeprefix("lychd-")
            if soulstone_name in soulstone_names:
                quadlets[soulstone_name] = manifest
        return quadlets

    def _call_runtime_factory(
        self,
        factory: AnimatorFactory,
        rune: AnimatorConfigDeclaration,
        quadlet: QuadletContainer | None,
    ) -> RuntimeAnimator | None:
        """Call runtime factories with Quadlet hydration when their signature supports it."""
        parameters = list(signature(factory).parameters.values())
        accepts_varargs = any(parameter.kind == Parameter.VAR_POSITIONAL for parameter in parameters)
        positional_parameters = [
            parameter
            for parameter in parameters
            if parameter.kind in {Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD}
        ]
        if accepts_varargs or len(positional_parameters) >= _RUNTIME_FACTORY_WITH_QUADLET_ARITY:
            return factory(rune, quadlet)
        return factory(rune)

    def ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def get_runtime(self, name: str) -> RuntimeAnimator | None:
        self.ensure_loaded()
        return self._animators.get(name)

    def get(self, name: str) -> RuntimeAnimator | None:
        return self.get_runtime(name)

    def get_soulstone_rune(self, name: str) -> SoulstoneConfig | None:
        self.ensure_loaded()
        return self._soulstones.get(name)

    def get_portal_rune(self, name: str) -> PortalConfig | None:
        self.ensure_loaded()
        return self._portals.get(name)

    def get_group(self, group_name: str) -> Sequence[SoulstoneConfig]:
        self.ensure_loaded()
        return self._groups.get(group_name, [])

    def list_runtime_animators(self) -> list[RuntimeAnimator]:
        self.ensure_loaded()
        return list(self._animators.values())

    def list_runes(self) -> list[AnimatorConfigDeclaration]:
        self.ensure_loaded()
        return [*self._soulstones.values(), *self._portals.values()]

    def list_models(self, name: str) -> Sequence[ModelInfo]:
        animator = self.get_runtime(name)
        if animator is None:
            return ()
        connector = animator.connector
        if not isinstance(connector, ModelConnector):
            return ()
        return tuple(connector.list_models())

    def is_ready(self, name: str) -> bool:
        animator = self.get_runtime(name)
        if animator is None:
            return False
        return animator.connector.link.up

    def bind_model(self, name: str, *, model_id: str | None = None) -> Model | None:
        animator = self.get_runtime(name)
        if animator is None:
            return None
        return self._binder.bind_model(animator, model_id=model_id)

    def list_capabilities(self) -> list[CapabilitySpec]:
        """List synthesized capabilities across all loaded animators."""
        self.ensure_loaded()
        return list(self._capabilities.values())

    def list_capabilities_for_animator(self, name: str) -> list[CapabilitySpec]:
        """List synthesized capabilities for a specific animator."""
        self.ensure_loaded()
        return [spec for spec in self._capabilities.values() if spec.animator_name == name]

    def get_capability(self, key: str) -> CapabilitySpec | None:
        """Return a capability spec by stable capability key."""
        self.ensure_loaded()
        return self._capabilities.get(key)

    def get_capability_state(self, key: str) -> CapabilityState | None:
        """Return the last observed capability state by stable capability key."""
        self.ensure_loaded()
        return self._capability_states.get(key)

    def list_capability_states(self) -> list[CapabilityState]:
        """List the last observed capability states across all loaded animators."""
        self.ensure_loaded()
        return list(self._capability_states.values())

    def list_capability_states_for_animator(self, name: str) -> list[CapabilityState]:
        """List the last observed capability states for a specific animator."""
        self.ensure_loaded()
        keys = {spec.key for spec in self.list_capabilities_for_animator(name)}
        return [state for state in self._capability_states.values() if state.capability_key in keys]

    def refresh_capability_states_for_animator(self, name: str) -> list[CapabilityState]:
        """Re-probe and cache capability states for one resolved runtime animator."""
        self.ensure_loaded()
        animator = self._animators.get(name)
        if animator is None:
            return []

        specs = self.list_capabilities_for_animator(name)
        if not specs:
            return []

        states = self._runtime_adapters.probe_capability_states(animator, specs)
        for state in states:
            self._capability_states[state.capability_key] = state
        return states

    def refresh_capability_state(self, key: str) -> CapabilityState | None:
        """Re-probe and return the latest cached state for one capability key."""
        self.ensure_loaded()
        spec = self._capabilities.get(key)
        if spec is None:
            return None

        self.refresh_capability_states_for_animator(spec.animator_name)
        return self._capability_states.get(key)

    def activate_capability(self, key: str) -> bool:
        """Request runtime-specific activation for a single capability key."""
        self.ensure_loaded()
        spec = self._capabilities.get(key)
        if spec is None:
            return False

        animator = self._animators.get(spec.animator_name)
        if animator is None:
            return False

        activated = self._runtime_adapters.activate_capability(animator, spec)
        if not activated:
            return False

        animator.connector.link.up = True
        self.refresh_capability_states_for_animator(spec.animator_name)
        return True

    def list_persistent_residents(self) -> list[CapabilitySpec]:
        """List capabilities declared on persistent-resident animators."""
        self.ensure_loaded()
        return [spec for spec in self._capabilities.values() if spec.concurrency.persistent_resident]

    def bind_toolsets(self, name: str) -> Sequence[AbstractToolset]:
        animator = self.get_runtime(name)
        if animator is None:
            return ()
        return self._binder.bind_toolsets(animator)

    def bind_toolset(self, name: str) -> AbstractToolset | None:
        animator = self.get_runtime(name)
        if animator is None:
            return None
        return self._binder.bind_toolset(animator)

    def prepare(self, name: str) -> RuntimePlan | None:
        """Return a container runtime plan for a Soulstone rune, if present."""
        soulstone = self.get_soulstone_rune(name)
        if soulstone is None:
            return None
        return self._runtime_adapters.plan(soulstone)

    def inspect_lifecycle(self, name: str) -> LlamaCppLifecycle | None:
        """Inspect llama.cpp lifecycle for a runtime animator when applicable."""
        animator = self.get_runtime(name)
        if animator is None:
            return None

        if getattr(animator.connector, "kind", None) != "llamacpp":
            return None

        control = self._get_llamacpp_control()
        return control.inspect_animator(animator)

    def _get_llamacpp_control(self) -> LlamaCppControlPlane:
        if self._llamacpp_control is None:
            from lychd.extensions.builtin.animator.llamacpp import LlamaCppControlPlane

            self._llamacpp_control = LlamaCppControlPlane()
        return self._llamacpp_control
