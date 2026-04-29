from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from lychd.domain.animation.animators import Animator
from lychd.domain.animation.connectors import Connector
from lychd.domain.animation.schemas import PortalConfig, SoulstoneConfig

LISTEN_HOST = "0.0.0.0"  # noqa: S104

type RuntimeAnimator = Animator[Connector, SoulstoneConfig | PortalConfig]


@dataclass(slots=True)
class RuntimePlan:
    """Container runtime plan emitted by an adapter."""

    exec_args: list[str] = field(default_factory=list)
    env_overrides: dict[str, str] = field(default_factory=dict)
    volumes: list[str] = field(default_factory=list)
    podman_args: list[str] = field(default_factory=list)


class SoulstoneRuntimeAdapter(Protocol):
    """Contract for Soulstone runtime planners/builders."""

    runtime: str

    def supports(self, runtime: str) -> bool: ...

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan: ...

    def build_runtime(self, soulstone: SoulstoneConfig) -> RuntimeAnimator | None: ...


class SoulstoneRuntimePlanner(Protocol):
    """Narrow planning contract used by transmutation orchestration."""

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan: ...


__all__ = [
    "LISTEN_HOST",
    "RuntimeAnimator",
    "RuntimePlan",
    "SoulstoneRuntimeAdapter",
    "SoulstoneRuntimePlanner",
]
