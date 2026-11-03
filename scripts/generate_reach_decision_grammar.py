"""Regenerate fixed Reach grammars offline with XGrammar==0.2.3.

Run in an explicitly provisioned offline converter environment with the source package
on PYTHONPATH: python -m scripts.generate_reach_decision_grammar [--check].
This script never installs dependencies or controls a model, process or service.
"""

from __future__ import annotations

import argparse
import json
import re
from hashlib import sha256
from importlib import import_module
from importlib.metadata import version
from pathlib import Path
from typing import Any

from lychd.compositions.reach.decision_format import (
    DECISION_SCHEMA_INPUT_SHA256,
    DecisionVariant,
    decision_bundle_sha256,
    decision_converter_metadata,
    decision_schema_inputs,
)

ARTIFACT = Path(__file__).resolve().parents[1] / "src/lychd/compositions/reach/decision_grammar_generated.py"

_MAX_BOUNDED_STRING_CHARS = 8000
_SURROGATE_START = 0xD800
_SURROGATE_END = 0xDFFF
_BOUNDED_LEAF = r"(([^\"\\\r\n]))"
_BOUNDED_LEAF_COUNTS: dict[DecisionVariant, int] = {
    "planning": 4,
    "conversation": 2,
    "terminal_correction": 2,
    "synthesis": 3,
    "addressing": 2,
    "checkback": 4,
    "goals": 1,
    "planning_documents": 4,
    "planning_web": 4,
    "checkback_goals": 14,
}
_JSON_SCALAR_RULES = (
    "reach_json_hex_v1 ::= [0-9a-fA-F]\n"
    r'reach_json_scalar_v1 ::= ([^\0-\x1f\"\\] | "\\" [\"\\/bfnrt] | "\\u" '
    r"([0-9a-cA-Ce-fE-F] reach_json_hex_v1 reach_json_hex_v1 reach_json_hex_v1 | "
    r"[dD] [0-7] reach_json_hex_v1 reach_json_hex_v1) | "
    r'"\\u" [dD] [89aAbB] reach_json_hex_v1 reach_json_hex_v1 '
    r'"\\u" [dD] [c-fC-F] reach_json_hex_v1 reach_json_hex_v1)'
    "\n"
)
_NONEMPTY_JSON_STRING = r'(("\"" reach_json_scalar_v1 reach_json_string_tail_v2))'
_JSON_STRING_RULES = (
    r'reach_json_escape_v2 ::= (([\"\\/bfnrt]) | ("u" '
    r"([0-9a-cA-Ce-fE-F] reach_json_hex_v1 reach_json_hex_v1 reach_json_hex_v1 | "
    r"[dD] [0-7] reach_json_hex_v1 reach_json_hex_v1)) | "
    r'("u" [dD] [89aAbB] reach_json_hex_v1 reach_json_hex_v1 "\\u" '
    r"[dD] [c-fC-F] reach_json_hex_v1 reach_json_hex_v1))"
    "\n"
    r'reach_json_string_tail_v2 ::= (("\"") | ([^\0-\x1f\"\\] reach_json_string_tail_v2) | '
    r'("\\" reach_json_escape_v2 reach_json_string_tail_v2)) (=([ \n\t]* [,}\]:]))'
    "\n"
)


def normalize_bounded_json_strings(variant: DecisionVariant, grammar: str) -> str:
    """Project pinned string leaves to nonempty JSON; native parsers retain maximum lengths."""
    expected = _BOUNDED_LEAF_COUNTS.get(variant)
    lines = grammar.splitlines()
    rules = [line.partition(" ::= ") for line in lines]
    names = [name for name, _, _ in rules]
    leaves = {name for name, _, body in rules if body == _BOUNDED_LEAF}
    if (
        expected is None
        or len(leaves) != expected
        or len(set(names)) != len(names)
        or any(not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) for name, separator, _ in rules)
        or "reach_json_" in grammar
    ):
        msg = "decision_grammar_string_normalization"
        raise ValueError(msg)
    # Every repaired unit must belong exclusively to a quoted bounded-string rule.
    prefix, suffix = r'(("\"" ', r' "\""))'
    references: dict[str, int] = dict.fromkeys(leaves, 0)
    owners: set[str] = set()
    for name, _, body in rules:
        used = leaves & set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", body))
        if not used:
            continue
        if len(used) != 1 or not body.startswith(prefix) or not body.endswith(suffix):
            msg = "decision_grammar_string_normalization"
            raise ValueError(msg)
        unit = next(iter(used))
        repeated = body[len(prefix) : -len(suffix)]
        bounds = re.fullmatch(re.escape(unit) + r"\{([0-9]+), ([0-9]+)\}", repeated)
        if (
            bounds is None
            or int(bounds[1]) != 1
            or not 1 <= int(bounds[2]) <= _MAX_BOUNDED_STRING_CHARS
            or name in leaves
        ):
            msg = "decision_grammar_string_normalization"
            raise ValueError(msg)
        references[unit] += 1
        owners.add(name)
    if any(count != 1 for count in references.values()):
        msg = "decision_grammar_string_normalization"
        raise ValueError(msg)
    return (
        "\n".join(
            f"{name} ::= {_NONEMPTY_JSON_STRING}"
            if name in owners
            else f"{name} ::= ((reach_json_scalar_v1))"
            if name in leaves
            else line
            for line, (name, _, _) in zip(lines, rules, strict=True)
        )
        + "\n"
        + _JSON_SCALAR_RULES
        + _JSON_STRING_RULES
    )


