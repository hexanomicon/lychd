from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

import structlog

from lychd.config.runes import RuneConfig
from lychd.domain.animation.animators import Animator
from lychd.domain.animation.connectors import Connector, ModelConnector
from lychd.domain.animation.schemas import ModelInfo, PortalConfig, SoulstoneConfig
from lychd.domain.animation.services.binder import AnimatorBinder
from lychd.domain.animation.services.loader import AnimatorLoader

if TYPE_CHECKING:
    from pydantic_ai.models import Model
    from pydantic_ai.toolsets import AbstractToolset

    from lychd.domain.animation.services.adapters.contracts import RuntimePlan
    from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
    from lychd.extensions.builtin.animator.llamacpp import LlamaCppControlPlane, LlamaCppLifecycle


type RuntimeAnimator = Animator[Connector, RuneConfig]
type AnimatorRune = SoulstoneConfig | PortalConfig
type AnimatorFactory = Callable[[AnimatorRune], RuntimeAnimator | None]

logger = structlog.get_logger()


class AnimatorRegistry:
    """Registry for animation rune configs and resolved runtime animators.

    Stores two distinct layers:
    - rune declarations (``SoulstoneConfig`` / ``PortalConfig``)
    - resolved runtime animators (``Animator`` handles with connectors/links)

    Runtime animator creation is delegated to factories. By default, the registry
    wires in ``RuntimeAdapterRegistry.runtime_factory`` so built-in Soulstone and
    portal runtimes resolve without extra setup.
    """

    def __init__(
        self,
        loader: AnimatorLoader | None = None,
        *,
        binder: AnimatorBinder | None = None,
        runtime_factories: Sequence[AnimatorFactory] | None = None,
        runtime_adapters: RuntimeAdapterRegistry | None = None,
        llamacpp_control: LlamaCppControlPlane | None = None,
    ) -> None:
        """Initialize loader/binder plus runtime factories and optional llama.cpp control."""
        self._loader = loader or AnimatorLoader()
        self._binder = binder or AnimatorBinder()

        if runtime_adapters is None:
            from lychd.domain.animation.services.adapters.registry import (
                RuntimeAdapterRegistry as _RuntimeAdapterRegistry,
            )

            runtime_adapters = _RuntimeAdapterRegistry()
        self._runtime_adapters = runtime_adapters

        if runtime_factories is None:
            self._runtime_factories: list[AnimatorFactory] = [self._runtime_adapters.runtime_factory]
        else:
            self._runtime_factories = list(runtime_factories)

        self._llamacpp_control = llamacpp_control

        self._soulstones: dict[str, SoulstoneConfig] = {}
        self._portals: dict[str, PortalConfig] = {}
        self._groups: dict[str, list[SoulstoneConfig]] = {}
        self._animators: dict[str, RuntimeAnimator] = {}
        self._loaded = False

    def register_runtime_factory(self, factory: AnimatorFactory) -> None:
        """Register a runtime animator factory used during `load()`."""
        self._runtime_factories.append(factory)

    def register_runtime(self, animator: RuntimeAnimator) -> None:
        """Register/replace a runtime animator handle directly by id."""
        self._animators[animator.id] = animator

    def load(self) -> None:
        """Load rune configs and build runtime animators via registered factories."""
        raw_soulstones, raw_portals = self._loader.load_all()

        new_soulstones = {stone.name: stone for stone in raw_soulstones}
        new_portals = {portal.name: portal for portal in raw_portals}
        new_groups: dict[str, list[SoulstoneConfig]] = {}
        for stone in raw_soulstones:
            for group in stone.groups:
                new_groups.setdefault(group, []).append(stone)

        new_animators: dict[str, RuntimeAnimator] = {}
        for rune in [*raw_soulstones, *raw_portals]:
            resolved = False
            for factory in self._runtime_factories:
                runtime = factory(rune)
                if runtime is None:
                    continue
                new_animators[runtime.id] = runtime
                resolved = True
                break
            if not resolved:
                logger.warning(
                    "runtime_unresolved",
                    rune_name=rune.name,
                    rune_type=type(rune).__name__,
                )

        self._soulstones = new_soulstones
        self._portals = new_portals
        self._groups = new_groups
        self._animators = new_animators
        self._loaded = True

        logger.info(
            "registry_loaded",
            soulstones=len(self._soulstones),
            portals=len(self._portals),
            groups=list(self._groups.keys()),
            runtime_animators=len(self._animators),
        )

    def ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def get_runtime(self, name: str) -> RuntimeAnimator | None:
        self.ensure_loaded()
        return self._animators.get(name)

    def get(self, name: str) -> RuntimeAnimator | None:
        return self.get_runtime(name)

    def get_soulstone_rune(self, name: str) -> SoulstoneConfig | None:
        self.ensure_loaded()
        return self._soulstones.get(name)

    def get_portal_rune(self, name: str) -> PortalConfig | None:
        self.ensure_loaded()
        return self._portals.get(name)

    def get_group(self, group_name: str) -> Sequence[SoulstoneConfig]:
        self.ensure_loaded()
        return self._groups.get(group_name, [])

    def list_runtime_animators(self) -> list[RuntimeAnimator]:
        self.ensure_loaded()
        return list(self._animators.values())

    def list_runes(self) -> list[AnimatorRune]:
        self.ensure_loaded()
        return [*self._soulstones.values(), *self._portals.values()]

    def list_models(self, name: str) -> Sequence[ModelInfo]:
        animator = self.get_runtime(name)
        if animator is None:
            return ()
        connector = animator.connector
        if not isinstance(connector, ModelConnector):
            return ()
        return tuple(connector.list_models())

    def is_ready(self, name: str) -> bool:
        animator = self.get_runtime(name)
        if animator is None:
            return False
        return animator.connector.link.up

    def bind_model(self, name: str, *, model_id: str | None = None) -> Model | None:
        animator = self.get_runtime(name)
        if animator is None:
            return None
        return self._binder.bind_model(animator, model_id=model_id)

    def bind_toolsets(self, name: str) -> Sequence[AbstractToolset]:
        animator = self.get_runtime(name)
        if animator is None:
            return ()
        return self._binder.bind_toolsets(animator)

    def bind_toolset(self, name: str) -> AbstractToolset | None:
        animator = self.get_runtime(name)
        if animator is None:
            return None
        return self._binder.bind_toolset(animator)

    def prepare(self, name: str) -> RuntimePlan | None:
        """Return a container runtime plan for a Soulstone rune, if present."""
        soulstone = self.get_soulstone_rune(name)
        if soulstone is None:
            return None
        return self._runtime_adapters.plan(soulstone)

    def inspect_lifecycle(self, name: str) -> LlamaCppLifecycle | None:
        """Inspect llama.cpp lifecycle for a runtime animator when applicable."""
        animator = self.get_runtime(name)
        if animator is None:
            return None

        if getattr(animator.connector, "kind", None) != "llamacpp":
            return None

        control = self._get_llamacpp_control()
        return control.inspect_animator(animator)

    def _get_llamacpp_control(self) -> LlamaCppControlPlane:
        if self._llamacpp_control is None:
            from lychd.extensions.builtin.animator.llamacpp import LlamaCppControlPlane

            self._llamacpp_control = LlamaCppControlPlane()
        return self._llamacpp_control
