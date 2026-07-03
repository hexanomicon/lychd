"""Animation persistence service (soulstone DB projection).

TOML remains the source of truth for soulstones (Codex law); this row is the
bind-time projection so ``Run.capability_key`` and the Nexus board can join
against bound-soulstone history. Natural-key upsert is by ``name``.
"""

from __future__ import annotations

from typing import ClassVar

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from lychd.db.models import SoulstoneRecord


class SoulstoneRecordService(SQLAlchemyAsyncRepositoryService[SoulstoneRecord]):
    """CRUD + natural-key upsert service for ``SoulstoneRecord`` projections."""

    class Repository(SQLAlchemyAsyncRepository[SoulstoneRecord]):
        model_type = SoulstoneRecord

    repository_type = Repository
    match_fields: ClassVar[list[str] | str | None] = ["name"]
