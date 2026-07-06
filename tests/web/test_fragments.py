"""Projector projection per event kind + FragmentRegistry validation (no HTTP)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING

from lychd.domain.cortex.stasis import RunEvent
from lychd.domain.web.fragments import build_fragment_registry

if TYPE_CHECKING:
    from lychd.domain.web.projection import Projector


def _event(kind: str, payload: str, seq: int = 0) -> RunEvent:
    return RunEvent(run_id="run_f", seq=seq, kind=kind, payload=payload)  # type: ignore[arg-type]


def test_project_token_escapes(projector: Projector) -> None:
    """Token deltas are HTML-escaped by the Projector (emitter emits raw)."""
    assert projector.project(_event("token", "<i>x</i>")) == "&lt;i&gt;x&lt;/i&gt;"


def test_project_status_passthrough(projector: Projector) -> None:
    """Status is a controlled keyword, passed through verbatim."""
    assert projector.project(_event("status", "weaving")) == "weaving"


def test_project_fragment_renders_genui(projector: Projector) -> None:
    """A fragment event renders the validated genUI server-side (not JSON)."""
    payload = json.dumps({"key": "genui.vision_summary", "params": {"title": "T", "body": "hello", "severity": "info"}})
    out = projector.project(_event("fragment", payload))
    assert 'data-fragment="genui.vision_summary"' in out
    assert "hello" in out
    assert '"key"' not in out


def test_project_fragment_unknown_key_empty(projector: Projector) -> None:
    """An unknown fragment key projects to the empty string (dropped)."""
    assert projector.project(_event("fragment", json.dumps({"key": "nope", "params": {}}))) == ""


def test_project_fragment_autoescapes_params(projector: Projector) -> None:
    """Fragment params are autoescaped — injected markup never renders as HTML."""
    payload = json.dumps(
        {"key": "genui.vision_summary", "params": {"title": "T", "body": "<script>evil</script>", "severity": "info"}}
    )
    out = projector.project(_event("fragment", payload))
    assert "<script>evil</script>" not in out
    assert "&lt;script&gt;" in out


def test_project_done_settles_turn_oob(projector: Projector) -> None:
    """A done event renders the settled agent turn as an OOB replacement."""
    out = projector.project(_event("done", "run_missing"))
    assert 'data-state="done"' in out
    assert "hx-swap-oob" in out


def test_registry_drops_unknown_and_invalid() -> None:
    """FragmentRegistry drops unknown keys and params that fail validation."""
    registry = build_fragment_registry()
    calls = [
        SimpleNamespace(fragment="nope", params={}),
        SimpleNamespace(fragment="genui.plan_checklist", params={"steps": ["a"]}),  # missing required title
    ]
    assert registry.validate_calls(calls) == []  # type: ignore[arg-type]

    good = [SimpleNamespace(fragment="genui.plan_checklist", params={"title": "Rite", "steps": ["a"]})]
    validated = registry.validate_calls(good)  # type: ignore[arg-type]
    assert len(validated) == 1
    assert validated[0].key == "genui.plan_checklist"
