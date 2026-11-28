"""Owned Webcrawler acquisition, durable settlement and transient workflow handoff.

One composition instance serves the HTTP cancellation boundary and the workers
on the same control loop. Persisted facts never reconstruct a live material
handle, network gate or execution permit.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import weakref
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from functools import cache
from typing import TYPE_CHECKING, Any, Literal, overload
from uuid import UUID, uuid4, uuid5

from lychd.domain.cortex.cancellation import RunEffectFence
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.scout.attempts import (
    NewScoutClaim,
    ScoutAttemptSnapshot,
    ScoutFeedPreparation,
    ScoutPreparation,
    ScoutSettlement,
    ScoutStoreError,
)
from lychd.domain.scout.authority import NetworkGateSnapshot, ScoutAction, ScoutHostAuthorizer, ScoutNetworkAuthority
from lychd.domain.scout.destination import preflight_destination
from lychd.domain.scout.extraction import ExtractedFeed, ExtractedText, ExtractionCode, ExtractionError
from lychd.domain.scout.transport import FetchCode, FetchError
from lychd.domain.webcrawler.feed import WebcrawlerFeedBinding, WebcrawlerFeedMaterial, WebcrawlerFeedProfile
from lychd.domain.webcrawler.profile import (
    WebcrawlerBinding,
    WebcrawlerMaterial,
    WebcrawlerProfile,
    WebcrawlerReviewRef,
    WebcrawlerWorkflowCode,
    WebcrawlerWorkflowError,
)
from lychd.domain.webcrawler.review import webcrawler_review
from lychd.system.scout_worker import (
    RSS_MAX_ELEMENTS,
    RSS_MAX_ITEMS,
    RSS_MEDIA,
    RSS_PROFILE,
    RSS_STRATEGY,
    RSS_TRANSFORMATIONS,
)
from lychd.system.services.scout_dns import ResolverEndpoint
from lychd.system.services.scout_extraction import (
    ExtractionLifecycle,
    ScoutExtractionRuntime,
    extract_rss_feed,
    extract_static_text,
)
from lychd.system.services.scout_fetch import AcquiredText, FetchObservation, fetch_rss_feed, fetch_static_page

if TYPE_CHECKING:
    from lychd.agents.workflows.base import Workflow
    from lychd.db.webcrawler import DbWebcrawlerAttemptStore
    from lychd.domain.codex.ledger import ConsentLedger
    from lychd.domain.cortex.ledger import RunLedger
    from lychd.domain.cortex.runs import RunRecord
    from lychd.domain.scout.authority import CurrentNetworkGate


def extraction_metadata(extraction: ExtractedText | ExtractedFeed) -> dict[str, object]:
    """Positively select mechanism metadata, never source content or future fields.

    The legacy text values keep their exact existing metadata encoding. Their
    extraction owner, not this projection, validates the worker return. The new
    feed branch additionally closes its first profile before any durable use.
    Neither a shaped extraction nor these facts confer actual material custody.
    """
    if type(extraction) is ExtractedText:
        return {
            "media_type": extraction.media_type,
            "source_digest": extraction.source_digest,
            "record_digest": extraction.record_digest,
            "text_digest": extraction.text_digest,
            "strategy": extraction.strategy,
            "transformations": extraction.transformations,
            "extractor": extraction.extractor,
        }
    if type(extraction) is not ExtractedFeed:
        raise ExtractionError(ExtractionCode.PROTOCOL)
    if (
        extraction.extractor != RSS_PROFILE
        or type(extraction.media_type) is not str
        or extraction.media_type not in RSS_MEDIA
        or extraction.strategy != RSS_STRATEGY
        or extraction.transformations != RSS_TRANSFORMATIONS
        or type(extraction.items) is not tuple
        or len(extraction.items) > RSS_MAX_ITEMS
        or type(extraction.omitted_elements) is not int
        or not 0 <= extraction.omitted_elements <= RSS_MAX_ELEMENTS
        or any(
            type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None
            for value in (extraction.source_digest, extraction.record_digest)
        )
    ):
        raise ExtractionError(ExtractionCode.PROTOCOL)
    return {
        "media_type": extraction.media_type,
        "source_digest": extraction.source_digest,
        "record_digest": extraction.record_digest,
        "strategy": extraction.strategy,
        "transformations": extraction.transformations,
        "extractor": extraction.extractor,
        "item_count": len(extraction.items),
        "omitted_elements": extraction.omitted_elements,
    }


@dataclass(frozen=True, slots=True)
class _AcquiredFeed:
    """Host-owned transient feed result before application custody admission."""

    extraction: ExtractedFeed = field(repr=False)
    observations: tuple[FetchObservation, ...] = field(repr=False)


def _validate_acquired_profile(
    binding: WebcrawlerBinding | WebcrawlerFeedBinding, acquired: AcquiredText | _AcquiredFeed
) -> None:
    """Refuse a mismatched mechanism result before success metadata can be retained."""
    if (
        type(binding) is WebcrawlerFeedBinding
        and (type(acquired) is not _AcquiredFeed or type(acquired.extraction) is not ExtractedFeed)
    ) or (
        type(binding) is WebcrawlerBinding
        and (type(acquired) is not AcquiredText or type(acquired.extraction) is not ExtractedText)
    ):
        raise ExtractionError(ExtractionCode.PROTOCOL)
    extraction_metadata(acquired.extraction)


@cache
def _bridge_profiles() -> tuple[Workflow, Workflow]:
    """Retain source-owned exact profiles without consulting live route configuration."""
    from lychd.agents.workflows import BRIDGE_CHAT_WEBCRAWLER, builtin_workflow_registry, resolve_named_workflow

    return BRIDGE_CHAT_WEBCRAWLER, resolve_named_workflow(builtin_workflow_registry(), BRIDGE_CHAT_WEBCRAWLER)


def _bridge_run_matches(run: RunRecord) -> bool:
    """Accept only an exact legacy or naming-aware public-page execution binding."""
    if run.workflow_name != "bridge_chat" or run.source != "bridge":
        return False
    legacy, named = _bridge_profiles()
    workflow = named if run.admitted_naming is not None else legacy
    if run.pattern_manifest != workflow.manifest.snapshot():
        return False
    try:
        # Reuse the profile's admitted input and naming validation before any effect.
        workflow.make_state(run.to_intent())
    except ValueError:
        return False
    return True


class WebcrawlerCompletions:
    """Keep exact owned completion objects until their durable settlement returns."""

    def __init__(self) -> None:
        """Accept no restored or caller-shaped completion as custody evidence."""
        self._owned: dict[UUID, tuple[NewScoutClaim, ScoutSettlement]] = {}

    def retain(self, claim: NewScoutClaim, settlement: ScoutSettlement) -> None:
        """Retain evidence only after the acquisition owner observes complete cleanup."""
        if claim.claim_id in self._owned:
            msg = "Webcrawler completion identity is already retained."
            raise ScoutStoreError(msg)
        self._owned[claim.claim_id] = claim, settlement

    def verify(self, claim: NewScoutClaim, settlement: ScoutSettlement) -> None:
        """Require actual owned objects, not equivalent serialized flags or counters."""
        owned = self._owned.get(claim.claim_id)
        if owned is None or owned[0] is not claim or owned[1] is not settlement:
            msg = "Webcrawler owned completion is unavailable."
            raise ScoutStoreError(msg)

    def forget(self, claim: NewScoutClaim) -> None:
        """Discard volatile evidence after the store has answered settlement."""
        self._owned.pop(claim.claim_id, None)


class WebcrawlerWorkflowService:
    """Assemble current authority, durable claims and the qualified native effects."""

    def __init__(
        self,
        *,
        store: DbWebcrawlerAttemptStore,
        completions: WebcrawlerCompletions,
        ledger: RunLedger,
        consents: ConsentLedger,
        profile: WebcrawlerProfile | WebcrawlerFeedProfile,
        capability_key: str | None,
        authorizer: ScoutHostAuthorizer,
        fence: RunEffectFence,
    ) -> None:
        """Bind one host-owned provider/profile on the actual control loop."""
        if (
            (type(profile) is WebcrawlerProfile and (type(capability_key) is not str or not capability_key.strip()))
            or (type(profile) is WebcrawlerFeedProfile and capability_key is not None)
            or type(profile) not in (WebcrawlerProfile, WebcrawlerFeedProfile)
        ):
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
        self._loop = asyncio.get_running_loop()
        self._store, self._completions = store, completions
        self._ledger, self._consents = ledger, consents
        self._profile, self._capability_key = profile, capability_key
        self._authorizer, self._fence = authorizer, fence
        self._network = ScoutNetworkAuthority(authorizer=authorizer, fence=fence)
        self._active: dict[UUID, tuple[str, asyncio.Task[AcquiredText | _AcquiredFeed]]] = {}
        self._uncertain_runs: set[str] = set()
        self._materials: dict[
            UUID,
            tuple[
                weakref.ReferenceType[WebcrawlerMaterial | WebcrawlerFeedMaterial], NewScoutClaim, WebcrawlerReviewRef
            ],
        ] = {}

    def _require_loop(self) -> None:
        if asyncio.get_running_loop() is not self._loop:
            msg = "Webcrawler workflow belongs to another control loop."
            raise RuntimeError(msg)

    async def _run(self, run_id: str, binding: WebcrawlerBinding | WebcrawlerFeedBinding) -> int:
        self._require_loop()
        run = await self._ledger.get(run_id)
        if (
            run is None
            or run.admitted_webcrawler != binding
            or binding.profile != self._profile
            or run.admitted_capability_key != self._capability_key
            or run.status is not RunStatus.RUNNING
            or self._fence.reason(run_id, run.enqueue_seq) is not None
        ):
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
        if type(binding) is WebcrawlerFeedBinding:
            consumer = binding.consumer
            if (
                run.source != "scavenger"
                or run.workflow_name != consumer.pattern
                or run.pattern_manifest.get("key") != consumer.pattern
                or run.pattern_manifest.get("revision") != consumer.pattern_revision
                or run.prompt != str(consumer.application_admission_id)
                or self._capability_key is not None
            ):
                raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
        elif type(binding) is not WebcrawlerBinding or not _bridge_run_matches(run):
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
        return run.enqueue_seq

    @staticmethod
    def _reference(snapshot: ScoutAttemptSnapshot) -> WebcrawlerReviewRef:
        return WebcrawlerReviewRef(
            attempt_id=snapshot.preparation.attempt_id,
            preparation_digest=snapshot.preparation.digest,
            consent_id=snapshot.consent_id,
            native_binding_digest=snapshot.native_binding.digest,
        )

    def _bound(
        self, snapshot: ScoutAttemptSnapshot, run_id: str, binding: WebcrawlerBinding | WebcrawlerFeedBinding
    ) -> None:
        p = snapshot.preparation
        if type(binding) is WebcrawlerFeedBinding:
            if (
                type(p) is not ScoutFeedPreparation
                or p.consumer != binding.consumer
                or p.expires_at != binding.expires_at
            ):
                raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
        elif type(binding) is not WebcrawlerBinding or type(p) is not ScoutPreparation:
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
        if (
            str(p.run_id) != run_id
            or p.request_id != binding.request_id
            or p.declaration != binding.declaration
            or p.configuration_digest != binding.profile.configuration_digest
            or p.capability_key != self._capability_key
        ):
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)

    async def prepare(self, *, run_id: str, binding: WebcrawlerBinding | WebcrawlerFeedBinding) -> WebcrawlerReviewRef:
        """Prepare once; a duplicate reads the original immutable review and expiry."""
        enqueue_seq = await self._run(run_id, binding)
        previous = await self._store.read_request(binding.request_id)
        self._require_unfenced(run_id, enqueue_seq)
        if previous is not None:
            self._bound(previous, run_id, binding)
            self._authorizer.require_current(ScoutAction.REVIEW, previous.preparation)
            return self._reference(previous)
        retained = await self._store.read_run_binding(UUID(run_id))
        self._require_unfenced(run_id, enqueue_seq)
        p, d = self._profile, binding.declaration
        fields: dict[str, Any] = {
            "request_id": binding.request_id,
            "attempt_id": uuid5(binding.request_id, f"scout:{run_id}"),
            "run_id": UUID(run_id),
            "enqueue_seq": retained.enqueue_seq,
            "workflow_name": retained.workflow_name,
            "sigil_name": retained.sigil_name,
            "capability_key": self._capability_key,
            "pattern_digest": retained.pattern_digest,
            "intent_digest": retained.intent_digest,
            "subject": d.subject,
            "authentication_generation": d.authentication_generation,
            "declaration": d,
            "url": d.url,
            "provider_id": p.provider_id,
            "profile": p.profile,
            "binding_digest": p.binding_digest,
            "configuration_digest": p.configuration_digest,
            "resolver_address": p.resolver_address,
            "resolver_port": p.resolver_port,
            "resolver_custody_statement": p.resolver_custody_statement,
            "resolver_custody_digest": p.resolver_custody_digest,
            "purpose": d.purpose,
            "policy_revision": p.policy_revision,
            "revocation_generation": p.revocation_generation,
            "expires_at": d.declared_at + timedelta(seconds=p.review_ttl_seconds),
            "allowance": p.allowance,
        }
        if type(binding) is WebcrawlerFeedBinding:
            fields["expires_at"] = binding.expires_at
            preparation = ScoutFeedPreparation(**fields, consumer=binding.consumer)
        else:
            preparation = ScoutPreparation(**fields)
        native, document = webcrawler_review(preparation)
        return self._reference(await self._store.prepare(preparation, native, document.canonical_bytes()))

    def _require_unfenced(self, run_id: str, enqueue_seq: int) -> None:
        if self._fence.reason(run_id, enqueue_seq) is not None:
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)

    async def _review(
        self, run_id: str, binding: WebcrawlerBinding | WebcrawlerFeedBinding, review: WebcrawlerReviewRef
    ) -> tuple[ScoutAttemptSnapshot, int]:
        enqueue_seq = await self._run(run_id, binding)
        snapshot = await self._store.read(review.attempt_id)
        self._bound(snapshot, run_id, binding)
        if self._reference(snapshot) != review:
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
        self._authorizer.require_current(ScoutAction.REVIEW, snapshot.preparation)
        self._require_unfenced(run_id, enqueue_seq)
        return snapshot, enqueue_seq

    async def consent(
        self, *, run_id: str, binding: WebcrawlerBinding | WebcrawlerFeedBinding, review: WebcrawlerReviewRef
    ) -> Literal["pending", "granted", "refused"]:
        """Read exact native judgment; only the store may claim its effect."""
        snapshot, enqueue_seq = await self._review(run_id, binding, review)
        view = await self._consents.get(str(snapshot.consent_id))
        self._authorizer.require_current(ScoutAction.REVIEW, snapshot.preparation)
        self._require_unfenced(run_id, enqueue_seq)
        if view is None or view.native_binding != snapshot.native_binding or view.run_id != run_id:
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.CONSENT)
        if view.status == "pending":
            return "pending"
        return "granted" if view.status == "granted" else "refused"

    async def _acquire(
        self, claim: NewScoutClaim, gate: CurrentNetworkGate, progress: ExtractionLifecycle
    ) -> AcquiredText | _AcquiredFeed:
        remaining = min(30.0, (claim.preparation.expires_at - datetime.now(UTC)).total_seconds())
        remaining = min(remaining, 30.0 - (datetime.now(UTC) - claim.committed_at).total_seconds())
        if remaining <= 0:
            raise FetchError(FetchCode.TIMEOUT)
        deadline = time.monotonic() + remaining
        try:
            async with asyncio.timeout(remaining):
                p = self._profile
                candidate = preflight_destination(claim.preparation.url)
                resolver = ResolverEndpoint(p.resolver_address, p.resolver_port)
                runtime = ScoutExtractionRuntime(p.bwrap, p.python_root, p.libraries)
                if type(claim.preparation) is ScoutFeedPreparation:
                    if type(p) is not WebcrawlerFeedProfile:
                        raise FetchError(FetchCode.CONFIG)
                    feed = await fetch_rss_feed(
                        candidate, resolver=resolver, gate=gate, ca_file=p.ca_file, deadline=deadline
                    )
                    self._authorizer.require_current(ScoutAction.EXTRACT, claim.preparation)
                    if self._fence.reason(str(claim.preparation.run_id), claim.enqueue_seq) is not None:
                        raise FetchError(FetchCode.EGRESS)
                    extracted_feed = await extract_rss_feed(
                        feed.body, media_type=feed.media_type, runtime=runtime, lifecycle=progress
                    )
                    return _AcquiredFeed(extracted_feed, feed.observations)
                if type(p) is not WebcrawlerProfile:
                    raise FetchError(FetchCode.CONFIG)
                page = await fetch_static_page(
                    candidate, resolver=resolver, gate=gate, ca_file=p.ca_file, deadline=deadline
                )
                self._authorizer.require_current(ScoutAction.EXTRACT, claim.preparation)
                if self._fence.reason(str(claim.preparation.run_id), claim.enqueue_seq) is not None:
                    raise FetchError(FetchCode.EGRESS)
                extraction = await extract_static_text(
                    page.body, media_type=page.media_type, runtime=runtime, lifecycle=progress
                )
                return AcquiredText(extraction, page.observations)
        except TimeoutError:
            raise FetchError(FetchCode.TIMEOUT) from None

    async def _settle(
        self,
        claim: NewScoutClaim,
        gate: NetworkGateSnapshot,
        acquired: AcquiredText | _AcquiredFeed | None,
        progress: ExtractionLifecycle,
    ) -> ScoutAttemptSnapshot:
        child = progress.child
        if child is None:
            raise ExtractionError(ExtractionCode.CLEANUP)
        evidence = json.loads(gate.evidence_bytes)
        if acquired is not None:
            evidence["observations"] = [asdict(item) for item in acquired.observations]
            evidence["extraction"] = extraction_metadata(acquired.extraction)
        settlement = ScoutSettlement(
            receipt_id=uuid4(),
            outcome="succeeded" if acquired is not None else "refused",
            usage=gate.usage,
            handoff_evidence=json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode(),
            sockets="closed",
            child=child,
        )
        self._completions.retain(claim, settlement)
        try:
            return await self._store.settle(claim, settlement)
        finally:
            self._completions.forget(claim)

    @overload
    async def acquire(
        self, *, run_id: str, binding: WebcrawlerBinding, review: WebcrawlerReviewRef
    ) -> WebcrawlerMaterial: ...

    @overload
    async def acquire(
        self, *, run_id: str, binding: WebcrawlerFeedBinding, review: WebcrawlerReviewRef
    ) -> WebcrawlerFeedMaterial: ...

    async def acquire(
        self, *, run_id: str, binding: WebcrawlerBinding | WebcrawlerFeedBinding, review: WebcrawlerReviewRef
    ) -> WebcrawlerMaterial | WebcrawlerFeedMaterial:
        """Issue one durable claim; completed or lost material is never reacquired."""
        snapshot, _ = await self._review(run_id, binding, review)
        enqueue_seq = await self._run(run_id, binding)
        claim = await self._store.claim(
            snapshot.preparation.attempt_id, snapshot.preparation.digest, enqueue_seq=enqueue_seq
        )
        if not isinstance(claim, NewScoutClaim):
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.MATERIAL_UNAVAILABLE)
        try:
            gate = self._network.activate(claim)
        except FetchError:
            await self._store.unknown(claim)
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING) from None
        progress = ExtractionLifecycle()
        task = asyncio.create_task(self._acquire(claim, gate, progress))
        self._active[claim.claim_id] = run_id, task
        acquired: AcquiredText | _AcquiredFeed | None = None
        try:
            acquired = await task
            _validate_acquired_profile(binding, acquired)
        except BaseException as exc:
            sealed = gate.seal()
            if (
                progress.child is not None
                and isinstance(exc, (FetchError, ExtractionError, asyncio.CancelledError))
                and not (isinstance(exc, ExtractionError) and exc.code is ExtractionCode.CLEANUP)
            ):
                await self._settle(claim, sealed, None, progress)
            else:
                self._uncertain_runs.add(run_id)
                await self._store.unknown(claim)
            raise
        finally:
            self._active.pop(claim.claim_id, None)
        settled = await self._settle(claim, gate.seal(), acquired, progress)
        if settled.receipt_id is None or settled.receipt_digest is None:
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.SETTLEMENT)
        material: WebcrawlerMaterial | WebcrawlerFeedMaterial
        fields: dict[str, Any] = {
            "attempt_id": snapshot.preparation.attempt_id,
            "receipt_id": settled.receipt_id,
            "receipt_digest": settled.receipt_digest,
            "requested_url": snapshot.preparation.url,
            "contacted_url": acquired.observations[-1].candidate.normalized_url,
            "acquired_at": datetime.now(UTC),
            "extraction": acquired.extraction,
        }
        if type(binding) is WebcrawlerFeedBinding:
            material = WebcrawlerFeedMaterial(**fields, consumer=binding.consumer)
        else:
            material = WebcrawlerMaterial(**fields)
        self._materials[material.receipt_id] = weakref.ref(material), claim, review
        return material

    def authorize_consume(
        self,
        *,
        run_id: str,
        binding: WebcrawlerBinding,
        review: WebcrawlerReviewRef,
        material: WebcrawlerMaterial,
        capability_key: str,
    ) -> None:
        """Check actual transient identity and current authority immediately before use."""
        self._require_loop()
        if (
            type(binding) is not WebcrawlerBinding
            or type(material) is not WebcrawlerMaterial
            or type(self._profile) is not WebcrawlerProfile
            or type(capability_key) is not str
            or not capability_key.strip()
        ):
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
        retained = self._materials.get(material.receipt_id)
        if retained is None or retained[0]() is not material:
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.MATERIAL_UNAVAILABLE)
        _, claim, issued_review = retained
        p = claim.preparation
        if (
            str(p.run_id) != run_id
            or p.request_id != binding.request_id
            or p.declaration != binding.declaration
            or p.configuration_digest != binding.profile.configuration_digest
            or review != issued_review
            or p.digest != review.preparation_digest
            or p.attempt_id != material.attempt_id
            or capability_key != p.capability_key
            or self._fence.reason(run_id, claim.enqueue_seq) is not None
        ):
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
        self._authorizer.require_current(ScoutAction.CONSUME, p)

    def authorize_feed_consume(
        self,
        *,
        run_id: str,
        binding: WebcrawlerFeedBinding,
        review: WebcrawlerReviewRef,
        material: WebcrawlerFeedMaterial,
    ) -> None:
        """Require actual issued feed identity and current use authority, not a model key."""
        self._require_loop()
        if type(binding) is not WebcrawlerFeedBinding or type(material) is not WebcrawlerFeedMaterial:
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
        retained = self._materials.get(material.receipt_id)
        if retained is None or retained[0]() is not material:
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.MATERIAL_UNAVAILABLE)
        _, claim, issued_review = retained
        p = claim.preparation
        if (
            type(p) is not ScoutFeedPreparation
            or str(p.run_id) != run_id
            or p.request_id != binding.request_id
            or p.declaration != binding.declaration
            or binding.profile != self._profile
            or p.configuration_digest != binding.profile.configuration_digest
            or p.consumer != binding.consumer
            or material.consumer != binding.consumer
            or p.expires_at != binding.expires_at
            or p.capability_key is not None
            or self._capability_key is not None
            or p.digest != review.preparation_digest
            or review.attempt_id != p.attempt_id
            or review.consent_id != claim.consent_id
            or review != issued_review
            or p.attempt_id != material.attempt_id
            or self._fence.reason(run_id, claim.enqueue_seq) is not None
        ):
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
        self._authorizer.require_current(ScoutAction.CONSUME, p)

    async def authorize_settle(
        self, *, run_id: str, binding: WebcrawlerBinding, review: WebcrawlerReviewRef, receipt_id: UUID | None
    ) -> None:
        """Authorize retained page-answer projection, never a feed application's result."""
        if type(binding) is not WebcrawlerBinding or type(self._profile) is not WebcrawlerProfile:
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)
        snapshot, _ = await self._review(run_id, binding, review)
        if receipt_id is not None and (snapshot.status != "succeeded" or snapshot.receipt_id != receipt_id):
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.SETTLEMENT)
        self._authorizer.require_current(ScoutAction.CONSUME, snapshot.preparation)

    def fence(self, run_id: str, reason: str) -> None:
        """Fence before HTTP cancellation performs its first awaited operation."""
        self._fence.fence(run_id, reason)

    def fence_claim(self, run_id: str, enqueue_seq: int, reason: str) -> None:
        """Fence one failed worker without withdrawing a successor's authority."""
        self._fence.fence_claim(run_id, enqueue_seq, reason)

    def fence_all(self, reason: str) -> None:
        """Permanently refuse future handoffs before process draining begins."""
        self._fence.fence_all(reason)

    async def contain(self, run_id: str) -> None:
        """Cancel and await every owned acquisition for this Run."""
        self._require_loop()
        tasks = tuple(task for owner, task in self._active.values() if owner == run_id)
        for task in tasks:
            task.cancel()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        if run_id in self._uncertain_runs or any(
            isinstance(result, BaseException)
            and (
                not isinstance(result, (FetchError, ExtractionError, asyncio.CancelledError))
                or (isinstance(result, ExtractionError) and result.code is ExtractionCode.CLEANUP)
            )
            for result in results
        ):
            msg = "Webcrawler owned acquisition cleanup remains uncertain."
            raise RuntimeError(msg)

    async def contain_all(self) -> None:
        """Drain all currently owned acquisitions, retaining uncertainty as failure."""
        self._require_loop()
        runs = {run_id for run_id, _ in self._active.values()} | self._uncertain_runs
        await asyncio.gather(*(self.contain(run_id) for run_id in runs))

    async def reconcile_before(self, cutoff: datetime) -> int:
        """Retain crash uncertainty and reservations before workers may resume."""
        return await self._store.reconcile_before(cutoff)
