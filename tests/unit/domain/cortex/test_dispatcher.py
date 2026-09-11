from __future__ import annotations

import asyncio
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


class ObservedRegistry(StubRegistry):
    """Separate cached ranking evidence from the next live observation."""

    def __init__(self, specs: list[CapabilitySpec], states: list[CapabilityState]) -> None:
        super().__init__(specs, states)
        self.observed = {state.capability_key: state for state in states}
        self.calls: list[tuple[str, str]] = []

    async def refresh_capability_state(self, key: str) -> CapabilityState | None:
        self.calls.append(("refresh", key))
        self._states[key] = self.observed[key]
        return self._states[key]

    async def issue_grant(self, key: str, *, holder: str) -> CapabilityGrant:
        self.calls.append(("issue", key))
        return await super().issue_grant(key, holder=holder)


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
async def test_later_exact_dispatch_can_recover_a_previously_observed_error() -> None:
    spec = _spec(key="local:chat:qwen", animator_name="local")
    registry = ObservedRegistry([spec], [_state(spec)])
    registry.observed[spec.key] = CapabilityState(
        capability_key=spec.key, phase=CapabilityPhase.ERROR, reason="temporary malformed inventory"
    )
    leases = LeaseLedger()
    dispatcher = Dispatcher(registry=registry, leases=leases)  # pyright: ignore[reportArgumentType]

    with pytest.raises(CapabilityUnavailable, match="temporary malformed inventory"):
        async with dispatcher.lease_grant(family="chat", capability_key=spec.key, run_id="first"):
            pytest.fail("a fresh error cannot issue a grant or request hardware")
    assert registry.calls == [("refresh", spec.key)]
    assert leases.active() == []

    registry.observed[spec.key] = _state(spec)
    async with dispatcher.lease_grant(family="chat", capability_key=spec.key, run_id="recovered") as grant:
        assert grant.spec == spec
        assert len(leases.active()) == 1

    assert registry.calls == [("refresh", spec.key), ("refresh", spec.key), ("issue", spec.key)]
    assert leases.active() == []


@pytest.mark.asyncio
async def test_cached_error_gets_one_fresh_probe_without_grant_or_hardware_on_persistent_error() -> None:
    spec = _spec(key="local:chat:qwen", animator_name="local")
    state = CapabilityState(capability_key=spec.key, phase=CapabilityPhase.ERROR, reason="still unavailable")
    registry = ObservedRegistry([spec], [state])
    leases = LeaseLedger()
    dispatcher = Dispatcher(registry=registry, leases=leases)  # pyright: ignore[reportArgumentType]

    with pytest.raises(CapabilityUnavailable, match="still unavailable"):
        async with dispatcher.lease_grant(family="chat", run_id="persistent"):
            pytest.fail("a fresh error cannot yield a grant")

    assert registry.calls == [("refresh", spec.key)]
    assert leases.active() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", [phase for phase in CapabilityPhase if phase is not CapabilityPhase.ERROR])
async def test_cached_error_ranks_behind_every_other_open_candidate(phase: CapabilityPhase) -> None:
    error = _spec(key="a:chat:error", animator_name="a")
    preferred = _spec(key="z:chat:preferred", animator_name="z")
    registry = ObservedRegistry(
        [error, preferred],
        [
            CapabilityState(capability_key=error.key, phase=CapabilityPhase.ERROR),
            CapabilityState(capability_key=preferred.key, phase=phase),
        ],
    )
    registry.observed[preferred.key] = _state(preferred)
    dispatcher = Dispatcher(registry=registry, leases=LeaseLedger())  # pyright: ignore[reportArgumentType]

    async with dispatcher.lease_grant(family="chat", run_id="preferred") as grant:
        assert grant.spec == preferred

    assert registry.calls == [("refresh", preferred.key), ("issue", preferred.key)]


@pytest.mark.asyncio
async def test_open_cached_error_still_ranks_before_a_draining_warm_route() -> None:
    draining = _spec(key="a:chat:draining", animator_name="a")
    recovered = _spec(key="z:chat:recovered", animator_name="z")
    registry = ObservedRegistry(
        [draining, recovered],
        [_state(draining), CapabilityState(capability_key=recovered.key, phase=CapabilityPhase.ERROR)],
    )
    registry.observed[recovered.key] = _state(recovered)
    leases = LeaseLedger()
    leases.begin_drain([draining.animator_name])
    dispatcher = Dispatcher(registry=registry, leases=leases)  # pyright: ignore[reportArgumentType]

    async with dispatcher.lease_grant(family="chat", run_id="open-recovery") as grant:
        assert grant.spec == recovered

    assert registry.calls == [("refresh", recovered.key), ("issue", recovered.key)]


