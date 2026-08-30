"""The A3 §2 phase decision table + lease lifecycle (wave3 keel K3).

Drives ``Dispatcher._grant_for_spec`` through every observed-phase row against a
controllable fake registry that honours the ``CapabilityRegistry`` reads and grant issue surface.
The HTR row asserts the truth seam: no lease is registered when a transition is
required (a parked run holds no lease).
"""
# The fake registry deliberately implements only the grant surface the Dispatcher
# touches; it is not the full CapabilityRegistry protocol. Its methods mirror the
# protocol signatures, so several parameters are intentionally unused.
# ruff: noqa: ARG002
# pyright: reportArgumentType=false

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import aclosing
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import pytest

from lychd.domain.animation.capabilities import (
    CapabilityGrant,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
    GrantLease,
)
from lychd.domain.animation.errors import CapabilityUnavailable
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.cortex.dispatcher import Dispatcher, HardwareTransitionRequired
from lychd.domain.cortex.events import InProcessEventBus, RunEvent, RunEventKind
from lychd.domain.cortex.execution_context import bind_occurrence, reset_occurrence
from lychd.domain.cortex.leases import LeaseAdmissionClosed, LeaseLedger

_KEY = "router:chat:main"


class _BoomError(RuntimeError):
    """Sentinel raised inside a lease CM body to exercise release-on-exception."""


class _FailingRunEvents:
    """Observer double that fails after lease acquisition."""

    def emitter(self, run_id: str) -> _FailingRunEvents:
        return self

    def dispatch(self, capability_key: str, **metadata: str) -> None:
        raise _BoomError


class FakeRegistry:
    """Controllable registry honouring the grant surface for the decision table."""

    def __init__(
        self,
        *,
        phase: CapabilityPhase,
        reason: str | None = None,
        refresh_phase: CapabilityPhase | None = None,
        dedicated: bool = True,
    ) -> None:
        self.spec = CapabilitySpec(
            key=_KEY,
            animator_name="router",
            runtime="llamacpp",
            source_kind="soulstone",
            family=CapabilityFamily.CHAT,
            model_id="main",
            is_dynamic=True,
            concurrency=ConcurrencyIntent(dedicated=dedicated),
            modalities_in=("text",),
        )
        self.state = CapabilityState(
            capability_key=_KEY,
            phase=phase,
            reason=reason,
        )
        self._refresh_phase = refresh_phase
        self.calls: list[str] = []

    def list_capabilities(self) -> list[CapabilitySpec]:
        return [self.spec]

    def get_capability(self, key: str) -> CapabilitySpec | None:
        return self.spec if key == _KEY else None

    def get_capability_state(self, key: str) -> CapabilityState | None:
        return self.state if key == _KEY else None

    async def refresh_capability_state(self, key: str) -> CapabilityState | None:
        self.calls.append("refresh")
        if self._refresh_phase is not None:
            self.state = self.state.model_copy(update={"phase": self._refresh_phase})
        return self.state

    async def issue_grant(self, key: str, *, holder: str, scope: str = "step") -> CapabilityGrant:
        self.calls.append("issue_grant")
        return CapabilityGrant(
            spec=self.spec,
            state=self.state,
            lease=GrantLease(grant_id=uuid4().hex, holder=holder, issued_at=datetime.now(UTC)),
            model=object(),
            toolsets=(),
        )


class GrantRaceRegistry(FakeRegistry):
    """Pause the first grant issue so a drain can close admission in that window."""

    def __init__(self) -> None:
        super().__init__(phase=CapabilityPhase.WARM)
        self.issue_started = asyncio.Event()
        self.finish_issue = asyncio.Event()

    async def issue_grant(self, key: str, *, holder: str, scope: str = "step") -> CapabilityGrant:
        self.issue_started.set()
        await self.finish_issue.wait()
        return await super().issue_grant(key, holder=holder, scope=scope)


def _dispatcher(registry: FakeRegistry) -> tuple[Dispatcher, LeaseLedger]:
    leases = LeaseLedger()
    return Dispatcher(registry=registry, leases=leases), leases


@pytest.mark.asyncio
async def test_warm_row_issues_grant_directly() -> None:
    registry = FakeRegistry(phase=CapabilityPhase.WARM)
    dispatcher, leases = _dispatcher(registry)

    async with dispatcher.lease_grant(family=CapabilityFamily.CHAT, model_name="main", run_id="1") as grant:
        assert grant.spec.key == _KEY
        assert leases.active(animator_name="router")  # held inside the CM

    assert "issue_grant" in registry.calls
    assert "activate" not in registry.calls
    assert leases.active() == []  # released on exit


