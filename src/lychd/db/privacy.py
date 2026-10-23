"""PostgreSQL disclosure admission; no transaction spans recorder handoff.

Every mutation locks permanent capacity rows in host/purpose/Cut order, then the
transmission, Run and exact Delivery. Counters only increase. Commit uncertainty
returns no activation and cannot restore capacity.
"""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lychd.db.models.privacy import DisclosureCapacityRecord, DisclosureTransmission
from lychd.db.models.run import Run
from lychd.db.models.run_delivery import RunDelivery
from lychd.domain.privacy.contracts import bytes_digest, canonical_bytes, digest
from lychd.domain.privacy.disclosure import (
    DisclosureAuthority,
    DisclosureCapacity,
    DisclosureCompletionOwner,
    DisclosureDecision,
    DisclosureError,
    DisclosureLimits,
    DisclosurePreparation,
    DisclosureSettlement,
    DisclosureSnapshot,
    DisclosureStatus,
    FreshDisclosureClaim,
    RecordingCompletion,
    refuse,
)
from lychd.domain.privacy.verification import checked


def _validate_retained_evidence(row: DisclosureTransmission, preparation: DisclosurePreparation) -> None:
    if row.status == "prepared":
        if any(
            value is not None
            for value in (row.claim_id, row.claimed_at, row.decision_bytes, row.receipt_id, row.settlement_bytes)
        ):
            refuse("conflict")
    else:
        if row.decision_bytes is None:
            refuse("conflict")
        decision = DisclosureDecision.model_validate_json(row.decision_bytes)
        if (
            canonical_bytes(decision.model_dump(mode="json")) != row.decision_bytes
            or decision.preparation_digest != preparation.digest
            or decision.claim_id != row.claim_id
            or decision.charged_bytes != preparation.candidate_size
            or decision.admitted_at != row.claimed_at
        ):
            refuse("conflict")
        if row.status == "claimed" and (row.receipt_id is not None or row.settlement_bytes is not None):
            refuse("conflict")
        if row.status in {"recorded", "refused"} and row.settlement_bytes is None:
            refuse("conflict")
        if row.settlement_bytes is not None:
            settlement = DisclosureSettlement.model_validate_json(row.settlement_bytes)
            if (
                canonical_bytes(settlement) != row.settlement_bytes
                or settlement.transmission_id != row.id
                or settlement.claim_id != row.claim_id
                or settlement.receipt_id != row.receipt_id
                or settlement.outcome != row.status
            ):
                refuse("conflict")
        elif row.receipt_id is not None:
            refuse("conflict")


def _snapshot(row: DisclosureTransmission) -> DisclosureSnapshot:
    try:
        preparation = DisclosurePreparation.model_validate_json(row.preparation_bytes)
        binding = preparation.cut.plan.binding
        if (
            preparation.canonical_bytes() != row.preparation_bytes
            or preparation.digest != row.preparation_digest
            or preparation.transmission_id != row.id
            or preparation.request_id != row.request_id
            or preparation.run.run_id != row.run_id
            or preparation.run.delivery_id != row.delivery_id
            or binding.occurrence_id != row.occurrence_id
            or binding.attempt_id != row.attempt_id
        ):
            refuse("conflict")
        _validate_retained_evidence(row, preparation)
        return DisclosureSnapshot(
            preparation=preparation,
            status=cast("DisclosureStatus", row.status),
            claim_id=row.claim_id,
            decision_digest=bytes_digest(row.decision_bytes) if row.decision_bytes is not None else None,
            receipt_id=row.receipt_id,
        )
    except (ValueError, TypeError):
        refuse("conflict")


async def _commit(session: AsyncSession) -> None:
    try:
        await session.commit()
    except BaseException:  # noqa: BLE001 - suppress foreign diagnostics at the privacy boundary
        with contextlib.suppress(BaseException):
            await session.rollback()
        refuse("commit-unknown")


