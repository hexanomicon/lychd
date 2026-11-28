"""Serialized PostgreSQL custody for one finite feed consumer, never an acquisition gate."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, cast
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from lychd.agents.router import Intent
from lychd.compositions.scavenger.ports import ObservationCommit
from lychd.compositions.scavenger.schemas import (
    CampaignSeed,
    LiteralFilter,
    MarketObservation,
    ScavengerRefused,
    canonical,
    decode,
    digest,
    title_link_field,
)
from lychd.db.models.run import Run
from lychd.db.models.run_delivery import RunDelivery
from lychd.db.models.scavenger import ScavengerObservation
from lychd.db.models.webcrawler import WebcrawlerAttempt
from lychd.domain.codex.scopes import scopes_satisfied
from lychd.domain.cortex.runs import TERMINAL_STATUSES, RunStatus
from lychd.domain.scout.attempts import (
    AttemptStatus,
    ScoutFeedConsumer,
    ScoutFeedPreparation,
    ScoutSettlement,
    decode_scout_preparation,
    document_digest,
)
from lychd.domain.webcrawler.feed import WebcrawlerFeedBinding

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from lychd.domain.webcrawler.feed import WebcrawlerFeedMaterial


@dataclass(frozen=True, kw_only=True)
class ScavengerAdmission:
    """Receiving-owner references; complete supplied facts remain in its table."""

    consumer: ScoutFeedConsumer
    deadline: datetime
    run_id: UUID | None
    status: str


@dataclass(frozen=True, kw_only=True)
class RetainedObservation:
    """Protected application read; this object must not enter generic Run projection."""

    admission_id: UUID
    request_digest: str
    status: Literal["reserved", "bound", "committed", "deleted"]
    run_id: UUID | None
    seed: CampaignSeed | None = field(repr=False)
    initial_filter: LiteralFilter | None = field(repr=False)
    observation: MarketObservation | None = field(repr=False)
    observation_digest: str | None
    run_status: RunStatus | None
    acquisition_status: AttemptStatus | None
    terminal_disposition: Literal["pending", "unknown", "terminal"]


@dataclass(frozen=True, kw_only=True)
class _Disposition:
    """One locked Run/delivery snapshot and immutable Webcrawler terminal observation."""

    run_id: UUID | None
    run_status: RunStatus | None
    acquisition_status: AttemptStatus | None
    state: Literal["pending", "unknown", "terminal"]


def _consumer(row: ScavengerObservation) -> ScoutFeedConsumer:
    return ScoutFeedConsumer(
        application_admission_id=row.id,
        application_request_digest=row.request_digest,
        seed_digest=row.seed_digest,
        initial_filter_digest=row.initial_filter_digest,
    )


def _payloads(row: ScavengerObservation) -> tuple[CampaignSeed, LiteralFilter]:
    if row.status == "deleted" or row.seed_bytes is None or row.filter_bytes is None:
        reason = "deleted"
        raise ScavengerRefused(reason)
    seed = decode(row.seed_bytes)
    selection = LiteralFilter.model_validate_json(row.filter_bytes)
    if (
        type(seed) is not CampaignSeed
        or canonical(seed) != row.seed_bytes
        or seed.digest != row.seed_digest
        or canonical(selection) != row.filter_bytes
        or digest(row.filter_bytes) != row.initial_filter_digest
    ):
        reason = "application_custody"
        raise ScavengerRefused(reason)
    return seed, selection


def _observation(row: ScavengerObservation) -> MarketObservation | None:
    if row.status != "committed":
        if row.observation_bytes is not None:
            reason = "application_custody"
            raise ScavengerRefused(reason)
        return None
    if row.observation_bytes is None:
        reason = "application_custody"
        raise ScavengerRefused(reason)
    result = decode(row.observation_bytes, observation=True)
    if (
        type(result) is not MarketObservation
        or canonical(result) != row.observation_bytes
        or result.digest != row.observation_digest
        or result.admission_id != row.id
        or result.observation_id != row.id
        or result.run_id != row.run_id
        or result.seed_digest != row.seed_digest
    ):
        reason = "application_custody"
        raise ScavengerRefused(reason)
    return result


def _reference(observation: MarketObservation) -> ObservationCommit:
    return ObservationCommit(
        admission_id=observation.admission_id,
        observation_id=observation.observation_id,
        run_id=observation.run_id,
        observation_digest=observation.digest,
        field_digest=observation.field_digest,
        item_count=len(observation.items),
    )


class DbScavengerStore:
    """Lock the finite application slot, then its row and Run.

    Webcrawler claim locks its attempt before Run; never take that attempt lock here.
    Successful Webcrawler settlement is immutable. The locked Run prevents a new
    claim from crossing a proved terminal Run during deletion.

    Every public operation requires a synchronous current-authority callback.
    It runs after lock acquisition, before commit and after transaction cleanup.
    Losing response authority cannot undo a committed mutation; exact replay
    reconciles that same identity. No method performs or retries acquisition.
    """

    def __init__(self, factory: async_sessionmaker[AsyncSession], *, pattern: dict[str, Any]) -> None:
        """Bind the Phylactery factory and exact source-built Pattern snapshot."""
        self.factory = factory
        self.pattern = pattern

    @asynccontextmanager
    async def _transaction(self) -> AsyncGenerator[AsyncSession]:
        """Keep payload-bearing driver/decoder failures out of generic Run/log evidence."""
        try:
            async with self.factory() as session, session.begin():
                yield session
        except SQLAlchemyError:
            reason = "application_storage"
            raise ScavengerRefused(reason) from None
        except ValidationError:
            reason = "application_custody"
            raise ScavengerRefused(reason) from None

    @staticmethod
    async def _lock(session: AsyncSession, authorize: Callable[[], None]) -> None:
        await session.execute(text("SET LOCAL statement_timeout = '5s'"))
        await session.execute(text("SET LOCAL lock_timeout = '2s'"))
        await session.execute(text("SELECT pg_advisory_xact_lock(727162, 1)"))
        authorize()

    @staticmethod
    async def _row(session: AsyncSession, admission_id: UUID, owner: str) -> ScavengerObservation:
        row = await session.scalar(
            select(ScavengerObservation)
            .where(
                ScavengerObservation.id == admission_id,
                ScavengerObservation.owner == owner,
            )
            .with_for_update()
        )
        if row is None:
            reason = "application_unavailable"
            raise ScavengerRefused(reason)
        return row

    async def _run(
        self,
        session: AsyncSession,
        row: ScavengerObservation,
        run_id: UUID,
        binding: WebcrawlerFeedBinding,
    ) -> Run:
        run = await session.scalar(select(Run).where(Run.id == run_id).with_for_update())
        if run is None:
            reason = "run_custody"
            raise ScavengerRefused(reason)
        # Admission idempotency metadata is not an Intent field.
        intent = Intent.model_validate({k: v for k, v in run.intent.items() if k != "idempotency_key"})
        if (
            run.source != "scavenger"
            or run.workflow_name != "scavenger.observe_market"
            or run.pattern_manifest != self.pattern
            or run.sigil_name != row.owner
            or run.capability_key is not None
            or intent.admitted_capability_key is not None
            or intent.source != "scavenger"
            or intent.sigil_name != row.owner
            or not scopes_satisfied(intent.sigil_scopes, ("runs:submit",))
            or intent.prompt != str(row.id)
            or type(intent.admitted_webcrawler) is not WebcrawlerFeedBinding
            or intent.admitted_webcrawler != binding
            or binding.consumer != _consumer(row)
            or binding.request_id != row.id
            or binding.profile.configuration_digest != row.configuration_digest
        ):
            reason = "run_custody"
            raise ScavengerRefused(reason)
        return run

    async def reserve(
        self,
        *,
        request_id: UUID,
        owner: str,
        seed: CampaignSeed,
        selection: LiteralFilter,
        configuration_digest: str,
        authorize: Callable[[], None],
    ) -> ScavengerAdmission:
        """Retain the exact supplied seed/filter once, before any Run is released."""
        authorize()
        seed_bytes, filter_bytes = canonical(seed), canonical(selection)
        request_digest = document_digest(
            {
                "request_id": str(request_id),
                "seed_digest": seed.digest,
                "initial_filter_digest": digest(filter_bytes),
                "profile": "bazos-pc-title-link@1",
                "configuration_digest": configuration_digest,
            }
        )
        async with self._transaction() as session:
            await self._lock(session, authorize)
            row = await session.get(ScavengerObservation, request_id)
            if row is not None:
                if row.owner != owner or row.request_digest != request_digest:
                    reason = "conflicting_replay"
                    raise ScavengerRefused(reason)
                retained_seed, _ = _payloads(row)
                result = ScavengerAdmission(
                    consumer=_consumer(row),
                    deadline=retained_seed.deadline,
                    run_id=row.run_id,
                    status=row.status,
                )
            else:
                occupied = await session.scalar(select(ScavengerObservation.id).where(ScavengerObservation.slot == 1))
                now = await session.scalar(select(func.clock_timestamp()))
                if occupied is not None or now is None or seed.deadline <= now:
                    reason = "reservation_unavailable"
                    raise ScavengerRefused(reason)
                authorize()
                row = ScavengerObservation(
                    id=request_id,
                    owner=owner,
                    request_digest=request_digest,
                    seed_digest=seed.digest,
                    initial_filter_digest=digest(filter_bytes),
                    configuration_digest=configuration_digest,
                    slot=1,
                    status="reserved",
                    seed_bytes=seed_bytes,
                    filter_bytes=filter_bytes,
                )
                session.add(row)
                await session.flush()
                result = ScavengerAdmission(
                    consumer=_consumer(row),
                    deadline=seed.deadline,
                    run_id=None,
                    status="reserved",
                )
            authorize()
        authorize()
        return result

    async def retain_run(
        self,
        *,
        run_id: UUID,
        binding: WebcrawlerFeedBinding,
        owner: str,
        authorize: Callable[[], None],
    ) -> None:
        """Bind one HELD delivery, or acknowledge its exact already-retained Run.

        Concurrent admission owners can both observe HELD before one releases
        it. The receiving row, not the later delivery phase, proves that this
        exact handoff already succeeded. A replay never rewrites its status.
        """
        authorize()
        async with self._transaction() as session:
            await self._lock(session, authorize)
            row = await self._row(session, binding.consumer.application_admission_id, owner)
            _payloads(row)
            run = await self._run(session, row, run_id, binding)
            delivery = await session.scalar(
                select(RunDelivery).where(
                    RunDelivery.run_id == run_id,
                    RunDelivery.enqueue_seq == run.enqueue_seq,
                )
            )
            if row.run_id == run_id and row.status in {"bound", "committed"}:
                _observation(row)
            elif row.run_id is None and row.status == "reserved":
                if delivery is None or delivery.state != "held" or run.status != "queued":
                    reason = "held_delivery_required"
                    raise ScavengerRefused(reason)
                row.run_id, row.status = run_id, "bound"
            else:
                reason = "application_binding"
                raise ScavengerRefused(reason)
            authorize()
        authorize()

    async def committed(
        self,
        *,
        run_id: UUID,
        binding: WebcrawlerFeedBinding,
        owner: str,
        authorize: Callable[[], None],
    ) -> ObservationCommit | None:
        """Resolve one known commit after lost acknowledgement, without a new claim."""
        authorize()
        async with self._transaction() as session:
            await self._lock(session, authorize)
            row = await self._row(session, binding.consumer.application_admission_id, owner)
            _payloads(row)
            await self._run(session, row, run_id, binding)
            if row.run_id != run_id or row.status not in {"bound", "committed"}:
                reason = "application_binding"
                raise ScavengerRefused(reason)
            observation = _observation(row)
            result = _reference(observation) if observation is not None else None
            authorize()
        authorize()
        return result

    async def adopt(
        self,
        *,
        run_id: UUID,
        binding: WebcrawlerFeedBinding,
        material: WebcrawlerFeedMaterial,
        owner: str,
        authorize: Callable[[], None],
    ) -> ObservationCommit:
        """Commit the complete field under exact successful Webcrawler/Run custody once."""
        authorize()
        async with self._transaction() as session:
            await self._lock(session, authorize)
            row = await self._row(session, binding.consumer.application_admission_id, owner)
            _payloads(row)
            run = await self._run(session, row, run_id, binding)
            if row.run_id != run_id or row.status not in {"bound", "committed"} or run.status != "running":
                reason = "adoption_unavailable"
                raise ScavengerRefused(reason)
            attempt = await session.scalar(select(WebcrawlerAttempt).where(WebcrawlerAttempt.id == material.attempt_id))
            authorize()
            observation = self._candidate(row, run, binding, material, attempt)
            retained = _observation(row)
            if retained is not None and canonical(retained) != canonical(observation):
                reason = "conflicting_result"
                raise ScavengerRefused(reason)
            authorize()
            row.observation_bytes = canonical(observation)
            row.observation_digest, row.status = observation.digest, "committed"
            result = _reference(observation)
        authorize()
        return result

    @staticmethod
    def _candidate(
        row: ScavengerObservation,
        run: Run,
        binding: WebcrawlerFeedBinding,
        material: WebcrawlerFeedMaterial,
        attempt: WebcrawlerAttempt | None,
    ) -> MarketObservation:
        if attempt is None or attempt.settlement_bytes is None:
            reason = "scout_custody"
            raise ScavengerRefused(reason)
        preparation = decode_scout_preparation(attempt.preparation_bytes)
        settlement = ScoutSettlement.model_validate_json(attempt.settlement_bytes)
        if (
            type(preparation) is not ScoutFeedPreparation
            or preparation.digest != attempt.preparation_digest
            or preparation.consumer != binding.consumer
            or preparation.request_id != row.id
            or preparation.attempt_id != material.attempt_id
            or preparation.run_id != run.id
            or preparation.pattern_digest != document_digest(run.pattern_manifest)
            or preparation.intent_digest != document_digest(run.intent)
            or preparation.sigil_name != run.sigil_name
            or preparation.expires_at != binding.expires_at
            or preparation.binding_digest != binding.profile.binding_digest
            or preparation.configuration_digest != binding.profile.configuration_digest
            or preparation.declaration != binding.declaration
            or attempt.run_id != run.id
            or attempt.status != "succeeded"
            or settlement.outcome != "succeeded"
            or attempt.execution_enqueue_seq != run.enqueue_seq
            or attempt.receipt_id != material.receipt_id
            or settlement.receipt_id != material.receipt_id
            or digest(attempt.settlement_bytes) != material.receipt_digest
            or material.consumer != binding.consumer
            or material.requested_url != preparation.url
            or material.contacted_url != preparation.url
        ):
            reason = "scout_custody"
            raise ScavengerRefused(reason)
        metadata = json.loads(settlement.handoff_evidence).get("extraction", {})
        if (
            metadata.get("source_digest") != material.extraction.source_digest
            or metadata.get("record_digest") != material.extraction.record_digest
            or metadata.get("item_count") != len(material.extraction.items)
        ):
            reason = "scout_custody"
            raise ScavengerRefused(reason)
        return MarketObservation(
            observation_id=row.id,
            admission_id=row.id,
            run_id=run.id,
            seed_digest=row.seed_digest,
            pattern_digest=preparation.pattern_digest,
            acquisition_binding_digest=preparation.binding_digest,
            requested_url=material.requested_url,
            contacted_url=material.contacted_url,
            acquired_at=material.acquired_at,
            scout_receipt_id=material.receipt_id,
            scout_receipt_digest=material.receipt_digest,
            source_digest=material.extraction.source_digest,
            record_digest=material.extraction.record_digest,
            omitted_elements=material.extraction.omitted_elements,
            items=title_link_field(material.extraction),
        )

    async def read(self, *, admission_id: UUID, owner: str, authorize: Callable[[], None]) -> RetainedObservation:
        """Read app-owned content under fresh retrieval authority, including after restart."""
        authorize()
        async with self._transaction() as session:
            await self._lock(session, authorize)
            row = await self._row(session, admission_id, owner)
            result = await self._read(session, row)
            authorize()
        authorize()
        return result

    async def active(self, *, owner: str, authorize: Callable[[], None]) -> RetainedObservation | None:
        """Read the one occupied slot without inventorying application history."""
        authorize()
        async with self._transaction() as session:
            await self._lock(session, authorize)
            row = await session.scalar(
                select(ScavengerObservation)
                .where(ScavengerObservation.slot == 1, ScavengerObservation.owner == owner)
                .with_for_update()
            )
            result = await self._read(session, row) if row is not None else None
            authorize()
        authorize()
        return result

    async def _read(self, session: AsyncSession, row: ScavengerObservation) -> RetainedObservation:
        seed, selection = (None, None) if row.status == "deleted" else _payloads(row)
        observation = _observation(row)
        if row.status not in {"reserved", "bound", "committed", "deleted"}:
            reason = "application_custody"
            raise ScavengerRefused(reason)
        disposition = await self._disposition(session, row)
        return RetainedObservation(
            admission_id=row.id,
            request_digest=row.request_digest,
            status=cast("Literal['reserved', 'bound', 'committed', 'deleted']", row.status),
            run_id=disposition.run_id,
            seed=seed,
            initial_filter=selection,
            observation=observation,
            observation_digest=row.observation_digest,
            run_status=disposition.run_status,
            acquisition_status=disposition.acquisition_status,
            terminal_disposition=disposition.state,
        )

    async def delete(
        self,
        *,
        admission_id: UUID,
        owner: str,
        request_digest: str,
        observation_digest: str | None,
        authorize: Callable[[], None],
    ) -> None:
        """Atomically erase controlled payloads only after proved terminal disposition."""
        authorize()
        async with self._transaction() as session:
            await self._lock(session, authorize)
            row = await self._row(session, admission_id, owner)
            if row.request_digest != request_digest or row.observation_digest != observation_digest:
                reason = "delete_identity"
                raise ScavengerRefused(reason)
            if row.status != "deleted":
                if (await self._disposition(session, row)).state != "terminal":
                    reason = "terminal_disposition_required"
                    raise ScavengerRefused(reason)
                authorize()
                row.seed_bytes, row.filter_bytes, row.observation_bytes = (
                    None,
                    None,
                    None,
                )
                row.status, row.slot = "deleted", None
            authorize()
        authorize()

    @staticmethod
    async def _disposition(session: AsyncSession, row: ScavengerObservation) -> _Disposition:
        if row.status == "deleted":
            return _Disposition(
                run_id=row.run_id,
                run_status=None,
                acquisition_status=None,
                state="terminal",
            )
        runs = list(
            await session.scalars(
                select(Run)
                .where(
                    Run.id == row.run_id
                    if row.run_id is not None
                    else Run.intent["admitted_scout"]["consumer"]["application_admission_id"].astext == str(row.id)
                )
                .with_for_update()
            )
        )
        if len(runs) > 1 or (row.run_id is not None and len(runs) != 1):
            reason = "run_custody"
            raise ScavengerRefused(reason)
        if not runs:
            return _Disposition(run_id=None, run_status=None, acquisition_status=None, state="terminal")
        run = runs[0]
        deliveries = list(await session.scalars(select(RunDelivery).where(RunDelivery.run_id == run.id)))
        attempts = list(await session.scalars(select(WebcrawlerAttempt).where(WebcrawlerAttempt.run_id == run.id)))
        allowed = {"prepared", "claimed", "unknown_after_crash", "succeeded", "refused"}
        if len(attempts) > 1 or any(a.status not in allowed for a in attempts):
            reason = "scout_custody"
            raise ScavengerRefused(reason)
        try:
            run_status = RunStatus(run.status)
        except ValueError:
            reason = "run_custody"
            raise ScavengerRefused(reason) from None
        acquisition = cast("AttemptStatus", attempts[0].status) if attempts else None
        state: Literal["pending", "unknown", "terminal"] = "pending"
        if acquisition == "unknown_after_crash" or (acquisition == "claimed" and run_status in TERMINAL_STATUSES):
            state = "unknown"
        elif run_status in TERMINAL_STATUSES and deliveries and all(d.state == "settled" for d in deliveries):
            state = "terminal"
        return _Disposition(
            run_id=run.id,
            run_status=run_status,
            acquisition_status=acquisition,
            state=state,
        )
