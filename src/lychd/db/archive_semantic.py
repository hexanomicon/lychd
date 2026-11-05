"""Exact native cosine selection with historical receipts and current resolution fences."""

from __future__ import annotations

import math
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from pydantic import TypeAdapter
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from lychd.db.archive_generation import exact_generation
from lychd.db.archive_namespace import lock_archive_namespace
from lychd.db.models.archive import ArchiveNote, ArchiveRecall
from lychd.db.models.archive_derivation import ArchiveEmbeddingGeneration, ArchiveNoteEmbedding
from lychd.domain.animation.embeddings import (
    canonical_float32_vector,
    embedding_digest,
    embedding_vector_digest,
)
from lychd.domain.archive.contracts import ArchiveRefused, ArchiveSubject, RecordRef, digest, text_digest
from lychd.domain.archive.derivation import (
    VECTOR_DIMENSION,
    DerivationReceipt,
    DerivationRequest,
    GenerationManifest,
    GenerationRef,
)
from lychd.domain.archive.semantic import (
    SEMANTIC_POLICY,
    SemanticCoverage,
    SemanticPrepared,
    SemanticQueryExecution,
    SemanticRecallItem,
    SemanticRecallProjection,
    SemanticRecallReceipt,
    SemanticRecallRequest,
    SemanticSelection,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy.sql.selectable import CTE

    from lychd.domain.archive.ports import AuthorizationCheck


SEMANTIC_SCHEMA = 2


def _receipt(row: ArchiveRecall) -> SemanticRecallReceipt:
    try:
        schema = row.receipt.get("schema_version")
    except AttributeError:
        raise ArchiveRefused("receipt_schema") from None  # noqa: EM101 - closed safe code
    if schema != SEMANTIC_SCHEMA:
        raise ArchiveRefused("receipt_schema")  # noqa: EM101 - closed safe code
    try:
        receipt = SemanticRecallReceipt.model_validate(row.receipt)
    except ValueError:
        raise ArchiveRefused("receipt_integrity") from None  # noqa: EM101 - closed safe code
    if (
        receipt.receipt_id != row.id
        or receipt.namespace_id != row.namespace_id
        or receipt.request_id != row.request_id
        or receipt.request_digest != row.request_digest
        or receipt.receipt_digest != row.receipt_digest
    ):
        raise ArchiveRefused("receipt_integrity")  # noqa: EM101 - closed safe code
    return receipt


def _seal(values: dict[str, Any]) -> SemanticRecallReceipt:
    # Pydantic's JSON projection gives UTC timestamps their canonical Z spelling.
    canonical = TypeAdapter(dict[str, Any]).dump_python(values, mode="json")
    canonical["receipt_digest"] = digest(canonical)
    try:
        return SemanticRecallReceipt.model_validate(canonical)
    except ValueError:
        raise ArchiveRefused("receipt_integrity") from None  # noqa: EM101 - closed safe code


def _binding(
    receipt: SemanticRecallReceipt,
    manifest: GenerationManifest,
    subject: ArchiveSubject,
    request: SemanticRecallRequest,
    purpose: str,
) -> None:
    if (
        receipt.namespace_id != manifest.archive.namespace_id
        or receipt.namespace_id != request.namespace_id
        or receipt.request_id != request.request_id
        or receipt.subject != subject
        or receipt.purpose != purpose
        or receipt.profile != manifest.archive.profile
        or receipt.policy_revision != manifest.archive.policy_revision
        or receipt.retrieval_policy != SEMANTIC_POLICY
        or receipt.generation != request.generation
        or receipt.generation.manifest_digest != manifest.digest
        or receipt.run_id != request.run_id
        or receipt.request_digest != request.binding_digest(manifest, subject, purpose)
        or receipt.query_digest != text_digest(request.query)
        or receipt.max_results != request.max_results
        or receipt.char_budget != request.char_budget
        or receipt.min_cosine != request.min_cosine
        or receipt.query_execution.profile_digest != manifest.embedding.digest
        or receipt.query_execution.rendered_digest != text_digest(manifest.embedding.query_prefix + request.query)
        or receipt.query_execution.tokens > manifest.embedding.max_input_tokens
    ):
        raise ArchiveRefused("request_conflict")  # noqa: EM101 - closed safe code


def _request(manifest: GenerationManifest, request: SemanticRecallRequest, generation_id: UUID) -> None:
    if request.namespace_id != manifest.archive.namespace_id:
        raise ArchiveRefused("namespace")  # noqa: EM101 - closed safe code
    if request.generation.manifest_digest != manifest.digest or request.generation.generation_id != generation_id:
        raise ArchiveRefused("generation_binding")  # noqa: EM101 - closed safe code


def _query(
    manifest: GenerationManifest,
    request: SemanticRecallRequest,
    execution: SemanticQueryExecution,
    vector: tuple[float, ...],
) -> None:
    try:
        execution = SemanticQueryExecution.model_validate(execution.model_dump(mode="json"))
        canonical = canonical_float32_vector(vector)
        if (
            len(canonical) != VECTOR_DIMENSION
            or vector != canonical
            or abs(math.sqrt(sum(v * v for v in canonical)) - 1) > manifest.embedding.normalization_tolerance
            or execution.profile_digest != manifest.embedding.digest
            or execution.item_id != str(request.request_id)
            or execution.input_digest != text_digest(request.query)
            or execution.rendered_digest != text_digest(manifest.embedding.query_prefix + request.query)
            or execution.vector_digest != embedding_vector_digest(canonical)
            or execution.tokens > manifest.embedding.max_input_tokens
            or len((manifest.embedding.query_prefix + request.query).encode()) > manifest.embedding.max_input_bytes
        ):
            raise ValueError  # noqa: TRY301 - collapse all internal validation to one safe code
    except (ValueError, TypeError):
        raise ArchiveRefused("embedding_result") from None  # noqa: EM101 - closed safe code


def _eligible(manifest: GenerationManifest, reference: GenerationRef, version: int) -> CTE:
    """Materialize the compatible set before distance; base ANN indexes cannot rank it."""
    return (
        select(ArchiveNoteEmbedding.id, ArchiveNoteEmbedding.note_id, ArchiveNoteEmbedding.vector)
        .join(
            ArchiveNote,
            (ArchiveNote.id == ArchiveNoteEmbedding.note_id)
            & (ArchiveNote.namespace_id == ArchiveNoteEmbedding.namespace_id),
        )
        .join(
            ArchiveEmbeddingGeneration,
            (ArchiveEmbeddingGeneration.id == ArchiveNoteEmbedding.generation_id)
            & (ArchiveEmbeddingGeneration.namespace_id == ArchiveNoteEmbedding.namespace_id),
        )
        .where(
            ArchiveNote.namespace_id == manifest.archive.namespace_id,
            ArchiveNote.lifecycle == "promoted",
            ArchiveNote.content.is_not(None),
            ArchiveNoteEmbedding.namespace_id == manifest.archive.namespace_id,
            ArchiveNoteEmbedding.generation_id == reference.generation_id,
            ArchiveNoteEmbedding.generation_manifest_digest == manifest.digest,
            ArchiveNoteEmbedding.generation_version == version,
            ArchiveEmbeddingGeneration.manifest_digest == manifest.digest,
            ArchiveEmbeddingGeneration.version == version,
            ArchiveEmbeddingGeneration.state == "active",
            ArchiveNoteEmbedding.source_revision_digest == ArchiveNote.revision_digest,
            ArchiveNoteEmbedding.source_digest == ArchiveNote.source_digest,
            ArchiveNoteEmbedding.source_lifecycle_version == ArchiveNote.lifecycle_version,
            ArchiveNoteEmbedding.chunk_ordinal == 0,
            ArchiveNoteEmbedding.state == "complete",
            ArchiveNoteEmbedding.vector.is_not(None),
            ArchiveNoteEmbedding.vector_digest.is_not(None),
            ArchiveNoteEmbedding.receipt.is_not(None),
            ArchiveNoteEmbedding.completed_at.is_not(None),
        )
        .cte("eligible_semantic")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )


def _selection(
    manifest: GenerationManifest,
    reference: GenerationRef,
    version: int,
    note: ArchiveNote,
    row: ArchiveNoteEmbedding,
    score: float,
) -> SemanticSelection:
    """Validate selected physical bytes and the native document receipt, before publication."""
    try:
        if note.content is None or row.vector is None or row.receipt is None:
            raise ValueError  # noqa: TRY301 - safe corruption classification below
        source = RecordRef(
            record_id=note.id, revision_digest=note.revision_digest, lifecycle_version=note.lifecycle_version
        )
        native = DerivationReceipt.model_validate(row.receipt)
        vector = canonical_float32_vector(tuple(float(value) for value in row.vector))
        metadata = native.model_dump(mode="json", exclude={"profile_digest", "operation", "receipt_digest"})
        if (
            note.namespace_id != manifest.archive.namespace_id
            or note.lifecycle != "promoted"
            or row.namespace_id != note.namespace_id
            or row.note_id != note.id
            or row.generation_id != reference.generation_id
            or row.generation_manifest_digest != manifest.digest
            or row.generation_version != version
            or row.source_revision_digest != source.revision_digest
            or row.source_lifecycle_version != source.lifecycle_version
            or row.source_digest != note.source_digest
            or row.binding_digest
            != digest(
                DerivationRequest(generation=reference, source=source).model_dump(mode="json", exclude={"run_id"})
            )
            or row.chunk_ordinal != 0
            or row.state != "complete"
            or row.completed_at is None
            or row.attempt_token is not None
            or row.expires_at is not None
            or row.subject is None
            or row.purpose is None
            or row.attempt_version < 1
            or len(vector) != VECTOR_DIMENSION
            or abs(math.sqrt(sum(v * v for v in vector)) - 1) > manifest.embedding.normalization_tolerance
            or row.vector_digest != embedding_vector_digest(vector)
            or native.profile_digest != manifest.embedding.digest
            or native.item_id != str(row.id)
            or native.input_digest != note.source_digest
            or native.rendered_digest != text_digest(manifest.embedding.document_prefix + note.content)
            or native.vector_digest != row.vector_digest
            or native.tokens > manifest.embedding.max_input_tokens
            or len((manifest.embedding.document_prefix + note.content).encode()) > manifest.embedding.max_input_bytes
            or native.receipt_digest
            != embedding_digest({"profile": native.profile_digest, "operation": native.operation, "items": [metadata]})
            or not math.isfinite(score)
            or not -1 <= score <= 1
        ):
            raise ValueError  # noqa: TRY301 - safe corruption classification below
        selection = SemanticSelection(
            reference=source,
            source_key=note.source_key,
            source_revision=note.source_revision,
            source_digest=note.source_digest,
            score=score,
            projection_digest=text_digest(note.content),
            projected_chars=len(note.content),
            derivation_id=row.id,
            row_version=row.row_version,
            vector_digest=native.vector_digest,
        )
        SemanticRecallItem(selection=selection, text=note.content)
    except (ValueError, TypeError, OverflowError):
        raise ArchiveRefused("source_integrity") from None  # noqa: EM101 - closed safe code
    return selection


async def _existing(session: AsyncSession, namespace_id: UUID, request_id: UUID) -> ArchiveRecall | None:
    return await session.scalar(
        select(ArchiveRecall).where(ArchiveRecall.namespace_id == namespace_id, ArchiveRecall.request_id == request_id)
    )


class DbArchiveSemanticStore:
    """Short serialized transactions; no query cache, inference, retries or source authority."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], *, generation_id: UUID) -> None:
        """Bind the admitted runtime factory without establishing database readiness."""
        self._session_factory = session_factory
        self._generation_id = generation_id

    @asynccontextmanager
    async def _transaction(self) -> AsyncGenerator[AsyncSession]:
        try:
            async with self._session_factory() as session, session.begin():
                yield session
        except SQLAlchemyError:
            raise ArchiveRefused("storage") from None  # noqa: EM101 - closed safe code

    async def preflight(
        self,
        manifest: GenerationManifest,
        subject: ArchiveSubject,
        request: SemanticRecallRequest,
        purpose: str,
        check: AuthorizationCheck,
    ) -> SemanticPrepared | SemanticRecallReceipt:
        _request(manifest, request, self._generation_id)
        binding = request.binding_digest(manifest, subject, purpose)
        async with self._transaction() as session:
            await lock_archive_namespace(session, manifest.archive)
            check(request.request_id, binding)
            row = await _existing(session, request.namespace_id, request.request_id)
            check(request.request_id, binding)
            if row is not None:
                if row.request_digest != binding:
                    raise ArchiveRefused("request_conflict")  # noqa: EM101 - closed safe code
                receipt = _receipt(row)
                _binding(receipt, manifest, subject, request, purpose)
                check(receipt.receipt_id, receipt.receipt_digest)
                return receipt
            generation = await exact_generation(session, manifest, request.generation)
            check(request.request_id, binding)
            return SemanticPrepared(generation_version=generation.version)

    async def complete(
        self,
        manifest: GenerationManifest,
        subject: ArchiveSubject,
        request: SemanticRecallRequest,
        purpose: str,
        prepared: SemanticPrepared,
        execution: SemanticQueryExecution,
        vector: tuple[float, ...],
        check: AuthorizationCheck,
    ) -> SemanticRecallReceipt:
        _request(manifest, request, self._generation_id)
        binding = request.binding_digest(manifest, subject, purpose)
        async with self._transaction() as session:
            await lock_archive_namespace(session, manifest.archive)
            check(request.request_id, binding)
            row = await _existing(session, request.namespace_id, request.request_id)
            check(request.request_id, binding)
            if row is not None:
                if row.request_digest != binding:
                    raise ArchiveRefused("request_conflict")  # noqa: EM101 - closed safe code
                receipt = _receipt(row)
                _binding(receipt, manifest, subject, request, purpose)
                check(receipt.receipt_id, receipt.receipt_digest)
                return receipt
            _query(manifest, request, execution, vector)
            generation = await exact_generation(session, manifest, request.generation)
            if generation.version != prepared.generation_version:
                raise ArchiveRefused("stale_version")  # noqa: EM101 - closed safe code
            check(request.request_id, binding)
            eligible = _eligible(manifest, request.generation, generation.version)
            promoted = await session.scalar(
                select(func.count())
                .select_from(ArchiveNote)
                .where(
                    ArchiveNote.namespace_id == request.namespace_id,
                    ArchiveNote.lifecycle == "promoted",
                    ArchiveNote.content.is_not(None),
                )
            )
            check(request.request_id, binding)
            count = await session.scalar(select(func.count()).select_from(eligible))
            check(request.request_id, binding)
            if promoted is None or count is None:
                raise ArchiveRefused("storage")  # noqa: EM101 - closed safe code
            # An explicit arithmetic similarity over a materialized relation is exact even
            # if a later migration adds a nearest-neighbor index to the underlying vector.
            score = (1.0 - eligible.c.vector.cosine_distance(list(vector))).label("score")
            matches = (
                await session.execute(
                    select(eligible.c.id, score)
                    .where(score >= request.min_cosine)
                    .order_by(score.desc(), eligible.c.note_id)
                    .limit(request.max_results)
                )
            ).all()
            check(request.request_id, binding)
            selected: list[SemanticSelection] = []
            remaining, omitted = request.char_budget, 0
            for row_id, rank in matches:
                pair = (
                    await session.execute(
                        select(ArchiveNote, ArchiveNoteEmbedding)
                        .join(ArchiveNoteEmbedding, ArchiveNoteEmbedding.note_id == ArchiveNote.id)
                        .where(ArchiveNoteEmbedding.id == row_id, ArchiveNote.namespace_id == request.namespace_id)
                    )
                ).one_or_none()
                check(request.request_id, binding)
                if pair is None:
                    raise ArchiveRefused("source_integrity")  # noqa: EM101 - closed safe code
                selection = _selection(manifest, request.generation, generation.version, pair[0], pair[1], float(rank))
                if selection.projected_chars > remaining:
                    omitted += 1
                    continue
                remaining -= selection.projected_chars
                selected.append(selection)
            values: dict[str, Any] = {
                "schema_version": 2,
                "receipt_id": uuid4(),
                "request_id": request.request_id,
                "namespace_id": request.namespace_id,
                "subject": subject,
                "purpose": purpose,
                "profile": manifest.archive.profile,
                "retrieval_policy": SEMANTIC_POLICY,
                "policy_revision": manifest.archive.policy_revision,
                "query_digest": text_digest(request.query),
                "request_digest": binding,
                "run_id": request.run_id,
                "max_results": request.max_results,
                "char_budget": request.char_budget,
                "min_cosine": request.min_cosine,
                "generation": request.generation,
                "generation_version": generation.version,
                "query_execution": execution,
                "coverage": SemanticCoverage(promoted_notes=promoted, eligible_notes=count),
                "selected": tuple(selected),
                "omitted_for_budget": omitted,
                "created_at": datetime.now(UTC),
            }
            receipt = _seal(values)
            check(receipt.receipt_id, receipt.receipt_digest)
            session.add(
                ArchiveRecall(
                    id=receipt.receipt_id,
                    namespace_id=request.namespace_id,
                    request_id=request.request_id,
                    request_digest=binding,
                    receipt_digest=receipt.receipt_digest,
                    receipt=receipt.model_dump(mode="json"),
                )
            )
            await session.flush()
            check(receipt.receipt_id, receipt.receipt_digest)
            return receipt

    async def inspect(
        self, manifest: GenerationManifest, request: SemanticRecallRequest, check: AuthorizationCheck
    ) -> SemanticRecallReceipt | None:
        _request(manifest, request, self._generation_id)
        async with self._transaction() as session:
            present = await lock_archive_namespace(session, manifest.archive, missing_ok=True)
            check(request.request_id, digest(request))
            if not present:
                return None
            row = await _existing(session, request.namespace_id, request.request_id)
            check(request.request_id, digest(request))
            if row is None:
                return None
            receipt = _receipt(row)
            if receipt.namespace_id != request.namespace_id or receipt.request_id != request.request_id:
                raise ArchiveRefused("receipt_integrity")  # noqa: EM101 - closed safe code
            check(receipt.receipt_id, receipt.receipt_digest)
            return receipt

    async def resolve(
        self,
        manifest: GenerationManifest,
        subject: ArchiveSubject,
        receipt_id: UUID,
        receipt_digest: str,
        purpose: str,
        check: AuthorizationCheck,
    ) -> SemanticRecallProjection:
        async with self._transaction() as session:
            await lock_archive_namespace(session, manifest.archive)
            check(receipt_id, receipt_digest)
            row = await session.scalar(
                select(ArchiveRecall).where(
                    ArchiveRecall.namespace_id == manifest.archive.namespace_id, ArchiveRecall.id == receipt_id
                )
            )
            check(receipt_id, receipt_digest)
            if row is None:
                raise ArchiveRefused("receipt_missing")  # noqa: EM101 - closed safe code
            receipt = _receipt(row)
            if (
                receipt.receipt_id != receipt_id
                or receipt.namespace_id != manifest.archive.namespace_id
                or receipt.receipt_digest != receipt_digest
                or receipt.subject != subject
                or receipt.purpose != purpose
                or receipt.profile != manifest.archive.profile
                or receipt.policy_revision != manifest.archive.policy_revision
                or receipt.generation.manifest_digest != manifest.digest
                or receipt.generation.generation_id != self._generation_id
                or receipt.query_execution.profile_digest != manifest.embedding.digest
                or receipt.query_execution.tokens > manifest.embedding.max_input_tokens
            ):
                raise ArchiveRefused("receipt_binding")  # noqa: EM101 - closed safe code
            generation = await exact_generation(session, manifest, receipt.generation)
            if generation.version != receipt.generation_version:
                raise ArchiveRefused("receipt_stale")  # noqa: EM101 - closed safe code
            check(receipt_id, receipt_digest)
            items: list[SemanticRecallItem] = []
            for selected in receipt.selected:
                pair = (
                    await session.execute(
                        select(ArchiveNote, ArchiveNoteEmbedding)
                        .join(ArchiveNoteEmbedding, ArchiveNoteEmbedding.note_id == ArchiveNote.id)
                        .where(
                            ArchiveNote.namespace_id == manifest.archive.namespace_id,
                            ArchiveNote.id == selected.reference.record_id,
                            ArchiveNoteEmbedding.id == selected.derivation_id,
                        )
                    )
                ).one_or_none()
                check(receipt_id, receipt_digest)
                if pair is None:
                    raise ArchiveRefused("receipt_stale")  # noqa: EM101 - closed safe code
                note, embedding = pair
                content = note.content
                if content is None:
                    raise ArchiveRefused("source_integrity")  # noqa: EM101 - closed safe code
                current = _selection(manifest, receipt.generation, generation.version, note, embedding, selected.score)
                if current != selected:
                    raise ArchiveRefused("receipt_stale")  # noqa: EM101 - closed safe code
                items.append(SemanticRecallItem(selection=selected, text=content))
            projection = SemanticRecallProjection(receipt=receipt, items=tuple(items))
            check(receipt_id, receipt_digest)
            return projection
