from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from lychd.db.models.run import Run


class DelegatedAgentJobRecord(UUIDAuditBase):
    """Durable LychD-owned identity and state for one delegated-agent job."""

    __tablename__ = "delegated_agent_job"

    job_id: Mapped[str] = mapped_column(String(128), unique=True)
    request_id: Mapped[str] = mapped_column(String(128), unique=True)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("run.id", ondelete="CASCADE"), index=True)
    runtime: Mapped[str] = mapped_column(String(128), index=True)
    profile: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), index=True)
    request: Mapped[dict[str, Any]] = mapped_column(JSONB)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    run: Mapped[Run] = relationship(lazy="noload")
    events: Mapped[list[DelegatedAgentEventRecord]] = relationship(
        back_populates="job",
        lazy="noload",
        cascade="all, delete-orphan",
    )


class DelegatedAgentEventRecord(UUIDAuditBase):
    """One immutable semantic event in a delegated-agent job ledger."""

    __tablename__ = "delegated_agent_event"
    __table_args__ = (UniqueConstraint("job_record_id", "seq", name="uq_delegated_agent_event_job_seq"),)

    job_record_id: Mapped[UUID] = mapped_column(
        ForeignKey("delegated_agent_job.id", ondelete="CASCADE"),
        index=True,
    )
    event_id: Mapped[str] = mapped_column(String(128), unique=True)
    seq: Mapped[int] = mapped_column()
    kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)

    job: Mapped[DelegatedAgentJobRecord] = relationship(back_populates="events", lazy="noload")


__all__ = ["DelegatedAgentEventRecord", "DelegatedAgentJobRecord"]
