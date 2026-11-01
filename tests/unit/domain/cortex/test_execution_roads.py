"""Serial selection preserves semantic bindings and treats uncertainty as no new work."""

from __future__ import annotations

import warnings
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from lychd.domain.cortex.execution_roads import (
    RoadAmounts,
    RoadAttemptObservation,
    RoadContract,
    RoadEligibility,
    RoadPolicyError,
    RoadScope,
    RoadSelectionContext,
    RoadSelectionPolicy,
    RoadSelectionProposal,
    propose_road,
)

NOW = datetime(2026, 11, 1, tzinfo=UTC)


def _policy() -> RoadSelectionPolicy:
    contract = RoadContract(
        key="source-answer",
        revision="1",
        input_schema_ref="question@1",
        output_schema_ref="answer@1",
        completion_ref="cited-comparison@1",
        non_completion_ref="insufficient-evidence@1",
        effects_ref="read-only@1",
        validators=("citations@1", "relevance@1"),
    )
    targets = (
        {"kind": "local", "binding_ref": "local-chat@1"},
        {"kind": "portal", "target_ref": "provider-target@1"},
        {"kind": "peer", "target_ref": "enrolled-peer@1", "task_schema_ref": "source-answer@1"},
        {"kind": "delegate", "runtime_ref": "coding-runtime@1", "profile": "read"},
    )
    keys = ("local", "portal", "peer", "delegate")
    return RoadSelectionPolicy.model_validate(
        {
            "key": "source-answer-roads",
            "revision": "1",
            "pattern_key": "example.answer",
            "pattern_revision": "1",
            "station": "compare",
            "contract": contract,
            "entry": "local",
            "alternatives": tuple(
                {
                    "key": key,
                    "contract_digest": contract.digest,
                    "target": target,
                    "projection_ref": f"{key}-input@1",
                    "ceiling": {"attempts": 1, "tokens": 100, "spend_microunits": 10, "disclosure_bytes": 1000},
                }
                for key, target in zip(keys, targets, strict=True)
            ),
            "transitions": (
                {"source": "local", "target": "portal", "when": "unavailable", "priority": 0},
                {"source": "local", "target": "peer", "when": "unavailable", "priority": 1},
                {"source": "portal", "target": "delegate", "when": "failed", "priority": 0},
                {"source": "peer", "target": "delegate", "when": "failed", "priority": 0},
            ),
            "limits": {"attempts": 4, "tokens": 400, "spend_microunits": 40, "disclosure_bytes": 4000},
            "currency": "USD",
        }
    )


def _context(policy: RoadSelectionPolicy, *, after_local: bool = False) -> RoadSelectionContext:
    scope = RoadScope(
        run_id="run-1",
        occurrence_ref="compare-1",
        pattern_key=policy.pattern_key,
        pattern_revision=policy.pattern_revision,
        station=policy.station,
        policy_digest=policy.digest,
    )
    return RoadSelectionContext(
        scope=scope,
        observation_ref="owner-snapshot-1",
        deadline=NOW + timedelta(seconds=60),
        consumed=RoadAmounts(attempts=int(after_local), tokens=100 if after_local else 0),
        outstanding=RoadAmounts(),
        admission_closed=False,
        visited=("local",) if after_local else (),
        previous=RoadAttemptObservation(
            scope=scope,
            owner_ref="local-attempt-1",
            alternative="local",
            outcome="unavailable",
            disposition="not_submitted",
        )
        if after_local
        else None,
        eligibility=tuple(
            RoadEligibility(
                scope=scope,
                alternative=alternative.key,
                alternative_digest=alternative.digest,
                state="eligible",
                observed_at=NOW - timedelta(seconds=1),
                valid_until=NOW + timedelta(seconds=30),
            )
            for alternative in policy.alternatives
        ),
    )


def _eligibility(context: RoadSelectionContext, key: str, **updates: object) -> RoadSelectionContext:
    return context.model_copy(
        update={
            "eligibility": tuple(
                observation.model_copy(update=updates) if observation.alternative == key else observation
                for observation in context.eligibility
            )
        }
    )


