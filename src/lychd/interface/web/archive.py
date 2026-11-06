"""Explicit local public-note intake, lifecycle, and receipt operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from litestar import Controller, Request, get, post
from litestar.datastructures import State
from litestar.exceptions import NotFoundException, ValidationException
from litestar.params import FromPath, FromQuery
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from lychd.agents.workflows import WorkflowRegistry, resolve_named_workflow
from lychd.agents.workflows.archive_chat import ARCHIVE_ANSWER_PURPOSE, BRIDGE_CHAT_ARCHIVE, archive_recall_request
from lychd.agents.workflows.base import pattern_snapshot_is_valid
from lychd.domain.archive import (
    ArchiveProfile,
    ArchiveRefused,
    NoteListPage,
    NoteListRequest,
    NoteProposal,
    NoteRecord,
    RecallProjection,
    RecallReceipt,
    RecallRequest,
)
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.web.contracts import ArchiveBridgeDefault, ArchiveRunRecall, BridgeComposer
from lychd.interface.web.archive_response import archive_result, require_archive_access

if TYPE_CHECKING:
    from lychd.domain.cortex.runs import RunRecord


def _archive_run_manifest(record: RunRecord, state: State) -> dict[str, Any] | None:
    """Require exact registered naming execution while preserving the legacy binding."""
    if record.pattern_manifest["revision"] == "3":
        return BRIDGE_CHAT_ARCHIVE.manifest.snapshot() if record.admitted_naming is None else None
    registry = getattr(getattr(state.services, "run_engine", None), "workflows", None)
    if not isinstance(registry, WorkflowRegistry) or record.admitted_naming is None:
        return None
    try:
        workflow = resolve_named_workflow(registry, BRIDGE_CHAT_ARCHIVE)
    except ValueError:
        return None
    return workflow.manifest.snapshot()


class ArchiveLifecycleIntent(BaseModel):
    """Compare-and-set one explicit lifecycle transition."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    expected_version: int = Field(ge=1)