@pytest.mark.asyncio
async def test_selected_fresh_error_does_not_retry_a_healthy_alternative() -> None:
    selected = _spec(key="a:chat:selected", animator_name="a")
    alternative = _spec(key="z:chat:alternative", animator_name="z")
    registry = ObservedRegistry([selected, alternative], [_state(selected), _state(alternative)])
    registry.observed[selected.key] = CapabilityState(
        capability_key=selected.key, phase=CapabilityPhase.ERROR, reason="selected route failed"
    )
    leases = LeaseLedger()
    dispatcher = Dispatcher(registry=registry, leases=leases)  # pyright: ignore[reportArgumentType]

    with pytest.raises(CapabilityUnavailable, match="selected route failed"):
        async with dispatcher.lease_grant(family="chat", run_id="no-fallback"):
            pytest.fail("selection cannot silently change after a fresh failure")

    assert registry.calls == [("refresh", selected.key)]
    assert leases.active() == []


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


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", ["openai-compatible", "ollama"])
@pytest.mark.parametrize("outcome", ["success", "failure", "cancelled"])
async def test_grant_closes_owned_model_client_before_releasing_lease(
    monkeypatch: pytest.MonkeyPatch, provider_name: str, outcome: str
) -> None:
    from pydantic_ai.models.openai import OpenAIChatModel

    from lychd.domain.animation.links import Link
    from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector

    spec = _spec(key="local-chat:chat:qwen")
    model = OpenAICompatibleConnector(
        link=Link(up=True), base_url="http://runtime.test/v1", default_model_id="qwen", provider_name=provider_name
    ).get_model()
    assert isinstance(model, OpenAIChatModel)
    registry = StubRegistry([spec], [_state(spec)])
    registry.bound_model = model
    leases = LeaseLedger()
    original_release = leases.release

    def release(grant_id: str) -> None:
        assert model.client.is_closed()
        original_release(grant_id)

    monkeypatch.setattr(leases, "release", release)
    dispatcher = Dispatcher(registry=registry, leases=leases)  # pyright: ignore[reportArgumentType]

    async def consume() -> None:
        async with dispatcher.lease_grant(family="chat", run_id="client-lifetime"):
            assert not model.client.is_closed()
            assert len(leases.active()) == 1
            if outcome == "failure":
                message = "consumer failed"
                raise RuntimeError(message)
            if outcome == "cancelled":
                raise asyncio.CancelledError

    if outcome == "success":
        await consume()
    else:
        with pytest.raises(RuntimeError if outcome == "failure" else asyncio.CancelledError):
            await consume()
    assert model.client.is_closed()
    assert leases.active() == []


@pytest.mark.asyncio
async def test_grant_retains_lease_until_model_cleanup_survives_repeated_cancellation() -> None:
    closing = asyncio.Event()
    finish_close = asyncio.Event()
    closed = asyncio.Event()

    class ClosingModel(TestModel):
        async def __aexit__(self, *_args: object) -> None:
            closing.set()
            await finish_close.wait()
            closed.set()

    spec = _spec(key="local-chat:chat:qwen")
    registry = StubRegistry([spec], [_state(spec)])
    registry.bound_model = ClosingModel()
    leases = LeaseLedger()
    dispatcher = Dispatcher(registry=registry, leases=leases)  # pyright: ignore[reportArgumentType]

    async def consume() -> None:
        async with dispatcher.lease_grant(family="chat", run_id="closing"):
            pass

    task = asyncio.create_task(consume())
    await closing.wait()
    for _ in range(2):
        task.cancel()
        await asyncio.sleep(0)
    assert len(leases.active()) == 1
    assert not task.done()
    finish_close.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed.is_set()
    assert leases.active() == []


@pytest.mark.asyncio
async def test_admission_race_closes_model_without_issuing_lease(monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic_ai.models.openai import OpenAIChatModel

    from lychd.domain.animation.errors import HardwareTransitionRequired
    from lychd.domain.animation.links import Link
    from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector

    spec = _spec(key="local-chat:chat:qwen")
    model = OpenAICompatibleConnector(
        link=Link(up=True), base_url="http://runtime.test/v1", default_model_id="qwen"
    ).get_model()
    assert isinstance(model, OpenAIChatModel)
    registry = StubRegistry([spec], [_state(spec)])
    registry.bound_model = model
    leases = LeaseLedger()
    original_issue = registry.issue_grant

    async def close_admission(key: str, *, holder: str) -> CapabilityGrant:
        grant = await original_issue(key, holder=holder)
        leases.begin_drain([spec.animator_name])
        return grant

    monkeypatch.setattr(registry, "issue_grant", close_admission)
    dispatcher = Dispatcher(registry=registry, leases=leases)  # pyright: ignore[reportArgumentType]
    with pytest.raises(HardwareTransitionRequired):
        async with dispatcher.lease_grant(family="chat", run_id="late-drain"):
            pytest.fail("closed admission must refuse the grant")
    assert model.client.is_closed()
    assert leases.active() == []
