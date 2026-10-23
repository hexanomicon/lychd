"""Opt-in synthetic offline recorder; no application boot, transport or peer grant.

The host pins expected binding, Run and policy independently of the supplied Cut.
Only this owner may consume a fresh database claim and create a completion. The
final current-authority/fence check and concrete recorder handoff do not yield.
"""

from __future__ import annotations

import asyncio
import time
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lychd.db.privacy import DbDisclosureStore
from lychd.domain.cortex.cancellation import RunEffectFence
from lychd.domain.privacy.contracts import (
    MAX_CANDIDATE_BYTES,
    CutBinding,
    PreparationPolicy,
    PreparedCut,
    PrivacyRefused,
    WireProjection,
    canonical_bytes,
    digest,
)
from lychd.domain.privacy.disclosure import (
    DisclosureError,
    DisclosureLimits,
    DisclosurePreparation,
    DisclosureRunBinding,
    DisclosureSnapshot,
    FreshDisclosureClaim,
    RecordingCompletion,
    refuse,
)
from lychd.domain.privacy.preparation import CutAuthority
from lychd.domain.privacy.verification import checked

_MAX_RECORDS = 1024
_RECEIPT_COUNT = 2
_MAX_PREPARATIONS = 16


class SyntheticExportAuthority:
    """Explicit test-profile host authority, never peer enrollment or normal egress.

    Construct from independently chosen host facts before preparing the Cut. A
    changed generation, policy, binding or revocation refuses old preparation.
    """

    def __init__(
        self,
        *,
        host_id: UUID,
        binding: CutBinding,
        run: DisclosureRunBinding,
        policy: PreparationPolicy,
        configuration_digest: str,
        generation: int = 0,
    ) -> None:
        """Pin independently selected synthetic facts before accepting Cut evidence."""
        self.host_id = host_id
        self.binding = checked(binding)
        self.run = checked(run)
        self.policy = checked(policy)
        self.configuration_digest = configuration_digest
        self.generation = generation
        self.revoked = False
        if self.binding.consumer_kind != "export" or self.binding.run_id != self.run.run_id:
            refuse("binding")

    def authorize(self, preparation: DisclosurePreparation) -> None:
        if (
            self.revoked
            or preparation.host_id != self.host_id
            or preparation.configuration_digest != self.configuration_digest
            or preparation.authority_generation != self.generation
            or preparation.cut.plan.binding != self.binding
            or preparation.run != self.run
            or preparation.cut.plan.policy_digest != digest(self.policy)
        ):
            refuse("authority")
        if not preparation.cut.issued_at <= int(time.time()) < preparation.cut.expires_at:
            refuse("expiry")


class RecordingSink:
    """Concrete bounded synchronous in-memory witness receiving only candidate bytes."""

    def __init__(self, *, max_records: int = 16, max_bytes: int = MAX_CANDIDATE_BYTES) -> None:
        """Set finite local witness capacity without a destination or callback."""
        if (
            type(max_records) is not int
            or type(max_bytes) is not int
            or not 1 <= max_records <= _MAX_RECORDS
            or not 1 <= max_bytes <= MAX_CANDIDATE_BYTES
        ):
            refuse("contract")
        self._max_records = max_records
        self._max_bytes = max_bytes
        self._records: list[bytes] = []
        self._size = 0

    @property
    def records(self) -> tuple[bytes, ...]:
        return tuple(self._records)

    def record(self, candidate: bytes) -> None:
        """Append one immutable exact payload or refuse before appending."""
        if (
            type(candidate) is not bytes
            or len(self._records) >= self._max_records
            or len(candidate) > self._max_bytes - self._size
        ):
            refuse("capacity")
        self._records.append(candidate)
        self._size += len(candidate)


