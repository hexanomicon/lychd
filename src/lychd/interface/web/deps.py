"""Web DI: pure `Provide` readers of the lifespan-built `AltarServices` (§TD-5).

The one assembly site is `interface/web/lifespan.py`; `app.state.services` holds the
`AltarServices` container. These providers only read it — no construction, no module
globals. Removed keys vs the old slice: `graph_runner` (dead) and
`context_orchestrator` (a graph-internal collaborator, not handler DI).
"""

from __future__ import annotations

from litestar.datastructures import State
from litestar.di import Provide

# Runtime imports (not TYPE_CHECKING): Litestar evaluates each provider's return
# annotation at app-init to type the injected dependency.
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.web.altar_services import RunEngine
from lychd.domain.web.fragments import FragmentRegistry
from lychd.domain.web.projection import Projector
from lychd.domain.web.sessions import BridgeSessionStore
from lychd.domain.web.tickets import TicketStore


def provide_registry(state: State) -> AnimatorRegistry:
    """Return the process-wide animator registry."""
    return state.services.registry


def provide_dispatcher(state: State) -> Dispatcher:
    """Return the process-wide capability dispatcher."""
    return state.services.dispatcher


def provide_orchestrator(state: State) -> OrchestratorManager:
    """Return the process-wide orchestrator manager."""
    return state.services.orchestrator


def provide_fragments(state: State) -> FragmentRegistry:
    """Return the generative-UI fragment registry."""
    return state.services.fragments


def provide_bridge_sessions(state: State) -> BridgeSessionStore:
    """Return the Bridge session store."""
    return state.services.bridge_sessions


def provide_tickets(state: State) -> TicketStore:
    """Return the in-flight swap-ticket store."""
    return state.services.tickets


def provide_run_engine(state: State) -> RunEngine:
    """Return the transitional run engine facade."""
    return state.services.run_engine


def provide_run_bus(state: State) -> InProcessEventBus:
    """Return the process run-event bus (SSE subscribe + reconnect replay)."""
    return state.services.bus


def provide_projector(state: State) -> Projector:
    """Return the engine-bound Projector (the sole renderer)."""
    return state.services.projector


web_dependencies: dict[str, Provide] = {
    "registry": Provide(provide_registry, sync_to_thread=False),
    "dispatcher": Provide(provide_dispatcher, sync_to_thread=False),
    "orchestrator": Provide(provide_orchestrator, sync_to_thread=False),
    "fragments": Provide(provide_fragments, sync_to_thread=False),
    "bridge_sessions": Provide(provide_bridge_sessions, sync_to_thread=False),
    "tickets": Provide(provide_tickets, sync_to_thread=False),
    "run_engine": Provide(provide_run_engine, sync_to_thread=False),
    "run_bus": Provide(provide_run_bus, sync_to_thread=False),
    "projector": Provide(provide_projector, sync_to_thread=False),
}
