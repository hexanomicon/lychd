from __future__ import annotations

from dataclasses import dataclass

import pytest

from lychd.domain.animation.capabilities import CapabilitySpec, CapabilityState
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.cortex.dispatcher import Dispatcher, HardwareTransitionRequired


@dataclass
class StubRuntime:
    id: str


class StubRegistry:
    def __init__(
        self,
        specs: list[CapabilitySpec],
        states: list[CapabilityState],
        runtimes: dict[str, StubRuntime],
    ) -> None:
        self._specs = {spec.key: spec for spec in specs}
        self._states = {state.capability_key: state for state in states}
        self._runtimes = runtimes
        self.bound_model: object | None = object()
        self.bound_toolsets: tuple[object, ...] = ()

    def list_capabilities(self) -> list[CapabilitySpec]:
        return list(self._specs.values())

    def get_capability(self, key: str) -> CapabilitySpec | None:
        return self._specs.get(key)

    def get_capability_state(self, key: str) -> CapabilityState | None:
        return self._states.get(key)

    def refresh_capability_state(self, key: str) -> CapabilityState | None:
        return self._states.get(key)

    def get_runtime(self, name: str) -> StubRuntime | None:
        return self._runtimes.get(name)

    def bind_model(self, _name: str, *, model_id: str | None = None) -> object | None:
        assert model_id is not None
        return self.bound_model

    def bind_toolsets(self, _name: str) -> tuple[object, ...]:
        return self.bound_toolsets


def _spec(
    *,
    key: str,
    family: CapabilityFamily = CapabilityFamily.CHAT,
    animator_name: str = "local-chat",
    lifecycle_mode: str = "static",
    concurrency: ConcurrencyIntent | None = None,
) -> CapabilitySpec:
    return CapabilitySpec(
        key=key,
        animator_name=animator_name,
        runtime="llamacpp",
        source_kind="soulstone",
        family=family,
        model_id=key.rsplit(":", maxsplit=1)[-1],
        lifecycle_mode=lifecycle_mode,
        concurrency=concurrency or ConcurrencyIntent(),
    )


def _state(
    spec: CapabilitySpec,
    *,
    is_static: bool = True,
    is_active: bool = True,
    warm: bool = True,
) -> CapabilityState:
    return CapabilityState(
        capability_key=spec.key,
        is_static=is_static,
        is_active=is_active,
        is_available=True,
        warm=warm,
        health="ok" if warm else "down",
        active_model_id=spec.model_id if is_active else None,
        loaded_model_ids=[spec.model_id] if is_active else [],
    )


def test_request_capability_grant_returns_capability_grant_for_warm_capability() -> None:
    spec = _spec(key="local-chat:chat:qwen")
    state = _state(spec)
    runtime = StubRuntime(id="local-chat")
    registry = StubRegistry([spec], [state], {"local-chat": runtime})
    registry.bound_toolsets = ("toolset",)

    grant = Dispatcher(registry=registry).request_capability_grant(spec.key)

    assert grant.spec == spec
    assert grant.state == state
    assert grant.animator == runtime
    assert grant.toolsets == ("toolset",)


def test_request_capability_grant_raises_transition_for_cold_dynamic_capability() -> None:
    spec = _spec(key="router:vision:router-vision", animator_name="router", lifecycle_mode="dynamic_soft")
    state = _state(spec, is_static=False, is_active=False, warm=False)
    runtime = StubRuntime(id="router")
    dispatcher = Dispatcher(registry=StubRegistry([spec], [state], {"router": runtime}))

    with pytest.raises(HardwareTransitionRequired) as exc_info:
        dispatcher.request_capability_grant(spec.key)

    assert exc_info.value.spec == spec
    assert exc_info.value.state == state
    assert exc_info.value.animator == runtime


def test_resolve_intent_prefers_warm_capability() -> None:
    cold = _spec(key="router:chat:router-main", animator_name="router", lifecycle_mode="dynamic_soft")
    warm = _spec(key="portal:chat:gpt-5", animator_name="portal", lifecycle_mode="static")
    registry = StubRegistry(
        [cold, warm],
        [
            _state(cold, is_static=False, is_active=False, warm=False),
            _state(warm),
        ],
        {
            "router": StubRuntime(id="router"),
            "portal": StubRuntime(id="portal"),
        },
    )

    resolved = Dispatcher(registry=registry).resolve_intent("reasoning")

    assert resolved == warm
