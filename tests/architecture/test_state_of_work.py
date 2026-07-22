"""Public delivery truth remains explicit, linked, and mechanically bounded."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

_ROOT = Path(__file__).resolve().parents[2]
_STATE = _ROOT / "docs" / "state-of-the-work.md"

_ALLOWED_STATES = frozenset(
    {
        "Available",
        "Operator validation",
        "Partial",
        "Designed",
        "Experimental",
        "External",
    }
)
_BOUNDARY_BY_STATE = {
    "Available": "**Boundary:**",
    "Operator validation": "**Receipt needed:**",
    "Partial": "**Boundary — Not yet:**",
    "Designed": "**Do not expect yet:**",
    "Experimental": "**Instability boundary:**",
    "External": "**External owner and boundary:**",
}
_BOUNDARY_MARKERS = tuple(_BOUNDARY_BY_STATE.values())

_FAMILY_ANCHORS = {
    "altar-and-observability",
    "animation-and-orchestration",
    "authority-and-artifacts",
    "evolution-and-federation",
    "inscription-and-embodiment",
    "persistence-execution-and-consent",
}
_RECORD_ANCHORS = {
    "a2a-intercom",
    "animator-dispatch-spine",
    "artifact-reference-contract",
    "audio-admission",
    "bindings-instrument",
    "bridge-surface",
    "core-cli-rites",
    "deployment-plan-materialization",
    "durable-attention",
    "exllamav3-tabbyapi",
    "extension-activation-contributions",
    "graph-stasis-consent",
    "host-reactor-protocol",
    "karma-semantic-memory",
    "legion-federation",
    "llamacpp-integration",
    "local-browser-bind-boundary",
    "local-sigil-authority",
    "loom-workflow-views",
    "mirror-identity",
    "native-oculus",
    "nexus-transition-board",
    "phylactery-first-light",
    "phoenix-eye",
    "proxy-veil",
    "public-release-artifact-chain",
    "pydantic-ai-v1-adapter",
    "pydantic-ai-v2-migration",
    "reliquary-instrument",
    "remote-iam",
    "resource-aware-scheduling",
    "riddle-evaluation",
    "rune-configuration-loading",
    "safe-runtime-transitions",
    "scrying-instrument",
    "sglang-integration",
    "shadow-simulation",
    "smith-forge-promotion",
    "soulforge-training",
    "structured-logging",
    "systemd-podman-embodiment",
    "tomb-untrusted-execution",
    "topology-a-local-runs",
    "vllm-integration",
    "vision-admission",
    "vpn-tether",
    "whole-body-snapshot-restore",
    "x402-payments",
}

_RECORD_RE = re.compile(
    r"^### (?P<title>.+?) \{#(?P<anchor>[a-z0-9-]+)\}\n"
    r"(?P<body>.*?)(?=^### |^## |\Z)",
    re.MULTILINE | re.DOTALL,
)
_FAMILY_RE = re.compile(r"^## .+ \{#(?P<anchor>[a-z0-9-]+)\}$", re.MULTILINE)
_LINK_RE = re.compile(r"\[[^\]]+\]\((?P<target>[^)]+)\)")
_EVIDENCE_LABEL_RE = re.compile(r"^- \*\*(?P<label>[^*]+):\*\*", re.MULTILINE)
_BARE_REPOSITORY_PATH_RE = re.compile(r"(?<![/.(])(?:\.agents|docs|src|tests)/[A-Za-z0-9_./*{}-]+")
_REPO_URL = "https://github.com/hexanomicon/lychd/"
_ALLOWED_EVIDENCE_LABELS = {
    "Current baseline",
    "Journey",
    "Law",
    "Rite",
    "Source",
    "Topic",
    "Verification",
    "Version",
}
_RUNNABLE_STATES = {"Available", "Experimental", "Operator validation", "Partial"}


def _text() -> str:
    return _STATE.read_text(encoding="utf-8")


def _records(text: str) -> list[re.Match[str]]:
    return list(_RECORD_RE.finditer(text))


def test_state_has_the_exact_public_jurisdictions_and_subjects() -> None:
    text = _text()
    family_anchors = {match.group("anchor") for match in _FAMILY_RE.finditer(text)}
    records = _records(text)
    record_anchors = {match.group("anchor") for match in records}

    assert family_anchors == _FAMILY_ANCHORS
    assert record_anchors == _RECORD_ANCHORS
    assert len(records) == len(_RECORD_ANCHORS) == 48
    assert len(record_anchors) == len(records), "State record anchors must be unique"


def test_each_subject_is_one_complete_vertical_record() -> None:
    text = _text()
    records = _records(text)
    seen_states: list[str] = []

    for record in records:
        title = record.group("title")
        anchor = record.group("anchor")
        body = record.group("body")
        states = re.findall(r"^\*\*State:\*\* (.+)$", body, re.MULTILINE)

        assert len(states) == 1, f"{title!r} must contain exactly one State field"
        state = states[0]
        seen_states.append(state)
        assert state in _ALLOWED_STATES, f"{title!r} uses unknown state {state!r}"
        assert body.count("**Proved now:**") == 1
        assert body.count("**Evidence**") == 1

        present_markers = [marker for marker in _BOUNDARY_MARKERS if marker in body]
        assert present_markers == [_BOUNDARY_BY_STATE[state]], f"{title!r} must use only the {state!r} boundary marker"
        assert not any(value.lower().replace(" ", "-") in anchor for value in _ALLOWED_STATES)

        evidence = body.split("**Evidence**", maxsplit=1)[1]
        assert _LINK_RE.search(evidence), f"{title!r} needs concrete linked evidence"

    assert set(seen_states) <= _ALLOWED_STATES
    assert "Experimental" not in seen_states, "No current subject has an experimental contract"
    assert text.count("**State:**") == len(records)


def test_delivery_page_is_not_a_wide_or_duplicate_ledger() -> None:
    text = _text()

    assert re.search(r"^\|", text, re.MULTILINE) is None
    assert ".agents/work" not in text
    assert "State of the Circle" not in text
    assert "**Pre-alpha**" in text
    assert "not a seventh delivery state" in text
    assert _BARE_REPOSITORY_PATH_RE.findall(text) == []


def test_state_links_resolve_to_the_claimed_repository_object_type() -> None:
    text = _text()
    anchors = _FAMILY_ANCHORS | _RECORD_ANCHORS

    for match in _LINK_RE.finditer(text):
        target = match.group("target").strip().strip("<>")
        assert not any(token in target for token in ("*", "{", "}")), target

        if target.startswith("#"):
            assert unquote(target[1:]) in anchors, target
            continue

        if target.startswith(_REPO_URL):
            relative = target.removeprefix(_REPO_URL)
            kind, separator, repository_path = relative.partition("/main/")
            assert separator, target
            assert kind in {"blob", "tree"}, target
            resolved = _ROOT / unquote(repository_path)
            if kind == "blob":
                assert resolved.is_file(), target
            else:
                assert resolved.is_dir(), target
            continue

        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            continue

        resolved = (_STATE.parent / unquote(parsed.path)).resolve()
        assert resolved.is_relative_to(_ROOT), target
        assert resolved.is_file(), target


def test_evidence_labels_and_minimum_contract_match_each_state() -> None:
    for record in _records(_text()):
        body = record.group("body")
        title = record.group("title")
        state = re.search(r"^\*\*State:\*\* (.+)$", body, re.MULTILINE)
        assert state is not None
        state_value = state.group(1)
        evidence = body.split("**Evidence**", maxsplit=1)[1]
        labels = set(_EVIDENCE_LABEL_RE.findall(evidence))

        assert labels, f"{title!r} has no recognized Evidence bullets"
        assert labels <= _ALLOWED_EVIDENCE_LABELS, (
            f"{title!r} uses unknown Evidence labels: {labels - _ALLOWED_EVIDENCE_LABELS}"
        )

        if state_value in _RUNNABLE_STATES:
            assert {"Source", "Verification"} <= labels, title
            assert "/blob/main/src/" in evidence, title
            assert "/blob/main/tests/" in evidence, title
        elif state_value == "Designed":
            assert labels & {"Law", "Topic"}, title
        elif state_value == "External":
            upstream_links = [
                match.group("target")
                for match in _LINK_RE.finditer(body)
                if urlsplit(match.group("target")).scheme and not match.group("target").startswith(_REPO_URL)
            ]
            assert upstream_links, f"{title!r} must link its non-LychD upstream owner"


def test_opening_earns_vocabulary_and_closes_with_one_next_act() -> None:
    text = _text()
    opening = text.split("## How to read this page", maxsplit=1)[0]

    assert "LychD names the software body" in opening
    assert "The Lich names the recurrent whole" in opening
    assert "not any one model" in opening
    assert "one LychD control process" in opening
    for unearned_name in ("Oculus", "Phoenix", "Magus", "Karma", "Sigil"):
        assert unearned_name not in opening

    assert text.rstrip().endswith(
        "observations are a bounded first-life result, not a maintained operator receipt; preserve them\n"
        "with all metadata above, and let the observed result—not hope—decide what this page may claim next."
    )
