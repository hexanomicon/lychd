from __future__ import annotations

from collections.abc import Callable

# Unit fixtures use only ephemeral keys/credentials and never contact the test address.
# ruff: noqa: ARG002, S106, S108
# pyright: reportPrivateUsage=false
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, cast
from uuid import UUID, uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

from lychd.db.intercom import IntercomStore, IntercomStoreError
from lychd.domain.codex.local_access import LocalOperatorAccess, LocalOperatorAuthentication
from lychd.domain.codex.peer import CapacityLimit, PeerAuthorityError, PeerPolicy, PublicTextSource
from lychd.system.services.intercom import IntercomService, IntercomUnknownError
from lychd.system.services.peer_authority import PeerAuthority


class MemoryCustody:
    def __init__(self) -> None:
        self.peers: dict[UUID, dict[str, Any]] = {}
        self.tasks: dict[UUID, dict[str, Any]] = {}
        self.claims = 0
        self.before_declare: Any = None
        self.before_task: Any = None
        self.failure_stage: str | None = None

    async def enroll(self, peer_id: UUID, record: dict[str, Any]) -> dict[str, Any]:
        peer = {
            **record,
            "peer_id": str(peer_id),
            "current_key": record["key"],
            "key_version": 1,
            "policy_generation": record["policy"]["generation"],
            "revocation_generation": 0,
            "revoked": False,
        }
        self.peers[peer_id] = peer
        return peer

    async def peer(self, peer_id: UUID) -> dict[str, Any]:
        return self.peers[peer_id]

    async def declare(self, declaration_id: UUID, record: dict[str, Any]) -> None:
        if self.before_declare:
            self.before_declare()

    async def create_task(self, task_id: UUID, record: dict[str, Any]) -> dict[str, Any]:
        self.tasks[task_id] = {
            **record,
            "body": record["body"].encode(),
            "task_id": str(task_id),
            "foreign_task_id": None,
            "context_id": None,
            "status": "prepared",
        }
        if self.before_task:
            self.before_task()
        if self.failure_stage == "create_task":
            msg = "commit-unknown"
            raise IntercomStoreError(msg)
        return self.tasks[task_id]

    async def task(self, task_id: UUID, *, peer_id: UUID) -> dict[str, Any]:
        task = self.tasks[task_id]
        if task["peer_id"] != str(peer_id):
            raise ValueError
        return task

    async def claim(
        self, task_id: UUID, attempt_id: UUID, record: dict[str, Any], limits: dict[str, Any]
    ) -> dict[str, Any]:
        self.claims += 1
        if self.failure_stage == "claim":
            msg = "commit-unknown"
            raise IntercomStoreError(msg)
        return record

    async def settle(
        self, task_id: UUID, attempt_id: UUID, record: dict[str, Any], *, current: Callable[[], None] | None = None
    ) -> dict[str, Any]:
        if current is not None:
            current()
        self.tasks[task_id]["status"] = record["status"]
        return self.tasks[task_id]


class BrokenContact:
    async def exchange(self, *args: Any, **kwargs: Any) -> Any:
        raise TimeoutError


