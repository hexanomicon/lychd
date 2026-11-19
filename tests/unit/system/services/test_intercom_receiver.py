from __future__ import annotations

import asyncio
import json
import ssl
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import SecretStr, ValidationError
from scripts import intercom_receive

from lychd.compositions.atelier.brief import ShortVideoBrief
from lychd.db.intercom_inbox import InboxError, Receipt, ReceiverInbox
from lychd.domain.intercom.codec import send_params
from lychd.domain.intercom.transport import IntercomError, IntercomRemoteError, PreparedRequest
from lychd.system.services import intercom_receiver
from lychd.system.services.intercom_http import prepare_request, verify_response
from lychd.system.services.intercom_receiver import IntercomReceiver, PeerInvitation
from lychd.system.services.local_access import LocalAccess


def _private(key: Ed25519PrivateKey) -> bytes:
    return key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )


def _public(key: Ed25519PrivateKey) -> str:
    return (
        key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )


@dataclass(frozen=True)
class _Pair:
    invitation: PeerInvitation
    sender: Ed25519PrivateKey
    receiver: Ed25519PrivateKey

    def submit(self, text: str) -> PreparedRequest:
        pair = self.invitation
        return prepare_request(
            method="SendMessage",
            local_task_id="commission",
            attempt_id="physical-1",
            peer_id=str(pair.receiver_id),
            workload_id=str(pair.sender_id),
            task_schema=pair.task_schema,
            endpoint=pair.endpoint,
            params=send_params(text, "message-1"),
            signing_key=_private(self.sender),
            key_id=pair.sender_key_id,
        )


@pytest.fixture
def pair() -> _Pair:
    sender, receiver = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    settings = {
        "sender_id": str(uuid4()),
        "receiver_id": str(uuid4()),
        "hostname": "receiver.test",
        "port": 8443,
        "listen_address": "127.0.0.1",
        "peer_address": "127.0.0.1",
        "task_schema": "atelier.short-video-brief@1",
        "sender_key_id": "sender-key",
        "signing_key_id": "receiver-key",
        "sender_public_key_pem": _public(sender),
        "receiver_public_key_pem": _public(receiver),
        "valid_until": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
        "tls_certificate": "/unused/cert.pem",
        "tls_key": "/unused/key.pem",
    }
    invitation = PeerInvitation.model_validate_json(json.dumps(settings))
    return _Pair(invitation, sender, receiver)


def _changed(pair: PeerInvitation, **settings: object) -> PeerInvitation:
    return PeerInvitation.model_validate_json(json.dumps({**pair.model_dump(mode="json"), **settings}))


def test_invitation_separates_workload_and_signer_roles(pair: _Pair) -> None:
    invitation = pair.invitation
    with pytest.raises(ValidationError):
        _changed(invitation, sender_id=str(invitation.receiver_id))
    with pytest.raises(ValidationError):
        _changed(invitation, sender_public_key_pem=invitation.receiver_public_key_pem)
    with pytest.raises(IntercomError):
        invitation.verify_signer(_private(pair.sender))
    invitation.verify_signer(_private(pair.receiver))


def test_intake_window_limits_new_work(pair: _Pair) -> None:
    now = datetime.now(UTC)
    public = ShortVideoBrief(recipe="captioned-excerpt", script="A public narration", duration_seconds=4)
    brief = public.model_dump_json(exclude_none=True)
    for start, end in ((-30, -20), (20, 30)):
        invitation = _changed(
            pair.invitation,
            accept_from=(now + timedelta(minutes=start)).isoformat(),
            accept_until=(now + timedelta(minutes=end)).isoformat(),
        )
        with pytest.raises(InboxError, match="intake-closed"):
            invitation.admit_new(brief, now, now + timedelta(days=1))
    current = _changed(
        pair.invitation,
        accept_from=(now - timedelta(minutes=1)).isoformat(),
        accept_until=(now + timedelta(minutes=1)).isoformat(),
    )
    current.admit_new(brief, now, now + timedelta(days=1))
    with pytest.raises(ValidationError):
        _changed(current, accept_until=None)


