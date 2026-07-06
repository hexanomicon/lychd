from __future__ import annotations

from lychd.domain.animation.capabilities import CapabilityGrant, CapabilitySpec, CapabilityState
from lychd.domain.animation.errors import HardwareTransitionRequired
from lychd.domain.animation.protocols import CapabilityRegistry, require_capability_record
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.services.binder import AnimatorBindingError

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
    """Resolve abstract intent onto the canonical capability registry."""

    def __init__(self, registry: CapabilityRegistry) -> None:
        """Initialize the dispatcher against the injected canonical runtime registry."""
        self._registry = registry

    def resolve_intent(self, intent_type: str) -> CapabilitySpec:
        """Resolve a semantic intent into one canonical capability spec."""
        family = self._normalize_family(intent_type)
        candidates: list[tuple[CapabilitySpec, CapabilityState]] = []
        for spec in self._registry.list_capabilities():
            if spec.family != family:
                continue

            state = self._registry.get_capability_state(spec.key)
            if state is None or not state.is_available:
                continue
            candidates.append((spec, state))

        if not candidates:
            msg = f"No registered capability can fulfill intent: {intent_type}"
            raise ValueError(msg)

        candidates.sort(key=self._candidate_sort_key)
        return candidates[0][0]

    def request_capability_grant(self, capability: CapabilitySpec | str) -> CapabilityGrant:
        """Grant one capability binding or raise a canonical transition signal."""
        key = capability.key if isinstance(capability, CapabilitySpec) else capability
        spec, state = require_capability_record(self._registry, key)

        animator = self._registry.get_runtime(spec.animator_name)
        if animator is None:
            msg = f"Runtime animator '{spec.animator_name}' is not registered."
            raise ValueError(msg)

        if not state.warm:
            raise HardwareTransitionRequired(spec, state, animator)

        model = None
        if spec.family != CapabilityFamily.TOOL_EXECUTION:
            try:
                model = self._registry.bind_model(spec.animator_name, model_id=spec.model_id)
            except AnimatorBindingError:
                model = None

        return CapabilityGrant(
            spec=spec,
            state=state,
            animator=animator,
            model=model,
            toolsets=tuple(self._registry.bind_toolsets(spec.animator_name)),
        )

    def resolve_capability_grant(self, intent_type: str) -> CapabilityGrant:
        """Resolve an intent and immediately request its binding grant."""
        return self.request_capability_grant(self.resolve_intent(intent_type))

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
