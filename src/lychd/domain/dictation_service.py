"""At-most-once private dictation orchestration over explicit injected ports.

Claim commit precedes the sole invocation. Timed-out or cancelled local waits
remain unknown; no surviving task can settle a result on its own.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal, Protocol
from uuid import UUID

from lychd.domain.artifacts import ArtifactRef
from lychd.domain.dictation import (
    DictationAttemptIdentity,
    DictationAttemptSummary,
    DictationCorrection,
    DictationCorrectionRequest,
    DictationDiscovery,
    DictationError,
    DictationModel,
    DictationProfile,
    DictationReason,
    DictationRequest,
    DictationResult,
    DictationTranscriberError,
    decode_audio,
)
from lychd.domain.dictation_store import DictationStore
from lychd.domain.speech_probe import content_digest


class DictationTranscriber(Protocol):
    """An explicit profile-bound adapter; no ambient transport discovery."""

    profile: DictationProfile

    async def transcribe(self, source: ArtifactRef, content: bytes, language: str) -> str: ...


class DictationDeleted(DictationModel):
    attempt_id: UUID
    status: Literal["deleted"] = "deleted"


def _now() -> datetime:
    return datetime.now(UTC)


def _consume(task: asyncio.Task[str]) -> None:
    if not task.cancelled():
        task.exception()


class DictationService:
    """Own the private store even while new transcription is unconfigured."""

    def __init__(
        self,
        *,
        store: DictationStore,
        profile: DictationProfile | None,
        transcriber: DictationTranscriber | None,
        now: Callable[[], datetime] = _now,
    ) -> None:
        """Initialize the explicit private-custody dependencies and bounds."""
        self.store = store
        self.profile = profile
        self.transcriber = transcriber
        self._now = now
        self._closed = False
        self._tasks: set[asyncio.Task[str]] = set()

    def _profile(self) -> DictationProfile | None:
        if self.profile is None or self._closed:
            return None
        try:
            profile = DictationProfile.model_validate_json(self.profile.model_dump_json())
            adapter = self.transcriber
            if adapter is None or DictationProfile.model_validate_json(adapter.profile.model_dump_json()) != profile:
                return None
        except (ValueError, TypeError, AttributeError):
            return None
        return profile

    def discovery(self) -> DictationDiscovery:
        profile = self._profile()
        if profile is None:
            return DictationDiscovery(reason="unconfigured" if self.profile is None else "not_qualified")
        languages = profile.transcriber_binding.model.languages
        if not languages:
            return DictationDiscovery(reason="language_unavailable")
        return DictationDiscovery(
            status="available",
            reason=None,
            profile_digest=profile.digest,
            languages=languages,
            raw_audio_retention_seconds=profile.raw_audio_retention_seconds,
            retention_seconds=profile.retention_seconds,
            max_records_per_owner=profile.max_records_per_owner,
        )

    async def transcribe(
        self,
        owner: str,
        request: DictationRequest,
        *,
        authorize: Callable[[], None],
    ) -> DictationResult:
        """Validate, claim unknown, invoke once, and settle only while current."""
        authorize()
        try:
            request = DictationRequest.model_validate(request.model_dump())
            content = decode_audio(request)
        except DictationError as error:
            return self._refused(request, error.reason)
        profile = self._profile()
        if profile is None:
            return self._refused(request, "unconfigured" if self.profile is None else "not_qualified", unavailable=True)
        if request.language not in profile.transcriber_binding.model.languages:
            return self._refused(request, "language_unavailable")
        return await self._claim_and_transcribe(owner, request, content, profile, authorize=authorize)

    async def _claim_and_transcribe(
        self,
        owner: str,
        request: DictationRequest,
        content: bytes,
        profile: DictationProfile,
        *,
        authorize: Callable[[], None],
    ) -> DictationResult:
        """Acquire dispatch only through an acknowledged fresh claim."""
        source_digest = content_digest(content)
        identity = DictationAttemptIdentity(
            owner=owner,
            attempt_id=request.attempt_id,
            source_digest=source_digest,
            profile_digest=profile.digest,
            language=request.language,
        )
        try:
            claim = await self.store.claim(identity, content, self._now(), profile)
        except DictationError as error:
            authorize()
            return self._refused(request, error.reason)
        authorize()
        if not claim.dispatch:
            if claim.record.result is None:
                return self._refused(request, "expired")
            return claim.record.result
        unknown = claim.record.result
        if unknown is None:
            return self._refused(request, "expired")
        if self._tasks:
            # Exact retries were resolved above. A new occurrence never queues
            # another local wait behind an active or cancellation-pending call.
            refused = DictationResult(
                attempt_id=identity.attempt_id,
                status="refused",
                source_digest=source_digest,
                profile_digest=profile.digest,
                language=identity.language,
                reason="capacity",
            )
            settled = await self.store.settle(identity, refused, self._now())
            authorize()
            return settled if settled is not None else self._refused(request, "expired")
        return await self._dispatch(request, content, profile, identity, unknown, authorize=authorize)

    async def _dispatch(
        self,
        request: DictationRequest,
        content: bytes,
        profile: DictationProfile,
        identity: DictationAttemptIdentity,
        unknown: DictationResult,
        *,
        authorize: Callable[[], None],
    ) -> DictationResult:
        """Wait for one invocation; only this caller may settle its result."""
        # A changed profile or shutdown cannot acquire the old claim's dispatch.
        if self._profile() != profile:
            return unknown
        source = ArtifactRef(
            artifact_id=f"bridge-dictation:{request.attempt_id}",
            digest=identity.source_digest,
            media_type="audio/wav",
            size=len(content),
            classification="private",
        )
        adapter = self.transcriber
        if adapter is None:
            return unknown

        async def invoke() -> str:
            authorize()
            if self._profile() != profile:
                msg = "refused"
                raise DictationTranscriberError(msg, "not_qualified")
            return await adapter.transcribe(source, content, request.language)

        task = asyncio.create_task(invoke())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        task.add_done_callback(_consume)
        try:
            done, _ = await asyncio.wait({task}, timeout=profile.total_timeout_seconds)
            authorize()
        except BaseException:
            task.cancel()
            raise
        if not done:
            task.cancel()
        if not done or self._profile() != profile:
            return unknown
        result = self._completed_result(task, identity, profile)
        if result is None:
            return unknown
        authorize()
        settled = await self.store.settle(identity, result, self._now())
        authorize()
        if self._profile() != profile:
            return unknown
        return settled if settled is not None else self._refused(request, "expired")

    @staticmethod
    def _completed_result(
        task: asyncio.Task[str], identity: DictationAttemptIdentity, profile: DictationProfile
    ) -> DictationResult | None:
        """Project a completed private port result without releasing diagnostics."""
        try:
            text = task.result()
            result = DictationResult(
                attempt_id=identity.attempt_id,
                status="transcribed",
                source_digest=identity.source_digest,
                profile_digest=profile.digest,
                language=identity.language,
                original_text=text,
            )
            if len(text) > profile.max_text_chars:
                return None
        except DictationTranscriberError as error:
            result = DictationResult(
                attempt_id=identity.attempt_id,
                status=error.outcome,
                source_digest=identity.source_digest,
                profile_digest=profile.digest,
                language=identity.language,
                reason=error.reason,
            )
        except asyncio.CancelledError:
            return None
        except Exception:  # noqa: BLE001 - private adapter diagnostics never cross the port
            return None
        return result

    @staticmethod
    def _refused(request: DictationRequest, reason: DictationReason, *, unavailable: bool = False) -> DictationResult:
        return DictationResult(
            attempt_id=request.attempt_id,
            status="unavailable" if unavailable else "refused",
            language=request.language,
            reason=reason,
        )

    async def get_result(self, owner: str, attempt_id: UUID) -> DictationResult | None:
        return await self.store.get_result(owner, attempt_id, self._now())

    async def correct(self, owner: str, request: DictationCorrectionRequest) -> DictationCorrection:
        return await self.store.correct(owner, request, self._now())

    async def list_corrections(self, owner: str) -> tuple[DictationCorrection, ...]:
        return await self.store.list_corrections(owner, self._now())

    async def list_attempts(self, owner: str) -> tuple[DictationAttemptSummary, ...]:
        return await self.store.list_attempts(owner, self._now())

    async def delete(self, owner: str, attempt_id: UUID) -> DictationDeleted:
        await self.store.delete(owner, attempt_id, self._now())
        # Same projection for absent/foreign/deleted, without revealing custody.
        return DictationDeleted(attempt_id=attempt_id)

    async def purge(self) -> None:
        await self.store.purge(self._now())

    async def aclose(self) -> None:
        """Fence admission and bound cleanup; never claim provider computation stopped."""
        self._closed = True
        tasks = set(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            _, pending = await asyncio.wait(tasks, timeout=5.0)
            if pending:
                msg = "Dictation local waits did not retire; shared dependencies must remain live."
                raise TimeoutError(msg)
