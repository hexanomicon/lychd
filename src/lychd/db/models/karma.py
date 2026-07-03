from __future__ import annotations

from typing import Any
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class Karma(UUIDAuditBase):
    """Memory row (CAG layer 4 / Reliquary v0). Embedding nullable so rows precede embeddings."""

    __tablename__ = "karma"

    kind: Mapped[str] = mapped_column(String(30), index=True)  # note|mistake|fact|preference
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Any | None] = mapped_column(Vector(), nullable=True)
    #   dimensionless vector; typed dim + HNSW index deferred to a future migration (§3.3)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    session_id: Mapped[UUID | None] = mapped_column(ForeignKey("session.id", ondelete="SET NULL"), nullable=True)
    run_id: Mapped[UUID | None] = mapped_column(ForeignKey("run.id", ondelete="SET NULL"), nullable=True)
