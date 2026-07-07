"""Projector projection per event kind + FragmentRegistry validation (no HTTP)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from lychd.domain.cortex.events import RunEvent
from lychd.domain.web.fragments import build_fragment_registry

if TYPE_CHECKING:
    from lychd.domain.web.projection import Projector


def _event(kind: str, payload: str, seq: int = 0) -> RunEvent:
    return RunEvent(run_id="run_f", seq=seq, kind=kind, data=payload)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_project_token_escapes(projector: Projector) -> None:
    """Token deltas are HTML-escaped by the Projector (emitter emits raw)."""
    assert await projector.project(_event("token", "<i>x</i>")) == "&lt;i&gt;x&lt;/i&gt;"


@pytest.mark.asyncio
async def test_project_status_passthrough(projector: Projector) -> None:
    """Status is a controlled keyword, passed through verbatim."""
    assert await projector.project(_event("status", "weaving")) == "weaving"


@pytest.mark.asyncio
async def test_project_fragment_renders_genui(projector: Projector) -> None:
    """A fragment event renders the validated genUI server-side (not JSON)."""
    payload = json.dumps(
        {"fragment": "genui.vision_summary", "params": {"title": "T", "body": "hello", "severity": "info"}}
    )
    out = await projector.project(_event("fragment", payload))
    assert 'data-fragment="genui.vision_summary"' in out
    assert "hello" in out
    assert '"key"' not in out


@pytest.mark.asyncio
async def test_project_fragment_unknown_key_empty(projector: Projector) -> None:
    """An unknown fragment key projects to the empty string (dropped)."""
    assert await projector.project(_event("fragment", json.dumps({"fragment": "nope", "params": {}}))) == ""


@pytest.mark.asyncio
async def test_project_fragment_autoescapes_params(projector: Projector) -> None:
    """Fragment params are autoescaped — injected markup never renders as HTML."""
    payload = json.dumps(
        {
            "fragment": "genui.vision_summary",
            "params": {"title": "T", "body": "<script>evil</script>", "severity": "info"},
        }
    )
    out = await projector.project(_event("fragment", payload))
    assert "<script>evil</script>" not in out
    assert "&lt;script&gt;" in out


@pytest.mark.asyncio
async def test_project_done_settles_turn_oob(projector: Projector) -> None:
    """A done event renders the settled agent turn as an OOB replacement."""
    out = await projector.project(_event("done", "run_missing"))
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
