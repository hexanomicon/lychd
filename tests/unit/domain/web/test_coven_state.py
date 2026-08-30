"""A6 / seam S9: the projector-owned capability data-state mapping."""

from __future__ import annotations

from typing import Any, cast

import pytest

from lychd.domain.web.schemas import build_nexus_board


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
        "is_dynamic": True,
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


@pytest.mark.parametrize(
    ("phase", "mode", "expected"),
    [
        ("activatable", "dynamic", "awaited"),
        ("activatable", "static", "cold"),
        ("warm", "dynamic", "active"),
        ("warming", "dynamic", "warming"),
        ("error", "dynamic", "fault"),
        ("unknown", "static", "cold"),
    ],
)
def test_build_nexus_board_projects_capability_state(
    phase: str,
    mode: str,
    expected: str,
) -> None:
    board = build_nexus_board(
        cast("Any", _FakeOrchestrator([_status(phase=phase, is_dynamic=mode == "dynamic")])),
        cast("Any", _FakeRegistry()),
    )
    assert board.covens[0][1][0].state == expected
