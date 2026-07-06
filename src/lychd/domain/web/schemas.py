"""Typed view-models for the Altar HTMX surfaces (§2).

Pure, frozen data carried from domain services into templates. No IO, no
rendering — the controllers build these and hand them to Jinja as context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from lychd.agents.workflows.base import Workflow
    from lychd.domain.animation.services.registry import AnimatorRegistry
    from lychd.domain.orchestration.manager import OrchestratorManager

TurnRole = Literal["user", "agent"]
# Internal turn state written by the graph; mapped to the frozen run-state
# `data-state` vocabulary (queued/streaming/consent/done/failed) by `run_data_state`.
TurnState = Literal["settled", "streaming", "pending_consent", "consented", "refused", "failed"]
# Capability `data-state` vocabulary (spec-web-design §5). `_coven_state` maps the
# phase-by-lifecycle table (S9); "warm" stays reserved vocabulary (Wave 6 W6-a may refine).
CovenState = Literal["active", "warm", "awaited", "warming", "cold", "fault"]
ConsentState = Literal["pending_consent", "consented", "refused"]
# Swap-ticket trio (spec-web-design §5): warming → settled → failed.
TicketState = Literal["warming", "settled", "failed"]

# Frozen run-state `data-state` vocabulary (spec-00-FINAL C5 / spec-web-design §5).
_RUN_DATA_STATE: dict[str, str] = {
    "settled": "done",
    "done": "done",
    "failed": "failed",
    "streaming": "streaming",
    "queued": "queued",
    "consent": "consent",
    "pending_consent": "consent",
    "consented": "done",
    "refused": "done",
}


def run_data_state(turn_state: str) -> str:
    """Map an internal turn/run state to the frozen run `data-state` token."""
    return _RUN_DATA_STATE.get(turn_state, "done")


@dataclass(frozen=True, kw_only=True)
class BridgeTurn:
    """One settled turn in a Bridge session thread."""

    role: TurnRole
    content: str
    run_id: str | None = None
    state: TurnState = "settled"
    fragments: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, kw_only=True)
class ConsentCard:
    """The Seat of Consent view-model for one parked, approval-bearing tool call."""

    id: str
    run_id: str
    session_id: str
    tool_name: str
    args: dict[str, Any]
    vision: str
    state: ConsentState = "pending_consent"


@dataclass(frozen=True, kw_only=True)
class NexusCovenRow:
    """One capability row on the Nexus board."""

    capability_key: str
    animator_name: str
    family: str
    runtime: str
    model_id: str
    state: CovenState
    is_active: bool
    warm: bool
    health: str
    reason: str | None
    dedicated: bool
    persistent_resident: bool


@dataclass(frozen=True, kw_only=True)
class NexusBoard:
    """The full Nexus board: covens (grouped soulstones) plus a Portals column."""

    covens: tuple[tuple[str, tuple[NexusCovenRow, ...]], ...]
    portals: tuple[NexusCovenRow, ...]


@dataclass(frozen=True, kw_only=True)
class SwapTicket:
    """An in-flight coven transition strip (polled by the Nexus)."""

    id: str
    target: str
    state: TicketState
    action_type: str
    total_metabolic_cost: float


@dataclass(frozen=True, kw_only=True)
class LoomView:
    """A single Loom workflow projection: mermaid source plus metadata."""

    name: str
    title: str
    description: str
    trigger_hint: str
    node_names: tuple[str, ...]
    mermaid_source: str


def _coven_state(*, lifecycle: str, phase: str) -> CovenState:
    """Map a capability's phase + lifecycle to its data-state literal (seam S9).

    No template or CSS ever sees a ``CapabilityPhase``/``CapabilityLifecycle``
    enum value. A DYNAMIC capability observed ACTIVATABLE is ``"awaited"`` (the
    S9 row); a STATIC one there degrades honestly to ``"cold"``.
    """
    if phase == "warm":
        return "active"
    if phase == "warming":
        return "warming"
    if phase == "activatable":
        return "awaited" if lifecycle == "dynamic" else "cold"
    if phase == "error":
        return "fault"
    return "cold"


def build_nexus_board(orchestrator: OrchestratorManager, registry: AnimatorRegistry) -> NexusBoard:
    """Group the orchestrator's capability statuses into covens plus a Portals column."""
    grouped: dict[str, list[NexusCovenRow]] = {}
    portals: list[NexusCovenRow] = []

    for status in orchestrator.list_capability_statuses():
        row = NexusCovenRow(
            capability_key=str(status["capability_key"]),
            animator_name=str(status["animator_name"]),
            family=str(status["family"]),
            runtime=str(status["runtime"]),
            model_id=str(status["model_id"]),
            state=_coven_state(lifecycle=str(status["lifecycle"]), phase=str(status["phase"])),
            is_active=bool(status["is_active"]),
            warm=bool(status["warm"]),
            health=str(status["health"]),
            reason=status["reason"],
            dedicated=bool(status["dedicated"]),
            persistent_resident=bool(status["persistent_resident"]),
        )
        if status["source_kind"] == "portal":
            portals.append(row)
            continue
        grouped.setdefault(_coven_name(registry, row.animator_name), []).append(row)

    covens = tuple((name, tuple(rows)) for name, rows in sorted(grouped.items(), key=lambda item: item[0]))
    return NexusBoard(covens=covens, portals=tuple(portals))


def _coven_name(registry: AnimatorRegistry, animator_name: str) -> str:
    """Resolve an animator's coven label (its first group), falling back to its name."""
    soulstone = registry.get_soulstone_rune(animator_name)
    if soulstone is not None and soulstone.groups:
        return soulstone.groups[0]
    return animator_name


def build_loom_view(workflow: Workflow, *, highlight: Any | None = None) -> LoomView:
    """Project a `Workflow` into its Loom view-model (mermaid source + metadata)."""
    node_names = tuple(node.__name__ for node in workflow.graph.get_nodes())
    return LoomView(
        name=workflow.name,
        title=workflow.title,
        description=workflow.description,
        trigger_hint=workflow.trigger.hint,
        node_names=node_names,
        mermaid_source=workflow.mermaid(highlight=highlight),
    )
