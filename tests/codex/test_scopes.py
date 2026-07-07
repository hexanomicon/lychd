"""Scope grammar property tests (wave4-design §3.2)."""

from __future__ import annotations

import pytest

from lychd.domain.codex.scopes import scopes_satisfied


@pytest.mark.parametrize(
    ("held", "required", "expected"),
    [
        # "*" grants everything
        (["*"], ["runs:submit", "altar:read", "codex:administer"], True),
        # "runs:*" grants any runs action only
        (["runs:*"], ["runs:submit"], True),
        (["runs:*"], ["runs:approve"], True),
        (["runs:*"], ["altar:read"], False),
        # exact match
        (["altar:read"], ["altar:read"], True),
        (["altar:read"], ["runs:submit"], False),
        # case-sensitive
        (["Runs:submit"], ["runs:submit"], False),
        (["runs:submit"], ["RUNS:submit"], False),
        # empty required is satisfied by anything (even empty held)
        ([], [], True),
        (["altar:read"], [], True),
        # empty held satisfies nothing non-empty
        ([], ["altar:read"], False),
        # every required must be covered
        (["altar:read", "runs:submit"], ["altar:read", "runs:submit"], True),
        (["altar:read"], ["altar:read", "runs:submit"], False),
    ],
)
def test_scopes_satisfied(held: list[str], required: list[str], *, expected: bool) -> None:
    assert scopes_satisfied(held, required) is expected