@pytest.mark.asyncio
async def test_graph_dispatch_emits_post_acquisition_occurrence_and_grant_identity() -> None:
    """Only an admitted lease becomes a Dispatcher selection observation."""
    registry = FakeRegistry(phase=CapabilityPhase.WARM)
    leases = LeaseLedger()
    events = InProcessEventBus()
    dispatcher = Dispatcher(registry=registry, leases=leases, events=events)
    occurrence_token = bind_occurrence("occurrence-1")
    try:
        async with dispatcher.lease_grant(
            family=CapabilityFamily.CHAT,
            run_id="run-1",
        ) as grant:
            assert [lease.grant_id for lease in leases.active()] == [grant.lease.grant_id]
            stream = cast("AsyncGenerator[RunEvent]", events.subscribe("run-1"))
            async with aclosing(stream):
                event = await anext(stream)
    finally:
        reset_occurrence(occurrence_token)

    assert event.kind is RunEventKind.DISPATCH
    assert event.data == _KEY
    assert event.meta == {
        "animator": "router",
        "family": "chat",
        "model_id": "main",
        "phase": "warm",
        "occurrence_id": "occurrence-1",
        "grant_id": grant.lease.grant_id,
    }
    assert leases.active() == []


@pytest.mark.asyncio
async def test_dispatch_observer_failure_releases_acquired_lease() -> None:
    registry = FakeRegistry(phase=CapabilityPhase.WARM)
    leases = LeaseLedger()
    dispatcher = Dispatcher(
        registry=registry,
        leases=leases,
        events=cast("Any", _FailingRunEvents()),
    )

    with pytest.raises(_BoomError):
        async with dispatcher.lease_grant(
            family=CapabilityFamily.CHAT,
            run_id="run-observer-failure",
        ):
            pytest.fail("a failed observation must not enter the lease body")

    assert leases.active() == []


@pytest.mark.asyncio
async def test_drain_racing_grant_issue_becomes_hardware_transition() -> None:
    """A grant that loses admission during issue parks; it never leaks or fails generically."""
    registry = GrantRaceRegistry()
    dispatcher, leases = _dispatcher(registry)

    async def _lease() -> None:
        async with dispatcher.lease_grant(
            family=CapabilityFamily.CHAT,
            model_name="main",
            run_id="race",
        ):
            pytest.fail("a grant must not enter after its animator starts draining")

    lease_task = asyncio.create_task(_lease())
    await registry.issue_started.wait()
    leases.begin_drain(["router"])
    registry.finish_issue.set()

    with pytest.raises(HardwareTransitionRequired) as exc_info:
        await lease_task

    assert exc_info.value.capability_key == _KEY
    assert isinstance(exc_info.value.__cause__, LeaseAdmissionClosed)
    assert leases.active() == []


@pytest.mark.parametrize(
    "phase",
    [CapabilityPhase.COLD, CapabilityPhase.ACTIVATABLE, CapabilityPhase.WARMING],
)
@pytest.mark.asyncio
async def test_owned_non_warm_row_requires_transition_without_mutation(
    phase: CapabilityPhase,
) -> None:
    registry = FakeRegistry(phase=phase)
    dispatcher, leases = _dispatcher(registry)

    with pytest.raises(HardwareTransitionRequired) as exc_info:
        async with dispatcher.lease_grant(family=CapabilityFamily.CHAT, model_name="main", run_id="1"):
            pass

    assert exc_info.value.capability_key == _KEY
    assert registry.calls == ["refresh"]
    assert leases.active() == []


@pytest.mark.asyncio
async def test_shared_non_warm_row_raises_capability_unavailable() -> None:
    registry = FakeRegistry(phase=CapabilityPhase.COLD, dedicated=False)
    dispatcher, _ = _dispatcher(registry)

    with pytest.raises(CapabilityUnavailable, match="not lifecycle-managed"):
        async with dispatcher.lease_grant(family=CapabilityFamily.CHAT, model_name="main", run_id="1"):
            pass


@pytest.mark.asyncio
async def test_error_row_raises_capability_unavailable() -> None:
    registry = FakeRegistry(phase=CapabilityPhase.ERROR, reason="model crashed")
    dispatcher, _ = _dispatcher(registry)

    with pytest.raises(CapabilityUnavailable):
        async with dispatcher.lease_grant(family=CapabilityFamily.CHAT, model_name="main", run_id="1"):
            pass


@pytest.mark.asyncio
async def test_unknown_row_refreshes_once_then_unavailable() -> None:
    registry = FakeRegistry(phase=CapabilityPhase.UNKNOWN, refresh_phase=CapabilityPhase.UNKNOWN)
    dispatcher, _ = _dispatcher(registry)

    with pytest.raises(CapabilityUnavailable):
        async with dispatcher.lease_grant(family=CapabilityFamily.CHAT, model_name="main", run_id="1"):
            pass

    assert registry.calls.count("refresh") == 1
    assert "activate" not in registry.calls  # stayed unknown, never activated


@pytest.mark.asyncio
async def test_lease_released_after_exception_inside_cm_body() -> None:
    registry = FakeRegistry(phase=CapabilityPhase.WARM)
    dispatcher, leases = _dispatcher(registry)

    async def _explode() -> None:
        async with dispatcher.lease_grant(family=CapabilityFamily.CHAT, model_name="main", run_id="1"):
            assert leases.active(animator_name="router")
            raise _BoomError

    with pytest.raises(_BoomError):
        await _explode()

    assert leases.active() == []  # released even on a mid-body exception
