"""PostgreSQL owns reservation, one-shot inference claims and response adoption."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select, text

from lychd.compositions.creation.schemas import (
    FEEDBACK_LIMIT,
    INPUT_TOKENS,
    OUTPUT_TOKENS,
    RESPONSE_BYTES,
    CaseView,
    ContinueRequest,
    ExternalAssessment,
    FeedbackEntry,
    FeedbackTarget,
    FeedbackView,
    InvestigationRequest,
    OwnerDecision,
    canonical,
    decode,
    digest,
    feedback_target,
    refuse,
    validate_annotations,
)
from lychd.db.models.creation import CreationAdmission, CreationAttempt, CreationCase, CreationFeedback
from lychd.db.models.run import Run
from lychd.db.models.run_delivery import RunDelivery
from lychd.domain.codex.sigil import Sigil
from lychd.domain.cortex.runs import TERMINAL_STATUSES


class DbCreationStore:
    """All forward transitions lock the case, then its exact admitted Run."""

    def __init__(self, factory: Any, policy: Any) -> None:
        """Bind PostgreSQL transactions and the same current authority policy."""
        self.factory, self.policy = factory, policy

    async def _case(self, session: Any, case_id: UUID) -> CreationCase:
        row = await session.scalar(select(CreationCase).where(CreationCase.id == case_id).with_for_update())
        if row is None:
            refuse("unknown_case")
        if digest(row.request_bytes) != row.request_digest or digest(row.profile_bytes) != row.profile_digest:
            refuse("custody_digest")
        if row.candidate_bytes is not None and digest(row.candidate_bytes) != row.candidate_digest:
            refuse("candidate_digest")
        return row

    async def reserve(self, request: InvestigationRequest, profile: dict[str, Any], binding: dict[str, Any]) -> UUID:
        request_bytes, profile_bytes = canonical(request), canonical(profile)
        async with self.factory() as session:
            # Serialize absence as well as presence; the unique nullable slot is a second guard.
            await session.execute(text("SELECT pg_advisory_xact_lock(727161, 1)"))
            existing = await session.get(CreationCase, request.request_id)
            if existing is not None:
                if existing.request_bytes != request_bytes or existing.profile_bytes != profile_bytes:
                    refuse("conflicting_replay")
                return existing.current_admission_id
            occupied = await session.scalar(select(CreationCase).where(CreationCase.slot == 1).with_for_update())
            if occupied is not None:
                await self._expire(session, occupied)
                if occupied.slot is not None:
                    refuse("reservation_unavailable")
            now = await session.scalar(select(func.clock_timestamp()))
            session.add(
                CreationCase(
                    id=request.request_id,
                    request_bytes=request_bytes,
                    request_digest=digest(request_bytes),
                    profile_bytes=profile_bytes,
                    profile_digest=digest(profile_bytes),
                    deadline=now + timedelta(seconds=180),
                    slot=1,
                    current_admission_id=UUID(binding["admission_id"]),
                    status="reserved",
                    cancelled=False,
                )
            )
            await session.flush()
            session.add(
                CreationAdmission(
                    id=UUID(binding["admission_id"]), case_id=request.request_id, binding_bytes=canonical(binding)
                )
            )
            await session.commit()
        return UUID(binding["admission_id"])

    async def continuation(
        self, case_id: UUID, request: ContinueRequest, binding: dict[str, Any], *, leases_clear: Any
    ) -> UUID:
        async with self.factory() as session:
            row = await self._case(session, case_id)
            previous = await session.get(CreationAdmission, row.current_admission_id)
            existing = await session.get(CreationAdmission, request.admission_id)
            if existing is not None:
                old = decode(existing.binding_bytes)
                if existing.case_id != case_id or old.get("continuation") != request.model_dump(mode="json"):
                    refuse("conflicting_continuation")
                return existing.id
            now = await session.scalar(select(func.clock_timestamp()))
            verifier = await session.scalar(
                select(CreationAttempt).where(CreationAttempt.case_id == case_id, CreationAttempt.role == "verifier")
            )
            constructor = await session.scalar(
                select(CreationAttempt).where(CreationAttempt.case_id == case_id, CreationAttempt.role == "constructor")
            )
            if (
                row.cancelled
                or row.status != "candidate"
                or row.slot != 1
                or now >= row.deadline
                or verifier is not None
                or constructor is None
                or not constructor.adopted
                or constructor.response_bytes is None
                or row.candidate_bytes is None
                or (request.request_digest, request.candidate_digest, request.profile_digest)
                != (row.request_digest, row.candidate_digest, row.profile_digest)
                or previous is None
                or previous.run_id is None
            ):
                refuse("continuation_ineligible")
            run = await session.scalar(select(Run).where(Run.id == previous.run_id).with_for_update())
            delivery = (
                await session.scalar(
                    select(RunDelivery).where(
                        RunDelivery.run_id == previous.run_id, RunDelivery.enqueue_seq == run.enqueue_seq
                    )
                )
                if run is not None
                else None
            )
            if run is None or run.status not in {"done", "failed"} or delivery is None or delivery.state != "settled":
                refuse("prior_run_unsettled")
            now = await session.scalar(select(func.clock_timestamp()))
            if now >= row.deadline or not leases_clear() or decode(previous.binding_bytes)["continuation"] is not None:
                refuse("recovery_allowance")
            binding["recovery_deadline"] = min(row.deadline, now + timedelta(seconds=30)).isoformat()
            binding["previous_run_id"] = str(previous.run_id)
            session.add(CreationAdmission(id=request.admission_id, case_id=case_id, binding_bytes=canonical(binding)))
            row.current_admission_id = request.admission_id
            await session.commit()
        return request.admission_id

    async def admission(self, admission_id: UUID) -> dict[str, Any]:
        async with self.factory() as session:
            row = await session.get(CreationAdmission, admission_id)
            if row is None:
                refuse("unknown_admission")
            return {**decode(row.binding_bytes), "run_id": str(row.run_id) if row.run_id else None}

    async def bind_run(self, admission_id: UUID, run_id: str) -> None:
        async with self.factory() as session:
            admission = await session.get(CreationAdmission, admission_id)
            if admission is None:
                refuse("unknown_admission")
            row = await self._case(session, admission.case_id)
            if row.current_admission_id != admission_id or admission.run_id not in {None, UUID(run_id)}:
                refuse("run_binding")
            admission.run_id = UUID(run_id)
            await session.commit()

    async def _live(self, session: Any, row: CreationCase, admission: CreationAdmission, run_id: str) -> None:
        binding = decode(admission.binding_bytes)
        run = await session.scalar(select(Run).where(Run.id == UUID(run_id)).with_for_update())
        now = await session.scalar(select(func.clock_timestamp()))
        if (
            row.cancelled
            or row.slot != 1
            or now >= row.deadline
            or (
                binding.get("recovery_deadline") is not None
                and now >= datetime.fromisoformat(binding["recovery_deadline"])
            )
            or row.current_admission_id != admission.id
            or admission.run_id != UUID(run_id)
            or run is None
            or run.status != "running"
            or run.workflow_name != "creation.investigate"
            or run.pattern_manifest != binding["pattern"]
            or run.sigil_name != binding["principal"]
            or sorted(run.intent.get("sigil_scopes", [])) != binding["scopes"]
            or run.intent.get("prompt") != str(admission.id)
            or run.source != "creation"
            or run.intent.get("session_id") != binding["session_id"]
        ):
            refuse("run_fence")
        self.policy.worker(binding, row.id)

    async def ready(self, admission_id: UUID, run_id: str) -> CaseView:
        async with self.factory() as session:
            admission = await session.get(CreationAdmission, admission_id)
            if admission is None:
                refuse("unknown_admission")
            row = await self._case(session, admission.case_id)
            await self._live(session, row, admission, run_id)
        return await self.read(admission.case_id)

    async def claim(self, admission_id: UUID, run_id: str, role: str, packet: bytes) -> UUID:
        async with self.factory() as session:
            admission = await session.get(CreationAdmission, admission_id)
            if admission is None:
                refuse("unknown_admission")
            row = await self._case(session, admission.case_id)
            await self._live(session, row, admission, run_id)
            existing = await session.scalar(
                select(CreationAttempt).where(CreationAttempt.case_id == row.id, CreationAttempt.role == role)
            )
            if existing is not None:
                refuse("attempt_already_claimed")
            if (role == "constructor" and row.status != "reserved") or (
                role == "verifier" and row.status != "candidate"
            ):
                refuse("stage_order")
            attempt_id = uuid4()
            now = await session.scalar(select(func.clock_timestamp()))
            session.add(
                CreationAttempt(
                    id=attempt_id,
                    case_id=row.id,
                    admission_id=admission_id,
                    role=role,
                    input_bytes=packet,
                    input_digest=digest(packet),
                    claimed_at=now,
                    adopted=False,
                )
            )
            await session.commit()
            return attempt_id

    async def overflow(self, attempt_id: UUID, metadata: dict[str, Any]) -> None:
        async with self.factory() as session:
            attempt = await session.scalar(
                select(CreationAttempt).where(CreationAttempt.id == attempt_id).with_for_update()
            )
            if attempt is None or attempt.response_bytes is not None:
                refuse("overflow_conflict")
            attempt.usage_bytes, attempt.error = canonical(metadata), "raw_response_bytes"
            await session.commit()

    async def complete(self, attempt_id: UUID, response: bytes, usage: dict[str, Any]) -> None:
        """Custody is independent of parsing, current authority and cancellation."""
        if len(response) > RESPONSE_BYTES:
            refuse("raw_response_bytes")
        async with self.factory() as session:
            attempt = await session.scalar(
                select(CreationAttempt).where(CreationAttempt.id == attempt_id).with_for_update()
            )
            if attempt is None:
                refuse("unknown_attempt")
            if attempt.response_bytes is not None:
                if attempt.response_bytes != response:
                    refuse("response_conflict")
                return
            attempt.response_bytes, attempt.response_digest, attempt.usage_bytes = (
                response,
                digest(response),
                canonical(usage),
            )
            await session.commit()

    async def adopt(self, attempt_id: UUID, run_id: str, output: bytes, validation: bytes) -> None:
        async with self.factory() as session:
            attempt = await session.get(CreationAttempt, attempt_id)
            if attempt is None:
                refuse("unknown_attempt")
            row = await self._case(session, attempt.case_id)
            admission = await session.get(CreationAdmission, attempt.admission_id)
            if admission is None or attempt.response_bytes is None:
                refuse("response_missing")
            await self._live(session, row, admission, run_id)
            usage = decode(attempt.usage_bytes or b"{}")
            if (
                not 1 <= usage.get("input_tokens", 0) <= INPUT_TOKENS
                or not 1 <= usage.get("output_tokens", 0) <= OUTPUT_TOKENS
            ):
                refuse("observed_usage")
            if attempt.adopted:
                if attempt.output_bytes != output or attempt.validation_bytes != validation:
                    refuse("output_conflict")
                return
            attempt.output_bytes, attempt.validation_bytes, attempt.adopted = output, validation, True
            if attempt.role == "constructor":
                row.candidate_bytes, row.candidate_digest, row.status = output, digest(output), "candidate"
            else:
                row.verdict_bytes, row.status, row.slot = output, decode(output)["disposition"], None
            await session.commit()

    async def fail(self, admission_id: UUID, reason: str, attempt_id: UUID | None = None) -> None:
        async with self.factory() as session:
            admission = await session.get(CreationAdmission, admission_id)
            if admission is None:
                refuse("unknown_admission")
            row = await self._case(session, admission.case_id)
            if attempt_id is not None:
                attempt = await session.get(CreationAttempt, attempt_id)
                if attempt is not None and attempt.error is None:
                    attempt.error = reason[:64]
            await self._finish(session, row, reason)
            await session.commit()

    async def _finish(self, session: Any, row: CreationCase, reason: str) -> None:
        unresolved = await session.scalar(
            select(CreationAttempt.id).where(
                CreationAttempt.case_id == row.id, CreationAttempt.response_bytes.is_(None)
            )
        )
        row.reason = reason[:64]
        if row.verdict_bytes is not None:
            return
        row.status = "cancelled" if row.cancelled else ("unknown" if unresolved else "incomplete")
        row.slot = 1 if unresolved else None

    async def _expire(self, session: Any, row: CreationCase) -> None:
        now = await session.scalar(select(func.clock_timestamp()))
        if row.slot == 1 and now >= row.deadline:
            await self._finish(session, row, "expired")

    async def cancel(self, case_id: UUID) -> tuple[str, ...]:
        async with self.factory() as session:
            row = await self._case(session, case_id)
            if row.verdict_bytes is None:
                row.cancelled = True
                await self._finish(session, row, "cancelled")
            admissions = list(
                await session.scalars(select(CreationAdmission).where(CreationAdmission.case_id == case_id))
            )
            runs = tuple(str(admission.run_id) for admission in admissions if admission.run_id is not None)
            await session.commit()
        return runs

    async def read(self, case_id: UUID) -> CaseView:
        async with self.factory() as session:
            row = await self._case(session, case_id)
            await self._expire(session, row)
            admissions = list(
                await session.scalars(
                    select(CreationAdmission)
                    .where(CreationAdmission.case_id == case_id)
                    .order_by(CreationAdmission.created_at, CreationAdmission.id)
                )
            )
            attempts = list(
                await session.scalars(
                    select(CreationAttempt)
                    .where(CreationAttempt.case_id == case_id)
                    .order_by(CreationAttempt.claimed_at, CreationAttempt.id)
                )
            )
            result = CaseView(
                case_id=row.id,
                request_digest=row.request_digest,
                profile_digest=row.profile_digest,
                status=row.status,
                deadline=row.deadline.isoformat(),
                slot_encumbered=row.slot == 1,
                request=InvestigationRequest.model_validate(decode(row.request_bytes)),
                profile=decode(row.profile_bytes),
                admissions=tuple(
                    {**decode(a.binding_bytes), "run_id": str(a.run_id) if a.run_id else None} for a in admissions
                ),
                attempts=tuple(
                    {
                        "id": str(a.id),
                        "role": a.role,
                        "admission_id": str(a.admission_id),
                        "input_digest": a.input_digest,
                        "input": decode(a.input_bytes),
                        "response": decode(a.response_bytes) if a.response_bytes else None,
                        "response_digest": a.response_digest,
                        "usage": decode(a.usage_bytes) if a.usage_bytes else None,
                        "validation": decode(a.validation_bytes) if a.validation_bytes else None,
                        "adopted": a.adopted,
                        "error": a.error,
                    }
                    for a in attempts
                ),
                candidate=decode(row.candidate_bytes) if row.candidate_bytes else None,
                candidate_digest=row.candidate_digest,
                verdict=decode(row.verdict_bytes) if row.verdict_bytes else None,
                reason=row.reason,
            )
            await session.commit()
            return result

    @staticmethod
    def _feedback_target(row: CreationCase) -> FeedbackTarget:
        if row.candidate_bytes is None or row.verdict_bytes is None:
            refuse("feedback_evidence_missing")
        return feedback_target(row.request_bytes, row.profile_bytes, row.candidate_bytes, row.verdict_bytes)

    @staticmethod
    def _feedback_entry(row: CreationFeedback, request: InvestigationRequest) -> FeedbackEntry:
        if digest(row.body_bytes) != row.body_digest:
            refuse("feedback_custody")
        body = decode(row.body_bytes)
        annotations: set[str] = set()
        if row.kind == "assessment":
            if (
                row.report_bytes is None
                or row.report_bytes != body["report"].encode("utf-8")
                or digest(row.report_bytes) != row.report_digest
            ):
                refuse("feedback_custody")
            annotations = {a["criterion"] for a in body["submitter_annotations"]}
        return FeedbackEntry(
            id=row.id,
            sequence=row.sequence,
            body_digest=row.body_digest,
            body=body,
            attribution=decode(row.attribution_bytes),
            created_at=row.created_at.isoformat(),
            report_digest=row.report_digest,
            criterion_coverage={
                c.id: "submitter_annotation" if c.id in annotations else "not_assessed" for c in request.criteria
            }
            if row.kind == "assessment"
            else {},
        )

    async def _feedback_settled(self, session: Any, row: CreationCase, leases_clear: Any) -> None:
        profile = decode(row.profile_bytes)
        if (profile.get("composition"), profile.get("revision"), profile.get("profile")) != (
            "creation.investigation",
            "2",
            "public-source-qwen@2",
        ):
            refuse("feedback_revision")
        if (
            row.slot is not None
            or row.cancelled
            or row.verdict_bytes is None
            or row.candidate_bytes is None
            or row.status != decode(row.verdict_bytes)["disposition"]
        ):
            refuse("feedback_unsettled")
        unresolved = await session.scalar(
            select(CreationAttempt.id).where(
                CreationAttempt.case_id == row.id, CreationAttempt.response_bytes.is_(None)
            )
        )
        if unresolved is not None:
            refuse("feedback_unresolved_claim")
        admissions = list(
            await session.scalars(
                select(CreationAdmission).where(CreationAdmission.case_id == row.id).order_by(CreationAdmission.id)
            )
        )
        if not admissions or any(a.run_id is None for a in admissions):
            refuse("feedback_run_unsettled")
        for admission in admissions:
            run = await session.scalar(select(Run).where(Run.id == admission.run_id).with_for_update())
            binding = decode(admission.binding_bytes)
            if (
                run is None
                or run.status not in TERMINAL_STATUSES
                or run.workflow_name != "creation.investigate"
                or run.source != "creation"
                or run.pattern_manifest != binding["pattern"]
                or run.sigil_name != binding["principal"]
                or run.intent.get("prompt") != str(admission.id)
                or run.intent.get("session_id") != binding["session_id"]
            ):
                refuse("feedback_run_unsettled")
            delivery = await session.scalar(
                select(RunDelivery)
                .where(RunDelivery.run_id == run.id, RunDelivery.enqueue_seq == run.enqueue_seq)
                .with_for_update()
            )
            if delivery is None or delivery.state != "settled":
                refuse("feedback_delivery_unsettled")
        if not leases_clear(tuple(str(a.run_id) for a in admissions)):
            refuse("feedback_active_lease")

    async def append_feedback(
        self,
        case_id: UUID,
        body: ExternalAssessment | OwnerDecision,
        *,
        authentication: object,
        principal: Sigil,
        leases_clear: Any,
    ) -> FeedbackEntry:
        """Serialize custody only; never expire, renew, infer or mutate the original case."""
        is_assessment = isinstance(body, ExternalAssessment)
        record_id = body.assessment_id if is_assessment else body.decision_id
        action = "assess" if is_assessment else "decide"
        body_bytes = canonical(body)
        async with self.factory() as session:
            row = await self._case(session, case_id)
            self.policy.http(authentication, principal, action)
            # Coordinate the globally unique client identity even across different cases.
            await session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": int.from_bytes(record_id.bytes[:8], "big", signed=True)},
            )
            self.policy.http(authentication, principal, action)
            existing = await session.get(CreationFeedback, record_id)
            request = InvestigationRequest.model_validate(decode(row.request_bytes))
            if existing is not None:
                if (
                    existing.case_id != case_id
                    or existing.body_bytes != body_bytes
                    or existing.kind != ("assessment" if is_assessment else "decision")
                ):
                    refuse("conflicting_feedback_replay")
                self.policy.http(authentication, principal, action)
                return self._feedback_entry(existing, request)
            await self._feedback_settled(session, row, leases_clear)
            if body.target != self._feedback_target(row):
                refuse("feedback_target")
            records = list(
                await session.scalars(
                    select(CreationFeedback)
                    .where(CreationFeedback.case_id == case_id)
                    .order_by(CreationFeedback.sequence)
                )
            )
            kind = "assessment" if is_assessment else "decision"
            if sum(record.kind == kind for record in records) >= FEEDBACK_LIMIT:
                refuse("feedback_capacity")
            if isinstance(body, ExternalAssessment):
                validate_annotations(request, body)
            else:
                assessments = [record for record in records if record.kind == "assessment"]
                if not assessments or (assessments[-1].id, assessments[-1].body_digest) != (
                    body.assessment_id,
                    body.assessment_digest,
                ):
                    refuse("feedback_latest_assessment")
                self._feedback_entry(assessments[-1], request)
            actor = self.policy.http(authentication, principal, action)
            record = CreationFeedback(
                id=record_id,
                case_id=case_id,
                sequence=records[-1].sequence + 1 if records else 1,
                kind=kind,
                assessment_id=None if is_assessment else body.assessment_id,
                body_bytes=body_bytes,
                body_digest=digest(body_bytes),
                report_bytes=body.report.encode("utf-8") if isinstance(body, ExternalAssessment) else None,
                report_digest=digest(body.report.encode("utf-8")) if isinstance(body, ExternalAssessment) else None,
                attribution_bytes=canonical(
                    {
                        "subject": actor.subject,
                        "authentication_generation": str(actor.authentication_generation),
                        "principal": principal.name,
                        "scopes": sorted(principal.scopes),
                        "role": "local-operator",
                    }
                ),
            )
            session.add(record)
            await session.flush()
            self.policy.http(authentication, principal, action)
            result = self._feedback_entry(record, request)
            await session.commit()
            return result

    async def feedback(self, case_id: UUID, *, authentication: object, principal: Sigil) -> FeedbackView:
        """Protected historical projection without invoking execution expiration."""
        async with self.factory() as session:
            row = await self._case(session, case_id)
            self.policy.http(authentication, principal, "feedback")
            records = list(
                await session.scalars(
                    select(CreationFeedback)
                    .where(CreationFeedback.case_id == case_id)
                    .order_by(CreationFeedback.sequence)
                )
            )
            request = InvestigationRequest.model_validate(decode(row.request_bytes))
            assessments = tuple(
                self._feedback_entry(record, request) for record in records if record.kind == "assessment"
            )
            decisions = tuple(self._feedback_entry(record, request) for record in records if record.kind == "decision")
            latest = assessments[-1] if assessments else None
            current = next(
                (d for d in reversed(decisions) if latest is not None and d.body["assessment_id"] == str(latest.id)),
                None,
            )
            self.policy.http(authentication, principal, "feedback")
            return FeedbackView(
                case_id=case_id,
                native_status=row.status,
                native_verdict=decode(row.verdict_bytes) if row.verdict_bytes else None,
                target=self._feedback_target(row)
                if row.candidate_bytes is not None and row.verdict_bytes is not None
                else None,
                status=("hold" if current.body["action"] == "hold" else "rejected")
                if current is not None
                else ("review_required" if latest else "unassessed"),
                current_assessment_id=latest.id if latest else None,
                current_decision_id=current.id if current else None,
                assessments=assessments,
                decisions=decisions,
            )
