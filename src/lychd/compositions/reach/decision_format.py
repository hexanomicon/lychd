"""Fixed provider grammar for raw controller outputs; native parsers own validity."""

from __future__ import annotations

import json
from hashlib import sha256
from itertools import product
from typing import TYPE_CHECKING, Any, Literal, cast

type DecisionPhase = Literal[
    "planning", "conversation", "terminal_correction", "synthesis", "addressing", "checkback", "goals"
]

DECISION_PHASES: tuple[DecisionPhase, ...] = (
    "planning",
    "conversation",
    "terminal_correction",
    "synthesis",
    "addressing",
    "checkback",
    "goals",
)

type DecisionVariant = (
    DecisionPhase
    | Literal[
        "planning_documents",
        "planning_web",
        "checkback_goals",
        "checkback_public",
        "checkback_public_goals",
    ]
)

DECISION_VARIANTS: tuple[DecisionVariant, ...] = (
    *DECISION_PHASES,
    "planning_documents",
    "planning_web",
    "checkback_goals",
    "checkback_public",
    "checkback_public_goals",
)

if TYPE_CHECKING:
    # Resolved lazily by __getattr__: schema regeneration must not need its old artifact.
    DECISION_SCHEMA_BUNDLE_SHA256: str

_MAX_RESEARCH_SOURCES = 4


def _text(limit: int, *, nullable: bool = False) -> dict[str, Any]:
    value: dict[str, Any] = {"type": "string", "minLength": 1, "maxLength": limit}
    return {"anyOf": [value, {"type": "null"}]} if nullable else value


def _array(items: dict[str, Any], limit: int, *, minimum: int = 0) -> dict[str, Any]:
    return {"type": "array", "items": items, "minItems": minimum, "maxItems": limit}


