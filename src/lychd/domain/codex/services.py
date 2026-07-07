"""Codex DB services: `ConsentService` + `PreauthService` (wave4-design §3.4).

advanced-alchemy service-nests-repository over the `consent` + `codex_preauthorization`
tables. Both are exercised on the durable Postgres substrate ([LINUX] tests); the
DB-free floor runs through `InMemoryConsentLedger` (ledger.py). `PreauthService`
consumes a matching preauthorization ATOMICALLY (a single guarded `UPDATE … RETURNING`)
so two concurrent parks can never overdraw one `max_uses` budget.
"""

from __future__ import annotations

from datetime import UTC, datetime
from fnmatch import fnmatchcase
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from lychd.db.models import CodexPreauthorization, Consent
from lychd.domain.codex.schemas import ConsentView, censor, constraints_admit

if TYPE_CHECKING:
    from lychd.domain.codex.runes import CodexPreauthRune
    from lychd.domain.codex.sigil import Sigil

__all__ = ["ConsentService", "PreauthService", "row_to_view"]


def row_to_view(row: Consent) -> ConsentView:
    """Map a `Consent` ORM row to its read-model."""
    payload: dict[str, Any] = dict(row.payload) if row.payload else {}
    raw_args = payload.get("args", {})
    args: dict[str, Any] = cast("dict[str, Any]", raw_args) if isinstance(raw_args, dict) else {}
    return ConsentView(
        id=str(row.id),
        run_id=str(row.run_id),
        tool_name=row.tool_name,
        args=args,
        status=cast("Any", row.status),
        decided_by=row.decided_by,
        preauth_slug=row.preauth_slug,
    )


class PreauthService(SQLAlchemyAsyncRepositoryService[CodexPreauthorization]):
    """CRUD + atomic consume over standing `codex_preauthorization` rows."""

    class Repository(SQLAlchemyAsyncRepository[CodexPreauthorization]):
        model_type = CodexPreauthorization

    repository_type = Repository

    async def match_and_consume(
        self, *, sigil: Sigil, tool_name: str, payload: dict[str, Any]
    ) -> CodexPreauthorization | None:
        """Find and atomically consume the first preauthorization admitting this call.

        Candidate filtering (fnmatch on sigil/tool, expiry, fail-closed constraints)
        is Python-side; the consume is a single guarded ``UPDATE … WHERE enabled AND
        (max_uses IS NULL OR uses < max_uses) RETURNING`` so a race can never overdraw.
        """
        from sqlalchemy import or_, update

        now = datetime.now(UTC)
        rows = await self.list(CodexPreauthorization.enabled.is_(True))
        for row in rows:
            if not fnmatchcase(sigil.name, row.sigil_pattern):
                continue
            if not fnmatchcase(tool_name, row.tool_pattern):
                continue
            if row.expires_at is not None and row.expires_at <= now:
                continue
            if not constraints_admit(dict(row.constraints or {}), payload):
                continue
            result = await self.repository.session.execute(
                update(CodexPreauthorization)
                .where(
                    CodexPreauthorization.id == row.id,
                    CodexPreauthorization.enabled.is_(True),
                    or_(
                        CodexPreauthorization.max_uses.is_(None),
                        CodexPreauthorization.uses < CodexPreauthorization.max_uses,
                    ),
                )
                .values(uses=CodexPreauthorization.uses + 1)
                .returning(CodexPreauthorization.id)
            )
            await self.repository.session.commit()
            if result.scalar_one_or_none() is not None:
                return row
        return None

    async def sync_from_runes(self, runes: list[CodexPreauthRune]) -> int:
        """Upsert preauthorizations from loaded runes (never reset `uses`).

        Match by slug: an existing row keeps its `uses`/`enabled` and refreshes its
        policy fields; a new slug is inserted. `granted_by` is always ``codex:rune``.
        """
        synced = 0
        for rune in runes:
            existing = await self.get_one_or_none(slug=rune.slug)
            values: dict[str, Any] = {
                "klass": rune.klass,
                "sigil_pattern": rune.sigil_pattern,
                "tool_pattern": rune.tool_pattern,
                "constraints": dict(rune.constraints),
                "expires_at": rune.expires_at,
                "max_uses": rune.max_uses,
                "granted_by": "codex:rune",
                "source_file": str(rune.source_file) if rune.source_file is not None else None,
            }
            if existing is None:
                await self.create(CodexPreauthorization(slug=rune.slug, **values), auto_commit=True)
            else:
                await self.update(values, item_id=existing.id, auto_commit=True)  # never touches `uses`
            synced += 1
        return synced


class ConsentService(SQLAlchemyAsyncRepositoryService[Consent]):
    """CRUD + verdict transitions over `consent` rows (preauth-first request)."""

    class Repository(SQLAlchemyAsyncRepository[Consent]):
        model_type = Consent

    repository_type = Repository

    async def request(
        self,
        *,
        run_id: str,
        tool_name: str,
        tool_call_id: str,
        call_ids: tuple[str, ...],
        payload: dict[str, Any],
        preauth: CodexPreauthorization | None,
    ) -> Consent:
        """Persist a consent row: auto-granted when a preauth consumed it, else pending."""
        stored = {"args": censor(payload), "call_ids": list(call_ids)}
        granted = preauth is not None
        return await self.create(
            Consent(
                run_id=UUID(run_id),
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                payload=stored,
                status="granted" if granted else "pending",
                decided_by="codex:preauth" if granted else None,
                decided_at=datetime.now(UTC) if granted else None,
                preauth_slug=preauth.slug if preauth is not None else None,
                expires_at=preauth.expires_at if preauth is not None else None,
            ),
            auto_commit=True,
        )

    async def _decide(self, consent_id: str, *, status: str, decided_by: str) -> ConsentView | None:
        row = await self.get_one_or_none(id=UUID(consent_id))
        if row is None:
            return None
        if row.status == "pending":  # idempotent: a settled verdict is never re-decided
            await self.update(
                {"status": status, "decided_by": decided_by, "decided_at": datetime.now(UTC)},
                item_id=row.id,
                auto_commit=True,
            )
            row = await self.get_one_or_none(id=UUID(consent_id))
        return row_to_view(row) if row is not None else None

    async def grant(self, consent_id: str, *, decided_by: str) -> ConsentView | None:
        """Idempotently mark a pending consent granted."""
        return await self._decide(consent_id, status="granted", decided_by=decided_by)

    async def deny(self, consent_id: str, *, decided_by: str) -> ConsentView | None:
        """Idempotently mark a pending consent denied."""
        return await self._decide(consent_id, status="denied", decided_by=decided_by)

    async def get_view(self, consent_id: str) -> ConsentView | None:
        """Return the read-model for one consent row, or None."""
        row = await self.get_one_or_none(id=UUID(consent_id))
        return row_to_view(row) if row is not None else None

    async def pending_count(self) -> int:
        """Return the number of consents still awaiting a verdict."""
        return await self.count(Consent.status == "pending")

    async def pending_for_run(self, run_id: str) -> ConsentView | None:
        """Return the run's still-pending consent, or None."""
        row = await self.get_one_or_none(run_id=UUID(run_id), status="pending")
        return row_to_view(row) if row is not None else None
