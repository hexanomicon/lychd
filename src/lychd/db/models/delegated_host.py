"""Restrictive no-reuse history for the non-authorizing host precursor."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import CheckConstraint, ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column


class DelegatedHostDispositionRecord(UUIDAuditBase):
    """One exact preparation/consumption and monotonic logical intake tombstone."""

    __tablename__ = "delegated_host_disposition"
    __table_args__ = (
        CheckConstraint(
            "(preparation_bytes IS NULL AND preparation_digest IS NULL AND prepared_at IS NULL) OR "
            "(preparation_bytes IS NOT NULL AND preparation_digest IS NOT NULL AND prepared_at IS NOT NULL)",
            name="preparation_complete",
        ),
        CheckConstraint(
            "preparation_bytes IS NULL OR octet_length(preparation_bytes) BETWEEN 1 AND 2097152",
            name="preparation_bytes_bounded",
        ),
        CheckConstraint(
            "preparation_digest IS NULL OR preparation_digest ~ '^sha256:[0-9a-f]{64}$'",
            name="preparation_digest",
        ),
        CheckConstraint(
            "(dispatch_id IS NULL AND dispatch_consumed_at IS NULL) OR "
            "(dispatch_id IS NOT NULL AND dispatch_consumed_at IS NOT NULL AND preparation_bytes IS NOT NULL)",
            name="dispatch_complete",
        ),
        CheckConstraint("preparation_bytes IS NOT NULL OR intake_closed_at IS NOT NULL", name="retained_disposition"),
    )

    job_record_id: Mapped[UUID] = mapped_column(ForeignKey("delegated_agent_job.id", ondelete="RESTRICT"), unique=True)
    preparation_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    preparation_digest: Mapped[str | None] = mapped_column(String(71), nullable=True)
    prepared_at: Mapped[datetime | None] = mapped_column(nullable=True)
    dispatch_id: Mapped[UUID | None] = mapped_column(unique=True, nullable=True)
    dispatch_consumed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    intake_closed_at: Mapped[datetime | None] = mapped_column(nullable=True)
