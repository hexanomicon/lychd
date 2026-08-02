"""Typed Altar API harness over a hand-rolled fake `AltarServices`."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import httpx
import pytest
from litestar import Litestar
from litestar.datastructures import State

from lychd.agents.workflows import builtin_workflow_registry
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.codex.ledger import InMemoryConsentLedger
from lychd.domain.codex.middleware import sigil_auth_middleware
from lychd.domain.cortex.engine import RunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.delegation.services import DelegatedAgentCoordinator, InMemoryDelegatedAgentJobStore
from lychd.domain.orchestration.journal import TransitionJournal
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.schema import TransitionPlan, TransitionTrace
from lychd.domain.web.contracts import CsrfClientContract
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.projection import EventProjector
from lychd.domain.web.sessions import BridgeSessionStore, RunHandle
from lychd.domain.web.swap_requests import InMemorySwapRequestLedger
from lychd.domain.web.tickets import TicketStore
from lychd.extensions.manager import ExtensionManager
from lychd.interface.web import AltarController, BridgeController, LoomController, NexusController, OrbController
from lychd.interface.web.deps import web_dependencies

if TYPE_CHECKING:
    from lychd.domain.cortex.priority import Priority

SAMPLE_STATUSES: list[dict[str, Any]] = [
    {
        "capability_key": "chat:local",
        "animator_name": "the-first-one",
        "family": "chat",
        "runtime": "llamacpp",
        "model_id": "qwen3-4b",
        "is_dynamic": True,
        "phase": "warm",
        "is_active": True,
        "warm": True,
        "health": "ok",
        "reason": None,
        "dedicated": True,
        "persistent_resident": True,
        "source_kind": "soulstone",
    },
    {
        "capability_key": "chat:remote",
        "animator_name": "portal-openai",
        "family": "chat",
        "runtime": "portal",
        "model_id": "gpt-x",
        "is_dynamic": False,
        "phase": "cold",
        "is_active": False,
        "warm": False,
        "health": "ok",
        "reason": None,
        "dedicated": False,
        "persistent_resident": False,
        "source_kind": "portal",
    },
]


class FakeRunEngine(RunEngine):
    """A scripted run engine: records submitted intents, opens a live channel on the bus.

    Subclasses the real `RunEngine` so Litestar's dependency-value validation
    (isinstance-based) accepts it; the dataclass initializer is intentionally bypassed.
    """

    def __init__(self, bus: InProcessEventBus, consents: Any = None, ledger: InMemoryRunLedger | None = None) -> None:
        self.bus = bus
        self.submitted: list[Any] = []
        self.consents = consents
        self.ledger = ledger
        self.admitted_keys: dict[str, str] = {}
        self.cancelled_runs: list[str] = []
        # (consent_id, approved, verdict_seen_at_approve_time) — verdict-order proof.
        self.approvals: list[tuple[str, bool, bool | None]] = []

    async def approve(self, consent_id: str, *, approved: bool) -> None:
        """Record the approve call + the verdict already visible in the ledger (ordering)."""
        seen = await self.consents.verdict(consent_id) if self.consents is not None else None
        self.approvals.append((consent_id, approved, seen))

    async def cancel(self, run_id: str, *, orphaned: bool = False) -> None:
        """Mirror idempotent terminal truth for Bridge controller tests."""
        _ = orphaned
        self.cancelled_runs.append(run_id)
        if self.ledger is None:
            return
        run = await self.ledger.get(run_id)
        if run is None or run.status in {RunStatus.DONE, RunStatus.FAILED, RunStatus.CANCELLED}:
            return
        elected = await self.ledger.begin_cancel(run_id)
        if elected is not None:
            await self.ledger.finish_cancel(run_id, enqueue_seq=elected.enqueue_seq)

    async def submit(
        self,
        intent: Any,
        *,
        retain_before_publish: Any = None,
        idempotency_key: str | None = None,
    ) -> RunHandle:
        """Record the intent and open a run channel on the bus for the stream to tail.

        S3: mirror the real engine — the run id is minted here (the ledger's job),
        not carried in on `intent.run_id` (which is advisory/None from the bridge).
        """
        import uuid

        existing_run_id = self.admitted_keys.get(idempotency_key) if idempotency_key is not None else None
        run_id = existing_run_id or intent.run_id or f"run_{uuid.uuid4().hex[:12]}"
        if existing_run_id is None:
            self.submitted.append(intent)
        if idempotency_key is not None:
            self.admitted_keys[idempotency_key] = run_id
        if existing_run_id is None and retain_before_publish is not None:
            await retain_before_publish(run_id)
        return RunHandle(
            run_id=run_id,
            workflow_name="bridge_chat",
            pattern_id="bridge_chat",
            pattern_revision="1",
            evidence_capture="process_local",
            channel=self.bus.open(run_id),
        )


class FakeOrchestrator(OrchestratorManager):
    """A fake orchestrator that serves fixed statuses and canned transition plans.

    Subclasses the real type for Litestar dep validation; parent `__init__` bypassed.
    """

    def __init__(self, statuses: list[dict[str, Any]] | None = None) -> None:
        self._statuses = statuses if statuses is not None else SAMPLE_STATUSES
        self.requests: list[str] = []
        self.transitions = TransitionJournal()
        self._contained_reason: str | None = None

    def list_capability_statuses(self) -> list[dict[str, Any]]:
        """Return the fixed capability statuses feeding the board."""
        return self._statuses

    async def calculate_transition_plan(self, target_capability_key: str) -> TransitionPlan:
        """Return a canned plan, or raise ValueError for the sentinel unknown target."""
        if target_capability_key == "chat:unknown":
            msg = "unknown target"
            raise ValueError(msg)
        return TransitionPlan(
            total_metabolic_cost=1.0,
            evict_coven_ids=[],
            launch_coven_ids=[target_capability_key],
            action_type="SOFT_SWAP",
        )

    async def request_transition(
        self,
        target_capability_key: str,
        priority: Priority = 0,
        **kwargs: Any,
    ) -> TransitionPlan:
        """Record the requested transition (completes immediately)."""
        _ = priority
        self.requests.append(target_capability_key)
        plan = TransitionPlan(
            total_metabolic_cost=1.0,
            evict_coven_ids=[],
            launch_coven_ids=[target_capability_key],
            action_type="SOFT_SWAP",
        )
        trace = kwargs.get("trace")
        if isinstance(trace, TransitionTrace):
            trace.plan = plan
            trace.phase = "completed"
            self.transitions.record(trace)
        return plan


class FakeRegistry(AnimatorRegistry):
    """A fake animator registry: no soulstone rune metadata (coven name = animator).

    Subclasses the real type for Litestar dep validation; parent `__init__` bypassed.
    """

    def __init__(self) -> None:
        """Bypass the real registry's required-args constructor."""

    def get_soulstone_rune(self, name: str) -> None:  # noqa: ARG002
        """Return no soulstone rune so coven labels fall back to the animator name."""
        return

    def ensure_loaded(self) -> None:
        """No-op warm."""


class AsgiClient:
    """Small sync facade over httpx's direct ASGI transport.

    Litestar's blocking-portal TestClient hangs with the repository's current
    AnyIO runtime even for an empty app. This adapter invokes the same ASGI app
    directly and does not introduce a second web contract.
    """

    def __init__(self, app: Litestar) -> None:
        self.app = app
        self._loop = asyncio.new_event_loop()

    def request(
        self,
        method: str,
        url: str,
        *,
        follow_redirects: bool = True,
        **kwargs: Any,
    ) -> httpx.Response:
        async def _request() -> httpx.Response:
            transport = httpx.ASGITransport(app=self.app)  # pyright: ignore[reportArgumentType]
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver.local",
                follow_redirects=follow_redirects,
            ) as client:
                return await client.request(method, url, **kwargs)

        async def _bounded_request() -> httpx.Response:
            return await asyncio.wait_for(_request(), timeout=5)

        return self._loop.run_until_complete(_bounded_request())

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)


