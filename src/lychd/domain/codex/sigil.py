"""`Sigil` — the Magus's authority handle (moved from agents/deps.py, ADR-09).

A frozen name + scope set, never the secret. Lives in `domain/codex` (the identity
floor) so both the agent plane and the web middleware read ONE definition. The old
home (`agents/deps.py`) re-exports it, so no call site breaks.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class Sigil:
    """The Magus's authority handle: a name and a set of scopes, never the secret."""

    name: str
    scopes: frozenset[str]


__all__ = ["Sigil"]
