from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from lychd.domain.animation.capabilities import CapabilityPhase, CapabilitySpec, CapabilityState
from lychd.domain.animation.errors import ActivationFailed, CapabilityUnavailable, HardwareTransitionRequired
from lychd.domain.animation.protocols import CapabilityRegistry, require_capability_record
from lychd.domain.animation.schemas.capability_family import CapabilityFamily

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from lychd.domain.animation.capabilities import CapabilityGrant
    from lychd.domain.cortex.leases import LeaseLedger

__all__ = ["CapabilityRegistry", "Dispatcher", "HardwareTransitionRequired"]

_INTENT_FAMILY_MAP = {
    "reasoning": CapabilityFamily.CHAT,
    "chat": CapabilityFamily.CHAT,
    "vision": CapabilityFamily.VISION,
    "embedding": CapabilityFamily.EMBEDDING,
    "stt": CapabilityFamily.STT,
    "tts": CapabilityFamily.TTS,
    "tool_execution": CapabilityFamily.TOOL_EXECUTION,
    "tool-execution": CapabilityFamily.TOOL_EXECUTION,
    "rerank": CapabilityFamily.RERANK,
}


class Dispatcher:
    """Resolve abstract intent onto the canonical registry and lease scoped grants."""

    def __init__(self, registry: CapabilityRegistry, *, leases: LeaseLedger) -> None:
        """Initialize against the injected canonical registry and the lease ledger."""
        self._registry = registry
        self._leases = leases

    @asynccontextmanager
    async def lease_grant(
        self,
        *,
        family: CapabilityFamily | str,
        model_name: str | None = None,
        run_id: str,
        priority: int = 50,
        require_modalities: tuple[str, ...] = (),
        # WAVE7-S10: `require_warm: bool = False` lands here (Wave 7 K4).
        # Params stay KW-ONLY so that addition is non-breaking.
    ) -> AsyncIterator[CapabilityGrant]:
        """Lease a scoped grant for the resolved family/model/modality request.

        Resolves family (+ model preference, + modality admission) to a spec,
        drives the phase decision table to WARM, and yields the grant.
        """
        spec = self._resolve_spec(family, model_name=model_name, require_modalities=require_modalities)
        grant = await self._grant_for_spec(spec, holder=f"run:{run_id}")
        self._leases.acquire(grant, priority=priority)
        try:
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
        self._leases.acquire(grant, priority=priority)
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
        return await self._drive_to_grant(spec, holder=holder, allow_refresh=True)

    async def _drive_to_grant(self, spec: CapabilitySpec, *, holder: str, allow_refresh: bool) -> CapabilityGrant:
        _spec, state = await require_capability_record(self._registry, spec.key)
        phase = state.phase

        if phase is CapabilityPhase.WARM:
            return await self._registry.issue_grant(spec.key, holder=holder)

        if phase is CapabilityPhase.ACTIVATABLE:
            result = await self._registry.activate_capability(spec.key)
            if not result.accepted:
                raise ActivationFailed(spec.key, result)
            await self._registry.await_warm(spec.key)
            return await self._registry.issue_grant(spec.key, holder=holder)

        if phase is CapabilityPhase.WARMING:
            await self._registry.await_warm(spec.key)
            return await self._registry.issue_grant(spec.key, holder=holder)

        if phase is CapabilityPhase.COLD:
            link = self._link_for(spec)
            if link is not None and getattr(link, "activatable", False):
                raise HardwareTransitionRequired(
                    spec.key, spec.animator_name, getattr(link, "estimated_ready_ms", None)
                )
            raise CapabilityUnavailable(spec.key, state.reason or "animator cold and not activatable")

        if phase is CapabilityPhase.ERROR:
            raise CapabilityUnavailable(spec.key, state.reason)

        # UNKNOWN: refresh once and re-enter the table exactly once.
        if allow_refresh:
            await self._registry.refresh_capability_state(spec.key)
            return await self._drive_to_grant(spec, holder=holder, allow_refresh=False)
        raise CapabilityUnavailable(spec.key, state.reason or "capability phase unknown")

    def _link_for(self, spec: CapabilitySpec) -> object | None:
        animator = self._registry.get_runtime(spec.animator_name)
        if animator is None:
            raise CapabilityUnavailable(spec.key, "animator not registered")
        return getattr(getattr(animator, "connector", None), "link", None)

    def resolve_intent(self, intent_type: str) -> CapabilitySpec:
        """Resolve a semantic intent into one canonical capability spec (Nexus/status read)."""
        return self._resolve_spec(intent_type, model_name=None, require_modalities=())

    def _resolve_spec(
        self,
        family: CapabilityFamily | str,
        *,
        model_name: str | None,
        require_modalities: tuple[str, ...],
    ) -> CapabilitySpec:
        target = family if isinstance(family, CapabilityFamily) else self._normalize_family(family)
        required = set(require_modalities)
        candidates: list[tuple[CapabilitySpec, CapabilityState]] = []
        for spec in self._registry.list_capabilities():
            if spec.family != target:
                continue
            if model_name is not None and spec.model_id != model_name:
                continue
            if required and not required <= set(spec.modalities_in):
                continue
            state = self._registry.get_capability_state(spec.key)
            if state is None or not state.is_available:
                continue
            candidates.append((spec, state))

        if not candidates:
            raise CapabilityUnavailable(str(family), "no registered capability can fulfill the request")

        candidates.sort(key=self._candidate_sort_key)
        return candidates[0][0]

    def _normalize_family(self, intent_type: str) -> CapabilityFamily:
        normalized = intent_type.strip().lower()
        if normalized in _INTENT_FAMILY_MAP:
            return _INTENT_FAMILY_MAP[normalized]

        try:
            return CapabilityFamily(normalized)
        except ValueError as exc:
            msg = f"Unknown intent type: {intent_type}"
            raise ValueError(msg) from exc

    def _candidate_sort_key(self, candidate: tuple[CapabilitySpec, CapabilityState]) -> tuple[bool, bool, str, str]:
        spec, state = candidate
        return (not state.is_active, not state.warm, spec.animator_name, spec.key)
