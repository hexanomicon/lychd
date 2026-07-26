"""Semantic event projection and closed GenUI descriptor validation."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from lychd.domain.cortex.events import RunEvent
from lychd.domain.web.fragments import build_fragment_registry

if TYPE_CHECKING:
    from lychd.domain.web.projection import EventProjector


def _event(kind: str, payload: str, seq: int = 0) -> RunEvent:
    return RunEvent(run_id="run_f", seq=seq, kind=kind, data=payload)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_project_token_remains_inert_text(
    projector: EventProjector,
) -> None:
    envelope = await projector.project(_event("token", "<i>x</i>"))

    assert envelope.kind == "token"
    assert envelope.payload == {"text": "<i>x</i>"}


@pytest.mark.asyncio
async def test_project_status_is_semantic_json(
    projector: EventProjector,
) -> None:
    envelope = await projector.project(_event("status", "weaving"))
    assert envelope.payload == {"text": "weaving"}


@pytest.mark.asyncio
async def test_project_fragment_returns_closed_descriptor(
    projector: EventProjector,
) -> None:
    payload = json.dumps(
        {
            "fragment": "genui.vision_summary",
            "params": {"title": "T", "body": "hello", "severity": "info"},
        }
    )
    envelope = await projector.project(_event("fragment", payload))

    assert envelope.payload["kind"] == "genui.vision_summary"
    assert envelope.payload["schema_version"] == 1
    assert envelope.payload["props"]["body"] == "hello"
    assert envelope.payload["actions"] == []


@pytest.mark.asyncio
async def test_project_fragment_unknown_key_is_visible_descriptor(
    projector: EventProjector,
) -> None:
    envelope = await projector.project(
        _event("fragment", json.dumps({"fragment": "nope", "params": {}})),
    )
    assert envelope.payload["kind"] == "genui.unknown"


@pytest.mark.asyncio
async def test_project_fragment_never_interprets_markup(
    projector: EventProjector,
) -> None:
    script = "<script>evil</script>"
    payload = json.dumps(
        {
            "fragment": "genui.vision_summary",
            "params": {"title": "T", "body": script, "severity": "info"},
        }
    )
    envelope = await projector.project(_event("fragment", payload))
    assert envelope.payload["props"]["body"] == script


@pytest.mark.asyncio
async def test_project_done_settles_turn(
    projector: EventProjector,
) -> None:
    envelope = await projector.project(_event("done", "done"))

    assert envelope.payload["status"] == "done"
    assert envelope.payload["turn"]["state"] == "settled"


def test_registry_drops_unknown_and_invalid() -> None:
    registry = build_fragment_registry()
    calls = [
        SimpleNamespace(fragment="nope", params={}),
        SimpleNamespace(
            fragment="genui.plan_checklist",
            params={"steps": ["a"]},
        ),
    ]
    assert registry.validate_calls(calls) == []  # type: ignore[arg-type]

    good = [
        SimpleNamespace(
            fragment="genui.plan_checklist",
            params={"title": "Rite", "steps": ["a"]},
        ),
    ]
    validated = registry.validate_calls(good)  # type: ignore[arg-type]
    assert len(validated) == 1
    assert validated[0].key == "genui.plan_checklist"
