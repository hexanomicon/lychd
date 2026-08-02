"""PostgreSQL admission ledger for operator-requested Nexus transitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from lychd.domain.web.swap_requests import SwapRequestClaim

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

__all__ = ["DbSwapRequestLedger"]


class DbSwapRequestLedger:
    """Reserve request identities atomically across processes and restarts."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Bind the ledger to the process database session factory."""
        self._session_factory = session_factory

    async def claim(self, *, request_id: str, target: str) -> SwapRequestClaim:
        """Insert once by request id and return the immutable first target."""
        from lychd.db.models import NexusSwapRequest

        async with self._session_factory() as session, session.begin():
            row_id = await session.scalar(
                insert(NexusSwapRequest)
                .values(request_id=request_id, target=target)
                .on_conflict_do_nothing(index_elements=[NexusSwapRequest.request_id])
                .returning(NexusSwapRequest.id)
            )
            row = await session.scalar(
                select(NexusSwapRequest).where(NexusSwapRequest.request_id == request_id).with_for_update()
            )
            if row is None:  # pragma: no cover - insert/read share one transaction
                message = "Nexus request admission completed without a readable row."
                raise RuntimeError(message)
            return SwapRequestClaim(
                request_id=row.request_id,
                target=row.target,
                created=row_id is not None,
            )