def validate_string_encoding(converter: Any, variant: DecisionVariant, grammar: str) -> None:
    """Prove JSON syntax and the explicit provider/native length handoff before publication."""
    compiler = converter.GrammarCompiler(converter.TokenizerInfo([]), max_threads=1, cache_enabled=False)
    compiled = compiler.compile_grammar(converter.Grammar.from_ebnf(grammar))
    limit = {"addressing": 128, "checkback": 500, "checkback_goals": 500, "goals": 200}.get(variant, 8000)

    def document(text: str) -> dict[str, object]:
        if variant == "addressing":
            return {"kind": "addressed", "request_id": text, "anchor_event_id": "anchor"}
        if variant == "checkback":
            return {"verdict": "revise", "issues": ["missing_component"], "clarification": text}
        if variant == "checkback_goals":
            return {
                "verdict": "needs_evidence",
                "issues": ["missing_evidence"],
                "coverage": [{"goal": 0, "status": "missing"}],
                "clarification": text,
            }
        if variant == "goals":
            return {"goals": [text]}
        return {"kind": "answer", "text": text}

    fixtures = [
        ("Plain text.", True),
        ('Intro:\n- "Quoted" text\n- Path a\\b\t漢字 👀', True),
        ("A\b\f\rB", True),
        ("", False),
        ("A" * limit, True),
        # Provider strings intentionally admit max+1; actual native parsers must refuse it.
        ("A" * (limit + 1), True),
        ("A" * (limit - 1) + "\n", True),
        ("A" * limit + "\n", True),
        ("A" * (limit - 1) + "😀", True),
        ("A" * limit + "😀", True),
        ("\ud83d", False),
        ("\ude00", False),
        ("\ude00\ud83d", False),
    ]
    encoded = [
        (json.dumps(document(text), ensure_ascii=ascii_only, separators=(",", ":")), expected)
        for text, expected in fixtures
        for ascii_only in (True, False)
        if ascii_only or not any(_SURROGATE_START <= ord(char) <= _SURROGATE_END for char in text)
    ]
    newline = json.dumps(document("A\nB"), separators=(",", ":"))
    encoded.extend((newline.replace(r"\n", invalid), False) for invalid in ("\n", "\t", "\x01", r"\x41", r"\u12"))
    encoded.extend(
        [
            (json.dumps(document("A"), separators=(",", ":")) + "\n", False),
            (json.dumps(document("A"), separators=(",", ": ")), False),
        ]
    )
    for text, expected in encoded:
        matcher = converter.GrammarMatcher(compiled, terminate_without_stop_token=True)
        accepted = matcher.accept_string(text)
        if bool(accepted and matcher.is_completed()) != expected:
            msg = f"decision_grammar_string_encoding:{variant}"
            raise ValueError(msg)


