from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Protocol

from lychd.domain.animation.animators import RuntimeAnimator
from lychd.domain.animation.capabilities import ActivationResult, CapabilitySpec, CapabilityState
from lychd.domain.animation.lifecycle import AnimatorLifecycle
from lychd.domain.animation.schemas import PortalConfig, SoulstoneConfig
from lychd.system.schemas import QuadletContainer

LISTEN_HOST = "0.0.0.0"  # noqa: S104


@dataclass(slots=True)
class RuntimePlan:
    """Container runtime plan emitted by an adapter."""

    exec_args: list[str] = field(default_factory=list)
    env_overrides: dict[str, str] = field(default_factory=dict)
    volumes: list[str] = field(default_factory=list)
    podman_args: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SoulstoneDefinition:
    """Registration-time definition of one Soulstone runtime family."""

    rune_schema: type[SoulstoneConfig]
    runtime_adapter: SoulstoneRuntimeAdapter


class PortalRuntimeFactory(Protocol):
    """Callable that builds a runtime animator for a Portal rune, or ``None``."""

    def __call__(self, portal: PortalConfig) -> RuntimeAnimator | None: ...


@dataclass(frozen=True)
class PortalDefinition:
    """Registration-time definition of one Portal provider family."""

    rune_schema: type[PortalConfig]
    factory: PortalRuntimeFactory


class AnimatorControlPlane(Protocol):
    """Optional per-runtime lifecycle surface returned by an adapter (spec §5).

    Generic seam: the domain talks to it via ``inspect_animator`` and, when a
    runtime supports in-place model loading, ``load_model``/``unload_model``.
    """

    async def inspect_animator(self, animator: RuntimeAnimator) -> AnimatorLifecycle: ...

    async def load_model(self, base_url: str, model: str) -> bool: ...

    async def unload_model(self, base_url: str, model: str) -> bool: ...


class SoulstoneRuntimeAdapter(Protocol):
    """Contract for Soulstone runtime planners/builders."""

    runtime: ClassVar[str]

    def supports(self, runtime: str) -> bool: ...

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan: ...

    def build_runtime(self, soulstone: SoulstoneConfig, quadlet: QuadletContainer) -> RuntimeAnimator | None: ...

    def build_capability_specs(self, soulstone: SoulstoneConfig) -> list[CapabilitySpec]: ...

    async def probe_capability_states(
        self,
        animator: RuntimeAnimator,
        specs: list[CapabilitySpec],
    ) -> list[CapabilityState]: ...

    async def activate_capability(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> ActivationResult: ...

    def control_plane(self, animator: RuntimeAnimator) -> AnimatorControlPlane | None: ...


class SoulstoneRuntimePlanner(Protocol):
    """Narrow planning contract used by transmutation orchestration."""

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan: ...


__all__ = [
    "LISTEN_HOST",
    "AnimatorControlPlane",
    "PortalDefinition",
    "PortalRuntimeFactory",
    "RuntimeAnimator",
    "RuntimePlan",
    "SoulstoneDefinition",
    "SoulstoneRuntimeAdapter",
    "SoulstoneRuntimePlanner",
]
