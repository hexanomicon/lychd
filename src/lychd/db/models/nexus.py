from __future__ import annotations

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column


class NexusSwapRequest(UUIDAuditBase):
    """The immutable first admission of one operator transition request id."""

    __tablename__ = "nexus_swap_request"

    request_id: Mapped[str] = mapped_column(String(128), unique=True)
    target: Mapped[str] = mapped_column(Text)


__all__ = ["NexusSwapRequest"]
