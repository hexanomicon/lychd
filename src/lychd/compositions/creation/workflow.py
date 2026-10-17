"""The fixed serial investigation score; no timer or automatic recovery scanner."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel
from pydantic_graph import BaseNode, End, GraphRunContext

from lychd.agents.router import Intent
from lychd.agents.services import WorkflowServices
from lychd.agents.workflows.base import PatternEdge, PatternManifest, PatternNode, Trigger, Workflow
from lychd.compositions.creation.schemas import PATTERN, CaseView, CreationRefused, CreationState, refuse
from lychd.compositions.creation.services import InvestigationService
from lychd.domain.cortex.graph import build_serial_graph


@dataclass(frozen=True)
class CreationDeps:
    common: WorkflowServices
    investigation: InvestigationService


@dataclass
class PrepareInvestigation(BaseNode[CreationState, CreationDeps]):
    async def run(
        self, ctx: GraphRunContext[CreationState, CreationDeps]
    ) -> ConstructInvestigation | VerifyInvestigation | ProjectInvestigation:
        try:
            view = await ctx.deps.investigation.store.ready(ctx.state.admission_id, ctx.state.run_id)
        except CreationRefused as exc:
            await ctx.deps.investigation.store.fail(ctx.state.admission_id, str(exc))
            return ProjectInvestigation()
        if view.status == "candidate":
            return VerifyInvestigation()
        return ConstructInvestigation() if view.status == "reserved" else ProjectInvestigation()


@dataclass
class ConstructInvestigation(BaseNode[CreationState, CreationDeps]):
    async def run(
        self, ctx: GraphRunContext[CreationState, CreationDeps]
    ) -> VerifyInvestigation | ProjectInvestigation:
        await ctx.deps.investigation.stage(ctx.state.admission_id, ctx.state.run_id, "constructor", ctx.deps.common)
        admission = await ctx.deps.investigation.store.admission(ctx.state.admission_id)
        view = await ctx.deps.investigation.store.read(UUID(admission["case_id"]))
        return VerifyInvestigation() if view.status == "candidate" else ProjectInvestigation()


@dataclass
class VerifyInvestigation(BaseNode[CreationState, CreationDeps]):
    async def run(self, ctx: GraphRunContext[CreationState, CreationDeps]) -> ProjectInvestigation:
        await ctx.deps.investigation.stage(ctx.state.admission_id, ctx.state.run_id, "verifier", ctx.deps.common)
        return ProjectInvestigation()


@dataclass
class ProjectInvestigation(BaseNode[CreationState, CreationDeps, CaseView]):
    async def run(self, ctx: GraphRunContext[CreationState, CreationDeps]) -> End[CaseView]:
        admission = await ctx.deps.investigation.store.admission(ctx.state.admission_id)
        return End(await ctx.deps.investigation.store.read(UUID(admission["case_id"])))


def _state(intent: Intent) -> CreationState:
    if intent.run_id is None or intent.source != "creation":
        refuse("run_identity")
    return CreationState(run_id=intent.run_id, session_id=intent.session_id, admission_id=UUID(intent.prompt))


def _validate_state(intent: Intent, state: BaseModel) -> None:
    if type(state) is not CreationState or state != _state(intent):
        refuse("checkpoint_binding")


def investigation_workflow(service: InvestigationService) -> Workflow:
    graph = build_serial_graph(
        nodes=(PrepareInvestigation, ConstructInvestigation, VerifyInvestigation, ProjectInvestigation),
        state_type=CreationState,
        deps_type=CreationDeps,
        output_type=CaseView,
        name="creation_investigate",
    )
    nodes = (
        ("prepare", PrepareInvestigation),
        ("construct", ConstructInvestigation),
        ("verify", VerifyInvestigation),
        ("project", ProjectInvestigation),
    )
    edges = (
        ("prepare", "construct"),
        ("prepare", "verify"),
        ("prepare", "project"),
        ("construct", "verify"),
        ("construct", "project"),
        ("verify", "project"),
        ("project", "end"),
    )
    manifest = PatternManifest(
        key=PATTERN,
        revision="2",
        implementation_revision="py.4",
        checkpoint_schema="creation-investigation-state-v1",
        entry_node="prepare",
        nodes=(
            *(PatternNode(key=key, label=node.__name__, kind="step", implementation=node) for key, node in nodes),
            PatternNode(key="end", label="End", kind="terminal"),
        ),
        edges=tuple(PatternEdge(key=f"{source}-to-{target}", source=source, target=target) for source, target in edges),
    )
    service.pattern = manifest.snapshot()
    return Workflow(
        name=PATTERN,
        title="Investigate bounded public source",
        description="Retain one candidate and a fresh attributed review.",
        trigger=Trigger(
            hint="An explicitly admitted Creation investigation", match=lambda intent: intent.source == "creation"
        ),
        graph=graph,
        start_node=PrepareInvestigation,
        make_state=_state,
        validate_state=_validate_state,
        bind_deps=lambda common: CreationDeps(common, service),
        manifest=manifest,
    )