async def setup() -> tuple[
    IntercomService, MemoryCustody, PeerAuthority, LocalOperatorAuthentication, UUID, str, dict[str, Any]
]:
    peer_id, workload_id = uuid4(), uuid4()
    uri = "https://peer.example:443/a2a"
    limit = CapacityLimit(100, 1024 * 1024, 100 * 512 * 1024)
    policy = PeerPolicy(
        1,
        frozenset({"enroll", "classify_public", "submit", "poll", "cancel", "read", "rotate", "revoke"}),
        frozenset({"test-public"}),
        frozenset({"public-task"}),
        frozenset({"public.text@1"}),
        frozenset({peer_id}),
        frozenset({uri}),
        limit,
        limit,
        limit,
        limit,
    )
    access = LocalOperatorAccess(access_password="ephemeral-unit-password")
    authority = PeerAuthority(access=access, policy=policy)
    marker = access.authenticate(username=b"magus", password=b"ephemeral-unit-password")
    assert marker is not None
    custody = MemoryCustody()
    private = Ed25519PrivateKey.generate()
    service = IntercomService(
        store=cast("IntercomStore", custody),
        authority=authority,
        workload_id=workload_id,
        signing_key=private.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()),
        signing_key_id="workload-1",
    )
    foreign = Ed25519PrivateKey.generate()
    now = datetime.now(UTC)
    key = {
        "key_id": "peer-1",
        "public_key_pem": foreign.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode(),
        "issuer": str(peer_id),
        "protocol": "rfc9421-ed25519@1",
        "audience": str(workload_id),
        "assurance": "operator-enrolled",
        "valid_from": (now - timedelta(seconds=1)).isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
    }
    await service.enroll(
        marker,
        peer_id=peer_id,
        endpoint={
            "address": "192.0.2.1",
            "hostname": "peer.example",
            "port": 443,
            "path": "/a2a",
            "ca_file": str(Path("/tmp/explicit-ca.pem")),
        },
        task_schema="public.text@1",
        purpose="test-public",
        key=key,
    )
    return service, custody, authority, marker, peer_id, uri, key


@pytest.mark.asyncio
async def test_reconstructed_marker_and_unclassified_source_have_no_authority() -> None:
    service, _, _, marker, peer_id, uri, _ = await setup()
    forged = LocalOperatorAuthentication(marker.subject, marker.authentication_generation)
    for presenter, source in (
        (forged, PublicTextSource("hello", public_assertion=True)),
        (marker, PublicTextSource("hello")),
        (marker, PublicTextSource("hello", public_assertion=True, influence_manifest=("private-context",))),
        (marker, PublicTextSource("hello", public_assertion=True, lineage_known=False)),
    ):
        with pytest.raises(PeerAuthorityError):
            await service.declare_public(
                presenter,
                peer_id=peer_id,
                purpose="test-public",
                task_schema="public.text@1",
                endpoint=uri,
                source=source,
            )


@pytest.mark.asyncio
async def test_classification_permission_is_separate_and_rechecked_after_await() -> None:
    service, custody, authority, marker, peer_id, uri, _ = await setup()
    custody.before_declare = lambda: authority.replace_policy(
        replace(authority.policy, generation=2, actions=frozenset({"submit"}))
    )
    with pytest.raises(PeerAuthorityError):
        await service.declare_public(
            marker,
            peer_id=peer_id,
            purpose="test-public",
            task_schema="public.text@1",
            endpoint=uri,
            source=PublicTextSource("hello", public_assertion=True),
        )
    assert not service._declarations


@pytest.mark.asyncio
async def test_copied_declaration_and_unknown_submit_cannot_resend() -> None:
    service, custody, _, marker, peer_id, uri, _ = await setup()
    declaration = await service.declare_public(
        marker,
        peer_id=peer_id,
        purpose="test-public",
        task_schema="public.text@1",
        endpoint=uri,
        source=PublicTextSource("hello", public_assertion=True),
    )
    with pytest.raises(PeerAuthorityError, match="declaration"):
        await service.submit(marker, declaration=replace(declaration))
    service._http = cast("Any", BrokenContact())
    with pytest.raises(IntercomUnknownError) as raised:
        await service.submit(marker, declaration=declaration)
    assert custody.tasks[raised.value.task_id]["status"] == "unknown"
    with pytest.raises(PeerAuthorityError, match="declaration"):
        await service.submit(marker, declaration=declaration)
    assert custody.claims == 1
    with pytest.raises(PeerAuthorityError, match="foreign-task-unknown"):
        await service.poll(
            marker,
            task_id=raised.value.task_id,
            peer_id=peer_id,
            purpose="test-public",
            task_schema="public.text@1",
            endpoint=uri,
        )
    assert custody.claims == 1


