"""Bounded, lossless Discord text projection without transport effects.

Only ordinary line-oriented triple-backtick fences receive synthetic closing and
reopening markers. Those markers never replace source text. If their overhead
cannot fit the finite budget, exact source slices take precedence over formatting.
"""

from __future__ import annotations

import re
from bisect import bisect_left, bisect_right

_MAX_LIMIT = 2000
_MAX_PARTS = 6
_BMP_MAX = 0xFFFF
_SURROGATE_START = 0xD800
_SURROGATE_END = 0xDFFF
_INVALID = "discord_message_invalid"
_TOO_LARGE = "discord_message_too_large"
_FENCE_LINE = re.compile(r"(?m)^ {0,3}```(?P<info>[^`\r\n]*)(?:\r?\n|\Z)")


def discord_units(text: str) -> int:
    """Count UTF-16 units, refusing non-text and isolated surrogate code points.

    Empty text has zero units. No encoding allocation or Unicode normalization is
    performed, and supplementary characters count as two units.
    """
    if type(text) is not str:
        raise ValueError(_INVALID)
    total = 0
    for character in text:
        codepoint = ord(character)
        if _SURROGATE_START <= codepoint <= _SURROGATE_END:
            raise ValueError(_INVALID)
        total += 1 + (codepoint > _BMP_MAX)
    return total


def _fences(text: str) -> tuple[list[str | None], list[bool]]:
    """Track the opener at each source boundary and protect structural lines."""
    contexts: list[str | None] = [None] * (len(text) + 1)
    protected = [False] * (len(text) + 1)
    opener: str | None = None
    position = 0
    for match in _FENCE_LINE.finditer(text):
        if opener is not None and match["info"].strip():
            continue
        contexts[position : match.start() + 1] = [opener] * (match.start() + 1 - position)
        protected[match.start() + 1 : match.end()] = [True] * (match.end() - match.start() - 1)
        opener = (match[0] if match[0].endswith("\n") else match[0] + "\n") if opener is None else None
        position = match.end()
    contexts[position:] = [opener] * (len(text) + 1 - position)
    return contexts, protected


def _suffix(text: str, end: int, contexts: list[str | None]) -> str:
    if end == len(text) or contexts[end] is None:
        return ""
    return "```" if text[end - 1] == "\n" else "\n```"


def _boundary(text: str, end: int) -> tuple[int, int]:
    if text.endswith(("\n\n", "\r\n\r\n"), 0, end):
        return 3, end
    if text[end - 1] == "\n":
        return 2, end
    return int(text[end - 1].isspace()), end


def _partition(
    text: str,
    offsets: list[int],
    contexts: list[str | None],
    protected: list[bool],
    *,
    limit: int,
    max_parts: int,
    prefer_boundaries: bool,
) -> tuple[str, ...] | None:
    parts: list[str] = []
    start = 0
    while start < len(text) and len(parts) < max_parts:
        prefix = contexts[start] or ""
        prefix_units = discord_units(prefix)
        end = bisect_right(offsets, offsets[start] + limit - prefix_units, lo=start + 1) - 1
        minimum = max(start + 1, bisect_left(offsets, offsets[-1] - (max_parts - len(parts) - 1) * limit))
        candidates = [
            boundary
            for boundary in range(minimum, end + 1)
            if not protected[boundary]
            and prefix_units + offsets[boundary] - offsets[start] + len(_suffix(text, boundary, contexts)) <= limit
        ]
        if not candidates:
            return None
        end = candidates[-1]
        if prefer_boundaries and end != len(text):
            end = max(candidates, key=lambda boundary: _boundary(text, boundary))
        parts.append(prefix + text[start:end] + _suffix(text, end, contexts))
        start = end
    return tuple(parts) if start == len(text) else None


def split_message(text: str, *, limit: int = 1900, max_parts: int = 6) -> tuple[str, ...]:
    """Project nonblank text into at most six messages of at most 2,000 units.

    ``limit`` and ``max_parts`` must be plain integers in ``1..2000`` and
    ``1..6`` respectively. Invalid values, blank text and surrogate code points
    raise ``ValueError("discord_message_invalid")``. Text that cannot fit the
    budget raises ``ValueError("discord_message_too_large")`` before any caller
    can send a partial result. Limits include synthetic fence markers.

    Paragraph, newline and whitespace boundaries are preferred in that order.
    Source whitespace is never stripped. Single-part text is returned unchanged;
    multipart output adds no numbering, ellipsis or truncation notice.
    """
    if (
        type(text) is not str
        or not text
        or type(limit) is not int
        or not 1 <= limit <= _MAX_LIMIT
        or type(max_parts) is not int
        or not 1 <= max_parts <= _MAX_PARTS
    ):
        raise ValueError(_INVALID)
    if len(text) > limit * max_parts:
        raise ValueError(_TOO_LARGE)
    total = discord_units(text)
    if not text.strip():
        raise ValueError(_INVALID)
    if total > limit * max_parts:
        raise ValueError(_TOO_LARGE)
    if total <= limit:
        return (text,)
    offsets = [0]
    for character in text:
        offsets.append(offsets[-1] + 1 + (ord(character) > _BMP_MAX))
    contexts, protected = _fences(text)
    plain_contexts: list[str | None] = [None] * len(offsets)
    for fence_contexts, fence_protected in ((contexts, protected), (plain_contexts, [False] * len(offsets))):
        for prefer_boundaries in (True, False):
            result = _partition(
                text,
                offsets,
                fence_contexts,
                fence_protected,
                limit=limit,
                max_parts=max_parts,
                prefer_boundaries=prefer_boundaries,
            )
            if result is not None:
                return result
    raise ValueError(_TOO_LARGE)
