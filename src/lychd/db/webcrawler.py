"""PostgreSQL Webcrawler custody; no transaction spans an acquisition effect.

All mutations lock permanent host budget, binding budget, attempt, Run, exact
RunDelivery and Consent in that order. Preparation and native Consent commit
atomically. Only an acknowledged fresh claim can produce an execution permit.
"""

from __future__ import annotations

import contextlib
import json
from datetime import datetime
from hashlib import sha256
from typing import cast
from uuid import UUID, uuid4

from pydantic import TypeAdapter
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lychd.db.models.consent import Consent
from lychd.db.models.run import Run
from lychd.db.models.run_delivery import RunDelivery
from lychd.db.models.webcrawler import WebcrawlerAttempt, WebcrawlerBudget
from lychd.domain.codex.schemas import NativeConsentBinding, decode_native_binding
from lychd.domain.codex.services import ConsentService
from lychd.domain.scout.attempts import (
    AttemptStatus,
    NewScoutClaim,
    ScoutAllowance,
    ScoutAnyPreparation,
    ScoutAttemptSnapshot,
    ScoutBudgetLimits,
    ScoutCommitUnknownError,
    ScoutConflictError,
    ScoutFeedPreparation,
    ScoutRunBinding,
    ScoutSettlement,
    ScoutSettlementVerifier,
    ScoutStoreAuthorizer,
    ScoutStoreError,
    decode_scout_preparation,
    document_digest,
)
from lychd.domain.scout.authority import ScoutAction, ScoutAuthorizationDecision
from lychd.domain.web.consent_reviews import NativeReviewDocument
from lychd.domain.webcrawler.feed import WebcrawlerFeedBinding
from lychd.domain.webcrawler.profile import WebcrawlerBinding
from lychd.domain.webcrawler.review import webcrawler_review

_DIMENSIONS = ("connects", "transmissions", "wire_bytes")


def _conflict() -> ScoutConflictError:
    return ScoutConflictError("Webcrawler retained binding differs.")


def _review_digest(encoded: bytes) -> str:
    try:
        value = json.loads(encoded)
        if (
            set(value) != {"schema_version", "title", "facts"}
            or type(value["schema_version"]) is not int
            or value["schema_version"] != 1
        ):
            raise _conflict()
        document = TypeAdapter(NativeReviewDocument).validate_python(
            {"title": value["title"], "facts": tuple(value["facts"])}
        )
        if document.canonical_bytes() != encoded:
            raise _conflict()
    except (ValueError, TypeError, KeyError):
        raise _conflict() from None
    else:
        return document.digest


def _snapshot(row: WebcrawlerAttempt) -> ScoutAttemptSnapshot:
    try:
        preparation = decode_scout_preparation(row.preparation_bytes)
        binding = decode_native_binding(row.native_binding)
        if binding is None:
            raise _conflict()
        expected_binding, expected_review = webcrawler_review(preparation, legacy=binding.owner == "scout")
        if (
            preparation.canonical_bytes() != row.preparation_bytes
            or preparation.digest != row.preparation_digest
            or preparation.attempt_id != row.id
            or preparation.request_id != row.request_id
            or preparation.run_id != row.run_id
            or preparation.enqueue_seq != row.preparation_enqueue_seq
            or binding != expected_binding
            or row.review_bytes != expected_review.canonical_bytes()
            or binding.action_id != str(row.id)
            or binding.preparation_digest != preparation.digest
            or binding.review_digest != _review_digest(row.review_bytes)
        ):
            raise _conflict()
        return ScoutAttemptSnapshot(
            preparation=preparation,
            consent_id=row.consent_id,
            native_binding=binding,
            status=cast("AttemptStatus", row.status),
            claim_id=row.claim_id,
            execution_enqueue_seq=row.execution_enqueue_seq,
            receipt_id=row.receipt_id,
            receipt_digest=sha256(row.settlement_bytes).hexdigest() if row.settlement_bytes is not None else None,
        )
    except (ValueError, TypeError):
        raise _conflict() from None


