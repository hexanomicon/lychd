from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from lychd.db.models.run import Run


class Step(UUIDAuditBase):
    """Append-only run event ledger. Web/CLI observability reads these; never updated."""

    __tablename__ = "step"
    __table_args__ = (UniqueConstraint("run_id", "seq", name="uq_step_run_seq"),)

    run_id: Mapped[UUID] = mapped_column(ForeignKey("run.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column()  # per-run monotonic
    kind: Mapped[str] = mapped_column(String(20))
    #   RunEventKind values excluding token: status|node|fragment|consent|log|done (C4)
    node_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # {data, meta}; kit_name rides meta
    run: Mapped[Run] = relationship(back_populates="steps", lazy="noload")
