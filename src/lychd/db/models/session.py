from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from lychd.db.models.run import Run


class Session(UUIDAuditBase):
    """One Bridge/API conversation. Survives restart (P2 'Phylactery first light')."""

    __tablename__ = "session"

    channel: Mapped[str] = mapped_column(String(20), default="bridge")  # bridge|api|cli
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sigil_name: Mapped[str] = mapped_column(String(100), index=True)
    message_history: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    #   pydantic-ai messages via to_jsonable_python(result.all_messages()); replayed with
    #   ModelMessagesTypeAdapter.validate_python(...) -> message_history= (Part 5.A).
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    last_run_id: Mapped[UUID | None] = mapped_column(nullable=True)
    runs: Mapped[list[Run]] = relationship(back_populates="session", lazy="noload")