@pytest.mark.asyncio
async def test_policy_change_after_task_commit_prevents_claim_and_contact() -> None:
    service, custody, authority, marker, peer_id, uri, _ = await setup()
    declaration = await service.declare_public(
        marker,
        peer_id=peer_id,
        purpose="test-public",
        task_schema="public.text@1",
        endpoint=uri,
        source=PublicTextSource("hello", public_assertion=True),
    )
    custody.before_task = lambda: authority.replace_policy(
        replace(authority.policy, generation=2, actions=frozenset({"read"}))
    )
    with pytest.raises(PeerAuthorityError):
        await service.submit(marker, declaration=declaration)
    assert custody.claims == 0


@pytest.mark.asyncio
async def test_changed_workload_credential_cannot_reuse_enrolled_identity() -> None:
    service, custody, authority, marker, peer_id, uri, _ = await setup()
    changed_key = Ed25519PrivateKey.generate().private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    restarted = IntercomService(
        store=cast("IntercomStore", custody),
        authority=authority,
        workload_id=service._workload_id,
        signing_key=changed_key,
        signing_key_id="workload-1",
    )
    with pytest.raises(PeerAuthorityError, match="current-peer"):
        await restarted.declare_public(
            marker,
            peer_id=peer_id,
            purpose="test-public",
            task_schema="public.text@1",
            endpoint=uri,
            source=PublicTextSource("hello", public_assertion=True),
        )
    assert custody.claims == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["create_task", "claim"])
async def test_commit_unknown_retains_generated_task_identity_and_consumed_declaration(stage: str) -> None:
    service, custody, _, marker, peer_id, uri, _ = await setup()
    declaration = await service.declare_public(
        marker,
        peer_id=peer_id,
        purpose="test-public",
        task_schema="public.text@1",
        endpoint=uri,
        source=PublicTextSource("hello", public_assertion=True),
    )
    custody.failure_stage = stage
    with pytest.raises(IntercomUnknownError) as raised:
        await service.submit(marker, declaration=declaration)
    assert raised.value.task_id in custody.tasks
    with pytest.raises(PeerAuthorityError, match="declaration"):
        await service.submit(marker, declaration=declaration)
    assert custody.claims == (1 if stage == "claim" else 0)


@pytest.mark.asyncio
async def test_cancel_known_terminal_does_not_close_first_terminal_read() -> None:
    service, custody, _, marker, peer_id, uri, _ = await setup()
    declaration = await service.declare_public(
        marker,
        peer_id=peer_id,
        purpose="test-public",
        task_schema="public.text@1",
        endpoint=uri,
        source=PublicTextSource("hello", public_assertion=True),
    )
    service._http = cast("Any", BrokenContact())
    with pytest.raises(IntercomUnknownError) as raised:
        await service.submit(marker, declaration=declaration)
    task_id = raised.value.task_id
    custody.tasks[task_id].update(
        {
            "status": "terminal",
            "local_status": "terminal",
            "foreign_task_id": "remote-known",
            "result": {"text": ["first terminal"], "origin": "authenticated-foreign-data"},
        }
    )
    with pytest.raises(PeerAuthorityError, match="terminal"):
        await service.cancel(
            marker, task_id=task_id, peer_id=peer_id, purpose="test-public", task_schema="public.text@1", endpoint=uri
        )
    assert task_id not in service._closed_adoption
    retained = await service.read(
        marker, task_id=task_id, peer_id=peer_id, purpose="test-public", task_schema="public.text@1", endpoint=uri
    )
    assert retained["result"]["text"] == ["first terminal"]