async def _commit(session: AsyncSession) -> None:
    try:
        await session.commit()
    except BaseException as error:
        with contextlib.suppress(Exception):
            await session.rollback()
        message = "Webcrawler commit acknowledgement is unavailable."
        raise ScoutCommitUnknownError(message) from error


def _counters(row: WebcrawlerBudget, suffix: str) -> ScoutAllowance:
    return ScoutAllowance(**{name: getattr(row, name + suffix) for name in _DIMENSIONS})


def _set_counters(row: WebcrawlerBudget, suffix: str, value: ScoutAllowance) -> None:
    for name in _DIMENSIONS:
        setattr(row, name + suffix, getattr(value, name))


def _validate_run(run: Run | None, preparation: ScoutAnyPreparation) -> None:
    if (
        run is None
        or run.id != preparation.run_id
        or run.workflow_name != preparation.workflow_name
        or run.sigil_name != preparation.sigil_name
        or run.intent.get("admitted_capability_key") != preparation.capability_key
        or document_digest(run.pattern_manifest) != preparation.pattern_digest
        or document_digest(run.intent) != preparation.intent_digest
    ):
        raise _conflict()
    try:
        if type(preparation) is ScoutFeedPreparation:
            admitted = WebcrawlerFeedBinding.model_validate(run.intent.get("admitted_scout"))
            if (
                run.capability_key is not None
                or run.source != "scavenger"
                or run.pattern_manifest.get("key") != preparation.consumer.pattern
                or run.pattern_manifest.get("revision") != preparation.consumer.pattern_revision
                or admitted.consumer != preparation.consumer
                or admitted.expires_at != preparation.expires_at
            ):
                raise _conflict()
        else:
            admitted = WebcrawlerBinding.model_validate(run.intent.get("admitted_scout"))
        profile = admitted.profile
        if (
            admitted.request_id != preparation.request_id
            or admitted.declaration != preparation.declaration
            or profile.configuration_digest != preparation.configuration_digest
            or profile.binding_digest != preparation.binding_digest
            or profile.provider_id != preparation.provider_id
            or profile.profile != preparation.profile
            or profile.resolver_address != preparation.resolver_address
            or profile.resolver_port != preparation.resolver_port
            or profile.resolver_custody_statement != preparation.resolver_custody_statement
            or profile.allowance != preparation.allowance
            or profile.policy_revision != preparation.policy_revision
            or profile.revocation_generation != preparation.revocation_generation
        ):
            raise _conflict()
    except (ValueError, TypeError):
        raise _conflict() from None


