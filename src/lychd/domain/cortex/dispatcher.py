from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from lychd.domain.animation.capabilities import CapabilityGrant, CapabilitySpec, CapabilityState
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.services.binder import AnimatorBindingError
from lychd.domain.animation.services.registry import AnimatorRegistry

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


class CapabilityRegistry(Protocol):
    """Registry surface required by dispatch resolution."""

    def list_capabilities(self) -> list[CapabilitySpec]: ...

    def get_capability(self, key: str, /) -> CapabilitySpec | None: ...

    def get_capability_state(self, key: str, /) -> CapabilityState | None: ...

    def refresh_capability_state(self, key: str, /) -> CapabilityState | None: ...

    def get_runtime(self, name: str, /) -> Any | None: ...

    def bind_model(self, name: str, /, *, model_id: str | None = None) -> Any | None: ...

    def bind_toolsets(self, name: str, /) -> Sequence[Any]: ...


class HardwareTransitionRequired(Exception):  # noqa: N818
    """Raised when a requested capability exists but the substrate is not warm."""

    def __init__(self, spec: CapabilitySpec, state: CapabilityState, animator: Any) -> None:
        """Store the canonical capability record that requires a transition."""
        super().__init__(f"Hardware transition required for capability: {spec.key}")
        self.spec = spec
        self.state = state
        self.animator = animator


class Dispatcher:
    """Resolve abstract intent onto the canonical capability registry."""

    def __init__(self, registry: CapabilityRegistry | None = None) -> None:
        """Initialize the dispatcher against the canonical runtime registry."""
        self._registry = registry or AnimatorRegistry()

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
        spec = self._resolve_spec(capability)
        state = self._registry.refresh_capability_state(spec.key) or self._registry.get_capability_state(spec.key)
        if state is None:
            msg = f"Capability state is unavailable for '{spec.key}'."
            raise ValueError(msg)

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

    def _resolve_spec(self, capability: CapabilitySpec | str) -> CapabilitySpec:
        if isinstance(capability, CapabilitySpec):
            return capability

        spec = self._registry.get_capability(capability)
        if spec is None:
            msg = f"Unknown capability: {capability}"
            raise ValueError(msg)
        return spec

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
