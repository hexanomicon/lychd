"""One consented model-free feed observation; material never enters a checkpoint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from pydantic_graph import BaseNode, End, GraphRunContext

from lychd.agents.services import WorkflowServices
from lychd.agents.workflows.base import Gate, PatternEdge, PatternManifest, PatternNode, Trigger, Workflow
from lychd.compositions.scavenger.ports import ObservationCommit
from lychd.domain.cortex.graph import build_serial_graph
from lychd.domain.cortex.runs import ConsentPending
from lychd.domain.webcrawler.feed import WebcrawlerFeedBinding
from lychd.domain.webcrawler.profile import WebcrawlerReviewRef, WebcrawlerWorkflowCode, WebcrawlerWorkflowError

if TYPE_CHECKING:
    from lychd.agents.router import Intent
    from lychd.compositions.scavenger.ports import ScavengerWorkflowPort
    from lychd.domain.webcrawler.feed import WebcrawlerFeedWorkflowPort


class ObserveMarketState(BaseModel):
    """Only admitted references and safe review/result facts survive durable parking."""

    model_config = ConfigDict(serialize_by_alias=True, extra="forbid", hide_input_in_errors=True)
    run_id: str
    webcrawler: WebcrawlerFeedBinding = Field(
        repr=False, validation_alias=AliasChoices("webcrawler", "scout"), serialization_alias="scout"
    )
    review: WebcrawlerReviewRef | None = None
    pending_consent_id: str | None = None
    commit: ObservationCommit | None = None


def _ports(services: WorkflowServices) -> tuple[WebcrawlerFeedWorkflowPort, ScavengerWorkflowPort]:
    if services.feed_webcrawler is None or services.scavenger is None:
        raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.ADMISSION)
    return services.feed_webcrawler, services.scavenger


def _review(state: ObserveMarketState) -> WebcrawlerReviewRef:
    if state.review is None:
        raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
    return state.review


@dataclass
class PrepareFeedReview(BaseNode[ObserveMarketState, WorkflowServices]):
    """Resolve a retained commit first; otherwise prepare one exact native review."""

    async def run(
        self, ctx: GraphRunContext[ObserveMarketState, WorkflowServices]
    ) -> AwaitFeedConsent | FinishMarketObservation:
        webcrawler, app = _ports(ctx.deps)
        state = ctx.state
        state.commit = await app.committed(run_id=str(state.run_id), binding=state.webcrawler)
        if state.commit is not None:
            return FinishMarketObservation()
        state.review = await webcrawler.prepare(run_id=str(state.run_id), binding=state.webcrawler)
        state.pending_consent_id = str(state.review.consent_id)
        return AwaitFeedConsent()


@dataclass
class AwaitFeedConsent(Gate, BaseNode[ObserveMarketState, WorkflowServices]):
    """Park without a model lease, source material or acquisition claim."""

    async def run(
        self, ctx: GraphRunContext[ObserveMarketState, WorkflowServices]
    ) -> AwaitFeedConsent | AcquireMarketField:
        webcrawler, _ = _ports(ctx.deps)
        verdict = await webcrawler.consent(
            run_id=str(ctx.state.run_id), binding=ctx.state.webcrawler, review=_review(ctx.state)
        )
        if verdict == "pending":
            raise ConsentPending(str(_review(ctx.state).consent_id), str(ctx.state.run_id), "webcrawler.public-feed")
        ctx.state.pending_consent_id = None
        if verdict != "granted":
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.CONSENT)
        return AcquireMarketField()


@dataclass
class AcquireMarketField(BaseNode[ObserveMarketState, WorkflowServices]):
    """Consume once and atomically adopt the whole field outside Graph state."""

    async def run(self, ctx: GraphRunContext[ObserveMarketState, WorkflowServices]) -> FinishMarketObservation:
        webcrawler, app = _ports(ctx.deps)
        state, run_id = ctx.state, str(ctx.state.run_id)
        # A previous commit can outlive its response or this node's checkpoint.
        state.commit = await app.committed(run_id=run_id, binding=state.webcrawler)
        if state.commit is None:
            review = _review(state)
            material = await webcrawler.acquire(run_id=run_id, binding=state.webcrawler, review=review)
            webcrawler.authorize_feed_consume(run_id=run_id, binding=state.webcrawler, review=review, material=material)
            state.commit = await app.adopt(run_id=run_id, binding=state.webcrawler, review=review, material=material)
        return FinishMarketObservation()


@dataclass
class FinishMarketObservation(BaseNode[ObserveMarketState, WorkflowServices, ObservationCommit]):
    """Recheck application custody and authority, including after checkpoint recovery."""

    async def run(self, ctx: GraphRunContext[ObserveMarketState, WorkflowServices]) -> End[ObservationCommit]:
        _, app = _ports(ctx.deps)
        current = await app.committed(run_id=str(ctx.state.run_id), binding=ctx.state.webcrawler)
        if current is None or current != ctx.state.commit:
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.SETTLEMENT)
        return End(current)


def _make_state(intent: Intent) -> ObserveMarketState:
    binding = intent.admitted_webcrawler
    if (
        type(binding) is not WebcrawlerFeedBinding
        or intent.run_id is None
        or intent.source != "scavenger"
        or intent.admitted_capability_key is not None
        or intent.prompt != str(binding.consumer.application_admission_id)
    ):
        raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.ADMISSION)
    return ObserveMarketState(run_id=intent.run_id, webcrawler=binding)


def _validate_state(intent: Intent, state: BaseModel) -> None:
    expected = _make_state(intent)
    if (
        type(state) is not ObserveMarketState
        or state.run_id != expected.run_id
        or state.webcrawler != expected.webcrawler
        or (
            state.pending_consent_id is not None
            and (state.review is None or state.pending_consent_id != str(state.review.consent_id))
        )
    ):
        raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)


OBSERVE_MARKET_GRAPH = build_serial_graph(
    nodes=(PrepareFeedReview, AwaitFeedConsent, AcquireMarketField, FinishMarketObservation),
    state_type=ObserveMarketState,
    deps_type=WorkflowServices,
    output_type=ObservationCommit,
    name="scavenger_observe_market",
)

OBSERVE_MARKET = Workflow(
    name="scavenger.observe_market",
    title="Observe public market feed",
    description="Consent to one finite title/link field, then retain it for local viewing.",
    trigger=Trigger(hint="explicit Scavenger observation", match=lambda intent: intent.source == "scavenger"),
    graph=OBSERVE_MARKET_GRAPH,
    start_node=PrepareFeedReview,
    make_state=_make_state,
    validate_state=_validate_state,
    manifest=PatternManifest(
        key="scavenger.observe_market",
        revision="2",
        implementation_revision="py.2",
        checkpoint_schema="scavenger-feed-state-v1",
        entry_node="prepare_feed_review",
        nodes=(
            PatternNode(key="prepare_feed_review", label="Prepare feed review", implementation=PrepareFeedReview),
            PatternNode(
                key="await_feed_consent", label="Await feed consent", kind="gate", implementation=AwaitFeedConsent
            ),
            PatternNode(key="acquire_market_field", label="Acquire market field", implementation=AcquireMarketField),
            PatternNode(
                key="finish_market_observation", label="Confirm retained field", implementation=FinishMarketObservation
            ),
            PatternNode(key="end", label="End", kind="terminal"),
        ),
        edges=(
            PatternEdge(key="prepare-to-consent", source="prepare_feed_review", target="await_feed_consent"),
            PatternEdge(key="prepare-to-finish", source="prepare_feed_review", target="finish_market_observation"),
            PatternEdge(key="consent-waits", source="await_feed_consent", target="await_feed_consent"),
            PatternEdge(key="consent-to-acquire", source="await_feed_consent", target="acquire_market_field"),
            PatternEdge(key="acquire-to-finish", source="acquire_market_field", target="finish_market_observation"),
            PatternEdge(key="finish-to-end", source="finish_market_observation", target="end"),
        ),
    ),
)
