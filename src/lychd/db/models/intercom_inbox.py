"""Private paired receiver custody, independent of outbound operations and Runs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from advanced_alchemy.base import UUIDBase
from sqlalchemy import CheckConstraint, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class IntercomInboxTask(UUIDBase):
    """One immutable semantic intake with its receiver-owned first terminal decision."""

    __tablename__ = "peer_inbox_task"
    __table_args__ = (
        UniqueConstraint("receiver", "peer", "local_id", name="uq_peer_inbox_task_local"),
        UniqueConstraint("receiver", "peer", "message_id", name="uq_peer_inbox_task_message"),
        CheckConstraint("octet_length(request_text) BETWEEN 1 AND 8192", name="text_bound"),
        CheckConstraint("expires_at > admitted_at", name="lifetime"),
        CheckConstraint("state IN ('submitted','working','completed','rejected','canceled','expired')", name="state"),
        CheckConstraint(
            "(state = 'completed' AND result IS NOT NULL AND octet_length(result) BETWEEN 1 AND 4096) "
            "OR (state <> 'completed' AND result IS NULL)",
            name="result_bound",
        ),
    )

    receiver: Mapped[UUID]
    peer: Mapped[UUID]
    local_id: Mapped[str] = mapped_column(String(128))
    message_id: Mapped[str] = mapped_column(String(128))
    body_digest: Mapped[str] = mapped_column(String(64))
    policy: Mapped[str] = mapped_column(String(64))
    task_schema: Mapped[str] = mapped_column(String(300))
    request_text: Mapped[str] = mapped_column(Text)
    admitted_at: Mapped[datetime]
    expires_at: Mapped[datetime]
    state: Mapped[str] = mapped_column(String(16))
    result: Mapped[str | None] = mapped_column(Text)


class IntercomInboxAttempt(UUIDBase):
    """Spent authenticated physical wrappers, retained through signature expiry."""

    __tablename__ = "peer_inbox_attempt"
    __table_args__ = (
        UniqueConstraint("receiver", "peer", "attempt", name="uq_peer_inbox_attempt_id"),
        UniqueConstraint("receiver", "peer", "nonce", name="uq_peer_inbox_attempt_nonce"),
    )

    receiver: Mapped[UUID]
    peer: Mapped[UUID]
    attempt: Mapped[str] = mapped_column(String(128))
    nonce: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime]
