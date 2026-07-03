"""Cortex persistence services (run substrate).

advanced-alchemy service-nests-repository pattern. Storage semantics live here;
run/transition state-machine semantics belong to the dispatch/orchestration layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from advanced_alchemy.exceptions import IntegrityError
from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy import func, select

from lychd.db.models import Karma, Run, Step

if TYPE_CHECKING:
    from uuid import UUID


class RunService(SQLAlchemyAsyncRepositoryService[Run]):
    """CRUD service for the durable ``Run`` substrate."""

    class Repository(SQLAlchemyAsyncRepository[Run]):
        model_type = Run

    repository_type = Repository


class StepService(SQLAlchemyAsyncRepositoryService[Step]):
    """Append-only ledger service for run ``Step`` events."""

    class Repository(SQLAlchemyAsyncRepository[Step]):
        model_type = Step

    repository_type = Repository

    _APPEND_MAX_RETRIES = 8

    async def append(
        self,
        *,
        run_id: UUID,
        kind: str,
        payload: dict[str, Any],
        node_key: str | None = None,
    ) -> Step:
        """Append one step with a per-run monotonic ``seq``.

        Contract: ``seq`` is unique and monotonic per run (gaps allowed). Under
        concurrent appends the ``uq_step_run_seq`` constraint is the arbiter; a
        collision recomputes ``max(seq)+1`` and retries.
        """
        session = self.repository.session
        last_error: IntegrityError | None = None
        for _ in range(self._APPEND_MAX_RETRIES):
            result = await session.execute(
                select(func.coalesce(func.max(Step.seq), -1) + 1).where(Step.run_id == run_id)
            )
            next_seq = int(result.scalar_one())
            try:
                return await self.create(
                    Step(run_id=run_id, seq=next_seq, kind=kind, payload=payload, node_key=node_key),
                    auto_commit=True,
                )
            except IntegrityError as exc:  # unique(run_id, seq) race — recompute and retry
                last_error = exc
                await session.rollback()
        msg = f"Could not allocate a monotonic step seq for run {run_id} after {self._APPEND_MAX_RETRIES} attempts."
        raise RuntimeError(msg) from last_error


class KarmaService(SQLAlchemyAsyncRepositoryService[Karma]):
    """CRUD service for memory (``Karma``) rows."""

    class Repository(SQLAlchemyAsyncRepository[Karma]):
        model_type = Karma

    repository_type = Repository