@pytest.mark.asyncio
@pytest.mark.parametrize("eligible", [True, False])
async def test_receiver_commits_only_a_recognized_atelier_brief(pair: _Pair, *, eligible: bool) -> None:
    script = "A public narration"
    public = ShortVideoBrief(recipe="captioned-excerpt", script=script, duration_seconds=4)
    brief = public.model_dump(mode="json", exclude_none=True)
    if not eligible:
        brief["recipe"] = "unavailable-recipe"
    sent = pair.submit(json.dumps(brief))
    receipt = Receipt(uuid4(), "commission", "TASK_STATE_SUBMITTED", "submitted", None, pair.invitation.valid_until)
    stored: list[Receipt] = []

    def intake(
        *, authorize: Callable[[], None], admit_new: Callable[[datetime, datetime], None], **facts: object
    ) -> Receipt:
        authorize()
        assert facts["method"] == "SendMessage"
        assert facts["text"] == json.dumps(brief)
        admit_new(datetime.now(UTC), receipt.expires_at)
        stored.append(receipt)
        return receipt

    inbox = Mock(spec=ReceiverInbox)
    inbox.receive = AsyncMock(side_effect=intake)
    service = IntercomReceiver(pair.invitation, cast("ReceiverInbox", inbox), _private(pair.receiver), lambda: None)
    reply, _ = await service._exchange(list(sent.headers), sent.body)  # pyright: ignore[reportPrivateUsage]
    verification_key = _public(pair.receiver).encode()
    if eligible:
        observed = verify_response(sent, reply.status, reply.headers, reply.body, verification_key, "receiver-key")
        assert (observed.foreign_task_id, observed.state) == (str(receipt.task_id), "TASK_STATE_SUBMITTED")
        assert stored == [receipt]
    else:
        with pytest.raises(IntercomRemoteError):
            verify_response(sent, reply.status, reply.headers, reply.body, verification_key, "receiver-key")
        assert stored == []
        assert script.encode() not in reply.body


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reason",
    [
        "storage",
        "commit-unknown",
        "invitation",
        "intake-aborted",
        "attempt-capacity",
        "replay",
        "unrecognized-disposition",
    ],
)
async def test_storage_or_authority_uncertainty_cannot_sign_a_disposition(pair: _Pair, reason: str) -> None:
    brief = ShortVideoBrief(recipe="animated-lesson", script="A public lesson", duration_seconds=15)
    sent = pair.submit(brief.model_dump_json(exclude_none=True))
    inbox = Mock(spec=ReceiverInbox)
    inbox.receive = AsyncMock(side_effect=InboxError(reason))
    service = IntercomReceiver(pair.invitation, cast("ReceiverInbox", inbox), _private(pair.receiver), lambda: None)
    with pytest.raises(InboxError, match=reason):
        await service._exchange(list(sent.headers), sent.body)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_local_review_requires_actual_operator_credential_before_opening_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    credential = uuid4().hex
    configured = LocalAccess("http://127.0.0.1", SecretStr(credential))
    monkeypatch.setattr(intercom_receive, "load_local_access", lambda: configured)
    with pytest.raises(InboxError, match="operator"):
        await intercom_receive.run_session(tmp_path / "absent.json", "pending", password=uuid4().hex)


@pytest.mark.asyncio
@pytest.mark.parametrize("retire", [True, False])
async def test_local_pending_rechecks_the_exact_invitation_after_waiting_for_storage(
    pair: _Pair, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, retire: bool
) -> None:
    credential = uuid4().hex
    access = LocalAccess("http://127.0.0.1", SecretStr(credential))
    monkeypatch.setattr(intercom_receive, "load_local_access", lambda: access)
    raw = pair.invitation.model_dump_json(exclude_none=True).encode()

    def read_config(_: Path) -> bytes:
        return raw

    monkeypatch.setattr(intercom_receive, "_read_config", read_config)
    monkeypatch.setenv("LYCHD_INTERCOM_DATABASE_URL", "unused-database")
    engine = Mock(dispose=AsyncMock())
    monkeypatch.setattr(intercom_receive, "create_async_engine", Mock(return_value=engine))
    receipt = Receipt(uuid4(), "commission", "TASK_STATE_SUBMITTED", "submitted", None, pair.invitation.valid_until)

    def pending(*, authorize: Callable[[], None]) -> tuple[Receipt, ...]:
        nonlocal raw
        if retire:
            raw = b"{}"
        authorize()
        return (receipt,)

    inbox = Mock(pending=AsyncMock(side_effect=pending))
    monkeypatch.setattr(intercom_receive, "ReceiverInbox", Mock(return_value=inbox))
    session = intercom_receive.run_session(tmp_path / "invitation.json", "pending", password=credential)
    if retire:
        with pytest.raises(InboxError, match="invitation"):
            await session
    else:
        assert await session == [asdict(receipt)]
    engine.dispose.assert_awaited_once_with()


