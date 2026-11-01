"""Pure serial road-selection proposals, without admission, execution or custody.

The caller supplies an owner snapshot. Shape validation cannot authenticate its
facts, prevent replay, reserve capacity or persist ADR 28's ExecutionRoadDecision.
Existing road owners must perform those operations before any proposed work.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated, Literal, Self, cast

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

type Reference = Annotated[
    str, Field(strict=True, min_length=1, max_length=256, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:@/-]*$")
]
type Digest = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
type Amount = Annotated[int, Field(strict=True, ge=0, le=2**63 - 1)]
type Failure = Literal["unavailable", "failed", "insufficient", "invalid"]
_MAX_INPUT_DEPTH = 16
_MAX_INPUT_ITEMS = 128


class RoadPolicyError(ValueError):
    """A content-free refusal of malformed or substituted selection inputs."""

    def __init__(self) -> None:
        """Expose a stable refusal without serialized input or provider diagnostics."""
        super().__init__("road_selection_invalid")


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True, revalidate_instances="always")


def _digest(value: _Record) -> str:
    payload = json.dumps(
        value.model_dump(mode="json", warnings=False), sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return sha256(payload.encode()).hexdigest()


def _selection_payload(value: object, depth: int = 0) -> object:
    """Preserve unchecked extras for validation without invoking warning-producing serializers."""
    if depth > _MAX_INPUT_DEPTH:
        raise RoadPolicyError
    if isinstance(value, _Record):
        if set(vars(value)) != set(type(value).model_fields) or value.__pydantic_extra__:
            raise RoadPolicyError
        return {key: _selection_payload(item, depth + 1) for key, item in vars(value).items()}
    if isinstance(value, dict):
        mapping = cast("dict[object, object]", value)
        if len(mapping) > _MAX_INPUT_ITEMS:
            raise RoadPolicyError
        return {key: _selection_payload(item, depth + 1) for key, item in mapping.items()}
    if isinstance(value, (tuple, list)):
        items = cast("tuple[object, ...] | list[object]", value)
        if len(items) > _MAX_INPUT_ITEMS:
            raise RoadPolicyError
        return tuple(_selection_payload(item, depth + 1) for item in items)
    return value


class RoadContract(_Record):
    """Exact declared semantics; matching references do not prove actual conformance."""

    key: Reference
    revision: Reference
    input_schema_ref: Reference
    output_schema_ref: Reference
    completion_ref: Reference
    non_completion_ref: Reference
    effects_ref: Reference
    validators: tuple[Reference, ...] = Field(min_length=1, max_length=16)

    @property
    def digest(self) -> str:
        return _digest(self)


class RoadAmounts(_Record):
    """Exact units: semantic attempts, tokens, currency microunits and disclosure bytes."""

    attempts: Amount = 0
    tokens: Amount = 0
    spend_microunits: Amount = 0
    disclosure_bytes: Amount = 0

    def fits(self, consumed: RoadAmounts, outstanding: RoadAmounts, limits: RoadAmounts) -> bool:
        """Include all supplied usage and unresolved reservations without modifying them."""
        return all(
            getattr(consumed, key) + getattr(outstanding, key) + getattr(self, key) <= getattr(limits, key)
            for key in type(self).model_fields
        )


class LocalRoad(_Record):
    """One registered local deterministic or cognitive implementation binding."""

    kind: Literal["local"] = "local"
    binding_ref: Reference


class PortalRoad(_Record):
    """One declared provider target; this reference grants no egress permission."""

    kind: Literal["portal"] = "portal"
    target_ref: Reference


class PeerRoad(_Record):
    """A sovereign public task target, without sender-selected peer models."""

    kind: Literal["peer"] = "peer"
    target_ref: Reference
    task_schema_ref: Reference


class DelegatedRoad(_Record):
    """An exact foreign-runtime binding with an independently admitted containment profile."""

    kind: Literal["delegate"] = "delegate"
    runtime_ref: Reference
    profile: Literal["read", "candidate", "verify"]


type RoadTarget = Annotated[LocalRoad | PortalRoad | PeerRoad | DelegatedRoad, Field(discriminator="kind")]


class RoadAlternative(_Record):
    """A declared alternative, including its own input projection and complete next ceiling."""

    key: Reference
    contract_digest: Digest
    target: RoadTarget
    projection_ref: Reference
    ceiling: RoadAmounts

    @property
    def digest(self) -> str:
        return _digest(self)


class RoadTransition(_Record):
    """Explicit failure predicate with unique precedence among one source's edges."""

    source: Reference
    target: Reference
    when: Failure
    priority: int = Field(strict=True, ge=0, le=127)


