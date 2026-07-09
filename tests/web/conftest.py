"""Web test harness: `create_test_client` + a hand-rolled fake `AltarServices`.

Tier A (the bulk): the real template config, the real `web_dependencies` shape, and
a fake services container (scripted `RunEngine`, fake orchestrator/registry, real
`FragmentRegistry`/`Projector`/`BridgeSessionStore`/`TicketStore`). A static lifespan
stamps `state.services`, mirrors the handles, binds the engine, and registers the
`route_path` global + `run_data_state` filter — exactly as the production lifespan
does — then builds the `Projector` against the app's own template engine.

Assertions use stdlib string/id checks (no extra dev-dep); never snapshot whole pages.
Every SSE test pre-closes its channel (terminal `done`) so reads cannot hang.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

import pytest
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.plugins.htmx import HTMXPlugin
from litestar.template.config import TemplateConfig
from litestar.testing import create_test_client  # pyright: ignore[reportUnknownVariableType]

from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.codex.ledger import InMemoryConsentLedger
from lychd.domain.codex.middleware import sigil_auth_middleware
from lychd.domain.cortex.engine import RunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.schema import TransitionPlan
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.projection import Projector
from lychd.domain.web.schemas import run_data_state
from lychd.domain.web.sessions import BridgeSessionStore, RunHandle
from lychd.domain.web.tickets import TicketStore
from lychd.interface.web import AltarController, BridgeController, LoomController, NexusController
from lychd.interface.web.deps import web_dependencies

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from litestar import Litestar
    from litestar.testing import TestClient

    from lychd.domain.cortex.priority import Priority

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "src" / "lychd" / "domain" / "web" / "templates"

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

    def __init__(self, bus: InProcessEventBus, consents: Any = None) -> None:
        self.bus = bus
        self.submitted: list[Any] = []
        self.consents = consents
        # (consent_id, approved, verdict_seen_at_approve_time) — verdict-order proof.
        self.approvals: list[tuple[str, bool, bool | None]] = []

    async def approve(self, consent_id: str, *, approved: bool) -> None:
        """Record the approve call + the verdict already visible in the ledger (ordering)."""
        seen = await self.consents.verdict(consent_id) if self.consents is not None else None
        self.approvals.append((consent_id, approved, seen))

    async def submit(self, intent: Any) -> RunHandle:
        """Record the intent and open a run channel on the bus for the stream to tail.

        S3: mirror the real engine — the run id is minted here (the ledger's job),
        not carried in on `intent.run_id` (which is advisory/None from the bridge).
        """
        import uuid

        self.submitted.append(intent)
        run_id = intent.run_id or f"run_{uuid.uuid4().hex[:12]}"
        return RunHandle(
            run_id=run_id,
            workflow_name="bridge_chat",
            channel=self.bus.open(run_id),
        )


class FakeOrchestrator(OrchestratorManager):
    """A fake orchestrator that serves fixed statuses and canned transition plans.

    Subclasses the real type for Litestar dep validation; parent `__init__` bypassed.
    """

    def __init__(self, statuses: list[dict[str, Any]] | None = None) -> None:
        self._statuses = statuses if statuses is not None else SAMPLE_STATUSES
        self.transitions: list[str] = []

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
    ) -> TransitionPlan:
        """Record the requested transition (completes immediately)."""
        _ = priority
        self.transitions.append(target_capability_key)
        return TransitionPlan(
            total_metabolic_cost=1.0,
            evict_coven_ids=[],
            launch_coven_ids=[target_capability_key],
            action_type="SOFT_SWAP",
        )


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


@pytest.fixture
def fake_services() -> SimpleNamespace:
    """Build the fake `AltarServices` container (attribute-compatible with the real one)."""
    sessions = BridgeSessionStore()
    consents = InMemoryConsentLedger()
    fragments = build_fragment_registry()
    tickets = TicketStore()
    # honor_intent_run_id: test-only seam so SSE tests can seed runs keyed by a stable
    # id (R4: production always mints; identity is the ledger's, not the advisory field).
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
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
        run_engine=FakeRunEngine(bus, consents),
        projector=None,  # built in the lifespan against the app's template engine
        ledger=ledger,
        bus=bus,
    )


def _static_lifespan(services: SimpleNamespace) -> Any:
    @asynccontextmanager
    async def _lifespan(app: Litestar) -> AsyncIterator[None]:
        app.state.services = services

        engine = cast("JinjaTemplateEngine", app.template_engine)
        template_globals = cast("dict[str, Any]", engine.engine.globals)
        template_globals["route_path"] = app.route_reverse
        template_globals["vite_hmr"] = _empty_template_helper
        template_globals["vite"] = _empty_template_helper
        engine.engine.filters["run_data_state"] = run_data_state
        services.projector = Projector(
            engine=engine,
            fragments=services.fragments,
            sessions=services.bridge_sessions,
            consents=services.consents,
        )
        yield

    return _lifespan


@pytest.fixture
def altar_client(fake_services: SimpleNamespace) -> Iterator[TestClient[Litestar]]:
    """A test client wired to the real controllers/templates over the fake services."""
    with create_test_client(
        route_handlers=[AltarController, BridgeController, NexusController, LoomController],
        template_config=TemplateConfig(directory=TEMPLATES_DIR, engine=JinjaTemplateEngine),
        plugins=[HTMXPlugin()],
        dependencies=web_dependencies,
        middleware=[sigil_auth_middleware()],  # the Ward: connection.user = settings Sigil (scopes ["*"])
        lifespan=[_static_lifespan(fake_services)],
    ) as client:
        yield client


@pytest.fixture
def projector() -> Projector:
    """A standalone Projector bound to a fresh engine (unit tests, no HTTP)."""
    engine = JinjaTemplateEngine(directory=TEMPLATES_DIR)
    template_globals = cast("dict[str, Any]", engine.engine.globals)
    template_globals["route_path"] = _test_route_path
    engine.engine.filters["run_data_state"] = run_data_state
    sessions = BridgeSessionStore()
    return Projector(
        engine=engine, fragments=build_fragment_registry(), sessions=sessions, consents=InMemoryConsentLedger()
    )


def _empty_template_helper(*_args: object, **_kwargs: object) -> str:
    return ""


def _test_route_path(*_args: object, **_kwargs: object) -> str:
    return "/x"
