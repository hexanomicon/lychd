"""Codex DB services: `ConsentService` + `PreauthService` (wave4-design §3.4).

advanced-alchemy service-nests-repository over the `consent` + `codex_preauthorization`
tables. Both are exercised on the durable Postgres substrate ([LINUX] tests); the
DB-free floor runs through `InMemoryConsentLedger` (ledger.py). `PreauthService`
consumes a matching preauthorization ATOMICALLY (a single guarded `UPDATE … RETURNING`)
so two concurrent parks can never overdraw one `max_uses` budget.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
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

PREAUTH_DIGEST_PAYLOAD_KEY = "preauth_digest"
_RUNE_PREAUTH_OWNER = "codex:rune"

__all__ = [
    "PREAUTH_DIGEST_PAYLOAD_KEY",
    "ConsentService",
    "PreauthService",
    "preauth_authorization_digest",
    "row_to_view",
]


def _canonical_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC).isoformat()
    return value.astimezone(UTC).isoformat()


def preauth_authorization_digest(row: CodexPreauthorization) -> str:
    """Digest the stable fields that gave a preauthorization its authority."""
    document = {
        "slug": row.slug,
        "priority": row.priority,
        "klass": row.klass,
        "sigil_pattern": row.sigil_pattern,
        "tool_pattern": row.tool_pattern,
        "constraints": dict(row.constraints or {}),
        "expires_at": _canonical_datetime(row.expires_at),
        "max_uses": row.max_uses,
        "granted_by": row.granted_by,
    }
    canonical = json.dumps(document, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validated_preauth_slugs(runes: list[CodexPreauthRune]) -> set[str]:
    """Return the generation's unique slugs or reject it deterministically."""
    seen: set[str] = set()
    duplicates: set[str] = set()
    for rune in runes:
        if rune.slug in seen:
            duplicates.add(rune.slug)
        seen.add(rune.slug)
    if duplicates:
        joined = ", ".join(sorted(duplicates))
        msg = f"Duplicate preauthorization Rune slug(s): {joined}."
        raise ValueError(msg)
    return seen


def _require_rune_owned_preauthorizations(rows: Iterable[CodexPreauthorization]) -> None:
    """Refuse durable slug collisions outside the Rune-owned policy domain."""
    ownership_conflicts = sorted((row.slug, row.granted_by) for row in rows if row.granted_by != _RUNE_PREAUTH_OWNER)
    if ownership_conflicts:
        joined = ", ".join(f"{slug} (owned by {owner!r})" for slug, owner in ownership_conflicts)
        msg = f"Refusing non-Rune-owned preauthorization slug collision(s): {joined}."
        raise ValueError(msg)


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
        decided_at=row.decided_at,
        preauth_slug=row.preauth_slug,
    )


