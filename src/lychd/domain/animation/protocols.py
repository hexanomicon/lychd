"""The one merged capability-registry protocol (A4-U1, spec-00-FINAL C1).

`CapabilityRegistry` is the single structural surface required by BOTH dispatch
resolution (`Dispatcher`) and transition planning (`OrchestratorManager`). It is
the union of the two near-duplicate protocols those modules used to declare
locally; `AnimatorRegistry` is its sole implementation and both consumers import
from here.

`require_capability_record` is the one copy of the `refresh… or get…` fallback +
canonical error strings that `Dispatcher._resolve_spec` and
`OrchestratorManager._get_capability_record` used to duplicate.

Async-surface note (spec-00-FINAL C1): A3's Wave-3 registry rework (U3/U4) flips
`refresh_capability_state`/`refresh_capability_states_for_animator`/
`activate_capability` to async and adds `issue_grant`/`await_warm` to the grant
surface. Those methods are declared here with their CURRENT (Wave-1) synchronous
signatures because the still-synchronous `Dispatcher`/`OrchestratorManager` and
graph nodes call them synchronously; flipping them now would require the Grant-v2
lease rework (explicitly Wave 3). The realignment lands with A3's U3/U4.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lychd.domain.animation.capabilities import (
        ActivationResult,
        CapabilitySpec,
        CapabilityState,
    )

__all__ = ["CapabilityRegistry", "require_capability_record"]


@runtime_checkable
class CapabilityRegistry(Protocol):
    """Unified registry surface for dispatch resolution AND transition planning.

    The structural union of the former ``dispatcher.CapabilityRegistry`` and
    ``manager.OrchestratorRegistry`` protocols. Sole implementation:
    ``AnimatorRegistry``.
    """

    # -- shared reads (both consumers) -----------------------------------
    def list_capabilities(self) -> list[CapabilitySpec]: ...

    def get_capability(self, key: str, /) -> CapabilitySpec | None: ...

    def get_capability_state(self, key: str, /) -> CapabilityState | None: ...

    def refresh_capability_state(self, key: str, /) -> CapabilityState | None: ...

    def get_runtime(self, name: str, /) -> Any | None: ...

    # -- dispatch surface -------------------------------------------------
    def bind_model(self, name: str, /, *, model_id: str | None = None) -> Any | None: ...

    def bind_toolsets(self, name: str, /) -> Sequence[Any]: ...

    # -- orchestration surface -------------------------------------------
    def list_capability_states_for_animator(self, name: str, /) -> list[CapabilityState]: ...

    def refresh_capability_states_for_animator(self, name: str, /) -> list[CapabilityState]: ...

    def get_soulstone_rune(self, name: str, /) -> Any | None: ...

    def activate_capability(self, key: str, /) -> ActivationResult: ...


def require_capability_record(
    registry: CapabilityRegistry,
    key: str,
) -> tuple[CapabilitySpec, CapabilityState]:
    """Return ``(spec, state)`` for ``key`` or raise the canonical error.

    The one copy of the ``refresh… or get…`` fallback both consumers duplicated.
    """
    spec = registry.get_capability(key)
    if spec is None:
        msg = f"Unknown capability: {key}"
        raise ValueError(msg)
    state = registry.refresh_capability_state(key) or registry.get_capability_state(key)
    if state is None:
        msg = f"Capability state is unavailable for '{key}'."
        raise ValueError(msg)
    return spec, state