class NativeMemoryCustody(MemoryCustody):
    """Detached native custody substitute; no host, database or network effects."""

    def __init__(self) -> None:
        super().__init__()
        self.declarations: dict[UUID, dict[str, Any]] = {}
        self.after_read: Callable[[], None] | None = None
        self.after_claim: Callable[[], None] | None = None
        self.close_failure = False

    async def declare(self, declaration_id: UUID, record: dict[str, Any]) -> None:
        self.declarations[declaration_id] = record.copy()

    async def declaration(self, declaration_id: UUID) -> dict[str, Any]:
        if self.after_read is not None:
            self.after_read()
        return {**self.declarations[declaration_id], "declaration_id": str(declaration_id)}

    async def create_native_task(
        self,
        task_id: UUID,
        record: dict[str, Any],
        *,
        ref: Any,
        pattern_digest: str,
        enqueue_seq: int,
        step_id: str,
        occurrence_id: str,
    ) -> dict[str, Any]:
        if task_id in self.tasks:
            assert self.tasks[task_id]["body"] == record["body"].encode()
            assert self.tasks[task_id]["expires_at"] == record["expires_at"]
            assert self.tasks[task_id]["native_step_id"] == step_id
            assert self.tasks[task_id]["native_occurrence_id"] == occurrence_id
            return self.tasks[task_id].copy()
        task = await self.create_task(task_id, record)
        task.update(
            {
                "native_run_id": ref.run_id,
                "native_station": ref.station,
                "native_request_id": str(ref.request_id),
                "native_binding_digest": ref.binding_digest,
                "native_pattern_digest": pattern_digest,
                "native_enqueue_seq": enqueue_seq,
                "native_step_id": step_id,
                "native_occurrence_id": occurrence_id,
                "local_status": "prepared",
                "submit_claimed": False,
                "adoption_closed": False,
            }
        )
        return task.copy()

    async def task(self, task_id: UUID, *, peer_id: UUID) -> dict[str, Any]:
        result = await super().task(task_id, peer_id=peer_id)
        if self.after_read is not None:
            self.after_read()
        return result.copy()

    async def claim(
        self,
        task_id: UUID,
        attempt_id: UUID,
        record: dict[str, Any],
        limits: dict[str, Any],
    ) -> dict[str, Any]:
        task = self.tasks[task_id]
        if record["method"] == "SendMessage":
            if task["submit_claimed"]:
                code = "claimed"
                raise IntercomStoreError(code)
            task["submit_claimed"] = True
            task["local_status"] = "submitting"
        result = await super().claim(task_id, attempt_id, record, limits)
        if self.after_claim is not None:
            self.after_claim()
        return result

    async def close_native_run(self, run_id: str) -> list[dict[str, Any]]:
        if self.close_failure:
            code = "commit-unknown"
            raise IntercomStoreError(code)
        results: list[dict[str, Any]] = []
        for task in self.tasks.values():
            if task.get("native_run_id") == run_id:
                task["adoption_closed"] = True
                task["closure_reason"] = "cancelled"
                if task["local_status"] != "terminal":
                    task["local_status"] = "cancelled"
                results.append(task.copy())
        return results


