"""Independent refusal cases for exact offline preparation and WUPHF's finite selection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from lychd.compositions.reach.connected.policy import prepare_batch, prepare_operation
from lychd.compositions.reach.connected.schemas import (
    ChatTarget,
    ConnectedPolicy,
    Connection,
    EmailTarget,
    ForgeTarget,
    PreparedOperation,
    PreparedRequest,
    ReadRequest,
    SendRequest,
    SocialTarget,
)

NOW = datetime(2026, 10, 29, 12, tzinfo=UTC)


def connection(**changes: Any) -> Connection:
    values: dict[str, Any] = {
        "connection_id": "mail",
        "partition_id": "company-a",
        "provider": "gmail",
        "account_id": "immutable-google-subject",
        "actor_id": "sender@example.test",
    }
    return Connection(**(values | changes))


def target(**changes: Any) -> EmailTarget:
    values: dict[str, Any] = {
        "connection_id": "mail",
        "mailbox_id": "me",
        "sender": "sender@example.test",
        "to": ("recipient@example.test",),
    }
    return EmailTarget(**(values | changes))


def policy(**changes: Any) -> ConnectedPolicy:
    values: dict[str, Any] = {
        "policy_id": "exact-test",
        "connections": (connection(),),
        "allowed_targets": (target(),),
        "operations": ("read", "send"),
    }
    return ConnectedPolicy(**(values | changes))


def request(**changes: Any) -> SendRequest:
    values: dict[str, Any] = {
        "request_id": "one",
        "target": target(),
        "text": "Private exact text\nSecond line.",
        "subject": "Decision",
    }
    return SendRequest(**(values | changes))


def test_preparation_pins_complete_policy_target_and_application_bytes() -> None:
    prepared = prepare_operation(policy(), request(), now=NOW)
    assert prepared.connection.account_id == "immutable-google-subject"
    assert prepared.request.target == target()
    assert prepared.expires_at == NOW + timedelta(seconds=300)
    assert prepared.policy_digest == policy().digest
    assert PreparedOperation.model_validate_json(prepared.model_dump_json()) == prepared
    assert "Private exact text" not in repr(prepared)
    same = prepare_operation(policy(), request(), now=NOW)
    assert same.digest == prepared.digest
    for changed in (
        prepare_operation(policy(ttl_seconds=299), request(), now=NOW),
        prepare_operation(policy(), request(text="Changed body"), now=NOW),
        prepare_operation(policy(), request(request_id="two"), now=NOW),
        prepare_operation(policy(), request(), now=NOW + timedelta(seconds=1)),
    ):
        assert changed.digest != prepared.digest


@pytest.mark.parametrize(
    "changed_target",
    [
        target(to=("outsider@example.test",)),
        target(cc=("observer@example.test",)),
        target(bcc=("hidden@example.test",)),
        target(thread_id="other-thread"),
    ],
)
def test_audience_or_thread_change_is_a_new_unselected_target(changed_target: EmailTarget) -> None:
    with pytest.raises(ValueError, match="exact target"):
        prepare_operation(policy(), request(target=changed_target), now=NOW)


def test_account_partition_sender_and_provider_are_distinct_bindings() -> None:
    with pytest.raises(ValueError, match="one partition"):
        policy(connections=(connection(), connection(connection_id="other", partition_id="company-b")))
    with pytest.raises(ValueError, match="mailbox and sender"):
        policy(allowed_targets=(target(mailbox_id="immutable-google-subject"),))
    with pytest.raises(ValueError, match="mailbox and sender"):
        policy(allowed_targets=(target(sender="alias@example.test"),))
    with pytest.raises(ValueError, match="provider family"):
        policy(allowed_targets=(ChatTarget(connection_id="mail", conversation_id="123"),))
    with pytest.raises(ValueError, match="publishing actor"):
        policy(
            connections=(connection(provider="facebook", actor_id="page-1"),),
            allowed_targets=(SocialTarget(connection_id="mail", account_id="page-2"),),
        )


def test_fastmail_requires_account_and_send_identity_without_reusing_gmail_selector() -> None:
    fast_connection = connection(provider="fastmail", account_id="jmap-account")
    fast_target = target(mailbox_id="jmap-account", identity_id="identity-a", draft_mailbox_id="drafts-a")
    fast_policy = policy(connections=(fast_connection,), allowed_targets=(fast_target,))
    prepared = prepare_operation(fast_policy, request(target=fast_target), now=NOW)
    assert isinstance(prepared.request.target, EmailTarget)
    assert prepared.request.target.identity_id == "identity-a"
    missing_identity = target(mailbox_id="jmap-account")
    with pytest.raises(ValueError, match="JMAP sending identity"):
        prepare_operation(
            policy(connections=(fast_connection,), allowed_targets=(missing_identity,)),
            request(target=missing_identity),
            now=NOW,
        )


def test_read_budget_is_finite_and_send_selection_is_not_read_authority() -> None:
    read = ReadRequest(request_id="read", target=target(), limit=7)
    assert prepare_operation(policy(max_read_limit=7), read, now=NOW).request == read
    with pytest.raises(ValueError, match="read exceeds"):
        prepare_operation(policy(max_read_limit=6), read, now=NOW)
    with pytest.raises(ValueError, match="outside the preparation policy"):
        prepare_operation(policy(operations=("send",)), read, now=NOW)
    with pytest.raises(ValueError, match="text exceeds"):
        prepare_operation(policy(max_text_chars=3), request(), now=NOW)
    with pytest.raises(ValueError, match="timezone-aware"):
        prepare_operation(policy(), request(), now=NOW.replace(tzinfo=None))


@pytest.mark.parametrize("injected", ["safe\r\nBcc: stolen@example.test", "bad\x00", "hidden\u202e", "\ud800"])
def test_header_and_control_injection_never_reaches_a_preparation(injected: str) -> None:
    with pytest.raises(ValidationError):
        request(subject=injected)
    with pytest.raises(ValidationError):
        request(reply_to_id=injected)
    with pytest.raises(ValidationError):
        target(sender=injected)
    with pytest.raises(ValidationError):
        request(text=injected)


def test_frozen_values_revalidate_copied_or_constructed_input_at_boundary() -> None:
    original = request()
    with pytest.raises(ValidationError):
        original.text = "replacement"
    malformed = original.model_copy(update={"text": "invalid\x00"})
    with pytest.raises(ValidationError):
        prepare_operation(policy(), malformed, now=NOW)
    wrong_limit = policy().model_copy(update={"max_batch_size": True})
    with pytest.raises(ValidationError):
        prepare_batch(wrong_limit, (request(),), now=NOW)


def test_wuphf_reuses_same_preparation_for_independent_settled_announcement_targets() -> None:
    chat_connection = connection(connection_id="chat", provider="telegram", actor_id="bot-actor", account_id="bot-id")
    chat_target = ChatTarget(connection_id="chat", conversation_id="-100123456")
    broadcast_policy = policy(
        connections=(connection(), chat_connection),
        allowed_targets=(target(), chat_target),
    )
    mail = request()
    chat = SendRequest(request_id="announce-chat", target=chat_target, text="Settled release is ready.")
    batch = prepare_batch(broadcast_policy, (mail, chat), now=NOW)
    assert len(batch.operations) == 2
    assert batch.operations[0] == prepare_operation(broadcast_policy, mail, now=NOW)
    assert batch.operations[1] == prepare_operation(broadcast_policy, chat, now=NOW)
    assert batch.policy_digest == broadcast_policy.digest
    assert "Settled release" not in repr(batch)
    altered = request(request_id="outside", target=target(to=("new@example.test",)))
    with pytest.raises(ValueError, match="exact target"):
        prepare_batch(broadcast_policy, (mail, altered), now=NOW)
    with pytest.raises(ValueError, match="duplicate"):
        prepare_batch(broadcast_policy, (mail, mail.model_copy(update={"request_id": "different-id"})), now=NOW)
    with pytest.raises(ValueError, match="duplicate"):
        prepare_batch(broadcast_policy, (mail, chat.model_copy(update={"request_id": "one"})), now=NOW)
    with pytest.raises(ValueError, match="finite tuple"):
        prepare_batch(broadcast_policy.model_copy(update={"max_batch_size": 1}), (mail, chat), now=NOW)


def test_exact_wire_body_and_nonsecret_version_headers_are_separate_from_authentication() -> None:
    prepared = prepare_operation(policy(), request(), now=NOW)
    wire = PreparedRequest(
        preparation=prepared,
        method="POST",
        route="gmail.messages.send",
        body='{"raw":"c2VhbGVk"}',
        headers=(("Content-Type", "application/json"),),
    )
    assert wire.wire_body == b'{"raw":"c2VhbGVk"}'
    assert "c2VhbGVk" not in repr(wire)
    assert wire.application_digest != wire.model_copy(update={"body": '{"raw":"other"}'}).application_digest
    with pytest.raises(ValueError, match="protocol headers"):
        PreparedRequest(
            preparation=prepared, method="POST", route="send", headers=(("Authorization", "Bearer secret"),)
        )
    with pytest.raises(ValueError, match="secret-free"):
        PreparedRequest(preparation=prepared, method="GET", route="read", query=(("access_token", "secret"),))


@pytest.mark.parametrize(
    "route", ["https://evil.test/send", "//evil.test/send", "/../send", "/%2e/send", "/send?q=x", "x\n"]
)
def test_untrusted_routes_cannot_become_an_http_endpoint(route: str) -> None:
    with pytest.raises(ValidationError):
        PreparedRequest(preparation=prepare_operation(policy(), request(), now=NOW), method="GET", route=route)


@pytest.mark.parametrize("repository", ["owner/../elsewhere", "owner/repo?extra", "owner/%2f", "owner\\repo"])
def test_forge_target_cannot_inject_a_request_path(repository: str) -> None:
    with pytest.raises(ValidationError):
        ForgeTarget(connection_id="forge", repository=repository, issue_number=1)