def _object(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


def _research_sources() -> dict[str, Any]:
    """Project native source-kind counts without selecting or admitting source IDs."""
    patterns = {"doc": r"^doc:[A-Za-z0-9_./-]{1,200}$", "web": r"^web:[a-z][a-z0-9_]{0,31}$"}
    limits = {"doc": 3, "web": 2}
    return {
        "anyOf": [
            {
                "type": "array",
                "prefixItems": [{"type": "string", "pattern": patterns[kind]} for kind in kinds],
                "items": False,
                "minItems": size,
                "maxItems": size,
            }
            for size in range(1, _MAX_RESEARCH_SOURCES + 1)
            for kinds in product(patterns, repeat=size)
            if all(kinds.count(kind) <= limit for kind, limit in limits.items())
        ]
    }


def _schema() -> dict[str, Any]:
    expressions = {
        "reaction": {
            "anyOf": [
                {"type": "string", "enum": ["👀", "👍", "❤️", "😂", "✨", "🤔"]},
                {"type": "null"},
            ]
        },
        "gif_id": _text(32, nullable=True),
    }
    source = _text(204)
    coverage = _object(
        {
            "goal": {"anyOf": [{"type": "integer", "minimum": 0, "maximum": 7}, _text(200)]},
            "status": {
                "type": "string",
                "enum": ["complete", "missing", "unsupported"],
            },
            "answer_quote": _text(240, nullable=True),
        },
        ["goal", "status"],
    )
    branches = [
        _object(
            {
                "kind": {"enum": ["answer", "read_more", "clarify"]},
                "text": _text(8000),
                **expressions,
            },
            ["kind", "text"],
        ),
        _object(
            {
                "kind": {"const": "research"},
                "text": _text(500),
                "focus": _text(500),
                "source_ids": _research_sources(),
            },
            ["kind", "text", "focus", "source_ids"],
        ),
        _object(
            {
                "kind": {"enum": ["answer", "clarify"]},
                "text": _text(8000),
                "citations": _array(source, 4),
                **expressions,
            },
            ["kind", "text"],
        ),
        _object(
            {
                "kind": {"enum": ["addressed", "ignore"]},
                "request_id": _text(128),
                "anchor_event_id": _text(128),
            },
            ["kind", "request_id", "anchor_event_id"],
        ),
        _object(
            {
                "verdict": {"enum": ["accept", "revise", "needs_evidence"]},
                "issues": _array(
                    {
                        "enum": [
                            "missing_component",
                            "unsupported_claim",
                            "quotation_mismatch",
                            "wrong_language",
                            "wrong_target",
                            "future_promise",
                            "unnecessary_clarification",
                            "contradiction",
                            "missing_evidence",
                        ]
                    },
                    4,
                ),
                "coverage": _array(coverage, 8),
                "clarification": _text(500, nullable=True),
                "current_runtime_claims": {"anyOf": [_array(_text(240), 4), {"type": "null"}]},
            },
            ["verdict", "issues"],
        ),
        _object(
            {
                "version": {"type": "integer", "const": 1},
                "goals": _array(_text(200), 8, minimum=1),
                "constraints": _array(_text(200), 4),
                "quotation_presentation": {
                    "type": "string",
                    "enum": ["none", "abbreviated", "full"],
                },
                "required_context": _array(_text(128), 2),
            },
            [
                "version",
                "goals",
                "constraints",
                "quotation_presentation",
                "required_context",
            ],
        ),
    ]
    return {"type": "object", "anyOf": branches}


def decision_phase(variant: DecisionVariant) -> DecisionPhase:
    """Keep resource-specific grammar selection separate from reasoning policy."""
    if type(variant) is not str or variant not in DECISION_VARIANTS:
        msg = "decision_schema_phase"
        raise ValueError(msg)
    if variant in {"planning_documents", "planning_web"}:
        return "planning"
    return (
        "checkback"
        if variant in {"checkback_goals", "checkback_public", "checkback_public_goals"}
        else cast("DecisionPhase", variant)
    )


def _goal_review_schema(branch: dict[str, Any]) -> dict[str, Any]:
    """Project native verdict coherence while leaving exact goals and evidence to admission."""
    properties = branch["properties"]
    coverage = properties["coverage"]
    item_properties = coverage["items"]["properties"]
    complete = _object(
        {
            **item_properties,
            "status": {"const": "complete"},
            "answer_quote": _text(240),
        },
        ["goal", "status", "answer_quote"],
    )
    incomplete = _object(
        {**item_properties, "status": {"enum": ["missing", "unsupported"]}},
        ["goal", "status"],
    )
    return {
        "type": "object",
        "anyOf": [
            _object(
                {
                    **properties,
                    "verdict": {"const": verdict},
                    "issues": {
                        **properties["issues"],
                        "minItems": 0 if verdict == "accept" else 1,
                        "maxItems": 0 if verdict == "accept" else properties["issues"]["maxItems"],
                    },
                    "coverage": {
                        **coverage,
                        "minItems": 1,
                        "items": complete if verdict == "accept" else {"anyOf": [complete, incomplete]},
                    },
                    "clarification": _text(500) if verdict == "needs_evidence" else {"type": "null"},
                },
                ["verdict", "issues", "coverage"]
                + (["clarification"] if verdict == "needs_evidence" else [])
                + (["current_runtime_claims"] if "current_runtime_claims" in branch["required"] else []),
            )
            for verdict in ("accept", "revise", "needs_evidence")
        ],
    }


def _phase_schema(variant: DecisionVariant) -> dict[str, Any]:
    phase = decision_phase(variant)
    branches = _schema()["anyOf"]
    if phase == "planning":
        if variant in {"planning_documents", "planning_web"}:
            pattern, limit = (
                (r"^doc:[A-Za-z0-9_./-]{1,200}$", 3)
                if variant == "planning_documents"
                else (r"^web:[a-z][a-z0-9_]{0,31}$", 2)
            )
            branches[1]["properties"]["source_ids"] = _array({"type": "string", "pattern": pattern}, limit, minimum=1)
        return {"type": "object", "anyOf": branches[:2]}
    if phase == "terminal_correction":
        branches[0]["properties"]["kind"]["enum"] = ["answer", "clarify"]
    if variant in {"checkback_public", "checkback_public_goals"}:
        branches[4]["properties"]["current_runtime_claims"] = _array(_text(240), 4)
        branches[4]["required"].append("current_runtime_claims")
    if variant in {"checkback_goals", "checkback_public_goals"}:
        return _goal_review_schema(branches[4])
    index = {
        "conversation": 0,
        "terminal_correction": 0,
        "synthesis": 2,
        "addressing": 3,
        "checkback": 4,
        "goals": 5,
    }
    return cast("dict[str, Any]", branches[index[phase]])


def decision_schema(phase: DecisionVariant) -> dict[str, Any]:
    """Return a fresh source schema without importing the generated grammar artifact."""
    return _phase_schema(phase)


def decision_schema_inputs() -> tuple[tuple[DecisionVariant, str], ...]:
    """Preserve both variant order and declared property order for offline conversion."""
    return tuple(
        (phase, json.dumps(decision_schema(phase), separators=(",", ":"), ensure_ascii=False, allow_nan=False))
        for phase in DECISION_VARIANTS
    )


def _fingerprint(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


DECISION_SCHEMA_INPUT_SHA256 = _fingerprint(decision_schema_inputs())


def decision_converter_metadata() -> dict[str, Any]:
    """Pin the offline converter and exact compact JSON spelling it emits."""
    return {
        "package": "xgrammar",
        "version": "0.2.3",
        "api": "Grammar.from_json_schema",
        "serialization": "str(Grammar)",
        "options": {"any_whitespace": False, "indent": None, "separators": [",", ":"]},
        "normalization": "nonempty-json-scalar-native-max-v2",
    }


def decision_bundle_sha256(grammars: tuple[tuple[str, str], ...], generator_sha256: str) -> str:
    """Bind source order, converter, generator and the exact effective provider carriers."""
    return _fingerprint(
        {
            "converter": decision_converter_metadata(),
            "generator_sha256": generator_sha256,
            "schema_inputs": decision_schema_inputs(),
            "carriers": [(variant, {"grammar": grammar}) for variant, grammar in grammars],
        }
    )


def _grammar_bundle() -> tuple[tuple[tuple[str, str], ...], str]:
    # This import is deliberately lazy: missing or stale artifacts must be regenerable.
    from lychd.compositions.reach import decision_grammar_generated as generated

    grammars = generated.GRAMMARS
    if (
        generated.SCHEMA_INPUT_SHA256 != DECISION_SCHEMA_INPUT_SHA256
        or json.loads(generated.CONVERTER_METADATA_JSON) != decision_converter_metadata()
        or tuple(name for name, _ in grammars) != DECISION_VARIANTS
        or len({grammar for _, grammar in grammars}) != len(DECISION_VARIANTS)
        or decision_bundle_sha256(grammars, generated.GENERATOR_SHA256) != generated.BUNDLE_SHA256
    ):
        msg = "decision_grammar_artifact"
        raise ValueError(msg)
    return grammars, generated.BUNDLE_SHA256


def __getattr__(name: str) -> str:
    """Resolve the effective binding only for runtime consumers, never schema generation."""
    if name == "DECISION_SCHEMA_BUNDLE_SHA256":
        return _grammar_bundle()[1]
    raise AttributeError(name)


def decision_response_format(phase: DecisionVariant) -> dict[str, Any]:
    """Return only the verified, fixed compact EBNF carrier for this variant."""
    decision_phase(phase)
    for variant, grammar in _grammar_bundle()[0]:
        if phase == variant:
            return {"grammar": grammar}
    msg = "decision_schema_phase"
    raise ValueError(msg)


def decision_format_phase(value: object) -> DecisionVariant | None:
    """Recognize exact generated carriers; native parsers still own output validity."""
    if type(value) is not dict:
        return None
    supplied = cast("dict[str, Any]", value)
    if set(supplied) != {"grammar"} or type(supplied["grammar"]) is not str:
        return None
    for variant, grammar in _grammar_bundle()[0]:
        if supplied["grammar"] == grammar:
            return cast("DecisionVariant", variant)
    return None
