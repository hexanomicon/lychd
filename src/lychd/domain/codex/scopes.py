"""Scope grammar (wave4-design §3.2): `scopes_satisfied` + `_scope_match`.

Case-sensitive `fnmatch` over `resource:action` tokens. Core vocabulary:
`altar:read`, `runs:submit`, `runs:approve`, `orchestrator:transition`,
`codex:administer`, `privilege:escalate`; extension scopes read `ext/{id}:{action}`.
A held `"*"` grants everything; a held `"runs:*"` grants any `runs` action only.
"""

from __future__ import annotations

from collections.abc import Iterable
from fnmatch import fnmatchcase

__all__ = ["scopes_satisfied"]


def _scope_match(held: str, required: str) -> bool:
    """Whether one held scope pattern satisfies one required scope (case-sensitive)."""
    return fnmatchcase(required, held)


def scopes_satisfied(held: Iterable[str], required: Iterable[str]) -> bool:
    """Whether the held scope set satisfies every required scope.

    Empty ``required`` is satisfied by anything; a non-empty ``required`` is never
    satisfied by an empty held set.
    """
    held_set = frozenset(held)
    return all(any(_scope_match(pattern, need) for pattern in held_set) for need in required)