class DbDisclosureStore:
    """Stable ceilings, exact retained owners and one-use process-local issuance."""

    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        authority: DisclosureAuthority,
        limits: DisclosureLimits,
        completions: DisclosureCompletionOwner,
    ) -> None:
        """Retain the trusted host and completion owners without any egress adapter."""
        self._factory = factory
        self._authority = authority
        self._limits = checked(limits)
        self._completions = completions
        self._live: dict[UUID, FreshDisclosureClaim] = {}

    async def _capacities(
        self, session: AsyncSession, preparation: DisclosurePreparation
    ) -> list[DisclosureCapacityRecord]:
        cut = preparation.cut
        scopes = (
            (
                "host",
                "host",
                self._limits.host,
                digest((preparation.host_id, preparation.configuration_digest, self._limits.host)),
            ),
            (
                "purpose",
                str(cut.plan.binding.purpose_id),
                self._limits.purpose,
                digest((preparation.host_id, preparation.configuration_digest, self._limits.purpose)),
            ),
            (
                "cut",
                str(cut.cut_id),
                DisclosureCapacity(
                    uses=cut.plan.max_disclosures, bytes=cut.plan.max_disclosures * preparation.candidate_size
                ),
                digest(cut),
            ),
        )
        rows: list[DisclosureCapacityRecord] = []
        for scope, scope_id, limit, configuration in scopes:
            await session.execute(
                insert(DisclosureCapacityRecord)
                .values(
                    id=uuid4(),
                    scope=scope,
                    scope_id=scope_id,
                    configuration_digest=configuration,
                    uses_limit=limit.uses,
                    bytes_limit=limit.bytes,
                    uses_charged=0,
                    bytes_charged=0,
                )
                .on_conflict_do_nothing(index_elements=["scope", "scope_id"])
            )
            row = await session.scalar(
                select(DisclosureCapacityRecord)
                .where(
                    DisclosureCapacityRecord.scope == scope,
                    DisclosureCapacityRecord.scope_id == scope_id,
                )
                .with_for_update()
            )
            if (
                row is None
                or row.configuration_digest != configuration
                or row.uses_limit != limit.uses
                or row.bytes_limit != limit.bytes
            ):
                refuse("conflict")
            rows.append(row)
        return rows

    async def _transmission(
        self, session: AsyncSession, preparation: DisclosurePreparation
    ) -> DisclosureTransmission | None:
        binding = preparation.cut.plan.binding
        rows = list(
            (
                await session.scalars(
                    select(DisclosureTransmission)
                    .where(
                        or_(
                            DisclosureTransmission.id == preparation.transmission_id,
                            DisclosureTransmission.request_id == preparation.request_id,
                            (DisclosureTransmission.run_id == binding.run_id)
                            & (DisclosureTransmission.occurrence_id == binding.occurrence_id)
                            & (DisclosureTransmission.attempt_id == binding.attempt_id),
                        )
                    )
                    .with_for_update()
                )
            ).all()
        )
        if len(rows) > 1 or (rows and _snapshot(rows[0]).preparation != preparation):
            refuse("conflict")
        return rows[0] if rows else None

    async def _execution(self, session: AsyncSession, preparation: DisclosurePreparation) -> None:
        expected = preparation.run
        run = await session.scalar(select(Run).where(Run.id == expected.run_id).with_for_update())
        if (
            run is None
            or run.status != "running"
            or run.enqueue_seq != expected.enqueue_seq
            or run.priority != expected.priority
            or run.queue_name != expected.queue_name
            or run.workflow_name != expected.workflow_name
            or run.sigil_name != expected.sigil_name
            or digest(run.intent) != expected.intent_digest
            or digest(run.pattern_manifest) != expected.pattern_digest
        ):
            refuse("binding")
        delivery = await session.scalar(
            select(RunDelivery)
            .where(
                RunDelivery.id == expected.delivery_id,
                RunDelivery.run_id == expected.run_id,
                RunDelivery.enqueue_seq == expected.enqueue_seq,
            )
            .with_for_update()
        )
        if (
            delivery is None
            or delivery.state != "claimed"
            or delivery.claimed_at is None
            or delivery.priority != expected.priority
            or delivery.queue_name != expected.queue_name
        ):
            refuse("binding")

    async def read(self, transmission_id: UUID) -> DisclosureSnapshot | None:
        """Read evidence without issuing or restoring a live claim."""
        try:
            async with self._factory() as session:
                row = await session.get(DisclosureTransmission, transmission_id)
                return _snapshot(row) if row is not None else None
        except DisclosureError:
            raise
        except Exception:  # noqa: BLE001 - project only closed privacy errors
            refuse("store")

    async def prepare(self, preparation: DisclosurePreparation) -> DisclosureSnapshot:
        """Retain exact prepared evidence; identity reuse with different bytes refuses."""
        try:
            preparation = checked(preparation)
            async with self._factory() as session:
                await self._capacities(session, preparation)
                row = await self._transmission(session, preparation)
                if row is not None:
                    return _snapshot(row)
                await self._execution(session, preparation)
                self._authority.authorize(preparation)
                binding = preparation.cut.plan.binding
                row = DisclosureTransmission(
                    id=preparation.transmission_id,
                    request_id=preparation.request_id,
                    run_id=preparation.run.run_id,
                    delivery_id=preparation.run.delivery_id,
                    occurrence_id=binding.occurrence_id,
                    attempt_id=binding.attempt_id,
                    preparation_bytes=preparation.canonical_bytes(),
                    preparation_digest=preparation.digest,
                    status="prepared",
                )
                session.add(row)
                await session.flush()
                snapshot = _snapshot(row)
                self._authority.authorize(preparation)
                await _commit(session)
                self._authority.authorize(preparation)
                return snapshot
        except DisclosureError:
            raise
        except Exception:  # noqa: BLE001 - project only closed privacy errors
            refuse("store")

    async def claim(self, preparation: DisclosurePreparation) -> FreshDisclosureClaim | DisclosureSnapshot:
        """Charge full bytes and one use before issuing an acknowledged fresh claim."""
        try:
            preparation = checked(preparation)
            async with self._factory() as session:
                capacities = await self._capacities(session, preparation)
                row = await self._transmission(session, preparation)
                if row is None:
                    refuse("claim")
                if row.status != "prepared":
                    return _snapshot(row)
                await self._execution(session, preparation)
                now = cast("datetime", await session.scalar(select(func.clock_timestamp())))
                if now.timestamp() >= preparation.cut.expires_at:
                    refuse("expiry")
                self._authority.authorize(preparation)
                for capacity in capacities:
                    if (
                        capacity.uses_charged >= capacity.uses_limit
                        or preparation.candidate_size > capacity.bytes_limit - capacity.bytes_charged
                    ):
                        refuse("capacity")
                    capacity.uses_charged += 1
                    capacity.bytes_charged += preparation.candidate_size
                claim_id = uuid4()
                decision = DisclosureDecision(
                    preparation_digest=preparation.digest,
                    claim_id=claim_id,
                    charged_bytes=preparation.candidate_size,
                    admitted_at=now,
                )
                row.status, row.claim_id, row.claimed_at = "claimed", claim_id, now
                row.decision_bytes = canonical_bytes(decision.model_dump(mode="json"))
                await session.flush()
                self._authority.authorize(preparation)
                await _commit(session)
                self._authority.authorize(preparation)
                claim = FreshDisclosureClaim(preparation, claim_id)
                self._live[claim_id] = claim
                return claim
        except DisclosureError:
            raise
        except Exception:  # noqa: BLE001 - project only closed privacy errors
            refuse("store")

    def consume(self, claim: FreshDisclosureClaim) -> None:
        """Consume exact issued identity before any final check or handoff."""
        if type(claim) is not FreshDisclosureClaim or self._live.get(claim.claim_id) is not claim:
            refuse("claim")
        del self._live[claim.claim_id]

    async def check_claim(self, claim: FreshDisclosureClaim) -> None:
        """Recheck retained claim and execution immediately before local activation."""
        try:
            async with self._factory() as session:
                await self._capacities(session, claim.preparation)
                row = await self._transmission(session, claim.preparation)
                if row is None or row.status != "claimed" or row.claim_id != claim.claim_id:
                    refuse("claim")
                await self._execution(session, claim.preparation)
                self._authority.authorize(claim.preparation)
                await _commit(session)
                self._authority.authorize(claim.preparation)
        except DisclosureError:
            raise
        except Exception:  # noqa: BLE001 - project only closed privacy errors
            refuse("store")

    async def recover(self, transmission_id: UUID) -> DisclosureSnapshot:
        """Absorb abandoned claims into uncertainty without refund or reissuance."""
        retained = await self.read(transmission_id)
        if retained is None:
            refuse("claim")
        try:
            async with self._factory() as session:
                await self._capacities(session, retained.preparation)
                row = await self._transmission(session, retained.preparation)
                if row is None:
                    refuse("conflict")
                if row.claim_id is not None:
                    self._live.pop(row.claim_id, None)
                if row.status == "claimed":
                    row.status = "unknown"
                    await session.flush()
                    snapshot = _snapshot(row)
                    await _commit(session)
                    return snapshot
                return _snapshot(row)
        except DisclosureError:
            raise
        except Exception:  # noqa: BLE001 - project only closed privacy errors
            refuse("store")

    async def settle(self, claim: FreshDisclosureClaim, completion: RecordingCompletion) -> DisclosureSnapshot:
        """Settle only the recording owner's original completion; unknown is absorbing."""
        self._completions.verify_completion(claim, completion)
        try:
            async with self._factory() as session:
                await self._capacities(session, claim.preparation)
                row = await self._transmission(session, claim.preparation)
                if row is None or row.claim_id != claim.claim_id:
                    refuse("claim")
                encoded = completion.canonical_bytes()
                if row.status == "unknown":
                    return _snapshot(row)
                if row.status in {"recorded", "refused"}:
                    if row.settlement_bytes != encoded:
                        refuse("conflict")
                    return _snapshot(row)
                if row.status != "claimed":
                    refuse("claim")
                row.status, row.receipt_id, row.settlement_bytes = completion.outcome, completion.receipt_id, encoded
                await session.flush()
                snapshot = _snapshot(row)
                await _commit(session)
                return snapshot
        except DisclosureError:
            raise
        except Exception:  # noqa: BLE001 - project only closed privacy errors
            refuse("store")
