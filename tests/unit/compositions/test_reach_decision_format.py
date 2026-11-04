"""The fixed provider shapes retain typed requirements and explicit public-review claims."""

from __future__ import annotations

from typing import Any

import pytest

from lychd.compositions.reach.decision_format import (
    DecisionVariant,
    decision_phase,
    decision_schema,
)
from tests.unit.compositions.test_reach_operator_model import (
    _schema_accepts,  # pyright: ignore[reportPrivateUsage] - shared focused schema oracle
)


def requirements() -> dict[str, Any]:
    return {
        "version": 1,
        "goals": ["Provide the full, untrimmed biblical quote."],
        "constraints": [],
        "quotation_presentation": "full",
        "required_context": [],
    }


@pytest.mark.parametrize(
    ("patch", "expected"),
    [
        ({}, True),
        ({"version": 2}, False),
        ({"version": True}, False),
        ({"version": "1"}, False),
        ({"goals": []}, False),
        ({"goals": ["Goal"] * 8}, True),
        ({"goals": ["Goal"] * 9}, False),
        ({"goals": [""]}, False),
        ({"goals": ["A" * 200]}, True),
        ({"goals": ["A" * 201]}, False),
        ({"constraints": ["Constraint"] * 4}, True),
        ({"constraints": ["Constraint"] * 5}, False),
        ({"constraints": [""]}, False),
        ({"constraints": ["A" * 200]}, True),
        ({"constraints": ["A" * 201]}, False),
        ({"quotation_presentation": "none"}, True),
        ({"quotation_presentation": "abbreviated"}, True),
        ({"quotation_presentation": "complete_quotes"}, False),
        ({"required_context": ["context:1", "context:2"]}, True),
        ({"required_context": ["context:1"] * 3}, False),
        ({"required_context": [""]}, False),
        ({"required_context": ["A" * 128]}, True),
        ({"required_context": ["A" * 129]}, False),
        ({"foreign": "value"}, False),
    ],
)
def test_requirements_schema_is_closed_and_bounded(patch: dict[str, Any], *, expected: bool) -> None:
    assert _schema_accepts(requirements() | patch, decision_schema("goals")) is expected


@pytest.mark.parametrize("omitted", list(requirements()))
def test_requirements_schema_requires_every_field(omitted: str) -> None:
    raw = requirements()
    del raw[omitted]
    assert not _schema_accepts(raw, decision_schema("goals"))


@pytest.mark.parametrize("variant", ["checkback_public", "checkback_public_goals"])
@pytest.mark.parametrize("verdict", ["accept", "revise", "needs_evidence"])
@pytest.mark.parametrize(
    ("claims", "expected"),
    [
        ({}, False),
        ({"current_runtime_claims": None}, False),
        ({"current_runtime_claims": []}, True),
    ],
)
def test_public_reviews_require_nonnull_claim_arrays_for_every_verdict(
    variant: DecisionVariant, verdict: str, claims: dict[str, Any], *, expected: bool
) -> None:
    raw: dict[str, Any] = {
        "verdict": verdict,
        "issues": [] if verdict == "accept" else ["missing_evidence"],
    }
    if variant == "checkback_public_goals":
        raw["coverage"] = [{"goal": 0, "status": "complete", "answer_quote": "Visible answer."}]
    if verdict == "needs_evidence":
        raw["clarification"] = "Which source?"
    assert decision_phase(variant) == "checkback"
    assert _schema_accepts(raw | claims, decision_schema(variant)) is expected


@pytest.mark.parametrize("variant", ["checkback", "checkback_goals"])
@pytest.mark.parametrize("claims", [{}, {"current_runtime_claims": None}, {"current_runtime_claims": []}])
def test_ordinary_reviews_preserve_optional_nullable_claims(variant: DecisionVariant, claims: dict[str, Any]) -> None:
    raw: dict[str, Any] = {"verdict": "accept", "issues": []}
    if variant == "checkback_goals":
        raw["coverage"] = [{"goal": 0, "status": "complete", "answer_quote": "Visible answer."}]
    assert _schema_accepts(raw | claims, decision_schema(variant))
