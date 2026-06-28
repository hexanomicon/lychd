"""Web DI: startup singletons on `app.state` and per-request `Provide` factories (§3).

Singletons are built once at startup; the `Provide` factories only read
`app.state`. `build_web_singletons` also wires the `bridge_chat` workflow module
so its graph nodes and the consent tool resolve their runtime collaborators.
"""

from __future__ import annotations

import asyncio
from typing import Any

from litestar import Litestar
from litestar.datastructures import State
from litestar.di import Provide

from lychd.agents.workflows import bridge_chat
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.graph_runner import GraphRunner
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.web.fragments import FragmentRegistry, build_fragment_registry
from lychd.domain.web.sessions import BridgeSessionStore


class QuiescentBroker:
    """A no-op worker broker satisfying `OrchestratorManager`'s drain protocol.

    The slice has no background workers, so draining is instantaneous and the
    active-worker count is always zero. The SAQ-backed broker replaces this later
    without touching the manager.
    """

    async def pause_queues(self) -> None:
        """Pause intake queues (no-op: no workers in the slice)."""

    async def broadcast_soft_stop(self) -> None:
        """Ask workers to finish their current job (no-op: no workers)."""

    async def unpause_queues(self) -> None:
        """Resume intake queues (no-op: no workers)."""

    async def get_active_worker_count(self) -> int:
        """Return the number of still-draining workers (always zero here)."""
        return 0


async def build_web_singletons(app: Litestar) -> None:
    """Construct the web singletons onto `app.state` and wire `bridge_chat`."""
    registry = AnimatorRegistry()
    dispatcher = Dispatcher(registry=registry)
    orchestrator = OrchestratorManager(worker_broker=QuiescentBroker(), registry=registry)
    context_orchestrator = ContextOrchestrator(registry=registry)
    fragments = build_fragment_registry()
    bridge_sessions = BridgeSessionStore()

    app.state.registry = registry
    app.state.dispatcher = dispatcher
    app.state.orchestrator = orchestrator
    app.state.context_orchestrator = context_orchestrator
    app.state.fragments = fragments
    app.state.bridge_sessions = bridge_sessions

    bridge_chat.wire(
        dispatcher=dispatcher,
        orchestrator=orchestrator,
        context=context_orchestrator,
        fragments=fragments,
        sessions=bridge_sessions,
    )

    # Warm the registry off the event loop: rune loading + quadlet transmutation is
    # synchronous disk IO, so force it at startup instead of stalling the first handler.
    await asyncio.to_thread(registry.ensure_loaded)


def provide_registry(state: State) -> AnimatorRegistry:
    """Return the process-wide animator registry."""
    return state.registry


def provide_dispatcher(state: State) -> Dispatcher:
    """Return the process-wide capability dispatcher."""
    return state.dispatcher


def provide_orchestrator(state: State) -> OrchestratorManager:
    """Return the process-wide orchestrator manager."""
    return state.orchestrator


def provide_context_orchestrator(state: State) -> ContextOrchestrator:
    """Return the process-wide context (CAG) orchestrator."""
    return state.context_orchestrator


def provide_fragments(state: State) -> FragmentRegistry:
    """Return the generative-UI fragment registry."""
    return state.fragments


def provide_bridge_sessions(state: State) -> BridgeSessionStore:
    """Return the Bridge session store."""
    return state.bridge_sessions


def provide_graph_runner(state: State) -> GraphRunner[Any]:
    """Return a per-request `GraphRunner` for inspecting or resuming runs.

    Persistence is bound per-run inside `submit()` (§5.5); this throwaway handle
    exists only for handlers that inspect the shared dispatcher/orchestrator.
    """
    from lychd.domain.cortex.stasis import LiveStasisPhylactery

    return GraphRunner(
        dispatcher=state.dispatcher,
        orchestrator=state.orchestrator,
        persistence=LiveStasisPhylactery(job_id="inspect"),
    )


web_dependencies: dict[str, Provide] = {
    "registry": Provide(provide_registry, sync_to_thread=False),
    "dispatcher": Provide(provide_dispatcher, sync_to_thread=False),
    "orchestrator": Provide(provide_orchestrator, sync_to_thread=False),
    "graph_runner": Provide(provide_graph_runner, sync_to_thread=False),
    "context_orchestrator": Provide(provide_context_orchestrator, sync_to_thread=False),
    "fragments": Provide(provide_fragments, sync_to_thread=False),
    "bridge_sessions": Provide(provide_bridge_sessions, sync_to_thread=False),
}
