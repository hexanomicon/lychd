"""Explicit local application authority around Scavenger custody and transient consumption."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from uuid import UUID

from lychd.agents.router import Intent
from lychd.compositions.scavenger.schemas import (
    PROFILE,
    LiteralFilter,
    ObservationAdmission,
    ObservationDocument,
    ObserveMarketRequest,
    ScavengerRefused,
    ScavengerState,
    canonical,
    local_view,
)
from lychd.domain.codex.local_access import LocalOperatorAccess, LocalOperatorAuthentication
from lychd.domain.codex.scopes import scopes_satisfied
from lychd.domain.cortex.runs import RunDeliveryState, RunStatus
from lychd.domain.webcrawler.feed import WebcrawlerFeedBinding

if TYPE_CHECKING:
    from lychd.compositions.scavenger.ports import ObservationCommit
    from lychd.compositions.scavenger.schemas import CampaignSeed, ObservationView
    from lychd.db.scavenger import DbScavengerStore, RetainedObservation, ScavengerAdmission
    from lychd.domain.codex.sigil import Sigil
    from lychd.domain.cortex.engine import RunEngine
    from lychd.domain.scout.attempts import ScoutFeedConsumer
    from lychd.domain.webcrawler.feed import WebcrawlerFeedMaterial, WebcrawlerFeedProfile, WebcrawlerFeedWorkflowPort
    from lychd.domain.webcrawler.profile import WebcrawlerReviewRef
    from lychd.interface.web.webcrawler_feed_admission import WebcrawlerFeedAdmissionService


def _document(retained: RetainedObservation) -> ObservationDocument:
    status: Literal["reserved", "pending", "awaiting_consent", "observed", "unavailable", "unknown", "deleted"]
    if retained.status == "deleted":
        status = "deleted"
    elif retained.observation is not None:
        status = "observed"
    elif retained.terminal_disposition == "unknown":
        status = "unknown"
    elif retained.run_id is not None and retained.terminal_disposition == "terminal":
        status = "unavailable"
    elif retained.run_status is RunStatus.AWAITING_CONSENT:
        status = "awaiting_consent"
    elif retained.run_id is None:
        status = "reserved"
    else:
        status = "pending"
    view = (
        local_view(retained.observation, retained.initial_filter)
        if (retained.observation is not None and retained.initial_filter is not None)
        else None
    )
    return ObservationDocument(
        admission_id=retained.admission_id,
        request_digest=retained.request_digest,
        status=status,
        run_id=retained.run_id,
        run_status=retained.run_status,
        acquisition_status=retained.acquisition_status,
        terminal_disposition=retained.terminal_disposition,
        seed=retained.seed,
        seed_document=canonical(retained.seed).decode("utf-8") if retained.seed is not None else None,
        initial_filter=retained.initial_filter,
        observation=retained.observation,
        observation_digest=retained.observation_digest,
        view=view,
    )


class LocalScavengerPolicy:
    """One credential-backed local owner; read/delete never borrow acquisition consent."""

    def __init__(self, *, access: LocalOperatorAccess, profile: WebcrawlerFeedProfile, owner: str) -> None:
        """Pin one actual startup authority, feed configuration and application owner."""
        self.access, self.profile, self.owner = access, profile, owner

    def http(
        self, authentication: object, principal: Sigil, action: Literal["reserve", "bind", "read", "delete"]
    ) -> None:
        required = {"reserve": "runs:submit", "bind": "runs:submit", "read": "altar:read", "delete": "runs:cancel"}
        if (
            action not in required
            or not self.access.current(authentication)
            or type(authentication) is not LocalOperatorAuthentication
            or principal.name != self.owner
            or not scopes_satisfied(principal.scopes, (required[action],))
        ):
            reason = "application_authority"
            raise ScavengerRefused(reason)

    def worker(self, binding: WebcrawlerFeedBinding) -> None:
        """Attribution is usable only with the exact retained Run checked by the store."""
        if (
            binding.profile != self.profile
            or binding.declaration.subject != "local-operator"
            or not self.access.current_binding(
                binding.declaration.subject, binding.declaration.authentication_generation
            )
        ):
            reason = "application_authority"
            raise ScavengerRefused(reason)


class ScavengerService:
    """Share one application policy/store with HTTP admission and the model-free Graph."""

    def __init__(
        self, *, store: DbScavengerStore, policy: LocalScavengerPolicy, webcrawler: WebcrawlerFeedWorkflowPort
    ) -> None:
        """Inject receiving custody and the actual transient-material owner."""
        self.store, self.policy, self.webcrawler = store, policy, webcrawler

    async def submit(
        self,
        request: ObserveMarketRequest,
        *,
        authentication: object,
        principal: Sigil,
        engine: RunEngine,
        admission: WebcrawlerFeedAdmissionService,
    ) -> ObservationAdmission:
        """Reserve before admission; same-key retries never refresh an existing acquisition."""
        reserved = await self.reserve(
            request_id=request.request_id,
            seed=request.seed,
            selection=request.initial_filter,
            authentication=authentication,
            principal=principal,
        )
        if reserved.run_id is not None:
            run = await engine.ledger.get(str(reserved.run_id))
            self.policy.http(authentication, principal, "reserve")
            if run is None:
                reason = "run_custody"
                raise ScavengerRefused(reason)
            delivery = await engine.ledger.get_delivery(run.run_id, enqueue_seq=run.enqueue_seq)
            self.policy.http(authentication, principal, "reserve")
            if delivery is None:
                reason = "run_custody"
                raise ScavengerRefused(reason)
            if delivery.state is not RunDeliveryState.HELD:
                return await self._admission(run.run_id, reserved.consumer, authentication, principal, engine)
        proof = admission.declare(
            consumer=reserved.consumer,
            request_id=request.request_id,
            deadline=reserved.deadline,
            authentication=authentication,
        )

        async def retain(run_id: str) -> None:
            # A concurrent admission may have won with an earlier declaration.
            # Use its actual committed binding, never this caller's new proof.
            run = await engine.ledger.get(run_id)
            self.policy.http(authentication, principal, "bind")
            if (
                run is None
                or type(run.admitted_webcrawler) is not WebcrawlerFeedBinding
                or run.admitted_webcrawler.consumer != reserved.consumer
            ):
                reason = "run_custody"
                raise ScavengerRefused(reason)
            await self.retain_run(
                run_id=run_id, binding=run.admitted_webcrawler, authentication=authentication, principal=principal
            )

        handle = await engine.submit(
            Intent(
                session_id=f"scavenger:{request.request_id}",
                prompt=str(request.request_id),
                source="scavenger",
                sigil_name=principal.name,
                sigil_scopes=principal.scopes,
            ),
            feed_declaration=proof,
            retain_before_publish=retain,
            idempotency_key=f"scavenger:{request.request_id}",
        )
        return await self._admission(handle.run_id, reserved.consumer, authentication, principal, engine)

    async def _admission(
        self,
        run_id: str,
        consumer: ScoutFeedConsumer,
        authentication: object,
        principal: Sigil,
        engine: RunEngine,
    ) -> ObservationAdmission:
        run = await engine.ledger.get(run_id)
        self.policy.http(authentication, principal, "reserve")
        if (
            run is None
            or run.source != "scavenger"
            or run.sigil_name != self.policy.owner
            or type(run.admitted_webcrawler) is not WebcrawlerFeedBinding
            or run.admitted_webcrawler.consumer != consumer
        ):
            reason = "run_custody"
            raise ScavengerRefused(reason)
        return ObservationAdmission(
            admission_id=consumer.application_admission_id, run_id=UUID(run_id), run_status=run.status
        )

    async def current(self, *, authentication: object, principal: Sigil) -> ScavengerState:
        retained = await self.store.active(
            owner=self.policy.owner,
            authorize=lambda: self.policy.http(authentication, principal, "read"),
        )
        self.policy.http(authentication, principal, "read")
        return ScavengerState(
            configured=True, profile=PROFILE, current=_document(retained) if retained is not None else None
        )

    async def document(self, *, admission_id: UUID, authentication: object, principal: Sigil) -> ObservationDocument:
        retained = await self.read(admission_id=admission_id, authentication=authentication, principal=principal)
        self.policy.http(authentication, principal, "read")
        return _document(retained)

    async def reserve(
        self,
        *,
        request_id: UUID,
        seed: CampaignSeed,
        selection: LiteralFilter,
        authentication: object,
        principal: Sigil,
    ) -> ScavengerAdmission:
        return await self.store.reserve(
            request_id=request_id,
            owner=self.policy.owner,
            seed=seed,
            selection=selection,
            configuration_digest=self.policy.profile.configuration_digest,
            authorize=lambda: self.policy.http(authentication, principal, "reserve"),
        )

    async def retain_run(
        self,
        *,
        run_id: str,
        binding: WebcrawlerFeedBinding,
        authentication: object,
        principal: Sigil,
    ) -> None:
        await self.store.retain_run(
            run_id=UUID(run_id),
            binding=binding,
            owner=self.policy.owner,
            authorize=lambda: self.policy.http(authentication, principal, "bind"),
        )

    async def committed(self, *, run_id: str, binding: WebcrawlerFeedBinding) -> ObservationCommit | None:
        return await self.store.committed(
            run_id=UUID(run_id),
            binding=binding,
            owner=self.policy.owner,
            authorize=lambda: self.policy.worker(binding),
        )

    async def adopt(
        self,
        *,
        run_id: str,
        binding: WebcrawlerFeedBinding,
        review: WebcrawlerReviewRef,
        material: WebcrawlerFeedMaterial,
    ) -> ObservationCommit:
        def current() -> None:
            self.policy.worker(binding)
            self.webcrawler.authorize_feed_consume(run_id=run_id, binding=binding, review=review, material=material)

        return await self.store.adopt(
            run_id=UUID(run_id), binding=binding, material=material, owner=self.policy.owner, authorize=current
        )

    async def read(self, *, admission_id: UUID, authentication: object, principal: Sigil) -> RetainedObservation:
        return await self.store.read(
            admission_id=admission_id,
            owner=self.policy.owner,
            authorize=lambda: self.policy.http(authentication, principal, "read"),
        )

    async def view(
        self, *, admission_id: UUID, selection: LiteralFilter, authentication: object, principal: Sigil
    ) -> ObservationView:
        retained = await self.read(admission_id=admission_id, authentication=authentication, principal=principal)
        self.policy.http(authentication, principal, "read")
        if retained.observation is None:
            reason = "field_unavailable"
            raise ScavengerRefused(reason)
        return local_view(retained.observation, selection)

    async def delete(
        self,
        *,
        admission_id: UUID,
        request_digest: str,
        observation_digest: str | None,
        authentication: object,
        principal: Sigil,
    ) -> None:
        await self.store.delete(
            admission_id=admission_id,
            owner=self.policy.owner,
            request_digest=request_digest,
            observation_digest=observation_digest,
            authorize=lambda: self.policy.http(authentication, principal, "delete"),
        )
