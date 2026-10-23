"""Operator-public-source sovereign task transport, with no implicit effect retry.

This owner composes actual local authentication, immutable enrolled remote keys,
restricted durable custody, complete signed wire admission and the numeric-pinned
TLS mechanism. Foreign text is returned as attributed data, never tool authority.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from ipaddress import ip_address
from pathlib import Path
from typing import Any, NoReturn, cast
from uuid import UUID, uuid4

from http_message_signatures import algorithms

from lychd.db.intercom import IntercomStore, IntercomStoreError
from lychd.domain.codex.local_access import LocalOperatorAuthentication
from lychd.domain.codex.peer import PeerAuthorityError, PeerObject, PublicDeclaration, PublicTextSource
from lychd.domain.intercom.codec import encode_request, send_params, task_params
from lychd.domain.intercom.native import PeerRunBinding, PeerTaskRef
from lychd.domain.intercom.transport import IntercomEndpoint, IntercomHandoff, PreparedRequest, TaskMethod
from lychd.system.services.intercom_http import BoundedIntercomHTTP, prepare_request, verify_response
from lychd.system.services.peer_authority import PeerAuthority

_NETWORK_ALLOWANCE = 512 * 1024
_MAX_PORT = 65535
_MIN_PATH_CHARACTER = 33
_MAX_PATH_BYTES = 1024
_MAX_KEY_ID_BYTES = 128


def _refuse(code: str) -> NoReturn:
    raise PeerAuthorityError(code) from None


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _status(task: dict[str, Any]) -> dict[str, Any]:
    return {
        key: task.get(key)
        for key in (
            "task_id",
            "status",
            "local_status",
            "foreign_task_id",
            "foreign_status",
            "context_id",
            "cancellation_observation",
            "adoption_closed",
            "closure_reason",
        )
    }


def _instant(value: str) -> datetime:
    try:
        instant = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        _refuse("validity")
    if instant.tzinfo is None:
        _refuse("validity")
    return instant


def _endpoint(record: dict[str, Any]) -> tuple[IntercomEndpoint, str]:
    try:
        if set(record) != {"address", "hostname", "port", "path", "ca_file"}:
            _refuse("endpoint")
        address, hostname, port, path, ca_file = (
            record["address"],
            record["hostname"],
            record["port"],
            record["path"],
            record["ca_file"],
        )
        if (
            not all(type(value) is str for value in (address, hostname, path, ca_file))
            or str(ip_address(address)) != address
            or type(port) is not int
            or not 1 <= port <= _MAX_PORT
            or not hostname
            or not hostname.isascii()
            or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-:" for char in hostname)
            or not path.startswith("/")
            or path.startswith("//")
            or not path.isascii()
            or any(ord(char) < _MIN_PATH_CHARACTER or char in "?#\\" for char in path)
            or len(path) > _MAX_PATH_BYTES
            or not Path(ca_file).is_absolute()
        ):
            _refuse("endpoint")
        authority = f"[{hostname}]" if ":" in hostname else hostname
        uri = f"https://{authority}:{port}{path}"
        return IntercomEndpoint(address=address, hostname=hostname, port=port, path=path, ca_file=Path(ca_file)), uri
    except (KeyError, TypeError, ValueError):
        _refuse("endpoint")


@dataclass(slots=True)
class _LiveDeclaration:
    declaration: PublicDeclaration
    source: PublicTextSource
    consumed: bool = False


class _TransmissionGate:
    """One acknowledged claim's finite synchronous check-and-syscall boundary."""

    def __init__(
        self,
        service: IntercomService,
        authentication: object,
        action: str,
        target: PeerObject,
        peer: dict[str, Any],
        task: dict[str, Any],
        endpoint: IntercomEndpoint,
        prepared: PreparedRequest,
        current: Callable[[], None] | None = None,
    ) -> None:
        self.service = service
        self.authentication = authentication
        self.action = action
        self.target = target
        self.peer = peer
        self.task = task
        self.endpoint = endpoint
        self.prepared = prepared
        self.current = current
        self.accepted = 0
        self.active = True
        self._offered = 0

    def handoff(self, handoff: IntercomHandoff, action: Callable[[], int]) -> int:
        """Consume pending capacity before the same-turn physical handoff."""
        self.service.check_current(
            self.authentication, self.action, self.target, self.peer, self.task, current=self.current
        )
        if (
            not self.active
            or handoff.target != self.endpoint
            or handoff.phase not in {"connect", "tls", "http"}
            or (handoff.phase == "connect" and handoff.wire_bytes != b"")
            or (handoff.phase == "tls" and handoff.application_bytes is not None)
            or (handoff.phase == "http" and handoff.application_bytes != self.prepared.wire)
            or self._offered + len(handoff.wire_bytes) > _NETWORK_ALLOWANCE
        ):
            _refuse("wire-gate")
        self._offered += len(handoff.wire_bytes)
        result = action()
        if type(result) is not int or (handoff.phase != "connect" and not 0 < result <= len(handoff.wire_bytes)):
            _refuse("handoff")
        if handoff.phase != "connect":
            self.accepted += result
        return result


