"""Explicit paired Intercom listener. All remote inputs terminate at the review inbox."""

from __future__ import annotations

import asyncio
import hashlib
import ssl
import time
from collections.abc import Callable
from datetime import datetime
from ipaddress import IPv4Address, IPv4Network
from pathlib import Path
from typing import Literal, Self
from uuid import UUID

import h11
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from lychd.compositions.atelier.brief import ShortVideoBrief
from lychd.db.intercom_inbox import InboxError, ReceiverInbox
from lychd.domain.intercom.transport import (
    MAX_HEADER_BYTES,
    MAX_OPERATION_SECONDS,
    IntercomCode,
    IntercomError,
    RawResponse,
)
from lychd.system.services.intercom_http import (
    request_content_length,
    sign_peer_refusal,
    sign_peer_response,
    verify_peer_request,
)

RECEIVE_PATH = "/a2a/jsonrpc"
_PRIVATE_ROADS = tuple(IPv4Network(cidr) for cidr in ("127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
_MAX_CLIENTS = 8
_INVITATION_POLL_SECONDS = 1.0
_SEMANTIC_REFUSALS = frozenset(
    {
        "capacity",
        "conflict",
        "expired",
        "intake-closed",
        "invalid-brief",
        "method",
        "start-window",
        "text",
        "unknown-task",
    }
)


class PeerInvitation(BaseModel):
    """One explicit endpoint, task policy, signing-key pair and current operator grant."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    receiver_id: UUID
    sender_id: UUID
    hostname: str = Field(min_length=1, max_length=253, pattern=r"^[a-zA-Z0-9.-]+$")
    port: int = Field(ge=1, le=65535)
    listen_address: IPv4Address
    peer_address: IPv4Address
    task_schema: Literal["public-text@1", "atelier.short-video-brief@1"]
    sender_key_id: str = Field(min_length=1, max_length=128, pattern=r"^[!-~]+$")
    sender_public_key_pem: str = Field(max_length=2048)
    signing_key_id: str = Field(min_length=1, max_length=128, pattern=r"^[!-~]+$")
    receiver_public_key_pem: str = Field(max_length=2048)
    valid_until: AwareDatetime
    accept_from: AwareDatetime | None = None
    accept_until: AwareDatetime | None = None
    tls_certificate: Path
    tls_key: Path

    @model_validator(mode="after")
    def check_pair(self) -> Self:
        if self.receiver_id == self.sender_id or any(
            not any(address in road for road in _PRIVATE_ROADS) for address in (self.listen_address, self.peer_address)
        ):
            raise IntercomError(IntercomCode.CONFIG)
        if (self.accept_from is None) != (self.accept_until is None) or (
            self.accept_from is not None
            and self.accept_until is not None
            and not self.accept_from < self.accept_until <= self.valid_until
        ):
            raise IntercomError(IntercomCode.CONFIG)
        sender = load_pem_public_key(self.sender_public_key_pem.encode("ascii"))
        receiver = load_pem_public_key(self.receiver_public_key_pem.encode("ascii"))
        if (
            not isinstance(sender, Ed25519PublicKey)
            or not isinstance(receiver, Ed25519PublicKey)
            or sender.public_bytes_raw() == receiver.public_bytes_raw()
        ):
            raise IntercomError(IntercomCode.CONFIG)
        return self

    @property
    def endpoint(self) -> str:
        return f"https://{self.hostname}:{self.port}{RECEIVE_PATH}"

    def verify_signer(self, pem: bytes) -> None:
        private = load_pem_private_key(pem, password=None)
        public = load_pem_public_key(self.receiver_public_key_pem.encode("ascii"))
        if not isinstance(private, Ed25519PrivateKey) or private.public_key() != public:
            raise IntercomError(IntercomCode.CONFIG)

    def _brief(self, text: str | None) -> ShortVideoBrief | None:
        if self.task_schema != "atelier.short-video-brief@1":
            return None
        try:
            return ShortVideoBrief.from_wire(text or "")
        except ValueError:
            msg = "invalid-brief"
            raise InboxError(msg) from None

    def admit_new(self, text: str | None, now: datetime, expires_at: datetime) -> None:
        """Admit a new task only while intake is open and its requested start remains possible."""
        if (
            self.accept_from is not None
            and self.accept_until is not None
            and not self.accept_from <= now < self.accept_until
        ):
            msg = "intake-closed"
            raise InboxError(msg)
        brief = self._brief(text)
        if brief is not None and (
            (brief.latest_start_at is not None and brief.latest_start_at <= now)
            or (brief.not_before is not None and brief.not_before >= expires_at)
        ):
            msg = "start-window"
            raise InboxError(msg)

    def check_start(self, text: str, now: datetime) -> None:
        """Enforce the admitted brief's UTC window on its first operator start."""
        brief = self._brief(text)
        if brief is not None and not brief.can_start(now):
            msg = "start-window"
            raise InboxError(msg)


class IntercomReceiver:
    """Each read, mutation and reply requires the currently selected pair."""

    def __init__(
        self, invitation: PeerInvitation, inbox: ReceiverInbox, signing_key: bytes, authorize: Callable[[], None]
    ) -> None:
        """Bind the verified receiver key and an authority check for this inbox."""
        invitation.verify_signer(signing_key)
        self.invitation = invitation
        self.inbox = inbox
        self._signing_key = signing_key
        self._authorize = authorize

    def _require_current(self) -> None:
        self._authorize()
        if time.time() >= self.invitation.valid_until.timestamp():
            msg = "invitation"
            raise InboxError(msg)

    async def _exchange(self, fields: list[tuple[str, str]], body: bytes) -> tuple[RawResponse, float]:
        self._require_current()
        pair = self.invitation
        request = verify_peer_request(
            http_method="POST",
            endpoint=pair.endpoint,
            headers=fields,
            body=body,
            sender_id=str(pair.sender_id),
            recipient_id=str(pair.receiver_id),
            task_schema=pair.task_schema,
            peer_public_key=pair.sender_public_key_pem.encode("ascii"),
            key_id=pair.sender_key_id,
        )

        def current() -> None:
            self._require_current()
            if time.time() >= request.expires_at:
                raise IntercomError(IntercomCode.AUTHENTICATION)

        try:
            receipt = await self.inbox.receive(
                method=request.method,
                local_id=request.local_task_id,
                body_digest=hashlib.sha256(body).hexdigest(),
                attempt=request.attempt_id,
                nonce=request.nonce,
                signature_expires=request.expires_at,
                message_id=request.message_id,
                text=request.text,
                task_id=request.task_id,
                authorize=current,
                admit_new=lambda now, expires_at: pair.admit_new(request.text, now, expires_at),
            )
        except InboxError as error:
            if error.code not in _SEMANTIC_REFUSALS:
                raise
            current()
            refusal = sign_peer_refusal(request, signing_key=self._signing_key, key_id=pair.signing_key_id)
            return refusal, request.expires_at
        current()
        deadline: float = request.expires_at
        if receipt.result is not None:
            deadline = min(deadline, receipt.expires_at.timestamp())
        reply = sign_peer_response(
            request,
            task_id=str(receipt.task_id),
            state=receipt.state,
            text=receipt.result,
            signing_key=self._signing_key,
            key_id=pair.signing_key_id,
        )
        return reply, deadline

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            async with asyncio.timeout(MAX_OPERATION_SECONDS):
                head = await reader.readuntil(b"\r\n\r\n")
                length = request_content_length(head, RECEIVE_PATH)
                connection = h11.Connection(h11.SERVER, max_incomplete_event_size=MAX_HEADER_BYTES)
                connection.receive_data(head)
                message = connection.next_event()
                if not isinstance(message, h11.Request):
                    raise IntercomError(IntercomCode.PROTOCOL)
                fields = [(k.decode("ascii"), v.decode("ascii")) for k, v in message.headers.raw_items()]
                reply, deadline = await self._exchange(fields, await reader.readexactly(length))
                headers = [(k.encode("ascii"), v.encode("ascii")) for k, v in reply.headers]
                wire = connection.send(h11.Response(status_code=reply.status, headers=headers, reason=b"OK"))
                wire += connection.send(h11.Data(data=reply.body)) + connection.send(h11.EndOfMessage())
                self._require_current()
                if time.time() >= deadline:
                    raise IntercomError(IntercomCode.AUTHENTICATION)
                writer.write(wire)
                await writer.drain()
        except (ValueError, OSError, EOFError, asyncio.LimitOverrunError, h11.ProtocolError):
            # Unauthenticated or ambiguous input never receives a task observation.
            return
        finally:
            writer.close()

    async def serve(self, tls: ssl.SSLContext) -> None:
        """Serve one numeric private interface with finite work and drain on retirement."""
        pair = self.invitation
        clients: set[asyncio.Task[None]] = set()
        retiring = False

        def accept(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            peer = writer.get_extra_info("peername")
            if retiring or not peer or peer[0] != str(pair.peer_address) or len(clients) >= _MAX_CLIENTS:
                writer.close()
                return
            task = asyncio.create_task(self._handle(reader, writer))
            clients.add(task)
            task.add_done_callback(clients.discard)

        self._require_current()
        server = await asyncio.start_server(
            accept,
            str(pair.listen_address),
            pair.port,
            ssl=tls,
            limit=MAX_HEADER_BYTES,
            ssl_handshake_timeout=MAX_OPERATION_SECONDS,
            ssl_shutdown_timeout=2,
            backlog=_MAX_CLIENTS,
        )
        try:
            while (remaining := pair.valid_until.timestamp() - time.time()) > 0:
                await asyncio.sleep(min(remaining, _INVITATION_POLL_SECONDS))
                self._require_current()
        finally:
            retiring = True
            server.close()
            server.abort_clients()
            for task in clients:
                task.cancel()
            await asyncio.gather(*clients, return_exceptions=True)
            await server.wait_closed()