class ArchiveResolveIntent(BaseModel):
    """Resolve only the exact retained selection supplied by its receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    receipt_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class ArchiveController(Controller):
    """Each operation enters the same current-authority service used by Graph."""

    path = "/api/v1/archive"
    guards = (requires_scopes("altar:read"),)

    @get("/profile", name="archive:profile", operation_id="getArchiveProfile")
    async def profile(self, request: Request[Any, Any, Any], state: State) -> ArchiveProfile:
        """Discover authorized configuration; this is no storage or readiness probe."""
        service, subject = require_archive_access(request, state)
        return await archive_result(service.discover_profile(subject, purpose="archive:manage"))

    @get("/bridge-default", name="archive:bridge-default", operation_id="getArchiveBridgeDefault")
    async def bridge_default(self, request: Request[Any, Any, Any], state: State) -> ArchiveBridgeDefault:
        """Compare current admission configuration without inspecting another profile or Run."""
        service, subject = require_archive_access(request, state)
        profile = await archive_result(service.discover_profile(subject, purpose="archive:manage"))
        engine = getattr(state.services, "run_engine", None)
        registry = getattr(engine, "workflows", None)
        current = None
        if isinstance(registry, WorkflowRegistry):
            try:
                workflow = registry.default
            except RuntimeError:
                # An unavailable admission binding remains unknown, not a catalogue fallback.
                pass
            else:
                current = BridgeComposer(
                    pattern_id=workflow.manifest.key, pattern_revision=workflow.manifest.revision, guidance=None
                )
        binding = getattr(engine, "bridge_archive", None)
        matches = None
        if current is not None:
            matches = (
                (current.pattern_id, current.pattern_revision) == ("bridge_chat", "3")
                and isinstance(binding, ArchiveProfile)
                and binding == profile
            )
        return ArchiveBridgeDefault(current_default=current, requests_profile=matches)

    @get("/runs/{run_id:uuid}/recall", name="archive:run-recall", operation_id="getArchiveRunRecall")
    async def run_recall(
        self, run_id: FromPath[UUID], request: Request[Any, Any, Any], state: State
    ) -> ArchiveRunRecall:
        """Inspect exact retained selection after Context release, without proving consumption."""
        service, subject = require_archive_access(request, state)
        profile = await archive_result(service.discover_profile(subject, purpose="archive:manage"))
        record = await state.services.ledger.get(str(run_id))
        # Ledger preparation may await; recheck even for absence or unsupported history.
        await archive_result(service.discover_profile(subject, purpose="archive:manage"))
        if record is None:
            raise NotFoundException(detail="Unknown run.")
        snapshot = record.pattern_manifest
        if record.run_id != str(run_id) or not pattern_snapshot_is_valid(snapshot):
            return await archive_result(_refuse_run_binding())
        if snapshot["key"] != "bridge_chat" or snapshot["revision"] not in {"3", "3-naming1"}:
            return ArchiveRunRecall(run_id=run_id, status="not_applicable", receipt=None)
        if (
            snapshot != _archive_run_manifest(record, state)
            or record.workflow_name != BRIDGE_CHAT_ARCHIVE.name
            or record.source != "bridge"
            or not isinstance(record.admitted_capability_key, str)
            or not record.admitted_capability_key.strip()
            or record.admitted_archive != profile
            or getattr(getattr(state.services, "run_engine", None), "bridge_archive", None) != profile
        ):
            return await archive_result(_refuse_run_binding())
        try:
            expected = archive_recall_request(profile=profile, run_id=record.run_id, prompt=record.prompt)
        except ValueError:
            return await archive_result(_refuse_run_binding())
        receipt = await archive_result(
            service.inspect_recall(subject, expected, recall_purpose=ARCHIVE_ANSWER_PURPOSE, purpose="archive:manage")
        )
        return ArchiveRunRecall(
            run_id=run_id, status="recorded" if receipt is not None else "not_recorded", receipt=receipt
        )

    @get("/notes", name="archive:list", operation_id="listArchiveNotes")
    async def list_notes(
        self,
        request: Request[Any, Any, Any],
        state: State,
        limit: FromQuery[int] = 50,
        source_key: FromQuery[str | None] = None,
        cursor: FromQuery[str | None] = None,
    ) -> NoteListPage:
        """Inspect a finite metadata page, including archived and revoked records."""
        service, subject = require_archive_access(request, state)
        try:
            query = NoteListRequest(
                namespace_id=service.profile.namespace_id, limit=limit, source_key=source_key, cursor=cursor
            )
        except ValidationError:
            raise ValidationException(detail="Invalid Archive metadata query.") from None
        return await archive_result(service.list_notes(subject, query, purpose="archive:manage"))

    @get("/notes/{record_id:uuid}", name="archive:get", operation_id="getArchiveNote")
    async def get_note(self, record_id: FromPath[UUID], request: Request[Any, Any, Any], state: State) -> NoteRecord:
        """Refresh one exact metadata identity without replaying a lifecycle effect."""
        service, subject = require_archive_access(request, state)
        return await archive_result(service.get_note(subject, record_id, purpose="archive:manage"))

    @post("/notes", name="archive:admit", operation_id="admitArchiveNote")
    async def admit(self, data: NoteProposal, request: Request[Any, Any, Any], state: State) -> NoteRecord:
        """Retain an attributed candidate; intake does not make it recall-eligible."""
        service, subject = require_archive_access(request, state)
        return await archive_result(service.admit(subject, data, purpose="archive:manage"))

    @post("/notes/{record_id:uuid}/promote", name="archive:promote", operation_id="promoteArchiveNote")
    async def promote(
        self,
        record_id: FromPath[UUID],
        data: ArchiveLifecycleIntent,
        request: Request[Any, Any, Any],
        state: State,
    ) -> NoteRecord:
        """Explicitly promote this candidate and supersede its prior promoted revision."""
        service, subject = require_archive_access(request, state)
        return await archive_result(
            service.promote(subject, record_id, expected_version=data.expected_version, purpose="archive:manage")
        )

    @post("/notes/{record_id:uuid}/archive", name="archive:archive", operation_id="archiveNote")
    async def archive(
        self,
        record_id: FromPath[UUID],
        data: ArchiveLifecycleIntent,
        request: Request[Any, Any, Any],
        state: State,
    ) -> NoteRecord:
        """Remove a promoted revision from ordinary recall while retaining its content."""
        service, subject = require_archive_access(request, state)
        return await archive_result(
            service.archive(subject, record_id, expected_version=data.expected_version, purpose="archive:manage")
        )

    @post("/notes/{record_id:uuid}/revoke", name="archive:revoke", operation_id="revokeArchiveNote")
    async def revoke(
        self,
        record_id: FromPath[UUID],
        data: ArchiveLifecycleIntent,
        request: Request[Any, Any, Any],
        state: State,
    ) -> NoteRecord:
        """Remove controlled content and retain the source-revision tombstone."""
        service, subject = require_archive_access(request, state)
        return await archive_result(
            service.revoke(subject, record_id, expected_version=data.expected_version, purpose="archive:manage")
        )

    @post("/recalls", name="archive:recall", operation_id="recallArchiveNotes")
    async def recall(self, data: RecallRequest, request: Request[Any, Any, Any], state: State) -> RecallReceipt:
        """Retain bounded lexical selection evidence without source text in the receipt."""
        service, subject = require_archive_access(request, state)
        return await archive_result(service.recall(subject, data, purpose="archive:answer"))

    @post("/recalls/{receipt_id:uuid}/resolve", name="archive:resolve", operation_id="resolveArchiveRecall")
    async def resolve(
        self,
        receipt_id: FromPath[UUID],
        data: ArchiveResolveIntent,
        request: Request[Any, Any, Any],
        state: State,
    ) -> RecallProjection:
        """Disclose an exact receipt only while current authority and lifecycle permit it."""
        service, subject = require_archive_access(request, state)
        return await archive_result(
            service.resolve_receipt(subject, receipt_id, data.receipt_digest, purpose="archive:answer")
        )


async def _refuse_run_binding() -> ArchiveRunRecall:
    """Project only a stable refusal code, never retained prompt or admission bytes."""
    msg = "run_recall_binding"
    raise ArchiveRefused(msg)