async def _native_setup() -> tuple[IntercomService, NativeMemoryCustody, PeerAuthority, Any, Any, Any]:
    from lychd.domain.intercom.native import PeerRunBinding, PeerTaskRef

    service, original, authority, marker, peer_id, uri, _ = await setup()
    custody = NativeMemoryCustody()
    custody.peers = original.peers.copy()
    service._store = cast("IntercomStore", custody)
    declaration = await service.declare_public(
        marker,
        peer_id=peer_id,
        purpose="test-public",
        task_schema="public.text@1",
        endpoint=uri,
        source=PublicTextSource("exact original public source", public_assertion=True),
    )
    binding = PeerRunBinding(
        request_id=uuid4(),
        declaration_id=declaration.declaration_id,
        operation_id=declaration.operation_id,
        peer_id=peer_id,
        purpose="test-public",
        task_schema="public.text@1",
        endpoint=uri,
        source_digest=declaration.source_digest,
        text_digest=declaration.text_digest,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    ref = PeerTaskRef(
        task_id=uuid4(),
        run_id=str(uuid4()),
        station="peer_wait",
        request_id=binding.request_id,
        binding_digest=binding.digest,
    )
    return service, custody, authority, marker, binding, ref


async def _native_prepare(service: IntercomService, marker: Any, binding: Any, ref: Any) -> dict[str, Any]:
    return await service.prepare_native(
        marker,
        binding=binding,
        ref=ref,
        pattern_digest="a" * 64,
        enqueue_seq=0,
        step_id=str(uuid4()),
        occurrence_id=str(uuid4()),
    )


def _native_args(binding: Any, ref: Any) -> dict[str, Any]:
    return {
        "task_id": ref.task_id,
        "peer_id": binding.peer_id,
        "purpose": binding.purpose,
        "task_schema": binding.task_schema,
        "endpoint": binding.endpoint,
    }


@pytest.mark.asyncio
async def test_native_prepare_requires_live_guard_and_never_contacts_or_changes_original_body() -> None:
    service, custody, _, marker, binding, ref = await _native_setup()
    with pytest.raises(PeerAuthorityError, match="native-permission"):
        await _native_prepare(service, marker, binding, ref)
    service.bind_native_guard(ref.task_id, lambda: None)
    first = await _native_prepare(service, marker, binding, ref)
    repeated = await service.prepare_native(
        marker,
        binding=binding,
        ref=ref,
        pattern_digest="a" * 64,
        enqueue_seq=0,
        step_id=first["native_step_id"],
        occurrence_id=first["native_occurrence_id"],
    )
    assert repeated["body"] == first["body"]
    assert repeated["expires_at"] == binding.expires_at.isoformat()
    assert b"exact original public source" in first["body"]
    assert custody.claims == 0
    assert not service._pending
    assert not service._native_exchanges


@pytest.mark.asyncio
async def test_native_original_source_lookup_rechecks_actual_marker_after_await() -> None:
    service, custody, authority, marker, binding, ref = await _native_setup()
    service.bind_native_guard(ref.task_id, lambda: None)
    custody.after_read = authority._access.revoke
    with pytest.raises(PeerAuthorityError, match="authentication"):
        await _native_prepare(service, marker, binding, ref)
    assert not custody.tasks


@pytest.mark.asyncio
async def test_native_unknown_submit_is_never_rearmed_with_fresh_wrapper() -> None:
    service, custody, _, marker, binding, ref = await _native_setup()
    service.bind_native_guard(ref.task_id, lambda: None)
    prepared = await _native_prepare(service, marker, binding, ref)
    service._http = cast("Any", BrokenContact())
    with pytest.raises(IntercomUnknownError):
        await service.send_prepared(marker, **_native_args(binding, ref), current=service._native_guards[ref.task_id])
    with pytest.raises(PeerAuthorityError, match="claimed"):
        await service.send_prepared(marker, **_native_args(binding, ref), current=service._native_guards[ref.task_id])
    assert custody.claims == 1
    assert custody.tasks[ref.task_id]["body"] == prepared["body"]
    assert custody.tasks[ref.task_id]["expires_at"] == prepared["expires_at"]


@pytest.mark.asyncio
async def test_native_claim_await_rechecks_guard_before_contact() -> None:
    service, custody, _, marker, binding, ref = await _native_setup()
    live = True

    def current() -> None:
        if not live:
            code = "stale-claim"
            raise PeerAuthorityError(code)

    service.bind_native_guard(ref.task_id, current)
    await _native_prepare(service, marker, binding, ref)

    def stale() -> None:
        nonlocal live
        live = False

    custody.after_claim = stale
    with pytest.raises(PeerAuthorityError, match="stale-claim"):
        await service.send_prepared(marker, **_native_args(binding, ref), current=service._native_guards[ref.task_id])
    assert custody.claims == 1
    assert custody.tasks[ref.task_id]["submit_claimed"]
    assert not service._pending
    assert not service._native_exchanges


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["read", "poll"])
async def test_native_read_and_poll_recheck_supplied_current_after_task_await(operation: str) -> None:
    service, custody, _, marker, binding, ref = await _native_setup()
    service.bind_native_guard(ref.task_id, lambda: None)
    await _native_prepare(service, marker, binding, ref)
    custody.tasks[ref.task_id]["foreign_task_id"] = "known-task"
    live = True

    def current() -> None:
        if not live:
            code = "stale-owner"
            raise PeerAuthorityError(code)

    def stale() -> None:
        nonlocal live
        live = False

    custody.after_read = stale
    with pytest.raises(PeerAuthorityError, match="stale-owner"):
        await getattr(service, operation)(marker, **_native_args(binding, ref), current=current)
    assert custody.claims == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("closure_fails", [False, True])
