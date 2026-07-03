from __future__ import annotations

from datetime import datetime
from typing import Any

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class CodexPreauthorization(UUIDAuditBase):
    """A Codex-governed standing approval. ZTE is a *bounded* class of this, never blanket."""

    __tablename__ = "codex_preauthorization"

    slug: Mapped[str] = mapped_column(String(100), unique=True)
    klass: Mapped[str] = mapped_column(String(20), default="standard")  # standard|zte
    sigil_pattern: Mapped[str] = mapped_column(String(100), default="*")  # fnmatch on sigil name
    tool_pattern: Mapped[str] = mapped_column(String(200))  # fnmatch on tool name
    constraints: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # arg allowlists, path prefixes
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    max_uses: Mapped[int | None] = mapped_column(nullable=True)
    uses: Mapped[int] = mapped_column(default=0)
    enabled: Mapped[bool] = mapped_column(default=True)
    granted_by: Mapped[str] = mapped_column(String(100))
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)  # TOML provenance
