"""Explicit inert connected preparation Pattern; construction never installs a route."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from pydantic_graph import BaseNode, End, GraphRunContext

from lychd.agents.router import Intent
from lychd.agents.services import WorkflowServices
from lychd.agents.workflows.base import PatternEdge, PatternManifest, PatternNode, Trigger, Workflow
from lychd.compositions.reach.connected.policy import prepare_batch
from lychd.compositions.reach.connected.providers import build_request
from lychd.compositions.reach.connected.schemas import (
    ConnectedPolicy,
    CorrespondenceRequest,
    Digest,
    PreparedBatch,
    PreparedRequest,
    Record,
    record_digest,
)
from lychd.compositions.reach.schemas import require_aware
from lychd.domain.cortex.graph import build_serial_graph

_SOURCE = "reach.connect.prepare"
_GUEST = "reach.guest"


class ConnectedPreparationRefused(ValueError):  # noqa: N818 - content-free domain refusal
    """A request cannot enter this no-effect preparation profile."""

    def __init__(self) -> None:
        """Expose only the content-free refusal across the ingress boundary."""
        super().__init__("Connected Reach preparation refused.")


class ConnectedPreparationResult(Record):
    """A finite application plan or content-free refusal, never effect authority."""

    reason: Literal["prepared", "expired", "clock_before_preparation", "preparation_refused"]
    policy_digest: Digest
    evaluated_at: AwareDatetime
    requests: tuple[PreparedRequest, ...] = Field(default=(), max_length=32, repr=False)

    @model_validator(mode="after")
    def coherent_result(self) -> Self:
        if (self.reason == "prepared") != bool(self.requests):
            msg = "Connected Reach result and application plans disagree."
            raise ValueError(msg)
        return self


class ConnectedPreparationState(BaseModel):
    """Only declared JSON continuation data; live handles belong in dependencies."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True, hide_input_in_errors=True)

    schema_version: Literal[1] = 1
    run_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    intent_digest: Digest
    prepared: PreparedBatch = Field(repr=False)
    result: ConnectedPreparationResult | None = Field(default=None, repr=False)

    @field_validator("schema_version", mode="before")
    @classmethod
    def original_schema_version(cls, value: object) -> object:
        if type(value) is not int:
            msg = "Connected Reach schema revision requires an original integer."
            raise ValueError(msg)
        return value


def _exact_batch(policy: ConnectedPolicy, batch: PreparedBatch) -> PreparedBatch:
    """Reconstruct the original admission without manufacturing another TTL."""
    try:
        batch = PreparedBatch.model_validate(batch.model_dump(mode="python"))
        expected = prepare_batch(policy, tuple(item.request for item in batch.operations), now=batch.prepared_at)
    except ValueError:
        raise ConnectedPreparationRefused from None
    if batch != expected:
        raise ConnectedPreparationRefused
    return expected


def _evaluate(policy: ConnectedPolicy, batch: PreparedBatch, *, now: datetime) -> ConnectedPreparationResult:
    require_aware(now)
    exact = _exact_batch(policy, batch)
    reason: Literal["prepared", "expired", "clock_before_preparation", "preparation_refused"]
    requests: tuple[PreparedRequest, ...] = ()
    if now < exact.prepared_at:
        reason = "clock_before_preparation"
    elif now >= exact.expires_at:
        reason = "expired"
    else:
        try:
            # Every operation already passed policy preflight. A failed builder
            # discards this local tuple, so no partial plan reaches the sink.
            requests = tuple(build_request(item) for item in exact.operations)
            reason = "prepared"
        except ValueError:
            reason = "preparation_refused"
    return ConnectedPreparationResult(
        reason=reason, policy_digest=exact.policy_digest, evaluated_at=now, requests=requests
    )


def make_connected_intent(
    policy: ConnectedPolicy,
    requests: tuple[CorrespondenceRequest, ...],
    *,
    session_id: str,
    now: datetime,
) -> Intent:
    """Preflight one explicit finite batch, including a single request as a tuple."""
    require_aware(now)
    if not session_id.strip():
        raise ConnectedPreparationRefused
    try:
        prepared = prepare_batch(policy, requests, now=now)
        result = _evaluate(policy, prepared, now=now)
    except ValueError:
        raise ConnectedPreparationRefused from None
    if result.reason != "prepared":
        raise ConnectedPreparationRefused
    return Intent(
        session_id=session_id,
        prompt=prepared.model_dump_json(),
        source=_SOURCE,
        sigil_name=_GUEST,
        sigil_scopes=frozenset(),
    )


@dataclass(frozen=True, kw_only=True)
class ConnectedPreparationDeps:
    """Worker handles; the supplied sink makes no durable application guarantee."""

    common: WorkflowServices
    policy: ConnectedPolicy
    clock: Callable[[], datetime]
    record_result: Callable[[ConnectedPreparationResult], None]


