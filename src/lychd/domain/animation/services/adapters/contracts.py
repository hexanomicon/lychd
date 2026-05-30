from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from lychd.domain.animation.animators import Animator
from lychd.domain.animation.capabilities import CapabilitySpec, CapabilityState
from lychd.domain.animation.connectors import Connector
from lychd.domain.animation.schemas import PortalConfig, SoulstoneConfig
from lychd.system.schemas import QuadletContainer

LISTEN_HOST = "0.0.0.0"  # noqa: S104

type RuntimeAnimator = Animator[Connector, SoulstoneConfig | PortalConfig]


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


class SoulstoneRuntimeAdapter(Protocol):
    """Contract for Soulstone runtime planners/builders."""

    runtime: str

    def supports(self, runtime: str) -> bool: ...

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan: ...

    def build_runtime(self, soulstone: SoulstoneConfig, quadlet: QuadletContainer) -> RuntimeAnimator | None: ...

    def build_capability_specs(self, soulstone: SoulstoneConfig) -> list[CapabilitySpec]: ...

    def probe_capability_states(self, animator: RuntimeAnimator, specs: list[CapabilitySpec]) -> list[CapabilityState]: ...

    def activate_capability(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> bool: ...


class SoulstoneRuntimePlanner(Protocol):
    """Narrow planning contract used by transmutation orchestration."""

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan: ...


__all__ = [
    "LISTEN_HOST",
    "RuntimeAnimator",
    "RuntimePlan",
    "SoulstoneDefinition",
    "SoulstoneRuntimeAdapter",
    "SoulstoneRuntimePlanner",
]
