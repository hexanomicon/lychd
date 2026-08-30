from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic_ai.models import Model
from pydantic_ai.models.test import TestModel

from lychd.domain.animation.capabilities import (
    CapabilityGrant,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
    GrantLease,
    SourceKind,
)
from lychd.domain.animation.errors import CapabilityUnavailable
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.animation.schemas.generation import GenerationProfile
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.leases import LeaseLedger


class StubRegistry:
    def __init__(
        self,
        specs: list[CapabilitySpec],
        states: list[CapabilityState],
    ) -> None:
        self._specs = {spec.key: spec for spec in specs}
        self._states = {state.capability_key: state for state in states}
        self.bound_model: Model | None = TestModel()
        self.bound_toolsets: tuple[object, ...] = ()

    def list_capabilities(self) -> list[CapabilitySpec]:
        return list(self._specs.values())

    def get_capability(self, key: str) -> CapabilitySpec | None:
        return self._specs.get(key)

    def get_capability_state(self, key: str) -> CapabilityState | None:
        return self._states.get(key)

    async def refresh_capability_state(self, key: str) -> CapabilityState | None:
        return self._states.get(key)

    def bind_model(self, _name: str, *, model_id: str | None = None) -> Model | None:
        assert model_id is not None
        return self.bound_model

    def bind_toolsets(self, _name: str) -> tuple[object, ...]:
        return self.bound_toolsets

    async def issue_grant(self, key: str, *, holder: str) -> CapabilityGrant:
        spec = self._specs[key]
        return CapabilityGrant(
            spec=spec,
            state=self._states[key],
            lease=GrantLease(grant_id=f"grant:{key}", holder=holder, issued_at=datetime.now(UTC)),
            model=self.bound_model,
        )


def _spec(
    *,
    key: str,
    family: CapabilityFamily = CapabilityFamily.CHAT,
    animator_name: str = "local-chat",
    lifecycle_mode: str = "static",
    concurrency: ConcurrencyIntent | None = None,
    modalities_in: tuple[str, ...] | None = None,
    supports_tools: bool | None = None,
    generation_profile: GenerationProfile | None = None,
) -> CapabilitySpec:
    return CapabilitySpec(
        key=key,
        animator_name=animator_name,
        runtime="llamacpp",
        source_kind=SourceKind.SOULSTONE,
        family=family,
        model_id=key.rsplit(":", maxsplit=1)[-1],
        modalities_in=modalities_in or (),
        supports_tools=supports_tools,
        generation_profile=generation_profile or GenerationProfile(),
        is_dynamic=lifecycle_mode == "dynamic_soft",
        concurrency=concurrency or ConcurrencyIntent(),
    )


def _state(
    spec: CapabilitySpec,
    *,
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
        phase=phase,
        health="ok" if warm else "down",
    )


def _dispatcher(
    specs: list[CapabilitySpec],
    states: list[CapabilityState],
) -> Dispatcher:
    return Dispatcher(
        registry=StubRegistry(specs, states),  # pyright: ignore[reportArgumentType]
        leases=LeaseLedger(),
    )


@pytest.mark.asyncio
async def test_dispatch_prefers_warm_capability() -> None:
    cold = _spec(key="router:chat:router-main", animator_name="router", lifecycle_mode="dynamic_soft")
    warm = _spec(key="portal:chat:gpt-5", animator_name="portal", lifecycle_mode="static")
    dispatcher = _dispatcher(
        [cold, warm],
        [
            _state(cold, is_active=False, warm=False),
            _state(warm),
        ],
    )

    async with dispatcher.lease_grant(family="reasoning", run_id="selection") as grant:
        assert grant.spec == warm


@pytest.mark.asyncio
async def test_dispatch_prefers_open_candidate_over_draining_warm_candidate() -> None:
    """A drain barrier removes its animator from new-work preference immediately."""
    draining = _spec(key="a:chat:draining", animator_name="a")
    open_candidate = _spec(key="b:chat:open", animator_name="b")
    leases = LeaseLedger()
    registry = StubRegistry(
        [draining, open_candidate],
        [_state(draining), _state(open_candidate)],
    )
    dispatcher = Dispatcher(registry=registry, leases=leases)  # pyright: ignore[reportArgumentType]
    leases.begin_drain(["a"])

    async with dispatcher.lease_grant(family="chat", run_id="selection") as grant:
        assert grant.spec == open_candidate


@pytest.mark.asyncio
async def test_dispatch_pins_model_name() -> None:
    qwen = _spec(key="local:chat:qwen", animator_name="local")
    llama = _spec(key="local:chat:llama", animator_name="local")
    dispatcher = _dispatcher(
        [qwen, llama],
        [_state(qwen), _state(llama)],
    )

    async with dispatcher.lease_grant(family="chat", model_name="llama", run_id="selection") as grant:
        assert grant.spec == llama


@pytest.mark.asyncio
async def test_dispatch_require_modalities_excludes_text_only() -> None:
    text_only = _spec(key="local:chat:qwen", animator_name="local", modalities_in=("text",))
    dispatcher = _dispatcher([text_only], [_state(text_only)])

    with pytest.raises(CapabilityUnavailable):
        async with dispatcher.lease_grant(
            family="chat",
            run_id="selection",
            require_modalities=("image",),
        ):
            pytest.fail("text-only capability must not be leased for image input")


@pytest.mark.asyncio
async def test_dispatch_requires_explicit_tool_support_when_requested() -> None:
    unspecified = _spec(key="a:chat:unspecified", animator_name="a", supports_tools=None)
    unsupported = _spec(key="b:chat:unsupported", animator_name="b", supports_tools=False)
    supported = _spec(key="z:chat:supported", animator_name="z", supports_tools=True)
    dispatcher = _dispatcher(
        [unspecified, unsupported, supported],
        [_state(unspecified), _state(unsupported), _state(supported)],
    )

    async with dispatcher.lease_grant(
        family="chat",
        run_id="selection",
        requires_tools=True,
    ) as grant:
        assert grant.spec == supported


@pytest.mark.asyncio
async def test_dispatch_no_candidate_raises_capability_unavailable() -> None:
    dispatcher = _dispatcher([], [])

    with pytest.raises(CapabilityUnavailable):
        async with dispatcher.lease_grant(family="chat", run_id="selection"):
            pytest.fail("an empty registry must not yield a grant")


def _grant(*, generation: GenerationProfile) -> CapabilityGrant:
    spec = _spec(key="local-chat:chat:qwen", generation_profile=generation)
    return CapabilityGrant(
        spec=spec,
        state=_state(spec),
        lease=GrantLease(grant_id="grant-1", holder="run:r1", issued_at=datetime.now(UTC)),
        model=None,
    )


def test_capability_grant_model_settings_reflects_generation() -> None:
    grant = _grant(generation=GenerationProfile(max_tokens=256, temperature=0.2, top_p=0.9))
    settings = grant.model_settings()

    assert settings == {"max_tokens": 256, "temperature": 0.2, "top_p": 0.9}
