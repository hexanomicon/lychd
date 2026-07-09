"""Workflow = graph + metadata + deterministic trigger (§5.1).

A `Workflow` binds a BaseNode-style `pydantic_graph.Graph` to the metadata the
Loom renders and the pure predicate the router matches. Adding a workflow never
edits the router.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import BaseModel
    from pydantic_graph import BaseNode, Graph

    from lychd.agents.router import Intent

# The necro-green highlight used for the active node in Loom projections.
HIGHLIGHT_CSS = "fill:#39ff8a33,stroke:#39ff8a,stroke-width:2px"


class Gate:
    """Marker mixin: a node that can park the run on an external verdict (consent/HitL).

    Any workflow whose graph contains a Gate node is assigned the Durable Stasis tier
    (`_workflow_parks` scans `graph.get_nodes()` for `issubclass(node, Gate)`).
    """


@dataclass(frozen=True, kw_only=True)
class Trigger:
    """Deterministic route predicate. Adding a workflow never edits the router."""

    hint: str
    match: Callable[[Intent], bool]


@dataclass(frozen=True, kw_only=True)
class Workflow:
    """A named workflow: its graph, its Loom metadata, and its route trigger."""

    name: str
    title: str
    description: str
    trigger: Trigger
    graph: Graph[Any, Any, Any]
    start_node: type[BaseNode[Any, Any, Any]]
    make_state: Callable[[Intent], BaseModel]
    # Computed once at construction: a workflow whose graph contains any `Gate` node
    # takes the Durable Stasis tier. Kept a derived property (not a hand-set flag) so it
    # can never drift from the graph — but resolved HERE, near `Gate`, not re-scanned by
    # the ghoul on every run.
    durable: bool = field(init=False)

    def __post_init__(self) -> None:
        """Derive the Durable-Stasis tier from the presence of any `Gate` node."""
        object.__setattr__(self, "durable", any(issubclass(node, Gate) for node in self.graph.get_nodes()))

    def mermaid(self, *, highlight: type[BaseNode[Any, Any, Any]] | None = None) -> str:
        """Return the stateDiagram-v2 source, optionally highlighting one node."""
        return self.graph.mermaid_code(
            title=self.title,
            direction="LR",
            highlighted_nodes=(highlight,) if highlight is not None else None,
            highlight_css=HIGHLIGHT_CSS,
        )
