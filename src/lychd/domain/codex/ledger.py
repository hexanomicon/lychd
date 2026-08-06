"""`ConsentLedger` — the consent verdict store the graph parks into (wave4-design §3.5).

One protocol, two implementations: `InMemoryConsentLedger` (loop-confined, DB-free —
the Mac dev floor + the offline park/resume suite) and `CodexConsentLedger` (over
`ConsentService`/`PreauthService`, the durable Postgres substrate). Both evaluate
preauthorizations with the SAME pure `constraints_admit`/`censor` functions, so the
preauth-hit path is identical in-memory and on Postgres.

The graph reads consent ONLY through this port's string ids (S8): `park` returns a
`ConsentDecision`, `verdict` returns True/False/None(pending). `domain/cortex` never
imports codex — it sees the ledger as an opaque port.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from fnmatch import fnmatchcase
from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable
from uuid import UUID, uuid4

from lychd.domain.codex.schemas import ConsentDecision, ConsentStatusValue, ConsentView, censor, constraints_admit

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from lychd.domain.codex.runes import CodexPreauthRune
    from lychd.domain.codex.sigil import Sigil

__all__ = ["CodexConsentLedger", "ConsentLedger", "InMemoryConsentLedger"]


@runtime_checkable
class ConsentLedger(Protocol):
    """The consent surface consumed by the graph, the web, the CLI, and reconcile."""

    async def park(
        self,
        *,
        run_id: str,
        tool_name: str,
        tool_call_id: str,
        call_ids: tuple[str, ...],
        args: dict[str, Any],
        sigil: Sigil,
    ) -> ConsentDecision:
        """Record a parked consent (preauth-first: auto-granted or pending)."""
        ...

    async def verdict(self, consent_id: str) -> bool | None:
        """Return True (granted), False (denied/expired), or None (still pending)."""
        ...

    async def get(self, consent_id: str) -> ConsentView | None:
        """Return the read-model for one consent, or None."""
        ...

    async def decide(self, consent_id: str, *, approved: bool, decided_by: str) -> ConsentView | None:
        """Idempotently settle a pending consent (grant/deny) and return the view."""
        ...

    async def pending_count(self) -> int:
        """Return the number of consents awaiting a verdict (feeds the topbar sigil)."""
        ...

    async def pending_views_for_runs(self, run_ids: frozenset[str]) -> list[ConsentView]:
        """Return pending consent cards owned by the named Runs."""
        ...

    async def latest_for_run(self, run_id: str) -> ConsentView | None:
        """Return the newest consent row for the narrow pre-park crash-window probe."""
        ...

    async def cancel_pending_for_run(self, run_id: str, *, decided_by: str = "cortex:run-cancelled") -> int:
        """Settle every pending consent owned by one terminalizing Run."""
        ...


def _verdict_of(status: ConsentStatusValue) -> bool | None:
    """Map a consent status to the graph's tri-state verdict."""
    if status == "granted":
        return True
    if status in {"denied", "expired", "cancelled"}:
        return False
    return None


# ---------------------------------------------------------------------------
# In-memory (Mac dev floor + offline suite)
# ---------------------------------------------------------------------------


