"""The `Intent` shape and the deterministic router (A5 §9).

Every surface (Bridge now; CLI and A2A later) enters through `RunEngine.submit`.
The engine routes an `Intent` to a `Workflow` ONCE via the `WorkflowRegistry`
(first-match `Trigger`), persists the choice on the run row, and enqueues the run
onto SAQ — the graph executes only inside the `perform_run` ghoul.

Wave 2 keystone: the old `submit()` (`asyncio.create_task`) is gone — its logic
moved into `domain/cortex/engine.py` (`RunEngine`) and `ghouls/runs.py`
(`perform_run`). `route()` remains as a thin delegate over the built-in registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from lychd.agents.workflows.base import Workflow

__all__ = ["Intent", "route"]


class Intent(BaseModel):
    """The single cross-surface request shape — one shape, one `submit()` law."""

    session_id: str
    # S3: run_id is advisory client-correlation ONLY. Run identity is minted by the
    # ledger (`engine.submit` returns the canonical id on the handle) and stashed here
    # in the intent JSONB. A caller may leave it None; surfaces no longer mint one.
    run_id: str | None = None
    prompt: str
    source: str = "bridge"
    sigil_scopes: frozenset[str] = Field(default_factory=frozenset)
    priority: int | None = None  # None → the [orchestration.routing] per-source default


def route(intent: Intent) -> Workflow:
    """Return the first workflow whose trigger matches; the default is the floor.

    A thin delegate over the built-in `WorkflowRegistry` (first-match `Trigger`
    semantics preserved). `RunEngine.submit` calls this once and persists the choice.
    """
    from lychd.agents.workflows import WORKFLOW_REGISTRY

    return WORKFLOW_REGISTRY.route(intent)
