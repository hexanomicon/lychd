"""Durable Atlas aggregate and immutable mutation receipts."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase, UUIDBase
from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class AtlasProjectRecord(UUIDAuditBase):
    """One owner-scoped, validated undertaking document."""

    __tablename__ = "atlas_project"
    __table_args__ = (CheckConstraint("version >= 1", name="positive_version"),)

    sigil_name: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[int] = mapped_column()
    document: Mapped[dict[str, Any]] = mapped_column(JSONB)
    creation_digest: Mapped[str] = mapped_column(String(64))


class AtlasRequestRecord(UUIDBase):
    """One request UUID bound to exactly one Project and validated payload."""

    __tablename__ = "atlas_request"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("atlas_project.id", ondelete="RESTRICT"), index=True)
    payload_digest: Mapped[str] = mapped_column(String(64))
