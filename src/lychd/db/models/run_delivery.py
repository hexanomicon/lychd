from __future__ import annotations

from datetime import datetime
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column


class RunDelivery(UUIDAuditBase):
    """One durable broker-publication hop for an exact Run sequence."""

    __tablename__ = "run_delivery"
    __table_args__ = (
        CheckConstraint(
            "state IN ('held', 'pending', 'published', 'claimed', 'settled')",
            name="state",
        ),
        CheckConstraint(
            "publish_attempts >= 0",
            name="publish_attempts_nonnegative",
        ),
        CheckConstraint("enqueue_seq >= 0", name="enqueue_seq_nonnegative"),
        CheckConstraint("priority BETWEEN 0 AND 100", name="priority_range"),
        Index("ix_run_delivery_state_queue_name", "state", "queue_name"),
        Index(
            "uq_run_delivery_one_active",
            "run_id",
            unique=True,
            postgresql_where=text("state <> 'settled'"),
        ),
        UniqueConstraint("run_id", "enqueue_seq", name="uq_run_delivery_run_enqueue_seq"),
    )

    run_id: Mapped[UUID] = mapped_column(ForeignKey("run.id", ondelete="CASCADE"))
    enqueue_seq: Mapped[int] = mapped_column()
    queue_name: Mapped[str] = mapped_column(String(50))
    priority: Mapped[int] = mapped_column()
    resume: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    state: Mapped[str] = mapped_column(String(20), default="pending", server_default=text("'pending'"))
    publish_attempts: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(nullable=True)


__all__ = ["RunDelivery"]
