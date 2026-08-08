# White-box access to Dispatcher._resolve_spec for the filter matrix.
# pyright: reportPrivateUsage=false
from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass, field
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from lychd.domain.animation.capabilities import (
    CapabilityGrant,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
    GrantLease,
    SourceKind,
)
from lychd.domain.animation.errors import CapabilityUnavailable
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.animation.schemas.generation import GenerationProfile
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.leases import LeaseLedger


def _stub_connector() -> SimpleNamespace:
    return SimpleNamespace(link=Link(up=False, activatable=True, estimated_ready_ms=2000))


@dataclass
class StubRuntime:
    id: str
    connector: SimpleNamespace = field(default_factory=_stub_connector)


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

    async def refresh_capability_state(self, key: str) -> CapabilityState | None:
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
    modalities_in: list[str] | None = None,
    supports_tools: bool | None = None,
) -> CapabilitySpec:
    return CapabilitySpec(
        key=key,
        animator_name=animator_name,
        runtime="llamacpp",
        source_kind=SourceKind.SOULSTONE,
        family=family,
        model_id=key.rsplit(":", maxsplit=1)[-1],
        modalities_in=modalities_in or [],
        supports_tools=supports_tools,
        is_dynamic=lifecycle_mode == "dynamic_soft",
        concurrency=concurrency or ConcurrencyIntent(),
    )


def _state(
    spec: CapabilitySpec,
    *,
    is_static: bool = True,
    is_active: bool = True,
    warm: bool = True,
) -> CapabilityState:
    if warm:
        phase = CapabilityPhase.WARM
    elif is_active:
        phase = CapabilityPhase.WARMING
    else:
        phase = CapabilityPhase.COLD
    return CapabilityState(
        capability_key=spec.key,
        is_dynamic=not is_static,
        phase=phase,
        health="ok" if warm else "down",
        active_model_id=spec.model_id if is_active else None,
        loaded_model_ids=[spec.model_id] if is_active else [],
    )


def _dispatcher(
    specs: list[CapabilitySpec],
    states: list[CapabilityState],
    runtimes: dict[str, StubRuntime],
) -> Dispatcher:
    return Dispatcher(
        registry=StubRegistry(specs, states, runtimes),  # pyright: ignore[reportArgumentType]
        leases=LeaseLedger(),
    )


def test_resolve_intent_prefers_warm_capability() -> None:
    cold = _spec(key="router:chat:router-main", animator_name="router", lifecycle_mode="dynamic_soft")
    warm = _spec(key="portal:chat:gpt-5", animator_name="portal", lifecycle_mode="static")
    dispatcher = _dispatcher(
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

    assert dispatcher.resolve_intent("reasoning") == warm


def test_resolve_intent_prefers_open_candidate_over_draining_warm_candidate() -> None:
    """A drain barrier removes its animator from new-work preference immediately."""
    draining = _spec(key="a:chat:draining", animator_name="a")
    open_candidate = _spec(key="b:chat:open", animator_name="b")
    leases = LeaseLedger()
    registry = StubRegistry(
        [draining, open_candidate],
        [_state(draining), _state(open_candidate)],
        {"a": StubRuntime(id="a"), "b": StubRuntime(id="b")},
    )
    dispatcher = Dispatcher(registry=registry, leases=leases)  # pyright: ignore[reportArgumentType]
    leases.begin_drain(["a"])

    assert dispatcher.resolve_intent("chat") == open_candidate


def test_resolve_spec_pins_model_name() -> None:
    qwen = _spec(key="local:chat:qwen", animator_name="local")
    llama = _spec(key="local:chat:llama", animator_name="local")
    dispatcher = _dispatcher(
        [qwen, llama],
        [_state(qwen), _state(llama)],
        {"local": StubRuntime(id="local")},
    )

    resolved = dispatcher._resolve_spec("chat", model_name="llama", require_modalities=())

    assert resolved == llama


def test_resolve_spec_require_modalities_excludes_text_only() -> None:
    text_only = _spec(key="local:chat:qwen", animator_name="local", modalities_in=["text"])
    dispatcher = _dispatcher([text_only], [_state(text_only)], {"local": StubRuntime(id="local")})

    with pytest.raises(CapabilityUnavailable):
        dispatcher._resolve_spec("chat", model_name=None, require_modalities=("image",))


def test_resolve_spec_requires_explicit_tool_support_when_requested() -> None:
    unspecified = _spec(key="a:chat:unspecified", animator_name="a", supports_tools=None)
    unsupported = _spec(key="b:chat:unsupported", animator_name="b", supports_tools=False)
    supported = _spec(key="z:chat:supported", animator_name="z", supports_tools=True)
    dispatcher = _dispatcher(
        [unspecified, unsupported, supported],
        [_state(unspecified), _state(unsupported), _state(supported)],
        {
            "a": StubRuntime(id="a"),
            "b": StubRuntime(id="b"),
            "z": StubRuntime(id="z"),
        },
    )

    resolved = dispatcher._resolve_spec(
        "chat",
        model_name=None,
        require_modalities=(),
        requires_tools=True,
    )

    assert resolved is supported


def test_resolve_spec_no_candidate_raises_capability_unavailable() -> None:
    dispatcher = _dispatcher([], [], {})

    with pytest.raises(CapabilityUnavailable):
        dispatcher._resolve_spec("chat", model_name=None, require_modalities=())


def _grant(*, generation: GenerationProfile) -> CapabilityGrant:
    spec = _spec(key="local-chat:chat:qwen")
    return CapabilityGrant(
        spec=spec,
        state=_state(spec),
        lease=GrantLease(grant_id="grant-1", holder="run:r1", issued_at=datetime.now(UTC)),
        generation=generation,
        model=None,
    )


def test_capability_grant_is_frozen() -> None:
    grant = _grant(generation=GenerationProfile())
    with pytest.raises(FrozenInstanceError):
        grant.model = object()  # type: ignore[misc]


def test_capability_grant_model_settings_reflects_generation() -> None:
    grant = _grant(generation=GenerationProfile(max_tokens=256))
    settings = grant.model_settings()

    assert settings is not None
    assert settings.get("max_tokens") == 256


def test_capability_grant_model_settings_none_for_empty_profile() -> None:
    assert _grant(generation=GenerationProfile()).model_settings() is None
