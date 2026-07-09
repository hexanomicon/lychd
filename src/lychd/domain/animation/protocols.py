"""The one merged capability-registry protocol (A4-U1, spec-00-FINAL C1).

`CapabilityRegistry` is the single structural surface required by BOTH dispatch
resolution (`Dispatcher`) and transition planning (`OrchestratorManager`). It is
the union of the two near-duplicate protocols those modules used to declare
locally; `AnimatorRegistry` is its sole implementation and both consumers import
from here.

`require_capability_record` is the one copy of the `refresh… or get…` fallback +
canonical error strings that `Dispatcher` and
`OrchestratorManager._get_capability_record` used to duplicate. It is async now
because `refresh_capability_state` is async (Wave 3).

Wave-3 surface (spec-00-FINAL C1): reads (`list_capabilities`/`get_capability`/
`get_capability_state`/`get_runtime`/`get_soulstone_rune`) stay sync;
the probe/activate/grant surface (`refresh_*`/`activate_capability`/`await_warm`/
`issue_grant`) is async. Sole implementation: `AnimatorRegistry`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from lychd.domain.animation.animators import RuntimeAnimator
    from lychd.domain.animation.capabilities import (
        ActivationResult,
        CapabilityGrant,
        CapabilitySpec,
        CapabilityState,
    )
    from lychd.domain.animation.schemas import SoulstoneConfig

__all__ = ["CapabilityRegistry", "require_capability_record"]


@runtime_checkable
class CapabilityRegistry(Protocol):
    """Unified registry surface for dispatch resolution AND transition planning.

    The structural union of the former ``dispatcher.CapabilityRegistry`` and
    ``manager.OrchestratorRegistry`` protocols. Sole implementation:
    ``AnimatorRegistry``.
    """

    # -- sync reads (unchanged) ------------------------------------------
    def list_capabilities(self) -> list[CapabilitySpec]: ...

    def get_capability(self, key: str, /) -> CapabilitySpec | None: ...

    def get_capability_state(self, key: str, /) -> CapabilityState | None: ...

    def get_runtime(self, name: str, /) -> RuntimeAnimator | None: ...

    def list_capability_states_for_animator(self, name: str, /) -> list[CapabilityState]: ...

    def get_soulstone_rune(self, name: str, /) -> SoulstoneConfig | None: ...

    # -- async probe/activate/grant surface (Wave 3 truth) ---------------
    async def refresh_capability_state(self, key: str, /) -> CapabilityState | None: ...

    async def refresh_capability_states_for_animator(self, name: str, /) -> list[CapabilityState]: ...

    async def activate_capability(self, key: str, /) -> ActivationResult: ...

    async def await_warm(
        self,
        key: str,
        /,
        *,
        timeout_s: float = 120.0,
        interval_s: float = 0.75,
    ) -> CapabilityState: ...

    async def issue_grant(
        self,
        key: str,
        /,
        *,
        holder: str,
        scope: Literal["step", "run"] = "step",
    ) -> CapabilityGrant: ...


async def require_capability_record(
    registry: CapabilityRegistry,
    key: str,
) -> tuple[CapabilitySpec, CapabilityState]:
    """Return ``(spec, state)`` for ``key`` or raise the canonical error.

    Async now (refresh is async). The one copy of the ``refresh… or get…``
    fallback both consumers duplicated, with the canonical error strings.
    """
    spec = registry.get_capability(key)
    if spec is None:
        msg = f"Unknown capability: {key}"
        raise ValueError(msg)
    state = await registry.refresh_capability_state(key) or registry.get_capability_state(key)
    if state is None:
        msg = f"Capability state is unavailable for '{key}'."
        raise ValueError(msg)
    return spec, state
