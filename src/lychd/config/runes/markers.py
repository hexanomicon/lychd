"""Pure wire markers shared by Rune readers and writers."""

from typing import Final

SAMPLE_MARKER: Final = "# lychd: sample-rune"
"""Identify generated sample TOML that is not yet authoritative intent."""

__all__ = ("SAMPLE_MARKER",)
