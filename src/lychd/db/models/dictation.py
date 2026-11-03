"""Private Bridge dictation custody, separate from public Archive and sessions."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from advanced_alchemy.base import UUIDBase
from advanced_alchemy.types import DateTimeUTC
from sqlalchemy import CheckConstraint, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class BridgeDictationAttempt(UUIDBase):
    """One owned attempt or content-free replay fence; raw payload loads are deferred."""

    __tablename__ = "bridge_dictation_attempt"
    __table_args__ = (
        UniqueConstraint("owner", "attempt_id", name="uq_bridge_dictation_attempt_owner_id"),
        CheckConstraint("char_length(owner) BETWEEN 1 AND 256", name="owner_bound"),
        CheckConstraint(
            "expires_at > created_at AND expires_at <= created_at + INTERVAL '30 days'",
            name="retention_bound",
        ),
        CheckConstraint(
            "audio_expires_at >= created_at AND audio_expires_at <= created_at + INTERVAL '1 hour'",
            name="raw_retention_bound",
        ),
        CheckConstraint(
            "content_json IS NULL OR octet_length(content_json) BETWEEN 1 AND 131072",
            name="content_bound",
        ),
        CheckConstraint(
            "(raw_audio IS NULL AND raw_size = 0) OR "
            "(raw_audio IS NOT NULL AND raw_size BETWEEN 46 AND 1048576 AND octet_length(raw_audio) = raw_size)",
            name="raw_bound",
        ),
        CheckConstraint("content_json IS NOT NULL OR (raw_audio IS NULL AND raw_size = 0)", name="erasure_complete"),
    )

    owner: Mapped[str] = mapped_column(String(256))
    attempt_id: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTimeUTC(timezone=True))
    audio_expires_at: Mapped[datetime] = mapped_column(DateTimeUTC(timezone=True))
    tombstone_until: Mapped[datetime] = mapped_column(DateTimeUTC(timezone=True))
    content_json: Mapped[str | None] = mapped_column(Text)
    raw_audio: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)
    raw_size: Mapped[int] = mapped_column(Integer)
