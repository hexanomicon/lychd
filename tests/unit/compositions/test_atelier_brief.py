"""Public brief grammar and first-start eligibility."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from lychd.compositions.atelier.brief import ShortVideoBrief

_BRIEF = {"recipe": "illustrated-story", "script": "A public story.", "duration_seconds": 30}
_OPEN = "2026-11-19T18:00:00Z"
_CLOSE = "2026-11-19T20:30:00+00:00"


def test_omitted_window_retains_existing_wire_shape() -> None:
    brief = ShortVideoBrief.from_wire(json.dumps(_BRIEF))
    assert json.loads(brief.model_dump_json()) == _BRIEF
    assert brief.can_start(datetime(2026, 11, 19, tzinfo=UTC))


def test_utc_window_is_half_open_and_roundtrips() -> None:
    brief = ShortVideoBrief.from_wire(json.dumps({**_BRIEF, "not_before": _OPEN, "latest_start_at": _CLOSE}))
    start = datetime.fromisoformat(_OPEN)
    end = datetime.fromisoformat(_CLOSE)
    tick = timedelta(microseconds=1)
    assert not brief.can_start(start - tick)
    assert brief.can_start(start)
    assert brief.can_start(end - tick)
    assert not brief.can_start(end)
    assert ShortVideoBrief.from_wire(brief.model_dump_json()) == brief


@pytest.mark.parametrize(
    "window",
    [
        {"not_before": _OPEN},
        {"latest_start_at": _CLOSE},
        {"not_before": None, "latest_start_at": None},
        {"not_before": 1_795_111_200, "latest_start_at": _CLOSE},
        {"not_before": "2026-11-19T19:00:00+01:00", "latest_start_at": _CLOSE},
        {"not_before": "2026-11-19T18:00:00", "latest_start_at": _CLOSE},
        {"not_before": _OPEN, "latest_start_at": _OPEN},
        {"not_before": _CLOSE, "latest_start_at": _OPEN},
        {"not_before": "2026-02-31T00:00:00Z", "latest_start_at": _CLOSE},
    ],
)
def test_ambiguous_invalid_and_empty_windows_refuse(window: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="UTC"):
        ShortVideoBrief.from_wire(json.dumps({**_BRIEF, **window}))


def test_duplicate_fields_refuse_before_interpreting_either_value() -> None:
    text = json.dumps(_BRIEF)[:-1] + ',"script":"replacement"}'
    with pytest.raises(ValueError, match="Duplicate brief field"):
        ShortVideoBrief.from_wire(text)
