"""Loop-safe execution identity propagated from GraphRunner into dispatch."""

from __future__ import annotations

from contextvars import ContextVar, Token

_OCCURRENCE_ID: ContextVar[str | None] = ContextVar("lychd_occurrence_id", default=None)


def current_occurrence_id() -> str | None:
    """Return the active Graph node occurrence for this async context."""
    return _OCCURRENCE_ID.get()


def bind_occurrence(occurrence_id: str) -> Token[str | None]:
    """Bind one node occurrence until the caller resets the returned token."""
    return _OCCURRENCE_ID.set(occurrence_id)


def reset_occurrence(token: Token[str | None]) -> None:
    """Restore the prior occurrence binding."""
    _OCCURRENCE_ID.reset(token)