class RoadSelectionPolicy(_Record):
    """A bounded selection subset, not the complete durable ExecutionRoadPolicy contract."""

    schema_version: Literal[1] = 1
    key: Reference
    revision: Reference
    pattern_key: Reference
    pattern_revision: Reference
    station: Reference
    contract: RoadContract
    entry: Reference
    alternatives: tuple[RoadAlternative, ...] = Field(min_length=1, max_length=32)
    transitions: tuple[RoadTransition, ...] = Field(max_length=128)
    limits: RoadAmounts
    currency: Annotated[str, Field(strict=True, pattern=r"^[A-Z]{3}$")]

    @field_validator("schema_version", mode="before")
    @classmethod
    def exact_version(cls, value: object) -> object:
        if type(value) is not int or value != 1:
            raise RoadPolicyError
        return value

    @model_validator(mode="after")
    def coherent_graph(self) -> Self:
        keys = {alternative.key for alternative in self.alternatives}
        if len(keys) != len(self.alternatives) or self.entry not in keys or self.limits.attempts == 0:
            raise RoadPolicyError
        for alternative in self.alternatives:
            if alternative.contract_digest != self.contract.digest or alternative.ceiling.attempts != 1:
                raise RoadPolicyError
        priorities: set[tuple[str, int]] = set()
        edges: set[tuple[str, str, str]] = set()
        for edge in self.transitions:
            identity = (edge.source, edge.target, edge.when)
            if (
                edge.source not in keys
                or edge.target not in keys
                or (edge.source, edge.priority) in priorities
                or identity in edges
            ):
                raise RoadPolicyError
            priorities.add((edge.source, edge.priority))
            edges.add(identity)
        self._validate_dag(keys)
        return self

    def _validate_dag(self, keys: set[str]) -> None:
        seen: set[str] = set()
        active: set[str] = set()

        def visit(key: str) -> None:
            if key in active:
                raise RoadPolicyError
            if key in seen:
                return
            active.add(key)
            for edge in self.transitions:
                if edge.source == key:
                    visit(edge.target)
            active.remove(key)
            seen.add(key)

        visit(self.entry)
        if seen != keys:
            raise RoadPolicyError

    @property
    def digest(self) -> str:
        """Canonicalize unordered declarations while preserving explicit edge precedence."""
        value = self.model_dump(mode="json", warnings=False)
        value["alternatives"] = sorted(value["alternatives"], key=lambda item: item["key"])
        value["transitions"] = sorted(value["transitions"], key=lambda item: (item["source"], item["priority"]))
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return sha256(encoded).hexdigest()


class RoadScope(_Record):
    """Owner-retained occurrence and immutable policy binding; never minted by the planner."""

    run_id: Reference
    occurrence_ref: Reference
    pattern_key: Reference
    pattern_revision: Reference
    station: Reference
    policy_digest: Digest


class RoadAttemptObservation(_Record):
    """Road-owner evidence, never inferred from exception names or accepted byte counts.

    replacement_permitted is an explicit owner disposition about safe new work,
    not merely terminal status. A claimed A2A submit cannot become not_submitted.
    This value cannot authenticate either assertion or authorize transport replay.
    """

    scope: RoadScope
    owner_ref: Reference
    alternative: Reference
    outcome: Failure | Literal["complete"]
    disposition: Literal["not_submitted", "replacement_permitted", "unresolved", "replacement_forbidden"]

    @model_validator(mode="after")
    def possible_completion(self) -> Self:
        if self.outcome == "complete" and self.disposition == "not_submitted":
            raise RoadPolicyError
        return self


class RoadEligibility(_Record):
    """A time-bounded owner observation, bound to exact target/projection declaration bytes."""

    scope: RoadScope
    alternative: Reference
    alternative_digest: Digest
    state: Literal["eligible", "ineligible", "unknown"]
    observed_at: AwareDatetime
    valid_until: AwareDatetime

    @model_validator(mode="after")
    def finite_window(self) -> Self:
        if self.valid_until.astimezone(UTC) <= self.observed_at.astimezone(UTC):
            raise RoadPolicyError
        return self


class RoadSelectionContext(_Record):
    """A supplied snapshot, not a ledger, live authority or proof against stale replay."""

    scope: RoadScope
    observation_ref: Reference
    deadline: AwareDatetime
    consumed: RoadAmounts
    outstanding: RoadAmounts
    admission_closed: bool = Field(strict=True)
    visited: tuple[Reference, ...] = Field(max_length=32)
    previous: RoadAttemptObservation | None
    eligibility: tuple[RoadEligibility, ...] = Field(min_length=1, max_length=32)


type SelectionStatus = Literal[
    "proposed",
    "closed",
    "reconciliation_required",
    "replacement_forbidden",
    "completed_observation",
    "expired",
    "outstanding_reservation",
    "exhausted",
    "no_transition",
    "ineligible",
    "eligibility_unknown",
]


class RoadSelectionProposal(_Record):
    """Calculation only: no reservation, grant, execution decision or result adoption.

    Every proposed alternative still needs fresh owner admission, input projection,
    atomic budget reservation and the full persisted road decision before use.
    Reconciliation_required grants no polling or retransmission authority.
    """

    status: SelectionStatus
    scope: RoadScope
    observation_ref: Reference
    predecessor_ref: Reference | None
    deadline: AwareDatetime
    alternative: RoadAlternative | None = None
    admission_closed: bool

    @model_validator(mode="after")
    def coherent_proposal(self) -> Self:
        if (self.status == "proposed") != (self.alternative is not None):
            raise RoadPolicyError
        return self


