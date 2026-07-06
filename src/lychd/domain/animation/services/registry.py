from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from inspect import Parameter, signature
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

import anyio
import structlog

from lychd.domain.animation.animators import Animator
from lychd.domain.animation.capabilities import (
    ActivationResult,
    CapabilityGrant,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
    GrantLease,
)
from lychd.domain.animation.connectors import Connector, ModelConnector
from lychd.domain.animation.errors import ActivationFailed, ActivationTimeout, CapabilityUnavailable
from lychd.domain.animation.schemas import ModelInfo, PortalConfig, SoulstoneConfig
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.services.binder import AnimatorBinder, AnimatorBindingError
from lychd.domain.animation.services.loader import AnimatorLoader
from lychd.lib.http import run_sync

if TYPE_CHECKING:
    from pathlib import Path

    from pydantic_ai.models import Model
    from pydantic_ai.toolsets import AbstractToolset

    from lychd.config.runes import RuneConfig
    from lychd.domain.animation.lifecycle import AnimatorLifecycle
    from lychd.domain.animation.services.adapters.contracts import (
        PortalRuntimeFactory,
        RuntimePlan,
        SoulstoneRuntimeAdapter,
    )
    from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
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
        runes_dir: Path | None = None,
        reserved_ports: dict[str, int] | None = None,
        runtime_factories: Sequence[AnimatorFactory] | None = None,
        portal_factories: Sequence[PortalRuntimeFactory] = (),
    ) -> None:
        """Initialize with required rune schemas and runtime adapters (injected by the host).

        ``runes_dir``/``reserved_ports`` are optional overrides threaded to the
        internally-built ``AnimatorLoader`` (used by tests to load fixtures from a
        temporary directory); production composition roots pass only the injected
        schemas + adapters.
        """
        from lychd.domain.animation.services.adapters.registry import (
            RuntimeAdapterRegistry as _RuntimeAdapterRegistry,
        )

        self._loader = AnimatorLoader(
            rune_schemas=list(rune_schemas),
            runes_dir=runes_dir,
            reserved_ports=reserved_ports,
        )
        self._binder = binder or AnimatorBinder()
        self._runtime_adapters: RuntimeAdapterRegistry = _RuntimeAdapterRegistry(
            adapters=list(runtime_adapters),
            portal_factories=list(portal_factories),
        )
        self._runtime_factories: list[AnimatorFactory] = (
            list(runtime_factories) if runtime_factories is not None else [self._runtime_adapters.runtime_factory]
        )

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
                for spec in self._runtime_adapters.build_capability_specs(rune, runtime):
                    new_capabilities[spec.key] = spec
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
        self._capability_states = {}
        self._loaded = True

        # Rune parse + transmute + spec synthesis is CPU-bound and stays sync;
        # the initial capability probe is async and bridged here so the state cache
        # is warm after load. This is the ONLY sanctioned ``run_sync`` in this
        # module — every other probe/activate surface is async. Composition roots
        # that want an explicit off-loop probe can call ``await probe_all()``.
        run_sync(self._probe_all_async())

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

    async def refresh_capability_states_for_animator(self, name: str) -> list[CapabilityState]:
        """Probe and cache capability states for one resolved runtime animator."""
        self.ensure_loaded()
        animator = self._animators.get(name)
        if animator is None:
            return []

        specs = self.list_capabilities_for_animator(name)
        if not specs:
            return []

        states = await self._runtime_adapters.probe_capability_states(animator, specs)
        for state in states:
            self._capability_states[state.capability_key] = state
        return states

    async def refresh_capability_state(self, key: str) -> CapabilityState | None:
        """Re-probe and return the latest cached state for one capability key."""
        self.ensure_loaded()
        spec = self._capabilities.get(key)
        if spec is None:
            return None
        await self.refresh_capability_states_for_animator(spec.animator_name)
        return self._capability_states.get(key)

    async def _probe_all_async(self) -> None:
        """Async core: refresh capability states for every resolved animator."""
        for name in list(self._animators):
            await self.refresh_capability_states_for_animator(name)

    async def probe_all(self) -> None:
        """Refresh capability states for every animator (startup async probe)."""
        self.ensure_loaded()
        await self._probe_all_async()

    async def activate_capability(self, key: str) -> ActivationResult:
        """Request runtime-specific activation for a single capability key.

        Returns an ``ActivationResult`` (A3-U4); on acceptance the animator's
        states are re-probed so the phase reflects the activation in flight.
        """
        self.ensure_loaded()
        spec = self._capabilities.get(key)
        if spec is None:
            return ActivationResult(accepted=False, phase=CapabilityPhase.UNKNOWN, reason="unknown capability")

        animator = self._animators.get(spec.animator_name)
        if animator is None:
            return ActivationResult(accepted=False, phase=CapabilityPhase.UNKNOWN, reason="animator not registered")

        result = await self._runtime_adapters.activate_capability(animator, spec)
        if result.accepted:
            await self.refresh_capability_states_for_animator(spec.animator_name)
        return result

    async def issue_grant(
        self,
        key: str,
        *,
        holder: str,
        scope: Literal["step", "run"] = "step",
    ) -> CapabilityGrant:
        """Assemble a grant for a WARM capability.

        Mechanics only — NO warm-up driving here (that is the Dispatcher's decision
        table). Raises ``CapabilityUnavailable`` if the capability is unknown, its
        animator is not registered, or it is not observed WARM at issue time.
        """
        self.ensure_loaded()
        spec = self._capabilities.get(key)
        if spec is None:
            raise CapabilityUnavailable(key, "unknown capability")

        state = self._capability_states.get(key)
        if state is None:
            state = await self.refresh_capability_state(key)
        if state is None or state.phase is not CapabilityPhase.WARM:
            reason = f"phase={state.phase.value}" if state else "capability state unavailable"
            raise CapabilityUnavailable(key, reason)

        animator = self._animators.get(spec.animator_name)
        if animator is None:
            raise CapabilityUnavailable(key, "animator not registered")

        model = None
        if spec.family is not CapabilityFamily.TOOL_EXECUTION:
            try:
                model = self._binder.bind_model(animator, model_id=spec.model_id)
            except AnimatorBindingError:
                model = None
        toolsets = tuple(self._binder.bind_toolsets(animator))

        lease = GrantLease(grant_id=uuid4().hex, holder=holder, issued_at=datetime.now(UTC), scope=scope)
        return CapabilityGrant(
            spec=spec,
            state=state,
            lease=lease,
            generation=spec.generation_profile,
            animator=animator,
            model=model,
            toolsets=toolsets,
        )

    async def await_warm(
        self,
        key: str,
        *,
        timeout_s: float = 120.0,
        interval_s: float = 0.75,
    ) -> CapabilityState:
        """Poll ``refresh_capability_state`` until the capability phase is WARM.

        Raises ``ActivationFailed`` immediately on phase ERROR and
        ``ActivationTimeout`` (carrying the last observed state) on deadline.
        ``Link.estimated_ready_ms`` seeds an adaptive first sleep when present.
        """
        self.ensure_loaded()
        spec = self._capabilities.get(key)
        if spec is None:
            raise CapabilityUnavailable(key, "unknown capability")

        animator = self._animators.get(spec.animator_name)
        estimated_ready_ms = getattr(animator.connector.link, "estimated_ready_ms", None) if animator else None
        if estimated_ready_ms:
            await anyio.sleep(min(estimated_ready_ms / 1000.0, timeout_s))

        deadline = time.monotonic() + timeout_s
        last_state: CapabilityState | None = None
        while True:
            state = await self.refresh_capability_state(key)
            if state is None:
                raise CapabilityUnavailable(key, "capability state unavailable")
            last_state = state
            if state.phase is CapabilityPhase.WARM:
                return state
            if state.phase is CapabilityPhase.ERROR:
                raise ActivationFailed(key, reason=state.reason)
            if time.monotonic() >= deadline:
                raise ActivationTimeout(key, last_state)
            await anyio.sleep(interval_s)

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

    async def inspect_lifecycle(self, name: str) -> AnimatorLifecycle | None:
        """Inspect runtime lifecycle for an animator via its adapter control plane.

        Generic (spec §5): the domain no longer imports a concrete runtime nor
        branches on ``connector.kind``; it delegates to the optional
        ``AnimatorControlPlane`` an adapter may expose.
        """
        animator = self.get_runtime(name)
        if animator is None:
            return None

        adapter = self._runtime_adapters.adapter_for_animator(animator)
        if adapter is None:
            return None

        control = adapter.control_plane(animator)
        if control is None:
            return None
        return await control.inspect_animator(animator)