class DbWebcrawlerAttemptStore:
    """One opt-in native profile's unique claims and cumulative reservation custody."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        authorizer: ScoutStoreAuthorizer,
        budget_limits: ScoutBudgetLimits,
        settlement_verifier: ScoutSettlementVerifier,
    ) -> None:
        """Require current host authority and an owned completion verifier."""
        self._factory = session_factory
        self._authorizer = authorizer
        self._limits = budget_limits
        self._settlement_verifier = settlement_verifier

    def _authorize(self, preparation: ScoutAnyPreparation, *actions: ScoutAction) -> None:
        for action in actions:
            decision = self._authorizer.authorize(action, preparation)
            if (
                type(decision) is not ScoutAuthorizationDecision
                or decision.action is not action
                or decision.preparation_digest != preparation.digest
                or decision.allowed is not True
            ):
                message = "Webcrawler current authority refused."
                raise ScoutStoreError(message)

    async def _budgets(
        self, session: AsyncSession, preparation: ScoutAnyPreparation
    ) -> tuple[WebcrawlerBudget, WebcrawlerBudget]:
        configuration = document_digest(
            {
                "limits": self._limits.digest,
                "binding": preparation.binding_digest,
                "configuration": preparation.configuration_digest,
            }
        )
        rows: list[WebcrawlerBudget] = []
        for scope, allowance in (("host", self._limits.host), ("binding", self._limits.binding)):
            values = {name + "_limit": getattr(allowance, name) for name in _DIMENSIONS}
            values.update({name + suffix: 0 for name in _DIMENSIONS for suffix in ("_reserved", "_used")})
            await session.execute(
                insert(WebcrawlerBudget)
                .values(id=uuid4(), scope=scope, configuration_digest=configuration, active_claims=0, **values)
                .on_conflict_do_nothing(index_elements=["scope"])
            )
            row = await session.scalar(
                select(WebcrawlerBudget).where(WebcrawlerBudget.scope == scope).with_for_update()
            )
            if row is None or row.configuration_digest != configuration or _counters(row, "_limit") != allowance:
                raise _conflict()
            rows.append(row)
        return rows[0], rows[1]

    async def _delivery(self, session: AsyncSession, preparation: ScoutAnyPreparation, enqueue_seq: int) -> None:
        run = await session.scalar(select(Run).where(Run.id == preparation.run_id).with_for_update())
        _validate_run(run, preparation)
        if run is None or run.status != "running" or run.enqueue_seq != enqueue_seq:
            message = "Webcrawler current Run delivery is unavailable."
            raise ScoutStoreError(message)
        delivery = await session.scalar(
            select(RunDelivery)
            .where(RunDelivery.run_id == run.id, RunDelivery.enqueue_seq == enqueue_seq)
            .with_for_update()
        )
        if (
            delivery is None
            or delivery.state != "claimed"
            or delivery.claimed_at is None
            or delivery.queue_name != run.queue_name
            or delivery.priority != run.priority
        ):
            message = "Webcrawler current Run delivery is unavailable."
            raise ScoutStoreError(message)

    async def read_request(self, request_id: UUID) -> ScoutAttemptSnapshot | None:
        """Find original preparation for exact duplicate handling, without authority."""
        async with self._factory() as session:
            row = await session.scalar(select(WebcrawlerAttempt).where(WebcrawlerAttempt.request_id == request_id))
            return _snapshot(row) if row is not None else None

    async def read_run_binding(self, run_id: UUID) -> ScoutRunBinding:
        """Project actual retained Run bytes, not a reserialized runtime Intent."""
        async with self._factory() as session:
            run = await session.get(Run, run_id)
            if run is None:
                message = "Webcrawler Run is unavailable."
                raise ScoutStoreError(message)
            return ScoutRunBinding(
                run_id=run.id,
                enqueue_seq=run.enqueue_seq,
                sigil_name=run.sigil_name,
                workflow_name=run.workflow_name,
                pattern_digest=document_digest(run.pattern_manifest),
                intent_digest=document_digest(run.intent),
            )

    async def read(self, attempt_id: UUID) -> ScoutAttemptSnapshot:
        """Read retained restricted status; never restore material or a live claim."""
        async with self._factory() as session:
            row = await session.get(WebcrawlerAttempt, attempt_id)
            if row is None:
                message = "Webcrawler attempt is unavailable."
                raise ScoutStoreError(message)
            return _snapshot(row)

    async def prepare(
        self, preparation: ScoutAnyPreparation, native_binding: NativeConsentBinding, review_bytes: bytes
    ) -> ScoutAttemptSnapshot:
        """Atomically retain one exact preparation and native review Consent."""
        expected_binding, expected_review = webcrawler_review(preparation)
        if (
            native_binding != expected_binding
            or review_bytes != expected_review.canonical_bytes()
            or type(native_binding) is not NativeConsentBinding
            or native_binding.owner != "webcrawler"
            or native_binding.action_id != str(preparation.attempt_id)
            or native_binding.preparation_digest != preparation.digest
            or len(review_bytes) > 256 * 1024
            or native_binding.review_digest != _review_digest(review_bytes)
        ):
            raise _conflict()
        async with self._factory() as session:
            await self._budgets(session, preparation)
            row = await session.scalar(
                select(WebcrawlerAttempt)
                .where(WebcrawlerAttempt.request_id == preparation.request_id)
                .with_for_update()
            )
            if row is not None:
                snapshot = _snapshot(row)
                # A concurrently retained legacy review owns this same preparation.
                if snapshot.preparation != preparation:
                    raise _conflict()
                return snapshot
            await self._delivery(session, preparation, preparation.enqueue_seq)
            now = cast("datetime", await session.scalar(select(func.clock_timestamp())))
            if preparation.expires_at <= now:
                message = "Webcrawler preparation expired."
                raise ScoutStoreError(message)
            self._authorize(preparation, ScoutAction.CLASSIFY_LOCATOR, ScoutAction.REVIEW)
            consent = await ConsentService(session=session).request(
                run_id=str(preparation.run_id),
                tool_name="webcrawler.fetch_extract",
                tool_call_id=str(preparation.attempt_id),
                call_ids=(str(preparation.attempt_id),),
                payload={"attempt_id": str(preparation.attempt_id)},
                preauth=None,
                native_binding=native_binding,
                auto_commit=False,
            )
            consent.expires_at = preparation.expires_at
            row = WebcrawlerAttempt(
                id=preparation.attempt_id,
                request_id=preparation.request_id,
                run_id=preparation.run_id,
                consent_id=consent.id,
                preparation_enqueue_seq=preparation.enqueue_seq,
                preparation_bytes=preparation.canonical_bytes(),
                preparation_digest=preparation.digest,
                native_binding=native_binding.document(),
                review_bytes=review_bytes,
                status="prepared",
            )
            session.add(row)
            await session.flush()
            snapshot = _snapshot(row)
            await _commit(session)
            return snapshot

    async def claim(
        self, attempt_id: UUID, expected_preparation_digest: str, enqueue_seq: int
    ) -> NewScoutClaim | ScoutAttemptSnapshot:
        """Reserve worst-case host and binding allowance before fresh issuance."""
        if type(enqueue_seq) is not int or enqueue_seq < 0:
            raise _conflict()
        retained = await self.read(attempt_id)
        if retained.preparation.digest != expected_preparation_digest:
            raise _conflict()
        async with self._factory() as session:
            budgets = await self._budgets(session, retained.preparation)
            row = await session.scalar(
                select(WebcrawlerAttempt).where(WebcrawlerAttempt.id == attempt_id).with_for_update()
            )
            if row is None:
                raise _conflict()
            snapshot = _snapshot(row)
            if snapshot.preparation != retained.preparation:
                raise _conflict()
            if row.status != "prepared":
                return snapshot
            await self._delivery(session, snapshot.preparation, enqueue_seq)
            consent = await session.scalar(select(Consent).where(Consent.id == row.consent_id).with_for_update())
            now = cast("datetime", await session.scalar(select(func.clock_timestamp())))
            self._validate_consent(snapshot, consent, now)
            self._reserve(budgets, snapshot.preparation.allowance)
            self._authorize(snapshot.preparation, ScoutAction.FETCH, ScoutAction.EXTRACT)
            claim_id = uuid4()
            row.claim_id, row.execution_enqueue_seq, row.claimed_at, row.status = claim_id, enqueue_seq, now, "claimed"
            await session.flush()
            claim = NewScoutClaim(
                preparation=snapshot.preparation,
                consent_id=row.consent_id,
                enqueue_seq=enqueue_seq,
                claim_id=claim_id,
                committed_at=now,
            )
            await _commit(session)
            return claim

    @staticmethod
    def _validate_consent(snapshot: ScoutAttemptSnapshot, consent: Consent | None, now: datetime) -> None:
        if (
            consent is None
            or consent.run_id != snapshot.preparation.run_id
            or consent.tool_name != f"{snapshot.native_binding.owner}.fetch_extract"
            or consent.tool_call_id != str(snapshot.preparation.attempt_id)
            or not consent.native_review_required
            or decode_native_binding(consent.native_binding) != snapshot.native_binding
            or consent.status != "granted"
            or not consent.decided_by
            or consent.decided_at is None
            or consent.preauth_slug is not None
            or consent.decided_by == "codex:preauth"
            or consent.expires_at is None
            or consent.expires_at <= now
            or snapshot.preparation.expires_at <= now
        ):
            message = "Webcrawler exact native Consent is unavailable."
            raise ScoutStoreError(message)

    @staticmethod
    def _reserve(budgets: tuple[WebcrawlerBudget, WebcrawlerBudget], allowance: ScoutAllowance) -> None:
        if budgets[1].active_claims != 0:
            message = "Webcrawler binding already has an active or uncertain passage."
            raise ScoutStoreError(message)
        budgets[1].active_claims = 1
        for row in budgets:
            reserved = _counters(row, "_reserved").add(allowance)
            if not _counters(row, "_used").add(reserved).within(_counters(row, "_limit")):
                message = "Webcrawler durable allowance is exhausted."
                raise ScoutStoreError(message)
            _set_counters(row, "_reserved", reserved)

    async def _locked_claim(
        self, session: AsyncSession, claim: NewScoutClaim
    ) -> tuple[WebcrawlerAttempt, tuple[WebcrawlerBudget, WebcrawlerBudget]]:
        budgets = await self._budgets(session, claim.preparation)
        row = await session.scalar(
            select(WebcrawlerAttempt).where(WebcrawlerAttempt.id == claim.preparation.attempt_id).with_for_update()
        )
        if row is None:
            raise _conflict()
        snapshot = _snapshot(row)
        if (
            snapshot.preparation != claim.preparation
            or row.claim_id != claim.claim_id
            or row.consent_id != claim.consent_id
            or row.execution_enqueue_seq != claim.enqueue_seq
            or row.claimed_at != claim.committed_at
        ):
            raise _conflict()
        return row, budgets

    async def reconcile_before(self, cutoff: datetime) -> int:
        """Before worker admission, fence prior claims without refund or replay."""
        if cutoff.tzinfo is None:
            raise _conflict()
        async with self._factory() as session:
            result = await session.execute(
                update(WebcrawlerAttempt)
                .where(WebcrawlerAttempt.status == "claimed", WebcrawlerAttempt.claimed_at < cutoff)
                .values(status="unknown_after_crash")
                .returning(WebcrawlerAttempt.id)
            )
            count = len(result.scalars().all())
            await _commit(session)
            return count

    async def recover_unknown(self, attempt_id: UUID) -> ScoutAttemptSnapshot:
        """Startup reconciliation fences an abandoned claim; it never reissues it."""
        retained = await self.read(attempt_id)
        async with self._factory() as session:
            await self._budgets(session, retained.preparation)
            row = await session.scalar(
                select(WebcrawlerAttempt).where(WebcrawlerAttempt.id == attempt_id).with_for_update()
            )
            if row is None or _snapshot(row).preparation != retained.preparation:
                raise _conflict()
            if row.status == "claimed":
                row.status = "unknown_after_crash"
                await session.flush()
                snapshot = _snapshot(row)
                await _commit(session)
                return snapshot
            return _snapshot(row)

    async def unknown(self, claim: NewScoutClaim) -> ScoutAttemptSnapshot:
        """Fence uncertainty without releasing a byte of the reserved allowance."""
        async with self._factory() as session:
            row, _ = await self._locked_claim(session, claim)
            if row.status in {"succeeded", "refused"}:
                return _snapshot(row)
            row.status = "unknown_after_crash"
            await session.flush()
            snapshot = _snapshot(row)
            await _commit(session)
            return snapshot

    async def settle(self, claim: NewScoutClaim, settlement: ScoutSettlement) -> ScoutAttemptSnapshot:
        """Persist verified owned evidence and usage before releasing unused reserve."""
        encoded = settlement.model_dump_json().encode()
        async with self._factory() as session:
            row, budgets = await self._locked_claim(session, claim)
            if row.status in {"succeeded", "refused"}:
                if row.settlement_bytes != encoded:
                    raise _conflict()
                return _snapshot(row)
            if not settlement.usage.within(claim.preparation.allowance):
                message = "Webcrawler measured allowance exceeds reservation."
                raise ScoutStoreError(message)
            self._settlement_verifier.verify(claim, settlement)
            if budgets[1].active_claims != 1:
                raise _conflict()
            budgets[1].active_claims = 0
            for budget in budgets:
                _set_counters(budget, "_reserved", _counters(budget, "_reserved").subtract(claim.preparation.allowance))
                _set_counters(budget, "_used", _counters(budget, "_used").add(settlement.usage))
            row.status, row.receipt_id, row.settlement_bytes = settlement.outcome, settlement.receipt_id, encoded
            await session.flush()
            snapshot = _snapshot(row)
            await _commit(session)
            return snapshot
