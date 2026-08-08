from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Collection, Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

import anyio
import structlog

from lychd.domain.animation.animators import RuntimeAnimator
from lychd.domain.animation.capabilities import (
    ActivationResult,
    CapabilityGrant,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
    GrantLease,
    SourceKind,
)
from lychd.domain.animation.conflicts import require_soulstone_capability_coverage
from lychd.domain.animation.connectors import ModelConnector
from lychd.domain.animation.errors import ActivationFailed, ActivationTimeout, CapabilityUnavailable
from lychd.domain.animation.schemas import CapabilityFamily, ModelInfo, PortalConfig, SoulstoneConfig
from lychd.domain.animation.services.binder import AnimatorBinder, AnimatorBindingError
from lychd.lib.asyncio import complete_under_cancellation
from lychd.lib.http import run_sync

if TYPE_CHECKING:
    from pydantic_ai.models import Model
    from pydantic_ai.toolsets import AbstractToolset

    from lychd.domain.animation.lifecycle import AnimatorLifecycle
    from lychd.domain.animation.services.adapters.contracts import (
        PortalDefinition,
        SoulstoneRuntimeAdapter,
    )
    from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
    from lychd.domain.animation.services.declarations import AnimatorDeclarations
type AnimatorConfigDeclaration = SoulstoneConfig | PortalConfig
type AnimatorFactory = Callable[[AnimatorConfigDeclaration], RuntimeAnimator | None]

logger = structlog.get_logger()
_ACTIVATION_CLEANUP_TIMEOUT_SECONDS = 5.0


class _ProbeContractError(ValueError):
    """Malformed adapter result plus the capability observations it invalidates."""

    def __init__(self, message: str, *, requested_keys: set[str]) -> None:
        super().__init__(message)
        self.requested_keys = frozenset(requested_keys)


def _declaration_provenance(declaration: AnimatorConfigDeclaration) -> str:
    source_file = str(declaration.source_file) if declaration.source_file is not None else None
    return f"{type(declaration).__name__}(name={declaration.name!r}, source_file={source_file!r})"


def _runtime_provenance(runtime: RuntimeAnimator) -> str:
    return f"{type(runtime).__name__} from {_declaration_provenance(runtime.rune)}"


def _capability_provenance(spec: CapabilitySpec, runtime: RuntimeAnimator) -> str:
    return (
        f"{type(spec).__name__}(animator_name={spec.animator_name!r}, runtime={spec.runtime!r}, "
        f"source_kind={spec.source_kind.value!r}, family={spec.family.value!r}, model_id={spec.model_id!r}) "
        f"from {_runtime_provenance(runtime)}"
    )


def _canonical_capability_owner(
    declaration: AnimatorConfigDeclaration,
) -> tuple[str, SourceKind]:
    if isinstance(declaration, SoulstoneConfig):
        return declaration.runtime_name, SourceKind.SOULSTONE
    return f"portal:{declaration.provider_name.strip().lower()}", SourceKind.PORTAL


def _require_runtime_identity(
    declaration: AnimatorConfigDeclaration,
    runtime: RuntimeAnimator,
) -> None:
    """Reject a factory result that does not preserve its exact Rune and identity."""
    if runtime.rune is not declaration:
        msg = (
            f"Runtime factory for {_declaration_provenance(declaration)} returned "
            f"{_runtime_provenance(runtime)}, which does not retain the exact input Rune."
        )
        raise ValueError(msg)
    if runtime.name != declaration.name or runtime.id != declaration.name:
        msg = (
            f"Runtime for {_declaration_provenance(declaration)} must use canonical name/id "
            f"{declaration.name!r}; received name={runtime.name!r}, id={runtime.id!r}."
        )
        raise ValueError(msg)


def _require_capability_identity(
    declaration: AnimatorConfigDeclaration,
    runtime: RuntimeAnimator,
    spec: CapabilitySpec,
) -> None:
    """Reject a capability that claims identity outside its exact runtime owner."""
    expected_runtime, expected_source = _canonical_capability_owner(declaration)
    expected_key = f"{runtime.id}:{spec.family.value}:{spec.model_id}"
    mismatches: list[str] = []
    if spec.animator_name != runtime.id:
        mismatches.append(f"animator_name={spec.animator_name!r}, expected {runtime.id!r}")
    if spec.runtime != expected_runtime:
        mismatches.append(f"runtime={spec.runtime!r}, expected {expected_runtime!r}")
    if spec.source_kind is not expected_source:
        mismatches.append(f"source_kind={spec.source_kind.value!r}, expected {expected_source.value!r}")
    if spec.key != expected_key:
        mismatches.append(f"key={spec.key!r}, expected {expected_key!r}")
    if mismatches:
        msg = f"Capability ownership mismatch for {_capability_provenance(spec, runtime)}: {'; '.join(mismatches)}."
        raise ValueError(msg)


