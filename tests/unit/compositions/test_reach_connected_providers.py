"""Independent protocol fixtures for credential-free provider request plans."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from email import policy
from email.parser import BytesParser
from hashlib import sha256
from typing import Any

import pytest

from lychd.compositions.reach.connected.providers import build_request
from lychd.compositions.reach.connected.schemas import (
    ChatTarget,
    Connection,
    EmailTarget,
    ForgeTarget,
    PreparedOperation,
    ReadRequest,
    SendRequest,
    SocialTarget,
)

NOW = datetime(2026, 10, 29, 12, tzinfo=UTC)
type Target = EmailTarget | ChatTarget | ForgeTarget | SocialTarget


def connection(provider: str, actor: str = "123", account: str = "account") -> Connection:
    return Connection.model_validate(
        {
            "connection_id": "connection",
            "partition_id": "partition",
            "provider": provider,
            "account_id": account,
            "actor_id": actor,
        }
    )


def preparation(
    binding: Connection, target: Target, *, read: bool = False, text: str = "Hello", **fields: Any
) -> PreparedOperation:
    request = (
        ReadRequest(request_id="request", target=target, **fields)
        if read
        else SendRequest(request_id="request", target=target, text=text, **fields)
    )
    return PreparedOperation(
        request=request,
        connection=binding,
        policy_digest="a" * 64,
        prepared_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
    )


def mail_target(**fields: Any) -> EmailTarget:
    values: dict[str, Any] = {
        "connection_id": "connection",
        "mailbox_id": "me",
        "sender": "sender@example.org",
        "to": ("to@example.org",),
        "cc": ("cc@example.org",),
        "bcc": ("hidden@example.org",),
    }
    return EmailTarget(**(values | fields))


def chat_target(**fields: Any) -> ChatTarget:
    return ChatTarget.model_validate({"connection_id": "connection", "conversation_id": "456"} | fields)


def test_gmail_wire_has_canonical_sealed_mime_and_all_recipient_headers() -> None:
    value = preparation(
        connection("gmail", "sender@example.org"),
        mail_target(thread_id="thread123"),
        subject="A subject",
        reply_to_id="<original@example.net>",
        text="Plain body.\nSecond line.",
    )
    result = build_request(value)
    assert result.method == "POST"
    assert result.route == "gmail:/gmail/v1/users/me/messages/send"
    payload = json.loads(result.body)
    assert set(payload) == {"raw", "threadId"}
    assert payload["threadId"] == "thread123"
    raw = base64.urlsafe_b64decode(payload["raw"] + "=" * (-len(payload["raw"]) % 4))
    assert b"\r\n" in raw
    assert b"\n" not in raw.replace(b"\r\n", b"")
    message = BytesParser(policy=policy.default).parsebytes(raw)
    assert message["Date"] == "Thu, 29 Oct 2026 12:00:00 +0000"
    assert message["From"] == "sender@example.org"
    assert message["To"] == "to@example.org"
    assert message["Cc"] == "cc@example.org"
    assert message["Bcc"] == "hidden@example.org"
    assert message["Subject"] == "A subject"
    assert message["In-Reply-To"] == "<original@example.net>"
    assert message["References"] == "<original@example.net>"
    assert message["Message-ID"] == f"<{value.digest}@reach.invalid>"
    assert message.get_content().splitlines() == ["Plain body.", "Second line."]
    assert result == build_request(value)
    assert result.wire_body == result.body.encode()


@pytest.mark.parametrize("provider", ["gmail", "fastmail"])
def test_message_identity_is_stable_only_for_the_same_complete_preparation(provider: str) -> None:
    binding = connection(provider, "sender@example.org", "account123")
    target = (
        mail_target()
        if provider == "gmail"
        else mail_target(mailbox_id="account123", identity_id="identity123", draft_mailbox_id="drafts123")
    )
    original = preparation(binding, target, subject="Subject")

    def message_id(value: PreparedOperation) -> str:
        payload = json.loads(build_request(value).body)
        if provider == "fastmail":
            return payload["methodCalls"][0][1]["create"]["message"]["messageId"][0]
        raw = base64.urlsafe_b64decode(payload["raw"] + "=" * (-len(payload["raw"]) % 4))
        return str(BytesParser(policy=policy.default).parsebytes(raw)["Message-ID"])

    expected = message_id(original)
    assert message_id(original) == expected
    changed_body = original.model_copy(update={"request": original.request.model_copy(update={"text": "Changed"})})
    changed_time = original.model_copy(
        update={"prepared_at": NOW + timedelta(seconds=1), "expires_at": original.expires_at + timedelta(seconds=1)}
    )
    other_sender = preparation(
        binding.model_copy(update={"actor_id": "other@example.org"}),
        target.model_copy(update={"sender": "other@example.org"}),
        subject="Subject",
    )
    assert all(message_id(changed) != expected for changed in (changed_body, changed_time, other_sender))


def test_gmail_read_is_bounded_listing_not_unbounded_thread_or_mail_body() -> None:
    result = build_request(
        preparation(
            connection("gmail", "sender@example.org"),
            mail_target(),
            read=True,
            limit=7,
            cursor="next-page",
        )
    )
    assert (result.method, result.route, result.body) == ("GET", "gmail:/gmail/v1/users/me/messages", "")
    assert result.query == (("maxResults", "7"), ("includeSpamTrash", "false"), ("pageToken", "next-page"))
    with pytest.raises(ValueError, match="gmail_read_requires_me_without_thread"):
        build_request(
            preparation(
                connection("gmail", "sender@example.org"),
                mail_target(thread_id="thread123"),
                read=True,
            )
        )


def test_fastmail_read_uses_bounded_result_reference_and_header_projection() -> None:
    result = build_request(
        preparation(
            connection("fastmail", "sender@example.org", "account123"),
            mail_target(mailbox_id="account123"),
            read=True,
            limit=3,
            cursor="20",
        )
    )
    assert result.route == "fastmail:api"
    assert result.method == "POST"
    assert json.loads(result.body) == {
        "using": ["urn:ietf:params:jmap:core", "urn:ietf:params:jmap:mail"],
        "methodCalls": [
            ["Email/query", {"accountId": "account123", "limit": 3, "position": 20}, "query"],
            [
                "Email/get",
                {
                    "accountId": "account123",
                    "#ids": {"resultOf": "query", "name": "Email/query", "path": "/ids"},
                    "properties": ["id", "threadId", "from", "to", "cc", "bcc", "subject", "preview", "receivedAt"],
                },
                "get",
            ],
        ],
    }


def test_fastmail_submission_creates_exact_mail_then_explicit_bcc_envelope() -> None:
    result = build_request(
        preparation(
            connection("fastmail", "sender@example.org", "account123"),
            mail_target(mailbox_id="account123", identity_id="identity123", draft_mailbox_id="drafts123"),
            subject="Subject",
            reply_to_id="<original@example.net>",
            text="Text",
        )
    )
    payload = json.loads(result.body)
    assert payload["using"] == [
        "urn:ietf:params:jmap:core",
        "urn:ietf:params:jmap:mail",
        "urn:ietf:params:jmap:submission",
    ]
    assert payload["methodCalls"] == [
        [
            "Email/set",
            {
                "accountId": "account123",
                "create": {
                    "message": {
                        "mailboxIds": {"drafts123": True},
                        "keywords": {"$draft": True},
                        "from": [{"email": "sender@example.org"}],
                        "to": [{"email": "to@example.org"}],
                        "cc": [{"email": "cc@example.org"}],
                        "bcc": [{"email": "hidden@example.org"}],
                        "subject": "Subject",
                        "messageId": [f"{result.preparation.digest}@reach.invalid"],
                        "inReplyTo": ["original@example.net"],
                        "references": ["original@example.net"],
                        "textBody": [{"partId": "body", "type": "text/plain"}],
                        "bodyValues": {"body": {"value": "Text"}},
                    }
                },
            },
            "create",
        ],
        [
            "EmailSubmission/set",
            {
                "accountId": "account123",
                "create": {
                    "submission": {
                        "identityId": "identity123",
                        "emailId": "#message",
                        "envelope": {
                            "mailFrom": {"email": "sender@example.org"},
                            "rcptTo": [
                                {"email": "to@example.org"},
                                {"email": "cc@example.org"},
                                {"email": "hidden@example.org"},
                            ],
                        },
                    }
                },
                "onSuccessUpdateEmail": {"#submission": {"keywords/$draft": None}},
            },
            "submit",
        ],
    ]
    assert "raw" not in payload


def test_discord_payload_preserves_suppressed_mentions_and_existing_reply_interface() -> None:
    value = preparation(connection("discord"), chat_target(reply_to_id="789"))
    result = build_request(value)
    assert result.route == "discord:/api/v10/channels/456/messages"
    assert json.loads(result.body) == {
        "content": "Hello",
        "flags": 4,
        "allowed_mentions": {"parse": [], "replied_user": False},
        "nonce": sha256(b"123:456:request").hexdigest()[:25],
        "enforce_nonce": True,
        "message_reference": {"message_id": "789", "channel_id": "456", "fail_if_not_exists": True},
    }
    read = build_request(preparation(connection("discord"), chat_target(), read=True, limit=2, cursor="900"))
    assert read.query == (("limit", "2"), ("before", "900"))


def test_telegram_bot_send_uses_exact_numeric_target_without_parse_mode_or_token() -> None:
    result = build_request(
        preparation(
            connection("telegram"),
            chat_target(conversation_id="-1001234567890", reply_to_id="789"),
        )
    )
    assert result.route == "telegram:/sendMessage"
    assert json.loads(result.body) == {
        "chat_id": -1001234567890,
        "text": "Hello",
        "link_preview_options": {"is_disabled": True},
        "reply_parameters": {"message_id": 789},
    }
    assert "token" not in result.model_dump_json().lower()


def test_whatsapp_freeform_business_plan_has_no_invented_window_or_eligibility_claim() -> None:
    result = build_request(
        preparation(
            connection("whatsapp"),
            chat_target(conversation_id="421900123456", reply_to_id="wamid.ABC123="),
        )
    )
    assert result.route == "whatsapp:/v26.0/123/messages"
    assert json.loads(result.body) == {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "421900123456",
        "type": "text",
        "text": {"preview_url": False, "body": "Hello"},
        "context": {"message_id": "wamid.ABC123="},
    }


def test_github_is_pinned_timeline_comment_and_bounded_read() -> None:
    target = ForgeTarget(connection_id="connection", repository="owner/repository", issue_number=12)
    result = build_request(preparation(connection("github"), target))
    assert result.route == "github:/repos/owner/repository/issues/12/comments"
    assert json.loads(result.body) == {"body": "Hello"}
    assert result.headers == (("accept", "application/vnd.github+json"), ("x-github-api-version", "2026-03-10"))
    read = build_request(preparation(connection("github"), target, read=True, limit=5, cursor="2"))
    assert read.method == "GET"
    assert read.query == (("per_page", "5"), ("page", "2"))


@pytest.mark.parametrize(
    ("provider", "actor", "kind", "route", "expected"),
    [
        ("facebook", "123", "page", "facebook:/v26.0/123/feed", {"message": "Hello", "published": True}),
        (
            "linkedin",
            "urn:li:person:abc",
            "member",
            "linkedin:/rest/posts",
            {
                "author": "urn:li:person:abc",
                "commentary": "Hello",
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": [],
                },
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False,
            },
        ),
        ("x", "123", "user", "x:/2/tweets", {"text": "Hello", "made_with_ai": True}),
    ],
)
def test_social_profiles_prepare_only_original_organic_text(
    provider: str,
    actor: str,
    kind: str,
    route: str,
    expected: dict[str, Any],
) -> None:
    target = SocialTarget.model_validate({"connection_id": "connection", "account_id": actor, "actor_kind": kind})
    result = build_request(preparation(connection(provider, actor), target))
    assert result.route == route
    assert json.loads(result.body) == expected
    if provider == "linkedin":
        assert result.headers == (("linkedin-version", "202610"), ("x-restli-protocol-version", "2.0.0"))


@pytest.mark.parametrize(
    ("provider", "actor", "kind"),
    [
        ("linkedin", "urn:li:organization:abc", "organization"),
    ],
)
def test_linkedin_organization_has_exact_author_family(provider: str, actor: str, kind: str) -> None:
    target = SocialTarget.model_validate({"connection_id": "connection", "account_id": actor, "actor_kind": kind})
    assert json.loads(build_request(preparation(connection(provider, actor), target)).body)["author"] == actor


def test_linkedin_text_is_bounded_without_splitting() -> None:
    target = SocialTarget(connection_id="connection", account_id="urn:li:person:abc", actor_kind="member")
    binding = connection("linkedin", target.account_id)
    assert json.loads(build_request(preparation(binding, target, text="x" * 3000)).body)["commentary"] == "x" * 3000
    for text in ("x" * 3001, "(" * 1501, "😀" * 1501):
        with pytest.raises(ValueError, match="linkedin_text_limit"):
            build_request(preparation(binding, target, text=text))


def test_linkedin_plain_text_cannot_inject_little_markup_or_mentions() -> None:
    target = SocialTarget(connection_id="connection", account_id="urn:li:person:abc", actor_kind="member")
    text = r"Hi (team) \ [x] @[Name](urn:li:person:abc) | {x} <x> #a *b* _c_ ~d~"
    value = preparation(connection("linkedin", target.account_id), target, text=text)
    result = build_request(value)
    assert json.loads(result.body)["commentary"] == (
        r"Hi \(team\) \\ \[x\] \@\[Name\]\(urn:li:person:abc\) \| \{x\} \<x\> \#a \*b\* \_c\_ \~d\~"
    )
    assert result.preparation.request == value.request


@pytest.mark.parametrize("provider", ["telegram", "whatsapp"])
def test_bot_and_business_reads_cannot_expand_to_account_wide_intake(provider: str) -> None:
    with pytest.raises(ValueError, match=r"telegram_target_read_unsupported|whatsapp_history_unsupported"):
        build_request(preparation(connection(provider), chat_target(), read=True))


@pytest.mark.parametrize("provider", ["facebook", "linkedin", "x"])
def test_social_reads_private_audiences_and_replies_are_unsupported(provider: str) -> None:
    actor, kind = (
        ("urn:li:person:abc", "member")
        if provider == "linkedin"
        else ("123", "page" if provider == "facebook" else "user")
    )
    target = SocialTarget.model_validate({"connection_id": "connection", "account_id": actor, "actor_kind": kind})
    binding = connection(provider, actor)
    with pytest.raises(ValueError, match="social_read_unsupported"):
        build_request(preparation(binding, target, read=True))
    with pytest.raises(ValueError, match="social_requires_original_public_post"):
        build_request(preparation(binding, target, reply_to_id="456"))
    with pytest.raises(ValueError, match="social_requires_original_public_post"):
        build_request(preparation(binding, target.model_copy(update={"visibility": "private"})))


def test_facebook_personal_account_and_linkedin_wrong_actor_kind_are_refused() -> None:
    with pytest.raises(ValueError, match="Page actor"):
        build_request(preparation(connection("facebook"), SocialTarget(connection_id="connection", account_id="123")))
    with pytest.raises(ValueError, match="member or organization actor"):
        build_request(
            preparation(
                connection("linkedin", "urn:li:person:abc"),
                SocialTarget(connection_id="connection", account_id="urn:li:person:abc", actor_kind="organization"),
            )
        )


@pytest.mark.parametrize(
    "repository",
    [
        "owner/repo/extra",
        "https://evil.example/repo",
        "owner/../repo",
        "owner/r%2f",
        "owner/r?x",
        "owner/r#x",
        "owner/\\evil",
    ],
)
def test_github_refuses_repository_route_injection_even_from_unsafe_construct(repository: str) -> None:
    target = ForgeTarget(connection_id="connection", repository="owner/repo", issue_number=1)
    original = preparation(connection("github"), target)
    altered = original.model_copy(
        update={
            "request": original.request.model_copy(
                update={
                    "target": target.model_copy(update={"repository": repository}),
                }
            )
        }
    )
    with pytest.raises(ValueError, match=r"invalid_github_repository|repository identifier"):
        build_request(altered)


@pytest.mark.parametrize("value", ["@username", "00123", "123/456", "123?x", "123%2f456", "1.0", "+123"])
def test_telegram_rejects_nonexact_numeric_target(value: str) -> None:
    with pytest.raises(ValueError, match="invalid_numeric_id"):
        build_request(preparation(connection("telegram"), chat_target(conversation_id=value)))


def test_radicle_wrong_family_connection_and_revision_cannot_build() -> None:
    target = ForgeTarget(connection_id="connection", repository="owner/repo", issue_number=1)
    with pytest.raises(ValueError, match="forge_provider_unsupported"):
        build_request(preparation(connection("radicle"), target))
    with pytest.raises(ValueError, match="same provider family"):
        build_request(preparation(connection("gmail", "sender@example.org"), chat_target()))
    with pytest.raises(ValueError, match="same provider family"):
        build_request(preparation(connection("discord"), chat_target(connection_id="other")))
    with pytest.raises(ValueError, match="unsupported_profile_revision"):
        build_request(
            preparation(connection("discord").model_copy(update={"profile_revision": "future"}), chat_target())
        )


def test_fastmail_requires_exact_account_identity_and_draft_mailbox() -> None:
    for target in (
        mail_target(mailbox_id="other", identity_id="identity", draft_mailbox_id="drafts"),
        mail_target(mailbox_id="account123", identity_id="identity"),
        mail_target(mailbox_id="account123", draft_mailbox_id="drafts"),
    ):
        with pytest.raises(ValueError, match=r"Email mailbox|sending identity and draft mailbox"):
            build_request(
                preparation(connection("fastmail", "sender@example.org", "account123"), target, subject="Subject")
            )


def test_gmail_sender_header_injection_and_thread_without_reply_are_refused() -> None:
    with pytest.raises(ValueError, match="mailbox and sender"):
        build_request(preparation(connection("gmail", "other@example.org"), mail_target(), subject="Subject"))
    original = preparation(connection("gmail", "sender@example.org"), mail_target(), subject="Subject")
    altered = original.model_copy(
        update={"request": original.request.model_copy(update={"subject": "Subject\r\nBcc: injected@example.org"})}
    )
    with pytest.raises(ValueError, match="Control characters"):
        build_request(altered)
    with pytest.raises(ValueError, match="gmail_thread_requires_reply_headers"):
        build_request(
            preparation(connection("gmail", "sender@example.org"), mail_target(thread_id="123"), subject="Subject")
        )


@pytest.mark.parametrize(("provider", "limit"), [("discord", 2001), ("telegram", 4097), ("whatsapp", 4097)])
def test_chat_message_limit_refuses_without_splitting(provider: str, limit: int) -> None:
    with pytest.raises(ValueError, match="text_limit"):
        build_request(preparation(connection(provider), chat_target(), text="x" * limit))


def test_wire_digest_changes_with_complete_envelope_and_protocol_headers() -> None:
    original = preparation(connection("gmail", "sender@example.org"), mail_target(), subject="Subject")
    changed = preparation(
        connection("gmail", "sender@example.org"), mail_target(bcc=("other@example.org",)), subject="Subject"
    )
    assert build_request(original).application_digest != build_request(changed).application_digest
    result = build_request(original)
    assert (
        result.application_digest
        != result.model_copy(update={"headers": (("accept", "application/json"),)}).application_digest
    )


def test_unsupported_attachments_ads_and_personal_intake_fields_are_closed() -> None:
    for field in ("attachments", "ad_account", "budget", "personal_session", "token", "api_url"):
        with pytest.raises(ValueError, match="Extra inputs are not permitted"):
            SendRequest.model_validate(
                {
                    "request_id": "request",
                    "target": chat_target().model_dump(),
                    "text": "Hello",
                    field: "forbidden",
                }
            )