def test_local_then_portal_proposal_is_repeatable_and_retains_owner_scope() -> None:
    policy = _policy()
    initial = propose_road(policy, _context(policy), now=NOW)
    assert initial.status == "proposed"
    assert initial.alternative is not None
    assert initial.alternative.target.kind == "local"
    context = _context(policy, after_local=True)
    before = context.model_dump_json()
    selected = propose_road(policy, context, now=NOW)
    assert selected == propose_road(policy, context, now=NOW)
    assert selected.alternative is not None
    assert selected.alternative.target.kind == "portal"
    assert selected.alternative.projection_ref == "portal-input@1"
    assert selected.scope == context.scope
    assert selected.deadline == context.deadline
    assert selected.predecessor_ref == "local-attempt-1"
    assert context.model_dump_json() == before
    assert RoadSelectionProposal.model_validate_json(selected.model_dump_json()) == selected


def test_ineligible_portal_can_leave_an_independently_eligible_peer() -> None:
    policy = _policy()
    context = _eligibility(_context(policy, after_local=True), "portal", state="ineligible")
    selected = propose_road(policy, context, now=NOW)
    assert selected.alternative is not None
    assert selected.alternative.target.kind == "peer"
    assert selected.alternative.projection_ref == "peer-input@1"


def test_settled_peer_failure_can_propose_a_declared_delegated_task() -> None:
    policy = _policy()
    context = _context(policy, after_local=True)
    assert context.previous is not None
    context = context.model_copy(
        update={
            "visited": ("local", "peer"),
            "previous": context.previous.model_copy(
                update={
                    "alternative": "peer",
                    "owner_ref": "intercom-task-1",
                    "outcome": "failed",
                    "disposition": "replacement_permitted",
                }
            ),
        }
    )
    result = propose_road(policy, context, now=NOW)
    assert result.alternative is not None
    assert result.alternative.target.kind == "delegate"
    assert result.predecessor_ref == "intercom-task-1"


@pytest.mark.parametrize("closed", [False, True])
@pytest.mark.parametrize("outcome", ["failed", "complete"])
def test_unresolved_blocks_all_new_work_even_after_expiry_or_closure(*, closed: bool, outcome: str) -> None:
    policy = _policy()
    context = _context(policy, after_local=True)
    assert context.previous is not None
    context = context.model_copy(
        update={
            "admission_closed": closed,
            "deadline": NOW,
            "previous": context.previous.model_copy(update={"disposition": "unresolved", "outcome": outcome}),
        }
    )
    result = propose_road(policy, context, now=NOW)
    assert result.status == "reconciliation_required"
    assert result.alternative is None
    assert result.predecessor_ref == "local-attempt-1"
    assert result.admission_closed is closed


def test_unknown_peer_submit_cannot_fall_back_to_an_eligible_local_implementation() -> None:
    payload = _policy().model_dump(mode="python")
    payload["entry"] = "peer"
    payload["transitions"] = (
        {"source": "peer", "target": "local", "when": "failed", "priority": 0},
        {"source": "local", "target": "portal", "when": "failed", "priority": 0},
        {"source": "portal", "target": "delegate", "when": "failed", "priority": 0},
    )
    policy = RoadSelectionPolicy.model_validate(payload)
    context = _context(policy)
    context = context.model_copy(
        update={
            "visited": ("peer",),
            "previous": RoadAttemptObservation(
                scope=context.scope,
                owner_ref="claimed-send-without-foreign-id",
                alternative="peer",
                outcome="failed",
                disposition="unresolved",
            ),
        }
    )
    assert propose_road(policy, context, now=NOW).status == "reconciliation_required"


@pytest.mark.parametrize(
    ("updates", "status"),
    [
        ({"admission_closed": True}, "closed"),
        ({"deadline": NOW}, "expired"),
        ({"outstanding": RoadAmounts(attempts=1)}, "outstanding_reservation"),
        ({"consumed": RoadAmounts(attempts=4)}, "exhausted"),
        ({"consumed": RoadAmounts(tokens=300), "outstanding": RoadAmounts(tokens=1)}, "exhausted"),
        ({"consumed": RoadAmounts(spend_microunits=30), "outstanding": RoadAmounts(spend_microunits=1)}, "exhausted"),
        ({"consumed": RoadAmounts(disclosure_bytes=3000), "outstanding": RoadAmounts(disclosure_bytes=1)}, "exhausted"),
    ],
)
def test_closure_deadline_and_shared_usage_prevent_a_new_attempt(updates: dict[str, Any], status: str) -> None:
    policy = _policy()
    context = _context(policy, after_local=True).model_copy(update=updates)
    assert propose_road(policy, context, now=NOW).status == status