@dataclass
class _ConsentRow:
    id: str
    run_id: str
    tool_name: str
    args: dict[str, Any]
    call_ids: tuple[str, ...]
    status: ConsentStatusValue = "pending"
    decided_by: str | None = None
    decided_at: datetime | None = None
    preauth_slug: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class InMemoryConsentLedger:
    """Loop-confined consent ledger; pairs with `InMemoryRunLedger` (process-local)."""

    def __init__(self, *, preauths: list[CodexPreauthRune] | None = None) -> None:
        """Create an empty ledger with an optional in-memory preauthorization source."""
        self._rows: dict[str, _ConsentRow] = {}
        self._preauths: list[CodexPreauthRune] = sorted(
            preauths or [],
            key=lambda rune: (-rune.priority, rune.slug),
        )
        self._uses: dict[str, int] = {}

    def _match_preauth(self, *, sigil: Sigil, tool_name: str, args: dict[str, Any]) -> CodexPreauthRune | None:
        now = datetime.now(UTC)
        for rune in self._preauths:
            if not fnmatchcase(sigil.name, rune.sigil_pattern):
                continue
            if not fnmatchcase(tool_name, rune.tool_pattern):
                continue
            if rune.expires_at is not None and rune.expires_at <= now:
                continue
            if rune.max_uses is not None and self._uses.get(rune.slug, 0) >= rune.max_uses:
                continue
            if not constraints_admit(dict(rune.constraints), args):
                continue
            self._uses[rune.slug] = self._uses.get(rune.slug, 0) + 1
            return rune
        return None

    async def park(
        self,
        *,
        run_id: str,
        tool_name: str,
        tool_call_id: str,
        call_ids: tuple[str, ...],
        args: dict[str, Any],
        sigil: Sigil,
    ) -> ConsentDecision:
        """Record a parked consent — auto-granted by a preauth, or pending."""
        _ = tool_call_id  # audited into the DB row; the graph state carries call_ids authoritatively
        consent_id = str(uuid4())
        preauth = self._match_preauth(sigil=sigil, tool_name=tool_name, args=args)
        row = _ConsentRow(
            id=consent_id,
            run_id=run_id,
            tool_name=tool_name,
            args=censor(args),
            call_ids=call_ids,
            status="granted" if preauth is not None else "pending",
            decided_by="codex:preauth" if preauth is not None else None,
            decided_at=datetime.now(UTC) if preauth is not None else None,
            preauth_slug=preauth.slug if preauth is not None else None,
        )
        self._rows[consent_id] = row
        status: Any = row.status
        return ConsentDecision(status=status, consent_id=consent_id, preauth_slug=row.preauth_slug)

    async def verdict(self, consent_id: str) -> bool | None:
        """Tri-state verdict for a consent (unknown → None)."""
        row = self._rows.get(consent_id)
        if row is None or (row.status != "pending" and (not row.decided_by or row.decided_at is None)):
            return None
        return _verdict_of(row.status)

    def _view(self, row: _ConsentRow) -> ConsentView:
        return ConsentView(
            id=row.id,
            run_id=row.run_id,
            tool_name=row.tool_name,
            args=row.args,
            status=row.status,
            decided_by=row.decided_by,
            decided_at=row.decided_at,
            preauth_slug=row.preauth_slug,
        )

    async def get(self, consent_id: str) -> ConsentView | None:
        """Read-model for one consent, or None."""
        row = self._rows.get(consent_id)
        return self._view(row) if row is not None else None

    async def decide(self, consent_id: str, *, approved: bool, decided_by: str) -> ConsentView | None:
        """Idempotently settle a pending consent and return its view."""
        row = self._rows.get(consent_id)
        if row is None:
            return None
        if row.status == "pending":
            row.status = "granted" if approved else "denied"
            row.decided_by = decided_by
            row.decided_at = datetime.now(UTC)
        return self._view(row)

    async def pending_count(self) -> int:
        """Return the number of pending consents."""
        return sum(1 for row in self._rows.values() if row.status == "pending")

    async def pending_views_for_runs(self, run_ids: frozenset[str]) -> list[ConsentView]:
        """Return pending consent cards for named Runs, oldest-first."""
        rows = sorted(
            (row for row in self._rows.values() if row.status == "pending" and row.run_id in run_ids),
            key=lambda row: (row.created_at, row.id),
        )
        return [self._view(row) for row in rows]

    async def latest_for_run(self, run_id: str) -> ConsentView | None:
        """Return the newest consent row for a run, or None."""
        rows = (r for r in self._rows.values() if r.run_id == run_id)
        row = max(rows, key=lambda item: (item.created_at, item.id), default=None)
        return self._view(row) if row is not None else None

    async def cancel_pending_for_run(self, run_id: str, *, decided_by: str = "cortex:run-cancelled") -> int:
        """Settle pending cards when their owning Run terminalizes."""
        settled = 0
        for row in self._rows.values():
            if row.run_id == run_id and row.status == "pending":
                row.status = "cancelled"
                row.decided_by = decided_by
                row.decided_at = datetime.now(UTC)
                settled += 1
        return settled


# ---------------------------------------------------------------------------
# Durable (Postgres substrate; [LINUX] tests)
# ---------------------------------------------------------------------------