@dataclass
class PrepareConnectedReach(BaseNode[ConnectedPreparationState, ConnectedPreparationDeps]):
    async def run(
        self, ctx: GraphRunContext[ConnectedPreparationState, ConnectedPreparationDeps]
    ) -> ProjectConnectedReach:
        if ctx.state.result is not None:
            raise ConnectedPreparationRefused
        ctx.state.result = _evaluate(ctx.deps.policy, ctx.state.prepared, now=ctx.deps.clock())
        return ProjectConnectedReach()


@dataclass
class ProjectConnectedReach(BaseNode[ConnectedPreparationState, ConnectedPreparationDeps, ConnectedPreparationResult]):
    async def run(
        self, ctx: GraphRunContext[ConnectedPreparationState, ConnectedPreparationDeps]
    ) -> End[ConnectedPreparationResult]:
        previous = ctx.state.result
        if previous is None or previous != _evaluate(ctx.deps.policy, ctx.state.prepared, now=previous.evaluated_at):
            raise ConnectedPreparationRefused
        now = ctx.deps.clock()
        require_aware(now)
        # Refused preparation cannot be resurrected by moving the clock backward.
        # A previously prepared plan is rebuilt only inside its ORIGINAL interval.
        result = _evaluate(ctx.deps.policy, ctx.state.prepared, now=now) if previous.reason == "prepared" else previous
        ctx.state.result = result
        ctx.deps.record_result(result)
        return End(result)


def connected_preparation_workflow(
    policy: ConnectedPolicy,
    *,
    clock: Callable[[], datetime],
    record_result: Callable[[ConnectedPreparationResult], None],
) -> Workflow:
    """Build reach.connect.prepare@1 explicitly, with no registration or effect scopes."""
    # Detach the complete validated policy from a potentially unchecked model_copy.
    policy = ConnectedPolicy.model_validate(policy.model_dump(mode="python"))

    def admitted(intent: Intent) -> PreparedBatch:
        if (
            intent.source != _SOURCE
            or intent.sigil_name != _GUEST
            or intent.sigil_scopes
            or not intent.session_id.strip()
        ):
            raise ConnectedPreparationRefused
        try:
            batch = PreparedBatch.model_validate_json(intent.prompt)
        except ValidationError:
            raise ConnectedPreparationRefused from None
        exact = _exact_batch(policy, batch)
        # Unsupported provider operations cannot become an admitted success.
        if _evaluate(policy, exact, now=exact.prepared_at).reason != "prepared":
            raise ConnectedPreparationRefused
        return exact

    def state(intent: Intent) -> ConnectedPreparationState:
        if intent.run_id is None:
            raise ConnectedPreparationRefused
        return ConnectedPreparationState(
            run_id=intent.run_id,
            session_id=intent.session_id,
            intent_digest=record_digest(intent),
            prepared=admitted(intent),
        )

    def validate(intent: Intent, candidate: BaseModel) -> None:
        expected = admitted(intent)
        if (
            type(candidate) is not ConnectedPreparationState
            or candidate.run_id != intent.run_id
            or candidate.session_id != intent.session_id
            or candidate.intent_digest != record_digest(intent)
            or candidate.prepared != expected
        ):
            raise ConnectedPreparationRefused
        ConnectedPreparationState.model_validate(candidate.model_dump(mode="python"))
        if candidate.result is not None and candidate.result != _evaluate(
            policy, expected, now=candidate.result.evaluated_at
        ):
            raise ConnectedPreparationRefused
        candidate.model_dump(mode="json")

    graph = build_serial_graph(
        nodes=(PrepareConnectedReach, ProjectConnectedReach),
        state_type=ConnectedPreparationState,
        deps_type=ConnectedPreparationDeps,
        output_type=ConnectedPreparationResult,
        name="reach_connected_preparation",
    )
    return Workflow(
        name=_SOURCE,
        title="Prepare connected correspondence",
        description="Prepare a finite exact-target batch without credentials, transport or delivery.",
        trigger=Trigger(hint="Explicit connected Reach preparation", match=lambda intent: intent.source == _SOURCE),
        graph=graph,
        start_node=PrepareConnectedReach,
        make_state=state,
        validate_state=validate,
        bind_deps=lambda common: ConnectedPreparationDeps(
            common=common, policy=policy, clock=clock, record_result=record_result
        ),
        manifest=PatternManifest(
            key=_SOURCE,
            revision="1",
            implementation_revision="py.1",
            checkpoint_schema="reach-connected-preparation-state-v1",
            entry_node="prepare",
            nodes=(
                PatternNode(key="prepare", label="Prepare finite batch", implementation=PrepareConnectedReach),
                PatternNode(key="project", label="Project exact plan", implementation=ProjectConnectedReach),
                PatternNode(key="end", label="End", kind="terminal"),
            ),
            edges=(
                PatternEdge(key="prepare-to-project", source="prepare", target="project"),
                PatternEdge(key="project-to-end", source="project", target="end"),
            ),
        ),
    )