def test_exact_budget_boundary_permits_only_the_declared_ceiling() -> None:
    policy = _policy()
    context = _context(policy, after_local=True).model_copy(
        update={
            "consumed": RoadAmounts(attempts=3, tokens=300, spend_microunits=30, disclosure_bytes=3000),
        }
    )
    assert propose_road(policy, context, now=NOW).status == "proposed"


@pytest.mark.parametrize("state", ["unknown", "eligible", "ineligible"])
def test_unknown_or_stale_higher_precedence_observation_blocks_lower_route(state: str) -> None:
    policy = _policy()
    context = _eligibility(_context(policy, after_local=True), "portal", state=state, valid_until=NOW)
    assert propose_road(policy, context, now=NOW).status == "eligibility_unknown"


def test_fresh_unknown_eligibility_is_not_silently_skipped() -> None:
    policy = _policy()
    context = _eligibility(_context(policy, after_local=True), "portal", state="unknown")
    assert propose_road(policy, context, now=NOW).status == "eligibility_unknown"


@pytest.mark.parametrize(
    ("outcome", "disposition", "status"),
    [
        ("complete", "replacement_permitted", "completed_observation"),
        ("failed", "replacement_forbidden", "replacement_forbidden"),
        ("insufficient", "replacement_permitted", "no_transition"),
    ],
)
def test_outcomes_neither_adopt_results_nor_invent_undeclared_transitions(
    outcome: str,
    disposition: str,
    status: str,
) -> None:
    policy = _policy()
    context = _context(policy, after_local=True)
    assert context.previous is not None
    context = context.model_copy(
        update={
            "previous": context.previous.model_copy(
                update={
                    "outcome": outcome,
                    "disposition": disposition,
                }
            )
        }
    )
    assert propose_road(policy, context, now=NOW).status == status


def test_policy_order_is_canonical_but_edge_priority_is_semantic() -> None:
    policy = _policy()
    reordered = policy.model_copy(
        update={
            "alternatives": tuple(reversed(policy.alternatives)),
            "transitions": tuple(reversed(policy.transitions)),
        }
    )
    assert reordered.digest == policy.digest
    assert propose_road(reordered, _context(policy, after_local=True), now=NOW).alternative == policy.alternatives[1]
    payload = policy.model_dump(mode="python")
    payload["transitions"][0]["priority"], payload["transitions"][1]["priority"] = 1, 0
    preferred_peer = RoadSelectionPolicy.model_validate(payload)
    assert preferred_peer.digest != policy.digest
    result = propose_road(preferred_peer, _context(preferred_peer, after_local=True), now=NOW)
    assert result.alternative is not None
    assert result.alternative.key == "peer"


@pytest.mark.parametrize(
    "mutation",
    [
        "cycle",
        "duplicate_key",
        "unknown_entry",
        "unknown_target",
        "duplicate_priority",
        "duplicate_edge",
        "unreachable",
        "contract_mismatch",
        "different_completion",
    ],
)
def test_malformed_policy_never_reaches_selection(mutation: str) -> None:
    payload = _policy().model_dump(mode="python")
    if mutation == "cycle":
        payload["transitions"] += ({"source": "delegate", "target": "local", "when": "failed", "priority": 0},)
    elif mutation == "duplicate_key":
        payload["alternatives"][1]["key"] = "local"
    elif mutation == "unknown_entry":
        payload["entry"] = "missing"
    elif mutation == "unknown_target":
        payload["transitions"][0]["target"] = "missing"
    elif mutation == "duplicate_priority":
        payload["transitions"][1]["priority"] = 0
    elif mutation == "duplicate_edge":
        payload["transitions"] += ({**payload["transitions"][0], "priority": 2},)
    elif mutation == "unreachable":
        payload["transitions"] = payload["transitions"][:1]
    elif mutation == "contract_mismatch":
        payload["alternatives"][1]["contract_digest"] = "0" * 64
    else:
        payload["contract"]["completion_ref"] = "uncited-summary@1"
    with pytest.raises((ValidationError, RoadPolicyError)):
        RoadSelectionPolicy.model_validate(payload)


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("policy", "schema_version", True),
        ("policy", "schema_version", 1.0),
        ("policy", "fallback_command", "unregistered"),
        ("ceiling", "attempts", 0),
        ("limits", "tokens", -1),
        ("limits", "tokens", True),
        ("limits", "tokens", 1.0),
        ("limits", "tokens", "1"),
        ("contract", "effects_ref", "write-tools@1"),
        ("contract", "non_completion_ref", "silent-truncation@1"),
    ],
)
def test_invalid_or_incompatible_wire_values_refuse(section: str, field: str, value: object) -> None:
    payload = _policy().model_dump(mode="python")
    if section == "policy":
        record = payload
    elif section == "ceiling":
        record = payload["alternatives"][0]["ceiling"]
    else:
        record = payload[section]
    record[field] = value
    with pytest.raises((ValidationError, RoadPolicyError)):
        RoadSelectionPolicy.model_validate(payload)


