"""Explicit inactive native preparation Pattern; normal boot imports none of it."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ValidationError
from pydantic_graph import BaseNode, End, GraphRunContext

from lychd.agents.router import Intent
from lychd.agents.services import WorkflowServices
from lychd.agents.workflows.base import PatternEdge, PatternManifest, PatternNode, Trigger, Workflow
from lychd.compositions.reach.policy import prepare_turn
from lychd.compositions.reach.schemas import (
    PreparedReachTurn,
    ReachDecision,
    ReachEvent,
    ReachPolicy,
    ReachPreparationState,
)
from lychd.domain.cortex.graph import build_serial_graph

_SOURCE = "reach.prepare"
_GUEST = "reach.guest"


class ReachPreparationRefused(ValueError):  # noqa: N818 - domain refusal with a content-free decision
    """A rejected ingress event, before any Intent or native Run is constructed."""

    def __init__(self, decision: ReachDecision) -> None:
        """Retain the content-free refusal for a caller that owns ingress."""
        self.decision = decision
        super().__init__(decision.reason)


def make_preparation_intent(policy: ReachPolicy, event: ReachEvent, *, session_id: str, now: datetime) -> Intent:
    """Prepare before admission; this opt-in guest fixture has zero effect scopes."""
    decision = prepare_turn(policy, event, now=now)
    if decision.prepared is None:
        raise ReachPreparationRefused(decision)
    if not session_id.strip():
        msg = "Reach preparation requires an explicit session."
        raise ValueError(msg)
    return Intent(
        session_id=session_id,
        prompt=decision.prepared.model_dump_json(),
        source=_SOURCE,
        sigil_name=_GUEST,
        sigil_scopes=frozenset(),
    )


@dataclass(frozen=True, kw_only=True)
class ReachPreparationDeps:
    """Worker-owned handles; the result callback makes no durable-record promise."""

    common: WorkflowServices
    policy: ReachPolicy
    clock: Callable[[], datetime]
    record_result: Callable[[ReachDecision], None]


@dataclass
class EvaluateReachPreparation(BaseNode[ReachPreparationState, ReachPreparationDeps]):
    async def run(self, ctx: GraphRunContext[ReachPreparationState, ReachPreparationDeps]) -> ProjectReachPreparation:
        if ctx.state.result is not None:
            msg = "Fresh Reach evaluation cannot replace a retained result."
            raise ValueError(msg)
        ctx.state.result = prepare_turn(ctx.deps.policy, ctx.state.prepared.event, now=ctx.deps.clock())
        return ProjectReachPreparation()


@dataclass
class ProjectReachPreparation(BaseNode[ReachPreparationState, ReachPreparationDeps, ReachDecision]):
    async def run(self, ctx: GraphRunContext[ReachPreparationState, ReachPreparationDeps]) -> End[ReachDecision]:
        if ctx.state.result is None:
            msg = "Reach projection requires its evaluated preparation."
            raise ValueError(msg)
        # The clock may advance between serial stations; never project stale permission.
        result = prepare_turn(ctx.deps.policy, ctx.state.prepared.event, now=ctx.deps.clock())
        ctx.state.result = result
        ctx.deps.record_result(result)
        return End(result)


def reach_preparation_workflow(
    policy: ReachPolicy,
    *,
    clock: Callable[[], datetime],
    record_result: Callable[[ReachDecision], None],
) -> Workflow:
    """Assemble reach.prepare@1 explicitly; no platform contract or startup registration."""

    def admitted(intent: Intent) -> PreparedReachTurn:
        if intent.source != _SOURCE or intent.sigil_name != _GUEST or intent.sigil_scopes:
            msg = "Reach preparation requires its exact restricted guest Intent."
            raise ValueError(msg)
        try:
            prepared = PreparedReachTurn.model_validate_json(intent.prompt)
        except ValidationError:
            msg = "Reach preparation requires a validated event envelope."
            raise ValueError(msg) from None
        original = prepare_turn(policy, prepared.event, now=prepared.prepared_at)
        if original.prepared != prepared:
            msg = "Reach preparation differs from the pinned policy or accepted event."
            raise ValueError(msg)
        return prepared

    def state(intent: Intent) -> ReachPreparationState:
        if intent.run_id is None:
            msg = "Reach preparation requires the canonical persisted Run."
            raise ValueError(msg)
        return ReachPreparationState(run_id=intent.run_id, session_id=intent.session_id, prepared=admitted(intent))

    def validate(intent: Intent, candidate: BaseModel) -> None:
        expected = admitted(intent)
        if (
            type(candidate) is not ReachPreparationState
            or candidate.run_id != intent.run_id
            or candidate.session_id != intent.session_id
            or candidate.prepared != expected
        ):
            msg = "Reach checkpoint differs from the admitted Run, session, policy or event."
            raise ValueError(msg)
        ReachPreparationState.model_validate(candidate.model_dump(mode="python"))
        if candidate.result is not None and candidate.result != prepare_turn(
            policy, expected.event, now=candidate.result.evaluated_at
        ):
            msg = "Reach checkpoint result differs from its exact evaluation."
            raise ValueError(msg)
        candidate.model_dump(mode="json")

    graph = build_serial_graph(
        nodes=(EvaluateReachPreparation, ProjectReachPreparation),
        state_type=ReachPreparationState,
        deps_type=ReachPreparationDeps,
        output_type=ReachDecision,
        name="reach_preparation",
    )
    return Workflow(
        name=_SOURCE,
        title="Prepare one restricted Reach turn",
        description="Evaluate bounded social eligibility without cognition, retrieval or delivery.",
        trigger=Trigger(hint="Explicit Reach preparation", match=lambda intent: intent.source == _SOURCE),
        graph=graph,
        start_node=EvaluateReachPreparation,
        make_state=state,
        validate_state=validate,
        bind_deps=lambda common: ReachPreparationDeps(
            common=common, policy=policy, clock=clock, record_result=record_result
        ),
        manifest=PatternManifest(
            key=_SOURCE,
            revision="1",
            implementation_revision="py.1",
            checkpoint_schema="reach-preparation-state-v1",
            entry_node="evaluate",
            nodes=(
                PatternNode(key="evaluate", label="Evaluate preparation", implementation=EvaluateReachPreparation),
                PatternNode(key="project", label="Project preparation", implementation=ProjectReachPreparation),
                PatternNode(key="end", label="End", kind="terminal"),
            ),
            edges=(
                PatternEdge(key="evaluate-to-project", source="evaluate", target="project"),
                PatternEdge(key="project-to-end", source="project", target="end"),
            ),
        ),
    )