@pytest.fixture
def fake_services() -> SimpleNamespace:
    """Build the fake `AltarServices` container (attribute-compatible with the real one)."""
    sessions = BridgeSessionStore()
    consents = InMemoryConsentLedger()
    fragments = build_fragment_registry()
    tickets = TicketStore()
    swap_requests = InMemorySwapRequestLedger()
    # honor_intent_run_id: test-only seam so SSE tests can seed runs keyed by a stable
    # id (R4: production always mints; identity is the ledger's, not the advisory field).
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    projector = EventProjector(fragments=fragments, sessions=sessions, consents=consents)
    extension_context = ExtensionManager(builtins=["delegation"], crypt=[]).assemble()
    delegates = DelegatedAgentCoordinator(
        runtimes=dict(extension_context.delegated_runtimes.runtime_adapters),
        store=InMemoryDelegatedAgentJobStore(),
    )
    workflows = builtin_workflow_registry()
    return SimpleNamespace(
        registry=FakeRegistry(),
        dispatcher=None,
        orchestrator=FakeOrchestrator(),
        leases=LeaseLedger(),
        context_orchestrator=None,
        fragments=fragments,
        bridge_sessions=sessions,
        consents=consents,
        tickets=tickets,
        swap_requests=swap_requests,
        workflows=workflows,
        run_engine=FakeRunEngine(bus, consents, ledger),
        projector=projector,
        ledger=ledger,
        bus=bus,
        delegates=delegates,
        delegated_runtime_catalog=extension_context.delegated_runtimes.registrations,
    )


@pytest.fixture
def altar_client(fake_services: SimpleNamespace) -> AsgiClient:
    """A test client wired to the real API and SPA controllers."""
    app = Litestar(
        route_handlers=[AltarController, BridgeController, NexusController, LoomController, OrbController],
        dependencies=web_dependencies,
        middleware=[sigil_auth_middleware()],  # the Ward: connection.user = settings Sigil (scopes ["*"])
        state=State(
            {
                "services": fake_services,
                "csrf_contract": CsrfClientContract(
                    cookie_name="csrftoken",
                    header_name="x-csrftoken",
                ),
            },
        ),
    )
    return AsgiClient(app)


@pytest.fixture
def projector() -> EventProjector:
    """A standalone semantic event projector."""
    sessions = BridgeSessionStore()
    return EventProjector(
        fragments=build_fragment_registry(),
        sessions=sessions,
        consents=InMemoryConsentLedger(),
    )
