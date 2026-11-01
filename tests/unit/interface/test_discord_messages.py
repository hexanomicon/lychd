from __future__ import annotations

from typing import Any

import pytest

from lychd.interface.discord.messages import discord_units, split_message


@pytest.mark.parametrize(
    ("text", "expected"),
    [("", 0), ("plain", 5), ("é漢", 2), ("A😀é", 4), ("👩\u200d💻", 5), ("e\u0301", 2)],
)
def test_units_count_utf16_without_normalization(text: str, expected: int) -> None:
    assert discord_units(text) == expected


@pytest.mark.parametrize("text", [None, b"text", 123, "\ud800", "a\udfffz"])
def test_units_refuse_invalid_values_without_echoing_input(text: Any) -> None:
    with pytest.raises(ValueError, match=r"^discord_message_invalid$"):
        discord_units(text)


def test_single_part_preserves_all_whitespace_and_formatting() -> None:
    text = " \tHello 🌒\r\n```py\nx = 1\n```\n "
    assert split_message(text) == (text,)


@pytest.mark.parametrize(
    ("text", "limit", "expected"),
    [
        ("one\n\ntwo three four", 12, ("one\n\n", "two three ", "four")),
        ("aaaa\nbbbb cccc", 10, ("aaaa\n", "bbbb cccc")),
        ("alpha beta gamma", 11, ("alpha beta ", "gamma")),
        ("one\r\n\r\ntwo three", 12, ("one\r\n\r\n", "two three")),
    ],
)
def test_prefers_paragraph_then_line_then_space_boundaries(text: str, limit: int, expected: tuple[str, ...]) -> None:
    parts = split_message(text, limit=limit)
    assert parts == expected
    assert "".join(parts) == text


def test_tight_part_budget_takes_precedence_over_early_word_boundary() -> None:
    text = "a " + "x" * 18
    parts = split_message(text, limit=10, max_parts=2)
    assert parts == (text[:10], text[10:])
    assert "".join(parts) == text


def test_supplementary_characters_fit_by_units_and_are_never_split() -> None:
    text = "🌒" * 1901
    parts = split_message(text)
    assert parts == ("🌒" * 950, "🌒" * 950, "🌒")
    assert all(discord_units(part) <= 1900 for part in parts)
    assert "".join(parts) == text


def test_closes_and_reopens_ordinary_fence_without_losing_code_or_language() -> None:
    opener = "```py\n"
    body = "print(1)\n" * 2
    text = opener + body * 4 + "```\n"
    parts = split_message(text, limit=30)
    assert parts == ((opener + body + "```"),) * 3 + (opener + body + "```\n",)
    restored = parts[0].removesuffix("```")
    restored += "".join(part.removeprefix(opener).removesuffix("```") for part in parts[1:-1])
    restored += parts[-1].removeprefix(opener)
    assert restored == text
    assert all(discord_units(part) <= 30 for part in parts)


def test_fence_overhead_never_rejects_text_that_fits_as_exact_slices() -> None:
    text = "```py\n123456789012\n```"
    parts = split_message(text, limit=11, max_parts=2)
    assert "".join(parts) == text
    assert len(parts) == 2
    assert all(discord_units(part) <= 11 for part in parts)


def test_inline_backticks_are_preserved_as_source_text() -> None:
    text = "prefix ```not a block``` suffix"
    parts = split_message(text, limit=12)
    assert "".join(parts) == text
    assert all(discord_units(part) <= 12 for part in parts)


@pytest.mark.parametrize("text", [None, b"private text", "", " \t\r\n", "private\ud800text"])
def test_split_refuses_invalid_or_blank_text_with_fixed_code(text: Any) -> None:
    with pytest.raises(ValueError, match=r"^discord_message_invalid$"):
        split_message(text)


@pytest.mark.parametrize("limit", [0, -1, 2001, True, 1.5, None])
def test_split_refuses_invalid_limit(limit: Any) -> None:
    with pytest.raises(ValueError, match=r"^discord_message_invalid$"):
        split_message("private text", limit=limit)


@pytest.mark.parametrize("max_parts", [0, -1, 7, True, 1.5, None])
def test_split_refuses_invalid_part_budget(max_parts: Any) -> None:
    with pytest.raises(ValueError, match=r"^discord_message_invalid$"):
        split_message("private text", max_parts=max_parts)


@pytest.mark.parametrize("text", ["x" * 11401, "🌒" * 5701])
def test_split_refuses_oversize_instead_of_returning_partial_text(text: str) -> None:
    with pytest.raises(ValueError, match=r"^discord_message_too_large$"):
        split_message(text)


def test_codepoint_larger_than_each_part_budget_is_refused() -> None:
    with pytest.raises(ValueError, match=r"^discord_message_too_large$"):
        split_message("🌒", limit=1)


def test_single_part_budget_accepts_exact_limit_and_refuses_overflow() -> None:
    assert split_message("xx", limit=2, max_parts=1) == ("xx",)
    with pytest.raises(ValueError, match=r"^discord_message_too_large$"):
        split_message("xxx", limit=2, max_parts=1)


@pytest.mark.parametrize("text", ["x" * 111, "x \t\n" * 25, "é😀\t \n" * 16])
def test_plain_split_is_deterministic_bounded_and_lossless(text: str) -> None:
    parts = split_message(text, limit=24)
    assert parts == split_message(text, limit=24)
    assert 1 <= len(parts) <= 6
    assert all(part and discord_units(part) <= 24 for part in parts)
    assert "".join(parts) == text