class CodexConsentLedger:
    """Durable consent ledger over `ConsentService`/`PreauthService`.

    Runtime-validation seam (PG, Linux): requires the `consent`/`codex_preauthorization`
    tables (migration 0001) + a live engine. The DB-free floor is `InMemoryConsentLedger`.
    """

    def __init__(self, *, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Bind the ledger to a session factory (typically `get_session_factory()`)."""
        self._session_factory = session_factory

    async def park(
        self,
        *,
        run_id: str,
        tool_name: str,
        tool_call_id: str,
        call_ids: tuple[str, ...],
        args: dict[str, Any],
        sigil: Sigil,
    ) -> ConsentDecision:
        """Atomically consume a matching preauth and persist its consent row."""
        from lychd.domain.codex.services import ConsentService, PreauthService

        async with self._session_factory() as session:
            preauth = await PreauthService(session=session).match_and_consume(
                sigil=sigil,
                tool_name=tool_name,
                payload=args,
                auto_commit=False,
            )
            row = await ConsentService(session=session).request(
                run_id=run_id,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                call_ids=call_ids,
                payload=args,
                preauth=preauth,
                auto_commit=False,
            )
            await session.commit()
            await session.refresh(row)
            status: Any = row.status
            return ConsentDecision(status=status, consent_id=str(row.id), preauth_slug=row.preauth_slug)

    async def verdict(self, consent_id: str) -> bool | None:
        """Return a verdict, revalidating any standing policy behind a grant."""
        from sqlalchemy import func, select

        from lychd.db.models import CodexPreauthorization, Consent
        from lychd.domain.codex.services import PREAUTH_DIGEST_PAYLOAD_KEY, preauth_authorization_digest

        async with self._session_factory() as session:
            row = await session.get(Consent, UUID(consent_id))
            if row is None:
                return None
            if row.status != "pending" and (not row.decided_by or row.decided_at is None):
                return None
            verdict = _verdict_of(cast("ConsentStatusValue", row.status))
            if verdict is not True or row.decided_by != "codex:preauth":
                return verdict

            payload = dict(row.payload or {})
            stored_digest = payload.get(PREAUTH_DIGEST_PAYLOAD_KEY)
            authorized = False
            if row.preauth_slug and isinstance(stored_digest, str):
                preauth = await session.scalar(
                    select(CodexPreauthorization).where(CodexPreauthorization.slug == row.preauth_slug)
                )
                if preauth is not None and preauth.enabled and preauth.source_present:
                    database_now = await session.scalar(select(func.now()))
                    authorized = (
                        database_now is not None
                        and (preauth.expires_at is None or preauth.expires_at > database_now)
                        and stored_digest == preauth_authorization_digest(preauth)
                    )
            return authorized

    async def get(self, consent_id: str) -> ConsentView | None:
        """Read-model for one consent, or None."""
        from lychd.domain.codex.services import ConsentService

        async with self._session_factory() as session:
            return await ConsentService(session=session).get_view(consent_id)

    async def decide(self, consent_id: str, *, approved: bool, decided_by: str) -> ConsentView | None:
        """Idempotently settle a pending consent."""
        from lychd.domain.codex.services import ConsentService

        async with self._session_factory() as session:
            svc = ConsentService(session=session)
            if approved:
                return await svc.grant(consent_id, decided_by=decided_by)
            return await svc.deny(consent_id, decided_by=decided_by)

    async def pending_count(self) -> int:
        """Return the number of pending consents."""
        from lychd.domain.codex.services import ConsentService

        async with self._session_factory() as session:
            return await ConsentService(session=session).pending_count()

    async def pending_views_for_runs(self, run_ids: frozenset[str]) -> list[ConsentView]:
        """Return pending consent cards for named Runs, oldest-first."""
        from lychd.db.models import Consent
        from lychd.domain.codex.services import ConsentService, row_to_view

        run_uuids: list[UUID] = []
        for run_id in run_ids:
            try:
                run_uuids.append(UUID(run_id))
            except ValueError:
                continue
        if not run_uuids:
            return []
        async with self._session_factory() as session:
            svc = ConsentService(session=session)
            rows = await svc.list(
                Consent.status == "pending",
                Consent.run_id.in_(run_uuids),
                order_by=[(Consent.created_at, False), (Consent.id, False)],
            )
            return [row_to_view(row) for row in rows]

    async def latest_for_run(self, run_id: str) -> ConsentView | None:
        """Return the newest consent row for a run, or None."""
        from sqlalchemy import select

        from lychd.db.models import Consent
        from lychd.domain.codex.services import row_to_view

        async with self._session_factory() as session:
            row = await session.scalar(
                select(Consent)
                .where(Consent.run_id == UUID(run_id))
                .order_by(Consent.created_at.desc(), Consent.id.desc())
                .limit(1)
            )
            return row_to_view(row) if row is not None else None

    async def cancel_pending_for_run(self, run_id: str, *, decided_by: str = "cortex:run-cancelled") -> int:
        """Atomically settle pending cards when their owning Run terminalizes."""
        from sqlalchemy import update

        from lychd.db.models import Consent

        async with self._session_factory() as session:
            result = await session.execute(
                update(Consent)
                .where(Consent.run_id == UUID(run_id), Consent.status == "pending")
                .values(
                    status="cancelled",
                    decided_by=decided_by,
                    decided_at=datetime.now(UTC),
                )
                .returning(Consent.id)
            )
            settled = len(result.scalars().all())
            await session.commit()
            return settled
