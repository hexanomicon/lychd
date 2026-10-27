"""Explicit reach.documents@1 native Workflow for disposable operator development."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from pydantic_graph import BaseNode, End, GraphRunContext

from lychd.agents.router import Intent
from lychd.agents.services import WorkflowServices
from lychd.agents.workflows.base import PatternEdge, PatternManifest, PatternNode, Trigger, Workflow
from lychd.compositions.reach.documents import PublicCorpus, context_excerpts, search_documents, validate_history
from lychd.compositions.reach.operator_wire import ReachWorkerRequest, ReachWorkerResult, ReachWorkerStatus
from lychd.compositions.reach.policy import prepare_turn
from lychd.compositions.reach.schemas import PolicyDigest, PreparedReachTurn, ReachPolicy, Record, require_aware
from lychd.domain.cortex.graph import build_serial_graph
from lychd.domain.web.schemas import BridgeTurn

SOURCE = "reach.documents"
GUEST = "reach.guest"


class DocumentsRefused(ValueError):  # noqa: N818 - explicit bounded domain refusal
    """A content-free refusal before native Run admission."""


class DocumentsEnvelope(Record):
    """Pin full policy, exact source export, input history and generation boundary."""

    policy: ReachPolicy
    corpus_digest: PolicyDigest
    request: ReachWorkerRequest = Field(repr=False)
    prepared: PreparedReachTurn = Field(repr=False)
    started_at: AwareDatetime


class DocumentsState(Record):
    """Declared continuation only; no credentials, SDK objects or model handles."""

    model_config = ConfigDict(
        extra="forbid", frozen=False, strict=True, validate_assignment=True, hide_input_in_errors=True
    )

    run_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    envelope: DocumentsEnvelope = Field(repr=False)
    evaluated_at: AwareDatetime | None = None
    result: ReachWorkerResult | None = Field(default=None, repr=False)


def make_documents_intent(
    policy: ReachPolicy,
    corpus: PublicCorpus,
    request: ReachWorkerRequest,
    *,
    session_id: str,
    started_at: datetime,
    now: datetime,
) -> Intent:
    """Refuse inadmissible observations and history before constructing an Intent."""
    require_aware(started_at)
    if request.event.occurred_at < started_at:
        msg = "before_generation"
        raise DocumentsRefused(msg)
    decision = prepare_turn(policy, request.event, now=now)
    if decision.prepared is None:
        raise DocumentsRefused(decision.reason)
    try:
        validate_history(policy, request)
    except ValueError:
        msg = "history_refused"
        raise DocumentsRefused(msg) from None
    envelope = DocumentsEnvelope(
        policy=policy, corpus_digest=corpus.digest, request=request, prepared=decision.prepared, started_at=started_at
    )
    return Intent(
        session_id=session_id,
        prompt=envelope.model_dump_json(),
        source=SOURCE,
        sigil_name=GUEST,
        sigil_scopes=frozenset(),
    )


@dataclass(frozen=True, kw_only=True)
class DocumentsDeps:
    """Worker-owned, effect-free search inputs and ordinary native turn settlement."""

    common: WorkflowServices
    policy: ReachPolicy
    corpus: PublicCorpus
    clock: Callable[[], datetime]


def _result(state: DocumentsState, policy: ReachPolicy, corpus: PublicCorpus, now: datetime) -> ReachWorkerResult:
    request = state.envelope.request
    decision = prepare_turn(policy, request.event, now=now)
    status: ReachWorkerStatus = "refused"
    text = ""
    reason: str | None = decision.reason
    if decision.allowed:
        validate_history(policy, request)
        status, text = (
            context_excerpts(request.history)
            if request.event.action == "summarize_context"
            else search_documents(corpus, request)
        )
        reason = None
    return ReachWorkerResult(
        request_id=request.request_id,
        status=status,
        text=text,
        run_id=state.run_id,
        policy_digest=policy.digest,
        corpus_digest=corpus.digest,
        reason=reason,
    )


@dataclass
class RevalidateDocuments(BaseNode[DocumentsState, DocumentsDeps]):
    async def run(self, ctx: GraphRunContext[DocumentsState, DocumentsDeps]) -> SearchDocuments:
        """Recheck live policy before using the pinned question or selected history."""
        if ctx.state.result is not None or ctx.state.evaluated_at is not None:
            msg = "documents_fresh_state"
            raise ValueError(msg)
        ctx.state.evaluated_at = ctx.deps.clock()
        return SearchDocuments()


@dataclass
class SearchDocuments(BaseNode[DocumentsState, DocumentsDeps]):
    async def run(self, ctx: GraphRunContext[DocumentsState, DocumentsDeps]) -> SettleDocuments:
        """Search once using the worker's verified public export; never call a model."""
        ctx.state.evaluated_at = ctx.deps.clock()
        ctx.state.result = _result(ctx.state, ctx.deps.policy, ctx.deps.corpus, ctx.state.evaluated_at)
        return SettleDocuments()


