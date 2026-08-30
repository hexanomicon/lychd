from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from lychd.domain.animation.animators import RuntimeAnimator
from lychd.domain.animation.capabilities import ActivationResult, CapabilitySpec, CapabilityState
from lychd.domain.animation.schemas import PortalConfig, SoulstoneConfig

LISTEN_HOST = "0.0.0.0"  # noqa: S104


@dataclass(slots=True)
class RuntimePlan:
    """Container runtime plan emitted by an adapter."""

    exec_args: list[str] = field(default_factory=list)
    env_overrides: dict[str, str] = field(default_factory=dict)
    volumes: list[str] = field(default_factory=list)
    podman_args: list[str] = field(default_factory=list)
    secrets: list[str] = field(default_factory=list)
    unit_binds_to: list[str] = field(default_factory=list)
    unit_after: list[str] = field(default_factory=list)
    pod_shared_memory_bytes: int = 0


@dataclass(frozen=True)
class SoulstoneDefinition:
    """Registration-time definition of one Soulstone runtime family."""

    rune_schema: type[SoulstoneConfig]
    runtime_adapter: SoulstoneRuntimeAdapter


class PortalRuntimeFactory(Protocol):
    """Total callable that builds a runtime animator for its exact Portal Rune schema."""

    def __call__(self, portal: PortalConfig) -> RuntimeAnimator: ...


class PortalProbe(Protocol):
    """Exact-owner live probe for one Portal runtime family."""

    async def __call__(self, animator: RuntimeAnimator) -> None: ...


@dataclass(frozen=True)
class PortalDefinition:
    """Registration-time factory and optional probe for one exact Portal schema."""

    rune_schema: type[PortalConfig]
    factory: PortalRuntimeFactory
    probe: PortalProbe | None = None


@runtime_checkable
class ActivationObserver(Protocol):
    """Optional adapter capability for releasing asynchronous activation observers."""

    async def abandon_activation(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> None: ...


@runtime_checkable
class CapabilityActivator(Protocol):
    """Optional adapter capability for runtimes with in-process model activation."""

    async def activate_capability(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> ActivationResult: ...


class SoulstoneRuntimeAdapter(Protocol):
    """Contract for Soulstone runtime planners/builders."""

    @property
    def runtime(self) -> str: ...

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan: ...

    def build_runtime(self, soulstone: SoulstoneConfig) -> RuntimeAnimator | None: ...

    def build_capability_specs(self, soulstone: SoulstoneConfig) -> list[CapabilitySpec]: ...

    async def probe_capability_states(
        self,
        animator: RuntimeAnimator,
        specs: list[CapabilitySpec],
    ) -> list[CapabilityState]: ...


class SoulstoneRuntimePlanner(Protocol):
    """Narrow planning contract used by transmutation orchestration."""

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan: ...


__all__ = [
    "LISTEN_HOST",
    "ActivationObserver",
    "CapabilityActivator",
    "PortalDefinition",
    "PortalProbe",
    "PortalRuntimeFactory",
    "RuntimeAnimator",
    "RuntimePlan",
    "SoulstoneDefinition",
    "SoulstoneRuntimeAdapter",
    "SoulstoneRuntimePlanner",
]