@pytest.mark.parametrize(
    "substitution", ["policy", "scope", "previous", "target", "projection", "duplicate", "visited"]
)
def test_substituted_or_unchecked_values_refuse_with_safe_code(substitution: str) -> None:
    policy = _policy()
    context = _context(policy, after_local=True)
    if substitution == "policy":
        policy = policy.model_copy(update={"revision": "2"})
    elif substitution == "scope":
        context = context.model_copy(update={"scope": context.scope.model_copy(update={"station": "other"})})
    elif substitution == "previous":
        assert context.previous is not None
        context = context.model_copy(
            update={
                "previous": context.previous.model_copy(
                    update={
                        "scope": context.scope.model_copy(update={"run_id": "other-run"}),
                    }
                )
            }
        )
    elif substitution in {"target", "projection"}:
        alternative = policy.alternatives[1]
        updates: dict[str, Any] = (
            {"projection_ref": "other-input@1"}
            if substitution == "projection"
            else {
                "target": {"kind": "portal", "target_ref": "other-provider@1"},
            }
        )
        changed = alternative.model_copy(update=updates)
        policy = policy.model_copy(update={"alternatives": (policy.alternatives[0], changed, *policy.alternatives[2:])})
        context = context.model_copy(
            update={
                "scope": context.scope.model_copy(update={"policy_digest": policy.digest}),
                "previous": context.previous.model_copy(
                    update={
                        "scope": context.scope.model_copy(
                            update={
                                "policy_digest": policy.digest,
                            }
                        )
                    }
                )
                if context.previous
                else None,
            }
        )
    elif substitution == "duplicate":
        context = context.model_copy(update={"eligibility": (context.eligibility[0],) * 4})
    else:
        context = context.model_copy(update={"visited": ("portal", "local")})
    with pytest.raises(RoadPolicyError, match=r"^road_selection_invalid$"):
        propose_road(policy, context, now=NOW)


def test_forged_nested_integer_and_naive_clock_refuse() -> None:
    policy = _policy()
    context = _context(policy).model_copy(update={"consumed": RoadAmounts().model_copy(update={"tokens": True})})
    with pytest.raises(RoadPolicyError, match=r"^road_selection_invalid$"):
        propose_road(policy, context, now=NOW)
    with pytest.raises(RoadPolicyError, match=r"^road_selection_invalid$"):
        propose_road(policy, _context(policy), now=NOW.replace(tzinfo=None))


def test_rejected_unchecked_input_never_reaches_serializer_warnings() -> None:
    policy = _policy()
    marker = "synthetic-confidential-marker"
    context = _context(policy).model_copy(
        update={
            "consumed": RoadAmounts().model_copy(update={"tokens": marker}),
        }
    )
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        with pytest.raises(RoadPolicyError, match=r"^road_selection_invalid$") as refused:
            propose_road(policy, context, now=NOW)
    assert not captured
    assert marker not in str(refused.value)


@pytest.mark.parametrize("location", ["policy", "context", "amounts", "target"])
def test_undeclared_fields_in_unchecked_copies_are_not_silently_dropped(location: str) -> None:
    policy, context = _policy(), _context(_policy())
    extra = {"unregistered_command": "synthetic-marker"}
    if location == "policy":
        policy = policy.model_copy(update=extra)
    elif location == "context":
        context = context.model_copy(update=extra)
    elif location == "amounts":
        context = context.model_copy(update={"outstanding": RoadAmounts().model_copy(update=extra)})
    else:
        alternative = policy.alternatives[0]
        changed = alternative.model_copy(update={"target": alternative.target.model_copy(update=extra)})
        policy = policy.model_copy(update={"alternatives": (changed, *policy.alternatives[1:])})
    with pytest.raises(RoadPolicyError, match=r"^road_selection_invalid$"):
        propose_road(policy, context, now=NOW)


