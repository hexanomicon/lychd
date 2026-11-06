"""Append-only bootstrap naming revisions scoped to the authenticated operator."""

from __future__ import annotations

from advanced_alchemy.base import UUIDBase
from sqlalchemy import BigInteger, CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class NamingRecord(UUIDBase):
    __tablename__ = "naming_record"
    __table_args__ = (
        UniqueConstraint("owner", "revision", name="uq_naming_record_owner_revision"),
        CheckConstraint("char_length(owner) BETWEEN 1 AND 256", name="owner_bound"),
        CheckConstraint("revision >= 1", name="revision_bound"),
        CheckConstraint("char_length(magus_name) BETWEEN 1 AND 96", name="magus_name_bound"),
        CheckConstraint("char_length(primus_name) BETWEEN 1 AND 96", name="primus_name_bound"),
        CheckConstraint(
            "magus_origin IN ('manual', 'dictionary', 'assisted', 'self_chosen')", name="magus_origin_bound"
        ),
        CheckConstraint(
            "primus_origin IN ('manual', 'dictionary', 'assisted', 'self_chosen')", name="primus_origin_bound"
        ),
    )

    owner: Mapped[str] = mapped_column(String(256))
    revision: Mapped[int] = mapped_column(BigInteger)
    magus_name: Mapped[str] = mapped_column(String(96))
    primus_name: Mapped[str] = mapped_column(String(96))
    magus_origin: Mapped[str] = mapped_column(String(16))
    primus_origin: Mapped[str] = mapped_column(String(16))
