from __future__ import annotations

from datetime import datetime
from typing import Any

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import CheckConstraint, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class CodexPreauthorization(UUIDAuditBase):
    """A Codex-governed standing approval. ZTE is a *bounded* class of this, never blanket."""

    __tablename__ = "codex_preauthorization"
    __table_args__ = (CheckConstraint("priority BETWEEN 0 AND 100", name="priority_range"),)

    slug: Mapped[str] = mapped_column(String(100), unique=True)
    priority: Mapped[int] = mapped_column(default=50, server_default=text("50"))
    klass: Mapped[str] = mapped_column(String(20), default="standard")  # standard|zte
    sigil_pattern: Mapped[str] = mapped_column(String(100), default="*")  # fnmatch on sigil name
    tool_pattern: Mapped[str] = mapped_column(String(200))  # fnmatch on tool name
    constraints: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # arg allowlists, path prefixes
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    max_uses: Mapped[int | None] = mapped_column(nullable=True)
    uses: Mapped[int] = mapped_column(default=0)
    enabled: Mapped[bool] = mapped_column(default=True)
    source_present: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    granted_by: Mapped[str] = mapped_column(String(100))
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)  # TOML provenance
