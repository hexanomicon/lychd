"""Shared discovery of terminal interruptions wrapped by effect transactions."""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast

_LINKED_ERROR_ATTRIBUTES = (
    "cause",
    "forward_error",
    "rollback_error",
)
_LINKED_ERROR_COLLECTIONS = (
    "cleanup_errors",
    "failures",
)


def find_terminal_interruption(
    error: BaseException,
) -> BaseException | None:
    """Find a wrapped ``KeyboardInterrupt`` or ``SystemExit`` without cycles."""
    pending = [error]
    seen: set[int] = set()
    while pending:
        candidate = pending.pop()
        if id(candidate) in seen:
            continue
        seen.add(id(candidate))
        if not isinstance(candidate, Exception):
            return candidate
        linked_errors = (
            candidate.__cause__,
            candidate.__context__,
            *(getattr(candidate, attribute, None) for attribute in _LINKED_ERROR_ATTRIBUTES),
        )
        pending.extend(linked for linked in linked_errors if isinstance(linked, BaseException))
        for attribute in _LINKED_ERROR_COLLECTIONS:
            linked_collection: object = getattr(candidate, attribute, ())
            if isinstance(linked_collection, (tuple, list)):
                pending.extend(
                    linked
                    for linked in cast("Iterable[object]", linked_collection)
                    if isinstance(linked, BaseException)
                )
    return None


__all__ = ("find_terminal_interruption",)
