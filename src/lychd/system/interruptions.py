"""Shared discovery of terminal interruptions wrapped by effect transactions."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
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


def iter_exception_graph(error: BaseException) -> Iterator[BaseException]:
    """Yield linked transaction failures once, including explicit peer ledgers."""
    pending = [error]
    seen: set[int] = set()
    while pending:
        candidate = pending.pop()
        if id(candidate) in seen:
            continue
        seen.add(id(candidate))
        yield candidate
        linked_errors = [
            linked for linked in (candidate.__cause__, candidate.__context__) if isinstance(linked, BaseException)
        ]
        if isinstance(candidate, Exception):
            linked_errors.extend(
                linked
                for attribute in _LINKED_ERROR_ATTRIBUTES
                if isinstance(
                    linked := getattr(candidate, attribute, None),
                    BaseException,
                )
            )
            for attribute in _LINKED_ERROR_COLLECTIONS:
                linked_collection: object = getattr(candidate, attribute, ())
                if not isinstance(linked_collection, (tuple, list)):
                    continue
                linked_errors.extend(
                    linked
                    for linked in cast("Iterable[object]", linked_collection)
                    if isinstance(linked, BaseException)
                )
        pending.extend(reversed(linked_errors))


def find_terminal_interruption(
    error: BaseException,
) -> BaseException | None:
    """Find a wrapped ``KeyboardInterrupt`` or ``SystemExit`` without cycles."""
    for candidate in iter_exception_graph(error):
        if not isinstance(candidate, Exception):
            return candidate
    return None


__all__ = ("find_terminal_interruption", "iter_exception_graph")
