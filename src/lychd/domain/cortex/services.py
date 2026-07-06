"""Cortex persistence services (run substrate).

advanced-alchemy service-nests-repository pattern. Storage semantics live here;
run/transition state-machine semantics belong to the dispatch/orchestration layer.
"""

from __future__ import annotations

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from lychd.db.models import Karma, Run, Step


class RunService(SQLAlchemyAsyncRepositoryService[Run]):
    """CRUD service for the durable ``Run`` substrate."""

    class Repository(SQLAlchemyAsyncRepository[Run]):
        model_type = Run

    repository_type = Repository


class StepService(SQLAlchemyAsyncRepositoryService[Step]):
    """Append-only ledger service for run ``Step`` events.

    Seq allocation lives in the caller (`DbRunLedger.append_event` writes the channel
    event's `seq` VERBATIM; ordering is guaranteed by the bus's per-run writer chain,
    H5). This service is a plain CRUD surface — there is deliberately NO insert-time
    `max(seq)+1` allocator here (that old contract was dropped; mixing it with verbatim
    seqs on the same table would corrupt Step.seq == emit order, R6).
    """

    class Repository(SQLAlchemyAsyncRepository[Step]):
        model_type = Step

    repository_type = Repository


class KarmaService(SQLAlchemyAsyncRepositoryService[Karma]):
    """CRUD service for memory (``Karma``) rows."""

    class Repository(SQLAlchemyAsyncRepository[Karma]):
        model_type = Karma

    repository_type = Repository
