from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import CheckConstraint, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from lychd.db.models.session import Session
    from lychd.db.models.step import Step


class Run(UUIDAuditBase):
    """One workflow execution and the durable run substrate."""

    __tablename__ = "run"
    __table_args__ = (
        CheckConstraint(
            "status <> 'awaiting_consent' OR consent_id IS NOT NULL",
            name="waiting_consent_owner",
        ),
        CheckConstraint("status <> 'awaiting_peer' OR peer_task_id IS NOT NULL", name="waiting_peer_owner"),
        CheckConstraint(
            "(CASE WHEN consent_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN delegated_job_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN peer_task_id IS NULL THEN 0 ELSE 1 END) <= 1",
            name="single_wait_owner",
        ),
    )

    workflow_name: Mapped[str] = mapped_column(String(100), index=True)
    pattern_manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    source: Mapped[str] = mapped_column(String(20))  # bridge|cli|api|rite
    status: Mapped[str] = mapped_column(String(20), default="queued", server_default=text("'queued'"), index=True)
    #   RunStatus (A4): queued|running|awaiting_hardware|awaiting_consent|awaiting_delegate|awaiting_peer|cancelling|done|failed|cancelled
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
    consent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "consent.id",
            name="fk_run_consent_id_consent",
            ondelete="SET NULL",
            use_alter=True,
        ),
        nullable=True,
        index=True,
    )
    delegated_job_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    peer_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("intercom_task.id", name="fk_run_peer_task_id_intercom_task", ondelete="RESTRICT", use_alter=True),
        nullable=True,
        index=True,
    )
    session: Mapped[Session | None] = relationship(back_populates="runs", lazy="noload")
    steps: Mapped[list[Step]] = relationship(back_populates="run", lazy="noload", cascade="all, delete-orphan")
