"""The A3 §2 phase decision table + lease lifecycle (wave3 keel K3).

Drives ``Dispatcher._grant_for_spec`` through every observed-phase row against a
controllable fake registry that honours the ``CapabilityRegistry`` grant surface
(``issue_grant``/``activate_capability``/``await_warm``/``refresh_capability_state``).
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
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from lychd.domain.animation.capabilities import (
    ActivationResult,
    CapabilityGrant,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
    GrantLease,
)
from lychd.domain.animation.errors import CapabilityUnavailable
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.cortex.dispatcher import Dispatcher, HardwareTransitionRequired
from lychd.domain.cortex.leases import LeaseAdmissionClosed, LeaseLedger

_KEY = "router:chat:main"


class _BoomError(RuntimeError):
    """Sentinel raised inside a lease CM body to exercise release-on-exception."""


class FakeRegistry:
    """Controllable registry honouring the grant surface for the decision table."""

    def __init__(
        self,
        *,
        phase: CapabilityPhase,
        activatable: bool = True,
        activate_accepted: bool = True,
        await_warm_raises: Exception | None = None,
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
            modalities_in=["text"],
        )
        self.state = CapabilityState(
            capability_key=_KEY,
            is_dynamic=True,
            phase=phase,
            reason=reason,
        )
        self._link = Link(up=(phase is CapabilityPhase.WARM), activatable=activatable, estimated_ready_ms=1500)
        self._runtime = SimpleNamespace(id="router", connector=SimpleNamespace(link=self._link))
        self._activate_accepted = activate_accepted
        self._await_warm_raises = await_warm_raises
        self._refresh_phase = refresh_phase
        self.calls: list[str] = []

    def list_capabilities(self) -> list[CapabilitySpec]:
        return [self.spec]

    def get_capability(self, key: str) -> CapabilitySpec | None:
        return self.spec if key == _KEY else None

    def get_capability_state(self, key: str) -> CapabilityState | None:
        return self.state if key == _KEY else None

    def get_runtime(self, name: str) -> Any | None:
        return self._runtime if name == "router" else None

    async def refresh_capability_state(self, key: str) -> CapabilityState | None:
        self.calls.append("refresh")
        if self._refresh_phase is not None:
            self.state.phase = self._refresh_phase
        return self.state

    async def activate_capability(self, key: str) -> ActivationResult:
        self.calls.append("activate")
        if not self._activate_accepted:
            return ActivationResult(accepted=False, phase=self.state.phase, reason="rejected")
        self.state.phase = CapabilityPhase.WARMING
        return ActivationResult(accepted=True, phase=CapabilityPhase.WARMING)

    async def await_warm(self, key: str, *, timeout_s: float = 120.0, interval_s: float = 0.75) -> CapabilityState:
        self.calls.append("await_warm")
        if self._await_warm_raises is not None:
            raise self._await_warm_raises
        self.state.phase = CapabilityPhase.WARM
        return self.state

    async def issue_grant(self, key: str, *, holder: str, scope: str = "step") -> CapabilityGrant:
        self.calls.append("issue_grant")
        return CapabilityGrant(
            spec=self.spec,
            state=self.state,
            lease=GrantLease(grant_id=uuid4().hex, holder=holder, issued_at=datetime.now(UTC)),
            generation=self.spec.generation_profile,
            animator=self._runtime,
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

    async with dispatcher.lease_grant_key(_KEY, holder="run:1") as grant:
        assert grant.spec.key == _KEY
        assert leases.active(animator_name="router")  # held inside the CM

    assert "issue_grant" in registry.calls
    assert "activate" not in registry.calls
    assert leases.active() == []  # released on exit


@pytest.mark.asyncio
async def test_drain_racing_grant_issue_becomes_hardware_transition() -> None:
    """A grant that loses admission during issue parks; it never leaks or fails generically."""
    registry = GrantRaceRegistry()
    dispatcher, leases = _dispatcher(registry)

    async def _lease() -> None:
        async with dispatcher.lease_grant_key(_KEY, holder="run:race"):
            pytest.fail("a grant must not enter after its animator starts draining")

    lease_task = asyncio.create_task(_lease())
    await registry.issue_started.wait()
    leases.begin_drain(["router"])
    registry.finish_issue.set()

    with pytest.raises(HardwareTransitionRequired) as exc_info:
        await lease_task

    assert exc_info.value.capability_key == _KEY
    assert exc_info.value.animator_name == "router"
    assert isinstance(exc_info.value.__cause__, LeaseAdmissionClosed)
    assert leases.active() == []


@pytest.mark.asyncio
async def test_activatable_row_signals_orchestrator_without_mutating_runtime() -> None:
    registry = FakeRegistry(phase=CapabilityPhase.ACTIVATABLE)
    dispatcher, leases = _dispatcher(registry)

    with pytest.raises(HardwareTransitionRequired):
        async with dispatcher.lease_grant_key(_KEY, holder="run:1"):
            pass

    assert "activate" not in registry.calls
    assert "await_warm" not in registry.calls
    assert "issue_grant" not in registry.calls
    assert leases.active() == []


@pytest.mark.asyncio
async def test_activatable_row_does_not_attempt_a_rejected_activation() -> None:
    registry = FakeRegistry(phase=CapabilityPhase.ACTIVATABLE, activate_accepted=False)
    dispatcher, _ = _dispatcher(registry)

    with pytest.raises(HardwareTransitionRequired):
        async with dispatcher.lease_grant_key(_KEY, holder="run:1"):
            pass

    assert "activate" not in registry.calls


@pytest.mark.asyncio
async def test_warming_row_signals_orchestrator_without_waiting() -> None:
    registry = FakeRegistry(phase=CapabilityPhase.WARMING)
    dispatcher, leases = _dispatcher(registry)

    with pytest.raises(HardwareTransitionRequired):
        async with dispatcher.lease_grant_key(_KEY, holder="run:1"):
            pass

    assert "activate" not in registry.calls
    assert "await_warm" not in registry.calls
    assert "issue_grant" not in registry.calls
    assert leases.active() == []


@pytest.mark.asyncio
async def test_cold_activatable_row_raises_htr_and_registers_no_lease() -> None:
    registry = FakeRegistry(phase=CapabilityPhase.COLD, activatable=True)
    dispatcher, leases = _dispatcher(registry)

    with pytest.raises(HardwareTransitionRequired) as exc_info:
        async with dispatcher.lease_grant_key(_KEY, holder="run:1"):
            pass

    assert exc_info.value.capability_key == _KEY
    assert exc_info.value.animator_name == "router"
    assert exc_info.value.estimated_ready_ms == 1500
    assert leases.active() == []  # THE truth seam: a parked run holds no lease


@pytest.mark.asyncio
async def test_cold_link_flag_does_not_override_lifecycle_ownership() -> None:
    registry = FakeRegistry(phase=CapabilityPhase.COLD, activatable=False, reason="no gpu")
    dispatcher, _ = _dispatcher(registry)

    with pytest.raises(HardwareTransitionRequired):
        async with dispatcher.lease_grant_key(_KEY, holder="run:1"):
            pass


@pytest.mark.asyncio
async def test_shared_non_warm_row_raises_capability_unavailable() -> None:
    registry = FakeRegistry(phase=CapabilityPhase.COLD, dedicated=False)
    dispatcher, _ = _dispatcher(registry)

    with pytest.raises(CapabilityUnavailable, match="not lifecycle-managed"):
        async with dispatcher.lease_grant_key(_KEY, holder="run:1"):
            pass


@pytest.mark.asyncio
async def test_error_row_raises_capability_unavailable() -> None:
    registry = FakeRegistry(phase=CapabilityPhase.ERROR, reason="model crashed")
    dispatcher, _ = _dispatcher(registry)

    with pytest.raises(CapabilityUnavailable):
        async with dispatcher.lease_grant_key(_KEY, holder="run:1"):
            pass


@pytest.mark.asyncio
async def test_unknown_row_refreshes_once_then_unavailable() -> None:
    registry = FakeRegistry(phase=CapabilityPhase.UNKNOWN, refresh_phase=CapabilityPhase.UNKNOWN)
    dispatcher, _ = _dispatcher(registry)

    with pytest.raises(CapabilityUnavailable):
        async with dispatcher.lease_grant_key(_KEY, holder="run:1"):
            pass

    assert "activate" not in registry.calls  # stayed unknown, never activated


@pytest.mark.asyncio
async def test_lease_released_after_exception_inside_cm_body() -> None:
    registry = FakeRegistry(phase=CapabilityPhase.WARM)
    dispatcher, leases = _dispatcher(registry)

    async def _explode() -> None:
        async with dispatcher.lease_grant_key(_KEY, holder="run:1"):
            assert leases.active(animator_name="router")
            raise _BoomError

    with pytest.raises(_BoomError):
        await _explode()

    assert leases.active() == []  # released even on a mid-body exception