async def test_native_retirement_cancels_actual_blocked_receive_and_closes_socket_even_if_store_fails(
    monkeypatch: pytest.MonkeyPatch,
    *,
    closure_fails: bool,
) -> None:
    import asyncio

    from lychd.system.services import intercom_http

    service, custody, _, marker, binding, ref = await _native_setup()
    service.bind_native_guard(ref.task_id, lambda: None)
    await _native_prepare(service, marker, binding, ref)
    receiving = asyncio.Event()
    closed = False

    class Stream:
        async def send(self, body: bytes) -> None:
            assert b"exact original public source" in body

        async def receive(self) -> bytes:
            receiving.set()
            await asyncio.Event().wait()
            raise AssertionError

        def close(self) -> None:
            nonlocal closed
            closed = True

    async def open_stream(*args: Any, **kwargs: Any) -> Any:
        return Stream()

    monkeypatch.setattr(intercom_http, "open_pinned_tls", open_stream)
    sender = asyncio.create_task(
        service.send_prepared(marker, **_native_args(binding, ref), current=service._native_guards[ref.task_id])
    )
    await receiving.wait()
    custody.close_failure = closure_fails
    if closure_fails:
        with pytest.raises(IntercomStoreError, match="commit-unknown"):
            await service.retire_native_run(ref.run_id)
    else:
        await service.retire_native_run(ref.run_id)
        assert custody.tasks[ref.task_id]["adoption_closed"]
    assert closed
    assert sender.done()
    with pytest.raises(asyncio.CancelledError):
        await sender
    with pytest.raises(PeerAuthorityError, match="native-retired"):
        await service.read(marker, **_native_args(binding, ref))
    assert not service._pending
    assert not service._native_exchanges


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["connect", "tls", "http"])
async def test_native_guard_fences_each_actual_socket_handoff(phase: Literal["connect", "tls", "http"]) -> None:
    from lychd.domain.intercom.transport import IntercomHandoff

    service, custody, _, marker, binding, ref = await _native_setup()
    live = True
    offered = False

    def current() -> None:
        if not live:
            code = "stale-handoff"
            raise PeerAuthorityError(code)

    class Contact:
        async def exchange(self, endpoint: Any, prepared: Any, *, gate: Any, deadline: float) -> Any:
            nonlocal live
            live = False

            def syscall() -> int:
                nonlocal offered
                offered = True
                return 1

            gate.handoff(
                IntercomHandoff(
                    endpoint, phase, b"" if phase == "connect" else b"x", prepared.wire if phase == "http" else None
                ),
                syscall,
            )
            raise AssertionError

    service.bind_native_guard(ref.task_id, current)
    await _native_prepare(service, marker, binding, ref)
    service._http = cast("Any", Contact())
    with pytest.raises(IntercomUnknownError):
        await service.send_prepared(marker, **_native_args(binding, ref), current=service._native_guards[ref.task_id])
    assert offered is False
    assert custody.claims == 1


@pytest.mark.asyncio
async def test_native_retirement_waits_cancelled_preparation_before_success() -> None:
    import asyncio

    service, custody, _, marker, binding, ref = await _native_setup()
    service.bind_native_guard(ref.task_id, lambda: None)
    entered = asyncio.Event()
    exited = False

    async def declaration(declaration_id: UUID) -> dict[str, Any]:
        nonlocal exited
        entered.set()
        try:
            await asyncio.Event().wait()
            raise AssertionError
        finally:
            exited = True

    custody.declaration = declaration
    preparing = asyncio.create_task(_native_prepare(service, marker, binding, ref))
    await entered.wait()
    await service.retire_native_run(ref.run_id)
    assert exited
    assert preparing.done()
    with pytest.raises(asyncio.CancelledError):
        await preparing
    assert not custody.tasks
    assert not service._native_preparations