@dataclass
class SettleDocuments(BaseNode[DocumentsState, DocumentsDeps, ReachWorkerResult]):
    async def run(self, ctx: GraphRunContext[DocumentsState, DocumentsDeps]) -> End[ReachWorkerResult]:
        """Revalidate before settlement; retain one exact operator result in the turn ledger."""
        if ctx.state.result is None:
            msg = "documents_missing_result"
            raise ValueError(msg)
        ctx.state.evaluated_at = ctx.deps.clock()
        ctx.state.result = _result(ctx.state, ctx.deps.policy, ctx.deps.corpus, ctx.state.evaluated_at)
        await ctx.deps.common.turns.settle_agent_turn(
            ctx.state.session_id,
            BridgeTurn(role="agent", content=ctx.state.result.model_dump_json(), run_id=ctx.state.run_id),
            new_messages=[],
        )
        return End(ctx.state.result)


def reach_documents_workflow(  # noqa: C901 - explicit state and manifest binding with independent refusals
    policy: ReachPolicy, corpus: PublicCorpus, *, started_at: datetime, clock: Callable[[], datetime]
) -> Workflow:
    """Build an explicit native score; normal boot never registers this profile."""
    require_aware(started_at)

    def admitted(intent: Intent) -> DocumentsEnvelope:
        if intent.source != SOURCE or intent.sigil_name != GUEST or intent.sigil_scopes:
            msg = "documents_guest"
            raise ValueError(msg)
        envelope = DocumentsEnvelope.model_validate_json(intent.prompt)
        expected = make_documents_intent(
            policy,
            corpus,
            envelope.request,
            session_id=intent.session_id,
            started_at=started_at,
            now=envelope.prepared.prepared_at,
        )
        if envelope.started_at != started_at or envelope != DocumentsEnvelope.model_validate_json(expected.prompt):
            msg = "documents_binding"
            raise ValueError(msg)
        return envelope

    def state(intent: Intent) -> DocumentsState:
        if intent.run_id is None:
            msg = "documents_run"
            raise ValueError(msg)
        return DocumentsState(run_id=intent.run_id, session_id=intent.session_id, envelope=admitted(intent))

    def validate(intent: Intent, candidate: BaseModel) -> None:
        expected = state(intent)
        if type(candidate) is not DocumentsState or (candidate.run_id, candidate.session_id, candidate.envelope) != (
            expected.run_id,
            expected.session_id,
            expected.envelope,
        ):
            msg = "documents_checkpoint"
            raise ValueError(msg)
        DocumentsState.model_validate(candidate.model_dump(mode="python"))
        if candidate.result is not None:
            if candidate.evaluated_at is None:
                msg = "documents_checkpoint_result"
                raise ValueError(msg)
            if candidate.result != _result(candidate, policy, corpus, candidate.evaluated_at):
                msg = "documents_checkpoint_result"
                raise ValueError(msg)
        candidate.model_dump(mode="json")

    graph = build_serial_graph(
        nodes=(RevalidateDocuments, SearchDocuments, SettleDocuments),
        state_type=DocumentsState,
        deps_type=DocumentsDeps,
        output_type=ReachWorkerResult,
        name="reach_documents",
    )
    return Workflow(
        name=SOURCE,
        title="Search public documents",
        description="Deterministic excerpts in a disposable operator development generation.",
        trigger=Trigger(hint="Explicit operator documents", match=lambda intent: intent.source == SOURCE),
        graph=graph,
        start_node=RevalidateDocuments,
        make_state=state,
        validate_state=validate,
        bind_deps=lambda common: DocumentsDeps(common=common, policy=policy, corpus=corpus, clock=clock),
        manifest=PatternManifest(
            key=SOURCE,
            revision="1",
            implementation_revision="py.1",
            checkpoint_schema="reach-documents-state-v1",
            entry_node="revalidate",
            nodes=(
                PatternNode(key="revalidate", label="Revalidate request", implementation=RevalidateDocuments),
                PatternNode(key="search", label="Search public excerpts", implementation=SearchDocuments),
                PatternNode(key="settle", label="Settle operator result", implementation=SettleDocuments),
                PatternNode(key="end", label="End", kind="terminal"),
            ),
            edges=(
                PatternEdge(key="revalidate-search", source="revalidate", target="search"),
                PatternEdge(key="search-settle", source="search", target="settle"),
                PatternEdge(key="settle-end", source="settle", target="end"),
            ),
        ),
    )
