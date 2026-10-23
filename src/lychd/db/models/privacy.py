"""Monotonic restricted offline disclosure custody; no payloads or reset API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class DisclosureCapacityRecord(UUIDAuditBase):
    """Permanent host, purpose and Cut ceilings with full nonrefundable charges."""

    __tablename__ = "privacy_disclosure_capacity"
    __table_args__ = (
        UniqueConstraint("scope", "scope_id", name="uq_privacy_disclosure_capacity_scope"),
        CheckConstraint("scope IN ('host','purpose','cut')", name="scope"),
        CheckConstraint("uses_limit >= 0 AND uses_charged >= 0 AND uses_charged <= uses_limit", name="uses_ceiling"),
        CheckConstraint(
            "bytes_limit >= 0 AND bytes_charged >= 0 AND bytes_charged <= bytes_limit", name="bytes_ceiling"
        ),
    )
    scope: Mapped[str] = mapped_column(String(10))
    scope_id: Mapped[str] = mapped_column(String(36))
    configuration_digest: Mapped[str] = mapped_column(String(64))
    uses_limit: Mapped[int] = mapped_column(BigInteger)
    bytes_limit: Mapped[int] = mapped_column(BigInteger)
    uses_charged: Mapped[int] = mapped_column(BigInteger, default=0)
    bytes_charged: Mapped[int] = mapped_column(BigInteger, default=0)


class DisclosureTransmission(UUIDAuditBase):
    """One retained occurrence; live claims and completion objects are never stored."""

    __tablename__ = "privacy_disclosure_transmission"
    __table_args__ = (
        UniqueConstraint("run_id", "occurrence_id", "attempt_id", name="uq_privacy_disclosure_occurrence"),
        CheckConstraint("status IN ('prepared','claimed','recorded','refused','unknown')", name="status"),
        CheckConstraint(
            "(status = 'prepared' AND claim_id IS NULL AND claimed_at IS NULL AND decision_bytes IS NULL) OR (status <> 'prepared' AND claim_id IS NOT NULL AND claimed_at IS NOT NULL AND decision_bytes IS NOT NULL)",
            name="claim_complete",
        ),
        CheckConstraint(
            "(status IN ('recorded','refused') AND receipt_id IS NOT NULL AND settlement_bytes IS NOT NULL) OR (status IN ('prepared','claimed') AND receipt_id IS NULL AND settlement_bytes IS NULL) OR status = 'unknown'",
            name="settlement_complete",
        ),
    )
    request_id: Mapped[UUID] = mapped_column(unique=True)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("run.id", ondelete="RESTRICT"))
    delivery_id: Mapped[UUID] = mapped_column(ForeignKey("run_delivery.id", ondelete="RESTRICT"))
    occurrence_id: Mapped[UUID] = mapped_column()
    attempt_id: Mapped[UUID] = mapped_column()
    preparation_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    preparation_digest: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(12))
    claim_id: Mapped[UUID | None] = mapped_column(unique=True, nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    decision_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    receipt_id: Mapped[UUID | None] = mapped_column(unique=True, nullable=True)
    settlement_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
