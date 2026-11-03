"""Private explicitly approved vocabulary, independent of attempt/correction custody."""

from __future__ import annotations

from datetime import datetime

from advanced_alchemy.base import UUIDBase
from advanced_alchemy.types import DateTimeUTC
from sqlalchemy import CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class BridgeDictationLexiconRule(UUIDBase):
    __tablename__ = "bridge_dictation_lexicon_rule"
    __table_args__ = (
        UniqueConstraint("owner", "language", "heard", name="uq_bridge_dictation_lexicon_owner_language_heard"),
        CheckConstraint("char_length(owner) BETWEEN 1 AND 256", name="owner_bound"),
        CheckConstraint("char_length(language) BETWEEN 2 AND 35 AND language = lower(language)", name="language_bound"),
        CheckConstraint("char_length(heard) BETWEEN 1 AND 128", name="heard_bound"),
        CheckConstraint("char_length(replacement) BETWEEN 1 AND 128", name="replacement_bound"),
        CheckConstraint(
            "expires_at > created_at AND expires_at <= created_at + INTERVAL '30 days'",
            name="retention_bound",
        ),
    )

    owner: Mapped[str] = mapped_column(String(256))
    language: Mapped[str] = mapped_column(String(35))
    heard: Mapped[str] = mapped_column(String(128))
    replacement: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTimeUTC(timezone=True))