class AnimatorRegistry:
    """Runtime registry over one injected Animator declaration snapshot.

    Stores two distinct layers:
    - hydrated declarations (``SoulstoneConfig`` / ``PortalConfig``)
    - resolved runtime animators (``Animator`` handles with connectors/links)

    Rune discovery and declaration collision policy belong to the declaration
    compiler. Hydration rejects duplicate runtime and capability keys. Runtime
    creation is delegated to factories; the built-in adapter registry supplies
    the default Soulstone and Portal factory.
    """

    def __init__(
        self,
        *,
        declarations: AnimatorDeclarations,
        runtime_adapters: Sequence[SoulstoneRuntimeAdapter],
        binder: AnimatorBinder | None = None,
        runtime_factories: Sequence[AnimatorFactory] | None = None,
        portal_definitions: Sequence[PortalDefinition] = (),
    ) -> None:
        """Initialize from one compiled declaration snapshot.

        Filesystem discovery, extension assembly, port collision policy, and
        declaration hydration stay outside the live registry. Production
        composition injects the same snapshot used by bind and status.
        """
        from lychd.domain.animation.services.adapters.registry import (
            RuntimeAdapterRegistry as _RuntimeAdapterRegistry,
        )

        self._declarations = declarations
        self._binder = binder or AnimatorBinder()
        self._runtime_adapters: RuntimeAdapterRegistry = _RuntimeAdapterRegistry(
            adapters=list(runtime_adapters),
            portal_definitions=list(portal_definitions),
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
        self._probe_lock = asyncio.Lock()
        self._loaded = False

    def load(self) -> None:
        """Build runtime animators from the injected declaration snapshot."""
        raw_soulstones = list(self._declarations.soulstones)
        raw_portals = list(self._declarations.portals)

        new_soulstones = {stone.name: stone for stone in raw_soulstones}
        new_portals = {portal.name: portal for portal in raw_portals}
        new_groups: dict[str, list[SoulstoneConfig]] = {}
        for stone in raw_soulstones:
            for group in stone.groups:
                new_groups.setdefault(group, []).append(stone)

        new_animators: dict[str, RuntimeAnimator] = {}
        new_capabilities: dict[str, CapabilitySpec] = {}
        new_capability_runtimes: dict[str, RuntimeAnimator] = {}
        for rune in [*raw_soulstones, *raw_portals]:
            resolved = False
            for factory in self._runtime_factories:
                runtime = factory(rune)
                if runtime is None:
                    continue
                _require_runtime_identity(rune, runtime)
                existing_runtime = new_animators.get(runtime.id)
                if existing_runtime is not None:
                    msg = (
                        f"Duplicate runtime key {runtime.id!r}: existing contributor "
                        f"{_runtime_provenance(existing_runtime)} conflicts with "
                        f"{_runtime_provenance(runtime)}."
                    )
                    raise ValueError(msg)
                new_animators[runtime.id] = runtime
                for spec in self._runtime_adapters.build_capability_specs(rune, runtime):
                    _require_capability_identity(rune, runtime, spec)
                    canonical_spec = spec.model_copy(deep=True)
                    existing_spec = new_capabilities.get(canonical_spec.key)
                    if existing_spec is not None:
                        msg = (
                            f"Duplicate capability key {canonical_spec.key!r}: existing contributor "
                            f"{_capability_provenance(existing_spec, new_capability_runtimes[canonical_spec.key])} "
                            f"conflicts with {_capability_provenance(canonical_spec, runtime)}."
                        )
                        raise ValueError(msg)
                    new_capabilities[canonical_spec.key] = canonical_spec
                    new_capability_runtimes[canonical_spec.key] = runtime
                resolved = True
                break
            if not resolved:
                logger.warning(
                    "runtime_unresolved",
                    rune_name=rune.name,
                    rune_type=rune.__class__.__name__,
                )

        require_soulstone_capability_coverage(
            raw_soulstones,
            capability_animator_names=(
                spec.animator_name for spec in new_capabilities.values() if spec.source_kind is SourceKind.SOULSTONE
            ),
        )

        # Probe the detached snapshot before publishing any new runtime or state.
        # A failed first load therefore leaves ``_loaded`` false and is retryable.
        new_capability_states = self._probe_staged_snapshot(new_animators, new_capabilities)

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

    def _probe_staged_snapshot(
        self,
        animators: dict[str, RuntimeAnimator],
        capabilities: dict[str, CapabilitySpec],
    ) -> dict[str, CapabilityState]:
        """Probe staged hydration and invalidate stale observations on contract failure."""
        try:
            return run_sync(
                self._probe_snapshot(
                    animators=animators,
                    capabilities=capabilities,
                )
            )
        except _ProbeContractError as exc:
            self._invalidate_capability_states(exc.requested_keys)
            raise

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
        rune = self._soulstones.get(name)
        return rune.model_copy(deep=True) if rune is not None else None

    def list_soulstone_runes(self) -> list[SoulstoneConfig]:
        """Return every local runtime declaration, including capability-empty stones."""
        self.ensure_loaded()
        return [rune.model_copy(deep=True) for rune in self._soulstones.values()]

    def get_portal_rune(self, name: str) -> PortalConfig | None:
        self.ensure_loaded()
        rune = self._portals.get(name)
        return rune.model_copy(deep=True) if rune is not None else None

    def get_group(self, group_name: str) -> Sequence[SoulstoneConfig]:
        self.ensure_loaded()
        return tuple(rune.model_copy(deep=True) for rune in self._groups.get(group_name, ()))

    def list_runtime_animators(self) -> list[RuntimeAnimator]:
        self.ensure_loaded()
        return list(self._animators.values())

    def list_runes(self) -> list[AnimatorConfigDeclaration]:
        self.ensure_loaded()
        return [
            *(rune.model_copy(deep=True) for rune in self._soulstones.values()),
            *(rune.model_copy(deep=True) for rune in self._portals.values()),
        ]

    def list_models(self, name: str) -> Sequence[ModelInfo]:
        animator = self.get_runtime(name)
        if animator is None:
            return ()
        connector = animator.connector
        if not isinstance(connector, ModelConnector):
            return ()
        return tuple(model.model_copy(deep=True) for model in connector.list_models())

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
        return [spec.model_copy(deep=True) for spec in self._capabilities.values()]

    def list_capabilities_for_animator(self, name: str) -> list[CapabilitySpec]:
        """List synthesized capabilities for a specific animator."""
        self.ensure_loaded()
        return [spec.model_copy(deep=True) for spec in self._capabilities.values() if spec.animator_name == name]

    def get_capability(self, key: str) -> CapabilitySpec | None:
        """Return a capability spec by stable capability key."""
        self.ensure_loaded()
        spec = self._capabilities.get(key)
        return spec.model_copy(deep=True) if spec is not None else None

    def get_capability_state(self, key: str) -> CapabilityState | None:
        """Return the last observed capability state by stable capability key."""
        self.ensure_loaded()
        state = self._capability_states.get(key)
        return state.model_copy(deep=True) if state is not None else None

    def list_capability_states(self) -> list[CapabilityState]:
        """List the last observed capability states across all loaded animators."""
        self.ensure_loaded()
        return [state.model_copy(deep=True) for state in self._capability_states.values()]

    def list_capability_states_for_animator(self, name: str) -> list[CapabilityState]:
        """List the last observed capability states for a specific animator."""
        self.ensure_loaded()
        keys = {spec.key for spec in self.list_capabilities_for_animator(name)}
        return [
            state.model_copy(deep=True) for state in self._capability_states.values() if state.capability_key in keys
        ]

    async def refresh_capability_states_for_animator(self, name: str) -> list[CapabilityState]:
        """Probe and atomically replace exact capability states for one Animator."""
        self.ensure_loaded()
        async with self._probe_lock:
            animator = self._animators.get(name)
            if animator is None:
                return []

            specs = [spec for spec in self._capabilities.values() if spec.animator_name == name]
            if not specs:
                return []

            try:
                states_by_key = await self._probe_animator(animator=animator, specs=specs)
            except _ProbeContractError as exc:
                self._invalidate_capability_states(exc.requested_keys)
                raise
            except asyncio.CancelledError:
                self._invalidate_capability_states({spec.key for spec in specs})
                raise
            except Exception:
                self._invalidate_capability_states({spec.key for spec in specs})
                raise
            requested_keys = set(states_by_key)
            replacement = {key: state for key, state in self._capability_states.items() if key not in requested_keys}
            replacement.update(states_by_key)
            self._capability_states = replacement
            return [states_by_key[spec.key].model_copy(deep=True) for spec in specs]

    async def refresh_capability_state(self, key: str) -> CapabilityState | None:
        """Re-probe and return the latest cached state for one capability key."""
        self.ensure_loaded()
        spec = self._capabilities.get(key)
        if spec is None:
            return None
        await self.refresh_capability_states_for_animator(spec.animator_name)
        state = self._capability_states.get(key)
        return state.model_copy(deep=True) if state is not None else None

    async def _probe_animator(
        self,
        *,
        animator: RuntimeAnimator,
        specs: Sequence[CapabilitySpec],
    ) -> dict[str, CapabilityState]:
        """Validate one adapter's probe as an exact, duplicate-free key set."""
        specs_by_key = {spec.key: spec for spec in specs}
        requested_keys = set(specs_by_key)
        states = await self._runtime_adapters.probe_capability_states(
            animator,
            [spec.model_copy(deep=True) for spec in specs],
        )
        states_by_key: dict[str, CapabilityState] = {}
        duplicate_keys: set[str] = set()
        inconsistent_keys: set[str] = set()
        for observed in states:
            state = observed.model_copy(deep=True)
            if state.capability_key in states_by_key:
                duplicate_keys.add(state.capability_key)
            states_by_key[state.capability_key] = state
            spec = specs_by_key.get(state.capability_key)
            if spec is not None and state.is_dynamic != spec.is_dynamic:
                inconsistent_keys.add(state.capability_key)

        returned_keys = set(states_by_key)
        missing_keys = requested_keys - returned_keys
        foreign_keys = returned_keys - requested_keys
        if duplicate_keys or missing_keys or foreign_keys or inconsistent_keys:
            details: list[str] = []
            if duplicate_keys:
                details.append(f"duplicate={sorted(duplicate_keys)!r}")
            if missing_keys:
                details.append(f"missing={sorted(missing_keys)!r}")
            if foreign_keys:
                details.append(f"foreign={sorted(foreign_keys)!r}")
            if inconsistent_keys:
                details.append(f"inconsistent={sorted(inconsistent_keys)!r}")
            msg = f"Probe contract violation for Animator {animator.id!r}: {', '.join(details)}."
            raise _ProbeContractError(msg, requested_keys=requested_keys)
        return states_by_key

    def _invalidate_capability_states(self, keys: Collection[str]) -> None:
        """Atomically remove observations invalidated by a malformed probe."""
        invalid = set(keys)
        self._capability_states = {key: state for key, state in self._capability_states.items() if key not in invalid}

    async def _probe_snapshot(
        self,
        *,
        animators: dict[str, RuntimeAnimator],
        capabilities: dict[str, CapabilitySpec],
    ) -> dict[str, CapabilityState]:
        """Probe a detached registry snapshot without publishing partial results."""
        states: dict[str, CapabilityState] = {}
        for name, animator in animators.items():
            specs = [spec for spec in capabilities.values() if spec.animator_name == name]
            if not specs:
                continue
            states.update(await self._probe_animator(animator=animator, specs=specs))
        return states

    async def _probe_all_async(self) -> None:
        """Probe every Animator and replace the complete state cache atomically."""
        async with self._probe_lock:
            try:
                states = await self._probe_snapshot(
                    animators=self._animators,
                    capabilities=self._capabilities,
                )
            except _ProbeContractError as exc:
                self._invalidate_capability_states(exc.requested_keys)
                raise
            except asyncio.CancelledError:
                self._invalidate_capability_states(self._capabilities)
                raise
            except Exception:
                self._invalidate_capability_states(self._capabilities)
                raise
            self._capability_states = states

    async def probe_all(self) -> None:
        """Refresh capability states for every animator (startup async probe)."""
        self.ensure_loaded()
        await self._probe_all_async()

    async def activate_capability(self, key: str) -> ActivationResult:
        """Request runtime-specific activation for a single capability key.

        On acceptance, the Animator's states are re-probed so the phase reflects the
        activation in flight.
        """
        self.ensure_loaded()
        spec = self._capabilities.get(key)
        if spec is None:
            return ActivationResult(accepted=False, phase=CapabilityPhase.UNKNOWN, reason="unknown capability")

        animator = self._animators.get(spec.animator_name)
        if animator is None:
            return ActivationResult(accepted=False, phase=CapabilityPhase.UNKNOWN, reason="animator not registered")

        try:
            result = await self._runtime_adapters.activate_capability(animator, spec.model_copy(deep=True))
            if result.accepted:
                await self.refresh_capability_states_for_animator(spec.animator_name)
        except asyncio.CancelledError:
            await self._abandon_activation(animator, spec)
            raise
        except Exception:
            await self._abandon_activation(animator, spec)
            raise
        else:
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
        if spec.source_kind is SourceKind.PORTAL:
            raise CapabilityUnavailable(key, "portal egress admission is not configured")

        # ADR 22 requires a fresh exact observation immediately before issue.
        # A cached WARM state may outlive the runtime or loaded model and cannot
        # authorize a new live handle on its own.
        await self.refresh_capability_state(key)
        async with self._probe_lock:
            state = self._capability_states.get(key)
            if state is None or state.phase is not CapabilityPhase.WARM:
                reason = f"phase={state.phase.value}" if state else "capability state unavailable"
                raise CapabilityUnavailable(key, reason)

            animator = self._animators.get(spec.animator_name)
            if animator is None:
                raise CapabilityUnavailable(key, "animator not registered")

            model = None
            toolsets: tuple[AbstractToolset[Any], ...] = ()
            if spec.family is CapabilityFamily.CHAT:
                try:
                    model = self._binder.bind_model(animator, model_id=spec.model_id)
                except AnimatorBindingError as exc:
                    raise CapabilityUnavailable(key, f"model hydration failed: {exc}") from exc
                if spec.supports_tools is True:
                    toolsets = tuple(self._binder.bind_toolsets(animator))
            elif spec.family is CapabilityFamily.TOOL_EXECUTION:
                toolsets = tuple(self._binder.bind_toolsets(animator))
                if not toolsets:
                    raise CapabilityUnavailable(key, "tool_execution has no admitted toolset surface")
            else:
                raise CapabilityUnavailable(
                    key,
                    f"v1 {spec.family.value} is routing metadata without an executable grant surface",
                )

            canonical_spec = spec.model_copy(deep=True)
            canonical_state = state.model_copy(deep=True)
            lease = GrantLease(grant_id=uuid4().hex, holder=holder, issued_at=datetime.now(UTC), scope=scope)
            return CapabilityGrant(
                spec=canonical_spec,
                state=canonical_state,
                lease=lease,
                generation=canonical_spec.generation_profile,
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

        deadline = time.monotonic() + timeout_s
        animator = self._animators.get(spec.animator_name)
        estimated_ready_ms = getattr(animator.connector.link, "estimated_ready_ms", None) if animator else None
        try:
            if estimated_ready_ms:
                remaining = max(0.0, deadline - time.monotonic())
                if remaining:
                    await anyio.sleep(min(estimated_ready_ms / 1000.0, remaining))
            return await self._poll_until_warm(
                key=key,
                deadline=deadline,
                interval_s=interval_s,
            )
        except asyncio.CancelledError:
            await self._abandon_activation(animator, spec)
            raise
        except Exception:
            await self._abandon_activation(animator, spec)
            raise

    async def _poll_until_warm(
        self,
        *,
        key: str,
        deadline: float,
        interval_s: float,
    ) -> CapabilityState:
        """Poll one capability under the caller's single absolute deadline."""
        last_state = self._capability_states.get(key)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ActivationTimeout(key, last_state)
            state: CapabilityState | None = None
            with anyio.move_on_after(remaining) as probe_scope:
                state = await self.refresh_capability_state(key)
            if probe_scope.cancel_called:
                raise ActivationTimeout(key, last_state)
            if state is None:
                raise CapabilityUnavailable(key, "capability state unavailable")
            last_state = state
            if state.phase is CapabilityPhase.WARM:
                return state
            if state.phase is CapabilityPhase.ERROR:
                raise ActivationFailed(key, reason=state.reason)
            await anyio.sleep(min(interval_s, max(0.0, deadline - time.monotonic())))

    async def _abandon_activation(self, animator: RuntimeAnimator | None, spec: CapabilitySpec) -> None:
        """Release adapter-owned observers without losing the canonical failure."""
        if animator is None:
            return

        async def abandon() -> None:
            with anyio.move_on_after(_ACTIVATION_CLEANUP_TIMEOUT_SECONDS, shield=True) as cleanup_scope:
                try:
                    await self._runtime_adapters.abandon_activation(animator, spec.model_copy(deep=True))
                except Exception:  # noqa: BLE001 - cleanup must never mask the canonical activation failure
                    logger.warning(
                        "activation_observer_cleanup_failed",
                        capability_key=spec.key,
                        exc_info=True,
                    )
            if cleanup_scope.cancel_called:
                logger.warning(
                    "activation_observer_cleanup_timed_out",
                    capability_key=spec.key,
                    timeout_s=_ACTIVATION_CLEANUP_TIMEOUT_SECONDS,
                )

        await complete_under_cancellation(abandon())

    def list_persistent_residents(self) -> list[CapabilitySpec]:
        """List capabilities declared on persistent-resident animators."""
        self.ensure_loaded()
        return [
            spec.model_copy(deep=True) for spec in self._capabilities.values() if spec.concurrency.persistent_resident
        ]

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
