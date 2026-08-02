"""Codex preauthorization runes (wave4-design §3.4d).

`CodexPreauthRune` is a TOML-backed standing approval under
``runes/codex/preauth/*.toml``. ZTE (`klass="zte"`) is a *bounded* class: it MUST
declare `expires_at`, `max_uses`, and `constraints` — the `_zte_is_bounded`
validator raises loudly if any is missing (never silently downgraded).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Literal

from pydantic import Field, model_validator

from lychd.config.runes import RuneConfig

__all__ = ["CodexPreauthRune", "CodexRune"]


class CodexRune(RuneConfig):
    """Typed policy declarations governing authority and consent."""

    path_fragment: ClassVar[Path] = Path("codex")


class CodexPreauthRune(CodexRune):
    """Standing approvals for matching Sigils and tools.

    Standard approvals match patterns. ZTE approvals additionally carry
    constraints, expiry, and a use budget.
    """

    path_fragment: ClassVar[Path] = Path("preauth")
    sample_template: ClassVar[str | None] = """
slug = "example-preauth"
klass = "standard"
sigil_pattern = "*"
tool_pattern = "request_coven_swap"
"""

    slug: str = Field(min_length=1, description="Stable unique identity for this preauthorization.")
    priority: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Selection precedence; higher wins, slug breaks ties.",
    )
    klass: Literal["standard", "zte"] = Field(default="standard", description="standard | zte (bounded).")
    sigil_pattern: str = Field(default="*", description="fnmatch pattern over the sigil name.")
    tool_pattern: str = Field(description="fnmatch pattern over the tool name.")
    constraints: dict[str, Any] = Field(default_factory=dict, description="Arg allowlists / path prefixes.")
    expires_at: datetime | None = Field(default=None, description="Absolute expiry; required for ZTE.")
    max_uses: int | None = Field(default=None, ge=1, description="Total grant budget; required for ZTE.")

    @model_validator(mode="after")
    def _zte_is_bounded(self) -> CodexPreauthRune:
        """ZTE preauthorizations MUST be bounded (§3.4c) — raise loudly otherwise."""
        if self.klass == "zte" and not (self.expires_at and self.max_uses and self.constraints):
            msg = (
                f"ZTE preauthorization '{self.slug}' must declare expires_at, max_uses, and constraints "
                "(a Zero-Trust Escalation is a BOUNDED class, never blanket)."
            )
            raise ValueError(msg)
        return self
