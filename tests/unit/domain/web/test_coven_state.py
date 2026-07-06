"""A6 / seam S9: the projector-owned capability data-state mapping."""

from __future__ import annotations

from typing import Any, cast

from lychd.domain.web.schemas import _coven_state, build_nexus_board


def test_s9_awaited_mapping() -> None:
    # The S9 row: a DYNAMIC capability observed ACTIVATABLE is "awaited".
    assert _coven_state(lifecycle="dynamic", phase="activatable") == "awaited"
    # A STATIC one there shouldn't occur; degrade honestly to "cold".
    assert _coven_state(lifecycle="static", phase="activatable") == "cold"
    # The rest of the table.
    assert _coven_state(lifecycle="dynamic", phase="warm") == "active"
    assert _coven_state(lifecycle="static", phase="warm") == "active"
    assert _coven_state(lifecycle="dynamic", phase="warming") == "warming"
    assert _coven_state(lifecycle="dynamic", phase="cold") == "cold"
    assert _coven_state(lifecycle="static", phase="unknown") == "cold"
    assert _coven_state(lifecycle="dynamic", phase="error") == "fault"


class _FakeOrchestrator:
    def __init__(self, statuses: list[dict[str, Any]]) -> None:
        self._statuses = statuses

    def list_capability_statuses(self) -> list[dict[str, Any]]:
        return self._statuses


class _FakeRegistry:
    def get_soulstone_rune(self, name: str) -> None:
        _ = name


def _status(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "capability_key": "atelier:vision:the-eye",
        "animator_name": "atelier",
        "family": "vision",
        "runtime": "llamacpp",
        "model_id": "the-eye",
        "lifecycle": "dynamic",
        "phase": "activatable",
        "is_active": False,
        "warm": False,
        "health": "ok",
        "reason": None,
        "dedicated": True,
        "persistent_resident": False,
        "source_kind": "soulstone",
    }
    base.update(overrides)
    return base


def test_build_nexus_board_projects_the_awaited_row() -> None:
    board = build_nexus_board(
        cast("Any", _FakeOrchestrator([_status()])),
        cast("Any", _FakeRegistry()),
    )
    row = board.covens[0][1][0]
    assert row.state == "awaited"


def test_no_enum_leaks_to_templates() -> None:
    # The projector consumes the string phase/lifecycle keys, never enum objects.
    board = build_nexus_board(
        cast("Any", _FakeOrchestrator([_status(phase="warm", is_active=True, warm=True)])),
        cast("Any", _FakeRegistry()),
    )
    assert board.covens[0][1][0].state == "active"