def test_foreign_occurrence_eligibility_is_rejected() -> None:
    policy = _policy()
    context = _context(policy)
    context = _eligibility(context, "local", scope=context.scope.model_copy(update={"occurrence_ref": "other"}))
    with pytest.raises(RoadPolicyError, match=r"^road_selection_invalid$"):
        propose_road(policy, context, now=NOW)


def test_future_observation_is_unknown() -> None:
    policy = _policy()
    context = _eligibility(_context(policy, after_local=True), "portal", observed_at=NOW + timedelta(seconds=1))
    assert propose_road(policy, context, now=NOW).status == "eligibility_unknown"


def test_declared_cheaper_alternative_can_fit_the_same_remaining_envelope() -> None:
    payload = _policy().model_dump(mode="python")
    payload["alternatives"][2]["ceiling"]["tokens"] = 50
    policy = RoadSelectionPolicy.model_validate(payload)
    context = _context(policy, after_local=True).model_copy(update={"consumed": RoadAmounts(tokens=350)})
    result = propose_road(policy, context, now=NOW)
    assert result.alternative is not None
    assert result.alternative.key == "peer"


@pytest.mark.parametrize("disposition", ["replacement_permitted", "replacement_forbidden"])
def test_local_closure_dominates_a_late_completed_observation(disposition: str) -> None:
    policy = _policy()
    context = _context(policy, after_local=True)
    assert context.previous is not None
    context = context.model_copy(
        update={
            "admission_closed": True,
            "previous": context.previous.model_copy(update={"outcome": "complete", "disposition": disposition}),
        }
    )
    assert propose_road(policy, context, now=NOW).status == "closed"


def test_unstarted_attempt_cannot_claim_completion() -> None:
    policy = _policy()
    context = _context(policy, after_local=True)
    assert context.previous is not None
    context = context.model_copy(update={"previous": context.previous.model_copy(update={"outcome": "complete"})})
    with pytest.raises(RoadPolicyError, match=r"^road_selection_invalid$"):
        propose_road(policy, context, now=NOW)


@pytest.mark.parametrize("state", ["eligible", "ineligible", "unknown"])
def test_initial_selection_does_not_invent_a_predecessor_outcome(
    state: Literal["eligible", "ineligible", "unknown"],
) -> None:
    policy = _policy()
    result = propose_road(policy, _eligibility(_context(policy), "local", state=state), now=NOW)
    assert (
        result.status == {"eligible": "proposed", "ineligible": "ineligible", "unknown": "eligibility_unknown"}[state]
    )
    assert result.predecessor_ref is None


def _timed_context(
    policy: RoadSelectionPolicy, start: datetime, end: datetime, deadline: datetime
) -> RoadSelectionContext:
    context = _context(policy)
    return context.model_copy(
        update={
            "deadline": deadline,
            "eligibility": tuple(
                observation.model_copy(update={"observed_at": start, "valid_until": end})
                for observation in context.eligibility
            ),
        }
    )


def test_deadline_compares_instants_during_repeated_local_hour() -> None:
    policy = _policy()
    zone = ZoneInfo("Europe/Bratislava")
    deadline = datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=0)
    now = datetime(2026, 10, 25, 2, 15, tzinfo=zone, fold=1)
    context = _timed_context(
        policy, datetime(2026, 10, 25, tzinfo=UTC), datetime(2026, 10, 25, 2, tzinfo=UTC), deadline
    )
    result = propose_road(policy, context, now=now)
    assert result.status == "expired"
    assert result.deadline == deadline


@pytest.mark.parametrize(
    ("start_fold", "start_minute", "end_minute", "now_fold", "now_minute", "status"),
    [
        (0, 45, 15, 1, 0, "proposed"),
        (1, 15, 45, 0, 30, "eligibility_unknown"),
        (0, 30, 45, 1, 15, "proposed"),
    ],
)
def test_eligibility_uses_utc_instants_across_fold(
    start_fold: int,
    start_minute: int,
    end_minute: int,
    now_fold: int,
    now_minute: int,
    status: str,
) -> None:
    policy = _policy()
    zone = ZoneInfo("Europe/Bratislava")
    start = datetime(2026, 10, 25, 2, start_minute, tzinfo=zone, fold=start_fold)
    end = datetime(2026, 10, 25, 2, end_minute, tzinfo=zone, fold=1)
    now = datetime(2026, 10, 25, 2, now_minute, tzinfo=zone, fold=now_fold)
    context = _timed_context(policy, start, end, datetime(2026, 10, 25, 2, tzinfo=UTC))
    assert propose_road(policy, context, now=now).status == status
