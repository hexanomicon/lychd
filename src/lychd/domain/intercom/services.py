"""Fail-closed Intercom admission and a process-local replay ledger."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from lychd.domain.intercom.models import (
    LEGAL_PEER_TASK_TRANSITIONS,
    TERMINAL_PEER_TASK_STATUSES,
    PeerAdmissionDecision,
    PeerTaskRecord,
    PeerTaskResult,
    PeerTaskStatus,
    VerifiedPeerEnvelope,
)
from lychd.domain.intercom.ports import PeerAdmissionPolicy, PeerEnvelopeVerifier, PeerTaskStore

__all__ = [
    "IllegalPeerTaskTransitionError",
    "InMemoryPeerTaskStore",
    "IntercomAdmissionService",
    "PeerEnvelopeRejectedError",
    "PeerReplayConflictError",
    "UnknownPeerTaskError",
]

_MAX_WIRE_MESSAGE_BYTES = 1_200_000


class PeerEnvelopeRejectedError(RuntimeError):
    """Raised when verified input cannot enter the local peer-task ledger."""


class PeerReplayConflictError(RuntimeError):
    """Raised when a peer reuses a replay identity for different authenticated content."""


class UnknownPeerTaskError(LookupError):
    """Raised when a state operation targets no retained peer task."""


class IllegalPeerTaskTransitionError(RuntimeError):
    """Raised when a peer task attempts to leave the accepted state machine."""


@dataclass
class _PeerTaskRow:
    verified: VerifiedPeerEnvelope
    admission: PeerAdmissionDecision | None = None
    status: PeerTaskStatus = PeerTaskStatus.RECEIVED
    result: PeerTaskResult | None = None

    def view(self) -> PeerTaskRecord:
        return PeerTaskRecord(
            verified=self.verified.model_copy(deep=True),
            admission=self.admission.model_copy(deep=True) if self.admission is not None else None,
            status=self.status,
            result=self.result.model_copy(deep=True) if self.result is not None else None,
        )


class InMemoryPeerTaskStore:
    """Loop-local reference ledger for exact replay and lifecycle semantics."""

    def __init__(self) -> None:
        """Create an empty task ledger with sender-scoped replay indexes."""
        self._rows: dict[str, _PeerTaskRow] = {}
        self._message_ids: dict[tuple[str, str, str], str] = {}
        self._idempotency_keys: dict[tuple[str, str, str], str] = {}
        self._nonces: dict[tuple[str, str, str], str] = {}
        self._lock = asyncio.Lock()

    async def receive(self, verified: VerifiedPeerEnvelope) -> tuple[PeerTaskRecord, bool]:
        """Record one exact verified envelope, atomically fencing every replay identity."""
        async with self._lock:
            envelope = verified.envelope
            task_id = envelope.task_id
            existing = self._rows.get(task_id)
            if existing is not None:
                self._require_same_verified(existing.verified, verified)
                return existing.view(), False

            sender_scope = (envelope.sender_peer_id, envelope.recipient_peer_id)
            replay_keys = (
                (self._message_ids, (*sender_scope, envelope.message_id), "message id"),
                (self._idempotency_keys, (*sender_scope, envelope.idempotency_key), "idempotency key"),
                (self._nonces, (*sender_scope, envelope.nonce), "nonce"),
            )
            for index, replay_key, label in replay_keys:
                conflicting_task_id = index.get(replay_key)
                if conflicting_task_id is not None:
                    conflicting = self._rows[conflicting_task_id]
                    self._raise_replay_conflict(label, conflicting.verified, verified)

            row = _PeerTaskRow(verified=verified.model_copy(deep=True))
            self._rows[task_id] = row
            for index, replay_key, _label in replay_keys:
                index[replay_key] = task_id
            return row.view(), True

    async def get(self, task_id: str) -> PeerTaskRecord | None:
        async with self._lock:
            row = self._rows.get(task_id)
            return row.view() if row is not None else None

    async def transition(
        self,
        task_id: str,
        status: PeerTaskStatus,
        *,
        admission: PeerAdmissionDecision | None = None,
    ) -> tuple[PeerTaskRecord, bool]:
        """Advance one legal nonterminal edge with explicit admission evidence."""
        if status in TERMINAL_PEER_TASK_STATUSES:
            msg = f"Terminal peer-task status {status.value!r} requires adopt() evidence."
            raise IllegalPeerTaskTransitionError(msg)
        async with self._lock:
            row = self._require(task_id)
            if row.status is status:
                return row.view(), False
            if status not in LEGAL_PEER_TASK_TRANSITIONS[row.status]:
                msg = f"Illegal peer-task transition for {task_id}: {row.status} → {status}"
                raise IllegalPeerTaskTransitionError(msg)
            if status is PeerTaskStatus.ADMITTED:
                if admission is None or not admission.allowed:
                    msg = "Peer-task admission requires an allowed policy decision."
                    raise IllegalPeerTaskTransitionError(msg)
                row.admission = admission
            elif admission is not None:
                msg = "Admission evidence may only be attached on the admitted transition."
                raise IllegalPeerTaskTransitionError(msg)
            row.status = status
            return row.view(), True

    async def adopt(
        self,
        task_id: str,
        result: PeerTaskResult,
        *,
        admission: PeerAdmissionDecision | None = None,
    ) -> tuple[PeerTaskRecord, bool]:
        """Adopt the first terminal result and leave every later delivery inert."""
        async with self._lock:
            row = self._require(task_id)
            if result.task_id != task_id:
                msg = f"Result for task {result.task_id!r} cannot settle peer task {task_id!r}."
                raise ValueError(msg)
            if row.status in TERMINAL_PEER_TASK_STATUSES:
                return row.view(), False
            if result.status not in LEGAL_PEER_TASK_TRANSITIONS[row.status]:
                msg = f"Illegal peer-task transition for {task_id}: {row.status} → {result.status}"
                raise IllegalPeerTaskTransitionError(msg)
            if admission is not None:
                if result.status is not PeerTaskStatus.REFUSED or admission.allowed:
                    msg = "Only a refused terminal may attach a denied admission decision."
                    raise IllegalPeerTaskTransitionError(msg)
                row.admission = admission
            row.status = result.status
            row.result = result.model_copy(deep=True)
            return row.view(), True

    def _require(self, task_id: str) -> _PeerTaskRow:
        try:
            return self._rows[task_id]
        except KeyError as exc:
            msg = f"Unknown peer task: {task_id}"
            raise UnknownPeerTaskError(msg) from exc

    @staticmethod
    def _require_same_verified(existing: VerifiedPeerEnvelope, incoming: VerifiedPeerEnvelope) -> None:
        if (
            existing.envelope != incoming.envelope
            or existing.canonical_envelope_digest != incoming.canonical_envelope_digest
            or existing.authenticated_peer_id != incoming.authenticated_peer_id
            or existing.key_generation != incoming.key_generation
        ):
            InMemoryPeerTaskStore._raise_replay_conflict("task id", existing, incoming)

    @staticmethod
    def _raise_replay_conflict(
        label: str,
        existing: VerifiedPeerEnvelope,
        incoming: VerifiedPeerEnvelope,
    ) -> None:
        digest_changed = existing.canonical_envelope_digest != incoming.canonical_envelope_digest
        detail = "different canonical content" if digest_changed else "different verified evidence"
        msg = f"Peer {label} was reused with {detail}."
        raise PeerReplayConflictError(msg)


class IntercomAdmissionService:
    """Verify, constrain, record, and locally admit one peer envelope without execution."""

    def __init__(
        self,
        *,
        local_peer_id: str,
        supported_protocol_versions: frozenset[str],
        supported_schema_versions: frozenset[str],
        verifier: PeerEnvelopeVerifier,
        policy: PeerAdmissionPolicy,
        store: PeerTaskStore,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Bind explicit version, verification, policy, and storage authorities."""
        if not local_peer_id.strip():
            msg = "Local peer identity must be non-blank."
            raise ValueError(msg)
        if not supported_protocol_versions or not supported_schema_versions:
            msg = "Intercom admission requires explicit supported protocol and schema versions."
            raise ValueError(msg)
        self._local_peer_id = local_peer_id
        self._supported_protocol_versions = frozenset(supported_protocol_versions)
        self._supported_schema_versions = frozenset(supported_schema_versions)
        self._verifier = verifier
        self._policy = policy
        self._store = store
        self._clock = clock or (lambda: datetime.now(UTC))
        self._admission_lock = asyncio.Lock()

    async def receive(self, message: bytes) -> PeerTaskRecord:
        """Admit one authenticated envelope or retain an explicit refusal terminal."""
        if not message or len(message) > _MAX_WIRE_MESSAGE_BYTES:
            msg = "Peer message is empty or exceeds the bounded wire-message limit."
            raise PeerEnvelopeRejectedError(msg)
        verified = await self._verifier.verify(message)
        envelope = verified.envelope
        if envelope.recipient_peer_id != self._local_peer_id:
            msg = "Peer envelope recipient does not match this node."
            raise PeerEnvelopeRejectedError(msg)
        if envelope.protocol_version not in self._supported_protocol_versions:
            msg = f"Unsupported peer protocol version: {envelope.protocol_version}"
            raise PeerEnvelopeRejectedError(msg)
        if envelope.schema_version not in self._supported_schema_versions:
            msg = f"Unsupported peer schema version: {envelope.schema_version}"
            raise PeerEnvelopeRejectedError(msg)
        now = self._now()
        if envelope.issued_at > now:
            msg = "Peer envelope issue time is in the future."
            raise PeerEnvelopeRejectedError(msg)

        async with self._admission_lock:
            record, created = await self._store.receive(verified)
            if not created and record.status is not PeerTaskStatus.RECEIVED:
                return record
            if envelope.expires_at <= now:
                result = PeerTaskResult(
                    task_id=envelope.task_id,
                    status=PeerTaskStatus.EXPIRED,
                    reason="peer envelope expired before local admission",
                )
                expired, _ = await self._store.adopt(envelope.task_id, result)
                return expired

            decision = await self._policy.decide(verified)
            if envelope.expires_at <= self._now():
                result = PeerTaskResult(
                    task_id=envelope.task_id,
                    status=PeerTaskStatus.EXPIRED,
                    reason="peer envelope expired during local admission",
                )
                expired, _ = await self._store.adopt(envelope.task_id, result)
                return expired
            if not decision.allowed:
                result = PeerTaskResult(
                    task_id=envelope.task_id,
                    status=PeerTaskStatus.REFUSED,
                    reason=decision.reason,
                )
                refused, _ = await self._store.adopt(envelope.task_id, result, admission=decision)
                return refused
            admitted, _ = await self._store.transition(
                envelope.task_id,
                PeerTaskStatus.ADMITTED,
                admission=decision,
            )
            return admitted

    async def queue(self, task_id: str) -> PeerTaskRecord:
        """Move one admitted task to the local queue boundary without publishing it."""
        async with self._admission_lock:
            terminal = await self._expire_or_terminal(task_id)
            if terminal is not None:
                return terminal
            record, _ = await self._store.transition(task_id, PeerTaskStatus.QUEUED)
            return record

    async def start(self, task_id: str) -> PeerTaskRecord:
        """Mark one locally claimed task running without granting execution authority."""
        async with self._admission_lock:
            terminal = await self._expire_or_terminal(task_id)
            if terminal is not None:
                return terminal
            record, _ = await self._store.transition(task_id, PeerTaskStatus.RUNNING)
            return record

    async def adopt(self, task_id: str, result: PeerTaskResult) -> tuple[PeerTaskRecord, bool]:
        """Adopt one terminal result through the first-writer-wins store boundary."""
        async with self._admission_lock:
            terminal = await self._expire_or_terminal(task_id)
            if terminal is not None:
                return terminal, False
            return await self._store.adopt(task_id, result)

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            msg = "Intercom admission clock must return timezone-aware values."
            raise RuntimeError(msg)
        return now

    async def _expire_or_terminal(self, task_id: str) -> PeerTaskRecord | None:
        record = await self._store.get(task_id)
        if record is None:
            return None
        if record.status in TERMINAL_PEER_TASK_STATUSES:
            return record
        if record.verified.envelope.expires_at > self._now():
            return None
        result = PeerTaskResult(
            task_id=task_id,
            status=PeerTaskStatus.EXPIRED,
            reason="peer envelope expired before local lifecycle transition",
        )
        expired, _ = await self._store.adopt(task_id, result)
        return expired