@pytest.mark.asyncio
async def test_native_failed_socket_teardown_prevents_successful_retirement(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    from lychd.system.services import intercom_http

    service, custody, _, marker, binding, ref = await _native_setup()
    service.bind_native_guard(ref.task_id, lambda: None)
    await _native_prepare(service, marker, binding, ref)
    entered = asyncio.Event()
    close_attempted = False

    class Stream:
        async def send(self, body: bytes) -> None:
            pass

        async def receive(self) -> bytes:
            entered.set()
            await asyncio.Event().wait()
            raise AssertionError

        def close(self) -> None:
            nonlocal close_attempted
            close_attempted = True
            raise OSError

    async def open_stream(*args: Any, **kwargs: Any) -> Any:
        return Stream()

    monkeypatch.setattr(intercom_http, "open_pinned_tls", open_stream)
    sender = asyncio.create_task(
        service.send_prepared(marker, **_native_args(binding, ref), current=service._native_guards[ref.task_id])
    )
    await entered.wait()
    with pytest.raises(PeerAuthorityError, match="native-retirement"):
        await service.retire_native_run(ref.run_id)
    with pytest.raises(IntercomUnknownError):
        await sender
    assert close_attempted
    with pytest.raises(PeerAuthorityError, match="native-retirement"):
        await service.retire_native_run(ref.run_id)
    assert custody.tasks[ref.task_id]["adoption_closed"]
    assert not service._native_exchanges


@pytest.mark.asyncio
async def test_native_preparation_consumes_original_declaration_for_standalone_submit() -> None:
    service, custody, _, marker, binding, ref = await _native_setup()
    original = service._declarations[binding.declaration_id].declaration
    service.bind_native_guard(ref.task_id, lambda: None)
    await _native_prepare(service, marker, binding, ref)
    with pytest.raises(PeerAuthorityError, match="declaration"):
        await service.submit(marker, declaration=original)
    assert custody.claims == 0
    assert list(custody.tasks) == [ref.task_id]


@pytest.mark.asyncio
async def test_native_explicit_reauthorization_read_uses_fresh_guard_over_old_permit() -> None:
    service, _, _, marker, binding, ref = await _native_setup()
    service.bind_native_guard(ref.task_id, lambda: None)
    await _native_prepare(service, marker, binding, ref)

    def old_permission() -> None:
        code = "old-permit"
        raise PeerAuthorityError(code)

    service.bind_native_guard(ref.task_id, old_permission)
    with pytest.raises(PeerAuthorityError, match="old-permit"):
        await service.read(marker, **_native_args(binding, ref))
    task = await service.read(marker, **_native_args(binding, ref), current=lambda: None)
    assert task["task_id"] == str(ref.task_id)


@pytest.mark.asyncio
async def test_native_bound_preparation_guard_does_not_authorize_standalone_first_send() -> None:
    service, custody, _, marker, binding, ref = await _native_setup()
    service.bind_native_guard(ref.task_id, lambda: None)
    await _native_prepare(service, marker, binding, ref)
    with pytest.raises(PeerAuthorityError, match="native-permission"):
        await service.send_prepared(marker, **_native_args(binding, ref))
    assert custody.claims == 0


@pytest.mark.asyncio
async def test_native_graceful_shutdown_retires_locally_without_closing_durable_adoption() -> None:
    service, custody, _, marker, binding, ref = await _native_setup()
    service.bind_native_guard(ref.task_id, lambda: None)
    await _native_prepare(service, marker, binding, ref)
    await service.retire_native_run(ref.run_id, close_adoption=False)
    assert custody.tasks[ref.task_id]["adoption_closed"] is False
    assert custody.tasks[ref.task_id]["local_status"] == "prepared"
    with pytest.raises(PeerAuthorityError, match="native-retired"):
        await service.send_prepared(marker, **_native_args(binding, ref), current=lambda: None)