def test_atelier_admission_uses_the_db_task_lifetime_and_first_start_uses_the_requested_window(pair: _Pair) -> None:
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=30)
    public = ShortVideoBrief(recipe="animated-lesson", script="Public", duration_seconds=10)
    brief = public.model_dump(exclude_none=True)

    def window(start: datetime, end: datetime) -> str:
        return json.dumps({**brief, "not_before": start.isoformat(), "latest_start_at": end.isoformat()})

    for unavailable in (window(now - timedelta(minutes=1), now), window(expires, expires + timedelta(minutes=5))):
        with pytest.raises(InboxError, match="start-window"):
            pair.invitation.admit_new(unavailable, now, expires)
    opening = now + timedelta(minutes=5)
    closing = now + timedelta(minutes=8)
    scheduled = window(opening, closing)
    pair.invitation.admit_new(scheduled, now, expires)
    pair.invitation.check_start(scheduled, opening)
    for outside in (now, closing):
        with pytest.raises(InboxError, match="start-window"):
            pair.invitation.check_start(scheduled, outside)
    with pytest.raises(InboxError, match="invalid-brief"):
        pair.invitation.check_start("{}", opening)
    public_text = _changed(pair.invitation, task_schema="public-text@1")
    public_text.check_start("An ordinary public note", now)


@pytest.mark.asyncio
async def test_idle_listener_retires_and_closes_an_unfinished_connection(
    pair: _Pair, monkeypatch: pytest.MonkeyPatch
) -> None:
    checks = 0

    def authorize() -> None:
        nonlocal checks
        checks += 1
        if checks > 1:
            msg = "invitation"
            raise InboxError(msg)

    server = Mock(wait_closed=AsyncMock())
    reader = asyncio.StreamReader()
    writer = Mock(spec=asyncio.StreamWriter)
    writer.get_extra_info.return_value = (str(pair.invitation.peer_address), 50000)
    server.abort_clients.side_effect = writer.close

    async def bind(
        accept: Callable[[asyncio.StreamReader, asyncio.StreamWriter], None], *args: object, **kwargs: object
    ) -> Mock:
        accept(reader, cast("asyncio.StreamWriter", writer))
        return server

    monkeypatch.setattr(intercom_receiver.asyncio, "start_server", bind)
    monkeypatch.setattr(intercom_receiver, "_INVITATION_POLL_SECONDS", 0)
    inbox = Mock(spec=ReceiverInbox)
    receiver = IntercomReceiver(pair.invitation, cast("ReceiverInbox", inbox), _private(pair.receiver), authorize)
    with pytest.raises(InboxError, match="invitation"):
        await receiver.serve(ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER))
    server.close.assert_called_once_with()
    server.abort_clients.assert_called_once_with()
    server.wait_closed.assert_awaited_once_with()
    writer.close.assert_called()
    inbox.receive.assert_not_called()


@pytest.mark.asyncio
async def test_expired_pair_never_opens_the_private_listener(pair: _Pair, monkeypatch: pytest.MonkeyPatch) -> None:
    expiry = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    expired = _changed(pair.invitation, valid_until=expiry)
    inbox = Mock(spec=ReceiverInbox)
    bind = AsyncMock()
    monkeypatch.setattr(intercom_receiver.asyncio, "start_server", bind)
    receiver = IntercomReceiver(expired, cast("ReceiverInbox", inbox), _private(pair.receiver), lambda: None)
    with pytest.raises(InboxError, match="invitation"):
        await receiver.serve(ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER))
    bind.assert_not_awaited()
