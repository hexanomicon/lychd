from __future__ import annotations

from datetime import datetime
from typing import Any

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class SoulstoneRecord(UUIDAuditBase):
    """DB *projection* of a bound soulstone rune.

    TOML remains the source of truth (Codex law); this row exists so
    Run.capability_key and the Nexus board can join against history.
    """

    __tablename__ = "soulstone_record"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    runtime: Mapped[str] = mapped_column(String(50))
    source_file: Mapped[str] = mapped_column(String(500))
    rune_hash: Mapped[str] = mapped_column(String(64))  # sha256 of TOML bytes
    spec: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # model_dump of the rune
    enabled: Mapped[bool] = mapped_column(default=True)
    last_bound_at: Mapped[datetime | None] = mapped_column(nullable=True)