def validate_goal_review_shape(converter: Any, grammar: str) -> None:
    """Prove verdict coherence and required coverage; native checks retain exact goals and evidence."""
    compiler = converter.GrammarCompiler(converter.TokenizerInfo([]), max_threads=1, cache_enabled=False)
    compiled = compiler.compile_grammar(converter.Grammar.from_ebnf(grammar))
    base: dict[str, Any] = {"verdict": "accept", "issues": []}
    complete = {"goal": 0, "status": "complete", "answer_quote": "Visible answer."}
    cases: list[tuple[dict[str, Any], bool]] = [
        (base | {"current_runtime_claims": [","]}, False),
        (base | {"coverage": []}, False),
        (base | {"coverage": [{"goal": 0, "status": "complete"}]}, False),
        (base | {"coverage": [complete | {"answer_quote": None}]}, False),
        (base | {"coverage": [complete]}, True),
        (base | {"coverage": [complete] * 9}, False),
        (base | {"coverage": [complete], "candidate": {}}, False),
        (base | {"coverage": [complete], "issues": ["missing_component"]}, False),
        (base | {"coverage": [complete], "clarification": None}, True),
        (base | {"coverage": [complete], "clarification": "Which source?"}, False),
    ]
    for status in ("missing", "unsupported"):
        cases.append((base | {"coverage": [complete | {"status": status}]}, False))
        cases.extend(
            (
                {
                    "verdict": "revise",
                    "issues": ["missing_component"],
                    "coverage": [{"goal": 0, "status": status, **quote}],
                },
                True,
            )
            for quote in ({}, {"answer_quote": None}, {"answer_quote": "Visible answer."})
        )
    for verdict in ("revise", "needs_evidence"):
        review = {"verdict": verdict, "issues": ["missing_component"], "coverage": [complete]}
        cases.extend(
            (review | clarification, accepted)
            for clarification, accepted in (
                ({}, verdict == "revise"),
                ({"clarification": None}, verdict == "revise"),
                ({"clarification": "Which source?"}, verdict == "needs_evidence"),
            )
        )
        valid = review | ({"clarification": "Which source?"} if verdict == "needs_evidence" else {})
        cases.append((valid | {"issues": []}, False))
    for value, expected in cases:
        matcher = converter.GrammarMatcher(compiled, terminate_without_stop_token=True)
        accepted = matcher.accept_string(json.dumps(value, separators=(",", ":"), ensure_ascii=False))
        if bool(accepted and matcher.is_completed()) != expected:
            msg = "decision_grammar_goal_review_shape"
            raise ValueError(msg)


def _python_literal(value: str) -> str:
    """Avoid unnecessary quote escapes while retaining the repository's double-quote default."""
    return repr(value) if '"' in value and "'" not in value else json.dumps(value)


def render_artifact(grammars: tuple[tuple[str, str], ...]) -> str:
    """Render deterministic Python literals, including independent input/output fingerprints."""
    generator_sha256 = sha256(Path(__file__).read_bytes()).hexdigest()
    metadata = json.dumps(decision_converter_metadata(), sort_keys=True, separators=(",", ":"))
    lines = [
        '"""Generated by scripts/generate_reach_decision_grammar.py; do not edit."""',
        "",
        "# fmt: off",
        f"GENERATOR_SHA256 = {_python_literal(generator_sha256)}",
        f"CONVERTER_METADATA_JSON = {_python_literal(metadata)}",
        f"SCHEMA_INPUT_SHA256 = {_python_literal(DECISION_SCHEMA_INPUT_SHA256)}",
        f"BUNDLE_SHA256 = {_python_literal(decision_bundle_sha256(grammars, generator_sha256))}",
        "",
        "GRAMMARS: tuple[tuple[str, str], ...] = (",
    ]
    for variant, grammar in grammars:
        lines.extend(
            [
                f"    ({_python_literal(variant)}, (",
                *(f"        {_python_literal(line)}" for line in grammar.splitlines(keepends=True)),
                "    )),",
            ]
        )
    return "\n".join([*lines, ")", "# fmt: on", ""])


def main() -> int:
    """Convert source schemas and optionally refuse a nonmatching checked-in artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare generated bytes without writing.")
    args = parser.parse_args()
    if version("xgrammar") != "0.2.3":
        parser.error("requires exactly xgrammar==0.2.3")
    xgrammar = import_module("xgrammar")

    grammars: tuple[tuple[DecisionVariant, str], ...] = tuple(
        (
            variant,
            normalize_bounded_json_strings(
                variant,
                str(
                    xgrammar.Grammar.from_json_schema(schema, any_whitespace=False, indent=None, separators=(",", ":"))
                ),
            ),
        )
        for variant, schema in decision_schema_inputs()
    )
    for variant, grammar in grammars:
        validate_string_encoding(xgrammar, variant, grammar)
        if variant == "checkback_goals":
            validate_goal_review_shape(xgrammar, grammar)
    expected = render_artifact(grammars)
    if args.check:
        if not ARTIFACT.is_file() or ARTIFACT.read_bytes() != expected.encode():
            parser.exit(1, "Reach grammar artifact differs; regenerate with xgrammar==0.2.3.\n")
    else:
        ARTIFACT.write_bytes(expected.encode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