def _validate_context(policy: RoadSelectionPolicy, context: RoadSelectionContext) -> None:
    scope = context.scope
    if (scope.policy_digest, scope.pattern_key, scope.pattern_revision, scope.station) != (
        policy.digest,
        policy.pattern_key,
        policy.pattern_revision,
        policy.station,
    ):
        raise RoadPolicyError
    alternatives = {alternative.key: alternative for alternative in policy.alternatives}
    observations = {observation.alternative: observation for observation in context.eligibility}
    if len(observations) != len(context.eligibility) or set(observations) != set(alternatives):
        raise RoadPolicyError
    if any(
        observations[key].scope != scope or observations[key].alternative_digest != alternative.digest
        for key, alternative in alternatives.items()
    ):
        raise RoadPolicyError
    if len(set(context.visited)) != len(context.visited) or not set(context.visited) <= set(alternatives):
        raise RoadPolicyError
    previous = context.previous
    if previous is None:
        if context.visited:
            raise RoadPolicyError
        return
    if previous.scope != scope or not context.visited or context.visited[-1] != previous.alternative:
        raise RoadPolicyError
    if context.visited[0] != policy.entry or any(
        not any(edge.source == source and edge.target == target for edge in policy.transitions)
        for source, target in zip(context.visited, context.visited[1:], strict=False)
    ):
        raise RoadPolicyError


def _candidates(policy: RoadSelectionPolicy, context: RoadSelectionContext) -> tuple[str, ...]:
    if context.previous is None:
        return (policy.entry,)
    return tuple(
        edge.target
        for edge in sorted(policy.transitions, key=lambda edge: edge.priority)
        if edge.source == context.previous.alternative and edge.when == context.previous.outcome
    )


def _stopping_status(context: RoadSelectionContext, now: datetime) -> SelectionStatus | None:
    """Keep safety dispositions ahead of new-work expiry, eligibility and capacity checks."""
    previous = context.previous
    conditions: tuple[tuple[bool, SelectionStatus], ...] = (
        (previous is not None and previous.disposition == "unresolved", "reconciliation_required"),
        (context.admission_closed, "closed"),
        (previous is not None and previous.disposition == "replacement_forbidden", "replacement_forbidden"),
        (previous is not None and previous.outcome == "complete", "completed_observation"),
        (now >= context.deadline, "expired"),
        (context.outstanding.attempts > 0, "outstanding_reservation"),
    )
    return next((status for matched, status in conditions if matched), None)


def _choose_alternative(
    policy: RoadSelectionPolicy, context: RoadSelectionContext, now: datetime
) -> tuple[SelectionStatus, RoadAlternative | None]:
    candidates = _candidates(policy, context)
    if not candidates:
        return "no_transition", None
    alternatives = {alternative.key: alternative for alternative in policy.alternatives}
    observations = {observation.alternative: observation for observation in context.eligibility}
    exhausted = False
    for key in candidates:
        alternative, observation = alternatives[key], observations[key]
        if not observation.observed_at <= now < observation.valid_until or observation.state == "unknown":
            return "eligibility_unknown", None
        if observation.state == "ineligible":
            continue
        if not alternative.ceiling.fits(context.consumed, context.outstanding, policy.limits):
            exhausted = True
            continue
        return "proposed", alternative
    return ("exhausted" if exhausted else "ineligible"), None


def _validated_inputs(
    policy: object, context: object, now: object
) -> tuple[RoadSelectionPolicy, RoadSelectionContext, datetime]:
    try:
        if not isinstance(now, datetime) or now.utcoffset() is None:
            raise RoadPolicyError
        if not isinstance(policy, RoadSelectionPolicy) or not isinstance(context, RoadSelectionContext):
            raise RoadPolicyError
        policy = RoadSelectionPolicy.model_validate(_selection_payload(policy))
        context = RoadSelectionContext.model_validate(_selection_payload(context))
    except (ValueError, TypeError, AttributeError):
        raise RoadPolicyError from None
    return policy, context, now.astimezone(UTC)


def propose_road(policy: RoadSelectionPolicy, context: RoadSelectionContext, *, now: datetime) -> RoadSelectionProposal:
    """Recommend one serial alternative from revalidated inputs without performing effects."""
    policy, context, now = _validated_inputs(policy, context, now)
    _validate_context(policy, context)
    status = _stopping_status(context, now)
    alternative = None
    if status is None:
        status, alternative = _choose_alternative(policy, context, now)
    return RoadSelectionProposal(
        status=status,
        scope=context.scope,
        observation_ref=context.observation_ref,
        predecessor_ref=context.previous.owner_ref if context.previous is not None else None,
        deadline=context.deadline,
        alternative=alternative,
        admission_closed=context.admission_closed,
    )
