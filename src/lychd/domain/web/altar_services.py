"""`AltarServices` — the one web-layer service container (§TD-5, spec-00-FINAL C6).

Everything the Altar's web surface needs, built once per app lifespan and placed on
`app.state.services`. Replaces the two module-global singleton nests
(`bridge_chat.wire()` and `nexus._TICKETS`). `deps.py` provides only pure readers of
this container; the sole assembly site is `interface/web/lifespan.py`.

`RunEngine` is the transitional facade Wave 2 swaps internals behind (C2): it keeps
the `submit()` shape so controllers never thread `state=` themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.projection import Projector
from lychd.domain.web.sessions import BridgeSessionStore
from lychd.domain.web.tickets import TicketStore

if TYPE_CHECKING:
    from collections.abc import Sequence

    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.datastructures import State

    from lychd.domain.animation.services.adapters.contracts import SoulstoneRuntimeAdapter
    from lychd.domain.web.fragments import FragmentRegistry
    from lychd.domain.web.sessions import RunHandle


class QuiescentBroker:
    """A no-op worker broker satisfying `OrchestratorManager`'s drain protocol.

    The slice has no background workers, so draining is instantaneous and the
    active-worker count is always zero. Agent 4's SAQ-backed broker replaces this
    later without touching the manager.
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


class RunEngine:
    """Transitional facade over `agents.router.submit` (C2: Wave 2 swaps internals).

    Controllers call `submit(intent)`; the `state=` threading is confined here.
    Bound to `app.state` in the lifespan so the run-scoped collaborators the graph
    needs (dispatcher, orchestrator, context, fragments, sessions) resolve there.
    """

    def __init__(self) -> None:
        """Create an unbound engine (the lifespan calls `bind`)."""
        self._state: State | None = None

    def bind(self, state: State) -> None:
        """Bind the engine to the populated app state."""
        self._state = state

    async def submit(self, intent: object) -> RunHandle:
        """Route, persist the choice, and launch the run on a background task."""
        from lychd.agents.router import Intent, submit

        if self._state is None:  # pragma: no cover - lifespan always binds
            msg = "RunEngine is not bound to app state."
            raise RuntimeError(msg)
        if not isinstance(intent, Intent):  # pragma: no cover - typed callers only
            msg = "RunEngine.submit expects an Intent."
            raise TypeError(msg)
        return await submit(intent, state=self._state)


@dataclass(frozen=True, kw_only=True)
class AltarServices:
    """Everything the web layer needs, built once per app lifespan."""

    registry: AnimatorRegistry
    dispatcher: Dispatcher
    orchestrator: OrchestratorManager
    context_orchestrator: ContextOrchestrator
    fragments: FragmentRegistry
    bridge_sessions: BridgeSessionStore
    tickets: TicketStore
    run_engine: RunEngine
    projector: Projector

    async def aclose(self) -> None:
        """Cancel tracked tasks and drain per-run resources on shutdown."""
        await self.tickets.aclose()


def build_altar_services(
    *,
    template_engine: JinjaTemplateEngine,
    rune_schemas: Sequence[type],
    runtime_adapters: Sequence[SoulstoneRuntimeAdapter],
) -> AltarServices:
    """Assemble the `AltarServices` container (the sole construction site)."""
    registry = AnimatorRegistry(rune_schemas=rune_schemas, runtime_adapters=runtime_adapters)
    dispatcher = Dispatcher(registry=registry)
    orchestrator = OrchestratorManager(worker_broker=QuiescentBroker(), registry=registry)
    context_orchestrator = ContextOrchestrator(registry=registry)
    fragments = build_fragment_registry()
    bridge_sessions = BridgeSessionStore()
    tickets = TicketStore()
    projector = Projector(engine=template_engine, fragments=fragments, sessions=bridge_sessions)
    return AltarServices(
        registry=registry,
        dispatcher=dispatcher,
        orchestrator=orchestrator,
        context_orchestrator=context_orchestrator,
        fragments=fragments,
        bridge_sessions=bridge_sessions,
        tickets=tickets,
        run_engine=RunEngine(),
        projector=projector,
    )