class PrivacyDisclosureService:
    """Same-loop one-shot recording owner and durable store assembly."""

    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        *,
        authority: SyntheticExportAuthority,
        cut_authority: CutAuthority,
        limits: DisclosureLimits,
        fence: RunEffectFence,
        sink: RecordingSink,
    ) -> None:
        """Own one concrete recorder and one loop for this synthetic export profile."""
        if (
            type(authority) is not SyntheticExportAuthority
            or type(sink) is not RecordingSink
            or type(cut_authority) is not CutAuthority
            or type(fence) is not RunEffectFence
        ):
            refuse("contract")
        self._loop = asyncio.get_running_loop()
        self._authority, self._cuts, self._fence, self._sink = authority, cut_authority, fence, sink
        self._prepared: dict[str, PreparedCut] = {}
        self._completions: dict[UUID, tuple[FreshDisclosureClaim, RecordingCompletion, bytes]] = {}
        self.store = DbDisclosureStore(factory, self, limits, self)

    def _require_loop(self) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            refuse("claim")
        if loop is not self._loop:
            refuse("claim")

    def _verify(self, preparation: DisclosurePreparation, prepared: PreparedCut) -> None:
        try:
            if (
                type(preparation) is not DisclosurePreparation
                or type(prepared) is not PreparedCut
                or type(prepared.candidate) is not bytes
            ):
                refuse("contract")
            preparation, prepared = checked(preparation), checked(prepared)
            self._authority.authorize(preparation)
            cut = preparation.cut
            if (
                prepared.cut != cut
                or len(prepared.candidate) != preparation.candidate_size
                or prepared.verification != cut.verification
                or digest(prepared.receipts) != cut.receipt_chain_digest
                or len(prepared.receipts) != _RECEIPT_COUNT
                or digest(prepared.receipts[-1]) != cut.terminal_receipt_digest
                or canonical_bytes(WireProjection.model_validate_json(prepared.candidate)) != prepared.candidate
            ):
                refuse("binding")
            self._cuts.verify_seal(
                cut, prepared.candidate, cut.plan, self._authority.binding, self._authority.policy, now=int(time.time())
            )
        except DisclosureError:
            raise
        except (PrivacyRefused, ValueError, TypeError, RecursionError):
            refuse("binding")

    def authorize(self, preparation: DisclosurePreparation) -> None:
        """Require this owner's verified preparation as well as current host facts."""
        self._require_loop()
        prepared = self._prepared.get(preparation.digest)
        if prepared is None:
            refuse("authority")
        self._verify(preparation, prepared)

    async def prepare(self, prepared: PreparedCut, *, request_id: UUID, transmission_id: UUID) -> DisclosureSnapshot:
        self._require_loop()
        try:
            if type(prepared) is not PreparedCut or type(prepared.candidate) is not bytes:
                refuse("contract")
            prepared = checked(prepared)
            preparation = DisclosurePreparation(
                request_id=request_id,
                transmission_id=transmission_id,
                host_id=self._authority.host_id,
                configuration_digest=self._authority.configuration_digest,
                authority_generation=self._authority.generation,
                run=self._authority.run,
                cut=prepared.cut,
                candidate_size=len(prepared.candidate),
            )
            self._verify(preparation, prepared)
        except DisclosureError:
            raise
        except (ValueError, TypeError):
            refuse("contract")
        if preparation.digest not in self._prepared and len(self._prepared) >= _MAX_PREPARATIONS:
            refuse("capacity")
        self._prepared[preparation.digest] = prepared
        return await self.store.prepare(preparation)

    async def claim(self, preparation: DisclosurePreparation) -> FreshDisclosureClaim | DisclosureSnapshot:
        self._require_loop()
        return await self.store.claim(preparation)

    async def record(self, claim: FreshDisclosureClaim) -> RecordingCompletion:
        """Consume first, await retained checks, then check and record without yielding."""
        self._require_loop()
        self.store.consume(claim)
        outcome: Literal["recorded", "refused", "unknown"] = "refused"
        try:
            await self.store.check_claim(claim)
            self.authorize(claim.preparation)
            if self._fence.reason(str(claim.preparation.run.run_id), claim.preparation.run.enqueue_seq) is not None:
                refuse("fenced")
            prepared = self._prepared[claim.preparation.digest]
            # This concrete call and its preceding checks share one loop turn.
            outcome = "unknown"
            self._sink.record(prepared.candidate)
            outcome = "recorded"
        except BaseException:  # noqa: BLE001 - suppress foreign diagnostics at the privacy boundary
            return self._complete(claim, outcome)
        return self._complete(claim, outcome)

    def _complete(
        self, claim: FreshDisclosureClaim, outcome: Literal["recorded", "refused", "unknown"]
    ) -> RecordingCompletion:
        completion = RecordingCompletion(uuid4(), claim.preparation.transmission_id, claim.claim_id, outcome)
        self._completions[claim.claim_id] = claim, completion, completion.canonical_bytes()
        return completion

    def verify_completion(self, claim: FreshDisclosureClaim, completion: RecordingCompletion) -> None:
        self._require_loop()
        if type(claim) is not FreshDisclosureClaim or type(completion) is not RecordingCompletion:
            refuse("claim")
        owned = self._completions.get(claim.claim_id)
        if (
            type(claim) is not FreshDisclosureClaim
            or type(completion) is not RecordingCompletion
            or owned is None
            or owned[0] is not claim
            or owned[1] is not completion
            or completion.claim_id != claim.claim_id
            or completion.transmission_id != claim.preparation.transmission_id
        ):
            refuse("claim")
        try:
            if completion.canonical_bytes() != owned[2]:
                refuse("claim")
        except (ValueError, TypeError):
            refuse("claim")

    async def settle(self, claim: FreshDisclosureClaim, completion: RecordingCompletion) -> DisclosureSnapshot:
        return await self.store.settle(claim, completion)
