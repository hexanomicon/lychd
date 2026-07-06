"""The deterministic router and the one `submit()` entrypoint (A5 §9).

Every surface (Bridge now; CLI and A2A later) enters through `submit()`. The
router runs once, the choice is persisted, and a `GraphRunner` drives the chosen
workflow's graph on a background task with a per-run Live Stasis phylactery.

`submit()` constructs the run-scoped `WorkflowServices` from handles that live on
`app.state` (the web/composition root owns those handles) and threads it into the
graph as `deps=`. Nothing here holds mutable module state.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, Field

from lychd.agents.services import WorkflowServices, build_workflow_services
from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import WORKFLOWS
from lychd.domain.cortex.graph_runner import GraphRunner
from lychd.domain.cortex.stasis import LiveStasisPhylactery

logger = structlog.get_logger()

if TYPE_CHECKING:
    from litestar.datastructures import State

    from lychd.agents.factory import AgentForge
    from lychd.agents.workflows.base import Workflow
    from lychd.domain.web.sessions import RunHandle


class Intent(BaseModel):
    """The single cross-surface request shape — one shape, one `submit()` law."""

    session_id: str
    run_id: str
    prompt: str
    source: str = "bridge"
    sigil_scopes: frozenset[str] = Field(default_factory=frozenset)


def route(intent: Intent) -> Workflow:
    """Return the first workflow whose trigger matches; bridge_chat is the floor."""
    for workflow in WORKFLOWS:
        if workflow.trigger.match(intent):
            return workflow
    return WORKFLOWS[0]


def _resolve_forge(state: State) -> AgentForge:
    """Return the process-scoped `AgentForge`, lazily seeding `app.state` once.

    The forge is THE agent cache: keeping it on `app.state` (not a module global)
    lets it live for the process while staying injectable and test-isolable. The
    composition root may pre-seed `state.forge`; this fallback covers the case it
    has not yet.
    """
    forge: AgentForge | None = getattr(state, "forge", None)
    if forge is None:
        forge = default_forge()
        state.forge = forge
    return forge


def _services_from_state(state: State) -> WorkflowServices:
    """Assemble the run-scoped `WorkflowServices` from the `app.state` handles."""
    return build_workflow_services(
        dispatcher=state.dispatcher,
        orchestrator=state.orchestrator,
        context=state.context_orchestrator,
        fragments=state.fragments,
        sessions=state.bridge_sessions,
        forge=_resolve_forge(state),
    )


def _fail_run(services: WorkflowServices, *, run_id: str, session_id: str, message: str) -> None:
    """Terminate a run that raised before settling: record a failed turn, close the stream.

    The background run guard calls this so a failed run still emits a terminal
    ``done`` event — otherwise the SSE stream and its streaming slot would hang
    forever (the turn would stay ``aria-busy``).
    """
    from lychd.domain.web.schemas import BridgeTurn

    services.turns.add_turn(
        session_id,
        BridgeTurn(role="agent", content=message, run_id=run_id, state="failed"),
    )
    services.turns.set_run_status(run_id, "failed")
    with suppress(RuntimeError):
        services.context.release(run_id)
    services.events.channel(run_id).emit("done", run_id)


async def submit(intent: Intent, *, state: State) -> RunHandle:
    """Route, persist the choice, launch the graph run, and register it.

    The router runs once and the choice is persisted. The graph is driven on a
    background task; tokens arrive over the run's SSE channel.
    """
    workflow = route(intent)
    sessions = state.bridge_sessions
    sessions.record_route(intent.run_id, workflow.name)

    services = _services_from_state(state)
    persistence = LiveStasisPhylactery(job_id=intent.run_id)
    runner: GraphRunner[Any] = GraphRunner(orchestrator=state.orchestrator, persistence=persistence)

    async def _drive() -> None:
        """Drive the run, guaranteeing a terminal event so the SSE stream never hangs."""
        try:
            await runner.run_graph(
                workflow.graph,
                workflow.start_node(),
                workflow.make_state(intent),
                deps=services,
            )
        except Exception:  # background guard: a failed run must still close its stream
            logger.exception("bridge_run_failed", run_id=intent.run_id, workflow=workflow.name)
            _fail_run(
                services,
                run_id=intent.run_id,
                session_id=intent.session_id,
                message=(
                    "The summoning faltered — no capability answered. Ensure a chat Soulstone is "
                    "bound and warm, then speak again."
                ),
            )

    task = asyncio.create_task(_drive(), name=f"run:{intent.run_id}")
    return sessions.register_run(intent.run_id, workflow, task)
