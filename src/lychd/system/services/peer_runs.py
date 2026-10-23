"""One native public peer passage through the existing Run/Graph lifecycle.

Only this process owns live operator permissions. Durable admission and task
custody identify what may be reauthorized; they never recreate a live marker.
Local retirement closes adoption, without claiming sovereign remote containment.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, NoReturn, cast
from uuid import UUID, uuid5

from lychd.agents.router import Intent
from lychd.domain.codex.local_access import LocalOperatorAuthentication
from lychd.domain.codex.peer import PeerAuthorityError, PeerObject, PublicTextSource
from lychd.domain.cortex.admission import RunAdmissionCoordinator
from lychd.domain.cortex.cancellation import RunEffectFence
from lychd.domain.cortex.execution_context import current_occurrence_id
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.intercom.native import PeerDeclarationProof, PeerRunBinding, PeerTaskOutcomeError, PeerTaskRef
from lychd.system.services.intercom import IntercomUnknownError

if TYPE_CHECKING:
    from lychd.db.intercom import IntercomStore
    from lychd.domain.cortex.cancellation import RunEffectLifecycle
    from lychd.domain.cortex.engine import RunEngine
    from lychd.domain.cortex.ledger import PeerAdmissionEvidence, RunLedger
    from lychd.domain.cortex.runs import RunHandle, RunRecord
    from lychd.system.services.intercom import IntercomService
    from lychd.system.services.peer_authority import PeerAuthority

_ACTIONS = frozenset({"submit", "poll", "read", "adopt", "resume"})
_WAIT = "peer_wait"


def _refuse(code: str) -> NoReturn:
    raise PeerAuthorityError(code) from None


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _target(binding: PeerRunBinding) -> PeerObject:
    return PeerObject(binding.peer_id, binding.purpose, binding.category, binding.task_schema, binding.endpoint)


@dataclass(frozen=True)
class _Permit:
    authentication: object = field(repr=False)
    binding: PeerRunBinding
    actions: frozenset[str]
    task_id: str | None = None


class PeerRunService:
    """Current native authority, bounded relay and required local effect owner."""

    def __init__(
        self,
        *,
        store: IntercomStore,
        intercom: IntercomService,
        ledger: RunLedger,
        authority: PeerAuthority,
        fence: RunEffectFence,
    ) -> None:
        """Bind existing custody, actual authentication and one control-loop fence."""
        self._store, self._intercom, self._ledger = store, intercom, ledger
        self._authority, self._fence = authority, fence
        self._loop = asyncio.get_running_loop()
        self._engine: RunEngine | None = None
        self._issued: dict[UUID, PeerDeclarationProof] = {}
        self._source_admissions = RunAdmissionCoordinator()
        self._permits: dict[str, _Permit] = {}
        self._known_runs: set[str] = set()
        self._driving: set[str] = set()
        self._resume_custody: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}

    def bind_engine(self, engine: RunEngine) -> None:
        """Bind the same engine used for operator admission and worker execution."""
        if self._engine is not None and self._engine is not engine:
            _refuse("native-engine")
        self._engine = engine

    def _require_loop(self) -> None:
        if asyncio.get_running_loop() is not self._loop:
            _refuse("control-loop")

    def authenticate_operator(self, authentication: object) -> None:
        """Authenticate an explicit local operation without granting a peer action."""
        self._authority.check_authentication(authentication)

    def admission(self, intent: Intent, proof: PeerDeclarationProof) -> PeerRunBinding:
        """Authenticate an actually issued proof synchronously after admission waits."""
        self._require_loop()
        binding = proof.binding
        if (
            self._issued.get(binding.request_id) is not proof
            or intent.source != "peer_public"
            or hashlib.sha256(intent.prompt.encode()).hexdigest() != binding.text_digest
            or datetime.now(UTC) >= binding.expires_at
        ):
            _refuse("native-admission")
        self._intercom.check_native(proof.authentication, "admit", binding)
        return binding

    def _check(self, run: RunRecord, action: str, *, task_id: str | None = None) -> _Permit:
        self._require_loop()
        permit = self._permits.get(run.run_id)
        if (
            permit is None
            or action not in permit.actions
            or run.admitted_peer != permit.binding
            or run.workflow_name != "native_public_peer"
            or run.pattern_manifest.get("revision") != "1"
            or run.source != "peer_public"
            or run.status not in {RunStatus.RUNNING, RunStatus.AWAITING_PEER, RunStatus.QUEUED}
            or self._fence.reason(run.run_id, run.enqueue_seq) is not None
            or (task_id is not None and permit.task_id not in {None, task_id})
        ):
            _refuse("native-permission")
        if action in {"adopt", "resume"}:
            # Expiry can authorize only a local failure route; every remote
            # operation and successful data consumption still checks its lifetime.
            self._authority.check(permit.authentication, action, _target(permit.binding))
        else:
            self._intercom.check_native(permit.authentication, action, permit.binding)
        return permit

    async def admit_public_run(
        self,
        authentication: object,
        *,
        session_id: str,
        request_id: UUID,
        source: PublicTextSource,
        peer_id: UUID,
        purpose: str,
        task_schema: str,
        endpoint: str,
    ) -> RunHandle:
        """Admit one explicitly authored public task through the real RunEngine."""
        self._require_loop()
        source.validate()
        target = PeerObject(peer_id, purpose, source.category, task_schema, endpoint)
        self._authority.check(authentication, "admit", target)
        engine = self._engine
        if engine is None:
            _refuse("native-engine")
        intent = Intent(session_id=session_id, prompt=source.text, source="peer_public")
        key = f"native-public-peer:{request_id}"
        admission_key = ("native-public-source", str(request_id))
        while not self._source_admissions.begin(admission_key):
            await self._source_admissions.wait(admission_key)
        try:
            proof = await self._prepare_admission(
                authentication,
                intent=intent,
                key=key,
                request_id=request_id,
                source=source,
                target=target,
            )
        finally:
            self._source_admissions.finish(admission_key)
        binding = proof.binding

        async def retain(run_id: str) -> None:
            run = await self._ledger.get(run_id)
            self.admission(intent, proof)
            if run is None or run.admitted_peer != binding:
                _refuse("native-binding")
            self._known_runs.add(run_id)
            self._permits[run_id] = _Permit(authentication, binding, _ACTIONS)

        return await engine.submit(intent, idempotency_key=key, retain_before_publish=retain, peer_declaration=proof)

    async def _prepare_admission(
        self,
        authentication: object,
        *,
        intent: Intent,
        key: str,
        request_id: UUID,
        source: PublicTextSource,
        target: PeerObject,
    ) -> PeerDeclarationProof:
        """Serialize only declaration preparation and retain its first exact proof."""
        existing = await self._ledger.get_idempotent(intent, idempotency_key=key)
        self._authority.check(authentication, "admit", target)
        if existing is not None:
            binding = existing.admitted_peer
            if (
                binding is None
                or _target(binding) != target
                or binding.text_digest != hashlib.sha256(source.text.encode()).hexdigest()
                or binding.source_digest != _digest(asdict(source))
                or binding.request_id != request_id
            ):
                _refuse("native-binding")
            proof = self._issued.get(request_id)
            if proof is None or proof.authentication is not authentication or proof.binding != binding:
                _refuse("native-reauthorization-required")
        elif request_id in self._issued:
            proof = self._issued[request_id]
            binding = proof.binding
            if (
                proof.authentication is not authentication
                or _target(binding) != target
                or binding.text_digest != hashlib.sha256(source.text.encode()).hexdigest()
                or binding.source_digest != _digest(asdict(source))
            ):
                _refuse("native-binding")
        else:
            declaration = await self._intercom.declare_public(
                authentication,
                peer_id=target.peer_id,
                purpose=target.purpose,
                task_schema=target.task_schema,
                endpoint=target.endpoint,
                source=source,
            )
            self._authority.check(authentication, "admit", target)
            binding = PeerRunBinding(
                request_id=request_id,
                declaration_id=declaration.declaration_id,
                operation_id=declaration.operation_id,
                peer_id=target.peer_id,
                purpose=target.purpose,
                task_schema=target.task_schema,
                endpoint=target.endpoint,
                source_digest=declaration.source_digest,
                text_digest=declaration.text_digest,
                expires_at=datetime.now(UTC) + timedelta(seconds=self._authority.policy.task_seconds),
            )
            proof = PeerDeclarationProof(authentication=authentication, binding=binding)
            self._issued[request_id] = proof
        self.admission(intent, proof)

        return proof

    async def _run(self, run_id: str, action: str, *, task_id: str | None = None) -> RunRecord:
        run = await self._ledger.get(run_id)
        if run is None:
            _refuse("native-binding")
        self._check(run, action, task_id=task_id)
        return run

    async def prepare(self, *, run_id: str, binding: PeerRunBinding, station: str) -> PeerTaskRef:
        """Commit one immutable preparation, without contacting the peer."""
        from lychd.domain.cortex.execution_context import current_step_id

        run = await self._run(run_id, "submit")
        if run.status is not RunStatus.RUNNING or run.admitted_peer != binding or station != _WAIT:
            _refuse("native-binding")
        occurrence, step = current_occurrence_id(), current_step_id()
        if occurrence is None or step is None:
            _refuse("native-provenance")
        ref = PeerTaskRef(
            task_id=uuid5(binding.request_id, f"native-public-peer:{run_id}:{station}"),
            run_id=run_id,
            station=station,
            request_id=binding.request_id,
            binding_digest=binding.digest,
        )
        permit = self._check(run, "submit")
        self._known_runs.add(run_id)
        self._permits[run_id] = _Permit(permit.authentication, binding, permit.actions, str(ref.task_id))

        def current() -> None:
            self._check(run, "submit", task_id=str(ref.task_id))

        self._intercom.bind_native_guard(ref.task_id, current)
        await self._intercom.prepare_native(
            permit.authentication,
            binding=binding,
            ref=ref,
            pattern_digest=cast("str", run.pattern_manifest["digest"]),
            enqueue_seq=run.enqueue_seq,
            step_id=step,
            occurrence_id=occurrence,
        )
        self._check(run, "submit", task_id=str(ref.task_id))
        return ref

    async def evidence(self, *, run_id: str, task_id: str) -> PeerAdmissionEvidence:
        """Read exact immutable provenance and correlated terminal custody."""
        from lychd.domain.cortex.ledger import PeerAdmissionEvidence

        run = await self._ledger.get(run_id)
        if run is None or run.admitted_peer is None:
            _refuse("native-binding")
        task = await self._store.task(UUID(task_id), peer_id=run.admitted_peer.peer_id)
        if task.get("native_run_id") != run_id or task.get("native_binding_digest") != run.admitted_peer.digest:
            _refuse("native-binding")
        ref = PeerTaskRef(
            task_id=UUID(task_id),
            run_id=run_id,
            station=task["native_station"],
            request_id=UUID(task["native_request_id"]),
            binding_digest=task["native_binding_digest"],
        )
        transmission = (
            await self._store.terminal_transmission(UUID(task_id))
            if task.get("local_status") == "terminal"
            else await self._store.native_transmission(UUID(task_id))
        )
        peer = await self._store.peer(run.admitted_peer.peer_id)
        self._resume_custody[task_id] = deepcopy(peer), deepcopy(task)
        return PeerAdmissionEvidence(
            ref=ref,
            pattern_digest=task["native_pattern_digest"],
            enqueue_seq=task["native_enqueue_seq"],
            step_id=task["native_step_id"],
            occurrence_id=task["native_occurrence_id"],
            task=task,
            transmission=transmission,
        )

    def require_resume(self, run_id: str, task_id: str, *, enqueue_seq: int) -> None:
        """Check current action authority inside the owning resume CAS."""
        permit = self._permits.get(run_id)
        if permit is None or permit.task_id != task_id or not {"adopt", "resume"} <= permit.actions:
            _refuse("native-permission")
        self._authority.check(permit.authentication, "resume", _target(permit.binding))
        if self._fence.reason(run_id, enqueue_seq) is not None:
            _refuse("native-permission")

        facts = self._resume_custody.get(task_id)
        if facts is None:
            _refuse("native-binding")
        peer, task = facts
        if task.get("native_run_id") != run_id or task.get("native_binding_digest") != permit.binding.digest:
            _refuse("native-binding")

        def current() -> None:
            if self._fence.reason(run_id, enqueue_seq) is not None:
                _refuse("native-permission")
            self._authority.check(permit.authentication, "adopt", _target(permit.binding))
            self._authority.check(permit.authentication, "resume", _target(permit.binding))

        target = PeerObject(
            permit.binding.peer_id,
            permit.binding.purpose,
            permit.binding.category,
            permit.binding.task_schema,
            permit.binding.endpoint,
            UUID(task_id),
            permit.binding.text_digest,
        )
        local = self._local_disposition(task) is not None
        for action in ("adopt", "resume"):
            self._intercom.check_current(
                permit.authentication,
                action,
                target,
                peer,
                task,
                current=current,
                allow_expired_native_disposition=local,
            )

    async def drive_wait(self, run_id: str) -> bool:  # noqa: C901, PLR0911, PLR0912 - one bounded wait decision
        """Perform at most one send or poll and one guarded resume per relay tick."""
        from lychd.domain.cortex.engine import admit_peer_resume

        self._require_loop()
        if run_id in self._driving or run_id not in self._permits:
            return False
        self._driving.add(run_id)
        try:
            run = await self._run(run_id, "resume")
            task_id = run.peer_task_id
            if run.status is not RunStatus.AWAITING_PEER or task_id is None or self._engine is None:
                return False
            self.require_resume(run_id, task_id, enqueue_seq=run.enqueue_seq)
            evidence = await self.evidence(run_id=run_id, task_id=task_id)
            permit = self._check(run, "resume", task_id=task_id)
            task = evidence.task
            if task.get("adoption_closed") is True:
                return False
            if (
                task.get("local_status") == "submitting"
                and task.get("submit_claimed")
                and not task.get("foreign_task_id")
            ):
                await self._reconcile_abandoned_submit(run, evidence)
                evidence = await self.evidence(run_id=run_id, task_id=task_id)
                task = evidence.task
            disposition = self._local_disposition(task)
            if task.get("local_status") != "terminal" and disposition is None:
                if not task.get("submit_claimed"):
                    action = "submit"
                    method = self._intercom.send_prepared
                elif task.get("foreign_task_id"):
                    action = "poll"
                    method = self._intercom.poll
                else:
                    return False
                if action not in permit.actions:
                    return False

                def current() -> None:
                    self._check(run, action, task_id=task_id)

                current()
                self._intercom.bind_native_guard(UUID(task_id), current)
                # Observe an unknown permanently charged claim before choosing
                # its explicit local failure route; never repeat its submit.
                with contextlib.suppress(IntercomUnknownError):
                    await method(
                        permit.authentication,
                        task_id=UUID(task_id),
                        peer_id=permit.binding.peer_id,
                        purpose=permit.binding.purpose,
                        task_schema=permit.binding.task_schema,
                        endpoint=permit.binding.endpoint,
                        current=current,
                    )
                self._check(run, action, task_id=task_id)
                evidence = await self.evidence(run_id=run_id, task_id=task_id)
            disposition = self._local_disposition(evidence.task)
            if evidence.task.get("local_status") != "terminal" and disposition is None:
                return False
            if disposition is None:
                await self._read_current(run, task_id)
            self._check(run, "adopt", task_id=task_id)

            def current_resume() -> None:
                self._resume_current(run, task_id)

            current_resume()
            return await admit_peer_resume(
                self._engine.queues, self._ledger, run, evidence=evidence, current=current_resume
            )
        except PeerAuthorityError:
            # Missing/revoked live permission leaves the durable wait untouched.
            return False
        finally:
            self._driving.discard(run_id)

    def _resume_current(self, run: RunRecord, task_id: str) -> None:
        self._check(run, "adopt", task_id=task_id)
        self._check(run, "resume", task_id=task_id)
        self.require_resume(run.run_id, task_id, enqueue_seq=run.enqueue_seq)

    async def _reconcile_abandoned_submit(self, run: RunRecord, evidence: PeerAdmissionEvidence) -> None:
        """Retire an unsettled permanent claim as unknown, without any new activation."""
        task_id = str(evidence.ref.task_id)
        transmission = evidence.transmission
        if (
            run.peer_task_id != task_id
            or evidence.ref.run_id != run.run_id
            or transmission is None
            or str(transmission.get("task_id")) != task_id
            or transmission.get("method") != "SendMessage"
            or transmission.get("status") != "claimed"
            or transmission.get("settlement") is not None
        ):
            _refuse("native-submit-custody")

        def current() -> None:
            self._resume_current(run, task_id)
            self._intercom.fence_abandoned_native_submit(run_id=run.run_id, task_id=UUID(task_id))

        current()
        await self._store.settle(
            UUID(task_id),
            UUID(str(transmission["id"])),
            {"status": "unknown", "accepted_network_bytes": 0, "local_status": "unknown"},
            current=current,
        )
        current()

    @staticmethod
    def _local_disposition(task: dict[str, Any]) -> str | None:
        expires_at = datetime.fromisoformat(str(task["expires_at"]))
        if expires_at <= datetime.now(UTC):
            return "expired"
        status = task.get("local_status")
        if status in {"expired", "revoked", "refused"}:
            return cast("str", status)
        if status == "unknown" and task.get("submit_claimed") and not task.get("foreign_task_id"):
            return "unknown"
        return None

    async def _read_current(self, run: RunRecord, task_id: str) -> dict[str, Any]:
        permit = self._check(run, "read", task_id=task_id)

        def current() -> None:
            self._check(run, "read", task_id=task_id)

        self._intercom.bind_native_guard(UUID(task_id), current)
        task = await self._intercom.read(
            permit.authentication,
            task_id=UUID(task_id),
            peer_id=permit.binding.peer_id,
            purpose=permit.binding.purpose,
            task_schema=permit.binding.task_schema,
            endpoint=permit.binding.endpoint,
            current=current,
        )
        current()
        return task

    async def result(self, *, run_id: str, binding: PeerRunBinding, ref: PeerTaskRef) -> str:
        """Consume authenticated foreign data only on the admitted successor claim."""
        run = await self._run(run_id, "resume", task_id=str(ref.task_id))
        if run.status is not RunStatus.RUNNING or run.peer_task_id != str(ref.task_id) or run.admitted_peer != binding:
            _refuse("native-binding")
        self._check(run, "adopt", task_id=str(ref.task_id))
        evidence = await self.evidence(run_id=run_id, task_id=str(ref.task_id))
        self._check(run, "resume", task_id=str(ref.task_id))
        disposition = self._local_disposition(evidence.task)
        if disposition is not None:
            raise PeerTaskOutcomeError(disposition)
        await self._read_current(run, str(ref.task_id))
        if evidence.ref != ref or evidence.task.get("adoption_closed") or evidence.transmission is None:
            _refuse("native-terminal")
        terminal = evidence.task.get("settlement")
        if not isinstance(terminal, dict):
            _refuse("native-terminal")
        terminal = cast("dict[str, Any]", terminal)
        transmission = evidence.transmission
        if (
            transmission.get("task_id") != str(ref.task_id)
            or transmission.get("status") != "received"
            or transmission.get("settlement") != terminal
            or terminal.get("status") != "received"
            or terminal.get("terminal") is not True
        ):
            _refuse("native-terminal")
        if terminal.get("foreign_status") != "TASK_STATE_COMPLETED":
            outcome = "remote_noncompletion"
            raise PeerTaskOutcomeError(outcome)
        result = terminal.get("result", {})
        if not isinstance(result, dict):
            _refuse("native-terminal")
        result = cast("dict[str, Any]", result)
        if result.get("origin") != "authenticated-foreign-data":
            _refuse("native-terminal")
        texts = result.get("text")
        if not isinstance(texts, list) or not all(isinstance(text, str) for text in cast("list[object]", texts)):
            _refuse("native-terminal")
        return "\n".join(cast("list[str]", texts))

    async def reauthorize_existing_run(  # noqa: C901 - preserve ordered authentication and custody checks
        self,
        authentication: object,
        *,
        run_id: str,
        expected_task_id: str,
        expected_binding_digest: str,
        actions: frozenset[str],
        reaffirm_public_source: bool = False,
    ) -> dict[str, object]:
        """Install a fresh exact live permission; claimed submits remain single-shot."""
        self._require_loop()
        if (
            type(authentication) is not LocalOperatorAuthentication
            or type(actions) is not frozenset
            or not actions
            or not actions <= _ACTIONS
        ):
            _refuse("native-reauthorization")
        # No database lookup is allowed until the real current marker is checked.
        self._authority.check_authentication(authentication)
        run = await self._ledger.get(run_id)
        binding = run.admitted_peer if run is not None else None
        if binding is None or run is None or binding.digest != expected_binding_digest:
            _refuse("native-binding")
        for action in actions:
            self._intercom.check_native(authentication, action, binding)
        if (
            run.status not in {RunStatus.AWAITING_PEER, RunStatus.QUEUED}
            or run.peer_task_id != expected_task_id
            or self._fence.reason(run_id, run.enqueue_seq) is not None
        ):
            _refuse("native-binding")
        evidence = await self.evidence(run_id=run_id, task_id=expected_task_id)
        for action in actions:
            self._intercom.check_native(authentication, action, binding)
        task = evidence.task
        if task.get("adoption_closed") or task.get("local_status") in {"cancelled", "expired", "revoked", "refused"}:
            _refuse("native-closed")
        if "submit" in actions and (not reaffirm_public_source or task.get("submit_claimed")):
            _refuse("native-submit")
        declaration = await self._store.declaration(binding.declaration_id)
        for action in actions:
            self._intercom.check_native(authentication, action, binding)
        source_record = declaration.get("source")
        if not isinstance(source_record, dict):
            _refuse("native-source")
        source_fields = dict(cast("dict[str, Any]", source_record))
        source_fields["source_manifest"] = tuple(source_fields["source_manifest"])
        source_fields["influence_manifest"] = tuple(source_fields["influence_manifest"])
        source = PublicTextSource(**source_fields)
        source.validate()
        if (
            _digest(asdict(source)) != binding.source_digest
            or hashlib.sha256(source.text.encode()).hexdigest() != binding.text_digest
        ):
            _refuse("native-source")
        if "submit" in actions:
            self._intercom.check_native(authentication, "classify_public", binding)

        def current() -> None:
            for action in actions:
                self._intercom.check_native(authentication, action, binding)
            if self._fence.reason(run_id, run.enqueue_seq) is not None:
                _refuse("native-permission")

        # This transient read callback is never installed as a live transmission
        # permission. It verifies durable current peer/key/task generations first.
        await self._intercom.read(
            authentication,
            task_id=UUID(expected_task_id),
            peer_id=binding.peer_id,
            purpose=binding.purpose,
            task_schema=binding.task_schema,
            endpoint=binding.endpoint,
            current=current,
        )
        current()

        await self._store.record_native_authorization(
            run_id,
            UUID(expected_task_id),
            {
                "subject": authentication.subject,
                "authentication_generation": str(authentication.authentication_generation),
                "actions": sorted(actions),
                "reaffirm_public_source": reaffirm_public_source,
                "authorized_at": datetime.now(UTC).isoformat(),
                "binding_digest": binding.digest,
            },
            current=current,
        )
        current()
        self._known_runs.add(run_id)
        self._permits[run_id] = _Permit(authentication, binding, actions, expected_task_id)
        return {"run_id": run_id, "task_id": expected_task_id, "authorized": True}

    async def status(self, authentication: object, *, run_id: str) -> dict[str, Any]:
        """Expose local truth and retained remote uncertainty under current read policy."""
        self._authority.check_authentication(authentication)
        run = await self._ledger.get(run_id)
        if run is None or run.admitted_peer is None:
            _refuse("native-binding")
        binding = run.admitted_peer
        self._authority.check_local_evidence(authentication, _target(binding))
        tasks = await self._store.native_tasks(run_id)
        self._authority.check_local_evidence(authentication, _target(binding))
        return {
            "run_id": run_id,
            "status": run.status.value,
            "task_id": run.peer_task_id,
            "binding_digest": binding.digest,
            "error_present": run.error is not None,
            "tasks": [
                {
                    "task_id": task["task_id"],
                    "local_status": task["local_status"],
                    "adoption_closed": bool(task.get("adoption_closed")),
                    "closure_reason": task.get("closure_reason"),
                    "foreign_task_id": task.get("foreign_task_id"),
                    "foreign_status": task.get("foreign_status"),
                    "submit_claimed": bool(task.get("submit_claimed")),
                    "remote_outcome_unknown": bool(task.get("submit_claimed"))
                    and not (
                        isinstance(task.get("settlement"), dict)
                        and cast("dict[str, Any]", task["settlement"]).get("terminal") is True
                        and cast("dict[str, Any]", task["settlement"]).get("status") == "received"
                    ),
                    "remote_containment": "unproved",
                }
                for task in tasks
            ],
        }

    async def read_result(self, authentication: object, *, run_id: str) -> str:
        """Read a completed local result under fresh current exact read authority."""
        self._authority.check_authentication(authentication)
        run = await self._ledger.get(run_id)
        if run is None or run.admitted_peer is None or run.peer_task_id is None or run.status is not RunStatus.DONE:
            _refuse("native-terminal")
        binding, task_id = run.admitted_peer, run.peer_task_id

        def current() -> None:
            self._intercom.check_native(authentication, "read", binding)

        current()
        task = await self._intercom.read(
            authentication,
            task_id=UUID(task_id),
            peer_id=binding.peer_id,
            purpose=binding.purpose,
            task_schema=binding.task_schema,
            endpoint=binding.endpoint,
            current=current,
        )
        current()
        transmission = await self._store.terminal_transmission(UUID(task_id))
        current()
        terminal = task.get("settlement")
        if (
            task.get("native_run_id") != run_id
            or task.get("native_binding_digest") != binding.digest
            or task.get("adoption_closed")
            or transmission is None
            or transmission.get("status") != "received"
            or transmission.get("settlement") != terminal
            or not isinstance(terminal, dict)
        ):
            _refuse("native-terminal")
        terminal = cast("dict[str, Any]", terminal)
        if terminal.get("foreign_status") != "TASK_STATE_COMPLETED" or terminal.get("terminal") is not True:
            _refuse("native-terminal")
        result = terminal.get("result")
        if not isinstance(result, dict):
            _refuse("native-terminal")
        result = cast("dict[str, Any]", result)
        texts = result.get("text")
        if result.get("origin") != "authenticated-foreign-data" or not isinstance(texts, list):
            _refuse("native-terminal")
        if not all(isinstance(text, str) for text in cast("list[object]", texts)):
            _refuse("native-terminal")
        return "\n".join(cast("list[str]", texts))

    def fence(self, run_id: str, reason: str) -> None:
        self._fence.fence(run_id, reason)

    def fence_claim(self, run_id: str, enqueue_seq: int, reason: str) -> None:
        self._fence.fence_claim(run_id, enqueue_seq, reason)

    def fence_all(self, reason: str) -> None:
        self._fence.fence_all(reason)

    async def close_run(self, run_id: str) -> None:
        """Trusted elected cancellation closes every local task and actual exchange."""
        self.fence(run_id, "native_peer_closed")
        self._permits.pop(run_id, None)
        await self._intercom.retire_native_run(run_id)

    async def contain(self, run_id: str) -> None:
        await self.close_run(run_id)

    async def contain_all(self) -> None:
        self.fence_all("native_peer_shutdown")
        self._permits.clear()
        results = await asyncio.gather(
            *(self._intercom.retire_native_run(run_id, close_adoption=False) for run_id in tuple(self._known_runs)),
            return_exceptions=True,
        )
        failures = [result for result in results if isinstance(result, BaseException)]
        if failures:
            message = "Native peer local shutdown did not complete."
            raise BaseExceptionGroup(message, failures)


class CompositeRunEffects:
    """Compose actual effect owners without replacing existing containment duties."""

    def __init__(self, *owners: RunEffectLifecycle) -> None:
        """Retain every independently required local effect owner."""
        self._owners = owners

    def fence(self, run_id: str, reason: str) -> None:
        for owner in self._owners:
            owner.fence(run_id, reason)

    def fence_claim(self, run_id: str, enqueue_seq: int, reason: str) -> None:
        for owner in self._owners:
            owner.fence_claim(run_id, enqueue_seq, reason)

    def fence_all(self, reason: str) -> None:
        for owner in self._owners:
            owner.fence_all(reason)

    async def contain(self, run_id: str) -> None:
        results = await asyncio.gather(*(owner.contain(run_id) for owner in self._owners), return_exceptions=True)
        failures = [result for result in results if isinstance(result, BaseException)]
        if failures:
            message = "Required Run effect containment failed."
            raise BaseExceptionGroup(message, failures)

    async def contain_all(self) -> None:
        results = await asyncio.gather(*(owner.contain_all() for owner in self._owners), return_exceptions=True)
        failures = [result for result in results if isinstance(result, BaseException)]
        if failures:
            message = "Required Run effect shutdown failed."
            raise BaseExceptionGroup(message, failures)
