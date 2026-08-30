"""Strict JSON object hooks shared by authority-bearing documents."""

from __future__ import annotations


def unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Build an object while rejecting JSON's otherwise ambiguous duplicate keys."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            msg = f"Duplicate JSON key: {key!r}."
            raise ValueError(msg)
        result[key] = value
    return result