class PreauthService(SQLAlchemyAsyncRepositoryService[CodexPreauthorization]):
    """CRUD + atomic consume over standing `codex_preauthorization` rows."""

    class Repository(SQLAlchemyAsyncRepository[CodexPreauthorization]):
        model_type = CodexPreauthorization

    repository_type = Repository

    async def match_and_consume(
        self,
        *,
        sigil: Sigil,
        tool_name: str,
        payload: dict[str, Any],
        auto_commit: bool = True,
    ) -> CodexPreauthorization | None:
        """Find and atomically consume the first preauthorization admitting this call.

        Candidate filtering (fnmatch on sigil/tool, expiry, fail-closed constraints)
        is Python-side; the consume is a single guarded ``UPDATE … WHERE enabled AND
        source_present AND (max_uses IS NULL OR uses < max_uses) RETURNING`` so a race
        can neither consume removed authority nor overdraw.
        """
        from sqlalchemy import func, or_, update

        now = datetime.now(UTC)
        rows = sorted(
            await self.list(
                CodexPreauthorization.enabled.is_(True),
                CodexPreauthorization.source_present.is_(True),
            ),
            key=lambda row: (-row.priority, row.slug),
        )
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
                    CodexPreauthorization.source_present.is_(True),
                    or_(
                        CodexPreauthorization.expires_at.is_(None),
                        CodexPreauthorization.expires_at > func.now(),
                    ),
                    or_(
                        CodexPreauthorization.max_uses.is_(None),
                        CodexPreauthorization.uses < CodexPreauthorization.max_uses,
                    ),
                )
                .values(uses=CodexPreauthorization.uses + 1)
                .returning(CodexPreauthorization.id)
            )
            if auto_commit:
                await self.repository.session.commit()
            if result.scalar_one_or_none() is not None:
                return row
        return None

    async def sync_from_runes(self, runes: list[CodexPreauthRune]) -> int:
        """Reconcile the complete Rune-owned policy set in one transaction.

        Present rows retain both usage and operator ``enabled`` state. Rune absence
        changes only ``source_present``; a later reappearance can reactivate a policy
        that was operator-enabled without undoing an explicit operator disable.
        Duplicate source slugs and collisions with non-Rune-owned rows fail before
        the generation can mutate durable policy. Any failure rolls the whole
        generation back instead of publishing a mixed set.
        """
        from sqlalchemy import select, update

        session = self.repository.session
        slugs = _validated_preauth_slugs(runes)
        try:
            existing_by_slug: dict[str, CodexPreauthorization] = {}
            if slugs:
                result = await session.scalars(
                    select(CodexPreauthorization).where(CodexPreauthorization.slug.in_(slugs)).with_for_update()
                )
                existing_by_slug = {row.slug: row for row in result.all()}

            _require_rune_owned_preauthorizations(existing_by_slug.values())

            for rune in runes:
                row = existing_by_slug.get(rune.slug)
                values: dict[str, Any] = {
                    "priority": rune.priority,
                    "klass": rune.klass,
                    "sigil_pattern": rune.sigil_pattern,
                    "tool_pattern": rune.tool_pattern,
                    "constraints": dict(rune.constraints),
                    "expires_at": rune.expires_at,
                    "max_uses": rune.max_uses,
                    "source_present": True,
                    "granted_by": _RUNE_PREAUTH_OWNER,
                    "source_file": str(rune.source_file) if rune.source_file is not None else None,
                }
                if row is None:
                    row = CodexPreauthorization(
                        slug=rune.slug,
                        uses=0,
                        enabled=True,
                        **values,
                    )
                    session.add(row)
                    existing_by_slug[rune.slug] = row
                else:
                    for field, value in values.items():
                        setattr(row, field, value)

            absent = [CodexPreauthorization.granted_by == _RUNE_PREAUTH_OWNER]
            if slugs:
                absent.append(CodexPreauthorization.slug.not_in(slugs))
            await session.execute(
                update(CodexPreauthorization)
                .where(*absent)
                .values(source_present=False)
                .execution_options(synchronize_session=False)
            )
            await session.commit()
        except BaseException:
            await session.rollback()
            raise
        return len(runes)


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
        auto_commit: bool = True,
    ) -> Consent:
        """Persist a consent row: auto-granted when a preauth consumed it, else pending."""
        stored = {"args": censor(payload), "call_ids": list(call_ids)}
        granted = preauth is not None
        if preauth is not None:
            stored[PREAUTH_DIGEST_PAYLOAD_KEY] = preauth_authorization_digest(preauth)
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
            auto_commit=auto_commit,
        )

    async def _decide(self, consent_id: str, *, status: str, decided_by: str) -> ConsentView | None:
        from sqlalchemy import update

        row_id = UUID(consent_id)
        await self.repository.session.execute(
            update(Consent)
            .where(Consent.id == row_id, Consent.status == "pending")
            .values(status=status, decided_by=decided_by, decided_at=datetime.now(UTC))
            .returning(Consent.id)
            .execution_options(synchronize_session=False)
        )
        await self.repository.session.commit()
        row = await self.get_one_or_none(id=row_id)
        return row_to_view(row) if row is not None else None

    async def grant(self, consent_id: str, *, decided_by: str) -> ConsentView | None:
        """Idempotently mark a pending consent granted."""
        return await self._decide(consent_id, status="granted", decided_by=decided_by)

    async def deny(self, consent_id: str, *, decided_by: str) -> ConsentView | None:
        """Idempotently mark a pending consent denied."""
        return await self._decide(consent_id, status="denied", decided_by=decided_by)

    async def get_view(self, consent_id: str) -> ConsentView | None:
        """Return the read-model for one consent row, or None."""
        try:
            row_id = UUID(consent_id)
        except ValueError:
            return None
        row = await self.get_one_or_none(id=row_id)
        return row_to_view(row) if row is not None else None

    async def pending_count(self) -> int:
        """Return the number of consents still awaiting a verdict."""
        return await self.count(Consent.status == "pending")

    async def pending_for_run(self, run_id: str) -> ConsentView | None:
        """Return the run's still-pending consent, or None."""
        row = await self.get_one_or_none(run_id=UUID(run_id), status="pending")
        return row_to_view(row) if row is not None else None
