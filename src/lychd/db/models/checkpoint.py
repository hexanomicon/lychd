"""The durable Pydantic Graph checkpoint for one run."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class RunCheckpoint(UUIDAuditBase):
    """One replaceable JSONB graph-snapshot document, owned by exactly one run."""

    __tablename__ = "run_checkpoint"

    run_id: Mapped[UUID] = mapped_column(ForeignKey("run.id", ondelete="CASCADE"), unique=True)
    snapshots: Mapped[list[Any]] = mapped_column(JSONB, default=list)
