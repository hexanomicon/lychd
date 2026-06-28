"""The deterministic router and the one `submit()` entrypoint (§5.5).

Every surface (Bridge now; CLI and A2A later) enters through `submit()`. The
router runs once, the choice is persisted, and a `GraphRunner` drives the chosen
workflow's graph on a background task with a per-run Live Stasis phylactery.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, Field

from lychd.agents.workflows import WORKFLOWS
from lychd.agents.workflows.bridge_chat import fail_run
from lychd.domain.cortex.graph_runner import GraphRunner
from lychd.domain.cortex.stasis import LiveStasisPhylactery

logger = structlog.get_logger()

if TYPE_CHECKING:
    from litestar.datastructures import State

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


async def submit(intent: Intent, *, state: State) -> RunHandle:
    """Route, persist the choice, launch the graph run, and register it.

    The router runs once and the choice is persisted. The graph is driven on a
    background task; tokens arrive over the run's SSE channel.
    """
    workflow = route(intent)
    sessions = state.bridge_sessions
    sessions.record_route(intent.run_id, workflow.name)

    persistence = LiveStasisPhylactery(job_id=intent.run_id)
    runner: GraphRunner[Any] = GraphRunner(
        dispatcher=state.dispatcher,
        orchestrator=state.orchestrator,
        persistence=persistence,
    )
    async def _drive() -> None:
        """Drive the run, guaranteeing a terminal event so the SSE stream never hangs."""
        try:
            await runner.run_graph(workflow.graph, workflow.start_node(), workflow.make_state(intent))
        except Exception:  # background guard: a failed run must still close its stream
            logger.exception("bridge_run_failed", run_id=intent.run_id, workflow=workflow.name)
            fail_run(
                run_id=intent.run_id,
                session_id=intent.session_id,
                message=(
                    "The summoning faltered — no capability answered. Ensure a chat Soulstone is "
                    "bound and warm, then speak again."
                ),
            )

    task = asyncio.create_task(_drive(), name=f"run:{intent.run_id}")
    return sessions.register_run(intent.run_id, workflow, task)