class IntercomUnknownError(PeerAuthorityError):
    """Unknown external execution with the durable local identity for reconciliation."""

    def __init__(self, task_id: UUID) -> None:
        """Expose an opaque task identity, never a source or foreign diagnostic."""
        self.task_id = task_id
        super().__init__("unknown")


class IntercomService:
    """Callable production operations; construction reads no ambient credential.

    One instance/control loop owns live declarations and fresh claims. Restart
    creates neither; a known durable foreign task may be explicitly polled with
    a newly authenticated marker and current exact policy. Native contact also
    requires the host's live per-operation Run permission; retirement owns the
    actual preparation and transport coroutines rather than only their gates.
    """

    def __init__(
        self,
        *,
        store: IntercomStore,
        authority: PeerAuthority,
        workload_id: UUID,
        signing_key: bytes,
        signing_key_id: str,
    ) -> None:
        """Compose trusted custody and an in-memory workload signing credential."""
        if not signing_key_id or not signing_key_id.isascii() or len(signing_key_id) > _MAX_KEY_ID_BYTES:
            _refuse("signing-key")
        try:
            key = algorithms.ED25519(private_key=signing_key)  # pyright: ignore[reportPrivateImportUsage]
            self._role_probe = b"lychd-outbound-public-text@1-role-separation"
            self._role_signature = cast("bytes", key.sign(self._role_probe))
            # Ed25519 is deterministic: this public fixed-message signature binds
            # the actual workload credential without retaining private key bytes.
            self._workload_key_binding = _digest(self._role_signature)
        except Exception:  # noqa: BLE001 - declared adapter errors never expose key material
            _refuse("signing-key")
        self._store = store
        self._authority = authority
        self._workload_id = workload_id
        self._signing_key = signing_key
        self._signing_key_id = signing_key_id
        self._http = BoundedIntercomHTTP()
        self._declarations: dict[UUID, _LiveDeclaration] = {}
        self._native_declarations: dict[UUID, UUID] = {}
        self._pending: dict[UUID, _TransmissionGate] = {}
        self._closed_adoption: set[UUID] = set()
        self._native_guards: dict[UUID, Callable[[], None]] = {}
        self._native_task_runs: dict[UUID, str] = {}
        self._retired_native_runs: set[str] = set()
        self._native_retirement_failures: set[str] = set()
        self._native_exchanges: dict[UUID, tuple[str, asyncio.Task[dict[str, Any]]]] = {}
        self._native_submits: dict[UUID, asyncio.Task[dict[str, Any]]] = {}
        self._abandoned_native_submits: set[UUID] = set()
        self._native_preparations: dict[UUID, tuple[str, asyncio.Task[dict[str, Any]]]] = {}

    def bind_native_guard(self, task_id: UUID, callback: Callable[[], None]) -> None:
        """Bind the host's live exact Run/claim permission; no retained row can supply it."""
        self._native_guards[task_id] = callback

    def fence_abandoned_native_submit(self, *, run_id: str, task_id: UUID) -> None:
        """Prove no owned submit remains, then permanently fence its activation road.

        This is local retirement evidence only. It neither proves zero remote
        execution nor constructs a replacement physical claim or transmission.
        """
        if self._native_task_runs.get(task_id) != run_id or run_id in self._native_retirement_failures:
            _refuse("native-binding")
        operation = self._native_submits.get(task_id)
        if operation is not None and not operation.done():
            _refuse("native-submit-active")
        if any(
            gate.active and gate.prepared.method == "SendMessage" and str(gate.task.get("task_id")) == str(task_id)
            for gate in self._pending.values()
        ):
            _refuse("native-submit-active")
        self._abandoned_native_submits.add(task_id)

    def _native_current(
        self,
        task_id: UUID | None,
        task: dict[str, Any] | None,
        current: Callable[[], None] | None,
    ) -> None:
        if current is not None:
            current()
        if task_id is None:
            return
        run_id = task.get("native_run_id") if task is not None else self._native_task_runs.get(task_id)
        if run_id is None:
            return
        self._native_task_runs[task_id] = str(run_id)
        if str(run_id) in self._retired_native_runs:
            _refuse("native-retired")
        guard = current or self._native_guards.get(task_id)
        if guard is None:
            _refuse("native-permission")
        if guard is not current:
            guard()

    def check_native(self, authentication: object, action: str, binding: PeerRunBinding) -> None:
        """Check the actual currently issued marker and exact immutable native target."""
        self._authority.check(
            authentication,
            action,
            self._target(
                binding.peer_id,
                purpose=binding.purpose,
                task_schema=binding.task_schema,
                category=binding.category,
                endpoint=binding.endpoint,
                content_digest=binding.text_digest,
            ),
        )
        if binding.expires_at.tzinfo is None or binding.expires_at <= datetime.now(UTC):
            _refuse("native-expiry")

    async def retire_native_run(  # noqa: C901 - fence, cancellation and required retirement form one lifecycle
        self,
        run_id: str,
        *,
        close_adoption: bool = True,
    ) -> None:
        """Retire local work; cancellation closes adoption, while process shutdown preserves waits."""
        try:
            run_id = str(UUID(run_id))
        except ValueError:
            _refuse("native-binding")
        self._retired_native_runs.add(run_id)
        owned = [
            task
            for owner, task in (*self._native_exchanges.values(), *self._native_preparations.values())
            if owner == run_id
        ]
        for gate in self._pending.values():
            if str(gate.task.get("native_run_id")) == run_id:
                gate.active = False
        for task in owned:
            task.cancel()
        closure_error: BaseException | None = None
        try:
            if close_adoption:
                await self._store.close_native_run(run_id)
        except BaseException as error:  # noqa: BLE001 - closure failure must still await local retirement
            closure_error = error
        finally:
            # A failed durable closure never skips actual coroutine/socket teardown.
            retired = asyncio.gather(*owned, return_exceptions=True)
            while True:
                try:
                    outcomes = await asyncio.shield(retired)
                    break
                except asyncio.CancelledError as error:
                    closure_error = closure_error or error
        if any(
            isinstance(outcome, BaseException) and not isinstance(outcome, asyncio.CancelledError)
            for outcome in outcomes
        ):
            self._native_retirement_failures.add(run_id)
        if closure_error is not None:
            raise closure_error
        if run_id in self._native_retirement_failures:
            _refuse("native-retirement")

    def _target(
        self,
        peer_id: UUID,
        *,
        purpose: str,
        task_schema: str,
        category: str,
        endpoint: str,
        task_id: UUID | None = None,
        content_digest: str | None = None,
    ) -> PeerObject:
        return PeerObject(peer_id, purpose, category, task_schema, endpoint, task_id, content_digest)

    def _key(self, peer: dict[str, Any]) -> dict[str, Any]:
        key = cast("dict[str, Any]", peer["current_key"])
        now = datetime.now(UTC)
        if (
            key.get("issuer") != str(peer["peer_id"])
            or key.get("protocol") != "rfc9421-ed25519@1"
            or key.get("audience") != str(self._workload_id)
            or key.get("assurance") != "operator-enrolled"
            or not _instant(key["valid_from"]) <= now < _instant(key["expires_at"])
        ):
            _refuse("peer-key")
        try:
            public = algorithms.ED25519(public_key=key["public_key_pem"].encode("ascii"))  # pyright: ignore[reportPrivateImportUsage]
        except Exception:  # noqa: BLE001 - reject all invalid enrolled key representations
            _refuse("peer-key")
        try:
            public.verify(self._role_signature, self._role_probe)
        except Exception as error:  # noqa: BLE001 - only installed adapter InvalidSignature proves distinctness
            # The pinned declared adapter delegates this verified mismatch to cryptography.
            if type(error).__name__ != "InvalidSignature" or type(error).__module__ != "cryptography.exceptions":
                _refuse("peer-key")
        else:
            _refuse("peer-key")
        return key

    def check_current(
        self,
        authentication: object,
        action: str,
        target: PeerObject,
        peer: dict[str, Any],
        task: dict[str, Any] | None = None,
        *,
        current: Callable[[], None] | None = None,
        allow_expired_native_disposition: bool = False,
    ) -> None:
        if allow_expired_native_disposition and (
            action not in {"adopt", "resume"} or task is None or task.get("native_run_id") is None
        ):
            _refuse("native-binding")
        self._authority.check(authentication, action, target)
        if action == "submit" and target.task_id in self._abandoned_native_submits:
            _refuse("native-submit-abandoned")
        self._native_current(target.task_id, task, current)
        policy = self._authority.policy
        if (
            not self._authority.credential_current(target.peer_id, peer["key_version"])
            or peer.get("revoked") is not False
            or peer.get("policy_generation") != policy.generation
            or peer.get("policy") != policy.record()
            or str(peer.get("workload_id")) != str(self._workload_id)
            or peer.get("workload_key_id") != self._signing_key_id
            or peer.get("workload_key_binding") != self._workload_key_binding
        ):
            _refuse("current-peer")
        self._key(peer)
        if (
            task is not None
            and UUID(str(task["task_id"])) in self._closed_adoption
            and task.get("local_status") != "cancelled"
            and action != "cancel"
        ):
            _refuse("adoption-closed")
        if task is not None and (
            (datetime.now(UTC) >= _instant(task["expires_at"]) and not allow_expired_native_disposition)
            or task["policy_generation"] != peer["policy_generation"]
            or task["key_version"] != peer["key_version"]
            or task["revocation_generation"] != peer["revocation_generation"]
        ):
            _refuse("current-task")

    async def enroll(
        self,
        authentication: object,
        *,
        peer_id: UUID,
        endpoint: dict[str, Any],
        task_schema: str,
        purpose: str,
        key: dict[str, Any],
        category: str = "public-task",
    ) -> dict[str, Any]:
        """Enroll one explicit remote Principal and immutable initial credential."""
        _, uri = _endpoint(endpoint)
        target = self._target(peer_id, purpose=purpose, task_schema=task_schema, category=category, endpoint=uri)
        self._authority.check(authentication, "enroll", target)
        if peer_id == self._workload_id:
            _refuse("identity")
        record = {
            "endpoint": endpoint.copy(),
            "task_schema": task_schema,
            "purpose": purpose,
            "category": category,
            "workload_id": str(self._workload_id),
            "workload_key_id": self._signing_key_id,
            "workload_key_binding": self._workload_key_binding,
            "key": key.copy(),
            "policy": self._authority.policy.record(),
        }
        # Validate the intended remote key before persisting any enrollment.
        self._key({"peer_id": str(peer_id), "current_key": key})
        try:
            retained = await self._store.enroll(peer_id, record)
        except BaseException:
            self._authority.uncertain(peer_id)
            raise
        self.check_current(authentication, "enroll", target, retained)
        return retained

    async def _peer_target(
        self,
        authentication: object,
        action: str,
        peer_id: UUID,
        *,
        purpose: str,
        task_schema: str,
        category: str,
        endpoint: str,
        task_id: UUID | None = None,
        current: Callable[[], None] | None = None,
    ) -> tuple[dict[str, Any], PeerObject]:
        target = self._target(
            peer_id, purpose=purpose, task_schema=task_schema, category=category, endpoint=endpoint, task_id=task_id
        )
        self._authority.check(authentication, action, target)
        self._native_current(task_id, None, current)
        peer = await self._store.peer(peer_id)
        self.check_current(authentication, action, target, peer, current=current)
        if (peer["purpose"], peer["task_schema"], peer["category"]) != (purpose, task_schema, category):
            _refuse("target")
        _, retained_uri = _endpoint(peer["endpoint"])
        if retained_uri != endpoint:
            _refuse("target")
        return peer, target

    async def declare_public(
        self,
        authentication: object,
        *,
        peer_id: UUID,
        purpose: str,
        task_schema: str,
        endpoint: str,
        source: PublicTextSource,
    ) -> PublicDeclaration:
        """Record a current separately authorized attributed public-source assertion."""
        source.validate()
        peer, target = await self._peer_target(
            authentication,
            "classify_public",
            peer_id,
            purpose=purpose,
            task_schema=task_schema,
            category=source.category,
            endpoint=endpoint,
        )
        if not isinstance(authentication, LocalOperatorAuthentication):
            _refuse("authentication")
        policy = self._authority.policy
        source_record = asdict(source)
        declaration = PublicDeclaration(
            uuid4(),
            uuid4(),
            target,
            authentication.subject,
            authentication.authentication_generation,
            policy.generation,
            policy.digest,
            datetime.now(UTC) + timedelta(seconds=policy.declaration_seconds),
            _digest(source.text.encode("utf-8")),
            _digest(_json(source_record)),
        )
        await self._store.declare(
            declaration.declaration_id,
            {
                "peer_id": str(peer_id),
                "operation_id": str(declaration.operation_id),
                "policy_generation": policy.generation,
                "policy_digest": policy.digest,
                "subject": declaration.subject,
                "authentication_generation": str(declaration.authentication_generation),
                "purpose": purpose,
                "task_schema": task_schema,
                "category": source.category,
                "endpoint": endpoint,
                "expires_at": declaration.expires_at.isoformat(),
                "text_digest": declaration.text_digest,
                "source_digest": declaration.source_digest,
                "source": source_record,
            },
        )
        self.check_current(authentication, "classify_public", target, peer)
        self._declarations[declaration.declaration_id] = _LiveDeclaration(declaration, source)
        return declaration

    def _declaration(self, authentication: object, declaration: PublicDeclaration) -> _LiveDeclaration:
        live = self._declarations.get(declaration.declaration_id)
        policy = self._authority.policy
        if (
            live is None
            or live.declaration is not declaration
            or live.consumed
            or declaration.expires_at <= datetime.now(UTC)
            or declaration.policy_generation != policy.generation
            or declaration.policy_digest != policy.digest
            or not self._authority.current_binding(declaration.subject, declaration.authentication_generation)
            or _digest(live.source.text.encode("utf-8")) != declaration.text_digest
            or _digest(_json(asdict(live.source))) != declaration.source_digest
        ):
            _refuse("declaration")
        self._authority.check(authentication, "submit", declaration.target)
        return live

    async def submit(self, authentication: object, *, declaration: PublicDeclaration) -> dict[str, Any]:
        """Commit immutable intent, charge once and submit once; unknown is never resent."""
        live = self._declaration(authentication, declaration)
        target = declaration.target
        peer, _ = await self._peer_target(
            authentication,
            "submit",
            target.peer_id,
            purpose=target.purpose,
            task_schema=target.task_schema,
            category=target.category,
            endpoint=target.endpoint,
        )
        live = self._declaration(authentication, declaration)
        live.consumed = True  # Before the next await: even uncertain commit cannot mint another task.
        task_id, attempt_id = uuid4(), uuid4()
        params = send_params(live.source.text, str(task_id))
        prepared = self._prepare(target, task_id, attempt_id, "SendMessage", params)
        record = {
            "peer_id": str(target.peer_id),
            "declaration_id": str(declaration.declaration_id),
            "operation_id": str(declaration.operation_id),
            "purpose": target.purpose,
            "task_schema": target.task_schema,
            "category": target.category,
            "endpoint": target.endpoint,
            "expires_at": (datetime.now(UTC) + timedelta(seconds=self._authority.policy.task_seconds)).isoformat(),
            "body": prepared.body.decode("utf-8"),
            "policy_generation": peer["policy_generation"],
            "key_version": peer["key_version"],
            "revocation_generation": peer["revocation_generation"],
        }
        try:
            task = await self._store.create_task(task_id, record)
            self.check_current(authentication, "submit", target, peer, task)
            return await self._transmit(authentication, "submit", target, peer, task, prepared)
        except IntercomStoreError as error:
            if error.code == "commit-unknown":
                raise IntercomUnknownError(task_id) from None
            raise

    async def prepare_native(
        self,
        authentication: object,
        *,
        binding: PeerRunBinding,
        ref: PeerTaskRef,
        pattern_digest: str,
        enqueue_seq: int,
        step_id: str,
        occurrence_id: str,
    ) -> dict[str, Any]:
        """Own preparation so retirement also fences and awaits pre-park custody work."""
        self.check_native(authentication, "submit", binding)
        self._native_task_runs[ref.task_id] = ref.run_id
        self._native_current(ref.task_id, None, None)
        operation_id = uuid4()
        operation = asyncio.create_task(
            self._prepare_native_owned(
                authentication,
                binding=binding,
                ref=ref,
                pattern_digest=pattern_digest,
                enqueue_seq=enqueue_seq,
                step_id=step_id,
                occurrence_id=occurrence_id,
            ),
            name=f"intercom-native-prepare-{operation_id}",
        )
        self._native_preparations[operation_id] = (ref.run_id, operation)
        try:
            task = await operation
            self.check_native(authentication, "submit", binding)
            self._native_current(ref.task_id, task, None)
            return task
        finally:
            self._native_preparations.pop(operation_id, None)

    async def _prepare_native_owned(  # noqa: C901 - keep exact original source and immutable preparation checks together
        self,
        authentication: object,
        *,
        binding: PeerRunBinding,
        ref: PeerTaskRef,
        pattern_digest: str,
        enqueue_seq: int,
        step_id: str,
        occurrence_id: str,
    ) -> dict[str, Any]:
        """Seal the original native source and lifetime without any network contact."""
        self.check_native(authentication, "submit", binding)
        if ref.binding_digest != binding.digest or ref.request_id != binding.request_id:
            _refuse("native-binding")
        live = self._declarations.get(binding.declaration_id)
        if live is not None:
            if live.consumed and self._native_declarations.get(binding.declaration_id) != ref.task_id:
                _refuse("declaration")
            live.consumed = True
            self._native_declarations[binding.declaration_id] = ref.task_id
        self._native_task_runs[ref.task_id] = ref.run_id
        self._native_current(ref.task_id, None, None)
        peer, target = await self._peer_target(
            authentication,
            "submit",
            binding.peer_id,
            purpose=binding.purpose,
            task_schema=binding.task_schema,
            category=binding.category,
            endpoint=binding.endpoint,
            task_id=ref.task_id,
        )
        self.check_native(authentication, "submit", binding)
        declaration = await self._store.declaration(binding.declaration_id)
        self.check_current(authentication, "submit", target, peer)
        for field in (
            "peer_id",
            "declaration_id",
            "operation_id",
            "purpose",
            "task_schema",
            "endpoint",
            "category",
            "source_digest",
            "text_digest",
        ):
            if str(declaration.get(field)) != str(getattr(binding, field)):
                _refuse("native-source")
        raw_source = declaration.get("source")
        if not isinstance(raw_source, dict):
            _refuse("native-source")
        raw_source = cast("dict[str, Any]", raw_source)
        try:
            source_record: dict[str, Any] = {
                **raw_source,
                "source_manifest": tuple(raw_source["source_manifest"]),
                "influence_manifest": tuple(raw_source["influence_manifest"]),
            }
            source = PublicTextSource(**source_record)
            source.validate()
        except (TypeError, KeyError):
            _refuse("native-source")
        if (
            _digest(_json(asdict(source))) != binding.source_digest
            or _digest(source.text.encode()) != binding.text_digest
        ):
            _refuse("native-source")
        body = encode_request("SendMessage", str(ref.task_id), send_params(source.text, str(ref.task_id)))
        record = {
            "peer_id": str(binding.peer_id),
            "declaration_id": str(binding.declaration_id),
            "operation_id": str(binding.operation_id),
            "purpose": binding.purpose,
            "task_schema": binding.task_schema,
            "category": binding.category,
            "endpoint": binding.endpoint,
            "expires_at": binding.expires_at.isoformat(),
            "body": body.decode(),
            "source_digest": binding.source_digest,
            "text_digest": binding.text_digest,
            "policy_generation": peer["policy_generation"],
            "key_version": peer["key_version"],
            "revocation_generation": peer["revocation_generation"],
        }
        self.check_current(authentication, "submit", target, peer)
        try:
            task = await self._store.create_native_task(
                ref.task_id,
                record,
                ref=ref,
                pattern_digest=pattern_digest,
                enqueue_seq=enqueue_seq,
                step_id=step_id,
                occurrence_id=occurrence_id,
            )
        except IntercomStoreError as error:
            if error.code == "commit-unknown":
                raise IntercomUnknownError(ref.task_id) from None
            raise
        self.check_current(authentication, "submit", target, peer, task)
        return task

    async def send_prepared(
        self,
        authentication: object,
        *,
        task_id: UUID,
        peer_id: UUID,
        purpose: str,
        task_schema: str,
        endpoint: str,
        category: str = "public-task",
        current: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        """Submit a provably unclaimed retained body once with a fresh signed wrapper."""
        peer, task, target = await self._load_task(
            authentication,
            "submit",
            task_id=task_id,
            peer_id=peer_id,
            purpose=purpose,
            task_schema=task_schema,
            endpoint=endpoint,
            category=category,
            current=current,
        )
        if (
            task.get("submit_claimed") is not False
            or task.get("foreign_task_id") is not None
            or task.get("local_status") != "prepared"
            or task.get("adoption_closed")
        ):
            _refuse("claimed")
        try:
            params = json.loads(task["body"])["params"]
        except (TypeError, ValueError, KeyError):
            _refuse("sealed-body")
        prepared = self._prepare(target, task_id, uuid4(), "SendMessage", params)
        self.check_current(authentication, "submit", target, peer, task, current=current)
        return await self._transmit(authentication, "submit", target, peer, task, prepared, current=current)

    def _prepare(
        self,
        target: PeerObject,
        task_id: UUID,
        attempt_id: UUID,
        method: TaskMethod,
        params: dict[str, object],
        *,
        context_id: str | None = None,
    ) -> PreparedRequest:
        return prepare_request(
            method=method,
            local_task_id=str(task_id),
            attempt_id=str(attempt_id),
            peer_id=str(target.peer_id),
            workload_id=str(self._workload_id),
            task_schema=target.task_schema,
            endpoint=target.endpoint,
            params=params,
            signing_key=self._signing_key,
            key_id=self._signing_key_id,
            expected_context_id=context_id,
        )

    async def _load_task(
        self,
        authentication: object,
        action: str,
        *,
        task_id: UUID,
        peer_id: UUID,
        purpose: str,
        task_schema: str,
        endpoint: str,
        category: str,
        current: Callable[[], None] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], PeerObject]:
        peer, target = await self._peer_target(
            authentication,
            action,
            peer_id,
            purpose=purpose,
            task_schema=task_schema,
            category=category,
            endpoint=endpoint,
            task_id=task_id,
            current=current,
        )
        self.check_current(authentication, action, target, peer, current=current)
        task = await self._store.task(task_id, peer_id=peer_id)
        self.check_current(authentication, action, target, peer, task, current=current)
        if (
            str(task["peer_id"]) != str(peer_id)
            or task["purpose"] != purpose
            or task["task_schema"] != task_schema
            or task["endpoint"] != endpoint
        ):
            _refuse("task-object")
        return peer, task, target

    async def poll(
        self,
        authentication: object,
        *,
        task_id: UUID,
        peer_id: UUID,
        purpose: str,
        task_schema: str,
        endpoint: str,
        category: str = "public-task",
        current: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        """Authorize a fresh safe read of a known receiver task identity."""
        peer, task, target = await self._load_task(
            authentication,
            "poll",
            task_id=task_id,
            peer_id=peer_id,
            purpose=purpose,
            task_schema=task_schema,
            endpoint=endpoint,
            category=category,
            current=current,
        )
        if not task.get("foreign_task_id"):
            _refuse("foreign-task-unknown")
        prepared = self._prepare(
            target,
            task_id,
            uuid4(),
            "GetTask",
            task_params("GetTask", task["foreign_task_id"]),
            context_id=task.get("context_id"),
        )
        return await self._transmit(authentication, "poll", target, peer, task, prepared, current=current)

    async def cancel(
        self,
        authentication: object,
        *,
        task_id: UUID,
        peer_id: UUID,
        purpose: str,
        task_schema: str,
        endpoint: str,
        category: str = "public-task",
        current: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        """Request cancellation; its acknowledgement is no rollback or containment proof."""
        peer, task, target = await self._load_task(
            authentication,
            "cancel",
            task_id=task_id,
            peer_id=peer_id,
            purpose=purpose,
            task_schema=task_schema,
            endpoint=endpoint,
            category=category,
            current=current,
        )
        if not task.get("foreign_task_id"):
            _refuse("foreign-task-unknown")
        if task.get("local_status") == "terminal":
            _refuse("terminal")
        self._closed_adoption.add(task_id)
        task = await self._store.close_task(task_id, peer_id=peer_id, reason="cancelled")
        if task.get("local_status") == "terminal":
            # Admission linearized before this cancellation election; retain its result.
            self._closed_adoption.discard(task_id)
            _refuse("terminal")
        self.check_current(authentication, "cancel", target, peer, task, current=current)
        prepared = self._prepare(
            target,
            task_id,
            uuid4(),
            "CancelTask",
            task_params("CancelTask", task["foreign_task_id"]),
            context_id=task.get("context_id"),
        )
        return await self._transmit(authentication, "cancel", target, peer, task, prepared, current=current)

    async def _transmit(
        self,
        authentication: object,
        action: str,
        target: PeerObject,
        peer: dict[str, Any],
        task: dict[str, Any],
        prepared: PreparedRequest,
        *,
        current: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        """Own native exchange execution so local retirement can cancel and await it."""
        self.check_current(authentication, action, target, peer, task, current=current)
        if task.get("native_run_id") is None:
            return await self._transmit_owned(authentication, action, target, peer, task, prepared, current=current)
        if current is None:
            _refuse("native-permission")
        attempt_id = UUID(prepared.attempt_id)
        task_id = UUID(str(task["task_id"]))
        if prepared.method == "SendMessage" and task_id in self._native_submits:
            _refuse("native-submit-active")
        operation = asyncio.create_task(
            self._transmit_owned(authentication, action, target, peer, task, prepared, current=current),
            name=f"intercom-native-{attempt_id}",
        )
        self._native_exchanges[attempt_id] = (str(task["native_run_id"]), operation)
        if prepared.method == "SendMessage":
            self._native_submits[task_id] = operation
        try:
            result = await operation
            self.check_current(authentication, action, target, peer, task, current=current)
            return result
        finally:
            self._native_exchanges.pop(attempt_id, None)
            if self._native_submits.get(task_id) is operation:
                self._native_submits.pop(task_id, None)

    async def _transmit_owned(
        self,
        authentication: object,
        action: str,
        target: PeerObject,
        peer: dict[str, Any],
        task: dict[str, Any],
        prepared: PreparedRequest,
        *,
        current: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        self.check_current(authentication, action, target, peer, task, current=current)
        endpoint, uri = _endpoint(peer["endpoint"])
        if uri != prepared.request_uri or (prepared.method == "SendMessage" and prepared.body != task["body"]):
            _refuse("sealed-body")
        attempt_id = UUID(prepared.attempt_id)
        task_id = UUID(str(task["task_id"]))
        await self._store.claim(
            task_id,
            attempt_id,
            {
                "method": prepared.method,
                "application_bytes": len(prepared.wire),
                "network_bytes": _NETWORK_ALLOWANCE,
                "wire_digest": _digest(prepared.wire),
                "policy_generation": peer["policy_generation"],
                "key_version": peer["key_version"],
                "revocation_generation": peer["revocation_generation"],
                "request_body_digest": prepared.digest,
                "request_nonce": prepared.nonce,
                "policy_digest": self._authority.policy.digest,
                "target": {
                    **asdict(target),
                    "peer_id": str(target.peer_id),
                    "task_id": str(target.task_id) if target.task_id else None,
                },
            },
            self._authority.policy.limits(),
        )
        # Only this acknowledged fresh claim creates a live owner; no row-to-gate constructor exists.
        self.check_current(authentication, action, target, peer, task, current=current)
        gate = _TransmissionGate(self, authentication, action, target, peer, task, endpoint, prepared, current)
        self._pending[attempt_id] = gate
        try:
            response = await self._http.exchange(
                endpoint,
                prepared,
                gate=gate,
                deadline=time.monotonic() + self._authority.policy.network_seconds,
            )
            self.check_current(authentication, action, target, peer, task, current=current)
            key = self._key(peer)
            observation = verify_response(
                prepared,
                response.status,
                response.headers,
                response.body,
                peer_public_key=key["public_key_pem"].encode("ascii"),
                key_id=key["key_id"],
            )
            self.check_current(authentication, action, target, peer, task, current=current)
            settled = await self._store.settle(
                task_id,
                attempt_id,
                {
                    "status": "received",
                    "accepted_network_bytes": gate.accepted,
                    "foreign_task_id": observation.foreign_task_id,
                    "foreign_status": observation.state,
                    "context_id": observation.context_id,
                    "terminal": observation.terminal,
                    "result": {"text": list(observation.text), "origin": "authenticated-foreign-data"},
                    "response_nonce": observation.response_nonce,
                    "response_digest": _digest(response.body),
                },
                current=lambda: self.check_current(authentication, action, target, peer, task, current=current),
            )
            self.check_current(authentication, action, target, peer, task, current=current)
        except BaseException as error:
            # No exception authorizes retry. Even signature/refusal errors leave remote execution unknown.
            with contextlib.suppress(BaseException):
                await self._store.settle(
                    task_id,
                    attempt_id,
                    {"status": "unknown", "accepted_network_bytes": gate.accepted, "local_status": "unknown"},
                )
            if isinstance(error, Exception):
                raise IntercomUnknownError(task_id) from None
            raise
        else:
            return _status(settled)
        finally:
            gate.active = False
            self._pending.pop(attempt_id, None)

    async def read(
        self,
        authentication: object,
        *,
        task_id: UUID,
        peer_id: UUID,
        purpose: str,
        task_schema: str,
        endpoint: str,
        category: str = "public-task",
        current: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        """Consume retained authenticated foreign data under a fresh read decision."""
        peer, task, target = await self._load_task(
            authentication,
            "read",
            task_id=task_id,
            peer_id=peer_id,
            purpose=purpose,
            task_schema=task_schema,
            endpoint=endpoint,
            category=category,
            current=current,
        )
        self.check_current(authentication, "read", target, peer, task, current=current)
        return task

    async def rotate(
        self,
        authentication: object,
        *,
        peer_id: UUID,
        purpose: str,
        task_schema: str,
        endpoint: str,
        key: dict[str, Any],
        category: str = "public-task",
    ) -> dict[str, Any]:
        """Append a remote credential version; fence pending old-key effects first."""
        peer, _target = await self._peer_target(
            authentication,
            "rotate",
            peer_id,
            purpose=purpose,
            task_schema=task_schema,
            category=category,
            endpoint=endpoint,
        )
        self._key({**peer, "current_key": key})
        if key["key_id"] == peer["current_key"]["key_id"]:
            _refuse("key-reuse")
        self._authority.retire_key(peer_id, peer["key_version"])
        try:
            retained = await self._store.rotate(peer_id, key)
            self.check_current(authentication, "rotate", _target, retained)
        except BaseException:
            self._authority.uncertain(peer_id)
            raise
        else:
            return retained

    async def revoke(
        self,
        authentication: object,
        *,
        peer_id: UUID,
        purpose: str,
        task_schema: str,
        endpoint: str,
        category: str = "public-task",
    ) -> dict[str, Any]:
        """Fence local handoffs synchronously before awaiting durable revocation."""
        _, target = await self._peer_target(
            authentication,
            "revoke",
            peer_id,
            purpose=purpose,
            task_schema=task_schema,
            category=category,
            endpoint=endpoint,
        )
        self._authority.check(authentication, "revoke", target)
        self._authority.fence(peer_id)
        try:
            retained = await self._store.revoke(peer_id)
            self._authority.check_revocation_completion(authentication, target)
        except BaseException:
            self._authority.uncertain(peer_id)
            raise
        else:
            return retained
