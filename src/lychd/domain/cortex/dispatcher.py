from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from lychd.domain.animation.capabilities import CapabilityPhase, CapabilitySpec, CapabilityState, SourceKind
from lychd.domain.animation.errors import CapabilityUnavailable, HardwareTransitionRequired
from lychd.domain.animation.protocols import CapabilityRegistry, require_capability_record
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.cortex.leases import AnimatorAdmission, LeaseAdmissionClosed

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from lychd.domain.animation.capabilities import CapabilityGrant
    from lychd.domain.cortex.events import RunEventBus
    from lychd.domain.cortex.leases import LeaseLedger

__all__ = ["CapabilityRegistry", "Dispatcher", "HardwareTransitionRequired"]

# Only TRUE synonyms belong here. Every identity mapping (chat→CHAT, …) and the
# hyphen variant (tool-execution) are handled by the normalize + enum fallback below,
# so listing them would just be a drift surface the day a family is added.
_INTENT_ALIASES = {"reasoning": CapabilityFamily.CHAT}


class Dispatcher:
    """Resolve abstract intent onto the canonical registry and lease scoped grants."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        *,
        leases: LeaseLedger,
        events: RunEventBus | None = None,
    ) -> None:
        """Initialize against the injected canonical registry and the lease ledger."""
        self._registry = registry
        self._leases = leases
        self._events = events

    @asynccontextmanager
    async def lease_grant(
        self,
        *,
        family: CapabilityFamily | str,
        model_name: str | None = None,
        run_id: str,
        priority: int = 50,
        require_modalities: tuple[str, ...] = (),
        requires_tools: bool = False,
        # WAVE7-S10: `require_warm: bool = False` lands here (Wave 7 K4).
        # Params stay KW-ONLY so that addition is non-breaking.
    ) -> AsyncIterator[CapabilityGrant]:
        """Lease a scoped grant for the resolved family/model/modality request.

        Resolves family (+ model preference, + modality admission) to a spec,
        drives the phase decision table to WARM, and yields the grant.
        """
        spec = self._resolve_spec(
            family,
            model_name=model_name,
            require_modalities=require_modalities,
            requires_tools=requires_tools,
        )
        grant = await self._grant_for_spec(spec, holder=f"run:{run_id}")
        self._acquire_or_park(grant, priority=priority)
        try:
            if self._events is not None:
                from lychd.domain.cortex.execution_context import current_occurrence_id

                self._events.emitter(run_id).dispatch(
                    grant.key,
                    animator=grant.spec.animator_name,
                    family=grant.spec.family.value,
                    model_id=grant.spec.model_id,
                    phase=grant.state.phase.value,
                    occurrence_id=current_occurrence_id() or "",
                    grant_id=grant.lease.grant_id,
                )
            yield grant
        finally:
            self._leases.release(grant.lease.grant_id)

    @asynccontextmanager
    async def lease_grant_key(
        self,
        key: str,
        *,
        holder: str,
        priority: int = 50,
    ) -> AsyncIterator[CapabilityGrant]:
        """Key-addressed lease form (CLI, tests, orchestrator manual paths)."""
        spec = self._registry.get_capability(key)
        if spec is None:
            msg = f"Unknown capability: {key}"
            raise ValueError(msg)
        grant = await self._grant_for_spec(spec, holder=holder)
        self._acquire_or_park(grant, priority=priority)
        try:
            yield grant
        finally:
            self._leases.release(grant.lease.grant_id)

    async def _grant_for_spec(self, spec: CapabilitySpec, *, holder: str) -> CapabilityGrant:
        """Drive the A3 §2 phase decision table to a warm grant.

        ``HardwareTransitionRequired`` is raised BEFORE any lease is registered — a
        parked run holds no lease (true by construction: ``acquire()`` happens only
        after this returns).
        """
        self._require_egress_admission(spec)
        if self._leases.admission(spec.animator_name) is AnimatorAdmission.DRAINING:
            raise self._transition_required(spec)
        return await self._drive_to_grant(spec, holder=holder)

    @staticmethod
    def _require_egress_admission(spec: CapabilitySpec) -> None:
        """Quarantine remote execution until a typed egress authority exists.

        Portal declarations and health remain observable through the registry/Nexus,
        but dispatching prompts or history to them is a deny-by-default boundary.
        """
        if spec.source_kind is SourceKind.PORTAL:
            raise CapabilityUnavailable(
                spec.key,
                "portal egress admission is not configured",
            )

    def _acquire_or_park(self, grant: CapabilityGrant, *, priority: int) -> None:
        """Atomically register a grant or convert a concurrent drain into stasis.

        ``issue_grant`` is async, so admission may close after the phase preflight but
        before the loop-confined ledger registration.  Only that typed, expected race
        becomes ``HardwareTransitionRequired``; duplicate-id and other ledger defects
        continue to fail loudly.
        """
        try:
            self._leases.acquire(grant, priority=priority)
        except LeaseAdmissionClosed as exc:
            raise self._transition_required(grant.spec) from exc

    def _transition_required(self, spec: CapabilitySpec) -> HardwareTransitionRequired:
        """Build the canonical handle-free signal for one managed capability."""
        return HardwareTransitionRequired(
            spec.key,
            spec.animator_name,
            self._estimated_ready_ms(spec),
        )

    async def _drive_to_grant(self, spec: CapabilitySpec, *, holder: str) -> CapabilityGrant:
        _spec, state = await require_capability_record(self._registry, spec.key)
        phase = state.phase

        if phase is CapabilityPhase.WARM:
            # ``require_capability_record`` probes asynchronously; admission may have
            # closed while that probe yielded, before grant assembly even begins.
            if self._leases.admission(spec.animator_name) is AnimatorAdmission.DRAINING:
                raise self._transition_required(spec)
            return await self._registry.issue_grant(spec.key, holder=holder)

        if phase in {CapabilityPhase.COLD, CapabilityPhase.ACTIVATABLE, CapabilityPhase.WARMING}:
            if spec.concurrency.dedicated:
                raise self._transition_required(spec)
            raise CapabilityUnavailable(
                spec.key,
                state.reason or f"shared animator '{spec.animator_name}' is not lifecycle-managed by LychD",
            )

        if phase is CapabilityPhase.ERROR:
            raise CapabilityUnavailable(spec.key, state.reason)

        # ``require_capability_record`` already performed the one admitted refresh.
        # UNKNOWN after that observation settles unavailable without a probe loop.
        raise CapabilityUnavailable(spec.key, state.reason or "capability phase unknown")

    def _estimated_ready_ms(self, spec: CapabilitySpec) -> int | None:
        """Read an optional estimate without making link presence an admission condition."""
        animator = self._registry.get_runtime(spec.animator_name)
        if animator is None:
            return None
        link = getattr(getattr(animator, "connector", None), "link", None)
        estimate = getattr(link, "estimated_ready_ms", None)
        return estimate if isinstance(estimate, int) else None

    def resolve_intent(self, intent_type: str) -> CapabilitySpec:
        """Resolve a semantic intent into one canonical capability spec (Nexus/status read)."""
        return self._resolve_spec(
            intent_type,
            model_name=None,
            require_modalities=(),
            requires_tools=False,
        )

    def _resolve_spec(
        self,
        family: CapabilityFamily | str,
        *,
        model_name: str | None,
        require_modalities: tuple[str, ...],
        requires_tools: bool = False,
    ) -> CapabilitySpec:
        target = family if isinstance(family, CapabilityFamily) else self._normalize_family(family)
        required = set(require_modalities)
        candidates: list[tuple[CapabilitySpec, CapabilityState]] = []
        quarantined_portal = False
        for spec in self._registry.list_capabilities():
            if spec.family != target:
                continue
            if model_name is not None and spec.model_id != model_name:
                continue
            if required and not required <= set(spec.modalities_in):
                continue
            if requires_tools and spec.supports_tools is not True:
                continue
            if spec.source_kind is SourceKind.PORTAL:
                quarantined_portal = True
                continue
            state = self._registry.get_capability_state(spec.key)
            if state is None or not state.is_available:
                continue
            candidates.append((spec, state))

        if not candidates:
            if quarantined_portal:
                raise CapabilityUnavailable(str(family), "portal egress admission is not configured")
            raise CapabilityUnavailable(str(family), "no registered capability can fulfill the request")

        candidates.sort(key=self._candidate_sort_key)
        return candidates[0][0]

    def _normalize_family(self, intent_type: str) -> CapabilityFamily:
        normalized = intent_type.strip().lower().replace("-", "_")
        if alias := _INTENT_ALIASES.get(normalized):
            return alias
        try:
            return CapabilityFamily(normalized)
        except ValueError as exc:
            msg = f"Unknown intent type: {intent_type}"
            raise ValueError(msg) from exc

    def _candidate_sort_key(
        self,
        candidate: tuple[CapabilitySpec, CapabilityState],
    ) -> tuple[bool, bool, bool, str, str]:
        """Prefer open admission before warmth so a draining runtime gets no new work."""
        spec, state = candidate
        draining = self._leases.admission(spec.animator_name) is AnimatorAdmission.DRAINING
        return (draining, not state.is_active, not state.warm, spec.animator_name, spec.key)
