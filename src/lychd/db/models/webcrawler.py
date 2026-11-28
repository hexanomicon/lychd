"""Restricted Webcrawler preparation, consent linkage and worst-case reservation custody."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class WebcrawlerBudget(UUIDAuditBase):
    """Permanent host/binding slots: changing a name cannot reset consumed capacity."""

    __tablename__ = "scout_budget"
    __table_args__ = (
        CheckConstraint("scope IN ('host','binding')", name="scope"),
        CheckConstraint(
            "(scope = 'host' AND active_claims = 0) OR (scope = 'binding' AND active_claims BETWEEN 0 AND 1)",
            name="active_binding_limit",
        ),
        CheckConstraint(
            "connects_limit >= 0 AND connects_reserved >= 0 AND connects_used >= 0 AND connects_used <= connects_limit - connects_reserved",
            name="connects_ceiling",
        ),
        CheckConstraint(
            "transmissions_limit >= 0 AND transmissions_reserved >= 0 AND transmissions_used >= 0 AND transmissions_used <= transmissions_limit - transmissions_reserved",
            name="transmissions_ceiling",
        ),
        CheckConstraint(
            "wire_bytes_limit >= 0 AND wire_bytes_reserved >= 0 AND wire_bytes_used >= 0 AND wire_bytes_used <= wire_bytes_limit - wire_bytes_reserved",
            name="wire_bytes_ceiling",
        ),
    )
    scope: Mapped[str] = mapped_column(String(10), unique=True)
    configuration_digest: Mapped[str] = mapped_column(String(64))
    active_claims: Mapped[int] = mapped_column(default=0)
    connects_limit: Mapped[int] = mapped_column(BigInteger)
    transmissions_limit: Mapped[int] = mapped_column(BigInteger)
    wire_bytes_limit: Mapped[int] = mapped_column(BigInteger)
    connects_reserved: Mapped[int] = mapped_column(BigInteger, default=0)
    transmissions_reserved: Mapped[int] = mapped_column(BigInteger, default=0)
    wire_bytes_reserved: Mapped[int] = mapped_column(BigInteger, default=0)
    connects_used: Mapped[int] = mapped_column(BigInteger, default=0)
    transmissions_used: Mapped[int] = mapped_column(BigInteger, default=0)
    wire_bytes_used: Mapped[int] = mapped_column(BigInteger, default=0)


class WebcrawlerAttempt(UUIDAuditBase):
    """One immutable request; a durable claim never becomes a second live permit."""

    __tablename__ = "scout_attempt"
    __table_args__ = (
        CheckConstraint("status IN ('prepared','claimed','unknown_after_crash','succeeded','refused')", name="status"),
        CheckConstraint("preparation_enqueue_seq >= 0", name="preparation_sequence"),
        CheckConstraint("execution_enqueue_seq IS NULL OR execution_enqueue_seq >= 0", name="execution_sequence"),
        CheckConstraint(
            "(status = 'prepared' AND claim_id IS NULL AND execution_enqueue_seq IS NULL AND claimed_at IS NULL) OR (status <> 'prepared' AND claim_id IS NOT NULL AND execution_enqueue_seq IS NOT NULL AND claimed_at IS NOT NULL)",
            name="claim_complete",
        ),
        CheckConstraint(
            "(status IN ('succeeded','refused') AND receipt_id IS NOT NULL AND settlement_bytes IS NOT NULL) OR (status NOT IN ('succeeded','refused') AND receipt_id IS NULL AND settlement_bytes IS NULL)",
            name="settlement_complete",
        ),
    )
    request_id: Mapped[UUID] = mapped_column(unique=True)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("run.id", ondelete="RESTRICT"))
    consent_id: Mapped[UUID] = mapped_column(ForeignKey("consent.id", ondelete="RESTRICT"), unique=True)
    preparation_enqueue_seq: Mapped[int] = mapped_column(BigInteger)
    preparation_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    preparation_digest: Mapped[str] = mapped_column(String(64))
    native_binding: Mapped[dict[str, Any]] = mapped_column(JSONB)
    review_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    status: Mapped[str] = mapped_column(String(24))
    claim_id: Mapped[UUID | None] = mapped_column(unique=True, nullable=True)
    execution_enqueue_seq: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    receipt_id: Mapped[UUID | None] = mapped_column(unique=True, nullable=True)
    settlement_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
