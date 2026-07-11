from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from lychd.db.models.session import Session
    from lychd.db.models.step import Step


class Run(UUIDAuditBase):
    """One workflow execution. THE durable run substrate (adw-kit Part 2.2/2.4 pattern)."""

    __tablename__ = "run"

    workflow_name: Mapped[str] = mapped_column(String(100), index=True)
    source: Mapped[str] = mapped_column(String(20))  # bridge|cli|api|rite
    status: Mapped[str] = mapped_column(String(20), default="queued", server_default=text("'queued'"), index=True)
    #   RunStatus (A4): queued|running|awaiting_hardware|awaiting_consent|done|failed|cancelled
    priority: Mapped[int] = mapped_column(default=50, server_default=text("50"))
    sigil_name: Mapped[str] = mapped_column(String(100))
    intent: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # serialized Intent
    capability_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("session.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # C4 additions (A4 durable-run substrate fields):
    queue_name: Mapped[str] = mapped_column(String(50))
    attempt: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    enqueue_seq: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    session: Mapped[Session | None] = relationship(back_populates="runs", lazy="noload")
    steps: Mapped[list[Step]] = relationship(back_populates="run", lazy="noload", cascade="all, delete-orphan")
