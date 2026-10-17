"""Durable immutable investigation custody and its one unresolved-case slot."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import CheckConstraint, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class CreationCase(UUIDAuditBase):
    __tablename__ = "creation_case"
    __table_args__ = (
        CheckConstraint("slot IS NULL OR slot = 1", name="one_slot"),
        CheckConstraint("octet_length(request_bytes) <= 16384", name="request_bound"),
        CheckConstraint("candidate_bytes IS NULL OR octet_length(candidate_bytes) <= 1536", name="candidate_bound"),
        CheckConstraint("verdict_bytes IS NULL OR octet_length(verdict_bytes) <= 1536", name="verdict_bound"),
    )
    request_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    request_digest: Mapped[str] = mapped_column(String(64))
    profile_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    profile_digest: Mapped[str] = mapped_column(String(64))
    deadline: Mapped[datetime]
    slot: Mapped[int | None] = mapped_column(unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="reserved")
    cancelled: Mapped[bool] = mapped_column(default=False)
    current_admission_id: Mapped[UUID]
    candidate_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    candidate_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verdict_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(64), nullable=True)


class CreationAdmission(UUIDAuditBase):
    __tablename__ = "creation_admission"
    case_id: Mapped[UUID] = mapped_column(ForeignKey("creation_case.id", ondelete="RESTRICT"))
    binding_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    run_id: Mapped[UUID | None] = mapped_column(unique=True, nullable=True)


class CreationAttempt(UUIDAuditBase):
    __tablename__ = "creation_attempt"
    __table_args__ = (
        UniqueConstraint("case_id", "role", name="uq_creation_attempt_case_role"),
        CheckConstraint("role IN ('constructor', 'verifier')", name="role"),
        CheckConstraint("octet_length(input_bytes) <= 12288", name="input_bound"),
        CheckConstraint("output_bytes IS NULL OR octet_length(output_bytes) <= 1536", name="output_bound"),
        CheckConstraint("NOT adopted OR response_bytes IS NOT NULL", name="adopted_response"),
        CheckConstraint("response_bytes IS NULL OR octet_length(response_bytes) <= 65536", name="response_bound"),
    )
    case_id: Mapped[UUID] = mapped_column(ForeignKey("creation_case.id", ondelete="RESTRICT"))
    admission_id: Mapped[UUID] = mapped_column(ForeignKey("creation_admission.id", ondelete="RESTRICT"))
    role: Mapped[str] = mapped_column(String(16))
    input_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    input_digest: Mapped[str] = mapped_column(String(64))
    claimed_at: Mapped[datetime]
    response_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    response_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    usage_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    output_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    validation_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    adopted: Mapped[bool] = mapped_column(default=False)
    error: Mapped[str | None] = mapped_column(String(64), nullable=True)


class CreationFeedback(UUIDAuditBase):
    """Append-only external assessment and owner disposition custody for Creation."""

    __tablename__ = "creation_feedback"
    __table_args__ = (
        UniqueConstraint("case_id", "sequence", name="uq_creation_feedback_case_sequence"),
        CheckConstraint("sequence > 0", name="positive_sequence"),
        CheckConstraint("kind IN ('assessment', 'decision')", name="kind"),
        CheckConstraint("octet_length(body_bytes) <= 16384", name="body_bound"),
        CheckConstraint("report_bytes IS NULL OR octet_length(report_bytes) <= 8192", name="report_bound"),
        CheckConstraint("octet_length(attribution_bytes) <= 16384", name="attribution_bound"),
        CheckConstraint(
            "(kind = 'assessment' AND assessment_id IS NULL AND report_bytes IS NOT NULL AND report_digest IS NOT NULL) OR (kind = 'decision' AND assessment_id IS NOT NULL AND report_bytes IS NULL AND report_digest IS NULL)",
            name="custody_shape",
        ),
    )
    case_id: Mapped[UUID] = mapped_column(ForeignKey("creation_case.id", ondelete="RESTRICT"))
    sequence: Mapped[int]
    kind: Mapped[str] = mapped_column(String(16))
    assessment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("creation_feedback.id", ondelete="RESTRICT"), nullable=True
    )
    body_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    body_digest: Mapped[str] = mapped_column(String(64))
    report_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    report_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attribution_bytes: Mapped[bytes] = mapped_column(LargeBinary)
